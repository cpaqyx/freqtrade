#!/usr/bin/env python3
"""
直接使用数据文件进行回测
"""
import pandas as pd
from pathlib import Path
from freqtrade.data.history import get_datahandler
from freqtrade.optimize.backtesting import Backtesting
from freqtrade.resolvers import StrategyResolver
from freqtrade.configuration import Configuration
import json

# 加载配置
config_file = '/opt/git/freqtrade/user_data/high_rate_sowing/config_backtest_A.json'
with open(config_file) as f:
    config = json.load(f)

# 设置回测参数
config['timerange'] = '20260323-20260523'
config['breakdown'] = ['day', 'week', 'month']
config['cache'] = 'none'

# 手动加载数据
data_dir = Path('/opt/git/freqtrade/user_data/data/binance')
pairs = ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT']

print("手动加载数据...")
data = {}
for pair in pairs:
    symbol = pair.replace('/', '_').replace(':', '_')
    file_path = data_dir / f"{symbol}-1m-futures.feather"

    if file_path.exists():
        df = pd.read_feather(file_path)
        df['date'] = pd.to_datetime(df['date'], utc=True)

        # 筛选时间范围
        mask = (df['date'] >= '2026-03-23') & (df['date'] <= '2026-05-23')
        df = df[mask]

        # 转换为Freqtrade期望的格式
        df = df.set_index('date')

        # 设置列名
        df.columns = ['open', 'high', 'low', 'close', 'volume']

        data[pair] = df
        print(f"  ✓ {pair}: {len(df)} 行")
    else:
        print(f"  ✗ {pair}: 文件不存在")

print(f"\n成功加载 {len(data)} 个交易对的数据")

# 保存数据到临时文件，让Freqtrade使用
print("\n保存数据为Freqtrade格式...")
dh = get_datahandler(data_dir)
for pair, df in data.items():
    df = df.reset_index()
    dh.ohlcv_store(pair, '1m', 'futures', df)
    print(f"  ✓ {pair}")

print("\n数据准备完成，现在可以运行回测了")
print(f"运行命令:")
print(f"  cd /opt/git/freqtrade && python -m freqtrade backtesting -c {config_file} --strategy HighRateSowing --timerange 20260323-20260523 --breakdown day week month --cache none")
