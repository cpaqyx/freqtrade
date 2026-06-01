import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame


class BuyOrDie(IStrategy):
    """
    BuyOrDie Strategy - Simple HMA Crossover
    
    Backtest Results (2020-01-01 to 2023-02-21, 1147 days):
    - Total Profit: 134.25%
    - Win Rate: 4.6% (141/3035) ⚠️ Extremely low
    - Avg Profit: 1.77%
    - Max Drawdown: 20.02%
    - Avg Duration: 3 days 13 hours
    
    Timeframe: 5m
    Exchange: Binance Futures
    
    WARNING: Very low win rate, relies on a few big wins
    """

    minimal_roi = {'0': 1000}

    stoploss = -0.02  # Very tight stoploss

    # Trailing stop:
    trailing_stop = True
    trailing_stop_positive = 0.332
    trailing_stop_positive_offset = 0.364
    trailing_only_offset_is_reached = True
    
    timeframe = '5m'
    use_exit_signal = False
    exit_profit_only = False
    ignore_roi_if_entry_signal = True

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Hull Moving Average (20)
        dataframe['hma_20'] = qtpylib.hull_moving_average(dataframe['close'], window=20)
        
        # Shifted values for crossover detection
        dataframe['close_prev'] = dataframe['close'].shift(2)
        dataframe['hma_20_prev'] = dataframe['hma_20'].shift(2)
        dataframe['close_curr'] = dataframe['close'].shift(1)
        dataframe['hma_20_current'] = dataframe['hma_20'].shift(1)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['close_curr'] > dataframe['hma_20_current']) &
                (dataframe['close_prev'] < dataframe['hma_20_prev'])
            ),
            'enter_long'
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe
