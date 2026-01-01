import numpy as np


def kline_reverse_trend(close_prices, part_cnt=10, part_percent=0.09,
                        first_part_cnt=5, first_part_percent=0.05, debug=False):
    """
    基于反向遍历的K线趋势段识别算法
    从最后一根K线开始向前推移，识别趋势段

    参数:
        close_prices: 收盘价序列 (list/array)
        part_cnt: 可确认方向的K线数量，达到此数量可确定为一段 (默认8)
        part_percent: 达到多少涨跌幅度时可确定为一段 (默认0.05即5%)
        first_part_cnt: 第一段允许的最小K线数量 (默认5)
        first_part_percent: 第一段达到多少涨跌幅度时可确定为一段 (默认0.03即3%)
        debug: 是否输出调试信息 (默认False)

    返回:
        list[dict]: 趋势段列表，每个元素包含 line, k_cnt, start_price, end_price, max_price, min_price
    """
    prices = np.array(close_prices)
    n = len(prices)

    if n < 2:
        return []

    if debug:
        print(f"\n========== K线反向趋势分析 ==========")
        print(f"K线数: {n}")
        print(f"参数: part_cnt={part_cnt}, part_percent={part_percent * 100}%")
        print(f"      first_part_cnt={first_part_cnt}, first_part_percent={first_part_percent * 100}%")

    # 存放段的列表
    part_list = []

    # 已确认的元素序号
    fix_index = 0

    # 当前段的变量
    cur_part_direct = None  # 当前段的方向：up|down|flat
    cur_part_start_index = 0  # 当前段的起始序号（从后往前，所以是起始）
    cur_part_cnt = 0  # 当前段的累计K线数量
    cur_part_percent = 0
    cur_part_same_percent = 0.0  # 当前段遇到的正向百分比
    cur_part_same_cnt = 0  # 当前段同向K线数量

    # 反向段的变量
    next_part_direct = None
    next_part_cnt = 0  # 当前段遇到的反向K线数量
    next_part_percent = 0.0  # 当前段遇到的反向百分比
    next_part_start_index = 0

    # 当前方向是否变向
    cur_direct_changed = False

    # 从最后一根K线开始向前遍历
    for i in range(n - 1, 0, -1):
        # 计算当前K线相对于前一根K线的涨跌幅度
        percent = (prices[i] - prices[i - 1]) / prices[i - 1] if prices[i - 1] != 0 else 0
        cur_price = prices[i]

        # 第一根K线的初始化
        if cur_part_direct is None:
            if percent > 0:
                cur_part_direct = 'up'
            else:
                cur_part_direct = 'down'
            cur_part_start_index = i
            cur_part_cnt = 0
            cur_part_same_percent = 0
            cur_part_same_cnt = 0

            if debug:
                print(f"  初始化当前段: {cur_part_direct}")

        # 判断赋值操作
        if percent > 0:  # 上涨
            if cur_part_direct == 'up':
                # 同向，强化当前段
                if not cur_direct_changed:
                    cur_part_cnt += 1
                    cur_part_percent += percent
                cur_part_same_percent += percent
                cur_part_same_cnt += 1
            else:
                # 反向，累加到反向段
                cur_part_same_percent = 0
                next_part_percent += percent
                next_part_cnt += 1
                cur_direct_changed = True
                if next_part_direct is None:
                    next_part_direct = 'up'
                    next_part_start_index = i

        elif percent < 0:  # 下跌
            if cur_part_direct == 'down':
                # 同向，强化当前段
                if not cur_direct_changed:
                    cur_part_cnt += 1
                    cur_part_percent += abs(percent)
                cur_part_same_percent += abs(percent)
                cur_part_same_cnt += 1
            else:
                # 反向，累加到反向段
                cur_part_same_percent = 0
                next_part_percent += abs(percent)
                next_part_cnt += 1
                cur_direct_changed = True
                if next_part_direct is None:
                    next_part_direct = 'down'
                    next_part_start_index = i

        # 判断逻辑
        # (1) 如果同向力量大于反向力量，则反向段被吸收
        if cur_part_same_percent > abs(next_part_percent) and next_part_cnt > 0:
            if debug:
                print(f"  同向力量强，吸收反向段")
            cur_part_percent -= next_part_percent
            cur_part_same_percent = 0
            next_part_percent = 0.0
            cur_part_cnt += next_part_cnt
            next_part_cnt = 0
            cur_direct_changed = False
            next_part_direct = None
            next_part_start_index = 0

        # (2) 如果反向力量没有形成独立的段，继续遍历
        if (abs(next_part_percent) - cur_part_same_percent < part_percent) or (
                next_part_cnt + cur_part_same_cnt < part_cnt):
            continue

        # 添加段逻辑
        # (1) 如果是第一段
        if len(part_list) == 0:
            # (1.1) 第一段满足条件
            if cur_part_cnt >= first_part_cnt or cur_part_percent >= first_part_percent:
                # 根据索引范围计算k_cnt：从next_part_start_index+1到cur_part_start_index
                actual_k_cnt = cur_part_start_index - next_part_start_index
                start_p = prices[next_part_start_index]
                end_p = prices[cur_part_start_index]
                change = ((end_p - start_p) / start_p) if start_p != 0 else 0
                part = {
                    'line': cur_part_direct,
                    'angle': 0,
                    'k_cnt': actual_k_cnt,
                    'start_price': start_p,  # 时间最早的价格
                    'end_price': end_p,  # 时间最晚的价格
                    'max_price': max(start_p, end_p),
                    'min_price': min(start_p, end_p),
                    'change': change
                }
                part_list.append(part)

                # 设置当前段
                cur_part_direct = next_part_direct
                cur_part_start_index = next_part_start_index
                cur_part_cnt = next_part_cnt + cur_part_same_cnt
                cur_part_percent = abs(next_part_percent) - cur_part_same_percent
                cur_part_same_percent = 0.0
                cur_part_same_cnt = 0

                # 重置下一段
                next_part_direct = None
                next_part_cnt = 0
                next_part_percent = 0.0
                next_part_start_index = 0

            # (1.2) 第一段不满足条件，合并到反向段
            else:
                # 设置当前段
                cur_part_direct = next_part_direct
                cur_part_cnt = cur_part_cnt + next_part_cnt + cur_part_same_cnt
                cur_part_percent = cur_part_percent + abs(next_part_percent) - cur_part_same_percent
                cur_part_same_percent = 0.0
                cur_part_same_cnt = 0

                # 重置下一段
                next_part_direct = None
                next_part_cnt = 0
                next_part_percent = 0.0
                next_part_start_index = 0

        # (2) 如果不是第一段
        else:
            # 根据索引范围计算k_cnt：不包含起点（起点是上一段的终点）
            actual_k_cnt = cur_part_start_index - next_part_start_index
            start_p = prices[next_part_start_index]
            end_p = prices[cur_part_start_index]
            change = ((end_p - start_p) / start_p) if start_p != 0 else 0
            part = {
                'line': cur_part_direct,
                'angle': 0,
                'k_cnt': actual_k_cnt,
                'start_price': start_p,  # 时间最早的价格
                'end_price': end_p,  # 时间最晚的价格
                'max_price': max(start_p, end_p),
                'min_price': min(start_p, end_p),
                'change': change
            }
            part_list.append(part)

            # 设置当前段
            cur_part_direct = next_part_direct
            cur_part_start_index = next_part_start_index
            cur_part_cnt = next_part_cnt + cur_part_same_cnt
            cur_part_percent = abs(next_part_percent) - cur_part_same_percent
            cur_part_same_percent = 0.0
            cur_part_same_cnt = 0

            # 重置下一段
            next_part_direct = None
            next_part_cnt = 0
            next_part_percent = 0.0
            next_part_start_index = 0

    # 遍历结束，添加剩余的段
    # 1. 添加当前段
    if next_part_direct is not None and next_part_cnt > 0:
        # 有相反段：当前段从next_part_start_index到cur_part_start_index
        if len(part_list) == 0:
            # 第一段
            actual_k_cnt = cur_part_start_index - next_part_start_index
        else:
            # 非第一段
            actual_k_cnt = cur_part_start_index - next_part_start_index
        start_p = prices[next_part_start_index]
        end_p = prices[cur_part_start_index]
        change = ((end_p - start_p) / start_p) if start_p != 0 else 0
        part = {
            'line': cur_part_direct,
            'angle': 0,
            'k_cnt': actual_k_cnt,
            'start_price': start_p,
            'end_price': end_p,
            'max_price': max(start_p, end_p),
            'min_price': min(start_p, end_p),
            'change': change
        }
        part_list.append(part)

        # 2. 添加相反段（从索引0到next_part_start_index）
        actual_k_cnt = next_part_start_index + 1
        start_p = prices[0]
        end_p = prices[next_part_start_index]
        change = ((end_p - start_p) / start_p) if start_p != 0 else 0
        part = {
            'line': next_part_direct,
            'angle': 0,
            'k_cnt': actual_k_cnt,
            'start_price': start_p,  # 时间最早的价格（索引0）
            'end_price': end_p,
            'max_price': max(start_p, end_p),
            'min_price': min(start_p, end_p),
            'change': change
        }
        part_list.append(part)
    else:
        # 没有相反段：当前段从索引0到cur_part_start_index
        actual_k_cnt = cur_part_start_index + 1
        start_p = prices[0]
        end_p = prices[cur_part_start_index]
        change = ((end_p - start_p) / start_p) if start_p != 0 else 0
        part = {
            'line': cur_part_direct,
            'angle': 0,
            'k_cnt': actual_k_cnt,
            'start_price': start_p,  # 时间最早的价格（索引0）
            'end_price': end_p,  # 时间最晚的价格
            'max_price': max(start_p, end_p),
            'min_price': min(start_p, end_p),
            'change': change
        }
        part_list.append(part)

    # 反转列表（因为是从后往前遍历的）
    part_list.reverse()

    # 验证k_cnt总和
    total_k_cnt = sum([p['k_cnt'] for p in part_list])

    if debug:
        print(f"\n========== 最终结果 ({len(part_list)}段) ==========")
        print(f"K线总数: {n}, k_cnt总和: {total_k_cnt} (期望: {n})")
        for idx, p in enumerate(part_list):
            change_pct = p['change'] * 100
            print(f"{idx}: {p['line']:5s} | {p['k_cnt']:3d}根 | 角度:{p['angle']:6.2f}° | 涨跌:{change_pct:+6.2f}% | "
                  f"{p['start_price']:.2f}→{p['end_price']:.2f} | 区间:[{p['min_price']:.2f}, {p['max_price']:.2f}]")

    return part_list


if __name__ == '__main__':
    # 测试示例
    test_prices = [100, 105, 110, 115, 120, 118, 116, 114, 112, 110,
                   115, 120, 125, 130, 128, 126, 124, 122, 120, 118]

    print("测试数据:", test_prices)
    result = kline_reverse_trend(test_prices, debug=True)

    print("\n最终输出:")
    for i, part in enumerate(result):
        print(f"段{i}: {part}")

