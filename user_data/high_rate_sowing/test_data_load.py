#!/usr/bin/env python3
"""
测试Freqtrade数据加载
"""
from freqtrade.data.history import get_datahandler
from pathlib import Path
import pandas as pd

# 数据目录
data_dir = Path('/opt/git/freqtrade/user_data/data/binance')
dh = get_datahandler(data_dir)

# 测试加载合约数据
pairs = ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT']
timeframe = '1m'
timerange = '20260323-20260523'

print("=" * 60)
print("测试Freqtrade数据加载")
print("=" * 60)

for pair in pairs:
    print(f"\n测试 {pair}:")

    # 尝试加载
    try:
        data = dh.ohlcv_load(pair, timeframe, 'futures', timerange=timerange)
        if data is not None and len(data) > 0:
            print(f"  ✓ 成功加载 {len(data)} 行数据")
        else:
            print(f"  ✗ 未加载到数据")
    except Exception as e:
        print(f"  ✗ 错误: {e}")

# 检查文件
print("\n" + "=" * 60)
print("检查数据文件")
print("=" * 60)

for pair in pairs:
    # 转换交易对格式: BTC/USDT:USDT -> BTC_USDT_USDT
    symbol = pair.replace('/', '_').replace(':', '_')
    pattern = f"{symbol}-{timeframe}-futures.feather"
    file_path = data_dir / pattern

    if file_path.exists():
        df = pd.read_feather(file_path)
        print(f"\n{pattern}:")
        print(f"  行数: {len(df)}")
        print(f"  时间: {df['date'].min()} 到 {df['date'].max()}")
    else:
        print(f"\n{pattern}: 文件不存在")

        # 查找可能的文件
        possible_files = list(data_dir.glob(f"{symbol.split('_')[0]}*{timeframe}*futures*.feather"))
        if possible_files:
            print(f"  可能的文件:")
            for f in possible_files:
                print(f"    - {f.name}")
