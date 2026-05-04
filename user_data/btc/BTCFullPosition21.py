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
from user_data.common.line_format import kline_reverse_trend


from freqtrade.strategy import IStrategy

logger = logging.getLogger(__name__)


class BTCFullPosition(IStrategy):
    """
    BTC全仓策略
    - 日线级别
    - 只做多
    - 全仓进出
    - 基于90日图形分析
    """
    
    INTERFACE_VERSION = 3
    
    # 策略参数
    timeframe = '1d'
    can_short = False
    startup_candle_count = 100  # 至少需要90根K线
    
    # 全仓配置
    position_adjustment_enable = False
    
    # ROI和止损（设置为极端值，由策略信号控制）
    minimal_roi = {
        "0": 10.0  # 1000%，实际由策略信号控制
    }
    stoploss = -0.99  # 极端止损，由策略信号控制
    
    # 策略参数
    max_drop_from_high = 0.25  # 从最高点跌25%触发建仓
    day_rise_threshold = 0.02  # 单日涨幅2%
    continuous_rise_threshold = 0.03  # 连续涨幅3%
    day_drop_threshold = 0.02  # 单日跌幅2%
    continuous_drop_threshold = 0.03  # 连续跌幅3%
    pattern_drop_threshold = 0.10  # 图形下跌10%
    double_top_threshold = 0.05  # 双顶差距5%（建仓用）
    double_top_higher_threshold = 0.03  # 双顶A比B高的阈值3%（平仓用）
    double_top_lower_threshold = 0.05  # 双顶A比B低的阈值5%（平仓用）
    last_down_threshold = 0.05  # 最后一段down的跌幅阈值5%
    
    def __init__(self, config: dict) -> None:
        super().__init__(config)
        logger.info("✅ BTC全仓策略已初始化")
    
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
            if diff_higher <= self.double_top_higher_threshold:
                logger.info(f"📉 平仓信号{segment_name}-AB: A比B高{diff_higher:.2%} (A={price_a:.2f}, B={price_b:.2f})")
                return True
        else:
            # A比B低的情况
            diff_lower = (price_b - price_a) / price_b
            if diff_lower <= self.double_top_lower_threshold:
                logger.info(f"📉 平仓信号{segment_name}-AB: A比B低{diff_lower:.2%} (A={price_a:.2f}, B={price_b:.2f})")
                return True
        
        # 如果AB不成立，比较A与第二个前面的up段C
        if len(up_segments) >= 2:
            price_c = up_segments[1]['max_price']
            
            if price_a >= price_c:
                # A比C高的情况
                diff_higher = (price_a - price_c) / price_c
                if diff_higher <= self.double_top_higher_threshold:
                    logger.info(f"📉 平仓信号{segment_name}-AC: A比C高{diff_higher:.2%} (A={price_a:.2f}, C={price_c:.2f})")
                    return True
            else:
                # A比C低的情况
                diff_lower = (price_c - price_a) / price_c
                if diff_lower <= self.double_top_lower_threshold:
                    logger.info(f"📉 平仓信号{segment_name}-AC: A比C低{diff_lower:.2%} (A={price_a:.2f}, C={price_c:.2f})")
                    return True
        
        return False
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
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
            close_prices_90 = dataframe['close'].iloc[i-89:i+1].values  # 最近90根（包括当前）
            try:
                pattern = kline_reverse_trend(close_prices_90)
                dataframe.at[dataframe.index[i], 'pattern'] = str(pattern)  # 转为字符串存储
            except Exception as e:
                logger.warning(f"计算图形指标失败 {dataframe.index[i]}: {e}")
                dataframe.at[dataframe.index[i], 'pattern'] = '[]'
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        建仓条件
        """
        conditions = []
        
        # 条件1：从最高点跌25%，直接建仓
        condition_1 = (
            (dataframe['close'] <= dataframe['max_90'] * (1 - self.max_drop_from_high))
        )
        
        # 条件2：当天涨幅>2% 或 连续上涨>3%，并满足图形条件
        # 2.1 单日涨幅>2%
        single_day_rise = (dataframe['day_change'] > self.day_rise_threshold)
        
        # 2.2 连续上涨>3%（计算最近3天的累计涨幅）
        dataframe['rise_3d'] = (
            (dataframe['close'] - dataframe['close'].shift(3)) / dataframe['close'].shift(3)
        )
        continuous_rise = (
            (dataframe['is_green'] == 1) &
            (dataframe['is_green'].shift(1) == 1) &
            (dataframe['is_green'].shift(2) == 1) &
            (dataframe['rise_3d'] > self.continuous_rise_threshold)
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
                pattern = eval(pattern_str)  # 将字符串转回list
                if not pattern or len(pattern) == 0:
                    continue
                
                # 检查图形条件
                # 条件2.1：最后1个为up/flat，倒数第二为down且跌幅>10%
                if len(pattern) >= 2:
                    last = pattern[-1]
                    second_last = pattern[-2]
                    
                    if last['line'] in ['up', 'flat'] and second_last['line'] == 'down':
                        drop_pct = abs((second_last['end_price'] - second_last['start_price']) / second_last['start_price'])
                        if drop_pct > self.pattern_drop_threshold:
                            dataframe.at[dataframe.index[i], 'pattern_entry_signal'] = True
                            logger.info(f"📈 条件2.1满足: 最后up/flat，倒数第二down跌{drop_pct:.1%}")
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
                                drop_pct = abs((third_last['end_price'] - third_last['start_price']) / third_last['start_price'])
                                if drop_pct > self.pattern_drop_threshold:
                                    dataframe.at[dataframe.index[i], 'pattern_entry_signal'] = True
                                    logger.info(f"📈 条件2.2满足(flat): 倒数第三down跌{drop_pct:.1%}")
                                    continue
                        
                        # 倒数第二为up但k_cnt<2且涨幅不超过5%
                        elif second_last['line'] == 'up' and second_last['k_cnt'] < 2:
                            rise_pct = abs((second_last['end_price'] - second_last['start_price']) / second_last['start_price'])
                            if rise_pct <= 0.05:
                                if third_last['line'] == 'down':
                                    drop_pct = abs((third_last['end_price'] - third_last['start_price']) / third_last['start_price'])
                                    if drop_pct > self.pattern_drop_threshold:
                                        dataframe.at[dataframe.index[i], 'pattern_entry_signal'] = True
                                        logger.info(f"📈 条件2.2满足(小up): 倒数第三down跌{drop_pct:.1%}")
                                        continue
                
            except Exception as e:
                logger.warning(f"解析图形指标失败 {dataframe.index[i]}: {e}")
        
        condition_2 = rise_condition & dataframe['pattern_entry_signal']
        
        # 最终建仓条件
        dataframe.loc[condition_1 | condition_2, 'enter_long'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        平仓条件：
        1. 当天跌幅为负且跌幅>2% 或 连续下跌>3%
        2. 分析图形指标检测双顶形态
        """
        # 条件1：当天跌幅为负且跌幅>2% 或 连续下跌>3%
        # 1.1 单日跌幅>2%（当天涨幅为负）
        single_day_drop = (dataframe['day_change'] < -self.day_drop_threshold)
        
        # 1.2 连续下跌>3%（计算最近3天的累计跌幅）
        dataframe['drop_3d'] = (
            (dataframe['close'] - dataframe['close'].shift(3)) / dataframe['close'].shift(3)
        )
        continuous_drop = (
            (dataframe['is_red'] == 1) &
            (dataframe['is_red'].shift(1) == 1) &
            (dataframe['is_red'].shift(2) == 1) &
            (dataframe['drop_3d'] < -self.continuous_drop_threshold)
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
                pattern = eval(pattern_str)
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
                    
                    if drop_pct <= self.last_down_threshold:
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
                
            except Exception as e:
                logger.warning(f"解析图形指标失败 {dataframe.index[i]}: {e}")
        
        # 最终平仓条件
        dataframe.loc[drop_condition & dataframe['pattern_exit_signal'], 'exit_long'] = 1
        
        return dataframe


