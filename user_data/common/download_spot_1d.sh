#!/bin/bash
# 下载日线K线数据（现货）
# 时间范围: 最近2500天（约7年）

cd /opt/git/freqtrade

echo "========================================"
echo "下载日线数据（现货）"
echo "========================================"
echo "配置文件: spot.json"
echo "交易对: BTC, ETH, SOL, XRP, ADA, DOGE, SUI, TRX, ENA"
echo "时间范围: 最近2500天（约7年）"
echo "K线周期: 日线"
echo ""

python freqtrade/main.py download-data \
  -c user_data/common/spot.json \
  --timeframe 1d \
  --days 2500 \
  --trading-mode spot \
  --erase

echo ""
echo "日线数据下载完成！"
