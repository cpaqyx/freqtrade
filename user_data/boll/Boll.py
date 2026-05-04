# user_data/strategies/BollingerVolumeStrategy.py
import pandas as pd

from freqtrade.strategy import IStrategy, DecimalParameter, IntParameter
from pandas import DataFrame
import talib
import numpy as np

class Boll(IStrategy):
    INTERFACE_VERSION = 3

    # === 参数优化 ===
    bb_period = IntParameter(18, 22, default=20, space="buy")
    bb_std = DecimalParameter(1.9, 2.3, default=2.1, space="buy")
    volume_multiplier = DecimalParameter(1.6, 2.2, default=1.8, space="buy")  # 恢复 1.8
    atr_period = IntParameter(12, 16, default=14, space="sell")
    atr_multiplier = DecimalParameter(1.3, 1.8, default=1.5, space="sell")

    # ROI 表（强制分批止盈）
    minimal_roi = {
        "0": 0.08,   # 8% 立即卖 50%
        "240": 0.04, # 4小时后降到 4%
        "720": 0.00  # 12小时后允许小亏出
    }

    stoploss = -0.10  # 兜底 10%
    use_custom_stoploss = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    timeframe = '4h'
    can_short = False

    # === 指标 ===
    def populate_indicators(self, dataframe: DataFrame, metadata) -> DataFrame:
        # 布林带
        bollinger = talib.BBANDS(
            dataframe['close'],
            timeperiod=self.bb_period.value,
            nbdevup=self.bb_std.value,
            nbdevdn=self.bb_std.value
        )
        dataframe['bb_lower'] = bollinger[2]
        dataframe['bb_middle'] = bollinger[1]
        dataframe['bb_upper'] = bollinger[0]

        # 成交量均线
        dataframe['volume_ma'] = dataframe['volume'].rolling(self.bb_period.value).mean()

        # ATR
        dataframe['atr'] = talib.ATR(dataframe['high'], dataframe['low'], dataframe['close'], timeperiod=self.atr_period.value)

        # 50期EMA（趋势过滤）
        dataframe['ema50'] = talib.EMA(dataframe['close'], timeperiod=50)

        return dataframe

    # === 入场 ===
    def populate_entry_trend(self, dataframe: DataFrame, metadata) -> DataFrame:
        df = dataframe

        long_condition = (
            # 1. 触碰下轨 + 收盘站稳
            (df['low'] <= df['bb_lower']) &
            (df['close'] >= df['bb_lower']) &
            # 2. 放量（1.8倍）
            (df['volume'] >= df['volume_ma'] * self.volume_multiplier.value) &
            # 3. 趋势过滤：价格 > EMA50
            (df['close'] > df['ema50']) &
            # 4. 避免假破：收盘 > 开盘（阳线）
            (df['close'] > df['open'])
        )

        df.loc[long_condition, 'enter_long'] = 1
        return df

    # === 出场 ===
    def populate_exit_trend(self, dataframe: DataFrame, metadata) -> DataFrame:
        df = dataframe

        # 价格触及中轨 → 触发卖出信号
        exit_condition = (
            (df['close'] >= df['bb_middle'])
        )
        df.loc[exit_condition, 'exit_long'] = 1

        return df

    # === 动态止损 ===
    def custom_stoploss(self, pair: str, trade, current_time, current_rate, current_profit, **kwargs):
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe.empty:
            return -0.10  # 兜底

        last_candle = dataframe.iloc[-1]
        atr = last_candle['atr']
        if pd.isna(atr) or atr <= 0:
            return -0.10

        # ATR 动态止损
        atr_stop = trade.open_rate * (1 - self.atr_multiplier.value * atr / trade.open_rate)
        return max(atr_stop, trade.open_rate * 0.90)  # 不低于 10% 止损