#!/usr/bin/env python3
"""
HighRateSowing 策略优化工作流脚本
自动化执行完整的策略优化流程
"""

import os
import sys
import json
import subprocess
import re
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import shutil

# 配置
STRATEGY_NAME = "HighRateSowing"
STRATEGY_DIR = Path("/opt/git/freqtrade/user_data/high_rate_sowing")
FREQTRADE_DIR = Path("/opt/git/freqtrade")
CONFIG_FILE = STRATEGY_DIR / "config.json"
STRATEGY_FILE = STRATEGY_DIR / f"{STRATEGY_NAME}.py"
STRATEGIES_DIR = FREQTRADE_DIR / "user_data/strategies"
BACKTEST_RESULTS_DIR = FREQTRADE_DIR / "user_data/backtest_results"
HYPEROPT_RESULTS_DIR = FREQTRADE_DIR / "user_data/hyperopt_results"
LOG_DIR = STRATEGY_DIR / "logs"
DATA_DIR = FREQTRADE_DIR / "user_data/data/binance/futures"

# 交易对列表
PAIRS = [
    "BTC/USDT:USDT",
    "ETH/USDT:USDT",
    "SOL/USDT:USDT",
    "XRP/USDT:USDT",
    "ADA/USDT:USDT",
    "DOGE/USDT:USDT",
    "SUI/USDT:USDT",
    "TRX/USDT:USDT",
    "ENA/USDT:USDT"
]

# 数据范围（各币种的上市时间不同）
PAIR_DATA_RANGE = {
    "BTC/USDT:USDT": ("20240522", "20260522"),
    "ETH/USDT:USDT": ("20240522", "20260522"),
    "SOL/USDT:USDT": ("20240522", "20260522"),
    "XRP/USDT:USDT": ("20250522", "20260522"),
    "ADA/USDT:USDT": ("20250522", "20260522"),
    "DOGE/USDT:USDT": ("20250522", "20260522"),
    "SUI/USDT:USDT": ("20250522", "20260522"),
    "TRX/USDT:USDT": ("20250522", "20260522"),
    "ENA/USDT:USDT": ("20250522", "20260522")
}


def log(msg: str, log_file: Path = None):
    """打印日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {msg}"
    print(log_msg)
    if log_file:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_msg + "\n")


def run_command(cmd: list, cwd: Path = None, timeout: int = None) -> tuple:
    """运行命令"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd or FREQTRADE_DIR,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8"
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "命令超时"
    except Exception as e:
        return -2, "", str(e)


def copy_strategy():
    """复制策略文件到 strategies 目录"""
    dest = STRATEGIES_DIR / f"{STRATEGY_NAME}.py"
    shutil.copy(STRATEGY_FILE, dest)
    log(f"已复制策略文件: {STRATEGY_FILE} -> {dest}")


def get_latest_backtest_result() -> Path:
    """获取最新的回测结果文件"""
    results = list(BACKTEST_RESULTS_DIR.glob("backtest-result-*.json"))
    if not results:
        return None
    return max(results, key=lambda x: x.stat().st_mtime)


def get_latest_hyperopt_result() -> Path:
    """获取最新的 hyperopt 结果文件"""
    results = list(HYPEROPT_RESULTS_DIR.glob("hyperopt_results-*.pickle"))
    if not results:
        return None
    return max(results, key=lambda x: x.stat().st_mtime)


def analyze_backtest_result(result_file: Path) -> dict:
    """分析回测结果"""
    if not result_file or not result_file.exists():
        return {"error": "无回测结果文件"}
    
    try:
        with open(result_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        strategy_data = data.get("strategy", {}).get(STRATEGY_NAME, {})
        
        # 提取关键指标
        trades = strategy_data.get("trades", [])
        total_trades = len(trades)
        
        profit_mean = strategy_data.get("profit_mean", 0)
        profit_total = strategy_data.get("profit_total", 0)
        profit_total_abs = strategy_data.get("profit_total_abs", 0)
        
        wins = strategy_data.get("wins", 0)
        losses = strategy_data.get("losses", 0)
        
        if total_trades > 0:
            win_rate = wins / total_trades * 100
        else:
            win_rate = 0
        
        return {
            "total_trades": total_trades,
            "profit_mean": profit_mean,
            "profit_total": profit_total,
            "profit_total_abs": profit_total_abs,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "trades": trades
        }
    except Exception as e:
        return {"error": str(e)}


def run_backtest(timerange: str, pairs: list = None, log_file: Path = None) -> dict:
    """运行回测"""
    log(f"执行回测: timerange={timerange}, pairs={pairs or 'all'}", log_file)
    
    # 复制策略
    copy_strategy()
    
    # 构建命令
    cmd = [
        "freqtrade", "backtesting",
        "--config", str(CONFIG_FILE),
        "--strategy", STRATEGY_NAME,
        "--datadir", "user_data/data/binance",
        "--timerange", timerange,
        "--cache", "none"
    ]
    
    if pairs:
        cmd.extend(["--pairs", ",".join(pairs)])
    
    log(f"命令: {' '.join(cmd)}", log_file)
    
    # 执行
    code, stdout, stderr = run_command(cmd, cwd=FREQTRADE_DIR, timeout=300)
    
    if code != 0:
        log(f"回测失败: {stderr}", log_file)
        return {"error": stderr, "stdout": stdout}
    
    log(f"回测完成", log_file)
    
    # 分析结果
    result_file = get_latest_backtest_result()
    analysis = analyze_backtest_result(result_file)
    
    log(f"回测结果: 总交易={analysis.get('total_trades', 0)}, "
        f"总收益={analysis.get('profit_total', 0):.2%}, "
        f"胜率={analysis.get('win_rate', 0):.1f}%", log_file)
    
    return analysis


def run_hyperopt(timerange: str, pairs: list = None, epochs: int = 15000, 
                 min_trades: int = 20, log_file: Path = None) -> dict:
    """运行参数优化"""
    log(f"执行参数优化: timerange={timerange}, pairs={pairs or 'all'}, "
        f"epochs={epochs}, min_trades={min_trades}", log_file)
    
    # 复制策略
    copy_strategy()
    
    # 构建命令
    cmd = [
        "freqtrade", "hyperopt",
        "--config", str(CONFIG_FILE),
        "--strategy", STRATEGY_NAME,
        "--strategy-path", "user_data/high_rate_sowing",
        "--timeframe", "1m",
        "--hyperopt-loss", "SharpeHyperOptLoss",
        "--epochs", str(epochs),
        "--spaces", "buy", "sell", "roi", "stoploss",
        "--random-state", "42",
        "--min-trades", str(min_trades),
        "-j", "-1",
        "--timerange", timerange
    ]
    
    if pairs:
        cmd.extend(["--pairs", ",".join(pairs)])
    
    log(f"命令: {' '.join(cmd)}", log_file)
    
    # 执行（hyperopt 可能需要很长时间）
    code, stdout, stderr = run_command(cmd, cwd=FREQTRADE_DIR, timeout=7200)
    
    if code != 0:
        log(f"参数优化失败: {stderr}", log_file)
        return {"error": stderr, "stdout": stdout}
    
    log(f"参数优化完成", log_file)
    
    # 解析最佳结果
    best_result = parse_hyperopt_output(stdout)
    
    return best_result


def parse_hyperopt_output(output: str) -> dict:
    """解析 hyperopt 输出"""
    result = {
        "best_epoch": None,
        "objective": None,
        "trades": None,
        "profit": None,
        "params": {}
    }
    
    # 查找最佳结果
    # 格式示例: Best result: 0.1234 with epoch 123
    best_match = re.search(r"Best result:\s*([-\d.]+)\s*with epoch\s*(\d+)", output)
    if best_match:
        result["best_epoch"] = int(best_match.group(2))
        result["objective"] = float(best_match.group(1))
    
    # 查找交易次数
    trades_match = re.search(r"Total trades:\s*(\d+)", output)
    if trades_match:
        result["trades"] = int(trades_match.group(1))
    
    # 查找收益
    profit_match = re.search(r"Profit:\s*([-\d.]+)%", output)
    if profit_match:
        result["profit"] = float(profit_match.group(1))
    
    # 查找参数值
    # 格式示例: buy_param1: 0.123
    param_matches = re.findall(r"(\w+):\s*([-\d.]+)", output)
    for param_name, param_value in param_matches[-20:]:  # 最后20个参数
        if param_name.startswith(("buy", "sell", "roi", "stoploss")):
            result["params"][param_name] = float(param_value)
    
    return result


def generate_timerange_windows(start_date: str, end_date: str, 
                               period_months: int, slide_days: int) -> list:
    """生成滑动时间窗口"""
    windows = []
    
    start = datetime.strptime(start_date, "%Y%m%d")
    end = datetime.strptime(end_date, "%Y%m%d")
    
    # 计算周期天数（近似）
    period_days = period_months * 30
    
    # 生成窗口
    current_start = start
    while current_start + timedelta(days=period_days) <= end:
        current_end = current_start + timedelta(days=period_days)
        window = (
            current_start.strftime("%Y%m%d"),
            current_end.strftime("%Y%m%d")
        )
        windows.append(window)
        
        # 滑动
        current_start = current_start + timedelta(days=slide_days)
    
    return windows


def main():
    """主函数"""
    # 创建日志目录
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    BACKTEST_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    HYPEROPT_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 主日志文件
    main_log = LOG_DIR / f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    log("=" * 60, main_log)
    log("HighRateSowing 策略优化工作流", main_log)
    log("=" * 60, main_log)
    log("", main_log)
    
    # ========== 步骤1: 所有交易对回测1 ==========
    log("【步骤1】所有交易对回测 - 最近两个月", main_log)
    log("", main_log)
    
    timerange1 = "20260322-20260522"
    result1 = run_backtest(timerange1, pairs=None, log_file=main_log)
    
    total_trades1 = result1.get("total_trades", 0)
    
    # 判断是否满足条件
    if total_trades1 < 50:
        log(f"⚠️ 交易次数不足({total_trades1} < 50)，需要调整策略参数使其更宽松", main_log)
        # TODO: 自动调整参数
    elif total_trades1 > 2000:
        log(f"⚠️ 交易次数过多({total_trades1} > 2000)，需要调整策略参数使其更严格", main_log)
        # TODO: 自动调整参数
    else:
        log(f"✅ 交易次数满足条件({total_trades1})", main_log)
    
    log("", main_log)
    
    # ========== 步骤2: 单个交易对回测2 ==========
    log("【步骤2】单个交易对回测 - 遍历9个币种", main_log)
    log("", main_log)
    
    for pair in PAIRS:
        log(f"--- {pair} ---", main_log)
        
        # 使用该币种的实际数据范围（最近两个月）
        data_start, data_end = PAIR_DATA_RANGE.get(pair, ("20250522", "20260522"))
        
        # 计算最近两个月
        end_date = datetime.strptime(data_end, "%Y%m%d")
        start_date = end_date - timedelta(days=60)
        timerange2 = f"{start_date.strftime('%Y%m%d')}-{data_end}"
        
        result2 = run_backtest(timerange2, pairs=[pair], log_file=main_log)
        
        trades2 = result2.get("total_trades", 0)
        
        if trades2 < 10:
            log(f"⚠️ {pair} 交易次数不足({trades2} < 10)", main_log)
        elif trades2 > 1000:
            log(f"⚠️ {pair} 交易次数过多({trades2} > 1000)", main_log)
        else:
            log(f"✅ {pair} 交易次数满足条件({trades2})", main_log)
        
        log("", main_log)
    
    # ========== 步骤3: 所有交易对参数优化1 ==========
    log("【步骤3】所有交易对参数优化 - 最近两个月", main_log)
    log("", main_log)
    
    timerange3 = "20260322-20260522"
    result3 = run_hyperopt(timerange3, pairs=None, epochs=15000, 
                           min_trades=100, log_file=main_log)
    
    if result3.get("error"):
        log(f"❌ 参数优化失败: {result3['error']}", main_log)
    else:
        trades3 = result3.get("trades", 0)
        profit3 = result3.get("profit", 0)
        
        if trades3 < 100:
            log(f"⚠️ 交易次数不足({trades3} < 100)", main_log)
        elif profit3 < 10:
            log(f"⚠️ 收益不足({profit3}% < 10%)", main_log)
        else:
            log(f"✅ 参数优化结果满足条件", main_log)
    
    log("", main_log)
    
    # ========== 步骤4: 单个交易对参数优化2 ==========
    log("【步骤4】单个交易对参数优化 - 遍历9个币种", main_log)
    log("", main_log)
    
    for pair in PAIRS:
        log(f"--- {pair} ---", main_log)
        
        data_start, data_end = PAIR_DATA_RANGE.get(pair, ("20250522", "20260522"))
        end_date = datetime.strptime(data_end, "%Y%m%d")
        start_date = end_date - timedelta(days=60)
        timerange4 = f"{start_date.strftime('%Y%m%d')}-{data_end}"
        
        result4 = run_hyperopt(timerange4, pairs=[pair], epochs=5000,
                               min_trades=8, log_file=main_log)
        
        if result4.get("error"):
            log(f"❌ {pair} 参数优化失败", main_log)
        else:
            trades4 = result4.get("trades", 0)
            profit4 = result4.get("profit", 0)
            
            log(f"{pair} 最佳结果: trades={trades4}, profit={profit4}%", main_log)
    
    log("", main_log)
    
    # ========== 步骤5 & 6: 参数回测（需要从 hyperopt 结果提取参数）==========
    # TODO: 实现参数提取和批量回测
    
    log("=" * 60, main_log)
    log("工作流完成", main_log)
    log("=" * 60, main_log)


if __name__ == "__main__":
    main()