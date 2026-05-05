#!/bin/bash
# ========================================
# 下载5分钟K线数据（最大历史范围）
# ========================================
# 配置文件: spot.json / futures.json
# 时间范围: 最近500天（约1.4年）
# K线周期: 5分钟
# 说明: 5分钟数据量大，500天约为API支持的最大范围
# ========================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FREQTRADE_ROOT="/opt/git/freqtrade"

cd "$FREQTRADE_ROOT"

echo "========================================"
echo "下载5分钟数据（500天 = 约1.4年）..."
echo "========================================"

python freqtrade/main.py download-data \
  -c user_data/common/spot.json \
  --timeframe 5m \
  --days 500 \
  --trading-mode spot \
  --erase

echo ""
echo "========================================"
echo "5分钟数据下载完成！"
echo "========================================"
