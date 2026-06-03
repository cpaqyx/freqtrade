# BTC Rebound Volume Strategy

## 策略概述

这是一个基于**整数关口反弹**和**成交量确认**的BTC期货策略，专为Freqtrade框架设计。

### 核心逻辑

1. **监控整数关口**
   - 可配置的整数价格关口列表（默认：65000, 64000, 63000, ..., 55000）
   - 当价格向下突破某个关口时，记录为"活跃关口"
   
2. **跟踪最低价**
   - 从关口突破后，持续跟踪该区间的最低价
   - 如果价格继续下跌到更低关口，切换跟踪新的关口
   
3. **反弹入场条件**（必须同时满足）
   - 价格向上突破关口（close > level）
   - 反弹幅度满足以下任意条件：
     - 从最低价反弹 ≥ 5%（`rebound_min_pct`）
     - 当前价格 ≥ 关口 + 1%（`level_buffer_pct`）
   
4. **成交量确认**（必须同时满足）
   - 最近1小时成交量 > 24小时平均成交量 × 1.1
   - 成交量放大 ≥ 10%

### 风控配置

- **杠杆**：固定 20x
- **仓位大小**：每次使用可用资金的 20%
- **止损**：8%（可配置）
- **追踪止损**：
  - 盈利 2% 后启动
  - 价格回撤 3% 触发
- **ROI**：
  - 立即：15%
  - 1小时：10%
  - 2小时：5%
  - 4小时：3%

---

## 文件结构

```
/opt/git/freqtrade/user_data/btc_0603/
├── BTC_Rebound_Volume_Strategy.py  # 策略主文件
├── config_dryrun.json              # 模拟运行配置
├── config_live.json                # 实盘运行配置
├── run_strategy.sh                 # 运行脚本
└── README.md                       # 此文档
```

---

## 参数配置

### 可配置参数列表

| 参数名 | 类型 | 默认值 | 范围 | 说明 |
|--------|------|--------|------|------|
| `price_levels` | List[int] | [65000,...55000] | - | 监控的整数关口 |
| `rebound_min_pct` | Decimal | 0.05 | 0.03-0.10 | 反弹幅度阈值（从最低价） |
| `level_buffer_pct` | Decimal | 0.01 | 0.005-0.03 | 关口缓冲百分比 |
| `vol_lookback_hours` | Int | 24 | 12-48 | 成交量观察窗口（小时） |
| `vol_confirm_hours` | Int | 1 | 1-4 | 成交量计算窗口（小时） |
| `vol_increase_pct` | Decimal | 0.10 | 0.05-0.30 | 成交量放大比例 |
| `stoploss_pct` | Decimal | -0.08 | -0.15~-0.03 | 止损百分比 |
| `leverage_value` | Int | 20 | - | 杠杆倍数 |
| `stake_ratio` | Decimal | 0.20 | - | 仓位比例 |

### 通过配置文件覆盖参数

可以在 `config.json` 中使用以下格式覆盖策略参数：

```json
{
  "strategy": "BTC_Rebound_Volume_Strategy",
  "rebound_min_pct": 0.06,
  "level_buffer_pct": 0.015,
  "vol_increase_pct": 0.12,
  "stoploss_pct": -0.10
}
```

---

## 运行方式

### 1. 模拟运行（Dry-Run）

```bash
# 使用运行脚本
cd /opt/git/freqtrade
./user_data/btc_0603/run_strategy.sh dryrun

# 或直接使用freqtrade命令
freqtrade trade \
    --strategy BTC_Rebound_Volume_Strategy \
    --strategy-path user_data/btc_0603 \
    --config user_data/btc_0603/config_dryrun.json \
    --dry-run
```

### 2. 实盘运行（Live Trading）

⚠️ **警告**：实盘运行将使用真实资金！

```bash
# 使用运行脚本（有确认提示）
cd /opt/git/freqtrade
./user_data/btc_0603/run_strategy.sh live

# 或直接使用freqtrade命令
freqtrade trade \
    --strategy BTC_Rebound_Volume_Strategy \
    --strategy-path user_data/btc_0603 \
    --config user_data/btc_0603/config_live.json
```

**实盘运行前请确认**：
- API Key 已正确配置并替换到 `config_live.json`
- 账户有足够的 USDT 余额
- 已在 dry-run 模式充分测试
- 了解策略风险

### 3. 回测

```bash
# 回测最近30天
cd /opt/git/freqtrade
./user_data/btc_0603/run_strategy.sh backtest --timerange 20250501-20250601

# 或使用freqtrade命令
freqtrade backtesting \
    --strategy BTC_Rebound_Volume_Strategy \
    --strategy-path user_data/btc_0603 \
    --config user_data/btc_0603/config_dryrun.json \
    --timeframe 1m \
    --timerange 20250501-20250601 \
    --trading-mode futures
```

### 4. 参数优化（Hyperopt）

```bash
# 优化入场参数
freqtrade hyperopt \
    --strategy BTC_Rebound_Volume_Strategy \
    --strategy-path user_data/btc_0603 \
    --config user_data/btc_0603/config_dryrun.json \
    --timeframe 1m \
    --timerange 20250401-20250601 \
    --spaces buy \
    --epochs 100 \
    --trading-mode futures
```

---

## 数据准备

### 下载期货数据

策略需要 1m K线数据。如果尚未下载，请执行：

```bash
freqtrade download-data \
    --exchange binance \
    --pairs BTC/USDT:USDT \
    --timeframe 1m \
    --timerange 20250101- \
    --trading-mode futures \
    --data-format-ohlcv feather
```

数据将保存到：`user_data/data/binance/BTC_USDT_USDT-1m-futures.feather`

---

## 配置文件说明

### config_dryrun.json（模拟配置）

关键配置项：
- `"dry_run": true` - 模拟模式
- `"dry_run_wallet": 10000` - 模拟钱包余额（USDT）
- `"trading_mode": "futures"` - 期货模式
- `"margin_mode": "isolated"` - 逐仓模式

### config_live.json（实盘配置）

关键配置项：
- `"dry_run": false` - 实盘模式
- `"trading_mode": "futures"` - 期货模式
- `"margin_mode": "isolated"` - 逐仓模式
- `"exchange.key"` / `"exchange.secret"` - 需替换为真实API

⚠️ **请务必替换API Key**：
```json
{
  "exchange": {
    "key": "YOUR_BINANCE_API_KEY",
    "secret": "YOUR_BINANCE_API_SECRET"
  }
}
```

---

## 监控与管理

### API Server

配置文件已启用 API Server，可通过以下方式访问：

- **地址**：http://localhost:8093
- **用户名**：admin
- **密码**：admin123

### FreqUI

启动 Web UI：

```bash
freqtrade webserver \
    --config user_data/btc_0603/config_dryrun.json
```

访问：http://localhost:8093

### 查看交易记录

```bash
freqtrade show-trades \
    --db-url sqlite:///user_data/btc_0603/tradesv3.dryrun.sqlite \
    --strategy BTC_Rebound_Volume_Strategy
```

---

## 策略优化建议

### 1. Hyperopt 参数优化

推荐优化空间：
- `buy` - 入场参数
- `sell` - 出场/止损参数
- `roi` - ROI 表（需使用 `--spaces roi`）

### 2. 回测时间范围

建议使用至少 3 个月的数据进行回测：
```bash
--timerange 20250301-20250601
```

### 3. 优化参数示例

```bash
# 优化入场和止损参数
freqtrade hyperopt \
    --strategy BTC_Rebound_Volume_Strategy \
    --strategy-path user_data/btc_0603 \
    --config user_data/btc_0603/config_dryrun.json \
    --timeframe 1m \
    --timerange 20250301-20250601 \
    --spaces buy sell \
    --epochs 200 \
    --trading-mode futures \
    --loss SharpeHyperOptLoss
```

---

## 风险提示

⚠️ **重要风险警告**

1. **杠杆风险**：20x 杠杆会放大盈亏，请确保了解期货交易风险
2. **市场风险**：加密货币市场波动剧烈，策略可能在极端行情下失效
3. **技术风险**：策略基于历史数据设计，未来市场可能表现不同
4. **资金风险**：建议先在 dry-run 模式充分测试，再考虑实盘

**建议**：
- 初期使用小仓位测试
- 定期监控策略表现
- 根据市场变化调整参数
- 设置合理的止损

---

## 技术细节

### 时间框架处理

- **运行时间框架**：1m（freqtrade 主循环）
- **成交量计算**：通过 `resample_to_hourly()` 将 1m 数据聚合为 1h
- **启动K线数**：1500 分钟（约25小时），确保足够计算24小时平均成交量

### 状态管理

策略使用以下机制跟踪状态：
- `active_levels` - 活跃关口字典
- `tracked_lows` - 最低价跟踪字典
- `breakout_times` - 突破时间记录

⚠️ 注意：在 backtesting 模式下，状态会在每次回测开始时重置。

### 入场标签（enter_tag）

入场时会生成标签记录触发原因：
- `rebound_5pct_vol_confirmed` - 5%反弹 + 成交量确认
- `level_buffer_1pct_vol_confirmed` - 关口缓冲 + 成交量确认

---

## 常见问题

### Q1: 为什么没有入场信号？

检查以下条件是否满足：
1. 价格是否跌破某个关口并反弹
2. 反弹幅度是否足够（≥5% 或 ≥关口+1%）
3. 成交量是否放大（≥110%平均）

### Q2: 回测速度慢怎么办？

1m 数据量大，回测可能较慢。建议：
- 使用较短的时间范围
- 减少启动K线数量（但至少需要1440用于计算24h成交量）
- 使用 feather 格式数据

### Q3: 如何修改监控关口？

在配置文件中添加：
```json
{
  "price_levels": [70000, 69000, 68000, 67000, 66000, 65000]
}
```

---

## 更新日志

### v1.0.0 (2026-06-03)
- 初始版本发布
- 实现整数关口监控逻辑
- 实现反弹 + 成交量确认入场条件
- 支持 futures 交易模式
- 固定20x杠杆，20%仓位

---

## 支持

如有问题或建议，请联系：
- GitHub: https://github.com/freqtrade/freqtrade
- Freqtrade 文档: https://www.freqtrade.io/en/stable/

---

**祝交易顺利！** 🚀