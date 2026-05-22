#!/usr/bin/env python3
"""
通用 Git 提交脚本
自动检测变更文件并提交到 Git 仓库
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_command(cmd: list[str], cwd: str = None) -> tuple[int, str, str]:
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, '', str(e)


def get_git_status(cwd: str) -> dict:
    """获取 Git 状态"""
    # 获取未跟踪的文件
    code, stdout, stderr = run_command(['git', 'status', '--porcelain'], cwd)
    if code != 0:
        return {'error': stderr}
    
    changes = {
        'modified': [],
        'added': [],
        'deleted': [],
        'untracked': [],
        'renamed': []
    }
    
    for line in stdout.strip().split('\n'):
        if not line:
            continue
        status = line[:2].strip()
        filepath = line[3:].strip()
        
        if status == 'M':
            changes['modified'].append(filepath)
        elif status == 'A':
            changes['added'].append(filepath)
        elif status == 'D':
            changes['deleted'].append(filepath)
        elif status == '??':
            changes['untracked'].append(filepath)
        elif status.startswith('R'):
            changes['renamed'].append(filepath)
    
    return changes


def get_diff_summary(cwd: str) -> str:
    """获取变更摘要"""
    code, stdout, stderr = run_command(['git', 'diff', '--stat'], cwd)
    if code == 0 and stdout.strip():
        return stdout.strip()
    
    # 检查暂存区的变更
    code, stdout, stderr = run_command(['git', 'diff', '--cached', '--stat'], cwd)
    if code == 0 and stdout.strip():
        return stdout.strip()
    
    return ''


def generate_commit_message(message: str = None, changes: dict = None) -> str:
    """生成提交消息"""
    if message:
        return message
    
    # 自动生成提交消息
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    parts = []
    if changes:
        if changes['modified']:
            parts.append(f"修改 {len(changes['modified'])} 个文件")
        if changes['added']:
            parts.append(f"添加 {len(changes['added'])} 个文件")
        if changes['deleted']:
            parts.append(f"删除 {len(changes['deleted'])} 个文件")
        if changes['untracked']:
            parts.append(f"新增 {len(changes['untracked'])} 个文件")
        if changes['renamed']:
            parts.append(f"重命名 {len(changes['renamed'])} 个文件")
    
    if parts:
        return f"[{timestamp}] " + ", ".join(parts)
    else:
        return f"[{timestamp}] 更新代码"


def add_files(cwd: str, files: list[str] = None) -> bool:
    """添加文件到暂存区"""
    if files:
        # 添加指定文件
        for f in files:
            code, _, stderr = run_command(['git', 'add', f], cwd)
            if code != 0:
                print(f"❌ 添加文件失败: {f}")
                print(f"   错误: {stderr}")
                return False
    else:
        # 添加所有变更
        code, _, stderr = run_command(['git', 'add', '.'], cwd)
        if code != 0:
            print(f"❌ 添加文件失败: {stderr}")
            return False
    
    return True


def commit(cwd: str, message: str) -> bool:
    """提交变更"""
    code, stdout, stderr = run_command(['git', 'commit', '-m', message], cwd)
    if code != 0:
        if 'nothing to commit' in stderr or 'nothing to commit' in stdout:
            print("ℹ️  没有需要提交的变更")
            return True
        print(f"❌ 提交失败: {stderr}")
        return False
    
    print(f"✅ 提交成功: {message}")
    return True


def push(cwd: str, branch: str = None) -> bool:
    """推送到远程仓库"""
    # 获取当前分支
    if not branch:
        code, stdout, stderr = run_command(['git', 'branch', '--show-current'], cwd)
        if code != 0:
            print(f"❌ 获取当前分支失败: {stderr}")
            return False
        branch = stdout.strip()
    
    # 推送
    print(f"📤 推送到远程仓库 (分支: {branch})...")
    code, stdout, stderr = run_command(['git', 'push', 'origin', branch], cwd)
    if code != 0:
        print(f"❌ 推送失败: {stderr}")
        return False
    
    print(f"✅ 推送成功")
    return True


def git_commit(
    cwd: str = None,
    message: str = None,
    files: list[str] = None,
    push_after_commit: bool = True,
    dry_run: bool = False
) -> bool:
    """
    主函数：执行 Git 提交流程
    
    Args:
        cwd: 工作目录（默认当前目录）
        message: 提交消息（自动生成如果未提供）
        files: 要添加的文件列表（默认添加所有变更）
        push_after_commit: 提交后是否推送
        dry_run: 仅显示将要执行的操作，不实际执行
    
    Returns:
        bool: 是否成功
    """
    if cwd is None:
        cwd = os.getcwd()
    
    print(f"📁 工作目录: {cwd}")
    print()
    
    # 检查是否在 Git 仓库中
    code, _, stderr = run_command(['git', 'rev-parse', '--git-dir'], cwd)
    if code != 0:
        print(f"❌ 不是 Git 仓库: {cwd}")
        return False
    
    # 获取状态
    changes = get_git_status(cwd)
    if 'error' in changes:
        print(f"❌ 获取 Git 状态失败: {changes['error']}")
        return False
    
    # 统计变更
    total_changes = sum(len(v) for v in changes.values())
    if total_changes == 0:
        print("ℹ️  没有需要提交的变更")
        return True
    
    # 显示变更
    print("📋 变更文件:")
    for category, files_list in changes.items():
        if files_list:
            print(f"  {category}: {len(files_list)} 个文件")
            for f in files_list[:5]:  # 只显示前5个
                print(f"    - {f}")
            if len(files_list) > 5:
                print(f"    ... 还有 {len(files_list) - 5} 个文件")
    print()
    
    # 显示 diff 摘要
    diff_summary = get_diff_summary(cwd)
    if diff_summary:
        print("📊 变更统计:")
        print(diff_summary)
        print()
    
    # 生成提交消息
    commit_message = generate_commit_message(message, changes)
    print(f"💬 提交消息: {commit_message}")
    print()
    
    # Dry run 模式
    if dry_run:
        print("🔍 [Dry Run] 仅显示操作，不实际执行")
        return True
    
    # 添加文件
    print("➕ 添加文件到暂存区...")
    if not add_files(cwd, files):
        return False
    
    # 提交
    if not commit(cwd, commit_message):
        return False
    
    # 推送
    if push_after_commit:
        if not push(cwd):
            return False
    
    return True


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='通用 Git 提交脚本')
    parser.add_argument('message', nargs='?', help='提交消息')
    parser.add_argument('-d', '--dir', '--cwd', dest='cwd', help='工作目录')
    parser.add_argument('-f', '--files', nargs='+', help='要添加的文件')
    parser.add_argument('--no-push', action='store_true', help='提交后不推送')
    parser.add_argument('--dry-run', action='store_true', help='仅显示操作，不实际执行')
    
    args = parser.parse_args()
    
    success = git_commit(
        cwd=args.cwd,
        message=args.message,
        files=args.files,
        push_after_commit=not args.no_push,
        dry_run=args.dry_run
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
