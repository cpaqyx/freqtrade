import freqtrade.vendor.qtpylib.indicators as qtpylib
import talib.abstract as ta
from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame


class CCI_BB(IStrategy):
    """
    CCI_BB Strategy - CCI + Bollinger Band
    
    Backtest Results (2020-01-01 to 2023-02-21, 1147 days):
    - Total Profit: 57.39%
    - Win Rate: 99.3% (1506/1517)
    - Avg Profit: 1.51%
    - Max Drawdown: 11.98%
    - Avg Duration: 7 days
    
    Timeframe: 5m
    Exchange: Binance Futures
    """

    minimal_roi = {
        "0": 0.02,
        "60": 0.04,
        "120": 0.02,
    }

    stoploss = -1  # No hard stoploss
    timeframe = '5m'
    exit_profit_only = False

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # CCI
        dataframe['cci'] = ta.CCI(dataframe)
        
        # Bollinger Bands (20, 2)
        bollinger1 = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe['bb_lowerband'] = bollinger1['lower']
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['cci'] <= -134) &
                (dataframe["close"] < dataframe['bb_lowerband'])
            ),
            'enter_long'
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Exit via ROI only
        return dataframe
