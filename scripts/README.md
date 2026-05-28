# Freqtrade Git 工具

本目录包含 freqtrade 项目专用的 Git 同步和策略更新工具。

## ⚠️ 重要说明

**这些脚本仅用于 freqtrade 项目！**

- 必须在 `/opt/git/freqtrade` 项目根目录下执行
- 脚本会自动检查项目标识，防止在其他项目中误用

## 脚本列表

### 1. git-sync.sh - Git 同步工具

自动提交、拉取、推送代码到 GitHub。

**用法：**

```bash
# 在项目根目录执行
cd /opt/git/freqtrade

# 完整同步（提交+拉取+推送）
./scripts/git-sync.sh

# 带提交信息
./scripts/git-sync.sh "你的提交信息"

# 仅推送
./scripts/git-sync.sh --push-only

# 仅拉取
./scripts/git-sync.sh --pull-only
```

### 2. strategy-pull.sh - 策略更新工具

拉取策略仓库的最新代码。

**用法：**

```bash
# 在项目根目录执行
cd /opt/git/freqtrade

# 拉取最新代码
./scripts/strategy-pull.sh

# 指定分支
./scripts/strategy-pull.sh --branch=main
```

## 功能特性

- ✅ 自动检测并设置代理（127.0.0.1:7890）
- ✅ 网络重试机制（最多3次）
- ✅ 项目标识检查（防止误用）
- ✅ 彩色日志输出
- ✅ 智能提交信息生成

## 示例

### 提交新策略

```bash
cd /opt/git/freqtrade
./scripts/git-sync.sh "新增策略：HighRateSowingSL"
```

### 获取最新策略

```bash
cd /opt/git/freqtrade
./scripts/strategy-pull.sh
```

## 注意事项

1. 必须在 `/opt/git/freqtrade` 根目录执行
2. 如果在其他目录执行，脚本会报错退出
3. 网络失败会自动重试，最多3次
4. 存在冲突时需要手动解决
