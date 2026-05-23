#!/usr/bin/env python3
"""
Hyperopt 结果解析脚本
自动解析最佳参数并更新策略配置
"""

import json
import re
import sys
from pathlib import Path

def parse_hyperopt_log(log_file: str) -> dict:
    """解析 hyperopt 日志文件，提取最佳参数"""
    
    with open(log_file, 'r') as f:
        content = f.read()
    
    # 查找最佳结果行
    # 格式: Best result: objective: -0.123, params: {...}
    best_match = re.search(r'Best result:.*?params:\s*(\{.*?\})', content, re.DOTALL)
    
    if not best_match:
        # 尝试另一种格式
        # 查找最后几行中的最佳参数
        lines = content.split('\n')
        for line in reversed(lines):
            if 'Best result' in line or 'objective' in line:
                # 提取参数
                param_match = re.search(r'\{.*\}', line)
                if param_match:
                    try:
                        params = json.loads(param_match.group())
                        return params
                    except:
                        continue
    
    if best_match:
        params_str = best_match.group(1)
        # 清理参数字符串
        params_str = params_str.replace("'", '"')
        params_str = re.sub(r'np\.float\d+\(([\d.]+)\)', r'\1', params_str)
        
        try:
            params = json.loads(params_str)
            return params
        except Exception as e:
            print(f"解析参数失败: {e}")
            return None
    
    return None


def extract_best_params_from_results(results_dir: str) -> dict:
    """从 hyperopt 结果文件中提取最佳参数"""
    
    results_path = Path(results_dir)
    
    # 查找最新的 hyperopt 结果文件
    result_files = list(results_path.glob('hyperopt_results_*.json'))
    
    if not result_files:
        return None
    
    latest_file = max(result_files, key=lambda x: x.stat().st_mtime)
    
    with open(latest_file, 'r') as f:
        data = json.load(f)
    
    # 提取最佳参数
    if 'best_params' in data:
        return data['best_params']
    
    return None


def generate_strategy_params(best_params: dict) -> str:
    """生成策略参数配置字符串"""
    
    if not best_params:
        return "# 未找到有效参数"
    
    lines = ["# Hyperopt 优化参数", ""]
    
    for key, value in best_params.items():
        if isinstance(value, float):
            lines.append(f"{key} = {value:.6f}")
        else:
            lines.append(f"{key} = {value}")
    
    return '\n'.join(lines)


def main():
    """主函数"""
    
    if len(sys.argv) < 2:
        print("用法: python parse_hyperopt.py <log_file|results_dir>")
        print("示例: python parse_hyperopt.py logs/hyperopt_20260523_003000.log")
        sys.exit(1)
    
    input_path = sys.argv[1]
    
    # 判断输入类型
    path = Path(input_path)
    
    if path.is_file() and path.suffix == '.log':
        # 解析日志文件
        print(f"解析日志文件: {input_path}")
        params = parse_hyperopt_log(input_path)
    elif path.is_dir():
        # 解析结果目录
        print(f"解析结果目录: {input_path}")
        params = extract_best_params_from_results(input_path)
    else:
        print(f"错误: 无法识别的输入路径 {input_path}")
        sys.exit(1)
    
    if params:
        print("\n" + "="*50)
        print("最佳参数:")
        print("="*50)
        for key, value in params.items():
            print(f"  {key}: {value}")
        
        print("\n" + "="*50)
        print("策略参数配置:")
        print("="*50)
        print(generate_strategy_params(params))
        
        # 保存参数
        output_file = path.parent / f"best_params_{Path(input_path).stem}.json"
        with open(output_file, 'w') as f:
            json.dump(params, f, indent=2)
        print(f"\n参数已保存到: {output_file}")
    else:
        print("未能提取有效参数")
        sys.exit(1)


if __name__ == '__main__':
    main()
