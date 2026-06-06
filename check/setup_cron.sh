#!/bin/bash
# Freqtrade监控定时任务配置脚本

SCRIPT_DIR="/opt/git/freqtrade/check"
PYTHON="/usr/bin/python3"
CHECK_SCRIPT="$SCRIPT_DIR/check_freqtrade.py"

# 检查虚拟环境
if [ ! -f "$PYTHON" ]; then
    echo "错误: Python虚拟环境不存在: $PYTHON"
    exit 1
fi

# 检查监控脚本
if [ ! -f "$CHECK_SCRIPT" ]; then
    echo "错误: 监控脚本不存在: $CHECK_SCRIPT"
    exit 1
fi

# 添加执行权限
chmod +x "$CHECK_SCRIPT"

# 创建cron任务（每10分钟执行一次）
CRON_JOB="*/10 * * * * $PYTHON $CHECK_SCRIPT >> $SCRIPT_DIR/logs/cron.log 2>&1"

# 检查是否已存在
if crontab -l 2>/dev/null | grep -q "check_freqtrade.py"; then
    echo "定时任务已存在，更新..."
    # 删除旧任务
    crontab -l 2>/dev/null | grep -v "check_freqtrade.py" | crontab -
fi

# 添加新任务
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo "✅ 定时任务配置成功"
echo "任务内容: $CRON_JOB"
echo ""
echo "查看定时任务:"
echo "  crontab -l"
echo ""
echo "查看监控日志:"
echo "  tail -f $SCRIPT_DIR/logs/check_\$(date +%Y%m%d).log"
echo ""
echo "手动执行监控:"
echo "  $PYTHON $CHECK_SCRIPT"