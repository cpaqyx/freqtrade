# HighFreq5mStrategy - 5分钟高频交易策略

## 📋 项目概述

这是一个针对加密货币永续合约的5分钟高频交易策略，支持多空双向交易，综合运用多个技术指标。

**创建日期**: 2025-10-24  
**版本**: v1.0  
**时间框架**: 5分钟  
**交易模式**: 永续合约（Futures）

---

## 🎯 策略特点

### 1. 支持多空双向交易
- ✅ 做多（Long）：在超卖区域买入
- ✅ 做空（Short）：在超买区域卖出
- ✅ 同时持仓：最多3个仓位

### 2. 综合多个技术指标

| 指标类型 | 具体指标 | 用途 |
|---------|---------|------|
| **趋势** | EMA短期/中期/长期 | 判断主趋势方向 |
|   | SuperTrend | 趋势跟踪和反转识别 |
| **超买超卖** | 布林带（BB） | 识别价格偏离程度 |
|   | RSI | 相对强弱指标 |
| **支撑压力** | 历史高低点 | 动态SR位计算 |
| **情绪** | 恐慌指数（FGI） | 市场情绪辅助判断 |
| **动量** | 连续K线 | 识别连续上涨/下跌 |

### 3. 信号投票机制
- 不使用严格的AND条件
- 采用"投票机制"：至少2-3个信号一致即可入场
- 提高交易频率，同时保持质量

### 4. 动态风险管理
- ROI分级止盈
- 追踪止损
- 动态止损调整

---

## 📂 文件结构

```
user_data/freq/
├── HighFreq5mStrategy.py       # 核心策略文件
├── FGIDataProvider.py          # 恐慌指数数据提供者
├── freq.json                   # 配置文件（9个币种）
├── freq_be.json                # 配置文件（BTC/ETH）
├── freq_other.json             # 配置文件（其他7个币种）
├── backtest_all.bat            # 回测脚本（全部币种）
├── backtest_be.bat             # 回测脚本（BTC/ETH）
├── backtest_other.bat          # 回测脚本（其他币种）
├── hyperopt_all.bat            # 优化脚本（全部币种）
├── hyperopt_be.bat             # 优化脚本（BTC/ETH）
└── README.md                   # 本文件
```

---

## ⚙️ 配置说明

### 交易对配置

#### freq.json (9个币种)
```
BTC/USDT:USDT, ETH/USDT:USDT, SOL/USDT:USDT,
XRP/USDT:USDT, ADA/USDT:USDT, DOGE/USDT:USDT,
SUI/USDT:USDT, TRX/USDT:USDT, ENA/USDT:USDT
```
- `max_open_trades`: 5
- `stake_amount`: 100 USDT

#### freq_be.json (BTC/ETH)
```
BTC/USDT:USDT, ETH/USDT:USDT
```
- `max_open_trades`: 3
- `stake_amount`: 200 USDT

#### freq_other.json (其他7个币种)
```
SOL/USDT:USDT, XRP/USDT:USDT, ADA/USDT:USDT,
DOGE/USDT:USDT, SUI/USDT:USDT, TRX/USDT:USDT, ENA/USDT:USDT
```
- `max_open_trades`: 7
- `stake_amount`: 50 USDT

---

## 🔧 可优化参数

### 1. 布林带参数
- `bb_length`: 15-40（默认20）
- `bb_std`: 1.5-3.0（默认2.0）
- `bb_buy_threshold`: 0.0-0.35（默认0.20）
- `bb_sell_threshold`: 0.65-1.0（默认0.80）

### 2. EMA趋势参数
- `ema_short`: 5-20（默认9）
- `ema_medium`: 20-50（默认21）
- `ema_long`: 50-200（默认50）

### 3. SuperTrend参数
- `supertrend_period`: 7-14（默认10）
- `supertrend_multiplier`: 2.0-4.0（默认3.0）

### 4. 压力位支撑位参数
- `sr_lookback`: 20-100（默认50）
- `sr_threshold`: 0.005-0.020（默认0.010）

### 5. 连续K线参数
- `consecutive_candles`: 2-5（默认3）

### 6. 恐慌指数参数
- `fgi_extreme_fear`: 20-35（默认25）
- `fgi_extreme_greed`: 65-80（默认75）
- `use_fgi_filter`: True/False（默认False）

### 7. 信号投票机制
- `min_long_signals`: 2-4（默认2）
- `min_short_signals`: 2-4（默认2）

### 8. 动态止损
- `custom_stoploss_value`: -0.05至-0.02（默认-0.03）

---

## 🚀 快速开始

### 1. 运行回测

#### 回测 BTC/ETH（推荐）
```cmd
.\user_data\freq\backtest_be.bat
```

#### 回测全部9个币种
```cmd
.\user_data\freq\backtest_all.bat
```

#### 回测其他7个币种
```cmd
.\user_data\freq\backtest_other.bat
```

### 2. 参数优化

#### 优化 BTC/ETH（推荐）
```cmd
.\user_data\freq\hyperopt_be.bat
```

#### 优化全部币种
```cmd
.\user_data\freq\hyperopt_all.bat
```

---

## 📊 初始回测结果（v1.0）

**测试配置**:
- 币种: BTC/USDT:USDT, ETH/USDT:USDT
- 时间范围: 2025-07-20 至 2025-10-24（96天）
- 初始资金: 1000 USDT

**结果统计**:
- 总交易次数: 2130次
- 日均交易: 22.19次 ✅（高频目标达成）
- 总收益: -203.836 USDT (-20.38%) ❌
- 胜率: 33.9%
- 盈利因子: 0.78

**问题分析**:
1. 数据范围限制（仅96天，横盘市场）
2. 出场信号过早（82%的exit_signal导致亏损）
3. 默认参数未优化

**优化方向**:
- ✅ 运行Hyperopt优化10000次
- ✅ 使用SharpeHyperOptLoss（夏普比率）
- ✅ 优化 buy, sell, roi, stoploss 所有空间

---

## 📈 优化状态

### 当前正在运行的优化任务

| 任务 | 状态 | 配置 | 进度 |
|-----|------|-----|------|
| Hyperopt BE | 🔄 运行中 | freq_be.json | 1000 epochs |

**优化参数**:
- 优化目标: SharpeHyperOptLoss
- 最小交易数: 30
- 优化空间: buy, sell, roi, stoploss
- 随机种子: 42
- 并行: -1（全核心）

**预计完成时间**: 数小时

---

## 📝 使用建议

### 1. 数据准备
确保已下载足够的5分钟数据：
```cmd
# 查看已下载数据
dir user_data\data\binance\futures\*-5m-*.feather
```

### 2. 参数优化顺序
1. 先优化 BTC/ETH（数据更稳定）
2. 再优化其他币种
3. 最后整体优化

### 3. 风险控制
- 初始资金不要超过总资金的30%
- 单笔交易不要超过总资金的5%
- 设置合理的最大开仓数

### 4. 实盘前测试
- 完成至少6个月回测
- 胜率 > 40%
- 盈利因子 > 1.2
- 最大回撤 < 20%

---

## ⚠️ 风险提示

1. **历史表现不代表未来收益**
2. **5分钟高频交易手续费成本高**
3. **需要稳定的网络和服务器**
4. **建议从小资金开始测试**
5. **务必在模拟环境充分测试后再实盘**

---

## 🔄 版本历史

### v1.0 (2025-10-24)
- ✅ 初始版本发布
- ✅ 实现多空双向交易
- ✅ 集成7个技术指标
- ✅ 信号投票机制
- ✅ 完成初始回测
- 🔄 Hyperopt优化进行中

---

## 📧 技术支持

如有问题，请检查：
1. Freqtrade版本是否为2025.9+
2. Python版本是否为3.12+
3. 所有依赖包是否已安装
4. 数据是否已下载完整

---

## 📜 许可证

本策略仅供学习研究使用，使用本策略进行实盘交易的风险由使用者自行承担。

---

**最后更新**: 2025-10-24 17:45  
**状态**: 🔄 参数优化中

