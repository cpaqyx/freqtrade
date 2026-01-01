"""
BTC全仓策略 - 基于90日图形分析
只做多，不做空，全仓进出
"""

import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from typing import Optional
import logging
import sys
import os

# 导入图形分析模块
sys.path.insert(0, os.path.join(os.getcwd(), 'user_data', 'common'))
try:
    from user_data.common.line_format_v2 import kline_1m_shape
except ImportError:
    from line_format_v2 import kline_1m_shape


from freqtrade.strategy import IStrategy, DecimalParameter

logger = logging.getLogger(__name__)


class BTCFullPosition_1m(IStrategy):
    """
    BTC全仓策略
    - 日线级别
    - 只做多
    - 全仓进出
    - 基于90日图形分析
    """

    # ==================== 测试模式开关 ====================
    # 立即成交测试模式：用于测试交易流程是否正常
    # True: 强制立即买入和卖出（忽略所有策略逻辑）
    # False: 按正常策略逻辑执行（默认）
    # instant_trade_test_mode = True

    INTERFACE_VERSION = 3

    # ==================== 基础策略参数 ====================

    # 时间周期：日线级别（1天一根K线）
    # 可选值：'1m', '5m', '15m', '1h', '4h', '1d', '1w' 等
    timeframe = '1m'

    # 是否允许做空：仅做多，不做空
    can_short = False

    # 启动所需K线数量：至少需要90根历史K线才能计算指标
    # 原因：rolling(90) 需要90根K线，图形分析也需要90根
    startup_candle_count = 100

    # 仓位调整：禁用加仓/减仓功能，仅全仓进出
    position_adjustment_enable = False

    process_only_new_candles = False  # 强制每次都执行（不推荐）
    # process_only_new_candles = True  # 只在新K线时执行（默认值，推荐）

    # ==================== ROI 和止损配置 ====================

    # 最小 ROI（Return on Investment）目标利润
    # "0": 10.0 表示从开仓时刻起，目标收益为 1000%
    # 设置为极端值，实际由策略的 populate_exit_trend 信号控制平仓
    minimal_roi = {
        "0": 10.0
    }

    # 止损比例：-0.99 表示允许最大亏损 99%
    # 设置为极端值，实际由策略信号控制平仓，避免因价格波动触发止损
    stoploss = -0.99

    # ==================== 可优化参数（Hyperopt）====================

    # -------------------- 建仓（买入）相关参数 --------------------

    # 从最高点跌幅阈值：价格从90日最高点下跌此比例时触发建仓
    # 调整为更敏感：允许更小的回落就触发，适配 1m 高频
    # space='buy' 表示属于买入空间，可通过 hyperopt 优化
    max_drop_from_high = DecimalParameter(
        0.001, 0.03, default=0.01, decimals=3, space='buy', optimize=True,
        load=True
    )

    # 单根K线涨幅阈值：当天涨幅超过此比例时，检查图形确认建仓
    # 调低阈值以更频繁触发
    # 示例：今日 open=100, close=102，涨幅2%，触发图形分析
    day_rise_threshold = DecimalParameter(
        0.0005, 0.020, default=0.0015, decimals=4, space='buy', optimize=True,
        load=True
    )

    # 连续涨幅阈值：连续3天上涨且累计涨幅超过此比例时，检查图形确认建仓
    # 调低阈值，以提高连续上涨触发概率
    # 示例：3天前100，今天103，累计涨3%且连续阳线，触发图形分析
    continuous_rise_threshold = DecimalParameter(
        0.0005, 0.02, default=0.006, decimals=3, space='buy', optimize=True,
        load=True
    )

    # 图形下跌幅度阈值：图形分析中，前一个 down 段跌幅超过此比例才确认建仓信号
    # 调低阈值，让更多 down 段参与建仓确认
    # 示例：识别到 down 段从 110 跌到 99，跌幅10%，满足条件
    # 逻辑：先大跌再上涨，确认反转信号
    pattern_drop_threshold = DecimalParameter(
        0.003, 0.080, default=0.007, decimals=3, space='buy', optimize=True,
        load=True
    )

    last_up_threshold = DecimalParameter(
        0.003, 0.05, default=0.005, decimals=3, space='buy', optimize=True,
        load=True
    )

    # 双顶差距阈值（建仓用）：暂未使用，预留参数
    # 适度放宽范围以便未来优化
    double_top_threshold = DecimalParameter(
        0.001, 0.100, default=0.005, decimals=3, space='buy', optimize=True,
        load=True
    )

    # -------------------- 平仓（卖出）相关参数 --------------------

    # 单根K线跌幅阈值：当天跌幅超过此比例时，检查图形确认平仓
    # 调低阈值，使轻微回撤也有机会触发平仓
    # 示例：今日 open=100, close=98，跌幅2%，触发图形分析
    # space='sell' 表示属于卖出空间，可通过 hyperopt 优化
    day_drop_threshold = DecimalParameter(
        0.0001, 0.01, default=0.0006, decimals=4, space='sell', optimize=True,
        load=True
    )

    # 连续跌幅阈值：连续3天下跌且累计跌幅超过此比例时，检查图形确认平仓
    # 调低阈值，让连续下跌更容易触发
    # 示例：3天前100，今天97，累计跌3%且连续阴线，触发图形分析
    continuous_drop_threshold = DecimalParameter(
        0.0002, 0.01, default=0.001, decimals=4, space='sell', optimize=True,
        load=True
    )

    # 双顶高位阈值：当前价格A比历史高点B高出的最大允许比例
    # 放宽上限，使更多创新高形态被识别为双顶
    # 示例：历史高点B=100，当前A=103，A比B高3%，在阈值内视为双顶
    # 用途：识别价格创新高但幅度不大的双顶形态
    double_top_higher_threshold = DecimalParameter(
        0.0005, 0.02, default=0.005, decimals=4, space='sell', optimize=True,
        load=True
    )

    # 双顶低位阈值：当前价格A比历史高点B低的最大允许比例
    # 放宽范围，使未能突破高点的形态更容易被识别
    # 示例：历史高点B=100，当前A=95，A比B低5%，在阈值内视为双顶
    # 用途：识别价格未能突破历史高点的双顶形态
    double_top_lower_threshold = DecimalParameter(
        0.0005, 0.02, default=0.006, decimals=3, space='sell', optimize=True,
        load=True
    )

    # 最后一段下跌阈值：最后一个 down 段的跌幅小于此比例时才进行双顶检测
    # 放宽阈值，让更多小幅下跌场景进入双顶检测
    # 示例：最后 down 段从102跌到100，跌幅1.96%，小于5%，继续检测双顶
    # 用途：过滤掉大幅下跌的情况，只在小幅回调时检测双顶
    last_down_threshold = DecimalParameter(
        0.0005, 0.020, default=0.001, decimals=4, space='sell', optimize=True,
        load=True
    )

    # ==================== 绘图配置 ====================
    # plot_config = {
    #     'main_plot': {
    #         # 主图显示90日最高价和最低价
    #         'max_90': {'color': 'red', 'type': 'line'},
    #         'min_90': {'color': 'green', 'type': 'line'},
    #     },
    #     'subplots': {
    #         # 子图1：当根K线涨跌幅百分比
    #         "涨跌幅%": {
    #             'candle_change_pct': {'color': 'blue', 'type': 'line'},
    #         },
    #         # 子图2：连续涨跌标记
    #         "涨跌标记": {
    #             'is_green': {'color': 'green', 'type': 'line'},
    #             'is_red': {'color': 'red', 'type': 'line'},
    #         },
    #     }
    # }

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        # logger.info("[OK] BTC全仓策略已初始化")

    def check_double_top(self, up_segments: list, price_a: float, segment_name: str = "") -> tuple:
        """
        检测双顶形态

        参数:
            up_segments: up段列表（已按从最近到最远排序）
            price_a: 基准价格A
            segment_name: 段名称（用于日志）

        返回:
            tuple: (是否检测到双顶, 标签说明)
        """
        # 需要至少1个前面的up段来比较
        if len(up_segments) < 1:
            return False, ""

        # 比较A与第一个前面的up段B
        price_b = up_segments[0]['max_price']

        # A比B高3%以内 或 A比B低5%以内
        if price_a >= price_b:
            # A比B高的情况
            diff_higher = (price_a - price_b) / price_b
            if diff_higher <= self.double_top_higher_threshold.value:
                tag = f"{segment_name}AB:A比B高{diff_higher:.2%}"
                # logger.info(
                #     f"[SELL] 平仓信号{tag} (A={price_a:.2f}, B={price_b:.2f})")
                return True, tag
        else:
            # A比B低的情况
            diff_lower = (price_b - price_a) / price_b
            if diff_lower <= self.double_top_lower_threshold.value:
                tag = f"{segment_name}AB:A比B低{diff_lower:.2%}"
                # logger.info(
                #     f"[SELL] 平仓信号{tag} (A={price_a:.2f}, B={price_b:.2f})")
                return True, tag

        # 如果AB不成立，比较A与第二个前面的up段C
        if len(up_segments) >= 2:
            price_c = up_segments[1]['max_price']

            if price_a >= price_c:
                # A比C高的情况
                diff_higher = (price_a - price_c) / price_c
                if diff_higher <= self.double_top_higher_threshold.value:
                    tag = f"{segment_name}AC:A比C高{diff_higher:.2%}"
                    # logger.info(
                    #     f"[SELL] 平仓信号{tag} (A={price_a:.2f}, C={price_c:.2f})")
                    return True, tag
            else:
                # A比C低的情况
                diff_lower = (price_c - price_a) / price_c
                if diff_lower <= self.double_top_lower_threshold.value:
                    tag = f"{segment_name}AC:A比C低{diff_lower:.2%}"
                    # logger.info(
                    #     f"[SELL] 平仓信号{tag} (A={price_a:.2f}, C={price_c:.2f})")
                    return True, tag

        return False, ""

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # print("populate_indicators执行")
        """
        计算指标
        """
        # 1. 最近90根最高价和最低价
        dataframe['max_90'] = dataframe['high'].rolling(90).max()
        dataframe['min_90'] = dataframe['low'].rolling(90).min()

        # 2. 当日涨跌幅
        dataframe['day_change'] = (dataframe['close'] - dataframe['open']) / dataframe['open']
        
        # 2.1 当根K线涨跌幅度（绝对值和百分比）
        dataframe['candle_change_pct'] = ((dataframe['close'] - dataframe['open']) / dataframe['open']) * 100  # 百分比
        dataframe['candle_change_abs'] = dataframe['close'] - dataframe['open']  # 绝对值

        # 3. 计算连续涨跌
        dataframe['is_green'] = (dataframe['close'] > dataframe['open']).astype(int)
        dataframe['is_red'] = (dataframe['close'] < dataframe['open']).astype(int)

        # 4. 计算90日图形指标
        dataframe['pattern'] = None  # 初始化为None

        # 从第90根开始计算图形指标
        for i in range(90, len(dataframe)):
            close_prices_90 = dataframe['close'].iloc[i - 89:i + 1].values  # 最近90根（包括当前）
            try:
                pattern = kline_1m_shape(close_prices_90)
                dataframe.at[dataframe.index[i], 'pattern'] = str(pattern)  # 转为字符串存储
            except Exception:
                # logger.warning(f"计算图形指标失败 {dataframe.index[i]}")
                dataframe.at[dataframe.index[i], 'pattern'] = '[]'

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # print("populate_entry_trend执行")
        """
        建仓条件
        """
        # ========== 测试模式：立即买入 ==========
        # if self.instant_trade_test_mode:
        #     logger.warning("[测试模式] 强制生成买入信号（忽略所有策略条件）")
        #     dataframe.loc[:, 'enter_long'] = 0  # 先清空所有信号
        #     if len(dataframe) > 0:
        #         dataframe.loc[dataframe.index[-1], 'enter_long'] = 1  # 最后一根K线强制买入
        #     return dataframe

        conditions = []

        # 条件1：从最高点跌25%，直接建仓
        condition_down = (
            (dataframe['close'] <= dataframe['max_90'] * (1 - self.max_drop_from_high.value))
        )

        # 条件2：当天涨幅>2% 或 连续上涨>3%，并满足图形条件
        # 2.1 单根K线涨幅>2%
        single_day_rise = (dataframe['day_change'] > self.day_rise_threshold.value)

        # 2.2 连续上涨>3%（计算最近3天的累计涨幅）
        dataframe['rise_3d'] = (
                (dataframe['close'] - dataframe['close'].shift(3)) / dataframe['close'].shift(3)
        )
        continuous_rise = (
                (dataframe['is_green'] == 1) &
                (dataframe['is_green'].shift(1) == 1) &
                (dataframe['is_green'].shift(2) == 1) &
                (dataframe['rise_3d'] > self.continuous_rise_threshold.value)
        )

        # 满足涨幅条件
        rise_condition = single_day_rise | continuous_rise

        # 图形条件（需要逐行检查）
        dataframe['last_down_signal'] = False
        dataframe['enter_tag'] = ''
        
        for i in range(90, len(dataframe)):
            if not rise_condition.iloc[i]:
                continue

            pattern_str = dataframe['pattern'].iloc[i]
            if not pattern_str or pattern_str == '[]':
                continue

            try:
                pattern = eval(pattern_str, {"np": np})  # 将字符串转回list，提供np上下文
                if not pattern or len(pattern) == 0:
                    continue

                # 检查图形条件
                # 条件2.1：最后1个为up/flat，倒数第二为down且跌幅>10%
                if len(pattern) >= 2:
                    last = pattern[-1]
                    second_last = pattern[-2]

                    if last['line'] in ['up', 'flat'] and second_last['line'] == 'down':
                        drop_pct = abs(
                            (second_last['end_price'] - second_last['start_price']) / second_last['start_price'])
                        if drop_pct > self.pattern_drop_threshold.value:
                            dataframe.at[dataframe.index[i], 'last_down_signal'] = True
                            dataframe.at[dataframe.index[i], 'enter_tag'] = f"反转2.1:down跌{drop_pct:.1%}后{last['line']}"
                            # logger.info(f"[BUY] 条件2.1满足: 最后up/flat，倒数第二down跌{drop_pct:.1%}")
                            continue

                # 条件2.2：最后1个为up/flat，倒数第二为flat或小up，倒数第三为down且跌幅>10%
                if len(pattern) >= 3:
                    last = pattern[-1]
                    second_last = pattern[-2]
                    third_last = pattern[-3]

                    # 最后一段为下跌，且跌幅大于pattern_drop_threshold，标识一下
                    if last['line'] in ['down']:
                        drop_pct = abs((last['end_price'] - last['start_price']) / last['start_price'])
                        if drop_pct > self.pattern_drop_threshold.value:
                            dataframe.at[dataframe.index[i], 'last_down_signal'] = True
                            dataframe.at[dataframe.index[i], 'enter_tag'] = f"2.2.1最后一段下跌{drop_pct}，仅标识"

                    # 最后一段和第二段都是下跌,且跌幅大于pattern_drop_threshold，标识一下
                    if last['line'] in ['down'] and second_last['line'] == 'down':
                        drop_pct = abs((last['end_price'] - second_last['start_price']) / second_last['start_price'])
                        if drop_pct > self.pattern_drop_threshold.value:
                            dataframe.at[dataframe.index[i], 'last_down_signal'] = True
                            dataframe.at[dataframe.index[i], 'enter_tag'] = f"2.2.2最后两段下跌{drop_pct}，仅标识"

                    # 最后一段上涨，第二段下跌，涨幅不能超过，且跌幅超过pattern_drop_threshold
                    if last['line'] in ['up'] and second_last['line'] == 'down':
                        up_pct = (last['end_price'] - last['start_price']) / last['start_price']
                        drop_pct = abs((last['end_price'] - second_last['start_price']) / second_last['start_price'])
                        if drop_pct > self.pattern_drop_threshold.value and up_pct < self.last_up_threshold.value:
                            dataframe.at[dataframe.index[i], 'last_down_signal'] = True
                            dataframe.at[dataframe.index[i], 'enter_tag'] = f"2.2.3最后段上涨{up_pct}二段下跌{drop_pct}，仅标识"

            except Exception:
                pass
                # logger.warning(f"解析图形指标失败 {dataframe.index[i]}")

        condition = rise_condition & dataframe['last_down_signal']

        # 最终建仓条件
        dataframe.loc[condition, 'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # print("populate_exit_trend执行")

        # ========== 测试模式：立即卖出 ==========
        # if self.instant_trade_test_mode:
        #     logger.warning("[测试模式] 强制生成卖出信号（忽略所有策略条件）")
        #     dataframe.loc[:, 'exit_long'] = 0  # 先清空所有信号
        #     if len(dataframe) > 0:
        #         dataframe.loc[dataframe.index[-1], 'exit_long'] = 1  # 最后一根K线强制卖出
        #     return dataframe

        """
        平仓条件：
        1. 当天跌幅为负且跌幅>2% 或 连续下跌>3%
        2. 分析图形指标检测双顶形态
        """

        # 条件1：当天跌幅为负且跌幅>2% 或 连续下跌>3%
        # 1.1 单日跌幅>2%（当天涨幅为负）
        single_day_drop = (dataframe['day_change'] < -self.day_drop_threshold.value)

        # 1.2 连续下跌>3%（计算最近3天的累计跌幅）
        dataframe['drop_3d'] = (
                (dataframe['close'] - dataframe['close'].shift(3)) / dataframe['close'].shift(3)
        )
        continuous_drop = (
                (dataframe['is_red'] == 1) &
                (dataframe['is_red'].shift(1) == 1) &
                (dataframe['is_red'].shift(2) == 1) &
                (dataframe['drop_3d'] < -self.continuous_drop_threshold.value)
        )

        # 满足跌幅条件
        drop_condition = single_day_drop | continuous_drop

        # 图形条件（需要逐行检查双顶）
        dataframe['pattern_exit_signal'] = False
        dataframe['exit_tag'] = ''
        
        for i in range(90, len(dataframe)):
            if not drop_condition.iloc[i]:
                continue

            pattern_str = dataframe['pattern'].iloc[i]
            if not pattern_str or pattern_str == '[]':
                continue

            try:
                pattern = eval(pattern_str, {"np": np})  # 将字符串转回list，提供np上下文
                if not pattern or len(pattern) == 0:
                    continue

                last = pattern[-1]

                # 情况1.1：最后1个段为up
                if last['line'] == 'up':
                    # 获取最后一个up段的最高价A
                    price_a = last['max_price']

                    # 找前面的up段进行双顶比较
                    up_segments = []
                    for j in range(len(pattern) - 2, -1, -1):
                        if pattern[j]['line'] == 'up':
                            up_segments.append(pattern[j])

                    # 使用独立方法检测双顶
                    is_double_top, tag = self.check_double_top(up_segments, price_a, "双顶1.1")
                    if is_double_top:
                        dataframe.at[dataframe.index[i], 'pattern_exit_signal'] = True
                        dataframe.at[dataframe.index[i], 'exit_tag'] = tag
                        continue

                # 情况1.2：最后1段为down，但跌幅绝对值在5%以内
                elif last['line'] == 'down':
                    drop_pct = abs((last['end_price'] - last['start_price']) / last['start_price'])

                    if drop_pct <= self.last_down_threshold.value:
                        # 向前找up段
                        up_segments = []
                        for j in range(len(pattern) - 2, -1, -1):
                            if pattern[j]['line'] == 'up':
                                up_segments.append(pattern[j])

                        # 至少需要2个up段来比较（第一个作为A，第二个和第三个作为B和C）
                        if len(up_segments) >= 2:
                            # 第一个up段的最高价作为A
                            price_a = up_segments[0]['max_price']
                            # 剩余的up段（从第二个开始）
                            remaining_up_segments = up_segments[1:]

                            # 使用独立方法检测双顶
                            is_double_top, tag = self.check_double_top(remaining_up_segments, price_a, f"双顶1.2(down跌{drop_pct:.1%})")
                            if is_double_top:
                                dataframe.at[dataframe.index[i], 'pattern_exit_signal'] = True
                                dataframe.at[dataframe.index[i], 'exit_tag'] = tag
                                continue

            except Exception:
                pass
                # logger.warning(f"解析图形指标失败 {dataframe.index[i]}")

        # 最终平仓条件
        dataframe.loc[drop_condition & dataframe['pattern_exit_signal'], 'exit_long'] = 1

        return dataframe


