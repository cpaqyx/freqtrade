#!/bin/bash
# 批量回测已实施的策略
cd /opt/git/freqtrade

echo "=== 批量回测汇总 ==="
echo "时间范围: 2026-03-21 至 2026-05-05"
echo ""

for dir in user_data/*/; do
    if [[ -f "${dir}config.json" ]] && [[ -f "${dir}strategy.py" ]]; then
        strategy_name=$(basename "$dir")
        echo "--- 测试: $strategy_name ---"
        freqtrade backtesting -c "${dir}config.json" --timerange 20260321-20260505 2>&1 | grep -E "Strategy|TOTAL|Profit|Win|Sharpe|Drawdown" | tail -5
        echo ""
    fi
done
