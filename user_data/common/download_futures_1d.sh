#!/bin/bash
# 下载日线K线数据（合约）
# 时间范围: 最近2500天（约7年）

cd /opt/git/freqtrade

echo "========================================"
echo "下载日线数据（合约）"
echo "========================================"
echo "配置文件: futures.json"
echo "交易对: BTC, ETH, SOL, XRP, ADA, DOGE, SUI, TRX, ENA"
echo "时间范围: 最近2500天（约7年）"
echo "K线周期: 日线"
echo ""

python freqtrade/main.py download-data \
  -c user_data/common/futures.json \
  --timeframe 1d \
  --days 2500 \
  --trading-mode futures \
  --erase

echo ""
echo "日线数据下载完成！"
