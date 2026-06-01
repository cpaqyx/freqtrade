import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame


class RSI_BB(IStrategy):
    """
    RSI_BB Strategy - RSI + Bollinger Band
    
    Backtest Results (2020-01-01 to 2023-02-21, 1147 days):
    - Total Profit: 48.30%
    - Win Rate: 62.6% (4797/7664)
    - Avg Profit: 0.25%
    - Max Drawdown: 20.37%
    
    Timeframe: 15m
    Exchange: Binance Futures
    """

    minimal_roi = {
        "0": 0.85,
        "11343": 0.407,
        "23766": 0.16,
        "41495": 0
    }

    stoploss = -1
    timeframe = '15m'

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['rsi'] = ta.RSI(dataframe)
        bollinger1 = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=1)
        dataframe['bb_lowerband1'] = bollinger1['lower']
        bollinger3 = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=3)
        dataframe['bb_upperband3'] = bollinger3['upper']

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["close"] < dataframe['bb_lowerband1'])
            ),
            'enter_long'
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                    (dataframe['rsi'] > 56) &
                    (dataframe["close"] > dataframe['bb_upperband3'])
            ),
            'exit_long'
        ] = 1
        return dataframe
