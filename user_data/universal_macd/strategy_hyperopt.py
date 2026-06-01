import talib.abstract as ta
from freqtrade.strategy.interface import IStrategy
from freqtrade.strategy import IntParameter, DecimalParameter
from pandas import DataFrame

class UniversalMACD(IStrategy):
    """
    UniversalMACD Strategy with HyperOpt Parameters
    
    Backtest Results (original):
    - Total Profit: 92.90%
    - Sharpe: 8.59
    
    Timeframe: 1h
    """
    minimal_roi = {"0": 0.20, "30": 0.10, "60": 0.05, "120": 0.02}
    stoploss = -0.10
    timeframe = '1h'

    # HyperOpt parameters
    buy_macd_fast = IntParameter(5, 20, default=12)
    buy_macd_slow = IntParameter(20, 40, default=26)
    buy_macd_signal = IntParameter(5, 15, default=9)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        macd = ta.MACD(dataframe, 
                       fastperiod=self.buy_macd_fast.value,
                       slowperiod=self.buy_macd_slow.value,
                       signalperiod=self.buy_macd_signal.value)
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