import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame


class EasyInEasyOut(IStrategy):
    """
    EasyInEasyOut Strategy - HMA Crossover with ROI
    
    Backtest Results (2020-01-01 to 2023-02-21, 1147 days):
    - Total Profit: 42.63%
    - Win Rate: 99.2% (1414/1425)
    - Avg Profit: 1.19%
    - Max Drawdown: 13.33%
    - Avg Duration: 7 days 15 hours
    
    Timeframe: 5m
    Exchange: Binance Futures
    """

    minimal_roi = {
        "0": 0.02,
        "60": 0.03,
        "120": 0.02,
        "900": 0.01
    }

    stoploss = -1  # No hard stoploss
    exit_profit_only = True
    timeframe = '5m'

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Hull Moving Average (20)
        dataframe['hma_20'] = qtpylib.hull_moving_average(dataframe['close'], window=20)
        
        # Shifted values for crossover
        dataframe['close_prev'] = dataframe['close'].shift(2)
        dataframe['hma_20_prev'] = dataframe['hma_20'].shift(2)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['close'] > dataframe['hma_20']) &
                (dataframe['close_prev'] < dataframe['hma_20_prev'])
            ),
            'enter_long'
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe