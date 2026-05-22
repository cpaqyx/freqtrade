"""
高倍率播种策略 - 基于分钟级别K线的合约交易策略
只做多，不做空，逐仓模式，20倍杠杆
"""

import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from typing import Optional
import logging
from freqtrade.persistence import Trade

# 导入图形分析模块
try:
    from user_data.common.line_format_v2 import kline_1m_shape, check_double_top
except ImportError:
    from line_format_v2 import kline_1m_shape, check_double_top

from freqtrade.strategy import IStrategy, DecimalParameter

logger = logging.getLogger(__name__)


class HighRateSowing(IStrategy):
    """
    高倍率播种策略
    - 分钟级别（1m）
    - 只做多
    - 逐仓模式，20倍杠杆
    - 基于波形指标的压力支撑判断
    - 最多同时持有3个合约
    """
    
    # 启动所需K线数量：分钟级别需要足够的历史数据计算指标
    startup_candle_count: int = 200
    
    # 每分钟都执行策略
    process_only_new_candles = False
    
    INTERFACE_VERSION = 3
    
    # ==================== 基础策略参数 ====================
    
    # 时间周期：分钟级别
    timeframe = '1m'
    
    # 是否允许做空：仅做多
    can_short = False
    
    # 仓位调整：禁用
    position_adjustment_enable = False
    
    # ==================== ROI 和止损配置 ====================
    
    # 极端ROI，由策略信号控制平仓
    minimal_roi = {
        "0": 10.0
    }
    
    # 极端止损，由策略信号控制
    stoploss = -0.99
    
    # ==================== 合约交易参数 ====================
    
    # 杠杆倍数
    leverage_default = 20
    
    # 交易模式：合约
    trading_mode = 'futures'
    
    # 保证金模式：逐仓
    margin_mode = 'isolated'
    
    # ==================== 可优化参数 ====================
    
    # -------------------- 通用参数 --------------------
    
    # 最大持仓数量
    max_open_trades = 3
    
    # 从最高点跌幅阈值（建仓条件1）
    max_drop_from_high = DecimalParameter(
        0.05, 0.50, default=0.15, decimals=2, space='buy', optimize=True, load=True
    )
    
    # 单根K线涨幅阈值
    candle_rise_threshold = DecimalParameter(
        0.001, 0.05, default=0.005, decimals=3, space='buy', optimize=True, load=True
    )
    
    # 连续涨幅阈值（3根K线）
    continuous_rise_threshold = DecimalParameter(
        0.005, 0.15, default=0.02, decimals=3, space='buy', optimize=True, load=True
    )
    
    # 图形下跌幅度阈值
    pattern_drop_threshold = DecimalParameter(
        0.005, 0.30, default=0.03, decimals=3, space='buy', optimize=True, load=True
    )
    
    # -------------------- 压力支撑相关参数 --------------------
    
    # 建仓：离支撑价格的百分比阈值（价格在支撑位上方X%以内）
    entry_near_support_pct = DecimalParameter(
        0.001, 0.10, default=0.02, decimals=3, space='buy', optimize=True, load=True
    )
    
    # 平仓：离压力价格的百分比阈值（价格在压力位下方X%以内，可为负数）
    exit_near_resistance_pct = DecimalParameter(
        -0.05, 0.10, default=0.02, decimals=3, space='sell', optimize=True, load=True
    )
    
    # -------------------- 平仓相关参数 --------------------
    
    # 单根K线跌幅阈值
    candle_drop_threshold = DecimalParameter(
        0.001, 0.05, default=0.005, decimals=3, space='sell', optimize=True, load=True
    )
    
    # 连续跌幅阈值（3根K线）
    continuous_drop_threshold = DecimalParameter(
        0.005, 0.15, default=0.02, decimals=3, space='sell', optimize=True, load=True
    )
    
    # 双顶高位阈值
    double_top_higher_threshold = DecimalParameter(
        0.005, 0.15, default=0.03, decimals=3, space='sell', optimize=True, load=True
    )
    
    # 双顶低位阈值
    double_top_lower_threshold = DecimalParameter(
        0.01, 0.15, default=0.05, decimals=2, space='sell', optimize=True, load=True
    )
    
    # 最后一段下跌阈值
    last_down_threshold = DecimalParameter(
        0.01, 0.15, default=0.05, decimals=2, space='sell', optimize=True, load=True
    )
    
    # -------------------- 动态止损参数 --------------------
    
    # 动态止损触发阈值（价格低于支撑价格X%时触发）
    dynamic_stoploss_pct = DecimalParameter(
        -0.02, 0.05, default=-0.005, decimals=3, space='sell', optimize=True, load=True
    )
    
    # 是否启用动态止损
    enable_dynamic_stoploss = True
    
    def __init__(self, config: dict) -> None:
        super().__init__(config)
        logger.info("[OK] 高倍率播种策略已初始化 - 分钟级别，20倍杠杆，逐仓模式")
    
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str],
                 side: str, **kwargs) -> float:
        """
        设置杠杆倍数为20倍
        """
        return self.leverage_default
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        计算所有指标
        """
        logger.info(f"populate_indicators执行 - {metadata['pair']}")
        
        # ========== 基础指标 ==========
        
        # 90周期最高价和最低价
        dataframe['max_90'] = dataframe['high'].rolling(90).max()
        dataframe['min_90'] = dataframe['low'].rolling(90).min()
        
        # 单根K线涨跌幅
        dataframe['candle_change'] = (dataframe['close'] - dataframe['open']) / dataframe['open']
        
        # 是否阳线/阴线
        dataframe['is_green'] = (dataframe['close'] > dataframe['open']).astype(int)
        dataframe['is_red'] = (dataframe['close'] < dataframe['open']).astype(int)
        
        # ========== 波形指标 ==========
        
        dataframe['pattern'] = None
        dataframe['shape_resistance'] = np.nan  # 压力价格
        dataframe['shape_support'] = np.nan     # 支撑价格
        dataframe['last_segment_line'] = ''     # 最近线段方向
        dataframe['last_segment_min'] = np.nan  # 最近down线段的最小价格
        dataframe['last_segment_max'] = np.nan  # 最近up线段的最大价格
        
        df_len = len(dataframe)
        logger.info(f"K线长度：{df_len}")
        
        # 计算波形指标
        for i in range(90, df_len):
            close_prices = dataframe['close'].iloc[i - 89:i + 1].values
            try:
                pattern = kline_1m_shape(close_prices)
                dataframe.at[dataframe.index[i], 'pattern'] = str(pattern)
                
                # 计算压力支撑价格
                if pattern and len(pattern) >= 2:
                    # 最近两根线段
                    last_two = pattern[-2:] if len(pattern) >= 2 else pattern
                    
                    # 压力价格：最近两根线段的最大值中的最大值
                    max_prices = [seg.get('max_price', 0) for seg in last_two]
                    resistance = max(max_prices) if max_prices else np.nan
                    dataframe.at[dataframe.index[i], 'shape_resistance'] = resistance
                    
                    # 支撑价格：最近两根线段的最小值中的最小值
                    min_prices = [seg.get('min_price', float('inf')) for seg in last_two]
                    support = min(min_prices) if min_prices else np.nan
                    dataframe.at[dataframe.index[i], 'shape_support'] = support
                    
                    # 最近一根线段的方向
                    if pattern:
                        last_seg = pattern[-1]
                        dataframe.at[dataframe.index[i], 'last_segment_line'] = last_seg.get('line', '')
                        
                        # 找到最近的down线段，记录其最小价格
                        for seg in reversed(pattern):
                            if seg.get('line') == 'down':
                                dataframe.at[dataframe.index[i], 'last_segment_min'] = seg.get('min_price', np.nan)
                                break
                        
                        # 找到最近的up线段，记录其最大价格
                        for seg in reversed(pattern):
                            if seg.get('line') == 'up':
                                dataframe.at[dataframe.index[i], 'last_segment_max'] = seg.get('max_price', np.nan)
                                break
                
            except Exception as e:
                logger.warning(f"计算波形指标失败 {dataframe.index[i]}: {e}")
                dataframe.at[dataframe.index[i], 'pattern'] = '[]'
        
        # ========== 辅助指标 ==========
        
        # 3根K线累计涨跌幅
        dataframe['change_3'] = (
            (dataframe['close'] - dataframe['close'].shift(3)) / dataframe['close'].shift(3)
        )
        
        # 距离压力位的百分比
        dataframe['dist_to_resistance'] = (
            (dataframe['shape_resistance'] - dataframe['close']) / dataframe['shape_resistance']
        )
        
        # 距离支撑位的百分比
        dataframe['dist_to_support'] = (
            (dataframe['close'] - dataframe['shape_support']) / dataframe['shape_support']
        )
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        建仓条件
        """
        logger.info(f"populate_entry_trend执行 - {metadata['pair']}")
        
        dataframe['enter_long'] = 0
        dataframe['enter_tag'] = ''
        
        # ========== 条件1：从最高点下跌超过阈值 ==========
        condition_drop = (
            (dataframe['close'] <= dataframe['max_90'] * (1 - self.max_drop_from_high.value))
        )
        
        # ========== 条件2：涨幅条件 ==========
        
        # 2.1 单根K线涨幅
        single_rise = (dataframe['candle_change'] > self.candle_rise_threshold.value)
        
        # 2.2 连续3根K线上涨
        continuous_rise = (
            (dataframe['is_green'] == 1) &
            (dataframe['is_green'].shift(1) == 1) &
            (dataframe['is_green'].shift(2) == 1) &
            (dataframe['change_3'] > self.continuous_rise_threshold.value)
        )
        
        rise_condition = single_rise | continuous_rise
        
        # ========== 条件3：图形反转条件 ==========
        dataframe['pattern_entry_signal'] = False
        
        for i in range(90, len(dataframe)):
            if not rise_condition.iloc[i]:
                continue
            
            pattern_str = dataframe['pattern'].iloc[i]
            if not pattern_str or pattern_str == '[]':
                continue
            
            try:
                pattern = eval(pattern_str, {"np": np})
                if not pattern or len(pattern) == 0:
                    continue
                
                # 检查图形条件：最后1个为up/flat，倒数第二为down且跌幅>阈值
                if len(pattern) >= 2:
                    last = pattern[-1]
                    second_last = pattern[-2]
                    
                    if last['line'] in ['up', 'flat'] and second_last['line'] == 'down':
                        drop_pct = abs(
                            (second_last['end_price'] - second_last['start_price']) / 
                            second_last['start_price']
                        )
                        if drop_pct > self.pattern_drop_threshold.value:
                            dataframe.at[dataframe.index[i], 'pattern_entry_signal'] = True
                            continue
                
                # 检查三段模式
                if len(pattern) >= 3:
                    last = pattern[-1]
                    second_last = pattern[-2]
                    third_last = pattern[-3]
                    
                    if last['line'] in ['up', 'flat']:
                        if second_last['line'] == 'flat':
                            if third_last['line'] == 'down':
                                drop_pct = abs(
                                    (third_last['end_price'] - third_last['start_price']) / 
                                    third_last['start_price']
                                )
                                if drop_pct > self.pattern_drop_threshold.value:
                                    dataframe.at[dataframe.index[i], 'pattern_entry_signal'] = True
                                    continue
                        
                        elif second_last['line'] == 'up' and second_last['k_cnt'] < 2:
                            rise_pct = abs(
                                (second_last['end_price'] - second_last['start_price']) / 
                                second_last['start_price']
                            )
                            if rise_pct <= 0.05:
                                if third_last['line'] == 'down':
                                    drop_pct = abs(
                                        (third_last['end_price'] - third_last['start_price']) / 
                                        third_last['start_price']
                                    )
                                    if drop_pct > self.pattern_drop_threshold.value:
                                        dataframe.at[dataframe.index[i], 'pattern_entry_signal'] = True
                                        continue
            
            except Exception as e:
                logger.warning(f"解析图形指标失败 {dataframe.index[i]}: {e}")
        
        condition_pattern = rise_condition & dataframe['pattern_entry_signal']
        
        # ========== 条件4：支撑位附近 + 上涨趋势 ==========
        
        # 价格在支撑位上方X%以内
        near_support = (
            (dataframe['dist_to_support'] >= 0) &
            (dataframe['dist_to_support'] <= self.entry_near_support_pct.value)
        )
        
        # 最近一根线段为up（上涨趋势）
        uptrend = (dataframe['last_segment_line'] == 'up')
        
        condition_support = near_support & uptrend
        
        # ========== 最终建仓条件 ==========
        
        # 必须满足：条件1或条件2+3，并且满足条件4
        base_condition = condition_drop | condition_pattern
        final_condition = base_condition & condition_support
        
        dataframe.loc[final_condition, 'enter_long'] = 1
        
        # 设置入场标签
        drop_from_high = (dataframe['max_90'] - dataframe['close']) / dataframe['max_90']
        
        dataframe.loc[condition_drop & condition_support, 'enter_tag'] = (
            'C1:跌' + (drop_from_high * 100).round(1).astype(str) + '%+支撑'
        )
        
        dataframe.loc[condition_pattern & condition_support, 'enter_tag'] = 'C2:涨+反转+支撑'
        
        dataframe.loc[condition_drop & condition_pattern & condition_support, 'enter_tag'] = (
            'C1+C2:跌' + (drop_from_high * 100).round(1).astype(str) + '%+反转+支撑'
        )
        
        # 统计信号
        entry_count = final_condition.sum()
        if entry_count > 0:
            logger.info(f"[{metadata['pair']}] 生成 {entry_count} 个建仓信号")
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        平仓条件
        """
        logger.info(f"populate_exit_trend执行 - {metadata['pair']}")
        
        dataframe['exit_long'] = 0
        dataframe['exit_tag'] = ''
        
        # ========== 条件1：跌幅条件 ==========
        
        # 单根K线跌幅
        single_drop = (dataframe['candle_change'] < -self.candle_drop_threshold.value)
        
        # 连续3根K线下跌
        continuous_drop = (
            (dataframe['is_red'] == 1) &
            (dataframe['is_red'].shift(1) == 1) &
            (dataframe['is_red'].shift(2) == 1) &
            (dataframe['change_3'] < -self.continuous_drop_threshold.value)
        )
        
        drop_condition = single_drop | continuous_drop
        
        # ========== 条件2：双顶检测 ==========
        dataframe['double_top_signal'] = False
        
        for i in range(90, len(dataframe)):
            if not drop_condition.iloc[i]:
                continue
            
            pattern_str = dataframe['pattern'].iloc[i]
            if not pattern_str or pattern_str == '[]':
                continue
            
            try:
                pattern = eval(pattern_str, {"np": np})
                if not pattern or len(pattern) == 0:
                    continue
                
                # 检查最后一段是否为down且跌幅小于阈值
                last = pattern[-1]
                if last['line'] == 'down':
                    drop_pct = abs(
                        (last['end_price'] - last['start_price']) / last['start_price']
                    )
                    if drop_pct < self.last_down_threshold.value:
                        # 获取所有up段
                        up_segments = [seg for seg in pattern if seg['line'] == 'up']
                        
                        if up_segments:
                            price_a = last['start_price']
                            if check_double_top(
                                up_segments, price_a,
                                self.double_top_higher_threshold.value,
                                self.double_top_lower_threshold.value
                            ):
                                dataframe.at[dataframe.index[i], 'double_top_signal'] = True
            
            except Exception as e:
                logger.warning(f"解析图形指标失败 {dataframe.index[i]}: {e}")
        
        condition_double_top = drop_condition & dataframe['double_top_signal']
        
        # ========== 条件3：压力位附近 + 下降趋势 ==========
        
        # 价格在压力位下方X%以内（参数可为负）
        near_resistance = (
            (dataframe['dist_to_resistance'] >= self.exit_near_resistance_pct.value)
        )
        
        # 最近一根线段为down（下降趋势）
        downtrend = (dataframe['last_segment_line'] == 'down')
        
        condition_resistance = near_resistance & downtrend
        
        # ========== 最终平仓条件 ==========
        
        # 满足：条件1+2 或 条件3
        final_condition = condition_double_top | condition_resistance
        
        dataframe.loc[final_condition, 'exit_long'] = 1
        
        # 设置出场标签
        dataframe.loc[condition_double_top, 'exit_tag'] = '双顶'
        dataframe.loc[condition_resistance, 'exit_tag'] = '压力位'
        dataframe.loc[condition_double_top & condition_resistance, 'exit_tag'] = '双顶+压力位'
        
        # 统计信号
        exit_count = final_condition.sum()
        if exit_count > 0:
            logger.info(f"[{metadata['pair']}] 生成 {exit_count} 个平仓信号")
        
        return dataframe
    
    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float, **kwargs) -> Optional[float]:
        """
        动态止损：当价格上涨时，设置止损价格为最近down线段的最小价格（支撑价格）
        当价格低于支撑价格X%时触发止损
        """
        if not self.enable_dynamic_stoploss:
            return None
        
        # 获取当前dataframe
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe is None or len(dataframe) == 0:
            return None
        
        last_row = dataframe.iloc[-1]
        
        # 获取最近down线段的最小价格（支撑价格）
        support_price = last_row.get('last_segment_min', np.nan)
        
        if pd.isna(support_price) or support_price <= 0:
            return None
        
        # 计算止损触发价格：支撑价格 * (1 + dynamic_stoploss_pct)
        # 例如：dynamic_stoploss_pct = -0.005，则止损价为支撑价的99.5%
        stoploss_price = support_price * (1 + self.dynamic_stoploss_pct.value)
        
        # 如果当前价格低于止损价格，触发止损
        if current_rate < stoploss_price:
            logger.info(f"[动态止损] {pair} 当前价{current_rate:.2f} < 止损价{stoploss_price:.2f} (支撑{support_price:.2f})")
            return 0.01  # 立即平仓（返回很小的止损值）
        
        # 否则返回None，使用默认止损
        return None
    
    def confirm_trade_entry(self, pair: str, order_type: str, amount: float,
                           rate: float, time_in_force: str, current_time: datetime,
                           entry_tag: Optional[str], side: str, **kwargs) -> bool:
        """
        确认是否开仓：检查当前持仓数量是否超过限制
        """
        # 获取当前开放交易数量
        open_trades = Trade.get_trades_proxy(is_open=True)
        open_count = len([t for t in open_trades])
        
        if open_count >= self.max_open_trades:
            logger.info(f"[开仓拒绝] {pair} 当前持仓{open_count}个，已达上限{self.max_open_trades}")
            return False
        
        logger.info(f"[开仓确认] {pair} 当前持仓{open_count}个，允许开仓")
        return True
    
    def bot_loop_start(self, current_time: datetime, **kwargs) -> None:
        """
        每个循环开始时执行（每分钟）
        用于实时监控和动态止损
        """
        # 获取所有交易对
        if not self.dp:
            return
        
        pairs = self.dp.current_whitelist()
        if not pairs:
            return
        
        for pair in pairs:
            try:
                # 获取最新数据
                dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
                if dataframe is None or len(dataframe) == 0:
                    continue
                
                last_row = dataframe.iloc[-1]
                
                # 检查动态止损
                if self.enable_dynamic_stoploss:
                    support_price = last_row.get('last_segment_min', np.nan)
                    current_rate = last_row['close']
                    
                    if not pd.isna(support_price) and support_price > 0:
                        stoploss_price = support_price * (1 + self.dynamic_stoploss_pct.value)
                        
                        # 检查是否有该交易对的持仓
                        open_trades = Trade.get_trades_proxy(is_open=True, pair=pair)
                        for trade in open_trades:
                            if current_rate < stoploss_price:
                                logger.info(
                                    f"[动态止损触发] {pair} "
                                    f"当前价{current_rate:.2f} < 止损价{stoploss_price:.2f} "
                                    f"(支撑{support_price:.2f})"
                                )
                                # 这里只是日志，实际止损由custom_stoploss处理
            
            except Exception as e:
                logger.error(f"bot_loop_start处理{pair}失败: {e}")
