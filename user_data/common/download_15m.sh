#!/bin/bash
# ========================================
# 下载15分钟K线数据（最大历史范围）
# ========================================
# 配置文件: spot.json
# 时间范围: 最近730天（约2年）
# K线周期: 15分钟
# ========================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FREQTRADE_ROOT="/opt/git/freqtrade"

cd "$FREQTRADE_ROOT"

echo "========================================"
echo "下载15分钟数据（730天 = 约2年）..."
echo "========================================"

python freqtrade/main.py download-data \
  -c user_data/common/spot.json \
  --timeframe 15m \
  --days 730 \
  --trading-mode spot \
  --erase

echo ""
echo "========================================"
echo "15分钟数据下载完成！"
echo "========================================"
