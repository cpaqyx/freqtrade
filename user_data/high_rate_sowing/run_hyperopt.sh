#!/bin/bash
# HighRateSowing Hyperopt 参数优化脚本
# 用法: ./run_hyperopt.sh [timerange] [epochs] [spaces] [min_trades]
# 示例: ./run_hyperopt.sh 20260322-20260522 15000 "buy sell roi stoploss" 100

set -e

# 配置
CONFIG="/opt/git/freqtrade/user_data/high_rate_sowing/config.json"
STRATEGY="HighRateSowing"
DATADIR="/opt/git/freqtrade/user_data/data/binance"
LOGDIR="/opt/git/freqtrade/user_data/high_rate_sowing/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 参数
TIMERANGE=${1:-"20260322-20260522"}
EPOCHS=${2:-15000}
SPACES=${3:-"buy sell roi stoploss"}
MIN_TRADES=${4:-100}

# 日志文件
LOGFILE="${LOGDIR}/hyperopt_${TIMESTAMP}.log"
RESULTS_FILE="${LOGDIR}/hyperopt_results_${TIMESTAMP}.json"

echo "========================================" | tee -a $LOGFILE
echo "HighRateSowing Hyperopt 参数优化" | tee -a $LOGFILE
echo "时间范围: $TIMERANGE" | tee -a $LOGFILE
echo "Epochs: $EPOCHS" | tee -a $LOGFILE
echo "Spaces: $SPACES" | tee -a $LOGFILE
echo "最小交易次数: $MIN_TRADES" | tee -a $LOGFILE
echo "开始时间: $(date)" | tee -a $LOGFILE
echo "========================================" | tee -a $LOGFILE

# 执行 hyperopt
cd /opt/git/freqtrade
freqtrade hyperopt \
    --config $CONFIG \
    --strategy $STRATEGY \
    --datadir $DATADIR \
    --timerange=$TIMERANGE \
    --epochs $EPOCHS \
    --spaces $SPACES \
    --hyperopt-loss SharpeHyperOptLoss \
    --min-trades $MIN_TRADES \
    --random-state 42 \
    --cache none \
    --job-workers 1 \
    2>&1 | tee -a $LOGFILE

echo "" | tee -a $LOGFILE
echo "Hyperopt 完成: $(date)" | tee -a $LOGFILE
