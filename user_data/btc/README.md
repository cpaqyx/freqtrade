# BTC 全仓策略

## 策略概述

**BTCFullPosition** 是一个基于90日图形分析的BTC全仓交易策略。

### 核心特点
- ✅ **日线级别** (1d timeframe)
- ✅ **只做多，不做空** (适用于现货)
- ✅ **全仓进出** (stake_amount = unlimited)
- ✅ **智能图形识别** (基于90日K线趋势分析)

---

## 策略逻辑

### 📊 计算指标

1. **最近90根最高价** (`max_90`)
2. **最近90根最低价** (`min_90`)
3. **90日图形指标** (调用 `line_format.py` 中的 `kline_trend_description`)
   - 返回 JSON 数组，包含趋势段信息
   - 每段包含：line(up/down/flat)、角度、价格区间、K线数量等

### 📈 建仓条件

**条件1：急跌抄底**
- 当前价与最近90根最高价相比，跌了 **25%**
- 直接在下一根K线开盘价建仓

**条件2：趋势确认**
- 当天涨幅 > 2% **或** 连续3天上涨且累计涨幅 > 3%
- 并满足以下图形条件之一：
  - **2.1**：最后1段为up/flat，倒数第2段为down且跌幅 > 10%
  - **2.2**：最后1段为up/flat，倒数第2段为flat或小up(k_cnt<2且涨幅≤5%)，倒数第3段为down且跌幅 > 10%

### 📉 平仓条件

**条件1：双顶形态**
- 当天跌幅 > 2% **或** 连续3天下跌且累计跌幅 > 3%
- 并满足图形条件：
  - 最后1段为down/flat
  - 倒数第2段为up，找到该up的max_price
  - 再向前找另一个up的max_price
  - 如果两个max_price相差 < 2%，判定为双顶，平仓

---

## 快速开始

### 1. 运行回测

```bash
cd user_data/btc
backtest.bat
```

### 2. 查看结果

- **命令行输出**：显示关键指标（胜率、收益率、Sharpe等）
- **FreqUI界面**：http://127.0.0.1:8086
- **导出文件**：`user_data/backtest_results/`

### 3. 参数调整

在 `BTCFullPosition.py` 中可调整以下参数：

```python
max_drop_from_high = 0.25  # 从最高点跌25%触发建仓
day_rise_threshold = 0.02  # 单日涨幅2%
continuous_rise_threshold = 0.03  # 连续涨幅3%
day_drop_threshold = 0.02  # 单日跌幅2%
continuous_drop_threshold = 0.03  # 连续跌幅3%
pattern_drop_threshold = 0.10  # 图形下跌10%
double_top_threshold = 0.02  # 双顶差距2%
```

---

## 配置说明

### config.json 关键配置

```json
{
  "max_open_trades": 1,         // 只允许1个仓位
  "stake_amount": "unlimited",  // 全仓操作
  "tradable_balance_ratio": 0.99,  // 99%资金使用率
  "pair_whitelist": ["BTC/USDT"],  // 只交易BTC
  "trading_mode": "spot"        // 现货模式
}
```

---

## 图形指标示例

```json
[
  {
    "line": "up",
    "angle": 30.44,
    "max_price": 24841.69,
    "min_price": 23511.81,
    "start_price": 24327.98,
    "end_price": 24841.69,
    "k_cnt": 5
  },
  {
    "line": "down",
    "angle": -56.14,
    "max_price": 24841.69,
    "min_price": 20151.4,
    "start_price": 24841.69,
    "end_price": 20151.4,
    "k_cnt": 18
  }
]
```

### 字段说明
- `line`: 趋势方向 (up/down/flat)
- `angle`: 角度 (度)
- `max_price`: 该段最高价
- `min_price`: 该段最低价
- `start_price`: 该段起始价
- `end_price`: 该段结束价
- `k_cnt`: K线根数

---

## 注意事项

1. **数据要求**：至少需要100根日线数据（包括90根启动数据）
2. **全仓风险**：策略使用全仓操作，风险较高，建议充分回测
3. **单一币种**：只针对BTC/USDT，不建议用于其他币种
4. **只做多**：不适合熊市长期下跌行情
5. **图形计算**：每根K线都会重新计算90日图形，计算量较大

---

## 文件结构

```
user_data/btc/
├── BTCFullPosition.py   # 策略主文件
├── config.json          # 配置文件
├── backtest.bat         # 回测脚本
└── README.md           # 说明文档
```

---

## 依赖

- `common/line_format.py` - 图形分析模块
- `numpy`, `pandas` - 数据处理
- `sklearn` - 机器学习（RANSAC回归）

---

## 更新日志

### v1.0 (2025-11-03)
- ✅ 初始版本
- ✅ 实现90日图形分析
- ✅ 实现全仓建仓/平仓逻辑
- ✅ 支持急跌抄底和趋势确认
- ✅ 支持双顶形态识别



