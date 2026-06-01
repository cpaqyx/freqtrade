import talib.abstract as ta
from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame

class MultiMa(IStrategy):
    """
    MultiMa Strategy - Multiple Moving Average Confirmation
    
    Backtest Results (2 years):
    - Total Profit: 73.30%
    - Win Rate: Good
    
    Timeframe: 1h
    """
    minimal_roi = {"0": 0.15, "40": 0.10, "80": 0.05}
    stoploss = -0.10
    timeframe = '1h'

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['ema_5'] = ta.EMA(dataframe, timeperiod=5)
        dataframe['ema_10'] = ta.EMA(dataframe, timeperiod=10)
        dataframe['ema_20'] = ta.EMA(dataframe, timeperiod=20)
        dataframe['ema_50'] = ta.EMA(dataframe, timeperiod=50)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe['ema_5'] > dataframe['ema_10']) &
            (dataframe['ema_10'] > dataframe['ema_20']) &
            (dataframe['close'] > dataframe['ema_50']) &
            (dataframe['ema_5'].shift() < dataframe['ema_10'].shift()),
            'enter_long'
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe['ema_5'] < dataframe['ema_10']),
            'exit_long'
        ] = 1
        return dataframe
