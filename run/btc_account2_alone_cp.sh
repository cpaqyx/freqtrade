#!/bin/bash

# 服务名称
SERVICE_NAME="BTC账户2独立cp策略"
# 脚本所在目录（run目录）
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
# 项目根目录（run目录的上级就是freqtrade根目录）
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")
# 配置和策略路径
ACCOUNT_DIR="user_data/btc_account2_alone_cp"
CONFIG_FILE="$ACCOUNT_DIR/config_live.json"
STRATEGY_FILE="$ACCOUNT_DIR/BTCFullPosition2_2.py"
STRATEGY_JSON="$ACCOUNT_DIR/BTCFullPosition2_2.json"
STRATEGY_NAME="BTCFullPosition2_2"
# PID文件和日志路径
PID_FILE="$SCRIPT_DIR/btc_account2_alone_cp.pid"
LOG_FILE="$PROJECT_ROOT/user_data/logs/btc_account2_alone_cp.log"

# 激活虚拟环境
source /opt/myenv/bin/activate

# 设置脚本专属代理（仅对当前进程生效，不影响全局环境）
export http_proxy=http://127.0.0.1:7890
export https_proxy=http://127.0.0.1:7890
export all_proxy=socks5://127.0.0.1:7891

# 切换到项目根目录
cd "$PROJECT_ROOT" || { echo "❌ 无法切换到项目根目录"; exit 1; }

# 检查进程是否运行
is_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

# 启动服务
start() {
    if is_running; then
        echo "$SERVICE_NAME 已经在运行中，PID: $(cat "$PID_FILE")"
        exit 0
    fi

    echo "========================================"
    echo "正在启动 $SERVICE_NAME"
    echo "========================================"

    # 检查配置文件
    if [ ! -f "$CONFIG_FILE" ]; then
        echo "❌ 错误：未找到配置文件 $CONFIG_FILE"
        exit 1
    fi

    # 复制策略文件
    if [ -f "$STRATEGY_FILE" ]; then
        echo "✓ 找到策略文件: $STRATEGY_FILE"
        cp -f "$STRATEGY_FILE" "user_data/strategies/BTCFullPosition2_2.py"
        echo "✓ 已复制策略文件到 strategies 目录"
    else
        echo "⚠️  警告：未找到策略文件 $STRATEGY_FILE，将尝试使用默认策略 BTCFullPosition2"
        STRATEGY_NAME="BTCFullPosition2"
    fi

    # 复制策略参数文件
    if [ -f "$STRATEGY_JSON" ]; then
        echo "✓ 找到参数文件: $STRATEGY_JSON"
        cp -f "$STRATEGY_JSON" "user_data/strategies/BTCFullPosition2_2.json"
        echo "✓ 已复制参数文件到 strategies 目录"
    else
        echo "⚠️  警告：未找到参数文件，将使用代码默认参数"
    fi

    # 检查运行模式
    if grep -q '"dry_run": false' "$CONFIG_FILE"; then
        MODE="实盘"
        echo "⚠️⚠️⚠️ 实盘模式 - 将执行真实交易 ⚠️⚠️⚠️"
    else
        MODE="模拟盘"
        echo "✓ 模拟盘模式 - 不执行真实交易"
    fi

    echo "策略: $STRATEGY_NAME"
    echo "模式: $MODE"
    echo "配置: $CONFIG_FILE"
    echo "日志: $LOG_FILE"

    # 创建日志目录
    mkdir -p "user_data/logs"

    # 后台启动
    nohup /opt/myenv/bin/python -m freqtrade trade \
      --config "$CONFIG_FILE" \
      --strategy "$STRATEGY_NAME" \
      --strategy-path "user_data/strategies" \
      --logfile "$LOG_FILE" > /dev/null 2>&1 &
    
    # 保存PID
    echo $! > "$PID_FILE"
    
    echo ""
    echo "✅ $SERVICE_NAME 启动成功，PID: $(cat "$PID_FILE")"
    echo "查看日志: tail -f $LOG_FILE"
}

# 停止服务
stop() {
    if ! is_running; then
        echo "$SERVICE_NAME 没有在运行"
        exit 0
    fi

    PID=$(cat "$PID_FILE")
    echo "正在停止 $SERVICE_NAME，PID: $PID"
    kill "$PID"
    
    # 等待进程停止
    wait "$PID" 2>/dev/null
    rm -f "$PID_FILE"
    
    echo "✅ $SERVICE_NAME 已停止"
}

# 重启服务
restart() {
    stop
    sleep 2
    start
}

# 查看状态
status() {
    if is_running; then
        echo "✅ $SERVICE_NAME 运行中，PID: $(cat "$PID_FILE")"
        echo "日志路径: $LOG_FILE"
    else
        echo "❌ $SERVICE_NAME 未运行"
    fi
}

# 主逻辑
case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    *)
        echo "用法: $0 {start|stop|restart|status}"
        echo "  start   启动服务"
        echo "  stop    停止服务"
        echo "  restart 重启服务"
        echo "  status  查看运行状态"
        exit 1
        ;;
esac
