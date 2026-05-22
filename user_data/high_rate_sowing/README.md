# 高倍率播种策略 (HighRateSowing)

## 策略概述

基于分钟级别K线的合约交易策略，专注于高倍杠杆的精准建仓和平仓。

### 核心特性

- **时间周期**: 1分钟（每分钟执行一次）
- **交易模式**: 合约交易（逐仓模式）
- **杠杆倍数**: 20倍
- **方向**: 只做多，不做空
- **最大持仓**: 3个合约

## 参数说明

### 建仓参数

| 参数名 | 默认值 | 范围 | 说明 |
|--------|--------|------|------|
| max_drop_from_high | 0.15 | 0.05-0.50 | 从最高点下跌阈值 |
| candle_rise_threshold | 0.005 | 0.001-0.05 | 单根K线涨幅阈值 |
| continuous_rise_threshold | 0.02 | 0.005-0.15 | 连续3根K线涨幅阈值 |
| pattern_drop_threshold | 0.03 | 0.005-0.30 | 图形下跌幅度阈值 |
| entry_near_support_pct | 0.02 | 0.001-0.10 | 建仓时离支撑价格百分比 |

### 平仓参数

| 参数名 | 默认值 | 范围 | 说明 |
|--------|--------|------|------|
| candle_drop_threshold | 0.005 | 0.001-0.05 | 单根K线跌幅阈值 |
| continuous_drop_threshold | 0.02 | 0.005-0.15 | 连续3根K线跌幅阈值 |
| double_top_higher_threshold | 0.03 | 0.005-0.15 | 双顶高位阈值 |
| double_top_lower_threshold | 0.05 | 0.01-0.15 | 双顶低位阈值 |
| last_down_threshold | 0.05 | 0.01-0.15 | 最后一段下跌阈值 |
| exit_near_resistance_pct | 0.02 | -0.05-0.10 | 平仓时离压力价格百分比 |
| dynamic_stoploss_pct | -0.005 | -0.02-0.05 | 动态止损触发阈值 |

## 建仓规则

### 条件组合

1. **基础条件**（满足其一）:
   - 条件1: 价格从90周期最高点下跌超过 `max_drop_from_high`
   - 条件2: 涨幅条件（单根K线涨幅 > `candle_rise_threshold` 或 连续3根K线涨幅 > `continuous_rise_threshold`）+ 图形反转信号

2. **必须条件**:
   - 条件3: 价格在支撑位附近（距离支撑价格 <= `entry_near_support_pct`）
   - 条件4: 最近一根线段为up（上涨趋势）

### 图形反转信号

- 最后1个线段为up/flat
- 倒数第2个线段为down，且跌幅 > `pattern_drop_threshold`

## 平仓规则

### 条件组合

满足以下其一即可平仓：

1. **双顶信号**:
   - 单根K线跌幅或连续跌幅条件
   - 检测到双顶形态

2. **压力位信号**:
   - 价格在压力位附近（距离压力价格 <= `exit_near_resistance_pct`）
   - 最近一根线段为down（下降趋势）

### 动态止损

- 当价格上涨时，设置止损价格为最近down线段的最小价格（支撑价格）
- 当当前价格低于 `支撑价格 * (1 + dynamic_stoploss_pct)` 时触发止损
- `dynamic_stoploss_pct` 可为负数，例如 -0.005 表示止损价为支撑价的99.5%

## 压力支撑计算

### 压力价格 (shape_resistance)
- 取波形指标中最近两根线段的最大值中的最大值

### 支撑价格 (shape_support)
- 取波形指标中最近两根线段的最小值中的最小值

## 使用方法

### 1. 回测

```bash
freqtrade backtesting \
  --config user_data/high_rate_sowing/config.json \
  --strategy HighRateSowing \
  --timerange 20240101-20240501
```

### 2. 模拟运行

```bash
freqtrade trade \
  --config user_data/high_rate_sowing/config.json \
  --strategy HighRateSowing \
  --dry-run
```

### 3. 实盘运行

修改 `config.json` 中的以下配置：
- `dry_run`: false
- `exchange.key`: 你的API Key
- `exchange.secret`: 你的API Secret

```bash
freqtrade trade \
  --config user_data/high_rate_sowing/config.json \
  --strategy HighRateSowing
```

## 参数优化

使用 Hyperopt 优化参数：

```bash
freqtrade hyperopt \
  --config user_data/high_rate_sowing/config.json \
  --strategy HighRateSowing \
  --hyperopt-loss SharpeHyperOptLoss \
  --spaces buy sell \
  --timerange 20240101-20240501 \
  --epochs 100
```

## 风险提示

⚠️ **高风险策略**

- 20倍杠杆会放大盈利和亏损
- 分钟级别交易频率高，手续费成本较大
- 请在充分回测和模拟运行后再考虑实盘
- 建议从小资金开始测试

## 技术指标依赖

- `user_data/common/line_format_v2.py`: 波形指标计算模块

## 文件结构

```
user_data/high_rate_sowing/
├── HighRateSowing.py      # 策略文件
├── config.json            # 配置文件
└── README.md              # 本文档
```

## 更新日志

- 2026-05-22: 初始版本，基于BTCFullPosition2_2.py改造
  - 改为分钟级别
  - 改为合约交易（逐仓，20倍杠杆）
  - 添加压力支撑价格判断
  - 添加动态止损功能
  - 限制最大持仓数量为3个
