#!/bin/bash
# 下载5分钟K线数据（合约）
# 时间范围: 最近500天（约1.4年）

cd /opt/git/freqtrade

echo "========================================"
echo "下载5分钟数据（合约）"
echo "========================================"
echo "配置文件: futures.json"
echo "时间范围: 最近500天（约1.4年）"
echo "K线周期: 5分钟"
echo ""

python freqtrade/main.py download-data \
  -c user_data/common/futures.json \
  --timeframe 5m \
  --days 500 \
  --trading-mode futures \
  --erase

echo ""
echo "5分钟数据下载完成！"
