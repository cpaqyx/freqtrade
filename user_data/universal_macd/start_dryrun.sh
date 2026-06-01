#!/bin/bash
# 实盘启动脚本 - UniversalMACD策略

cd /opt/git/freqtrade

echo "=== 启动 UniversalMACD 实盘dry-run ==="
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "策略: UniversalMACD"
echo "交易对: BTC/USDT:USDT, ETH/USDT:USDT, SOL/USDT:USDT"
echo ""

# 检查配置文件
if [ ! -f "user_data/universal_macd/config.json" ]; then
    echo "❌ 配置文件不存在"
    exit 1
fi

# 启动dry-run
freqtrade trade -c user_data/universal_macd/config.json --dry-run
