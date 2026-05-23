#!/usr/bin/env python3
"""
HighRateSowing 完整优化工作流
自动化执行: 回测 -> Hyperopt -> 参数验证 -> 滑动窗口回测
"""

import subprocess
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
import time

# 配置
BASE_DIR = Path("/opt/git/freqtrade/user_data/high_rate_sowing")
CONFIG_FILE = BASE_DIR / "config.json"
LOG_DIR = BASE_DIR / "logs"
STRATEGY = "HighRateSowing"

# 交易对配置
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

# 数据范围配置
DATA_RANGES = {
    "BTC/USDT:USDT": ("20240522", "20260522"),
    "ETH/USDT:USDT": ("20240522", "20260522"),
    "SOL/USDT:USDT": ("20240522", "20260522"),
    "XRP/USDT:USDT": ("20250522", "20260522"),
    "ADA/USDT:USDT": ("20250522", "20260522"),
    "DOGE/USDT:USDT": ("20250522", "20260522"),
    "SUI/USDT:USDT": ("20250522", "20260522"),
    "TRX/USDT:USDT": ("20250522", "20260522"),
    "ENA/USDT:USDT": ("20250522", "20260522"),
}

def run_command(cmd: str, timeout: int = 3600) -> tuple:
    """执行命令并返回结果"""
    print(f"\n执行: {cmd}")
    start_time = time.time()
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd="/opt/git/freqtrade"
        )
        elapsed = time.time() - start_time
        return result.returncode, result.stdout, result.stderr, elapsed
    except subprocess.TimeoutExpired:
        return -1, "", "命令超时", timeout


def parse_backtest_result(output: str) -> dict:
    """解析回测结果"""
    result = {
        "trades": 0,
        "profit_pct": 0.0,
        "profit_usdt": 0.0,
        "win_rate": 0.0,
        "sharpe": 0.0,
        "max_drawdown": 0.0,
    }
    
    # 提取总交易数
    match = re.search(r'TOTAL.*?│\s+(\d+)\s+│', output)
    if match:
        result["trades"] = int(match.group(1))
    
    # 提取总利润百分比
    match = re.search(r'Tot Profit %.*?│\s+([\d.-]+)', output)
    if match:
        result["profit_pct"] = float(match.group(1))
    
    # 提取 Sharpe
    match = re.search(r'Sharpe.*?│\s+([\d.-]+)', output)
    if match:
        result["sharpe"] = float(match.group(1))
    
    # 提取最大回撤
    match = re.search(r'Max % of account underwater.*?│\s+([\d.]+)%', output)
    if match:
        result["max_drawdown"] = float(match.group(1))
    
    return result


def step1_all_pairs_backtest():
    """步骤1: 所有交易对回测"""
    print("\n" + "="*60)
    print("步骤1: 所有交易对回测 (20260322-20260522)")
    print("="*60)
    
    timerange = "20260322-20260522"
    log_file = LOG_DIR / f"step1_backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    cmd = f"freqtrade backtesting --config {CONFIG_FILE} --strategy {STRATEGY} --datadir user_data/data/binance --timerange={timerange} --cache none"
    
    returncode, stdout, stderr, elapsed = run_command(cmd, timeout=600)
    
    # 保存日志
    with open(log_file, 'w') as f:
        f.write(f"命令: {cmd}\n")
        f.write(f"返回码: {returncode}\n")
        f.write(f"执行时间: {elapsed:.2f}秒\n")
        f.write("\n输出:\n")
        f.write(stdout)
        if stderr:
            f.write("\n错误:\n")
            f.write(stderr)
    
    # 解析结果
    result = parse_backtest_result(stdout)
    print(f"\n回测结果:")
    print(f"  交易次数: {result['trades']}")
    print(f"  总利润: {result['profit_pct']}%")
    print(f"  Sharpe: {result['sharpe']}")
    print(f"  最大回撤: {result['max_drawdown']}%")
    print(f"  日志文件: {log_file}")
    
    return result


def step2_single_pair_backtest():
    """步骤2: 单个交易对回测"""
    print("\n" + "="*60)
    print("步骤2: 单个交易对回测 (遍历9个币种)")
    print("="*60)
    
    results = {}
    
    for pair in PAIRS:
        # 获取该币种的数据范围
        start_date, end_date = DATA_RANGES.get(pair, ("20250522", "20260522"))
        timerange = f"{start_date}-{end_date}"
        
        print(f"\n回测 {pair} ({timerange})")
        
        # 创建临时配置文件
        temp_config = BASE_DIR / f"config_{pair.replace('/', '_')}.json"
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        config['exchange']['pair_whitelist'] = [pair]
        with open(temp_config, 'w') as f:
            json.dump(config, f, indent=2)
        
        cmd = f"freqtrade backtesting --config {temp_config} --strategy {STRATEGY} --datadir user_data/data/binance --timerange={timerange} --cache none"
        
        returncode, stdout, stderr, elapsed = run_command(cmd, timeout=600)
        
        # 解析结果
        result = parse_backtest_result(stdout)
        results[pair] = result
        
        print(f"  交易次数: {result['trades']}")
        print(f"  总利润: {result['profit_pct']}%")
        
        # 清理临时配置
        os.remove(temp_config)
    
    # 保存汇总结果
    summary_file = LOG_DIR / f"step2_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n汇总结果已保存: {summary_file}")
    
    return results


def step3_all_pairs_hyperopt():
    """步骤3: 所有交易对参数优化"""
    print("\n" + "="*60)
    print("步骤3: 所有交易对 Hyperopt 优化 (15000 epochs)")
    print("="*60)
    
    timerange = "20260322-20260522"
    log_file = LOG_DIR / f"step3_hyperopt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    cmd = f"freqtrade hyperopt --config {CONFIG_FILE} --strategy {STRATEGY} --datadir user_data/data/binance --timerange={timerange} --epochs 15000 --spaces buy sell roi stoploss --loss-function SharpeHyperOptLoss --min-trades 100 --random-state 42 --cache none"
    
    returncode, stdout, stderr, elapsed = run_command(cmd, timeout=72000)  # 20小时超时
    
    # 保存日志
    with open(log_file, 'w') as f:
        f.write(f"命令: {cmd}\n")
        f.write(f"返回码: {returncode}\n")
        f.write(f"执行时间: {elapsed:.2f}秒\n")
        f.write("\n输出:\n")
        f.write(stdout)
        if stderr:
            f.write("\n错误:\n")
            f.write(stderr)
    
    print(f"\nHyperopt 完成，日志: {log_file}")
    
    return log_file


def step4_single_pair_hyperopt():
    """步骤4: 单个交易对参数优化"""
    print("\n" + "="*60)
    print("步骤4: 单个交易对 Hyperopt 优化 (遍历9个币种)")
    print("="*60)
    
    results = {}
    
    for pair in PAIRS:
        start_date, end_date = DATA_RANGES.get(pair, ("20250522", "20260522"))
        timerange = f"{start_date}-{end_date}"
        
        print(f"\n优化 {pair} ({timerange})")
        
        # 创建临时配置文件
        temp_config = BASE_DIR / f"config_{pair.replace('/', '_')}.json"
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        config['exchange']['pair_whitelist'] = [pair]
        with open(temp_config, 'w') as f:
            json.dump(config, f, indent=2)
        
        log_file = LOG_DIR / f"step4_hyperopt_{pair.replace('/', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        cmd = f"freqtrade hyperopt --config {temp_config} --strategy {STRATEGY} --datadir user_data/data/binance --timerange={timerange} --epochs 5000 --spaces buy sell roi stoploss --loss-function SharpeHyperOptLoss --min-trades 8 --random-state 42 --cache none"
        
        returncode, stdout, stderr, elapsed = run_command(cmd, timeout=28800)  # 8小时超时
        
        # 保存日志
        with open(log_file, 'w') as f:
            f.write(stdout)
        
        results[pair] = log_file
        
        # 清理临时配置
        os.remove(temp_config)
        
        print(f"  完成，日志: {log_file}")
    
    return results


def step5_sliding_window_backtest():
    """步骤5: 滑动时间窗口批量回测验证"""
    print("\n" + "="*60)
    print("步骤5: 滑动时间窗口批量回测验证")
    print("="*60)
    
    # 计算滑动窗口
    # 从 20260322 开始，每15天一个窗口，直到 20260522
    windows = []
    start = datetime(2026, 3, 22)
    end = datetime(2026, 5, 22)
    
    current = start
    while current < end:
        window_end = current + timedelta(days=30)
        if window_end > end:
            window_end = end
        
        windows.append((
            current.strftime("%Y%m%d"),
            window_end.strftime("%Y%m%d")
        ))
        
        current += timedelta(days=15)
    
    print(f"共 {len(windows)} 个时间窗口")
    
    results = {}
    
    for i, (window_start, window_end) in enumerate(windows):
        timerange = f"{window_start}-{window_end}"
        
        print(f"\n窗口 {i+1}/{len(windows)}: {timerange}")
        
        cmd = f"freqtrade backtesting --config {CONFIG_FILE} --strategy {STRATEGY} --datadir user_data/data/binance --timerange={timerange} --cache none"
        
        returncode, stdout, stderr, elapsed = run_command(cmd, timeout=600)
        
        result = parse_backtest_result(stdout)
        results[timerange] = result
        
        print(f"  交易次数: {result['trades']}")
        print(f"  总利润: {result['profit_pct']}%")
    
    # 保存汇总
    summary_file = LOG_DIR / f"step5_sliding_window_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n滑动窗口汇总: {summary_file}")
    
    return results


def main():
    """主函数"""
    print("="*60)
    print("HighRateSowing 完整优化工作流")
    print("="*60)
    print(f"开始时间: {datetime.now()}")
    
    # 创建日志目录
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # 记录工作流日志
    workflow_log = LOG_DIR / f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    def log(msg):
        print(msg)
        with open(workflow_log, 'a') as f:
            f.write(f"{datetime.now().isoformat()} - {msg}\n")
    
    try:
        # 步骤1
        log("开始步骤1: 所有交易对回测")
        step1_result = step1_all_pairs_backtest()
        log(f"步骤1完成: {step1_result}")
        
        # 步骤2
        log("开始步骤2: 单个交易对回测")
        step2_results = step2_single_pair_backtest()
        log(f"步骤2完成: {len(step2_results)} 个币种")
        
        # 步骤3
        log("开始步骤3: 所有交易对 Hyperopt")
        step3_log = step3_all_pairs_hyperopt()
        log(f"步骤3完成: {step3_log}")
        
        # 步骤4
        log("开始步骤4: 单个交易对 Hyperopt")
        step4_results = step4_single_pair_hyperopt()
        log(f"步骤4完成: {len(step4_results)} 个币种")
        
        # 步骤5
        log("开始步骤5: 滑动窗口回测")
        step5_results = step5_sliding_window_backtest()
        log(f"步骤5完成: {len(step5_results)} 个窗口")
        
        log("工作流完成!")
        
    except Exception as e:
        log(f"错误: {e}")
        import traceback
        log(traceback.format_exc())
        raise


if __name__ == '__main__':
    main()
