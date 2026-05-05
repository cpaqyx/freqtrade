#!/bin/bash
# 下载1小时K线数据（现货）
# 时间范围: 最近1095天（约3年）

cd /opt/git/freqtrade

echo "========================================"
echo "下载1小时数据（现货）"
echo "========================================"
echo "配置文件: spot.json"
echo "时间范围: 最近1095天（约3年）"
echo "K线周期: 1小时"
echo ""

python freqtrade/main.py download-data \
  -c user_data/common/spot.json \
  --timeframe 1h \
  --days 1095 \
  --trading-mode spot \
  --erase

echo ""
echo "1小时数据下载完成！"
