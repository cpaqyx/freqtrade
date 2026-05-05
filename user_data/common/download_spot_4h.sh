#!/bin/bash
# 下载4小时K线数据（现货）
# 时间范围: 最近1825天（约5年）

cd /opt/git/freqtrade

echo "========================================"
echo "下载4小时数据（现货）"
echo "========================================"
echo "配置文件: spot.json"
echo "时间范围: 最近1825天（约5年）"
echo "K线周期: 4小时"
echo ""

python freqtrade/main.py download-data \
  -c user_data/common/spot.json \
  --timeframe 4h \
  --days 1825 \
  --trading-mode spot \
  --erase

echo ""
echo "4小时数据下载完成！"
