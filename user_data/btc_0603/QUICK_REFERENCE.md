# BTC Rebound Volume Strategy - 快速参考

## 📁 文件清单

| 文件 | 说明 |
|------|------|
| `BTC_Rebound_Volume_Strategy.py` | 策略主文件 |
| `config_dryrun.json` | 模拟运行配置 |
| `config_live.json` | 实盘运行配置 |
| `config_with_params.json` | 带参数示例配置 |
| `run_strategy.sh` | 运行脚本 |
| `README.md` | 详细文档 |

## 🚀 快速开始

### 1. 测试策略语法
```bash
cd /opt/git/freqtrade
freqtrade list-strategies --strategy-path user_data/btc_0603
```

### 2. 模拟运行（Dry-Run）
```bash
./user_data/btc_0603/run_strategy.sh dryrun
```

### 3. 回测
```bash
# 回测最近1个月
freqtrade backtesting \
    --strategy BTC_Rebound_Volume_Strategy \
    --strategy-path user_data/btc_0603 \
    --config user_data/btc_0603/config_dryrun.json \
    --timeframe 1m \
    --timerange 20250501-20250601 \
    --trading-mode futures
```

### 4. 实盘运行
```bash
# 1. 先编辑 config_live.json，替换 API Key
# 2. 启动实盘
./user_data/btc_0603/run_strategy.sh live
```

## 📊 核心参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 价格关口 | 65000-55000 | 每1000一个整数关口 |
| 反弹幅度 | 5% | 从最低价计算的反弹阈值 |
| 关口缓冲 | 1% | 价格需高于关口的百分比 |
| 成交量窗口 | 24h | 计算平均成交量的窗口 |
| 成交量放大 | 10% | 需要放大比例 |
| 杠杆 | 20x | 固定杠杆 |
| 仓位比例 | 20% | 每次使用的资金比例 |
| 止损 | 8% | 止损百分比 |

## ⚙️ 配置修改

### 修改价格关口
在配置文件中添加：
```json
{
  "strategy_parameters": {
    "price_levels": [70000, 69000, 68000, 67000, 66000]
  }
}
```

### 修改反弹参数
```json
{
  "rebound_min_pct": 0.06,
  "level_buffer_pct": 0.015
}
```

### 修改风控参数
```json
{
  "stoploss_pct": -0.10,
  "stake_ratio": 0.15
}
```

## 🔍 监控命令

### 查看交易记录
```bash
freqtrade show-trades \
    --db-url sqlite:///user_data/btc_0603/tradesv3.dryrun.sqlite
```

### 查看日志
```bash
tail -f user_data/logs/freqtrade.log
```

### 启动 Web UI
```bash
freqtrade webserver --config user_data/btc_0603/config_dryrun.json
```

访问：http://localhost:8093

## 📈 入场逻辑

**触发条件**：
1. 价格跌破整数关口 → 记录活跃关口 + 跟踪最低价
2. 价格反弹突破关口（close > level）
3. 反弹幅度 ≥ 5% **或** 价格 ≥ 关口 + 1%
4. 成交量放大 ≥ 10%（最近1h vs 24h平均）

**入场标签**：
- `rebound_5pct_vol_confirmed` - 反弹触发
- `level_buffer_1pct_vol_confirmed` - 关口缓冲触发

## ⚠️ 注意事项

1. **数据要求**：需要 1m K线数据
   ```bash
   freqtrade download-data \
       --pairs BTC/USDT:USDT \
       --timeframe 1m \
       --trading-mode futures
   ```

2. **API Key**：实盘前务必替换 `config_live.json` 中的 API Key

3. **资金安全**：建议先 dry-run 充分测试

4. **杠杆风险**：20x 杠杆风险较高，请谨慎操作

## 🛠️ 参数优化

```bash
# 优化入场参数
freqtrade hyperopt \
    --strategy BTC_Rebound_Volume_Strategy \
    --strategy-path user_data/btc_0603 \
    --config user_data/btc_0603/config_dryrun.json \
    --timeframe 1m \
    --timerange 20250301-20250601 \
    --spaces buy \
    --epochs 100 \
    --trading-mode futures
```

## 📞 获取帮助

- 详细文档：`README.md`
- Freqtrade 文档：https://www.freqtrade.io
- Freqtrade GitHub：https://github.com/freqtrade/freqtrade

---

**策略版本**：v1.0.0  
**创建日期**：2026-06-03  
**作者**：OpenClaw AI