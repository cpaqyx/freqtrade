#!/bin/bash
# HighRateSowing 回测脚本
# 用法: ./run_backtest.sh [timerange] [strategy_params]
# 示例: ./run_backtest.sh 20260322-20260522

set -e

# 配置
CONFIG="/opt/git/freqtrade/user_data/high_rate_sowing/config.json"
STRATEGY="HighRateSowing"
DATADIR="/opt/git/freqtrade/user_data/data/binance"
LOGDIR="/opt/git/freqtrade/user_data/high_rate_sowing/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 参数
TIMERANGE=${1:-"20260322-20260522"}
EXTRA_PARAMS=${2:-""}

# 日志文件
LOGFILE="${LOGDIR}/backtest_${TIMESTAMP}.log"

echo "========================================" | tee -a $LOGFILE
echo "HighRateSowing 回测" | tee -a $LOGFILE
echo "时间范围: $TIMERANGE" | tee -a $LOGFILE
echo "开始时间: $(date)" | tee -a $LOGFILE
echo "========================================" | tee -a $LOGFILE

# 执行回测
cd /opt/git/freqtrade
freqtrade backtesting \
    --config $CONFIG \
    --strategy $STRATEGY \
    --datadir $DATADIR \
    --timerange=$TIMERANGE \
    --cache none \
    $EXTRA_PARAMS \
    2>&1 | tee -a $LOGFILE

echo "" | tee -a $LOGFILE
echo "回测完成: $(date)" | tee -a $LOGFILE
