#!/usr/bin/env python
"""
BTC全仓策略 - 账号1 调试启动脚本
支持在Python中打断点进行调试

使用方法：
1. 在IDE中打开此文件（如PyCharm）
2. 在BTCFullPosition2_1.py中设置断点
3. 运行此脚本进行调试
"""

import os
import sys
import shutil
import json
import logging
from pathlib import Path

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent
os.chdir(PROJECT_ROOT)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_and_copy_strategy():
    """检查并复制策略文件"""
    source_strategy = Path("user_data/btc_account1/BTCFullPosition2_1.py")
    dest_strategy = Path("user_data/strategies/BTCFullPosition2_1.py")
    
    if source_strategy.exists():
        logger.info(f"✓ 找到策略文件: {source_strategy}")
        shutil.copy2(source_strategy, dest_strategy)
        logger.info(f"✓ 已复制策略文件到 {dest_strategy}")
        return "BTCFullPosition2_1"
    else:
        logger.warning(f"⚠️  警告：未找到策略文件，使用默认策略 BTCFullPosition2")
        return "BTCFullPosition2"


def check_and_copy_params():
    """检查并复制策略参数文件"""
    source_params = Path("user_data/btc_account1/BTCFullPosition2_1.json")
    dest_params = Path("user_data/strategies/BTCFullPosition2_1.json")
    
    if source_params.exists():
        logger.info(f"✓ 找到参数文件: {source_params}")
        shutil.copy2(source_params, dest_params)
        logger.info(f"✓ 已复制参数文件到 {dest_params}")
        return True
    else:
        logger.warning(f"⚠️  警告：未找到参数文件，将使用代码默认参数")
        return False


def check_api_key(config_path):
    """检查API密钥"""
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    api_key = config.get('exchange', {}).get('key', '')
    if api_key.startswith('YOUR_') or api_key == '':
        logger.warning("⚠️  警告：检测到默认 API 密钥")
        logger.warning("请在 config_live.json 中设置真实的 Binance API Key 和 Secret")
        logger.warning("（将无法执行真实交易）") 
        response = input("\n[Y] 继续启动    [N] 取消退出\n请选择: ").strip().upper()
        if response == 'N':
            logger.info("已取消启动")
            return False
    return True


def get_run_mode(config_path):
    """读取运行模式"""
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    dry_run = config.get('dry_run', True)
    if dry_run:
        return "模拟盘"
    else:
        return "实盘"


def confirm_live_mode(mode):
    """确认实盘模式"""
    if mode == "实盘":
        logger.warning("")
        logger.warning("=" * 40)
        logger.warning("  警告：即将启动实盘交易模式！")
        logger.warning("=" * 40)
        logger.warning("")
        response = input("[Y] 确认启动实盘    [N] 取消退出\n请选择: ").strip().upper()
        if response == 'N':
            logger.info("已取消启动")
            return False
    return True


def create_log_dir():
    """创建日志目录"""
    log_dir = Path("user_data/logs")
    log_dir.mkdir(exist_ok=True)


def start_freqtrade(config_path, strategy_name):
    """启动 freqtrade"""
    logger.info("")
    logger.info("正在启动策略...")
    logger.info("按 Ctrl+C 可停止运行")
    logger.info("")
    
    try:
        # 使用 freqtrade 的 main 函数
        from freqtrade.main import main as freqtrade_main
        
        # 构建命令行参数
        args = [
            'freqtrade',
            'trade',
            '--config', str(config_path),
            '--strategy', strategy_name,
            '--strategy-path', 'user_data/strategies',
            '--logfile', 'user_data/logs/btc_account1.log'
        ]
        
        # 替换 sys.argv
        sys.argv = args
        
        # 启动 freqtrade
        freqtrade_main()
        
    except KeyboardInterrupt:
        logger.info("")
        logger.info("策略已停止")
    except Exception as e:
        logger.error(f"启动失败: {e}", exc_info=True)
        raise


def main():
    """主函数"""
    logger.info("=" * 40)
    logger.info("BTC全仓策略 - 账号1调试启动")
    logger.info("=" * 40)
    logger.info("")
    
    # 检查配置文件
    config_path = Path("user_data/btc_account1/config_live.json")
    if not config_path.exists():
        logger.error(f"❌ 错误：未找到配置文件 {config_path}")
        sys.exit(1)
    
    # 检查并复制策略文件
    strategy_name = check_and_copy_strategy()
    
    # 检查并复制参数文件
    check_and_copy_params()
    
    # 检查 API 密钥
    if not check_api_key(config_path):
        sys.exit(0)
    
    # 获取运行模式
    mode = get_run_mode(config_path)
    
    # 创建日志目录
    create_log_dir()
    
    # 显示配置信息
    logger.info("策略: %s", strategy_name)
    logger.info("币种: BTC/USDT")
    logger.info("模式: %s", mode)
    logger.info("配置: user_data/btc_account1/config_live.json")
    
    params_path = Path("user_data/btc_account1/BTCFullPosition2_1.json")
    if params_path.exists():
        logger.info("参数: user_data/btc_account1/BTCFullPosition2_1.json (独立参数)")
    else:
        logger.info("参数: 使用代码默认值")
    
    logger.info("API端口: 8091")
    logger.info("")
    
    # 确认实盘模式
    if not confirm_live_mode(mode):
        sys.exit(0)
    
    # 启动 freqtrade
    start_freqtrade(config_path, strategy_name)


if __name__ == "__main__":
    main()
