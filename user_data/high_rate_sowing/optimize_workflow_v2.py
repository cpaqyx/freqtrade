#!/usr/bin/env python3
"""
HighRateSowing 优化工作流 V2
分批处理，避免内存溢出
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

# 交易对配置 - 分批处理
PAIRS_BATCH_1 = ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT"]  # 数据量大的币种
PAIRS_BATCH_2 = ["XRP/USDT:USDT", "ADA/USDT:USDT", "DOGE/USDT:USDT"]  # 中等数据量
PAIRS_BATCH_3 = ["SUI/USDT:USDT", "TRX/USDT:USDT", "ENA/USDT:USDT"]   # 数据量较小

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

def run_command(cmd: str, timeout: int = 3600, log_file: str = None) -> tuple:
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
        
        # 保存日志
        if log_file:
            with open(log_file, 'w') as f:
                f.write(f"命令: {cmd}\n")
                f.write(f"返回码: {result.returncode}\n")
                f.write(f"执行时间: {elapsed:.2f}秒\n")
                f.write("\n输出:\n")
                f.write(result.stdout)
                if result.stderr:
                    f.write("\n错误:\n")
                    f.write(result.stderr)
        
        return result.returncode, result.stdout, result.stderr, elapsed
    except subprocess.TimeoutExpired:
        return -1, "", "命令超时", timeout


def parse_backtest_result(output: str) -> dict:
    """解析回测结果"""
    result = {
        "trades": 0,
        "profit_pct": 0.0,
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


def create_temp_config(pairs: list) -> Path:
    """创建临时配置文件"""
    temp_config = BASE_DIR / f"config_temp_{'_'.join([p.split('/')[0] for p in pairs])}.json"
    
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    
    config['exchange']['pair_whitelist'] = pairs
    config['bot_name'] = f"HighRateSowing_{'_'.join([p.split('/')[0] for p in pairs])}"
    
    with open(temp_config, 'w') as f:
        json.dump(config, f, indent=2)
    
    return temp_config


def step1_batch_backtest(pairs: list, batch_name: str, timerange: str):
    """单批次回测"""
    print(f"\n{'='*60}")
    print(f"回测批次: {batch_name}")
    print(f"交易对: {pairs}")
    print(f"时间范围: {timerange}")
    print(f"{'='*60}")
    
    # 创建临时配置
    temp_config = create_temp_config(pairs)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = LOG_DIR / f"backtest_{batch_name}_{timestamp}.log"
    
    cmd = f"freqtrade backtesting --config {temp_config} --strategy {STRATEGY} --datadir user_data/data/binance --timerange={timerange} --cache none"
    
    returncode, stdout, stderr, elapsed = run_command(cmd, timeout=1200, log_file=log_file)
    
    # 解析结果
    result = parse_backtest_result(stdout)
    
    # 清理临时配置
    os.remove(temp_config)
    
    print(f"\n结果:")
    print(f"  交易次数: {result['trades']}")
    print(f"  总利润: {result['profit_pct']}%")
    print(f"  Sharpe: {result['sharpe']}")
    print(f"  日志: {log_file}")
    
    return result


def step1_all_pairs_backtest():
    """步骤1: 所有交易对回测（分批处理）"""
    print("\n" + "="*60)
    print("步骤1: 所有交易对回测 (分批处理)")
    print("="*60)
    
    results = {}
    
    # 批次1: BTC/ETH/SOL (20260322-20260522)
    results['batch1'] = step1_batch_backtest(
        PAIRS_BATCH_1, 
        "batch1_BTC_ETH_SOL",
        "20260322-20260522"
    )
    
    # 批次2: XRP/ADA/DOGE (20260322-20260522)
    results['batch2'] = step1_batch_backtest(
        PAIRS_BATCH_2,
        "batch2_XRP_ADA_DOGE",
        "20260322-20260522"
    )
    
    # 批次3: SUI/TRX/ENA (20260322-20260522)
    results['batch3'] = step1_batch_backtest(
        PAIRS_BATCH_3,
        "batch3_SUI_TRX_ENA",
        "20260322-20260522"
    )
    
    # 保存汇总
    summary_file = LOG_DIR / f"step1_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n步骤1完成，汇总: {summary_file}")
    return results


def step2_single_pair_backtest():
    """步骤2: 单个交易对回测"""
    print("\n" + "="*60)
    print("步骤2: 单个交易对回测")
    print("="*60)
    
    all_pairs = PAIRS_BATCH_1 + PAIRS_BATCH_2 + PAIRS_BATCH_3
    results = {}
    
    for pair in all_pairs:
        start_date, end_date = DATA_RANGES.get(pair, ("20250522", "20260522"))
        timerange = f"{start_date}-{end_date}"
        
        print(f"\n回测 {pair} ({timerange})")
        
        # 创建临时配置
        temp_config = create_temp_config([pair])
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = LOG_DIR / f"backtest_{pair.replace('/', '_')}_{timestamp}.log"
        
        cmd = f"freqtrade backtesting --config {temp_config} --strategy {STRATEGY} --datadir user_data/data/binance --timerange={timerange} --cache none"
        
        returncode, stdout, stderr, elapsed = run_command(cmd, timeout=600, log_file=log_file)
        
        result = parse_backtest_result(stdout)
        results[pair] = result
        
        print(f"  交易次数: {result['trades']}, 利润: {result['profit_pct']}%")
        
        # 清理
        os.remove(temp_config)
    
    # 保存汇总
    summary_file = LOG_DIR / f"step2_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n步骤2完成，汇总: {summary_file}")
    return results


def step3_all_pairs_hyperopt():
    """步骤3: 所有交易对 Hyperopt（分批处理）"""
    print("\n" + "="*60)
    print("步骤3: 所有交易对 Hyperopt (分批处理)")
    print("="*60)
    
    results = {}
    
    # 批次1: BTC/ETH/SOL
    print("\n批次1: BTC/ETH/SOL")
    temp_config = create_temp_config(PAIRS_BATCH_1)
    log_file = LOG_DIR / f"hyperopt_batch1_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    cmd = f"freqtrade hyperopt --config {temp_config} --strategy {STRATEGY} --datadir user_data/data/binance --timerange=20260322-20260522 --epochs 5000 --spaces buy sell roi stoploss --hyperopt-loss SharpeHyperOptLoss --min-trades 50 --random-state 42 -j 1"
    
    returncode, stdout, stderr, elapsed = run_command(cmd, timeout=28800, log_file=log_file)
    results['batch1'] = log_file
    os.remove(temp_config)
    
    # 批次2: XRP/ADA/DOGE
    print("\n批次2: XRP/ADA/DOGE")
    temp_config = create_temp_config(PAIRS_BATCH_2)
    log_file = LOG_DIR / f"hyperopt_batch2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    cmd = f"freqtrade hyperopt --config {temp_config} --strategy {STRATEGY} --datadir user_data/data/binance --timerange=20260322-20260522 --epochs 5000 --spaces buy sell roi stoploss --hyperopt-loss SharpeHyperOptLoss --min-trades 50 --random-state 42 -j 1"
    
    returncode, stdout, stderr, elapsed = run_command(cmd, timeout=28800, log_file=log_file)
    results['batch2'] = log_file
    os.remove(temp_config)
    
    # 批次3: SUI/TRX/ENA
    print("\n批次3: SUI/TRX/ENA")
    temp_config = create_temp_config(PAIRS_BATCH_3)
    log_file = LOG_DIR / f"hyperopt_batch3_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    cmd = f"freqtrade hyperopt --config {temp_config} --strategy {STRATEGY} --datadir user_data/data/binance --timerange=20260322-20260522 --epochs 5000 --spaces buy sell roi stoploss --hyperopt-loss SharpeHyperOptLoss --min-trades 50 --random-state 42 -j 1"
    
    returncode, stdout, stderr, elapsed = run_command(cmd, timeout=28800, log_file=log_file)
    results['batch3'] = log_file
    os.remove(temp_config)
    
    print(f"\n步骤3完成")
    return results


def step4_single_pair_hyperopt():
    """步骤4: 单个交易对 Hyperopt"""
    print("\n" + "="*60)
    print("步骤4: 单个交易对 Hyperopt")
    print("="*60)
    
    all_pairs = PAIRS_BATCH_1 + PAIRS_BATCH_2 + PAIRS_BATCH_3
    results = {}
    
    for pair in all_pairs:
        start_date, end_date = DATA_RANGES.get(pair, ("20250522", "20260522"))
        timerange = f"{start_date}-{end_date}"
        
        print(f"\n优化 {pair}")
        
        temp_config = create_temp_config([pair])
        log_file = LOG_DIR / f"hyperopt_{pair.replace('/', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        cmd = f"freqtrade hyperopt --config {temp_config} --strategy {STRATEGY} --datadir user_data/data/binance --timerange={timerange} --epochs 2000 --spaces buy sell roi stoploss --hyperopt-loss SharpeHyperOptLoss --min-trades 8 --random-state 42 -j 1"
        
        returncode, stdout, stderr, elapsed = run_command(cmd, timeout=14400, log_file=log_file)
        results[pair] = log_file
        
        os.remove(temp_config)
        print(f"  完成: {log_file}")
    
    print(f"\n步骤4完成")
    return results


def step5_sliding_window_backtest():
    """步骤5: 滑动时间窗口批量回测"""
    print("\n" + "="*60)
    print("步骤5: 滑动时间窗口批量回测")
    print("="*60)
    
    # 计算滑动窗口
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
        
        # 使用较少的交易对以节省内存
        temp_config = create_temp_config(PAIRS_BATCH_2 + PAIRS_BATCH_3)
        
        cmd = f"freqtrade backtesting --config {temp_config} --strategy {STRATEGY} --datadir user_data/data/binance --timerange={timerange} --cache none"
        
        returncode, stdout, stderr, elapsed = run_command(cmd, timeout=600)
        
        result = parse_backtest_result(stdout)
        results[timerange] = result
        
        print(f"  交易次数: {result['trades']}, 利润: {result['profit_pct']}%")
        
        os.remove(temp_config)
    
    # 保存汇总
    summary_file = LOG_DIR / f"step5_sliding_window_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n步骤5完成，汇总: {summary_file}")
    return results


def main():
    """主函数"""
    print("="*60)
    print("HighRateSowing 优化工作流 V2")
    print("="*60)
    print(f"开始时间: {datetime.now()}")
    
    # 创建日志目录
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # 记录工作流日志
    workflow_log = LOG_DIR / f"workflow_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    def log(msg):
        print(msg)
        with open(workflow_log, 'a') as f:
            f.write(f"{datetime.now().isoformat()} - {msg}\n")
    
    try:
        # 步骤1
        log("开始步骤1: 所有交易对回测（分批）")
        step1_results = step1_all_pairs_backtest()
        log(f"步骤1完成")
        
        # 步骤2
        log("开始步骤2: 单个交易对回测")
        step2_results = step2_single_pair_backtest()
        log(f"步骤2完成")
        
        # 步骤3
        log("开始步骤3: 所有交易对 Hyperopt（分批）")
        step3_results = step3_all_pairs_hyperopt()
        log(f"步骤3完成")
        
        # 步骤4
        log("开始步骤4: 单个交易对 Hyperopt")
        step4_results = step4_single_pair_hyperopt()
        log(f"步骤4完成")
        
        # 步骤5
        log("开始步骤5: 滑动窗口回测")
        step5_results = step5_sliding_window_backtest()
        log(f"步骤5完成")
        
        log("工作流完成!")
        
    except Exception as e:
        log(f"错误: {e}")
        import traceback
        log(traceback.format_exc())
        raise


if __name__ == '__main__':
    main()
