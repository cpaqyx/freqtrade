"""
BTC Rebound Volume Strategy for Freqtrade
==========================================

策略逻辑：
1. 监控整数价格关口（可配置：65000, 64000, ..., 55000）
2. 当价格向下突破关口时，记录该关口为"活跃关口"，并跟踪最低价
3. 当价格向上反弹突破关口，且满足以下条件时做多：
   - 反弹幅度 >= 5%（从最低价计算）或 价格 >= 关口 + 1%
   - 最近1小时成交量 > 24小时平均成交量 * 1.1
4. 固定20x杠杆，每次使用20%可用资金

适用场景：BTCUSDT 永续合约（futures）
Timeframe: 1m（使用 resample 计算小时级别指标）

Author: OpenClaw AI
Date: 2026-06-03
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from pandas import DataFrame
from freqtrade.strategy import (
    IStrategy,
    IntParameter,
    DecimalParameter,
    CategoricalParameter,
    merge_informative_pair,
)
from freqtrade.persistence import Trade

logger = logging.getLogger(__name__)


class BTC_Rebound_Volume_Strategy(IStrategy):
    """
    BTC 反弹成交量策略
    
    核心逻辑：
    - 监控整数关口，突破后跟踪最低价
    - 反弹确认 + 成交量放大时入场
    - 适合 futures 市场，固定杠杆
    """
    
    # ==================== 策略基础配置 ====================
    INTERFACE_VERSION = 3
    
    # 时间框架：使用1m运行，但会在内部resample计算小时指标
    timeframe = '1m'
    
    # 启动需要的K线数量（需要足够计算24小时成交量）
    startup_candle_count = 1500  # 1500分钟 ≈ 25小时
    
    # 使用自定义卖出逻辑
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    
    # 订单类型
    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'emergency_exit': 'market',
        'force_entry': 'market',
        'force_exit': 'market',
        'stoploss': 'market',
        'stoploss_on_exchange': False,
    }
    
    # 订单超时
    order_time_in_force = {
        'entry': 'GTC',
        'exit': 'GTC',
    }
    
    # ==================== 可配置参数 ====================
    
    # 整数关口列表（动态计算，覆盖价格范围的1000整数倍关口）
    # 在 populate_indicators 中会根据当前价格动态计算
    # 此处定义关口步长
    level_step = 1000  # 每1000一个关口
    
    # 反弹幅度阈值（从最低价计算的百分比）- 扩大范围
    rebound_min_pct = DecimalParameter(
        0.01, 0.20, default=0.05, decimals=3,
        space='buy', optimize=True,
        load=True
    )
    
    # 关口缓冲百分比（价格需要高于关口多少才算突破）- 扩大范围
    level_buffer_pct = DecimalParameter(
        0.001, 0.05, default=0.01, decimals=3,
        space='buy', optimize=True,
        load=True
    )
    
    # 成交量确认：观察窗口（小时）- 扩大范围
    vol_lookback_hours = IntParameter(
        6, 72, default=24,
        space='buy', optimize=True,
        load=True
    )
    
    # 成交量确认：计算窗口（小时）- 扩大范围
    vol_confirm_hours = IntParameter(
        1, 8, default=1,
        space='buy', optimize=True,
        load=True
    )
    
    # 成交量放大倍数 - 扩大范围
    vol_increase_pct = DecimalParameter(
        0.01, 0.50, default=0.10, decimals=2,
        space='buy', optimize=True,
        load=True
    )
    
    # 固定止损（freqtrade要求的属性）- 扩大范围
    stoploss = -0.08  # 8%止损
    
    # 止损百分比（可优化参数）- 扩大范围
    stoploss_pct = DecimalParameter(
        -0.25, -0.02, default=-0.08, decimals=3,
        space='sell', optimize=True,
        load=True
    )
    
    # 止盈ROI（可配置，格式：{时间(分钟): 利润率}）
    minimal_roi = {
        "0": 0.15,    # 立即：15%利润
        "60": 0.10,   # 1小时后：10%利润
        "120": 0.05,  # 2小时后：5%利润
        "240": 0.03   # 4小时后：3%利润
    }
    
    # 追踪止损配置
    trailing_stop = True
    trailing_stop_positive = 0.02      # 盈利2%后启动追踪止损
    trailing_stop_positive_offset = 0.03  # 价格回撤3%触发止损
    trailing_only_offset_is_reached = True
    
    # 杠杆倍数
    leverage_value = 20
    
    # 每次交易使用的资金比例
    stake_ratio = 0.20  # 20% of available balance
    
    # ==================== 状态管理 ====================
    # 使用类变量跟踪状态（每个交易对独立）
    # 注意：dry-run 和 live 都会正确维护这些状态
    
    # 活跃关口 {pair: level}
    active_levels: Dict[str, Optional[float]] = {}
    
    # 最低价跟踪 {pair: low_price}
    tracked_lows: Dict[str, Optional[float]] = {}
    
    # 关口突破时间 {pair: datetime}
    breakout_times: Dict[str, Optional[datetime]] = {}
    
    # ==================== 生命周期钩子 ====================
    
    def bot_start(self, **kwargs) -> None:
        """
        机器人启动时初始化状态
        """
        logger.info("=" * 60)
        logger.info("BTC Rebound Volume Strategy Started")
        logger.info(f"Level Step: {self.level_step} (dynamic price levels)")
        logger.info(f"Rebound Min %: {self.rebound_min_pct.value}")
        logger.info(f"Level Buffer %: {self.level_buffer_pct.value}")
        logger.info(f"Volume Lookback: {self.vol_lookback_hours.value} hours")
        logger.info(f"Volume Confirm: {self.vol_confirm_hours.value} hours")
        logger.info(f"Volume Increase: {self.vol_increase_pct.value * 100}%")
        logger.info(f"Stoploss: {self.stoploss_pct.value * 100}%")
        logger.info(f"Leverage: {self.leverage_value}x")
        logger.info(f"Stake Ratio: {self.stake_ratio * 100}%")
        logger.info("=" * 60)
    
    def bot_loop_start(self, current_time: datetime, **kwargs) -> None:
        """
        每个循环开始时调用（可用于状态清理）
        """
        pass
    
    # ==================== 杠杆和仓位管理 ====================
    
    def leverage(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_leverage: float,
        max_leverage: float,
        entry_tag: Optional[str],
        side: str,
        **kwargs
    ) -> float:
        """
        固定杠杆设置
        
        Args:
            pair: 交易对
            current_time: 当前时间
            current_rate: 当前价格
            proposed_leverage: 建议杠杆
            max_leverage: 最大允许杠杆
            entry_tag: 入场标签
            side: 交易方向 ('long' or 'short')
            
        Returns:
            实际使用的杠杆倍数
        """
        # 如果最大杠杆小于我们需要的杠杆，使用最大杠杆
        if max_leverage < self.leverage_value:
            logger.warning(f"{pair}: Max leverage {max_leverage} < requested {self.leverage_value}")
            return max_leverage
        
        return self.leverage_value
    
    def custom_stake_amount(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_stake: float,
        min_stake: Optional[float],
        max_stake: float,
        leverage: float,
        entry_tag: Optional[str],
        side: str,
        **kwargs
    ) -> float:
        """
        自定义仓位大小：使用可用资金的20%
        
        Args:
            pair: 交易对
            current_time: 当前时间
            current_rate: 当前价格
            proposed_stake: 建议仓位
            min_stake: 最小仓位
            max_stake: 最大仓位
            leverage: 杠杆倍数
            entry_tag: 入场标签
            side: 交易方向
            
        Returns:
            实际使用的仓位金额
        """
        # 计算期望仓位
        desired_stake = proposed_stake * self.stake_ratio
        
        # 确保不超过最大仓位
        if max_stake is not None:
            desired_stake = min(desired_stake, max_stake)
        
        # 确保不低于最小仓位
        if min_stake is not None:
            desired_stake = max(desired_stake, min_stake)
        
        logger.info(f"{pair}: Custom stake = {desired_stake:.2f} USDT (proposed: {proposed_stake:.2f})")
        
        return desired_stake
    
    # ==================== 止损管理 ====================
    
    def custom_stoploss(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        after_fill: bool,
        **kwargs
    ) -> Optional[float]:
        """
        自定义止损逻辑
        
        Returns:
            止损比例（负数）或 None 使用默认
        """
        # 使用可配置的止损参数
        return self.stoploss_pct.value
    
    # ==================== 指标计算 ====================
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        计算所有需要的指标
        
        Args:
            dataframe: OHLCV数据
            metadata: 元数据（包含pair等信息）
            
        Returns:
            添加了指标列的 dataframe
        """
        pair = metadata['pair']
        
        # ========== 1. Resample 计算小时级别成交量 ==========
        # 将1m数据resample为1h
        dataframe = self.resample_to_hourly(dataframe)
        
        # ========== 2. 计算成交量指标 ==========
        # 24小时平均每小时成交量
        vol_lookback = int(self.vol_lookback_hours.value)
        dataframe['volume_mean_24h'] = dataframe['volume_1h'].rolling(
            window=vol_lookback, min_periods=12
        ).mean()
        
        # 最近1小时成交量
        dataframe['volume_recent'] = dataframe['volume_1h']
        
        # 成交量放大比例
        dataframe['volume_ratio'] = (
            dataframe['volume_recent'] / dataframe['volume_mean_24h']
        ).fillna(1.0)
        
        # ========== 3. 价格关口逻辑 ==========
        # 找出当前价格所在的关口区间
        dataframe['active_level'] = self.find_active_level(dataframe)
        
        # 跟踪最低价（从突破关口开始）
        dataframe = self.track_low_since_breakout(dataframe, pair)
        
        # ========== 4. 入场信号计算 ==========
        dataframe = self.calculate_entry_signals(dataframe, pair)
        
        # ========== 5. 出场信号计算 ==========
        dataframe = self.calculate_exit_signals(dataframe, pair)
        
        return dataframe
    
    def resample_to_hourly(self, dataframe: DataFrame) -> DataFrame:
        """
        将1m数据resample为1h，用于计算小时级别成交量
        
        Args:
            dataframe: 1m OHLCV数据
            
        Returns:
            添加了 resampled 列的 dataframe
        """
        # 确保 date 列存在
        if 'date' not in dataframe.columns:
            dataframe['date'] = pd.to_datetime(dataframe.index)
        
        # 设置 date 为索引
        df = dataframe.copy()
        df.set_index('date', inplace=True)
        
        # Resample 到 1h
        hourly = df.resample('1h').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })
        
        # 重命名列以避免冲突
        hourly.columns = [f'{col}_1h' for col in hourly.columns]
        
        # 向前填充，使每分钟都能访问到当前小时的聚合数据
        # 注意：这里使用 'ffill' 会填充整个小时，包括开始时
        hourly_expanded = hourly.reindex(df.index, method='ffill')
        
        # 合并回原始 dataframe
        for col in hourly_expanded.columns:
            dataframe[col] = hourly_expanded[col].values
        
        return dataframe
    
    def find_active_level(self, dataframe: DataFrame) -> pd.Series:
        """
        找出每个时间点的活跃关口（价格刚跌破的关口）
        
        逻辑：
        - 动态计算价格范围内的1000整数倍关口
        - 如果 close < level，说明已经跌破该关口
        - 活跃关口是最大的那个被跌破的关口
        
        Args:
            dataframe: OHLCV数据
            
        Returns:
            活跃关口序列
        """
        close = dataframe['close']
        
        # 动态计算价格范围内的关口（1000整数倍）
        price_min = close.min()
        price_max = close.max()
        
        # 计算关口范围（向下取整到最近的1000，向上取整到最近的1000）
        level_min = int(price_min // self.level_step) * self.level_step
        level_max = int(price_max // self.level_step + 1) * self.level_step
        
        # 生成关口列表
        levels = list(range(level_max, level_min - self.level_step, -self.level_step))
        
        # 初始化为 NaN
        active_level = pd.Series(np.nan, index=dataframe.index)
        
        # 对于每个关口，检查是否被跌破
        for level in sorted(levels, reverse=True):  # 从高到低
            # 如果价格低于关口，且当前没有活跃关口（或更低）
            mask = (close < level) & (active_level.isna() | (active_level > level))
            active_level = active_level.mask(mask, level)
        
        return active_level
    
    def track_low_since_breakout(self, dataframe: DataFrame, pair: str) -> DataFrame:
        """
        跟踪从关口突破以来的最低价
        
        Args:
            dataframe: OHLCV数据
            pair: 交易对
            
        Returns:
            添加了 tracked_low 列的 dataframe
        """
        # 初始化
        dataframe['tracked_low'] = np.nan
        dataframe['breakout_occurred'] = False
        
        active_level = dataframe['active_level']
        close = dataframe['close']
        low = dataframe['low']
        
        # 跟踪状态
        current_level = None
        current_low = None
        
        tracked_lows = []
        breakouts = []
        
        for i in range(len(dataframe)):
            row_level = active_level.iloc[i]
            row_close = close.iloc[i]
            row_low = low.iloc[i]
            
            # 如果有活跃关口（价格跌破某个关口）
            if pd.notna(row_level):
                # 如果是新的关口（更低的关口），重置最低价跟踪
                if current_level is None or row_level != current_level:
                    # 检查是否是更低的关口（价格继续下跌）
                    if current_level is None or row_level < current_level:
                        current_level = row_level
                        current_low = row_low
                    else:
                        # 价格回升到更高的关口，保持原有关口
                        pass
                else:
                    # 同一个关口，更新最低价
                    if current_low is None or row_low < current_low:
                        current_low = row_low
                
                tracked_lows.append(current_low)
                breakouts.append(False)
            else:
                # 没有活跃关口（价格高于所有监控关口）
                current_level = None
                current_low = None
                tracked_lows.append(np.nan)
                breakouts.append(False)
        
        dataframe['tracked_low'] = tracked_lows
        dataframe['breakout_occurred'] = breakouts
        
        return dataframe
    
    def calculate_entry_signals(self, dataframe: DataFrame, pair: str) -> DataFrame:
        """
        计算入场信号
        
        条件：
        1. 价格向上突破关口（close > level）
        2. 反弹幅度 >= rebound_min_pct 或 价格 >= level * (1 + level_buffer_pct)
        3. 成交量放大：最近1h成交量 >= 24h平均 * (1 + vol_increase_pct)
        
        Args:
            dataframe: OHLCV数据
            pair: 交易对
            
        Returns:
            添加了入场信号列的 dataframe
        """
        # 初始化信号列
        dataframe['enter_long'] = 0
        dataframe['enter_tag'] = ''
        
        close = dataframe['close']
        active_level = dataframe['active_level']
        tracked_low = dataframe['tracked_low']
        volume_ratio = dataframe['volume_ratio']
        
        # 条件1：价格向上突破关口
        # 注意：active_level 是 NaN 表示价格已经回到关口之上
        # 我们需要检测：之前有 active_level，现在变成了 NaN（或更高的 level）
        
        # 重新计算：检查价格是否刚刚回到关口之上
        # 逻辑：前一个时刻有 active_level，当前时刻 price > level
        level_breakout = pd.Series(False, index=dataframe.index)
        
        for i in range(1, len(dataframe)):
            prev_level = active_level.iloc[i - 1]
            curr_close = close.iloc[i]
            
            # 如果之前有活跃关口，且现在价格回到该关口之上
            if pd.notna(prev_level) and curr_close > prev_level:
                level_breakout.iloc[i] = True
        
        # 条件2：反弹幅度
        # (a) 从最低价反弹超过 rebound_min_pct
        rebound_from_low = pd.Series(False, index=dataframe.index)
        if tracked_low.notna().any():
            rebound_from_low = (close - tracked_low) / tracked_low >= self.rebound_min_pct.value
        
        # (b) 价格高于关口 + buffer
        # 由于 active_level 已经是 NaN，我们需要用之前的 level
        level_with_buffer = pd.Series(np.nan, index=dataframe.index)
        for i in range(1, len(dataframe)):
            prev_level = active_level.iloc[i - 1]
            if pd.notna(prev_level):
                level_with_buffer.iloc[i] = prev_level * (1 + self.level_buffer_pct.value)
        
        price_above_buffer = close > level_with_buffer
        
        # 反弹条件满足
        rebound_satisfied = rebound_from_low | price_above_buffer.fillna(False)
        
        # 条件3：成交量放大
        volume_satisfied = volume_ratio >= (1 + self.vol_increase_pct.value)
        
        # 综合入场信号
        enter_condition = level_breakout & rebound_satisfied & volume_satisfied
        
        dataframe.loc[enter_condition, 'enter_long'] = 1
        
        # 生成入场标签
        for i in range(len(dataframe)):
            if enter_condition.iloc[i]:
                tags = []
                if rebound_from_low.iloc[i]:
                    tags.append(f"rebound_{int(self.rebound_min_pct.value * 100)}pct")
                if price_above_buffer.iloc[i]:
                    tags.append(f"level_buffer_{int(self.level_buffer_pct.value * 100)}pct")
                if volume_satisfied.iloc[i]:
                    tags.append("vol_confirmed")
                
                dataframe.loc[dataframe.index[i], 'enter_tag'] = "_".join(tags) if tags else "rebound_entry"
        
        return dataframe
    
    def calculate_exit_signals(self, dataframe: DataFrame, pair: str) -> DataFrame:
        """
        计算出场信号
        
        Args:
            dataframe: OHLCV数据
            pair: 交易对
            
        Returns:
            添加了出场信号列的 dataframe
        """
        # 目前不使用主动出场信号，依靠 ROI 和 stoploss
        dataframe['exit_long'] = 0
        dataframe['exit_tag'] = ''
        
        return dataframe
    
    # ==================== 入场/出场逻辑 ====================
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        入场趋势（已在 populate_indicators 中计算）
        """
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        出场趋势（已在 populate_indicators 中计算）
        """
        return dataframe
    
    # ==================== 自定义确认逻辑 ====================
    
    def confirm_trade_entry(
        self,
        pair: str,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        current_time: datetime,
        entry_tag: Optional[str],
        side: str,
        **kwargs
    ) -> bool:
        """
        入场确认（可用于额外的风险控制）
        
        Returns:
            True 允许入场，False 拒绝入场
        """
        logger.info(
            f"Confirming entry: {pair} | {side} | Amount: {amount:.6f} | "
            f"Rate: {rate:.2f} | Tag: {entry_tag}"
        )
        
        # 可以在这里添加额外的确认逻辑
        # 例如：检查是否有未平仓的交易、检查市场状态等
        
        return True
    
    def confirm_trade_exit(
        self,
        pair: str,
        trade: Trade,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        exit_reason: str,
        current_time: datetime,
        **kwargs
    ) -> bool:
        """
        出场确认
        
        Returns:
            True 允许出场，False 拒绝出场
        """
        logger.info(
            f"Confirming exit: {pair} | Reason: {exit_reason} | "
            f"Profit: {trade.calc_profit_ratio(rate):.4f}"
        )
        
        return True
    
    # ==================== 辅助方法 ====================
    
    def custom_exit(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs
    ) -> Optional[str]:
        """
        自定义出场逻辑
        
        Returns:
            出场原因字符串或 None
        """
        # 示例：如果盈利超过某个阈值，考虑出场
        # 这里可以使用更复杂的逻辑
        
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()
        
        # 示例：如果成交量急剧萎缩，考虑出场
        if hasattr(last_candle, 'volume_ratio'):
            if last_candle['volume_ratio'] < 0.5:
                return 'volume_dry_up'
        
        return None
