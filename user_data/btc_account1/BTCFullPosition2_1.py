"""
（1）适用于btc等不同币种;
（2）全仓操作，独立的资金，但首次买入时会有冲突
（3）每分钟都会执行一次populate_indicators、populate_entry_trend、populate_exit_trend、bot_loop_start，确保可靠
（4）为了保证交易，会在买入时提高价格，卖出时降低价格的0.5%，基本等同于市价成交
（5）持久化信息到json文件，确保可靠执行
"""

import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from typing import Optional
import logging
from freqtrade.persistence import Trade
import os
import json
from datetime import datetime, timedelta
# 导入图形分析模块
try:
    from user_data.common.line_format_v2 import kline_1d_shape, check_double_top
except ImportError:
    from line_format_v2 import kline_1d_shape, check_double_top
from freqtrade.strategy import IStrategy, DecimalParameter
import ast  # 新增：用于安全解析 pattern_str
logger = logging.getLogger(__name__)


class BTCFullPosition2_1(IStrategy):
    """
    BTC全仓策略 - 账号1
    - 日线级别
    - 只做多
    - 全仓进出
    - 基于90日图形分析
    """
    # 启动所需K线数量：至少需要90根历史K线才能计算指标,多出90根的则是计算前一段时间的信号，方便查看, 以配置文件中的为准
    startup_candle_count: int = 150

    # 只在新K线时执行策略（推荐设置，避免同一K线反复执行导致信号不稳定）
    process_only_new_candles = False

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

    # 仓位调整：禁用加仓/减仓功能，仅全仓进出
    position_adjustment_enable = False  # 修复：设为 False，因为策略不支持加减仓

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

        # === 新增：信号持久化文件路径（将在 bot_loop_start 中动态处理） ===
        self.last_signal = {}  # 按 pair 存储信号
        self.min_amounts = {}  # 存储每个 pair 的最小 amount
        self.min_notional = {}  # 存储每个 pair 的最小订单价值
        self.min_amounts_loaded = False  # 标志是否已加载

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        print("populate_indicators执行")
        # 强制只用最近 150 根（90天指标 + 60天缓冲）
        dataframe = dataframe.tail(self.startup_candle_count).copy()
        # 原有指标计算（无需改动）
        dataframe['max_90'] = dataframe['high'].rolling(90).max()
        dataframe['min_90'] = dataframe['low'].rolling(90).min()
        dataframe['day_change'] = (dataframe['close'] - dataframe['open']) / dataframe['open']
        dataframe['is_green'] = (dataframe['close'] > dataframe['open']).astype(int)
        dataframe['is_red'] = (dataframe['close'] < dataframe['open']).astype(int)
        dataframe['pattern'] = None

        df_len = len(dataframe)
        logger.info(f"K线长度：{df_len}")
        for i in range(90, df_len):
            close_prices_90 = dataframe['close'].iloc[i - 89:i + 1].values
            try:
                pattern = kline_1d_shape(close_prices_90)
                dataframe.at[dataframe.index[i], 'pattern'] = str(pattern)
            except Exception:
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
        dataframe['enter_long'] = 0

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
                logger.warning(f"解析图形指标失败 {dataframe.index[i]}")

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

        # ==================== 新增：返回前打印所有行信号详情 ====================
        logger.info("[populate_entry_trend] === 所有K线买入信号详情（共 {} 行）===".format(len(dataframe)))
        logger.info("{:<4} {:<12} {:<10} {:<8} {:<20}".format("索引", "日期", "收盘价", "买入信号", "标签"))
        logger.info("-" * 60)
        # 只取最后5行（如果数据不足5行，就显示全部）
        rows_to_print = dataframe.tail(5)
        for idx, row in rows_to_print.iterrows():
            date_str = row['date'].strftime('%Y-%m-%d') if pd.notna(row['date']) else 'N/A'
            close_price = row['close']
            enter_signal = row.get('enter_long', 0)
            enter_tag = row.get('enter_tag', '')
            signal_text = "买入" if enter_signal == 1 else "-"
            logger.info("{:<4} {:<12} {:<10.2f} {:<8} {:<20}".format(
                idx, date_str, close_price, signal_text, enter_tag))
        logger.info("[populate_entry_trend] 信号打印完毕\n")

        # === 新增：如果最后一行有买入信号，持久化到文件 ===
        if len(dataframe) > 0 and dataframe['enter_long'].iloc[-1] == 1:
            pair = metadata.get('pair')  # 从 metadata 获取 pair
            if pair:
                signal_file = f'user_data/signal_{pair.replace("/", "_")}.json'  # 修复：按 pair 独立文件
                last_date = dataframe['date'].iloc[-1].strftime('%Y-%m-%d') if pd.notna(
                    dataframe['date'].iloc[-1]) else 'N/A'
                last_close = dataframe['close'].iloc[-1]
                signal_data = {
                    'type': 'entry',
                    'date': last_date,
                    'price': last_close,
                    'executed': False
                }
                try:
                    with open(signal_file, 'w') as f:
                        json.dump(signal_data, f)
                    self.last_signal[pair] = signal_data  # 按 pair 存储
                    logger.info(f"持久化买入信号 ({pair}): {signal_data}")
                except Exception as e:
                    logger.error(f"持久化买入信号失败 ({pair}): {e}")

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
        dataframe['exit_long'] = 0

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
                    if check_double_top(up_segments, price_a, self.double_top_higher_threshold.value,
                                        self.double_top_lower_threshold.value, "(情况1.1)"):
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
                            if check_double_top(remaining_up_segments, price_a, self.double_top_higher_threshold.value,
                                                self.double_top_lower_threshold.value, "(情况1.2)"):
                                dataframe.at[dataframe.index[i], 'pattern_exit_signal'] = True
                                continue

            except Exception:
                logger.warning(f"解析图形指标失败 {dataframe.index[i]}")

        # 最终平仓条件
        dataframe.loc[drop_condition & dataframe['pattern_exit_signal'], ['exit_long', 'enter_long']] = (1, 0)

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

        # ==================== 新增：返回前打印所有行信号详情 ====================
        logger.info("[populate_exit_trend] === 所有K线卖出信号详情（共 {} 行）===".format(len(dataframe)))
        logger.info("{:<4} {:<12} {:<10} {:<8} {:<20}".format("索引", "日期", "收盘价", "卖出信号", "标签"))
        logger.info("-" * 60)
        # 只取最后5行（如果数据不足5行，就显示全部）
        rows_to_print = dataframe.tail(5)
        for idx, row in rows_to_print.iterrows():
            date_str = row['date'].strftime('%Y-%m-%d') if pd.notna(row['date']) else 'N/A'
            close_price = row['close']
            exit_signal = row.get('exit_long', 0)
            exit_tag = row.get('exit_tag', '')
            signal_text = "卖出" if exit_signal == 1 else "-"
            logger.info("{:<4} {:<12} {:<10.2f} {:<8} {:<20}".format(
                idx, date_str, close_price, signal_text, exit_tag))
        logger.info("[populate_exit_trend] 信号打印完毕\n")

        # === 新增：如果最后一行有卖出信号，持久化到文件 ===
        if len(dataframe) > 0 and dataframe['exit_long'].iloc[-1] == 1:
            pair = metadata.get('pair')
            if pair:
                signal_file = f'user_data/signal_{pair.replace("/", "_")}.json'  # 修复：按 pair 独立文件
                last_date = dataframe['date'].iloc[-1].strftime('%Y-%m-%d') if pd.notna(
                    dataframe['date'].iloc[-1]) else 'N/A'
                last_close = dataframe['close'].iloc[-1]
                signal_data = {
                    'type': 'exit',
                    'date': last_date,
                    'price': last_close,
                    'executed': False
                }
                try:
                    with open(signal_file, 'w') as f:
                        json.dump(signal_data, f)
                    self.last_signal[pair] = signal_data
                    logger.info(f"持久化卖出信号 ({pair}): {signal_data}")
                except Exception as e:
                    logger.error(f"持久化卖出信号失败 ({pair}): {e}")

        return dataframe

    def bot_loop_start(self, **kwargs) -> None:
        """
        每分钟执行一次，用于强制挂单（限价单）和处理历史未执行信号
        支持多交易对，使用 config 中的 pair_whitelist 获取交易对
        """
        # ==================== 从 config 获取当前白名单交易对 ====================
        pair_whitelist = self.config.get('exchange', {}).get('pair_whitelist', [])
        if not pair_whitelist:
            logger.warning("config 中未配置 pair_whitelist，白名单为空，无法执行 bot_loop_start")
            return

        logger.debug(f"[bot_loop_start] 当前白名单交易对数量: {len(pair_whitelist)} - {pair_whitelist}")

        # ==================== 延迟加载市场限制（仅第一次执行时加载） ====================
        if not getattr(self, 'min_amounts_loaded', False):
            self.min_amounts = {}
            self.min_notional = {}
            try:
                markets = self.dp.exchange.markets
                for p, info in markets.items():
                    if 'limits' in info:
                        if 'amount' in info['limits'] and 'min' in info['limits']['amount']:
                            self.min_amounts[p] = info['limits']['amount']['min']
                        if 'cost' in info['limits'] and 'min' in info['limits']['cost']:
                            self.min_notional[p] = info['limits']['cost']['min']
                logger.info(f"预加载市场限制完成，共 {len(self.min_amounts)} 个交易对")
            except Exception as e:
                logger.warning(f"预加载市场限制失败，使用默认值: {e}")
            self.min_amounts_loaded = True

        # ==================== 对每个白名单交易对逐个处理 ====================
        for pair in pair_whitelist:
            try:
                coin, quote = pair.split('/')
            except Exception as e:
                logger.error(f"解析交易对失败: {pair} - {e}")
                continue

            logger.debug(f"[bot_loop_start] 处理交易对: {pair}")

            # 使用预加载的最小限制
            min_amount = self.min_amounts.get(pair, 0.00001)
            min_stake = self.min_notional.get(pair, self.config.get('stake_min', 5.0))

            # 余额获取
            total_coin_balance = self.wallets.get_total(coin)
            free_quote_balance = self.wallets.get_free(quote)

            # 获取最新分析的 dataframe（即使没有新K线，也会返回最近一次分析的结果）
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            if dataframe is None or len(dataframe) == 0:
                logger.debug(f"{pair} 无可用数据，跳过本次处理")
                continue

            last_row = dataframe.iloc[-1]

            # 获取当前实时价格
            try:
                ticker = self.dp.ticker(pair)
                current_rate = ticker['last']
            except Exception as e:
                logger.debug(f"获取 {pair} 实时价格失败: {e}，跳过")
                continue

            # 检查是否有开放交易
            open_trades = Trade.get_trades_proxy(is_open=True)
            has_open_trade = any(t.pair == pair for t in open_trades)

            # exchange 实例
            try:
                exchange = self.dp._exchange
            except AttributeError:
                exchange = self.exchange

            # ==================== 处理历史未执行信号 ====================
            signal_file = f'user_data/signal_{pair.replace("/", "_")}.json'
            current_date = datetime.now().strftime('%Y-%m-%d')

            last_signal = self.last_signal.get(pair)
            if last_signal is None and os.path.exists(signal_file):
                try:
                    with open(signal_file, 'r') as f:
                        self.last_signal[pair] = json.load(f)
                    last_signal = self.last_signal[pair]
                except Exception as e:
                    logger.error(f"加载历史信号失败 {pair}: {e}")

            if last_signal and not last_signal.get('executed', True):
                signal_date = last_signal.get('date', 'N/A')
                if signal_date in [current_date, (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')]:
                    signal_type = last_signal['type']

                    if (signal_type == 'entry' and not has_open_trade and
                        total_coin_balance < min_amount * 2 and free_quote_balance >= min_stake):
                        buy_price = current_rate * 1.01
                        amount = (free_quote_balance * 0.999) / buy_price
                        if amount >= min_amount:
                            try:
                                order = exchange.create_order(pair=pair, ordertype='limit', side='buy',
                                                              amount=amount, rate=buy_price, leverage=1.0)
                                logger.info(f"[历史信号] 补买入成功 {pair}: {amount:.8f} {coin}")
                                last_signal['executed'] = True
                                with open(signal_file, 'w') as f:
                                    json.dump(last_signal, f)
                            except Exception as e:
                                logger.error(f"历史买入失败 {pair}: {e}")

                    elif (signal_type == 'exit' and not has_open_trade and total_coin_balance > min_amount):
                        sell_price = current_rate * 0.99
                        amount = total_coin_balance * 0.99
                        try:
                            order = exchange.create_order(pair=pair, ordertype='limit', side='sell',
                                                          amount=amount, rate=sell_price, leverage=1.0)
                            logger.info(f"[历史信号] 补卖出成功 {pair}: {amount:.8f} {coin}")
                            last_signal['executed'] = True
                            with open(signal_file, 'w') as f:
                                json.dump(last_signal, f)
                        except Exception as e:
                            logger.error(f"历史卖出失败 {pair}: {e}")

            # ==================== 处理当前信号 ====================
            if (last_row.get('exit_long', 0) == 1 and
                total_coin_balance > min_amount and
                not has_open_trade):

                sell_price = current_rate * 0.99
                amount = total_coin_balance * 0.99

                try:
                    order = exchange.create_order(pair=pair, ordertype='limit', side='sell',
                                                  amount=amount, rate=sell_price, leverage=1.0)
                    logger.info(f"[卖出] 挂单成功 {pair}: {amount:.8f} {coin}")
                    if os.path.exists(signal_file):
                        os.remove(signal_file)
                        self.last_signal.pop(pair, None)
                except Exception as e:
                    logger.error(f"卖出挂单失败 {pair}: {e}")
                finally:
                    self.wallets.update()

            elif (last_row.get('enter_long', 0) == 1 and
                  not has_open_trade):

                if free_quote_balance < min_stake:
                    logger.info(f"{pair} 可用资金不足，忽略买入")
                    continue

                buy_price = current_rate * 1.01
                amount = (free_quote_balance * 0.999) / buy_price

                if amount < min_amount:
                    logger.info(f"{pair} 买入数量太小，忽略")
                    continue

                order_value = amount * buy_price
                if order_value < min_stake:
                    logger.info(f"{pair} 订单价值太小，忽略")
                    continue

                try:
                    order = exchange.create_order(pair=pair, ordertype='limit', side='buy',
                                                  amount=amount, rate=buy_price, leverage=1.0)
                    logger.info(f"[买入] 挂单成功 {pair}: {amount:.8f} {coin}")
                    if os.path.exists(signal_file):
                        os.remove(signal_file)
                        self.last_signal.pop(pair, None)
                except Exception as e:
                    logger.error(f"买入挂单失败 {pair}: {e}")
                finally:
                    self.wallets.update()

        logger.debug("bot_loop_start 本次循环完成")