#!/bin/bash
# BTC Rebound Volume Strategy - 完整运行流程
# 
# 流程：回测 → 参数优化 → 应用最优参数 → 实盘配置

set -e

PROJECT_DIR="/opt/git/freqtrade"
STRATEGY_DIR="user_data/btc_0603"
CONFIG_DRYRUN="$STRATEGY_DIR/config_dryrun.json"
CONFIG_LIVE="$STRATEGY_DIR/config_live.json"

cd "$PROJECT_DIR"

echo "=================================================="
echo "BTC Rebound Volume Strategy - 完整运行流程"
echo "=================================================="
echo ""

# 检查策略语法
echo "【步骤1】检查策略语法..."
freqtrade list-strategies --strategy-path "$STRATEGY_DIR" | grep BTC_Rebound_Volume_Strategy
echo "✅ 策略语法正确"
echo ""

# 回测（最近1个月）
echo "【步骤2】运行回测（最近1个月）..."
freqtrade backtesting \
    --strategy BTC_Rebound_Volume_Strategy \
    --strategy-path "$STRATEGY_DIR" \
    --config "$CONFIG_DRYRUN" \
    --timeframe 1m \
    --timerange 20260501-20260521

echo ""
echo "【步骤3】参数优化（后台运行）..."
echo "使用命令查看进度: tail -f /tmp/hyperopt_output.txt"
echo ""

# 显示最优参数
echo "【步骤4】查看优化结果..."
freqtrade hyperopt-show --config "$CONFIG_DRYRUN" --best 2>&1 | head -50

echo ""
echo "=================================================="
echo "流程完成！"
echo ""
echo "后续步骤："
echo "1. 查看优化结果: freqtrade hyperopt-show --best"
echo "2. 将最优参数应用到配置文件"
echo "3. 运行 dry-run 模式测试"
echo "4. 确认无误后启动实盘"
echo "=================================================="