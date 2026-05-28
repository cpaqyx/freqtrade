#!/usr/bin/env python3
"""
HighRateSowing策略优化工作流脚本
自动化执行回测和参数优化流程
"""

import os
import sys
import json
import time
import shutil
import subprocess
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

# 项目根目录
PROJECT_ROOT = Path('/opt/git/freqtrade')
WORKSPACE_DIR = PROJECT_ROOT / 'user_data' / 'high_rate_sowing'
DATA_DIR = PROJECT_ROOT / 'user_data' / 'data' / 'binance'
BACKTEST_RESULTS_DIR = PROJECT_ROOT / 'user_data' / 'backtest_results'
HYPEROPT_RESULTS_DIR = PROJECT_ROOT / 'user_data' / 'hyperopt_results'
STRATEGIES_DIR = PROJECT_ROOT / 'user_data' / 'strategies'
LOGS_DIR = WORKSPACE_DIR / 'logs'

# 所有交易对（BTC/ETH/SOL）
ALL_PAIRS = ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT']

# 数据时间范围
DATA_START_DATE = '2024-05-01'
DATA_END_DATE = '2026-05-21'

# 最近两个月（用于初始测试）
RECENT_2_MONTHS_START = '20260321'
RECENT_2_MONTHS_END = '20260521'

# 回测滑动窗口参数
ROLLING_WINDOW_START = '20240601'  # 一年前开始
ROLLING_WINDOW_MIN_WEEKS = 1
ROLLING_WINDOW_MAX_WEEKS = 10
ROLLING_WINDOW_STEP_DAYS = 5

# 优化参数
HYPEROPT_EPOCHS = 10000
HYPEROPT_MIN_TRADES = 20
HYPEROPT_SPACES = 'buy sell roi stoploss'
HYPEROPT_LOSS = 'SharpeHyperOptLoss'

# 进度报告间隔（秒）
PROGRESS_REPORT_INTERVAL = 600  # 10分钟

class OptimizationWorkflow:
    def __init__(self):
        self.log_file = LOGS_DIR / 'optimization_workflow.log'
        self.progress_file = LOGS_DIR / 'progress.json'
        self.current_step = 0
        self.current_task = ''
        self.start_time = time.time()
        self.last_progress_report = time.time()
        
        # 创建必要的目录
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        BACKTEST_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        HYPEROPT_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        STRATEGIES_DIR.mkdir(parents=True, exist_ok=True)
        
    def log(self, message: str, level: str = 'INFO'):
        """记录日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] [{level}] {message}"
        print(log_line)
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_line + '\n')
    
    def report_progress(self):
        """报告进度"""
        elapsed = time.time() - self.start_time
        elapsed_str = f"{int(elapsed // 3600)}h {int((elapsed % 3600) // 60)}m {int(elapsed % 60)}s"
        
        progress_info = {
            'current_step': self.current_step,
            'current_task': self.current_task,
            'elapsed_time': elapsed_str,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_info, f, indent=2)
        
        self.log(f"进度报告: 步骤{self.current_step} - {self.current_task} (已运行 {elapsed_str})")
        self.last_progress_report = time.time()
    
    def check_progress_interval(self):
        """检查是否需要报告进度"""
        if time.time() - self.last_progress_report >= PROGRESS_REPORT_INTERVAL:
            self.report_progress()
    
    def run_command(self, cmd: List[str], timeout: int = None, retries: int = 3) -> Dict:
        """运行命令，支持重试"""
        self.log(f"执行命令: {' '.join(cmd)}")
        
        for attempt in range(retries):
            try:
                result = subprocess.run(
                    cmd,
                    cwd=PROJECT_ROOT,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    encoding='utf-8'
                )
                
                if result.returncode == 0:
                    return {'success': True, 'stdout': result.stdout, 'stderr': result.stderr}
                else:
                    self.log(f"命令失败 (尝试 {attempt + 1}/{retries}): {result.stderr}", 'WARNING')
                    if attempt < retries - 1:
                        self.log("等待5秒后重试...")
                        time.sleep(5)
                        # 尝试启动代理
                        self.try_start_proxy()
                        
            except subprocess.TimeoutExpired:
                self.log(f"命令超时 (尝试 {attempt + 1}/{retries})", 'WARNING')
                if attempt < retries - 1:
                    self.log("等待5秒后重试...")
                    time.sleep(5)
                    
            except Exception as e:
                self.log(f"命令执行异常: {e}", 'ERROR')
                if attempt < retries - 1:
                    time.sleep(5)
        
        return {'success': False, 'stdout': '', 'stderr': 'Command failed after retries'}
    
    def try_start_proxy(self):
        """尝试启动代理"""
        self.log("尝试检查/启动代理...")
        try:
            # 检查代理是否运行
            result = subprocess.run(
                ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', 
                 '--proxy', 'http://127.0.0.1:7890', 'https://api.binance.com/api/v3/ping'],
                timeout=10
            )
            if result.returncode == 0:
                self.log("代理已正常运行")
                return True
        except:
            pass
        
        self.log("代理可能未运行，尝试启动ShellCrash...")
        # 这里需要根据实际情况启动代理
        return False
    
    def copy_strategy_file(self):
        """复制策略文件到strategies目录"""
        src = WORKSPACE_DIR / 'HighRateSowing.py'
        dst = STRATEGIES_DIR / 'HighRateSowing.py'
        
        if src.exists():
            shutil.copy2(src, dst)
            self.log(f"已复制策略文件: {src} -> {dst}")
            return True
        else:
            self.log(f"策略文件不存在: {src}", 'ERROR')
            return False
    
    def create_config_for_pairs(self, pairs: List[str], config_name: str) -> Path:
        """创建指定交易对的配置文件"""
        base_config = WORKSPACE_DIR / 'config.json'
        config_path = WORKSPACE_DIR / config_name
        
        if base_config.exists():
            with open(base_config, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 修改交易对列表
            config['exchange']['pair_whitelist'] = pairs
            config['bot_name'] = f"high_rate_sowing_{config_name.replace('.json', '').replace('config_', '')}"
            config['data_dir'] = 'user_data/data/binance'
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            
            self.log(f"已创建配置文件: {config_path} (交易对: {pairs})")
            return config_path
        else:
            self.log(f"基础配置文件不存在: {base_config}", 'ERROR')
            return None
    
    def run_backtest(self, config_path: Path, timerange: str, 
                     pairs: Optional[List[str]] = None) -> Dict:
        """运行回测"""
        self.current_task = f"回测: {config_path.name}, 时间范围: {timerange}"
        self.report_progress()
        
        cmd = [
            'python', '-m', 'freqtrade', 'backtesting',
            '-c', str(config_path.relative_to(PROJECT_ROOT)),
            '--strategy', 'HighRateSowing',
            '--timerange', timerange,
            '--datadir', 'user_data/data/binance',
            '--cache', 'none'
        ]
        
        if pairs:
            cmd.extend(['--pairs', ','.join(pairs)])
        
        result = self.run_command(cmd, timeout=3600)
        
        if result['success']:
            self.log(f"回测完成: {config_path.name}")
            # 分析结果
            return self.parse_backtest_result(result['stdout'])
        else:
            self.log(f"回测失败: {result['stderr']}", 'ERROR')
            return {'success': False}
    
    def run_hyperopt(self, config_path: Path, timerange: str,
                     epochs: int = HYPEROPT_EPOCHS,
                     min_trades: int = HYPEROPT_MIN_TRADES,
                     spaces: str = HYPEROPT_SPACES) -> Dict:
        """运行参数优化"""
        self.current_task = f"参数优化: {config_path.name}, 时间范围: {timerange}"
        self.report_progress()
        
        cmd = [
            'python', '-m', 'freqtrade', 'hyperopt',
            '-c', str(config_path.relative_to(PROJECT_ROOT)),
            '--strategy', 'HighRateSowing',
            '--strategy-path', 'user_data/high_rate_sowing',
            '--timeframe', '1m',
            '--timerange', timerange,
            '--hyperopt-loss', HYPEROPT_LOSS,
            '--epochs', str(epochs),
            '--spaces', spaces,
            '--min-trades', str(min_trades),
            '-j', '1',
            '--random-state', '42'
        ]
        
        result = self.run_command(cmd, timeout=7200)  # 2小时超时
        
        if result['success']:
            self.log(f"参数优化完成: {config_path.name}")
            return self.parse_hyperopt_result(result['stdout'])
        else:
            self.log(f"参数优化失败: {result['stderr']}", 'ERROR')
            return {'success': False}
    
    def parse_backtest_result(self, output: str) -> Dict:
        """解析回测结果"""
        result = {'success': True, 'trades': 0, 'profit': 0, 'win_rate': 0}
        
        # 从输出中提取关键指标
        lines = output.split('\n')
        for line in lines:
            if 'Total trades' in line or '交易总数' in line:
                try:
                    trades = int(line.split(':')[1].strip().split()[0])
                    result['trades'] = trades
                except:
                    pass
            if 'Total profit' in line or '总盈利' in line or 'Profit' in line:
                try:
                    profit_str = line.split(':')[1].strip()
                    # 提取百分比
                    if '%' in profit_str:
                        profit = float(profit_str.replace('%', '').strip())
                        result['profit'] = profit
                except:
                    pass
        
        self.log(f"回测结果: 交易次数={result['trades']}, 盈利={result['profit']}%")
        return result
    
    def parse_hyperopt_result(self, output: str) -> Dict:
        """解析参数优化结果"""
        result = {'success': True, 'best_params': {}, 'trades': 0, 'profit': 0}
        
        # 从输出中提取最佳参数
        lines = output.split('\n')
        for line in lines:
            if 'Best result' in line or '最佳结果' in line:
                # 解析最佳结果
                pass
        
        return result
    
    def get_hyperopt_top_results(self, n: int = 50) -> List[Dict]:
        """获取hyperopt最佳结果"""
        # 分析hyperopt结果文件
        results = []
        
        # 查找最近的结果文件
        result_files = list(HYPEROPT_RESULTS_DIR.glob('*.pickle'))
        if result_files:
            latest_file = max(result_files, key=lambda x: x.stat().st_mtime)
            self.log(f"分析hyperopt结果文件: {latest_file}")
            # TODO: 使用freqtrade的hyperopt-list命令获取结果
        
        return results
    
    def git_commit(self, message: str):
        """提交代码变更"""
        self.log(f"提交代码: {message}")
        result = subprocess.run(
            ['python', str(PROJECT_ROOT / 'user_data' / 'common' / 'git_commit.py'), message],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )
        self.log(f"提交结果: {result.stdout}")
    
    def check_backtest_trades(self, result: Dict, min_trades: int, max_trades: int) -> bool:
        """检查回测交易次数是否在合理范围"""
        trades = result.get('trades', 0)
        if trades < min_trades:
            self.log(f"交易次数太少 ({trades} < {min_trades}), 需要放宽参数", 'WARNING')
            return False
        elif trades > max_trades:
            self.log(f"交易次数太多 ({trades} > {max_trades}), 需要收紧参数", 'WARNING')
            return False
        else:
            self.log(f"交易次数合理 ({trades} 在 [{min_trades}, {max_trades}] 范围内)")
            return True
    
    def adjust_strategy_parameters(self, direction: str = 'looser'):
        """调整策略参数"""
        # TODO: 根据回测结果自动调整参数范围
        self.log(f"调整策略参数方向: {direction}")
        pass
    
    def run_step1_all_pairs_backtest(self):
        """步骤1：所有交易对回测"""
        self.current_step = 1
        self.log("=" * 60)
        self.log("步骤1：所有交易对回测（BTC/ETH/SOL）")
        self.log("=" * 60)
        
        # 复制策略文件
        self.copy_strategy_file()
        
        # 创建配置文件
        config_path = self.create_config_for_pairs(ALL_PAIRS, 'config_step1_all.json')
        
        # 运行回测
        result = self.run_backtest(config_path, f"{RECENT_2_MONTHS_START}-{RECENT_2_MONTHS_END}")
        
        # 检查交易次数
        # 标准：2个月50-2000次交易
        passed = self.check_backtest_trades(result, 50, 2000)
        
        if not passed:
            self.log("需要调整策略参数，放宽条件")
            # TODO: 调整参数后重新回测
            return False
        
        self.log("步骤1完成")
        return True
    
    def run_step2_single_pair_backtest(self):
        """步骤2：单个交易对回测"""
        self.current_step = 2
        self.log("=" * 60)
        self.log("步骤2：单个交易对回测")
        self.log("=" * 60)
        
        for pair in ALL_PAIRS:
            self.log(f"处理交易对: {pair}")
            
            # 创建单个交易对的配置文件
            config_name = f"config_step2_{pair.replace('/', '_').replace(':', '_')}.json"
            config_path = self.create_config_for_pairs([pair], config_name)
            
            # 运行回测
            result = self.run_backtest(config_path, f"{RECENT_2_MONTHS_START}-{RECENT_2_MONTHS_END}")
            
            # 检查交易次数
            # 标准：2个月10-1000次交易
            passed = self.check_backtest_trades(result, 10, 1000)
            
            if not passed:
                self.log(f"{pair} 需要调整策略参数")
                # TODO: 调整参数后重新回测
                return False
        
        self.log("步骤2完成")
        return True
    
    def run_step3_all_pairs_hyperopt(self):
        """步骤3：所有交易对参数优化"""
        self.current_step = 3
        self.log("=" * 60)
        self.log("步骤3：所有交易对参数优化")
        self.log("=" * 60)
        
        config_path = WORKSPACE_DIR / 'config_step1_all.json'
        
        # 运行参数优化
        result = self.run_hyperopt(config_path, f"{RECENT_2_MONTHS_START}-{RECENT_2_MONTHS_END}")
        
        # 检查结果
        # 标准：交易次数 >= 100, 正收益 >= 10%
        if result.get('trades', 0) < 100 or result.get('profit', 0) < 10:
            self.log("参数优化结果未达标，需要分析问题")
            # TODO: 分析问题并调整
            return False
        
        self.log("步骤3完成")
        return True
    
    def run_step4_single_pair_hyperopt(self):
        """步骤4：单个交易对参数优化"""
        self.current_step = 4
        self.log("=" * 60)
        self.log("步骤4：单个交易对参数优化")
        self.log("=" * 60)
        
        for pair in ALL_PAIRS:
            self.log(f"处理交易对: {pair}")
            
            config_name = f"config_step2_{pair.replace('/', '_').replace(':', '_')}.json"
            config_path = WORKSPACE_DIR / config_name
            
            # 运行参数优化
            result = self.run_hyperopt(config_path, f"{RECENT_2_MONTHS_START}-{RECENT_2_MONTHS_END}")
            
            # 检查结果
            # 标准：交易次数 >= 8, 正收益 >= 10%
            if result.get('trades', 0) < 8 or result.get('profit', 0) < 10:
                self.log(f"{pair} 参数优化结果未达标")
                # TODO: 分析问题并调整
                return False
        
        self.log("步骤4完成")
        return True
    
    def run_optimization_workflow(self):
        """执行完整的优化工作流"""
        self.log("开始优化工作流")
        self.start_time = time.time()
        
        try:
            # 步骤1：所有交易对回测
            if not self.run_step1_all_pairs_backtest():
                self.log("步骤1失败，停止工作流")
                return False
            
            # 提交变更
            self.git_commit("步骤1完成：所有交易对回测")
            
            # 步骤2：单个交易对回测
            if not self.run_step2_single_pair_backtest():
                self.log("步骤2失败，停止工作流")
                return False
            
            self.git_commit("步骤2完成：单个交易对回测")
            
            # 步骤3：所有交易对参数优化
            if not self.run_step3_all_pairs_hyperopt():
                self.log("步骤3失败，停止工作流")
                return False
            
            self.git_commit("步骤3完成：所有交易对参数优化")
            
            # 步骤4：单个交易对参数优化
            if not self.run_step4_single_pair_hyperopt():
                self.log("步骤4失败，停止工作流")
                return False
            
            self.git_commit("步骤4完成：单个交易对参数优化")
            
            # TODO: 步骤5和6
            
            self.log("优化工作流完成")
            return True
            
        except Exception as e:
            self.log(f"工作流异常: {e}", 'ERROR')
            return False


def main():
    workflow = OptimizationWorkflow()
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        step = sys.argv[1]
        if step == '1':
            workflow.run_step1_all_pairs_backtest()
        elif step == '2':
            workflow.run_step2_single_pair_backtest()
        elif step == '3':
            workflow.run_step3_all_pairs_hyperopt()
        elif step == '4':
            workflow.run_step4_single_pair_hyperopt()
        elif step == 'all':
            workflow.run_optimization_workflow()
        else:
            print(f"未知步骤: {step}")
            print("可用步骤: 1, 2, 3, 4, all")
    else:
        # 默认运行完整工作流
        workflow.run_optimization_workflow()


if __name__ == '__main__':
    main()