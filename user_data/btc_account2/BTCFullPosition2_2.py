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

from freqtrade.persistence import Trade

# 导入图形分析模块
sys.path.insert(0, os.path.join(os.getcwd(), 'user_data', 'common'))
try:
    from user_data.common.line_format_v2 import kline_1d_shape
except ImportError:
    from line_format_v2 import kline_1d_shape

from freqtrade.strategy import IStrategy, DecimalParameter

logger = logging.getLogger(__name__)


class BTCFullPosition2_2(IStrategy):
    """
    BTC全仓策略 - 账号2
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
    timeframe = '1d'

    # 是否允许做空：仅做多，不做空
    can_short = False

    # 启动所需K线数量：至少需要90根历史K线才能计算指标
    # 原因：rolling(90) 需要90根K线，图形分析也需要90根
    startup_candle_count = 100

    # 仓位调整：禁用加仓/减仓功能，仅全仓进出
    # position_adjustment_enable = False

    # 只在新K线时执行策略（推荐设置，避免同一K线反复执行导致信号不稳定）
    # process_only_new_candles = True

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
    # 范围：10%-70%，默认36%（JSON优化值0.47接近旧上限0.55，扩大到0.70）
    # 示例：最高点10000，跌25%到7500时建仓
    # space='buy' 表示属于买入空间，可通过 hyperopt 优化
    max_drop_from_high = DecimalParameter(
        0.10, 0.70, default=0.36, decimals=2, space='buy', optimize=True,
        load=True
    )

    # 单日涨幅阈值：当天涨幅超过此比例时，检查图形确认建仓
    # 范围：0.3%-10%，默认1%（JSON优化值0.05达到旧上限，扩大到0.10）
    # 示例：今日 open=100, close=102，涨幅2%，触发图形分析
    day_rise_threshold = DecimalParameter(
        0.003, 0.10, default=0.01, decimals=3, space='buy', optimize=True,
        load=True
    )

    # 连续涨幅阈值：连续3天上涨且累计涨幅超过此比例时，检查图形确认建仓
    # 范围：1%-20%，默认6%（JSON优化值0.06在中间，适度扩大范围）
    # 示例：3天前100，今天103，累计涨3%且连续阳线，触发图形分析
    continuous_rise_threshold = DecimalParameter(
        0.01, 0.20, default=0.06, decimals=2, space='buy', optimize=True,
        load=True
    )

    # 图形下跌幅度阈值：图形分析中，前一个 down 段跌幅超过此比例才确认建仓信号
    # 范围：0.5%-40%，默认7%（JSON优化值0.02接近下限0.01，降低到0.005）
    # 示例：识别到 down 段从 110 跌到 99，跌幅10%，满足条件
    # 逻辑：先大跌再上涨，确认反转信号
    pattern_drop_threshold = DecimalParameter(
        0.005, 0.40, default=0.07, decimals=3, space='buy', optimize=True,
        load=True
    )

    # 双顶差距阈值（建仓用）：暂未使用，预留参数
    # 范围：2%-30%，默认10%（JSON优化值0.08在中间，适度扩大范围）
    double_top_threshold = DecimalParameter(
        0.02, 0.30, default=0.1, decimals=2, space='buy', optimize=True,
        load=True
    )

    # -------------------- 平仓（卖出）相关参数 --------------------

    # 单日跌幅阈值：当天跌幅超过此比例时，检查图形确认平仓
    # 范围：0.5%-8%，默认2%（JSON优化值0.02在中间，适度扩大范围）
    # 示例：今日 open=100, close=98，跌幅2%，触发图形分析
    # space='sell' 表示属于卖出空间，可通过 hyperopt 优化
    day_drop_threshold = DecimalParameter(
        0.005, 0.08, default=0.02, decimals=3, space='sell', optimize=True,
        load=True
    )

    # 连续跌幅阈值：连续3天下跌且累计跌幅超过此比例时，检查图形确认平仓
    # 范围：0.3%-12%，默认2%（JSON优化值0.06达到旧上限，扩大到0.12）
    # 示例：3天前100，今天97，累计跌3%且连续阴线，触发图形分析
    continuous_drop_threshold = DecimalParameter(
        0.003, 0.12, default=0.02, decimals=3, space='sell', optimize=True,
        load=True
    )

    # 双顶高位阈值：当前价格A比历史高点B高出的最大允许比例
    # 范围：0.5%-18%，默认6%（JSON优化值0.05在中间，适度扩大范围）
    # 示例：历史高点B=100，当前A=103，A比B高3%，在阈值内视为双顶
    # 用途：识别价格创新高但幅度不大的双顶形态
    double_top_higher_threshold = DecimalParameter(
        0.005, 0.18, default=0.06, decimals=3, space='sell', optimize=True,
        load=True
    )

    # 双顶低位阈值：当前价格A比历史高点B低的最大允许比例
    # 范围：2%-15%，默认5%（JSON优化值0.05在中间，适度扩大范围）
    # 示例：历史高点B=100，当前A=95，A比B低5%，在阈值内视为双顶
    # 用途：识别价格未能突破历史高点的双顶形态
    double_top_lower_threshold = DecimalParameter(
        0.02, 0.15, default=0.05, decimals=2, space='sell', optimize=True,
        load=True
    )

    # 最后一段下跌阈值：最后一个 down 段的跌幅小于此比例时才进行双顶检测
    # 范围：2%-18%，默认7%（JSON优化值0.09接近旧上限0.12，扩大到0.18）
    # 示例：最后 down 段从102跌到100，跌幅1.96%，小于5%，继续检测双顶
    # 用途：过滤掉大幅下跌的情况，只在小幅回调时检测双顶
    last_down_threshold = DecimalParameter(
        0.02, 0.18, default=0.07, decimals=2, space='sell', optimize=True,
        load=True
    )

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        # logger.info("[OK] BTC全仓策略已初始化")

    def check_double_top(self, up_segments: list, price_a: float, segment_name: str = "") -> bool:
        """
        检测双顶形态

        参数:
            up_segments: up段列表（已按从最近到最远排序）
            price_a: 基准价格A
            segment_name: 段名称（用于日志）

        返回:
            bool: 是否检测到双顶
        """
        # 需要至少1个前面的up段来比较
        if len(up_segments) < 1:
            return False

        # 比较A与第一个前面的up段B
        price_b = up_segments[0]['max_price']

        # A比B高3%以内 或 A比B低5%以内
        if price_a >= price_b:
            # A比B高的情况
            diff_higher = (price_a - price_b) / price_b
            if diff_higher <= self.double_top_higher_threshold.value:
                # logger.info(
                #     f"[SELL] 平仓信号{segment_name}-AB: A比B高{diff_higher:.2%} (A={price_a:.2f}, B={price_b:.2f})")
                return True
        else:
            # A比B低的情况
            diff_lower = (price_b - price_a) / price_b
            if diff_lower <= self.double_top_lower_threshold.value:
                # logger.info(
                #     f"[SELL] 平仓信号{segment_name}-AB: A比B低{diff_lower:.2%} (A={price_a:.2f}, B={price_b:.2f})")
                return True

        # 如果AB不成立，比较A与第二个前面的up段C
        if len(up_segments) >= 2:
            price_c = up_segments[1]['max_price']

            if price_a >= price_c:
                # A比C高的情况
                diff_higher = (price_a - price_c) / price_c
                if diff_higher <= self.double_top_higher_threshold.value:
                    # logger.info(
                    #     f"[SELL] 平仓信号{segment_name}-AC: A比C高{diff_higher:.2%} (A={price_a:.2f}, C={price_c:.2f})")
                    return True
            else:
                # A比C低的情况
                diff_lower = (price_c - price_a) / price_c
                if diff_lower <= self.double_top_lower_threshold.value:
                    # logger.info(
                    #     f"[SELL] 平仓信号{segment_name}-AC: A比C低{diff_lower:.2%} (A={price_a:.2f}, C={price_c:.2f})")
                    return True

        return False

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        print("populate_indicators执行")
        """
        计算指标
        """
        # 1. 最近90根最高价和最低价
        dataframe['max_90'] = dataframe['high'].rolling(90).max()
        dataframe['min_90'] = dataframe['low'].rolling(90).min()

        # 2. 当日涨跌幅
        dataframe['day_change'] = (dataframe['close'] - dataframe['open']) / dataframe['open']

        # 3. 计算连续涨跌
        dataframe['is_green'] = (dataframe['close'] > dataframe['open']).astype(int)
        dataframe['is_red'] = (dataframe['close'] < dataframe['open']).astype(int)

        # 4. 计算90日图形指标
        dataframe['pattern'] = None  # 初始化为None

        # 从第90根开始计算图形指标
        for i in range(90, len(dataframe)):
            close_prices_90 = dataframe['close'].iloc[i - 89:i + 1].values  # 最近90根（包括当前）
            try:
                pattern = kline_1d_shape(close_prices_90)
                dataframe.at[dataframe.index[i], 'pattern'] = str(pattern)  # 转为字符串存储
            except Exception:
                # logger.warning(f"计算图形指标失败 {dataframe.index[i]}")
                dataframe.at[dataframe.index[i], 'pattern'] = '[]'

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        print("populate_entry_trend执行")
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
        pass_max_drop = (
            (dataframe['close'] <= dataframe['max_90'] * (1 - self.max_drop_from_high.value))
        )

        # 条件2：当天涨幅>2% 或 连续上涨>3%，并满足图形条件
        # 2.1 单日涨幅>2%
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
        dataframe['pattern_entry_signal'] = False
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
                            dataframe.at[dataframe.index[i], 'pattern_entry_signal'] = True
                            # logger.info(f"[BUY] 条件2.1满足: 最后up/flat，倒数第二down跌{drop_pct:.1%}")
                            continue

                # 条件2.2：最后1个为up/flat，倒数第二为flat或小up，倒数第三为down且跌幅>10%
                if len(pattern) >= 3:
                    last = pattern[-1]
                    second_last = pattern[-2]
                    third_last = pattern[-3]

                    if last['line'] in ['up', 'flat']:
                        # 倒数第二为flat
                        if second_last['line'] == 'flat':
                            if third_last['line'] == 'down':
                                drop_pct = abs(
                                    (third_last['end_price'] - third_last['start_price']) / third_last['start_price'])
                                if drop_pct > self.pattern_drop_threshold.value:
                                    dataframe.at[dataframe.index[i], 'pattern_entry_signal'] = True
                                    # logger.info(f"[BUY] 条件2.2满足(flat): 倒数第三down跌{drop_pct:.1%}")
                                    continue

                        # 倒数第二为up但k_cnt<2且涨幅不超过5%
                        elif second_last['line'] == 'up' and second_last['k_cnt'] < 2:
                            rise_pct = abs(
                                (second_last['end_price'] - second_last['start_price']) / second_last['start_price'])
                            if rise_pct <= 0.05:
                                if third_last['line'] == 'down':
                                    drop_pct = abs((third_last['end_price'] - third_last['start_price']) / third_last[
                                        'start_price'])
                                    if drop_pct > self.pattern_drop_threshold.value:
                                        dataframe.at[dataframe.index[i], 'pattern_entry_signal'] = True
                                        # logger.info(f"[BUY] 条件2.2满足(小up): 倒数第三down跌{drop_pct:.1%}")
                                        continue

            except Exception:
                pass
                # logger.warning(f"解析图形指标失败 {dataframe.index[i]}")

        condition_2 = rise_condition & dataframe['pattern_entry_signal']

        # 最终建仓条件
        dataframe.loc[pass_max_drop | condition_2, 'enter_long'] = 1
        
        # 调试信息：显示建仓信号数量
        entry_count = (pass_max_drop | condition_2).sum()
        if entry_count > 0:
            print(f"[DEBUG] 生成 {entry_count} 个建仓信号 | "
                  f"条件1: {pass_max_drop.sum()} | 条件2: {condition_2.sum()}")
        
        # 添加条件状态说明字段（用于UI查看）
        dataframe['enter_tag'] = ''
        
        # 计算从最高点下跌幅度（用于标签显示）
        drop_from_high = (dataframe['max_90'] - dataframe['close']) / dataframe['max_90']
        
        # 为满足条件的行添加标签
        # 只满足条件1（从最高点下跌）
        dataframe.loc[pass_max_drop & ~condition_2, 'enter_tag'] = (
            'C1:max90跌' + (drop_from_high * 100).round(1).astype(str) + '%'
        )
        
        # 只满足条件2（涨幅+图形反转）
        dataframe.loc[~pass_max_drop & condition_2, 'enter_tag'] = 'C2:涨+反转'
        
        # 同时满足条件1和条件2
        dataframe.loc[pass_max_drop & condition_2, 'enter_tag'] = (
            'C1+C2:max90跌' + (drop_from_high * 100).round(1).astype(str) + '%+涨+反转'
        )

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        print("populate_exit_trend执行")

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
                    if self.check_double_top(up_segments, price_a, "(情况1.1)"):
                        dataframe.at[dataframe.index[i], 'pattern_exit_signal'] = True
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
                            if self.check_double_top(remaining_up_segments, price_a, "(情况1.2)"):
                                dataframe.at[dataframe.index[i], 'pattern_exit_signal'] = True
                                continue

            except Exception:
                pass
                # logger.warning(f"解析图形指标失败 {dataframe.index[i]}")

        # 最终平仓条件
        dataframe.loc[drop_condition & dataframe['pattern_exit_signal'], 'exit_long'] = 1
        
        # 添加条件状态说明字段（用于UI查看）
        dataframe['exit_tag'] = ''
        
        # 为满足平仓条件的行添加标签
        exit_mask = drop_condition & dataframe['pattern_exit_signal']
        
        # 判断是单日跌幅还是连续跌幅触发
        single_drop_only = exit_mask & single_day_drop & ~continuous_drop
        continuous_drop_only = exit_mask & continuous_drop & ~single_day_drop
        both_drop = exit_mask & single_day_drop & continuous_drop
        
        # 添加标签
        dataframe.loc[single_drop_only, 'exit_tag'] = '单日跌+双顶'
        dataframe.loc[continuous_drop_only, 'exit_tag'] = '连续跌+双顶'
        dataframe.loc[both_drop, 'exit_tag'] = '单日跌+连续跌+双顶'

        return dataframe

    # 处理信号冲突的位置，同时出现两种信号时，以卖出信号为准，买入信号消除
    def populate_trades(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 优先处理信号冲突：有卖出信号时，强制清除买入信号
        dataframe.loc[dataframe['exit_long'] == 1, 'enter_long'] = 0

        # 如果你还想处理短仓（short）冲突，可以类似处理
        # dataframe.loc[dataframe['exit_short'] == 1, 'enter_short'] = 0

        return dataframe

    # ==================== 新增：自定义初始下注金额（实现买入时用全部USDT） ====================
    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                            proposed_stake: float, min_stake: Optional[float], max_stake: float,
                            leverage: float, entry_tag: Optional[str], side: str,
                            **kwargs) -> float:
        """
        当 stake_amount = "unlimited" 时，此方法决定初始开仓金额。
        返回一个极大值，让 Freqtrade 用掉几乎全部可用余额（受 tradable_balance_ratio=0.99 控制）。
        """
        logger.info(f"[custom_stake_amount] 执行开始: pair={pair}, current_time={current_time}, "
                    f"current_rate={current_rate}, proposed_stake={proposed_stake}, "
                    f"min_stake={min_stake}, max_stake={max_stake}, leverage={leverage}, "
                    f"entry_tag={entry_tag}, side={side}")

        # 计算返回值（足够大即可，确保取 max_stake）
        return_value = max_stake * 10
        logger.info(f"[custom_stake_amount] 计算返回值: return_value={return_value} (基于 max_stake={max_stake})")

        logger.info("[custom_stake_amount] 执行结束")
        return return_value

    # ==================== 新增：动态仓位调整（实现卖出时全卖，包括预存量BTC） ====================
    def adjust_trade_position(self, trade: Trade, current_time: datetime,
                              current_rate: float, current_profit: float,
                              min_stake: Optional[float], max_stake: float,
                              current_entry_rate: float, current_exit_rate: float,
                              current_entry_profit: float, current_exit_profit: float,
                              **kwargs) -> Optional[float]:

        logger.info(f"[adjust_trade_position] 执行开始: trade_id={trade.id}, pair={trade.pair}, "
                    f"current_time={current_time}, current_rate={current_rate}, "
                    f"current_profit={current_profit}, min_stake={min_stake}, max_stake={max_stake}, "
                    f"current_entry_rate={current_entry_rate}, current_exit_rate={current_exit_rate}, "
                    f"current_entry_profit={current_entry_profit}, current_exit_profit={current_exit_profit}")

        # 检查是否有挂单
        if trade.has_open_orders:
            logger.info("[adjust_trade_position] 有挂单存在，不进行调整，返回 None")
            logger.info("[adjust_trade_position] 执行结束")
            return None

        # 获取当前交易对的基本币种（如 BTC）
        coin = trade.pair.split('/')[0]
        logger.info(f"[adjust_trade_position] 币种: coin={coin}")

        # 获取账户中该币种的全部持仓量（包括预先存在的存量/dust）
        total_coin_balance = self.wallets.get_total(coin)
        logger.info(f"[adjust_trade_position] 账户总持仓量: total_coin_balance={total_coin_balance}")

        # 当前机器人管理的持仓量
        logger.info(f"[adjust_trade_position] 机器人管理持仓量: trade.amount={trade.amount}")

        # 获取 analyzed dataframe 检查卖出信号
        dataframe, _ = self.dp.get_analyzed_dataframe(trade.pair, self.timeframe)
        if dataframe.empty:
            logger.warning("[adjust_trade_position] dataframe 为空，无法检查信号，返回 None")
            logger.info("[adjust_trade_position] 执行结束")
            return None

        last_candle = dataframe.iloc[-1]
        exit_long = last_candle.get('exit_long', 0)
        logger.info(f"[adjust_trade_position] 最后蜡烛卖出信号: exit_long={exit_long}")

        if exit_long == 1:
            logger.info("[adjust_trade_position] 检测到卖出信号，开始计算全卖逻辑")

            # 计算额外存量
            extra_amount = total_coin_balance - trade.amount
            logger.info(f"[adjust_trade_position] 额外存量（预存部分）: extra_amount={extra_amount}")

            if extra_amount > 0:
                # 计算额外 stake 价值
                extra_stake = extra_amount * current_rate
                logger.info(
                    f"[adjust_trade_position] 额外 stake 价值: extra_stake={extra_stake} (基于 current_rate={current_rate})")

                # 计算返回值（负值，全卖 + 额外，留缓冲）
                return_value = - (trade.stake_amount + extra_stake * 0.999)
                logger.info(
                    f"[adjust_trade_position] 计算返回值: return_value={return_value} (标签: full_sell_including_dust)")
                logger.info("[adjust_trade_position] 执行结束")
                return return_value, "full_sell_including_dust"
            else:
                # 无额外，直接全卖
                return_value = -trade.stake_amount
                logger.info(
                    f"[adjust_trade_position] 无额外存量，计算返回值: return_value={return_value} (标签: full_sell_normal)")
                logger.info("[adjust_trade_position] 执行结束")
                return return_value, "full_sell_normal"

        logger.info("[adjust_trade_position] 无卖出信号或条件不满足，返回 None")
        logger.info("[adjust_trade_position] 执行结束")
        return None