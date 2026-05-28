#!/bin/bash

# Strategy Pull - Freqtrade 项目专用策略更新工具
# 功能：拉取策略仓库的最新代码，支持网络重试和代理
# 用法：./strategy-pull.sh [--branch=branch-name]
# 注意：此脚本仅用于 freqtrade 项目，必须在项目根目录执行

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 默认配置
MAX_RETRIES=3
RETRY_DELAY=5
PROXY_HOST="127.0.0.1"
PROXY_PORT="7890"
EXPECTED_REPO="/opt/git/freqtrade"
DEFAULT_BRANCH="develop"

# 打印带颜色的消息
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${CYAN}[STEP]${NC} $1"
}

# 检查是否在 freqtrade 项目根目录
check_freqtrade_project() {
    # 检查是否存在 freqtrade 特有的文件/目录
    if [ ! -d "freqtrade" ] || [ ! -d "user_data" ] || [ ! -f "setup.sh" ]; then
        log_error "此脚本仅用于 freqtrade 项目"
        log_error "请在 /opt/git/freqtrade 根目录下执行"
        log_error "当前目录: $(pwd)"
        exit 1
    fi
    
    # 检查是否在正确的仓库路径
    local current_repo=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
    
    if [ "$current_repo" != "$EXPECTED_REPO" ]; then
        log_error "当前仓库路径不正确"
        log_error "期望路径: $EXPECTED_REPO"
        log_error "当前路径: $current_repo"
        exit 1
    fi
}

# 检查代理是否可用
check_proxy() {
    if curl -s --connect-timeout 2 -x "http://${PROXY_HOST}:${PROXY_PORT}" https://github.com > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# 设置代理
set_proxy() {
    if check_proxy; then
        log_info "检测到可用代理，设置代理环境变量"
        export http_proxy="http://${PROXY_HOST}:${PROXY_PORT}"
        export https_proxy="http://${PROXY_HOST}:${PROXY_PORT}"
        export all_proxy="socks5://${PROXY_HOST}:7891"
        return 0
    else
        log_warning "代理不可用，使用直连"
        return 1
    fi
}

# 带重试的 git 操作
git_retry() {
    local cmd="$1"
    local max_attempts=${2:-$MAX_RETRIES}
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        log_info "尝试执行: $cmd (第 $attempt/$max_attempts 次)"
        
        if eval "$cmd" 2>&1; then
            return 0
        fi
        
        if [ $attempt -lt $max_attempts ]; then
            log_warning "执行失败，${RETRY_DELAY}秒后重试..."
            sleep $RETRY_DELAY
        fi
        
        attempt=$((attempt + 1))
    done
    
    log_error "执行失败，已达到最大重试次数"
    return 1
}

# 获取当前分支
get_current_branch() {
    git branch --show-current
}

# 显示策略目录
show_strategies() {
    log_info "可用的策略目录："
    echo ""
    ls -1 user_data/ | grep -E "high_rate|strategy" | while read dir; do
        echo "  - $dir"
    done
    echo ""
}

# 显示最新提交
show_latest_commit() {
    log_info "最新提交信息："
    git log -1 --pretty=format:"  提交: %h%n  作者: %an%n  日期: %ad%n  信息: %s" --date=format:'%Y-%m-%d %H:%M:%S'
    echo ""
}

# 显示更新的文件
show_updated_files() {
    log_info "更新的文件："
    git diff --name-only HEAD@{1} HEAD 2>/dev/null | head -20 | while read file; do
        echo "  - $file"
    done
    local count=$(git diff --name-only HEAD@{1} HEAD 2>/dev/null | wc -l)
    if [ $count -gt 20 ]; then
        echo "  ... 还有 $((count - 20)) 个文件"
    fi
    echo ""
}

# 主函数
main() {
    local branch="$DEFAULT_BRANCH"
    local show_diff=true
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --branch=*)
                branch="${1#*=}"
                shift
                ;;
            --no-diff)
                show_diff=false
                shift
                ;;
            --help|-h)
                echo "用法: ./strategy-pull.sh [选项]"
                echo ""
                echo "功能: 拉取策略仓库的最新代码"
                echo ""
                echo "选项:"
                echo "  --branch=NAME   指定分支 (默认: $DEFAULT_BRANCH)"
                echo "  --no-diff       不显示更新的文件"
                echo "  --help, -h      显示帮助信息"
                echo ""
                echo "注意: 此脚本仅用于 freqtrade 项目"
                echo "      必须在项目根目录 /opt/git/freqtrade 下执行"
                echo ""
                echo "示例:"
                echo "  ./strategy-pull.sh                    # 拉取默认分支的最新代码"
                echo "  ./strategy-pull.sh --branch=main      # 拉取 main 分支"
                exit 0
                ;;
            *)
                log_warning "未知参数: $1"
                shift
                ;;
        esac
    done
    
    # 检查是否在 git 仓库中
    if [ ! -d ".git" ]; then
        log_error "当前目录不是 Git 仓库"
        exit 1
    fi
    
    # 验证是否为 freqtrade 项目
    check_freqtrade_project
    
    log_step "开始获取策略最新代码"
    echo ""
    
    # 设置代理
    set_proxy
    
    # 获取当前分支
    local current_branch=$(get_current_branch)
    log_info "当前分支: $current_branch"
    log_info "目标分支: $branch"
    log_info "仓库路径: $EXPECTED_REPO"
    echo ""
    
    # 如果当前分支与目标分支不同，切换分支
    if [ "$current_branch" != "$branch" ]; then
        log_info "切换到分支: $branch"
        git checkout "$branch"
        echo ""
    fi
    
    # 保存当前 HEAD
    local old_head=$(git rev-parse HEAD)
    
    # 拉取最新代码
    log_step "拉取远程最新代码..."
    if ! git_retry "git pull --rebase origin $branch"; then
        log_error "拉取失败，可能存在冲突，请手动解决后重试"
        exit 1
    fi
    echo ""
    
    # 获取新的 HEAD
    local new_head=$(git rev-parse HEAD)
    
    # 显示结果
    if [ "$old_head" = "$new_head" ]; then
        log_success "代码已是最新，无需更新"
    else
        log_success "代码更新成功！"
        echo ""
        
        # 显示最新提交
        show_latest_commit
        
        # 显示更新的文件
        if [ "$show_diff" = true ]; then
            show_updated_files
        fi
    fi
    
    echo ""
    
    # 显示策略目录
    show_strategies
    
    log_success "获取完成！"
}

# 执行主函数
main "$@"
