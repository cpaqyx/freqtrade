"""
高倍率播种策略 - 支持做空版本
基于分钟级别K线的合约交易策略
双向持仓（多空），逐仓模式，10倍杠杆

核心逻辑：
- 买入信号时：有空仓则平空，无空仓则开多
- 卖出信号时：有多仓则平多，无多仓则开空
- 单向持仓：同一时间只持有一个方向
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


class HighRateSowingSL(IStrategy):
    """
    高倍率播种策略 - 支持做空版本
    - 分钟级别（1m）
    - 支持做多和做空（双向）
    - 逐仓模式，10倍杠杆
    - 基于波形指标的压力支撑判断
    - 最多同时持有3个合约（单向持仓）
    """
    
    # 启动所需K线数量：分钟级别需要足够的历史数据计算指标
    startup_candle_count: int = 200
    
    # 每分钟都执行策略
    process_only_new_candles = False
    
    INTERFACE_VERSION = 3
    
    # ==================== 基础策略参数 ====================
    
    # 时间周期：分钟级别
    timeframe = '1m'
    
    # 是否允许做空：支持做空
    can_short = True
    
    # 仓位调整：禁用
    position_adjustment_enable = False
    
    # ==================== ROI 和止损配置 ====================
    
    # 极端ROI，由策略信号控制平仓
    minimal_roi = {
        "0": 10.0
    }
    
    # 合理止损，防止爆仓
    stoploss = -0.05
    
    # ==================== 合约交易参数 ====================
    
    # 杠杆倍数 - 降低杠杆减少爆仓风险
    leverage_default = 10
    
    # 交易模式：合约
    trading_mode = 'futures'
    
    # 保证金模式：逐仓
    margin_mode = 'isolated'
    
    # ==================== 可优化参数 ====================
    
    # -------------------- 通用参数 --------------------
    
    # 最大持仓数量
    max_open_trades = 3
    
    # 从最高点跌幅阈值（建仓条件1）- 降低阈值以适应震荡行情
    max_drop_from_high = DecimalParameter(
        0.01, 0.50, default=0.03, decimals=2, space='buy', optimize=True, load=True
    )
    
    # 单根K线涨幅阈值
    candle_rise_threshold = DecimalParameter(
        0.001, 0.05, default=0.003, decimals=3, space='buy', optimize=True, load=True
    )
    
    # 连续涨幅阈值（3根K线）
    continuous_rise_threshold = DecimalParameter(
        0.002, 0.15, default=0.01, decimals=3, space='buy', optimize=True, load=True
    )
    
    # 图形下跌幅度阈值 - 降低阈值以适应震荡行情
    pattern_drop_threshold = DecimalParameter(
        0.002, 0.30, default=0.01, decimals=3, space='buy', optimize=True, load=True
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
        logger.info("[OK] 高倍率播种策略(做空版)已初始化 - 分钟级别，20倍杠杆，逐仓模式，支持做空")
    
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
        
        核心逻辑：
        - enter_long = 1: 买入信号 → 有空仓则平空，无空仓则开多
        - enter_short = 1: 卖出信号 → 有多仓则平多，无多仓则开空
        """
        logger.info(f"populate_entry_trend执行 - {metadata['pair']}")
        
        dataframe['enter_long'] = 0
        dataframe['enter_short'] = 0
        dataframe['enter_tag'] = ''
        
        # ========== 条件1：从最高点下跌超过阈值（买入信号）==========
        condition_drop = (
            (dataframe['close'] <= dataframe['max_90'] * (1 - self.max_drop_from_high.value))
        )
        
        # ========== 条件2：涨幅条件（买入信号）==========
        
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
        
        # ========== 条件3：图形反转条件（大跌后反弹 - 买入信号）==========
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
        
        # ========== 条件4：震荡行情支撑位反弹（买入信号）==========
        support_available = dataframe['last_segment_min'].notna() & (dataframe['last_segment_min'] > 0)
        
        near_support_oscillation = (
            support_available &
            (dataframe['close'] >= dataframe['last_segment_min'] * 0.98) &
            (dataframe['close'] <= dataframe['last_segment_min'] * 1.02) &
            single_rise
        )
        
        # ========== 条件5：简单上涨趋势入场（买入信号）==========
        uptrend = (dataframe['last_segment_line'] == 'up')
        simple_uptrend_entry = uptrend & single_rise
        
        # ========== 条件4验证：支撑位附近 ==========
        near_support = (
            (dataframe['shape_support'].notna()) &
            (dataframe['dist_to_support'] >= 0) &
            (dataframe['dist_to_support'] <= self.entry_near_support_pct.value)
        )
        
        condition_support = near_support & uptrend
        
        # ========== 买入信号（enter_long）==========
        base_condition = condition_drop | condition_pattern
        long_condition = (base_condition & condition_support) | (base_condition & uptrend)
        long_condition = long_condition | near_support_oscillation
        long_condition = long_condition | simple_uptrend_entry
        
        dataframe.loc[long_condition, 'enter_long'] = 1
        
        # 设置买入入场标签
        drop_from_high = (dataframe['max_90'] - dataframe['close']) / dataframe['max_90']
        
        dataframe.loc[condition_drop & condition_support, 'enter_tag'] = (
            'C1:跌' + (drop_from_high * 100).round(1).astype(str) + '%+支撑'
        )
        
        dataframe.loc[condition_pattern & condition_support, 'enter_tag'] = 'C2:涨+反转+支撑'
        
        dataframe.loc[condition_drop & condition_pattern & condition_support, 'enter_tag'] = (
            'C1+C2:跌' + (drop_from_high * 100).round(1).astype(str) + '%+反转+支撑'
        )
        
        dataframe.loc[condition_drop & uptrend & ~condition_support, 'enter_tag'] = (
            'C1:跌' + (drop_from_high * 100).round(1).astype(str) + '%+上涨'
        )
        
        dataframe.loc[condition_pattern & uptrend & ~condition_support, 'enter_tag'] = 'C2:涨+反转+上涨'
        
        dataframe.loc[condition_drop & condition_pattern & uptrend & ~condition_support, 'enter_tag'] = (
            'C1+C2:跌' + (drop_from_high * 100).round(1).astype(str) + '%+反转+上涨'
        )
        
        dataframe.loc[near_support_oscillation, 'enter_tag'] = 'C3:震荡支撑反弹'
        
        dataframe.loc[simple_uptrend_entry, 'enter_tag'] = 'C4:上涨趋势入场'
        
        # ========== 卖出信号（enter_short）==========
        # 使用原策略的平仓条件作为开空信号
        
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
        
        # 双顶检测
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
                
                last = pattern[-1]
                if last['line'] == 'down':
                    drop_pct = abs(
                        (last['end_price'] - last['start_price']) / last['start_price']
                    )
                    if drop_pct < self.last_down_threshold.value:
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
        
        # 压力位附近 + 下降趋势
        near_resistance = (
            (dataframe['dist_to_resistance'] >= self.exit_near_resistance_pct.value)
        )
        
        downtrend = (dataframe['last_segment_line'] == 'down')
        
        condition_resistance = near_resistance & downtrend
        
        # 卖出信号条件
        short_condition = condition_double_top | condition_resistance
        
        dataframe.loc[short_condition, 'enter_short'] = 1
        
        # 设置卖出入场标签（开空）
        dataframe.loc[condition_double_top & (dataframe['enter_tag'] == ''), 'enter_tag'] = 'S1:双顶开空'
        dataframe.loc[condition_resistance & (dataframe['enter_tag'] == ''), 'enter_tag'] = 'S2:压力位开空'
        dataframe.loc[condition_double_top & condition_resistance & (dataframe['enter_tag'] == ''), 'enter_tag'] = 'S3:双顶+压力位开空'
        
        # 统计信号
        long_count = long_condition.sum()
        short_count = short_condition.sum()
        if long_count > 0 or short_count > 0:
            logger.info(f"[{metadata['pair']}] 生成 {long_count} 个做多信号, {short_count} 个做空信号")
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        平仓条件
        
        核心逻辑：
        - exit_long = 1: 卖出信号 → 有多仓则平多
        - exit_short = 1: 买入信号 → 有空仓则平空
        """
        logger.info(f"populate_exit_trend执行 - {metadata['pair']}")
        
        dataframe['exit_long'] = 0
        dataframe['exit_short'] = 0
        dataframe['exit_tag'] = ''
        
        # ========== 卖出信号（exit_long / 平多仓）==========
        
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
        
        # 双顶检测
        dataframe['double_top_signal_exit'] = False
        
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
                
                last = pattern[-1]
                if last['line'] == 'down':
                    drop_pct = abs(
                        (last['end_price'] - last['start_price']) / last['start_price']
                    )
                    if drop_pct < self.last_down_threshold.value:
                        up_segments = [seg for seg in pattern if seg['line'] == 'up']
                        
                        if up_segments:
                            price_a = last['start_price']
                            if check_double_top(
                                up_segments, price_a,
                                self.double_top_higher_threshold.value,
                                self.double_top_lower_threshold.value
                            ):
                                dataframe.at[dataframe.index[i], 'double_top_signal_exit'] = True
            
            except Exception as e:
                logger.warning(f"解析图形指标失败 {dataframe.index[i]}: {e}")
        
        condition_double_top = drop_condition & dataframe['double_top_signal_exit']
        
        # 压力位附近 + 下降趋势
        near_resistance = (
            (dataframe['dist_to_resistance'] >= self.exit_near_resistance_pct.value)
        )
        
        downtrend = (dataframe['last_segment_line'] == 'down')
        
        condition_resistance = near_resistance & downtrend
        
        # 平多仓条件
        exit_long_condition = condition_double_top | condition_resistance
        
        dataframe.loc[exit_long_condition, 'exit_long'] = 1
        
        # 设置平多仓标签
        dataframe.loc[condition_double_top, 'exit_tag'] = '双顶平多'
        dataframe.loc[condition_resistance, 'exit_tag'] = '压力位平多'
        dataframe.loc[condition_double_top & condition_resistance, 'exit_tag'] = '双顶+压力位平多'
        
        # ========== 买入信号（exit_short / 平空仓）==========
        
        # 从最高点下跌超过阈值
        condition_drop_exit = (
            (dataframe['close'] <= dataframe['max_90'] * (1 - self.max_drop_from_high.value))
        )
        
        # 涨幅条件
        single_rise = (dataframe['candle_change'] > self.candle_rise_threshold.value)
        
        continuous_rise = (
            (dataframe['is_green'] == 1) &
            (dataframe['is_green'].shift(1) == 1) &
            (dataframe['is_green'].shift(2) == 1) &
            (dataframe['change_3'] > self.continuous_rise_threshold.value)
        )
        
        rise_condition = single_rise | continuous_rise
        
        # 图形反转条件
        dataframe['pattern_exit_signal'] = False
        
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
                
                if len(pattern) >= 2:
                    last = pattern[-1]
                    second_last = pattern[-2]
                    
                    if last['line'] in ['up', 'flat'] and second_last['line'] == 'down':
                        drop_pct = abs(
                            (second_last['end_price'] - second_last['start_price']) / 
                            second_last['start_price']
                        )
                        if drop_pct > self.pattern_drop_threshold.value:
                            dataframe.at[dataframe.index[i], 'pattern_exit_signal'] = True
                            continue
                
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
                                    dataframe.at[dataframe.index[i], 'pattern_exit_signal'] = True
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
                                        dataframe.at[dataframe.index[i], 'pattern_exit_signal'] = True
                                        continue
            
            except Exception as e:
                logger.warning(f"解析图形指标失败 {dataframe.index[i]}: {e}")
        
        condition_pattern_exit = rise_condition & dataframe['pattern_exit_signal']
        
        # 支撑位附近 + 上涨趋势
        near_support = (
            (dataframe['shape_support'].notna()) &
            (dataframe['dist_to_support'] >= 0) &
            (dataframe['dist_to_support'] <= self.entry_near_support_pct.value)
        )
        
        uptrend = (dataframe['last_segment_line'] == 'up')
        
        condition_support_exit = near_support & uptrend
        
        # 平空仓条件
        base_exit_condition = condition_drop_exit | condition_pattern_exit
        exit_short_condition = (base_exit_condition & condition_support_exit) | (base_exit_condition & uptrend)
        
        dataframe.loc[exit_short_condition, 'exit_short'] = 1
        
        # 设置平空仓标签
        drop_from_high = (dataframe['max_90'] - dataframe['close']) / dataframe['max_90']
        
        dataframe.loc[condition_drop_exit & condition_support_exit & (dataframe['exit_tag'] == ''), 'exit_tag'] = (
            '支撑位平空:跌' + (drop_from_high * 100).round(1).astype(str) + '%'
        )
        
        dataframe.loc[condition_pattern_exit & condition_support_exit & (dataframe['exit_tag'] == ''), 'exit_tag'] = '反转+支撑平空'
        
        dataframe.loc[condition_drop_exit & condition_pattern_exit & condition_support_exit & (dataframe['exit_tag'] == ''), 'exit_tag'] = (
            '跌' + (drop_from_high * 100).round(1).astype(str) + '%+反转+支撑平空'
        )
        
        # 统计信号
        exit_long_count = exit_long_condition.sum()
        exit_short_count = exit_short_condition.sum()
        if exit_long_count > 0 or exit_short_count > 0:
            logger.info(f"[{metadata['pair']}] 生成 {exit_long_count} 个平多信号, {exit_short_count} 个平空信号")
        
        return dataframe
    
    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float, **kwargs) -> Optional[float]:
        """
        动态止损：
        - 多仓：当价格低于支撑价格X%时触发止损
        - 空仓：当价格高于压力价格X%时触发止损
        """
        if not self.enable_dynamic_stoploss:
            return None
        
        # 获取当前dataframe
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe is None or len(dataframe) == 0:
            return None
        
        last_row = dataframe.iloc[-1]
        
        # 根据仓位方向选择止损逻辑
        if trade.is_short:
            # 空仓止损：价格高于压力价格X%时触发
            resistance_price = last_row.get('shape_resistance', np.nan)
            
            if pd.isna(resistance_price) or resistance_price <= 0:
                return None
            
            # 止损触发价格：压力价格 * (1 - dynamic_stoploss_pct)
            # 例如：dynamic_stoploss_pct = -0.005，则止损价为压力价的100.5%
            stoploss_price = resistance_price * (1 - self.dynamic_stoploss_pct.value)
            
            # 如果当前价格高于止损价格，触发止损
            if current_rate > stoploss_price:
                logger.info(f"[动态止损-空仓] {pair} 当前价{current_rate:.2f} > 止损价{stoploss_price:.2f} (压力{resistance_price:.2f})")
                return 0.01  # 立即平仓
        else:
            # 多仓止损：价格低于支撑价格X%时触发
            support_price = last_row.get('last_segment_min', np.nan)
            
            if pd.isna(support_price) or support_price <= 0:
                return None
            
            # 止损触发价格：支撑价格 * (1 + dynamic_stoploss_pct)
            stoploss_price = support_price * (1 + self.dynamic_stoploss_pct.value)
            
            # 如果当前价格低于止损价格，触发止损
            if current_rate < stoploss_price:
                logger.info(f"[动态止损-多仓] {pair} 当前价{current_rate:.2f} < 止损价{stoploss_price:.2f} (支撑{support_price:.2f})")
                return 0.01  # 立即平仓
        
        return None
    
    def confirm_trade_entry(self, pair: str, order_type: str, amount: float,
                           rate: float, time_in_force: str, current_time: datetime,
                           entry_tag: Optional[str], side: str, **kwargs) -> bool:
        """
        确认是否开仓：检查当前持仓数量是否超过限制
        单向持仓：同一时间只持有一个方向
        """
        # 获取当前开放交易数量
        open_trades = Trade.get_trades_proxy(is_open=True)
        open_count = len([t for t in open_trades])
        
        if open_count >= self.max_open_trades:
            logger.info(f"[开仓拒绝] {pair} 当前持仓{open_count}个，已达上限{self.max_open_trades}")
            return False
        
        # 检查是否已有该交易对的持仓（单向持仓）
        pair_trades = [t for t in open_trades if t.pair == pair]
        if pair_trades:
            existing_trade = pair_trades[0]
            # 如果已有持仓且方向相反，允许开仓（会先平仓再开仓）
            if existing_trade.is_short != (side == 'short'):
                logger.info(f"[开仓确认] {pair} 已有{'空仓' if existing_trade.is_short else '多仓'}，将平仓后开{'空仓' if side == 'short' else '多仓'}")
                return True
            else:
                logger.info(f"[开仓拒绝] {pair} 已有同方向持仓")
                return False
        
        logger.info(f"[开仓确认] {pair} 当前持仓{open_count}个，允许开仓")
        return True
    
    def bot_loop_start(self, current_time: datetime, **kwargs) -> None:
        """
        每个循环开始时执行（每分钟）
        用于实时监控和动态止损
        """
        if not self.dp:
            return
        
        pairs = self.dp.current_whitelist()
        if not pairs:
            return
        
        for pair in pairs:
            try:
                dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
                if dataframe is None or len(dataframe) == 0:
                    continue
                
                last_row = dataframe.iloc[-1]
                
                if self.enable_dynamic_stoploss:
                    support_price = last_row.get('last_segment_min', np.nan)
                    resistance_price = last_row.get('shape_resistance', np.nan)
                    current_rate = last_row['close']
                    
                    open_trades = Trade.get_trades_proxy(is_open=True, pair=pair)
                    for trade in open_trades:
                        if trade.is_short:
                            # 空仓止损检查
                            if not pd.isna(resistance_price) and resistance_price > 0:
                                stoploss_price = resistance_price * (1 - self.dynamic_stoploss_pct.value)
                                if current_rate > stoploss_price:
                                    logger.info(
                                        f"[动态止损触发-空仓] {pair} "
                                        f"当前价{current_rate:.2f} > 止损价{stoploss_price:.2f} "
                                        f"(压力{resistance_price:.2f})"
                                    )
                        else:
                            # 多仓止损检查
                            if not pd.isna(support_price) and support_price > 0:
                                stoploss_price = support_price * (1 + self.dynamic_stoploss_pct.value)
                                if current_rate < stoploss_price:
                                    logger.info(
                                        f"[动态止损触发-多仓] {pair} "
                                        f"当前价{current_rate:.2f} < 止损价{stoploss_price:.2f} "
                                        f"(支撑{support_price:.2f})"
                                    )
            
            except Exception as e:
                logger.error(f"bot_loop_start处理{pair}失败: {e}")
