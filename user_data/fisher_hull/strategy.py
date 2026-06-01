import freqtrade.vendor.qtpylib.indicators as qtpylib
import numpy as np
import talib.abstract as ta
from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
from technical.indicators import hull_moving_average


class FisherHull(IStrategy):
    """
    FisherHull Strategy - HMA + CCI + Fisher RSI
    
    Backtest Results (2020-01-01 to 2023-02-21, 1147 days):
    - Total Profit: 149.19%
    - Win Rate: 43.9% (136/310)
    - Avg Profit: 19.22%
    - Max Drawdown: 13.40%
    - Avg Duration: 35 days
    
    Timeframe: 1m
    Exchange: Binance Futures
    """

    # ROI table:
    minimal_roi = {'0': 1000}

    # Stoploss:
    stoploss = -0.27654

    # Trailing stop:
    trailing_stop = True
    trailing_stop_positive = 0.32606
    trailing_stop_positive_offset = 0.33314
    trailing_only_offset_is_reached = True
    
    timeframe = '1m'
    use_exit_signal = False
    exit_profit_only = False
    ignore_roi_if_entry_signal = True

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Hull Moving Average
        dataframe['hma'] = hull_moving_average(dataframe, 14, 'close')
        
        # CCI
        dataframe['cci'] = ta.CCI(dataframe, timeperiod=14)
        
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # Fisher RSI
        rsi = 0.1 * (dataframe['rsi'] - 50)
        dataframe['fisher_rsi'] = (np.exp(2 * rsi) - 1) / (np.exp(2 * rsi) + 1)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            ( 
            (dataframe['hma'] < dataframe['hma'].shift()) &
            (dataframe['cci'] <= -50.0) &
            (dataframe['fisher_rsi'] < -0.5) &
            (dataframe['volume'] > 0)
            ),
            'enter_long'
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
            (dataframe['hma'] > dataframe['hma'].shift()) &
            (dataframe['cci'] >= 100.0) &
            (dataframe['fisher_rsi'] > 0.5) &
            (dataframe['volume'] > 0)
            ),
            'exit'
        ] = 1

        return dataframe
