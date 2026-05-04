为了简单，投资资金全仓操作，即买入时全仓买入，卖出时全仓卖出，只征对btc永续合约，k线为天为单位分析，即建仓时全部金额建仓，平仓时全部持仓平仓，并且只做多和平多，不做空和平空，以适用于现货，编码写到freqtrade\user_data\btc 目录下。
策略详情如下：
计算指标：
（1）最近90根最高价；
（2）最近90根最低低；
（3）计算近90根的图形指标，该指标是一个json信息，已经实现，放到common/line_format.py中，调用kline_trend_description方法，传入参数为近90天所有k线收盘价,得到的是一个json数组，不用指标展示；json示例如下：
 [{'line': 'up', 'angle': 30.44, 'max_price': 24841.69, 'min_price': 23511.81, 'start_price': 24327.98, 'end_price': 24841.69, 'k_cnt': 5}, {'line': 'down', 'angle': -56.14, 'max_price': 24841.69, 'min_price': 20151.4, 'start_price': 24841.69, 'end_price': 20151.4, 'k_cnt': 18}, {'line': 'up', 'angle': 76.41, 'max_price': 28107.3, 'min_price': 20151.4, 'start_price': 20151.4, 'end_price': 28107.3, 'k_cnt': 11}, {'line': 'down', 'angle': -78.46, 'max_price': 28107.3, 'min_price': 27251.05, 'start_price': 28107.3, 'end_price': 27251.05, 'k_cnt': 1}, {'line': 'up', 'angle': 38.65, 'max_price': 30466.97, 'min_price': 27124.14, 'start_price': 27251.05, 'end_price': 30466.97, 'k_cnt': 23}]

建仓条件：
（1）如果当前价与最近90根最高价相比，跌了25%，则直接在每二根k线的开盘价建仓做多；
（2）当天涨幅为正，并且涨幅超过2%以上或者向前连续的几天都上涨，并且涨幅超过3%以上，则进一步分析当前的图形指标，如果图形指标数组中从最后的一个向前推，如果是以下情况，满足一个则建仓:
（2.1）最后1个的line值为up或者为flat; 倒数第二为down,并且这段下跌超过10%（用start_price、end_price计算跌幅）；
（2.2）最后1个的line值为up或者为flat; 倒数第二为flat或者为up但k线根数小于2,并且涨幅不超过5%；倒数第二为down,并且这段下跌超过10%（用start_price、end_price计算跌幅）；

平仓条件：
（1）当天涨幅为负，并且跌幅超过2%以上或者向前连续的几天都下跌，并且跌幅超过3%以上，则进一步分析当前的图形指标，如果图形指标数组中从最后的一个向前推，如果是以下情况，满足一个则平仓:
（1.1）最后1个的line值为down或者为flat; 倒数第二为up,获取该up的max_price, 再向前找到同样是up的max_price，如果两个max_price值相差2%以内，则平仓。


平仓条件：
（1.2）先找出近期的高点，要求

如果最后一个的line值为"up",则获取这段的max_price, 这里称为maxA, 但如果最后一个line的值为down或flat 倒数第二个为up, 获取该up的max_price, 再向前找到同样是up的max_price，如果两个max_price值相差2%以内，则平仓。

## 优化
BTCFullPosition.py 策略修改，平仓条件改为
（1）当天涨幅为负，并且跌幅超过2%以上或者向前连续的几天都下跌，并且跌幅超过3%以上，则进一步分析当前的图形指标，如果图形指标数组中从最后的一个向前推，如果是以下情况，满足一个则平仓:
(1.1)最后1个的line（或称段）值为up,获取最高价格A，并向前找到最近的一个同样是up的段，找到最高价B，如果A与B差异在2%（做成参数）以内，即双顶情况，则平仓；如果不成立，则再向前找到一下up段，得到段的最高价C，如果A与B差异在2%以内，也平仓；
(1.2)最后1段为down, 但跌幅的绝对值在5%以内，则向前找到一个up段，获取最高价格A，并向前找到最近的一个同样是up的段，找到最高价B，如果A与B差异在2%以内，即双顶情况，则平仓；如果不成立，则再向前找到一下up段，得到段的最高价C，如果A与B差异在2%以内，也平仓；

## 优化2
BTCFullPosition.py 策略修改，平仓条件改为
（1）当天涨幅为负，并且跌幅超过2%以上或者向前连续的几天都下跌，并且跌幅超过3%以上，则进一步分析当前的图形指标，如果图形指标数组中从最后的一个向前推，如果是以下情况，满足一个则平仓:
(1.1)最后1个的line（或称段）值为up,获取最高价格A，并向前找到最近的一个同样是up的段，找到最高价B，如果A比B高3%以内或A比B低5%以内（做成参数），即双顶情况，则平仓；如果不成立，则再向前找到一下up段，得到段的最高价C，如果A比C高3%以内或A比C低5%以内（做成参数），即双顶情况，则平仓；
(1.2)最后1段为down, 但跌幅的绝对值在5%以内，则向前找到一个up段，获取最高价格A，并向前找到最近的一个同样是up的段，找到最高价B，如果如果A比B高3%以内或A比B低5%以内（做成参数），即双顶情况，则平仓；如果不成立，则再向前找到一下up段，得到段的最高价C，如果A比C高3%以内或A比C低5%以内（做成参数），即双顶情况，则平仓；
由于上面的判断逻辑一样，写一个独立的方法做这些判断。

BTCFullPosition.py 中以阈值都做成参数，给出默认值用当前的赋值，并给出合并理的参数范围，以方便进行参数优化。



## 优化参数
生成BTCFullPosition.py 策略参数优化的命令文件.bat, 调用hyperopt，损失函数用 MultiMetricHyperOptLoss，优化sell、buy参数，迭代次数10000次。
其他参数参考backtest.bat

## 最佳参数
c:\users\administrator\.conda\envs\python312\python.exe .\freqtrade\main.py hyperopt-show --config ./user_data/btc/config.json --hyperopt-filename strategy_BTCFullPosition_2025-11-05_13-55-39.fthypt -n 4450

c:\users\administrator\.conda\envs\python312\python.exe .\freqtrade\main.py hyperopt-list   --config user_data/btc/config.json   --hyperopt-filename strategy_BTCFullPosition_2025-11-05_13-55-39.fthypt  --best  --min-trades 10 --no-color
#### 交易笔数多，48，收益81.7倍也大：
c:\users\administrator\.conda\envs\python312\python.exe .\freqtrade\main.py hyperopt-show --config ./user_data/btc/config.json --hyperopt-filename strategy_BTCFullPosition_2025-11-05_13-55-39.fthypt -n 552
    # Buy hyperspace params:
    buy_params = {
        "continuous_rise_threshold": 0.06,
        "day_rise_threshold": 0.01,
        "double_top_threshold": 0.1,
        "max_drop_from_high": 0.36,
        "pattern_drop_threshold": 0.07,
    }

    # Sell hyperspace params:
    sell_params = {
        "continuous_drop_threshold": 0.02,
        "day_drop_threshold": 0.02,
        "double_top_higher_threshold": 0.06,
        "double_top_lower_threshold": 0.05,
        "last_down_threshold": 0.07,
    }

    # ROI table:  # value loaded from strategy
    minimal_roi = {
        "0": 10.0
    }

    # Stoploss:
    stoploss = -0.99  # value loaded from strategy

    # Trailing stop:
    trailing_stop = False  # value loaded from strategy
    trailing_stop_positive = None  # value loaded from strategy
    trailing_stop_positive_offset = 0.0  # value loaded from strategy
    trailing_only_offset_is_reached = False  # value loaded from strategy

    # Max Open Trades:
    max_open_trades = 1  # value loaded from strategy

#### 最佳收益90倍，交易数量31
    # Buy hyperspace params:
    buy_params = {
        "continuous_rise_threshold": 0.06,
        "day_rise_threshold": 0.04,
        "double_top_threshold": 0.04,
        "max_drop_from_high": 0.35,
        "pattern_drop_threshold": 0.07,
    }

    # Sell hyperspace params:
    sell_params = {
        "continuous_drop_threshold": 0.02,
        "day_drop_threshold": 0.02,
        "double_top_higher_threshold": 0.05,
        "double_top_lower_threshold": 0.05,
        "last_down_threshold": 0.08,
    }

    # ROI table:  # value loaded from strategy
    minimal_roi = {
        "0": 10.0
    }

