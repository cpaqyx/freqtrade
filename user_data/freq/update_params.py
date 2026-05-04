"""
自动更新策略最优参数

从Hyperopt生成的JSON文件中读取最优参数，
并自动更新到策略文件的默认值中。

使用方法:
    python user_data/freq/update_params.py
"""

import json
import re
import os
from pathlib import Path


def load_hyperopt_params(json_file):
    """加载hyperopt生成的参数文件"""
    if not os.path.exists(json_file):
        print(f"错误：找不到参数文件 {json_file}")
        print("请先运行 hyperopt 优化")
        return None
    
    with open(json_file, 'r', encoding='utf-8') as f:
        params = json.load(f)
    
    return params


def update_strategy_file(strategy_file, params):
    """更新策略文件中的默认参数"""
    if not os.path.exists(strategy_file):
        print(f"错误：找不到策略文件 {strategy_file}")
        return False
    
    # 读取策略文件
    with open(strategy_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取参数
    params_dict = params.get('params', {})
    buy_params = params_dict.get('buy', {})
    sell_params = params_dict.get('sell', {})
    roi_params = params_dict.get('roi', {})
    stoploss_params = params_dict.get('stoploss', {})
    
    # 合并所有参数
    all_params = {**buy_params, **sell_params}
    
    # 更新参数
    updated_count = 0
    for param_name, param_value in all_params.items():
        # 构建正则表达式匹配参数定义
        # 例如: bb_length = IntParameter(15, 40, default=20, ...)
        
        if isinstance(param_value, int):
            pattern = rf"({param_name}\s*=\s*IntParameter\([^,]+,\s*[^,]+,\s*default=)(\d+)"
            replacement = rf"\g<1>{param_value}"
        elif isinstance(param_value, float):
            pattern = rf"({param_name}\s*=\s*DecimalParameter\([^,]+,\s*[^,]+,\s*[^,]*,\s*default=)([\d.]+)"
            replacement = rf"\g<1>{param_value}"
        elif isinstance(param_value, bool):
            pattern = rf"({param_name}\s*=\s*CategoricalParameter\([^,]+,\s*default=)(True|False)"
            replacement = rf"\g<1>{param_value}"
        else:
            continue
        
        # 执行替换
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            updated_count += 1
            content = new_content
            print(f"✓ 更新参数: {param_name} = {param_value}")
    
    # 更新 minimal_roi
    if roi_params:
        roi_str = str(roi_params).replace("'", '"')
        pattern = r'(minimal_roi\s*=\s*){[^}]+}'
        replacement = rf'\g<1>{roi_str}'
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            updated_count += 1
            content = new_content
            print(f"✓ 更新参数: minimal_roi = {roi_params}")
    
    # 更新 stoploss
    if 'stoploss' in stoploss_params:
        stoploss_value = stoploss_params['stoploss']
        pattern = r'(stoploss\s*=\s*)([-\d.]+)'
        replacement = rf'\g<1>{stoploss_value}'
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            updated_count += 1
            content = new_content
            print(f"✓ 更新参数: stoploss = {stoploss_value}")
    
    # 写回文件
    if updated_count > 0:
        with open(strategy_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"\n✅ 成功更新 {updated_count} 个参数到策略文件")
        return True
    else:
        print("\n⚠️ 没有找到需要更新的参数")
        return False


def show_params_summary(params):
    """显示参数摘要"""
    print("\n" + "="*60)
    print("                   优化参数摘要")
    print("="*60)
    
    params_dict = params.get('params', {})
    
    # Buy参数
    buy_params = params_dict.get('buy', {})
    if buy_params:
        print("\n【Buy Parameters】")
        for k, v in buy_params.items():
            print(f"  {k:30s} = {v}")
    
    # Sell参数
    sell_params = params_dict.get('sell', {})
    if sell_params:
        print("\n【Sell Parameters】")
        for k, v in sell_params.items():
            print(f"  {k:30s} = {v}")
    
    # ROI参数
    roi_params = params_dict.get('roi', {})
    if roi_params:
        print("\n【ROI】")
        print(f"  {roi_params}")
    
    # Stoploss参数
    stoploss_params = params_dict.get('stoploss', {})
    if stoploss_params:
        print("\n【Stoploss】")
        for k, v in stoploss_params.items():
            print(f"  {k:30s} = {v}")
    
    # 性能指标
    print("\n【Performance Metrics】")
    results = params.get('results_metrics', {})
    if results:
        print(f"  Total Profit:                  {results.get('profit_total_abs', 0):.2f} USDT")
        print(f"  Total Profit %:                {results.get('profit_total', 0)*100:.2f}%")
        print(f"  Total Trades:                  {results.get('total_trades', 0)}")
        print(f"  Win Rate:                      {results.get('wins', 0)}/{results.get('total_trades', 0)}")
        print(f"  Average Profit %:              {results.get('profit_mean', 0)*100:.4f}%")
        print(f"  Profit Factor:                 {results.get('profit_factor', 0):.2f}")
        print(f"  Expectancy:                    {results.get('expectancy', 0):.2f}")
        print(f"  Sharpe Ratio:                  {results.get('sharpe', 0):.2f}")
    
    print("="*60)


def main():
    """主函数"""
    # 定义文件路径
    base_dir = Path("user_data/freq")
    json_file = base_dir / "HighFreq5mStrategy.json"
    strategy_file = base_dir / "HighFreq5mStrategy.py"
    
    print("\n" + "="*60)
    print("          HighFreq5mStrategy 参数更新工具")
    print("="*60)
    print(f"\n参数文件: {json_file}")
    print(f"策略文件: {strategy_file}\n")
    
    # 加载参数
    params = load_hyperopt_params(json_file)
    if params is None:
        return
    
    # 显示参数摘要
    show_params_summary(params)
    
    # 确认更新
    print("\n是否要将这些参数更新到策略文件？")
    print("(这将修改策略文件中的默认参数值)")
    
    choice = input("\n请输入 [y/n]: ").strip().lower()
    
    if choice == 'y':
        # 备份原文件
        backup_file = str(strategy_file) + ".backup"
        import shutil
        shutil.copy(strategy_file, backup_file)
        print(f"\n✓ 已备份原文件到: {backup_file}")
        
        # 更新参数
        success = update_strategy_file(strategy_file, params)
        
        if success:
            print("\n✅ 参数更新完成！")
            print("\n下一步：")
            print("  1. 检查策略文件，确认参数正确")
            print("  2. 运行回测验证新参数")
            print("  3. 如有问题，可从备份文件恢复")
        else:
            print("\n⚠️ 参数更新失败，请检查日志")
    else:
        print("\n已取消更新")


if __name__ == "__main__":
    main()

