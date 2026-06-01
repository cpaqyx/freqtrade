import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy.interface import IStrategy
from freqtrade.strategy import IntParameter, DecimalParameter
from pandas import DataFrame

class RSI_BB(IStrategy):
    """
    RSI_BB Strategy with HyperOpt Parameters
    
    Original Results:
    - Win Rate: 69.9%
    - Sharpe: 3.64
    
    Timeframe: 15m
    """
    stoploss = -1
    timeframe = '15m'

    # HyperOpt parameters
    buy_rsi_threshold = IntParameter(20, 40, default=30)
    buy_bb_period = IntParameter(15, 25, default=20)
    buy_bb_std = DecimalParameter(0.5, 2.5, default=1.0)
    
    exit_rsi_threshold = IntParameter(50, 70, default=56)
    exit_bb_std = DecimalParameter(2.0, 4.0, default=3.0)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        bollinger1 = qtpylib.bollinger_bands(
            qtpylib.typical_price(dataframe), 
            window=self.buy_bb_period.value, 
            stds=self.buy_bb_std.value
        )
        dataframe['bb_lowerband'] = bollinger1['lower']
        
        bollinger3 = qtpylib.bollinger_bands(
            qtpylib.typical_price(dataframe), 
            window=self.buy_bb_period.value, 
            stds=self.exit_bb_std.value
        )
        dataframe['bb_upperband'] = bollinger3['upper']

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["close"] < dataframe['bb_lowerband']),
            'enter_long'
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe['rsi'] > self.exit_rsi_threshold.value) &
            (dataframe["close"] > dataframe['bb_upperband']),
            'exit_long'
        ] = 1
        return dataframe