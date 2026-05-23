#!/bin/bash
# HighRateSowing 策略启动脚本（实盘/模拟运行）
# 参考 /opt/git/freqtrade/user_data/btc_account/start_live.bat

set -e

# 配置
STRATEGY_NAME="HighRateSowing"
STRATEGY_DIR="/opt/git/freqtrade/user_data/high_rate_sowing"
STRATEGY_FILE="${STRATEGY_DIR}/${STRATEGY_NAME}.py"
CONFIG_FILE="${STRATEGY_DIR}/config.json"
STRATEGIES_DIR="/opt/git/freqtrade/user_data/strategies"
FREQTRADE_DIR="/opt/git/freqtrade"
LOG_DIR="${STRATEGY_DIR}/logs"

# 创建日志目录
mkdir -p "${LOG_DIR}"

# 日志文件
LOG_FILE="${LOG_DIR}/trading_$(date +%Y%m%d).log"

echo "=== HighRateSowing 启动脚本 ==="
echo "时间: $(date)"
echo ""

# 1. 复制策略文件到 strategies 目录
echo "[步骤1] 复制策略文件..."
cp "${STRATEGY_FILE}" "${STRATEGIES_DIR}/${STRATEGY_NAME}.py"
echo "  ✅ 已复制: ${STRATEGY_FILE} -> ${STRATEGIES_DIR}/${STRATEGY_NAME}.py"
echo ""

# 2. 进入 freqtrade 目录
cd "${FREQTRADE_DIR}"

# 3. 启动交易机器人
echo "[步骤2] 启动交易机器人..."
echo "  配置文件: ${CONFIG_FILE}"
echo "  策略: ${STRATEGY_NAME}"
echo "  日志文件: ${LOG_FILE}"
echo ""

freqtrade trade \
    --config "${CONFIG_FILE}" \
    --strategy "${STRATEGY_NAME}" \
    --logfile "${LOG_FILE}" \
    $@
