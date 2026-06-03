#!/bin/bash
# BTC Rebound Volume Strategy - 运行脚本
# 
# 作者: OpenClaw AI
# 日期: 2026-06-03

set -e

# 项目根目录
PROJECT_DIR="/opt/git/freqtrade"
cd "$PROJECT_DIR"

# 策略目录
STRATEGY_DIR="user_data/btc_0603"

# ==================== 函数定义 ====================

# 显示帮助信息
show_help() {
    echo "=================================================="
    echo "BTC Rebound Volume Strategy 运行脚本"
    echo "=================================================="
    echo ""
    echo "用法: $0 <命令> [参数]"
    echo ""
    echo "命令:"
    echo "  dryrun       - 模拟运行（dry-run mode）"
    echo "  live         - 实盘运行（live trading）"
    echo "  backtest     - 回测"
    echo "  test         - 测试策略语法"
    echo "  show-trades  - 显示交易记录"
    echo "  help         - 显示此帮助信息"
    echo ""
    echo "参数:"
    echo "  --timerange  - 回测时间范围（格式：20240101-20240601）"
    echo "  --details    - 显示详细交易信息"
    echo ""
    echo "示例:"
    echo "  $0 dryrun                   # 启动模拟运行"
    echo "  $0 backtest --timerange 20250501-20250601  # 回测5月数据"
    echo "  $0 test                     # 测试策略语法"
    echo ""
    echo "=================================================="
}

# 测试策略语法
test_strategy() {
    echo "=================================================="
    echo "测试策略语法..."
    echo "=================================================="
    
    freqtrade test-strategy \
        --strategy BTC_Rebound_Volume_Strategy \
        --strategy-path "$STRATEGY_DIR" \
        --config "$STRATEGY_DIR/config_dryrun.json"
    
    echo "✅ 策略语法测试完成"
}

# 模拟运行
run_dryrun() {
    echo "=================================================="
    echo "启动模拟运行（Dry-Run Mode）"
    echo "=================================================="
    echo ""
    echo "配置信息:"
    echo "  - 交易模式: Futures (永续合约)"
    echo "  - 交易对: BTC/USDT:USDT"
    echo "  - 模拟钱包: 10000 USDT"
    echo "  - 杠杆: 20x"
    echo "  - 仓位比例: 20%"
    echo ""
    echo "=================================================="
    
    freqtrade trade \
        --strategy BTC_Rebound_Volume_Strategy \
        --strategy-path "$STRATEGY_DIR" \
        --config "$STRATEGY_DIR/config_dryrun.json" \
        --dry-run
}

# 实盘运行
run_live() {
    echo "=================================================="
    echo "⚠️  启动实盘运行（Live Trading Mode）"
    echo "=================================================="
    echo ""
    echo "⚠️  警告: 实盘模式将使用真实资金！"
    echo "请确保:"
    echo "  1. API Key 已正确配置"
    echo "  2. 账户有足够的 USDT 余额"
    echo "  3. 已充分测试策略"
    echo ""
    read -p "确认启动实盘运行？(yes/no): " confirm
    
    if [[ "$confirm" != "yes" ]]; then
        echo "已取消实盘运行"
        exit 0
    fi
    
    echo ""
    echo "配置信息:"
    echo "  - 交易模式: Futures (永续合约)"
    echo "  - 交易对: BTC/USDT:USDT"
    echo "  - 杠杆: 20x"
    echo "  - 仓位比例: 20%"
    echo "  - 止损: 8%"
    echo ""
    echo "=================================================="
    
    freqtrade trade \
        --strategy BTC_Rebound_Volume_Strategy \
        --strategy-path "$STRATEGY_DIR" \
        --config "$STRATEGY_DIR/config_live.json"
}

# 回测
run_backtest() {
    timerange=""
    details=false
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --timerange)
                timerange="$2"
                shift 2
                ;;
            --details)
                details=true
                shift
                ;;
            *)
                echo "未知参数: $1"
                exit 1
                ;;
        esac
    done
    
    echo "=================================================="
    echo "运行回测..."
    echo "=================================================="
    echo ""
    
    # 构建回测命令
    backtest_cmd="freqtrade backtesting \
        --strategy BTC_Rebound_Volume_Strategy \
        --strategy-path \"$STRATEGY_DIR\" \
        --config \"$STRATEGY_DIR/config_dryrun.json\" \
        --timeframe 1m \
        --trading-mode futures"
    
    if [[ -n "$timerange" ]]; then
        backtest_cmd="$backtest_cmd --timerange $timerange"
    fi
    
    if [[ "$details" == true ]]; then
        backtest_cmd="$backtest_cmd --export trades"
    fi
    
    echo "执行命令: $backtest_cmd"
    echo ""
    
    eval $backtest_cmd
    
    echo ""
    echo "✅ 回测完成"
    
    if [[ "$details" == true ]]; then
        echo ""
        echo "交易详情已导出到 user_data/backtest_results/"
    fi
}

# 显示交易记录
show_trades() {
    details=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --details)
                details=true
                shift
                ;;
            *)
                shift
                ;;
        esac
    done
    
    echo "=================================================="
    echo "交易记录（Dry-Run）"
    echo "=================================================="
    
    freqtrade trade-show \
        --db-url sqlite:///user_data/btc_0603/tradesv3.dryrun.sqlite \
        --strategy BTC_Rebound_Volume_Strategy
}

# ==================== 主逻辑 ====================

if [[ $# -eq 0 ]]; then
    show_help
    exit 0
fi

command="$1"
shift

case "$command" in
    dryrun)
        run_dryrun
        ;;
    live)
        run_live
        ;;
    backtest)
        run_backtest "$@"
        ;;
    test)
        test_strategy
        ;;
    show-trades)
        show_trades "$@"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "未知命令: $command"
        echo "使用 '$0 help' 查看可用命令"
        exit 1
        ;;
esac