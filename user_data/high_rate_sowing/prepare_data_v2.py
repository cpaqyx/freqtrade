#!/usr/bin/env python3
"""
直接使用数据文件进行回测 - 修正版
"""
import pandas as pd
from pathlib import Path
from freqtrade.data.history.history_utils import refresh_backtest_ohlcv_data
from freqtrade.enums import CandleType
import json

# 加载配置
config_file = '/opt/git/freqtrade/user_data/high_rate_sowing/config_backtest_A.json'
with open(config_file) as f:
    config = json.load(f)

# 手动加载数据
data_dir = Path('/opt/git/freqtrade/user_data/data/binance')
pairs = ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT']

print("手动加载数据...")
data_frames = {}
for pair in pairs:
    symbol = pair.replace('/', '_').replace(':', '_')
    file_path = data_dir / f"{symbol}-1m-futures.feather"

    if file_path.exists():
        df = pd.read_feather(file_path)
        df['date'] = pd.to_datetime(df['date'], utc=True)

        # 筛选时间范围
        mask = (df['date'] >= '2026-03-23') & (df['date'] <= '2026-05-23')
        df = df[mask]

        data_frames[pair] = df
        print(f"  ✓ {pair}: {len(df)} 行")
    else:
        print(f"  ✗ {pair}: 文件不存在")

print(f"\n成功加载 {len(data_frames)} 个交易对的数据")

# 使用Freqtrade的方法存储数据
print("\n使用Freqtrade方法存储数据...")
from freqtrade.data.history import get_datahandler

dh = get_datahandler(data_dir)

for pair, df in data_frames.items():
    # 使用正确的CandleType
    candle_type = CandleType.FUTURES

    # 存储数据
    dh.ohlcv_store(pair, '1m', candle_type, df)
    print(f"  ✓ {pair}")

print("\n数据准备完成！")

# 验证数据是否可以被加载
print("\n验证数据加载...")
for pair in pairs:
    data = dh.ohlcv_load(pair, '1m', candle_type, timerange='20260323-20260523')
    if data is not None and len(data) > 0:
        print(f"  ✓ {pair}: {len(data)} 行")
    else:
        print(f"  ✗ {pair}: 未加载到数据")