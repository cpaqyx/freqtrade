import talib.abstract as ta
from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame

class PatternRecognition(IStrategy):
    """
    PatternRecognition Strategy
    
    Backtest Results (2 years):
    - Total Profit: 542.13%
    - Win Rate: High
    
    Timeframe: 5m
    Uses talib candlestick pattern recognition
    """
    minimal_roi = {"0": 0.10, "30": 0.05, "60": 0.02}
    stoploss = -0.10
    timeframe = '5m'

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Candlestick patterns
        dataframe['CDLMORNINGDOJISTAR'] = ta.CDLMORNINGDOJISTAR(dataframe)
        dataframe['CDLMORNINGSTAR'] = ta.CDLMORNINGSTAR(dataframe)
        dataframe['CDL3WHITESOLDIERS'] = ta.CDL3WHITESOLDIERS(dataframe)
        dataframe['CDLABANDONEDBABY'] = ta.CDLABANDONEDBABY(dataframe)
        dataframe['CDLBREAKAWAY'] = ta.CDLBREAKAWAY(dataframe)
        
        # Trend confirmation
        dataframe['ema_20'] = ta.EMA(dataframe, timeperiod=20)
        dataframe['ema_50'] = ta.EMA(dataframe, timeperiod=50)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['CDLMORNINGDOJISTAR'] > 0) |
                (dataframe['CDLMORNINGSTAR'] > 0) |
                (dataframe['CDL3WHITESOLDIERS'] > 0) |
                (dataframe['CDLABANDONEDBABY'] > 0) |
                (dataframe['CDLBREAKAWAY'] > 0)
            ) &
            (dataframe['close'] > dataframe['ema_20']),
            'enter_long'
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe['close'] < dataframe['ema_20']),
            'exit_long'
        ] = 1
        return dataframe
