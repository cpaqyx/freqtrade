#!/bin/bash

echo "========================================"
echo "BTC全仓策略 - 账号2实盘启动 (Linux版)"
echo "========================================"
echo ""

# 切换到项目根目录
cd /opt/git/freqtrade/ || { echo "❌ 无法切换到项目目录"; exit 1; }

CONFIG_FILE="user_data/btc_account2_alone_cp/config_live.json"
STRATEGY_FILE="user_data/btc_account2_alone_cp/BTCFullPosition2_2.py"
STRATEGY_JSON="user_data/btc_account2_alone_cp/BTCFullPosition2_2.json"
STRATEGY_NAME="BTCFullPosition2_2"

# 检查配置文件
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ 错误：未找到配置文件 $CONFIG_FILE"
    exit 1
fi

# 检查并复制策略文件
if [ -f "$STRATEGY_FILE" ]; then
    echo "✓ 找到策略文件: $STRATEGY_FILE"
    cp -f "$STRATEGY_FILE" "user_data/strategies/BTCFullPosition2_2.py"
    echo "✓ 已复制策略文件到 strategies 目录"
else
    echo "⚠️  警告：未找到策略文件 $STRATEGY_FILE，将尝试使用默认策略"
fi

# 检查并复制策略参数文件
if [ -f "$STRATEGY_JSON" ]; then
    echo "✓ 找到参数文件: $STRATEGY_JSON"
    cp -f "$STRATEGY_JSON" "user_data/strategies/BTCFullPosition2_2.json"
    echo "✓ 已复制参数文件到 strategies 目录"
else
    echo "⚠️  警告：未找到参数文件，将使用代码默认参数"
fi

# 检查是否为实盘模式
if grep -q '"dry_run": false' "$CONFIG_FILE"; then
    MODE="实盘"
    echo "⚠️⚠️⚠️ 实盘模式 - 将执行真实交易 ⚠️⚠️⚠️"
else
    MODE="模拟盘"
    echo "✓ 模拟盘模式 - 不执行真实交易"
fi

echo ""
echo "策略: $STRATEGY_NAME"
echo "币种: BTC/USDT"
echo "模式: $MODE"
echo "配置: $CONFIG_FILE"
if [ -f "$STRATEGY_JSON" ]; then
    echo "参数: $STRATEGY_JSON (独立参数)"
else
    echo "参数: 使用代码默认值"
fi
echo "API端口: 8092"
echo ""

# 创建日志目录
mkdir -p "user_data/logs"

# 启动交易
echo ""
echo "正在启动策略..."
echo "按 Ctrl+C 可停止运行"
echo ""

/opt/myenv/bin/python -m freqtrade trade \
  --config "$CONFIG_FILE" \
  --strategy "$STRATEGY_NAME" \
  --strategy-path "user_data/strategies" \
  --logfile "user_data/logs/btc_account2_alone_cp.log"

echo ""
echo "策略已停止"
