"""
HighFreq5mStrategy - 5分钟高频交易策略
========================================

策略特点：
1. 支持多空双向交易（永续合约）
2. 综合多个指标：布林带、趋势（EMA/SuperTrend）、压力位支撑位、恐慌指数、连续K线
3. 所有参数可配置，适合hyperopt优化
4. 使用"信号投票机制"提高交易频率
5. 针对5分钟时间框架优化

作者：AI Assistant
版本：v1.0
日期：2025-10-24
"""

import sys
import os
from datetime import datetime
from typing import Optional
import logging

import numpy as np
import pandas as pd
from pandas import DataFrame
import talib.abstract as ta
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter, CategoricalParameter

# 添加路径以导入FGI提供者
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'panicIndex'))
from FGIDataProvider import FGIDataProvider

logger = logging.getLogger(__name__)


class HighFreq5mStrategy(IStrategy):
    """
    5分钟高频交易策略
    
    综合考虑：
    - 布林带（超买超卖）
    - 趋势（EMA交叉、SuperTrend）  
    - 压力位支撑位（历史高低点）
    - 恐慌指数（辅助）
    - 连续K线（动量）
    """
    
    # 策略版本
    INTERFACE_VERSION = 3
    
    # 支持做空
    can_short = True
    
    # 时间框架
    timeframe = '5m'
    
    # ROI（5分钟级别，更激进）
    minimal_roi = {
        "0": 0.025,    # 2.5% 立即目标
        "10": 0.018,   # 10根K线后（50分钟）降至1.8%
        "30": 0.012,   # 30根K线后（2.5小时）降至1.2%
        "60": 0.008    # 60根K线后（5小时）降至0.8%
    }
    
    # 止损
    stoploss = -0.03
    
    # 追踪止损
    trailing_stop = True
    trailing_stop_positive = 0.015
    trailing_stop_positive_offset = 0.025
    trailing_only_offset_is_reached = True
    
    # 资金管理
    position_adjustment_enable = False
    
    # ==================== 可优化参数 ====================
    
    # 1. 布林带参数
    bb_length = IntParameter(15, 40, default=20, space='buy', optimize=True)
    bb_std = DecimalParameter(1.5, 3.0, decimals=1, default=2.0, space='buy', optimize=True)
    bb_buy_threshold = DecimalParameter(0.0, 0.35, decimals=2, default=0.20, space='buy', optimize=True)
    bb_sell_threshold = DecimalParameter(0.65, 1.0, decimals=2, default=0.80, space='sell', optimize=True)
    
    # 2. EMA趋势参数
    ema_short = IntParameter(5, 20, default=9, space='buy', optimize=True)
    ema_medium = IntParameter(20, 50, default=21, space='buy', optimize=True)
    ema_long = IntParameter(50, 200, default=50, space='buy', optimize=True)
    
    # 3. SuperTrend参数
    supertrend_period = IntParameter(7, 14, default=10, space='buy', optimize=True)
    supertrend_multiplier = DecimalParameter(2.0, 4.0, decimals=1, default=3.0, space='buy', optimize=True)
    
    # 4. 压力位支撑位参数
    sr_lookback = IntParameter(20, 100, default=50, space='buy', optimize=True)
    sr_threshold = DecimalParameter(0.005, 0.020, decimals=3, default=0.010, space='buy', optimize=True)
    
    # 5. 连续K线参数
    consecutive_candles = IntParameter(2, 5, default=3, space='buy', optimize=True)
    
    # 6. 恐慌指数参数（辅助）
    fgi_extreme_fear = IntParameter(20, 35, default=25, space='buy', optimize=True)
    fgi_extreme_greed = IntParameter(65, 80, default=75, space='sell', optimize=True)
    use_fgi_filter = CategoricalParameter([True, False], default=False, space='buy', optimize=True)
    
    # 7. 信号投票机制
    min_long_signals = IntParameter(2, 4, default=2, space='buy', optimize=True)
    min_short_signals = IntParameter(2, 4, default=2, space='sell', optimize=True)
    
    # 8. 动态止损参数
    custom_stoploss_value = DecimalParameter(-0.05, -0.02, decimals=3, default=-0.03, space='sell', optimize=True)
    
    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self.config = config
        self.fgi_provider = None
        logger.info("HighFreq5mStrategy v1.0 - 5分钟高频策略初始化")
        logger.info("支持多空双向交易，综合布林带、趋势、SR、FGI、连续K线")
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        计算所有技术指标
        """
        # 延迟初始化FGI提供者（避免pickle问题）
        if self.fgi_provider is None:
            try:
                self.fgi_provider = FGIDataProvider(self.config)
                logger.info("FGI数据提供者初始化成功")
            except Exception as e:
                logger.warning(f"FGI数据提供者初始化失败: {e}，将不使用FGI指标")
                self.fgi_provider = None
        
        # ===== 1. 布林带 =====
        upper, middle, lower = ta.BBANDS(
            dataframe['close'],
            timeperiod=self.bb_length.value,
            nbdevup=self.bb_std.value,
            nbdevdn=self.bb_std.value
        )
        dataframe['bb_upper'] = upper
        dataframe['bb_middle'] = middle
        dataframe['bb_lower'] = lower
        
        # BB位置（0=下轨，0.5=中轨，1=上轨）
        dataframe['bb_position'] = (
            (dataframe['close'] - dataframe['bb_lower']) /
            (dataframe['bb_upper'] - dataframe['bb_lower'] + 1e-10)
        )
        
        # ===== 2. EMA趋势 =====
        dataframe['ema_short'] = ta.EMA(dataframe['close'], timeperiod=self.ema_short.value)
        dataframe['ema_medium'] = ta.EMA(dataframe['close'], timeperiod=self.ema_medium.value)
        dataframe['ema_long'] = ta.EMA(dataframe['close'], timeperiod=self.ema_long.value)
        
        # ===== 3. SuperTrend =====
        dataframe = self.calculate_supertrend(
            dataframe,
            period=self.supertrend_period.value,
            multiplier=self.supertrend_multiplier.value
        )
        
        # ===== 4. 压力位支撑位 =====
        dataframe['resistance'] = dataframe['high'].rolling(window=self.sr_lookback.value).max()
        dataframe['support'] = dataframe['low'].rolling(window=self.sr_lookback.value).min()
        
        # 距离SR的百分比
        dataframe['dist_to_resistance'] = (dataframe['resistance'] - dataframe['close']) / dataframe['close']
        dataframe['dist_to_support'] = (dataframe['close'] - dataframe['support']) / dataframe['close']
        
        # ===== 5. 连续K线 =====
        dataframe['consecutive_up'] = self.count_consecutive(dataframe, direction='up')
        dataframe['consecutive_down'] = self.count_consecutive(dataframe, direction='down')
        
        # ===== 6. 恐慌指数（如果可用） =====
        if self.fgi_provider is not None:
            try:
                dataframe['fgi'] = dataframe['date'].apply(
                    lambda x: self.fgi_provider.get_fgi_for_date(x) if pd.notna(x) else 50
                )
            except Exception as e:
                logger.warning(f"FGI计算失败: {e}，使用默认值50")
                dataframe['fgi'] = 50
        else:
            dataframe['fgi'] = 50
        
        # ===== 7. RSI（辅助） =====
        dataframe['rsi'] = ta.RSI(dataframe['close'], timeperiod=14)
        
        # ===== 8. 成交量 =====
        dataframe['volume_ma'] = dataframe['volume'].rolling(window=20).mean()
        dataframe['volume_ratio'] = dataframe['volume'] / (dataframe['volume_ma'] + 1e-10)
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        做多入场条件（信号投票机制）
        """
        # 初始化信号列
        dataframe['long_signal_count'] = 0
        dataframe['short_signal_count'] = 0
        
        # ===== 做多信号 =====
        
        # 信号1：BB超卖
        long_bb = dataframe['bb_position'] < self.bb_buy_threshold.value
        dataframe.loc[long_bb, 'long_signal_count'] += 1
        
        # 信号2：EMA多头排列
        long_ema = (
            (dataframe['ema_short'] > dataframe['ema_medium']) &
            (dataframe['ema_medium'] > dataframe['ema_long'])
        )
        dataframe.loc[long_ema, 'long_signal_count'] += 1
        
        # 信号3：SuperTrend看多
        long_supertrend = dataframe['supertrend_direction'] == 1
        dataframe.loc[long_supertrend, 'long_signal_count'] += 1
        
        # 信号4：接近支撑位
        long_support = dataframe['dist_to_support'] < self.sr_threshold.value
        dataframe.loc[long_support, 'long_signal_count'] += 1
        
        # 信号5：连续下跌后反弹
        long_consecutive = dataframe['consecutive_down'] >= self.consecutive_candles.value
        dataframe.loc[long_consecutive, 'long_signal_count'] += 1
        
        # 信号6：FGI极度恐慌（如果启用）
        if self.use_fgi_filter.value:
            long_fgi = dataframe['fgi'] < self.fgi_extreme_fear.value
            dataframe.loc[long_fgi, 'long_signal_count'] += 1
        
        # 信号7：RSI超卖
        long_rsi = dataframe['rsi'] < 35
        dataframe.loc[long_rsi, 'long_signal_count'] += 1
        
        # 做多条件：至少N个信号
        dataframe.loc[
            (dataframe['long_signal_count'] >= self.min_long_signals.value) &
            (dataframe['volume'] > 0),  # 确保有成交量
            'enter_long'
        ] = 1
        
        # ===== 做空信号 =====
        
        # 信号1：BB超买
        short_bb = dataframe['bb_position'] > self.bb_sell_threshold.value
        dataframe.loc[short_bb, 'short_signal_count'] += 1
        
        # 信号2：EMA空头排列
        short_ema = (
            (dataframe['ema_short'] < dataframe['ema_medium']) &
            (dataframe['ema_medium'] < dataframe['ema_long'])
        )
        dataframe.loc[short_ema, 'short_signal_count'] += 1
        
        # 信号3：SuperTrend看空
        short_supertrend = dataframe['supertrend_direction'] == -1
        dataframe.loc[short_supertrend, 'short_signal_count'] += 1
        
        # 信号4：接近压力位
        short_resistance = dataframe['dist_to_resistance'] < self.sr_threshold.value
        dataframe.loc[short_resistance, 'short_signal_count'] += 1
        
        # 信号5：连续上涨后回调
        short_consecutive = dataframe['consecutive_up'] >= self.consecutive_candles.value
        dataframe.loc[short_consecutive, 'short_signal_count'] += 1
        
        # 信号6：FGI极度贪婪（如果启用）
        if self.use_fgi_filter.value:
            short_fgi = dataframe['fgi'] > self.fgi_extreme_greed.value
            dataframe.loc[short_fgi, 'short_signal_count'] += 1
        
        # 信号7：RSI超买
        short_rsi = dataframe['rsi'] > 65
        dataframe.loc[short_rsi, 'short_signal_count'] += 1
        
        # 做空条件：至少N个信号
        dataframe.loc[
            (dataframe['short_signal_count'] >= self.min_short_signals.value) &
            (dataframe['volume'] > 0),
            'enter_short'
        ] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        平仓条件
        """
        # 做多平仓：BB回到上轨 或 趋势反转
        dataframe.loc[
            (
                (dataframe['bb_position'] > 0.7) |  # BB接近上轨
                (dataframe['supertrend_direction'] == -1) |  # SuperTrend转空
                (dataframe['ema_short'] < dataframe['ema_medium'])  # EMA死叉
            ) &
            (dataframe['volume'] > 0),
            'exit_long'
        ] = 1
        
        # 做空平仓：BB回到下轨 或 趋势反转
        dataframe.loc[
            (
                (dataframe['bb_position'] < 0.3) |  # BB接近下轨
                (dataframe['supertrend_direction'] == 1) |  # SuperTrend转多
                (dataframe['ema_short'] > dataframe['ema_medium'])  # EMA金叉
            ) &
            (dataframe['volume'] > 0),
            'exit_short'
        ] = 1
        
        return dataframe
    
    def custom_stoploss(self, pair: str, trade, current_time, current_rate,
                       current_profit: float, **kwargs) -> float:
        """
        动态止损
        """
        # 盈利时收紧止损
        if current_profit > 0.02:
            return -0.01  # 盈利2%后，止损收紧至-1%
        elif current_profit > 0.01:
            return -0.015  # 盈利1%后，止损收紧至-1.5%
        
        # 默认止损
        return self.custom_stoploss_value.value
    
    # ==================== 辅助函数 ====================
    
    def calculate_supertrend(self, dataframe: DataFrame, period: int, multiplier: float) -> DataFrame:
        """
        计算SuperTrend指标
        """
        # 计算ATR
        atr = ta.ATR(dataframe['high'], dataframe['low'], dataframe['close'], timeperiod=period)
        
        # 计算上下轨
        hl2 = (dataframe['high'] + dataframe['low']) / 2
        upperband = hl2 + (multiplier * atr)
        lowerband = hl2 - (multiplier * atr)
        
        # 初始化
        supertrend = pd.Series(index=dataframe.index, dtype=float)
        direction = pd.Series(index=dataframe.index, dtype=int)
        
        supertrend.iloc[0] = hl2.iloc[0]
        direction.iloc[0] = 1
        
        # 计算SuperTrend
        for i in range(1, len(dataframe)):
            if pd.isna(upperband.iloc[i]) or pd.isna(lowerband.iloc[i]):
                supertrend.iloc[i] = supertrend.iloc[i-1]
                direction.iloc[i] = direction.iloc[i-1]
                continue
            
            # 更新上下轨
            if dataframe['close'].iloc[i] > upperband.iloc[i-1]:
                direction.iloc[i] = 1
            elif dataframe['close'].iloc[i] < lowerband.iloc[i-1]:
                direction.iloc[i] = -1
            else:
                direction.iloc[i] = direction.iloc[i-1]
                
                if direction.iloc[i] == 1 and lowerband.iloc[i] < lowerband.iloc[i-1]:
                    lowerband.iloc[i] = lowerband.iloc[i-1]
                if direction.iloc[i] == -1 and upperband.iloc[i] > upperband.iloc[i-1]:
                    upperband.iloc[i] = upperband.iloc[i-1]
            
            # 设置SuperTrend值
            if direction.iloc[i] == 1:
                supertrend.iloc[i] = lowerband.iloc[i]
            else:
                supertrend.iloc[i] = upperband.iloc[i]
        
        dataframe['supertrend'] = supertrend
        dataframe['supertrend_direction'] = direction
        
        return dataframe
    
    def count_consecutive(self, dataframe: DataFrame, direction: str) -> pd.Series:
        """
        计算连续上涨或下跌的K线数量
        """
        if direction == 'up':
            condition = dataframe['close'] > dataframe['close'].shift(1)
        else:  # down
            condition = dataframe['close'] < dataframe['close'].shift(1)
        
        # 计算连续次数
        consecutive = pd.Series(0, index=dataframe.index)
        count = 0
        
        for i in range(len(dataframe)):
            if condition.iloc[i]:
                count += 1
            else:
                count = 0
            consecutive.iloc[i] = count
        
        return consecutive

