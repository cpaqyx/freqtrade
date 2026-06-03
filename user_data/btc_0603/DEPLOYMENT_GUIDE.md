# BTC Rebound Volume Strategy - 部署指南

## 当前状态

✅ **策略已创建并验证**
✅ **配置文件已更新（包含真实API Key和代理）**
✅ **回测已运行**
🔄 **参数优化进行中**

---

## 快速开始

### 1. 查看回测结果

```bash
cd /opt/git/freqtrade
freqtrade backtesting-show --config user_data/btc_0603/config_dryrun.json
```

### 2. 运行参数优化

```bash
# 查看优化进度
tail -f /tmp/hyperopt_output.txt

# 查看最优参数
freqtrade hyperopt-show --config user_data/btc_0603/config_dryrun.json --best
```

### 3. 应用最优参数

将优化得到的参数更新到配置文件中：

```bash
# 编辑配置文件
nano user_data/btc_0603/config_dryrun.json
```

在 `strategy` 部分添加参数：

```json
{
  "strategy": "BTC_Rebound_Volume_Strategy",
  "strategy_path": "user_data/btc_0603",
  
  // 添加以下参数（示例值，需替换为优化结果）
  "rebound_min_pct": 0.05,
  "level_buffer_pct": 0.01,
  "vol_lookback_hours": 24,
  "vol_confirm_hours": 1,
  "vol_increase_pct": 0.1,
  "stoploss_pct": -0.08
}
```

### 4. Dry-Run 测试

```bash
# 启动 dry-run 模式
freqtrade trade \
    --strategy BTC_Rebound_Volume_Strategy \
    --strategy-path user_data/btc_0603 \
    --config user_data/btc_0603/config_dryrun.json
```

### 5. 实盘运行（确认无误后）

```bash
# ⚠️ 警告：实盘运行将使用真实资金！
# 确保已完成以下检查：
# - dry-run 模式运行至少24小时
# - 参数已优化
# - 风控设置已确认
# - API权限正确（需要交易权限）

freqtrade trade \
    --strategy BTC_Rebound_Volume_Strategy \
    --strategy-path user_data/btc_0603 \
    --config user_data/btc_0603/config_live.json
```

---

## 配置说明

### 关键配置项

| 配置项 | 值 | 说明 |
|--------|-----|------|
| 交易对 | BTC/USDT:USDT | BTC永续合约 |
| 杠杆 | 20x | 固定杠杆 |
| 仓位比例 | 20% | 每次使用20%可用资金 |
| 止损 | -8% | 8%止损 |
| 代理 | http://127.0.0.1:7890 | 访问Binance API |
| API端口 | 8093 | FreqUI访问端口 |

### 策略参数

| 参数 | 默认值 | 优化范围 | 说明 |
|------|--------|----------|------|
| rebound_min_pct | 0.05 | 0.03-0.10 | 反弹幅度阈值 |
| level_buffer_pct | 0.01 | 0.005-0.03 | 关口缓冲百分比 |
| vol_lookback_hours | 24 | 12-48 | 成交量观察窗口 |
| vol_confirm_hours | 1 | 1-4 | 成交量确认窗口 |
| vol_increase_pct | 0.1 | 0.05-0.30 | 成交量放大比例 |
| stoploss_pct | -0.08 | -0.15--0.03 | 止损百分比 |

---

## 风险提示

⚠️ **重要提醒**

1. **杠杆风险**: 20x杠杆放大盈利的同时也放大亏损
2. **止损风险**: 8%止损 + 20x杠杆 = 实际亏损160%
3. **市场风险**: 策略在横盘/震荡市场可能表现不佳
4. **资金风险**: 建议先用小额资金测试

---

## 监控与维护

### 查看日志

```bash
# 实时日志
tail -f /opt/git/freqtrade/user_data/logs/freqtrade.log

# 查看交易记录
freqtrade show_trades --config user_data/btc_0603/config_dryrun.json
```

### API 访问

```bash
# 获取JWT Token
curl -X POST http://localhost:8093/api/v1/token/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# 使用Token查询状态
curl -X GET http://localhost:8093/api/v1/status \
  -H "Authorization: Bearer <your_token>"
```

### FreqUI 访问

访问: http://localhost:8093

---

## 文件列表

```
/opt/git/freqtrade/user_data/btc_0603/
├── BTC_Rebound_Volume_Strategy.py  # 策略主文件
├── config_dryrun.json              # 模拟配置
├── config_live.json                # 实盘配置
├── run_strategy.sh                 # 运行脚本
├── full_workflow.sh                # 完整流程脚本
└── DEPLOYMENT_GUIDE.md             # 本文件
```

---

## 故障排查

### 问题1: 无法连接交易所

检查代理是否运行：
```bash
curl -x http://127.0.0.1:7890 https://api.binance.com/api/v3/ping
```

### 问题2: 没有交易信号

检查价格范围和关口设置：
```bash
freqtrade backtesting --config user_data/btc_0603/config_dryrun.json \
    --timerange 20260501-20260521 --export signals
```

### 问题3: API 权限错误

确认API Key权限：
- 需要 "Futures" 权限
- IP白名单设置正确

---

## 联系与支持

- Freqtrade 文档: https://www.freqtrade.io/en/stable/
- FreqUI: http://localhost:8093
- 日志文件: `/opt/git/freqtrade/user_data/logs/freqtrade.log`
