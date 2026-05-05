#!/bin/bash
# ========================================
# 下载1小时K线数据（最大历史范围）
# ========================================
# 配置文件: spot.json
# 交易对: BTC, ETH, SOL, XRP, ADA, DOGE, SUI, TRX, ENA
# 时间范围: 最近1095天（约3年）
# K线周期: 1小时
# 说明: 1小时数据适合高频策略开发
# ========================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FREQTRADE_ROOT="/opt/git/freqtrade"

cd "$FREQTRADE_ROOT"

echo "========================================"
echo "下载1小时数据（1095天 = 约3年）..."
echo "========================================"

python freqtrade/main.py download-data \
  -c user_data/common/spot.json \
  --timeframe 1h \
  --days 1095 \
  --trading-mode spot \
  --erase

echo ""
echo "========================================"
echo "1小时数据下载完成！"
echo "========================================"
