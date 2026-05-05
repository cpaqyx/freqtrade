#!/bin/bash
# ========================================
# 下载日线K线数据（最大历史范围）
# ========================================
# 配置文件: spot.json
# 交易对: BTC, ETH, SOL, XRP, ADA, DOGE, SUI, TRX, ENA
# 时间范围: 最近2500天（约7年）
# K线周期: 日线
# 说明: 日线数据量小，2500天约为API支持的最大范围
#
# 注意: 使用 --erase 参数将删除现有数据并重新下载完整数据
# ========================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FREQTRADE_ROOT="/opt/git/freqtrade"

cd "$FREQTRADE_ROOT"

echo "========================================"
echo "下载日线数据（2500天 = 约7年）..."
echo "========================================"

python freqtrade/main.py download-data \
  -c user_data/common/spot.json \
  --timeframe 1d \
  --days 2500 \
  --trading-mode spot \
  --erase

echo ""
echo "========================================"
echo "日线数据下载完成！"
echo "========================================"
