#!/bin/bash

# Git Sync - 通用 Git 同步工具
# 功能：自动提交、拉取、推送代码，支持网络重试
# 用法：git-sync [commit-message] [branch-name]
#       git-sync --push-only
#       git-sync --pull-only

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认配置
MAX_RETRIES=3
RETRY_DELAY=5
PROXY_HOST="127.0.0.1"
PROXY_PORT="7890"

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

# 检查是否有未提交的更改
has_changes() {
    [ -n "$(git status --porcelain)" ]
}

# 检查是否有未推送的提交
has_unpushed() {
    local branch=$(get_current_branch)
    local upstream=$(git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || echo "origin/$branch")
    [ -n "$(git log $upstream..HEAD --oneline 2>/dev/null)" ]
}

# 主函数
main() {
    local mode="sync"
    local commit_msg=""
    local branch=""
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --push-only)
                mode="push"
                shift
                ;;
            --pull-only)
                mode="pull"
                shift
                ;;
            --help|-h)
                echo "用法: git-sync [commit-message] [branch-name]"
                echo "       git-sync --push-only"
                echo "       git-sync --pull-only"
                echo ""
                echo "选项:"
                echo "  --push-only    仅推送已有提交"
                echo "  --pull-only    仅拉取最新代码"
                echo "  --help, -h     显示帮助信息"
                exit 0
                ;;
            *)
                if [ -z "$commit_msg" ]; then
                    commit_msg="$1"
                elif [ -z "$branch" ]; then
                    branch="$1"
                fi
                shift
                ;;
        esac
    done
    
    # 检查是否在 git 仓库中
    if [ ! -d ".git" ]; then
        log_error "当前目录不是 Git 仓库"
        exit 1
    fi
    
    # 设置代理
    set_proxy
    
    # 获取当前分支
    local current_branch=$(get_current_branch)
    [ -z "$branch" ] && branch="$current_branch"
    
    log_info "当前分支: $current_branch"
    
    case $mode in
        pull)
            log_info "模式: 仅拉取"
            git_retry "git pull origin $branch"
            log_success "拉取完成"
            ;;
        push)
            log_info "模式: 仅推送"
            if has_unpushed; then
                git_retry "git push origin $branch"
                log_success "推送完成"
            else
                log_info "没有需要推送的提交"
            fi
            ;;
        sync)
            log_info "模式: 完整同步（提交 + 拉取 + 推送）"
            
            # 1. 检查是否有更改
            if has_changes; then
                # 生成提交信息
                if [ -z "$commit_msg" ]; then
                    local changed_files=$(git diff --name-only | head -5 | tr '\n' ', ' | sed 's/,$//')
                    commit_msg="更新: $changed_files"
                    [ $(git diff --name-only | wc -l) -gt 5 ] && commit_msg="$commit_msg 等"
                fi
                
                # 2. 添加所有更改
                log_info "添加更改到暂存区..."
                git add -A
                
                # 3. 提交
                log_info "提交更改: $commit_msg"
                git commit -m "$commit_msg"
            else
                log_info "没有需要提交的更改"
            fi
            
            # 4. 拉取最新代码
            log_info "拉取远程最新代码..."
            if ! git_retry "git pull --rebase origin $branch"; then
                log_error "拉取失败，可能存在冲突，请手动解决后重试"
                exit 1
            fi
            
            # 5. 推送
            if has_unpushed || has_changes; then
                log_info "推送到远程仓库..."
                if ! git_retry "git push origin $branch"; then
                    log_error "推送失败"
                    exit 1
                fi
                log_success "推送完成"
            else
                log_info "没有需要推送的提交"
            fi
            
            log_success "同步完成！"
            ;;
    esac
}

# 执行主函数
main "$@"
