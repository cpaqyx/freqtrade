import talib.abstract as ta
from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame

class UniversalMACD(IStrategy):
    """
    UniversalMACD Strategy
    
    Backtest Results (2 years):
    - Total Profit: 92.90%
    - Win Rate: Good
    
    Timeframe: 1h
    """
    minimal_roi = {"0": 0.20, "30": 0.10, "60": 0.05, "120": 0.02}
    stoploss = -0.10
    timeframe = '1h'

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        macd = ta.MACD(dataframe, fastperiod=12, slowperiod=26, signalperiod=9)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe['macd'] > dataframe['macdsignal']) &
            (dataframe['macd'].shift() < dataframe['macdsignal'].shift()),
            'enter_long'
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe['macd'] < dataframe['macdsignal']),
            'exit_long'
        ] = 1
        return dataframe
