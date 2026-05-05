#!/bin/bash
# ========================================
# 下载4小时K线数据（最大历史范围）
# ========================================
# 配置文件: spot.json
# 时间范围: 最近1825天（约5年）
# K线周期: 4小时
# ========================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FREQTRADE_ROOT="/opt/git/freqtrade"

cd "$FREQTRADE_ROOT"

echo "========================================"
echo "下载4小时数据（1825天 = 约5年）..."
echo "========================================"

python freqtrade/main.py download-data \
  -c user_data/common/spot.json \
  --timeframe 4h \
  --days 1825 \
  --trading-mode spot \
  --erase

echo ""
echo "========================================"
echo "4小时数据下载完成！"
echo "========================================"
