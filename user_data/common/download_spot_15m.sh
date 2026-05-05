#!/bin/bash
# 下载15分钟K线数据（现货）
# 时间范围: 最近730天（约2年）

cd /opt/git/freqtrade

echo "========================================"
echo "下载15分钟数据（现货）"
echo "========================================"
echo "配置文件: spot.json"
echo "时间范围: 最近730天（约2年）"
echo "K线周期: 15分钟"
echo ""

python freqtrade/main.py download-data \
  -c user_data/common/spot.json \
  --timeframe 15m \
  --days 730 \
  --trading-mode spot \
  --erase

echo ""
echo "15分钟数据下载完成！"
