#!/bin/bash
# 下载1小时K线数据（合约）
# 时间范围: 最近1095天（约3年）

cd /opt/git/freqtrade

echo "========================================"
echo "下载1小时数据（合约）"
echo "========================================"
echo "配置文件: futures.json"
echo "时间范围: 最近1095天（约3年）"
echo "K线周期: 1小时"
echo ""

python freqtrade/main.py download-data \
  -c user_data/common/futures.json \
  --timeframe 1h \
  --days 1095 \
  --trading-mode futures \
  --erase

echo ""
echo "1小时数据下载完成！"
