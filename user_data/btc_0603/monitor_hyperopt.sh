#!/bin/bash
# 监控 Hyperopt 进度

LOG_FILE="/tmp/hyperopt_1000.log"

echo "========================================="
echo "BTC Rebound Volume Strategy - Hyperopt 监控"
echo "========================================="
echo ""
echo "日志文件: $LOG_FILE"
echo "开始时间: $(date)"
echo ""

# 检查进程是否运行
if pgrep -f "freqtrade hyperopt" > /dev/null; then
    echo "✅ Hyperopt 正在运行"
    echo ""
    
    # 显示最新进度
    echo "最新进度:"
    tail -20 "$LOG_FILE" 2>/dev/null | grep -E "(Epochs|Best|trades|profit)" || tail -5 "$LOG_FILE"
    echo ""
    
    # 计算进度
    CURRENT=$(grep -c "Epoch" "$LOG_FILE" 2>/dev/null || echo "0")
    echo "已完成轮数: $CURRENT / 1000"
    echo ""
    
    echo "========================================="
    echo "监控命令:"
    echo "  tail -f $LOG_FILE"
    echo "  grep 'Best' $LOG_FILE"
    echo "========================================="
else
    echo "❌ Hyperopt 未运行或已完成"
    echo ""
    
    if [ -f "$LOG_FILE" ]; then
        echo "最后输出:"
        tail -30 "$LOG_FILE"
        echo ""
        
        # 显示最佳结果
        echo "最佳结果:"
        grep -A 30 "Best result:" "$LOG_FILE" 2>/dev/null || echo "未找到最佳结果"
    fi
fi