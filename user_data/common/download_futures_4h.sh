#!/bin/bash
# 下载4小时K线数据（合约）
# 时间范围: 最近1825天（约5年）

cd /opt/git/freqtrade

echo "========================================"
echo "下载4小时数据（合约）"
echo "========================================"
echo "配置文件: futures.json"
echo "时间范围: 最近1825天（约5年）"
echo "K线周期: 4小时"
echo ""

python freqtrade/main.py download-data \
  -c user_data/common/futures.json \
  --timeframe 4h \
  --days 1825 \
  --trading-mode futures \
  --erase

echo ""
echo "4小时数据下载完成！"
