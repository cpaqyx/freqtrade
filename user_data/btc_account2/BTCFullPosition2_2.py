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
from freqtrade.persistence import Trade

# 导入图形分析模块
try:
    from user_data.common.line_format_v2 import kline_1d_shape, check_double_top
except ImportError:
    from line_format_v2 import kline_1d_shape, check_double_top
from freqtrade.strategy import IStrategy, DecimalParameter
logger = logging.getLogger(__name__)


class BTCFullPosition2_2(IStrategy):
    """
    BTC全仓策略 - 账号1
    - 日线级别
    - 只做多
    - 全仓进出
    - 基于90日图形分析
    """
    # 启动所需K线数量：至少需要90根历史K线才能计算指标,多出90根的则是计算前一段时间的信号，方便查看, 以配置文件中的为准
    startup_candle_count: int = 150

    # 保持默认行为：只有新K线时才完整执行策略函数（每天执行一次）
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
    position_adjustment_enable = True

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

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        print("populate_indicators执行")
        # 注意：不再截断 dataframe，保持与输入相同的长度
        # Freqtrade 会根据 startup_candle_count 自动管理数据量
        input_len = len(dataframe)
        logger.info(f"[populate_indicators] K线长度: {input_len}")
        
        # 原有指标计算
        dataframe['max_90'] = dataframe['high'].rolling(90).max()
        dataframe['min_90'] = dataframe['low'].rolling(90).min()
        dataframe['day_change'] = (dataframe['close'] - dataframe['open']) / dataframe['open']
        dataframe['is_green'] = (dataframe['close'] > dataframe['open']).astype(int)
        dataframe['is_red'] = (dataframe['close'] < dataframe['open']).astype(int)
        dataframe['pattern'] = None

        # 只从第90根开始计算图形（前面的数据不足以计算90日指标）
        for i in range(90, len(dataframe)):
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
                pass
                # logger.warning(f"解析图形指标失败 {dataframe.index[i]}")

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

        return dataframe

    # ==================== 新增：动态仓位调整（实现卖出时全卖，包括预存量BTC） ====================
    def adjust_trade_position(self, trade: Trade, current_time: datetime,
                              current_rate: float, current_profit: float,
                              min_stake: Optional[float], max_stake: float,
                              current_entry_rate: float, current_exit_rate: float,
                              current_entry_profit: float, current_exit_profit: float,
                              **kwargs) -> Optional[float]:

        coin, quote = trade.pair.split('/')  # e.g., 'BTC/USDT' → coin='BTC', quote='USDT'

        # 获取钱包余额
        total_coin_balance = self.wallets.get_total(coin)  # 该币总持有量（包括尘埃）
        free_quote_balance = self.wallets.get_free(quote)  # 可用稳定币余额（可用于买入）

        # 获取最新信号
        dataframe, _ = self.dp.get_analyzed_dataframe(trade.pair, self.timeframe)
        last_row = dataframe.iloc[-1]

        logger.info(f"[adjust_trade_position] 时间:{current_time}, 交易对:{trade.pair}, "
                    f"钱包{coin}:{total_coin_balance:.8f}, 机器人持仓:{trade.amount:.8f}, "
                    f"可用{quote}:{free_quote_balance:.2f}, 当前价:{current_rate}, "
                    f"最新K线:{last_row['date']}, enter_long:{last_row.get('enter_long', 0)}, "
                    f"exit_long:{last_row.get('exit_long', 0)}")

        # 修改后的挂单检查：仅对买入信号应用检查，对卖出信号允许继续执行全卖（忽略挂单）
        if trade.has_open_orders:
            if last_row.get('exit_long', 0) == 1:
                logger.info("[adjust_trade_position] 存在挂单，但卖出信号，继续全卖")
            else:
                logger.info("[adjust_trade_position] 存在挂单，跳过本次调整")
                return None

        # 1. 卖出信号：全仓平仓（包括钱包中多余的尘埃币），持续尝试直到卖完
        if last_row.get('exit_long', 0) == 1:
            # 计算总需卖出量（机器人持仓 + 尘埃）
            total_to_sell = total_coin_balance
            if total_to_sell > 0:
                # 卖出全部（留0.1%手续费余地）
                sell_stake = total_to_sell * current_rate * 0.99
                logger.info(f"[adjust_trade_position] 全卖全部仓位 ({total_to_sell:.8f} {coin})，返回 -{sell_stake:.2f}")
                return -sell_stake
            else:
                logger.info("[adjust_trade_position] 无仓位可卖，返回 None")
                return None

        # 2. 买入信号：全仓加仓（用尽所有可用稳定币买入），持续尝试直到买完可用资金
        elif last_row.get('enter_long', 0) == 1:
            if free_quote_balance > min_stake:  # 有足够资金才加仓
                # 用掉几乎所有可用稳定币（留一点防滑点/手续费）
                add_stake = free_quote_balance * 0.999
                logger.info(
                    f"[adjust_trade_position] 全仓加仓，可用{quote}:{free_quote_balance:.2f}，返回 +{add_stake:.2f}")
                return add_stake
            else:
                logger.info(f"[adjust_trade_position] 买入信号但可用资金不足{min_stake}，跳过加仓")
                return None

        # 3. 无信号：不操作
        logger.info("[adjust_trade_position] 无明确进出信号，返回 None")
        return None

    # ==================== 新增：自定义买入价格（当前价 +1%） ====================
    def custom_entry_price(self, pair: str, current_time: datetime, proposed_rate: float,
                           entry_tag: Optional[str], side: str, **kwargs) -> float:
        return proposed_rate * 1.01

    # ==================== 新增：自定义卖出价格（当前价 -1%） ====================
    def custom_exit_price(self, pair: str, current_time: datetime, proposed_rate: float,
                          exit_tag: Optional[str], side: str, **kwargs) -> float:
        return proposed_rate * 0.99

    # ==================== 新增：每分钟检查信号并处理无交易时的订单 ====================
    def bot_loop_start(self, **kwargs) -> None:
        logger.info("执行检查信号并处理无交易时的订单")
        pair = 'BTC/USDT'
        coin = 'BTC'
        quote = 'USDT'
        total_coin_balance = self.wallets.get_total(coin)
        free_quote_balance = self.wallets.get_free(quote)
        # 假设最小下单金额，从配置中获取或硬编码
        min_stake = self.config.get('stake_min', 5.0)  # 如果配置中无，默认为5 USDT

        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if len(dataframe) == 0:
            return

        last_row = dataframe.iloc[-1]

        # 获取当前实时价格
        try:
            ticker = self.dp.ticker(pair)
            current_rate = ticker['last']
        except Exception as e:
            logger.error(f"Failed to get current rate: {e}")
            return

        # 检查开放交易
        open_trades = Trade.get_trades_proxy(is_open=True)
        has_open_trade = any(t.pair == pair for t in open_trades)

        # 卖出信号：如果有信号且有持仓且无开放交易，直接挂限价卖单
        if last_row.get('exit_long', 0) == 1 and total_coin_balance > 0 and not has_open_trade:
            logger.info("处理卖出信号")
            if total_coin_balance < 0.00001:
                logger.info(f"{coin} 可用于交易的数量为：{total_coin_balance}, 小于最小可买卖单位，本次忽略")
                return
            sell_price = current_rate * 0.99
            amount = total_coin_balance * 0.99  # 留一点防尘埃
            # 安全获取 exchange 实例
            try:
                exchange = self.dp._exchange
            except AttributeError:
                # 备选：直接用 self.exchange（某些版本有效）
                exchange = self.exchange

            # 留一点防尘埃
            try:
                order = exchange.create_order(
                    pair=pair,
                    ordertype='limit',
                    side='sell',
                    amount=amount,
                    rate=sell_price,
                    leverage=1.0
                )
                logger.info(
                    f"[bot_loop_start] 挂卖单成功: {amount:.8f} {coin} @ {sell_price:.2f}, order_id: {order.get('id')}")
                # 关键修复：每次循环前强制同步钱包余额（从交易所实时拉取）
                try:
                    self.wallets.update()  # ← 这行就是核心！
                    logger.debug("钱包余额已强制同步")
                except Exception as e:
                    logger.error(f"钱包同步失败: {e}")
                    # 可选：同步失败时直接返回，避免用旧数据下单
                    return
            except Exception as e:
                # 关键修复：每次循环前强制同步钱包余额（从交易所实时拉取）
                try:
                    self.wallets.update()  # ← 这行就是核心！
                    logger.debug("钱包余额已强制同步")
                except Exception as e:
                    logger.error(f"钱包同步失败: {e}")
                    # 可选：同步失败时直接返回，避免用旧数据下单
                    return
                logger.error(f"Failed to create sell order: {e}")
        # 买入信号：如果有信号且有资金且无开放交易，直接挂限价买单
        elif last_row.get('enter_long', 0) == 1 and not has_open_trade:
            logger.info("处理买入信号")
            # 先检查可用 quote 是否足够最小门槛
            if free_quote_balance < min_stake:
                logger.info(f"{quote} 可用余额为：{free_quote_balance:.2f}, 小于最小订单价值 {min_stake} USDT，本次忽略")
                return

            buy_price = current_rate * 1.01
            # 使用几乎全部可用余额，但留 0.1% 防尘埃/手续费
            amount = (free_quote_balance * 0.999) / buy_price

            # 检查计算出的 amount 是否满足最小币种数量
            if amount < 0.00001:
                logger.info(f"计算买入 {coin} 数量为：{amount:.8f}, 小于最小可买卖单位 0.00001 BTC，本次忽略")
                return

            # 可选：额外检查订单总价值（虽已检查余额，但以防价格波动）
            order_value = amount * buy_price
            if order_value < min_stake:
                logger.info(f"订单总价值 {order_value:.2f} USDT 小于最小门槛 {min_stake} USDT，本次忽略")
                return
            # 安全获取 exchange 实例
            try:
                exchange = self.dp._exchange
            except AttributeError:
                # 备选：直接用 self.exchange（某些版本有效）
                exchange = self.exchange
            try:
                order = exchange.create_order(
                    pair=pair,
                    ordertype='limit',
                    side='buy',
                    amount=amount,
                    rate=buy_price,
                    leverage=1.0
                )
                logger.info(
                    f"[bot_loop_start] 挂买单成功: {amount:.8f} {coin} @ {buy_price:.2f}, order_id: {order.get('id')}")
            except Exception as e:
                logger.error(f"Failed to create buy order: {e}")
            finally:
                # 无论成功或失败，都强制同步钱包
                try:
                    self.wallets.update()
                    logger.debug("钱包余额已强制同步")
                except Exception as sync_e:
                    logger.error(f"钱包同步失败: {sync_e}")
        else:
            logger.info("本次没有任何买入或卖信号，忽略处理")