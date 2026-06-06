# BTC全仓策略修改方案

## 📋 修改目标

1. **保持5分钟心跳周期** - 不改变核心交易频率
2. **区分管理/非管理资金** - 新增功能
3. **防止重复下单** - 新增订单状态检查
4. **增强网络异常处理** - 新增重试机制
5. **保持信号逻辑不变** - 不改变策略核心

## 📊 当前问题分析

### 问题1: 没有检查未成交订单
**现状:**
```python
# bot_loop_start 每5分钟执行
if last_row.get('enter_long', 0) == 1 and free_quote_balance > min_stake:
    # 直接下单，不检查是否已有未成交订单
    order = exchange.create_order(...)
```

**风险:**
- 同一个信号可能触发多次下单
- 资金被重复冻结
- 订单堆积

**影响:**
- 🔴 严重：可能导致资金被锁死，无法正常交易

### 问题2: 没有区分管理/非管理资金
**现状:**
```python
total_coin_balance = self.wallets.get_total(coin)  # 获取交易所总余额
```

**场景:**
- 用户可能在交易所还有其他资金
- 策略会操作所有资金，包括非管理资金

**影响:**
- ⚠️ 中等：可能误操作用户的非量化资金

### 问题3: 网络异常处理不完善
**现状:**
```python
try:
    order = exchange.create_order(...)
except Exception as e:
    logger.error(f"挂买单失败: {e}")
```

**风险:**
- 网络问题导致下单失败，没有重试
- 异常后状态不一致

**影响:**
- ⚠️ 中等：可能错过交易机会

### 问题4: 信号可能在盘中出现收盘后消失
**现状:**
```python
process_only_new_candles = False  # 允许盘中交易
```

**场景:**
- 13:00 检测到信号，下单
- 23:59 收盘时信号消失
- 回测和实盘不一致

**影响:**
- ⚠️ 中等：实盘和回测结果差异

## ✅ 修改方案

### 修改1: 添加未成交订单检查

**修改位置:** `bot_loop_start` 函数开头

**新增代码:**
```python
def bot_loop_start(self, **kwargs) -> None:
    logger.info("执行检查信号并处理交易")
    pair = 'BTC/USDT'
    
    # ==================== 新增：检查未成交订单 ====================
    try:
        exchange = self.dp._exchange if hasattr(self.dp, '_exchange') else self.exchange
        open_orders = exchange.fetch_open_orders(pair)
        
        if open_orders:
            logger.info(f"[bot_loop_start] ⚠️ 发现 {len(open_orders)} 个未成交订单:")
            for order in open_orders:
                logger.info(f"  - {order['side']}: {order['amount']:.8f} @ {order['price']:.2f}, ID={order['id']}")
            logger.info("[bot_loop_start] 跳过本次下单，等待订单成交或取消")
            return  # 有未成交订单，跳过本次检查
    except Exception as e:
        logger.error(f"[bot_loop_start] 检查订单失败: {e}")
        # 网络异常时保守处理，跳过本次下单
        return
    
    # 原有逻辑继续...
```

**影响:**
- ✅ 防止重复下单
- ✅ 避免资金被多次冻结
- ⚠️ 如果订单长时间不成交，可能错过新的交易机会

### 修改2: 添加订单过期取消

**新增函数:**
```python
def cancel_expired_orders(self, pair: str, max_age_hours: int = 2) -> int:
    """
    取消超过指定时间的未成交订单
    
    参数:
        pair: 交易对
        max_age_hours: 最大保留时间（小时），默认2小时
    
    返回:
        取消的订单数量
    """
    try:
        exchange = self.dp._exchange if hasattr(self.dp, '_exchange') else self.exchange
        open_orders = exchange.fetch_open_orders(pair)
        cancelled_count = 0
        
        for order in open_orders:
            order_time = datetime.fromtimestamp(order['timestamp'] / 1000)
            age_hours = (datetime.now() - order_time).total_seconds() / 3600
            
            if age_hours > max_age_hours:
                exchange.cancel_order(order['id'], pair)
                logger.info(f"[cancel_expired_orders] 取消过期订单: {order['id']}, 年龄: {age_hours:.1f}小时")
                cancelled_count += 1
        
        if cancelled_count > 0:
            # 强制同步钱包
            self.wallets.update()
        
        return cancelled_count
    
    except Exception as e:
        logger.error(f"[cancel_expired_orders] 取消订单失败: {e}")
        return 0
```

**在 bot_loop_start 中调用:**
```python
def bot_loop_start(self, **kwargs) -> None:
    # 检查未成交订单（上面的代码）
    
    # ==================== 新增：取消过期订单 ====================
    try:
        cancelled = self.cancel_expired_orders(pair, max_age_hours=2)
        if cancelled > 0:
            logger.info(f"[bot_loop_start] 取消了 {cancelled} 个过期订单")
    except Exception as e:
        logger.error(f"[bot_loop_start] 取消过期订单失败: {e}")
    
    # 继续原有逻辑...
```

**影响:**
- ✅ 自动清理长期不成交的订单
- ✅ 释放冻结资金
- ✅ 防止订单堆积

### 修改3: 增强网络异常处理

**新增重试函数:**
```python
def place_order_with_retry(self, pair: str, side: str, amount: float, price: float, max_retries: int = 3) -> bool:
    """
    带网络重试的下单函数
    
    参数:
        pair: 交易对
        side: 'buy' 或 'sell'
        amount: 数量
        price: 价格
        max_retries: 最大重试次数，默认3次
    
    返回:
        True: 下单成功
        False: 下单失败
    """
    for attempt in range(1, max_retries + 1):
        try:
            exchange = self.dp._exchange if hasattr(self.dp, '_exchange') else self.exchange
            
            logger.info(f"[place_order] 第 {attempt} 次尝试: {side} {amount:.8f} @ {price:.2f}")
            
            order = exchange.create_order(
                pair=pair,
                ordertype='limit',
                side=side,
                amount=amount,
                rate=price,
                leverage=1.0
            )
            
            logger.info(f"[place_order] ✅ 下单成功! 订单ID: {order.get('id')}")
            return True
        
        except Exception as e:
            logger.error(f"[place_order] 第 {attempt} 次失败: {e}")
            
            if attempt < max_retries:
                logger.info(f"[place_order] 等待 5 秒后重试...")
                import time
                time.sleep(5)
            else:
                logger.error(f"[place_order] ❌ 下单失败，已达到最大重试次数")
                return False
    
    return False
```

**在 bot_loop_start 中使用:**
```python
# 原来的代码:
# order = exchange.create_order(...)

# 改为:
success = self.place_order_with_retry(
    pair=pair,
    side='buy',  # 或 'sell'
    amount=amount,
    price=buy_price,  # 或 sell_price
    max_retries=3
)

if success:
    # 下单成功，同步钱包
    self.wallets.update()
```

**影响:**
- ✅ 网络抖动时自动重试
- ✅ 提高下单成功率
- ⚠️ 可能增加下单延迟（最多15秒）

### 修改4: 区分管理/非管理资金（可选）

**方案A: 简单方案 - 使用所有可用资金**
```python
# 保持现有逻辑，使用所有可用资金
total_coin_balance = self.wallets.get_total(coin)  # 所有BTC
free_quote_balance = self.wallets.get_free(quote)  # 可用USDT

# 优点: 简单，最大化资金利用率
# 缺点: 可能操作非量化资金
```

**方案B: 精确方案 - 追踪管理资金**
```python
# 新增类变量
managed_coin_balance = 0.0  # 机器人管理的BTC
managed_quote_balance = 0.0  # 机器人管理的USDT

def update_managed_balance(self, pair: str):
    """
    根据订单和交易记录更新管理资金
    """
    coin = pair.split('/')[0]
    quote = pair.split('/')[1]
    
    # 从数据库获取持仓
    trades = Trade.get_trades_proxy(is_open=True)
    db_coin = sum(t.amount for t in trades if t.pair == pair)
    
    # 获取未成交订单冻结
    open_orders = exchange.fetch_open_orders(pair)
    frozen_coin = sum(o['amount'] for o in open_orders if o['side'] == 'sell')
    frozen_quote = sum(o['amount'] * o['price'] for o in open_orders if o['side'] == 'buy')
    
    # 管理资金 = 数据库持仓 + 订单冻结
    self.managed_coin_balance = db_coin + frozen_coin
    self.managed_quote_balance = frozen_quote

# 在 bot_loop_start 中:
# 只交易管理资金，不操作非管理资金
available_coin = self.managed_coin_balance
available_quote = self.managed_quote_balance
```

**推荐: 方案A（简单方案）**
- 原因: 全仓策略的核心就是最大化利用资金
- 用户如果想区分，可以在不同账户操作

## 📊 修改影响评估

### 功能影响

| 功能 | 修改前 | 修改后 | 影响 |
|------|--------|--------|------|
| **交易频率** | 每5分钟检查 | 每5分钟检查 | ✅ 无变化 |
| **信号逻辑** | 盘中可交易 | 盘中可交易 | ✅ 无变化 |
| **下单逻辑** | 直接下单 | 检查订单后下单 | ⚠️ 更安全但可能错过机会 |
| **资金使用** | 所有资金 | 所有资金（推荐） | ✅ 无变化 |
| **网络异常** | 失败即停止 | 重试3次 | ✅ 更可靠 |

### 风险评估

| 风险 | 修改前 | 修改后 | 说明 |
|------|--------|--------|------|
| **重复下单** | 🔴 高风险 | ✅ 已解决 | 添加订单检查 |
| **订单堆积** | 🔴 高风险 | ✅ 已解决 | 自动取消过期订单 |
| **网络问题** | ⚠️ 中风险 | ✅ 已缓解 | 重试机制 |
| **错过交易** | ⚠️ 中风险 | ⚠️ 仍存在 | 订单不成交可能错过 |
| **信号漂移** | ⚠️ 中风险 | ⚠️ 仍存在 | 保持盘中交易设计 |

### 性能影响

| 项目 | 修改前 | 修改后 | 影响 |
|------|--------|--------|------|
| **心跳执行时间** | ~1秒 | ~2秒 | 添加订单查询 |
| **网络请求次数** | 2次/心跳 | 3-4次/心跳 | 订单查询+取消 |
| **内存占用** | 正常 | 正常 | 无变化 |
| **CPU占用** | 正常 | 正常 | 无变化 |

## 🚀 实施步骤

### 阶段1: 准备（立即）
1. ✅ 提交当前代码到 Git
2. ✅ 备份现有配置
3. ✅ 创建修改分支

### 阶段2: 修改代码
1. 修改 `bot_loop_start` 添加订单检查
2. 添加 `cancel_expired_orders` 函数
3. 添加 `place_order_with_retry` 函数
4. 测试语法正确性

### 阶段3: 测试验证
1. 在模拟环境测试
2. 验证订单检查逻辑
3. 验证重试机制
4. 验证取消过期订单

### 阶段4: 部署上线
1. 停止当前策略
2. 更新代码
3. 启动策略
4. 监控日志

## 📝 需要修改的文件

1. `/opt/git/freqtrade/user_data/strategies/BTCFullPosition2_2.py`
2. `/opt/git/freqtrade/user_data/btc_account2_alone_cp/BTCFullPosition2_2.py`
3. 同步修改所有其他 BTCFullPosition2_*.py 文件

## ⚠️ 注意事项

1. **不要修改信号逻辑** - 保持 populate_entry_trend 和 populate_exit_trend 不变
2. **不要改变交易频率** - 保持 5 分钟心跳
3. **测试充分后再上线** - 建议先在模拟环境测试
4. **监控日志** - 上线后密切关注日志输出
5. **准备回滚方案** - 如果出现问题可以快速回滚

## 🎯 预期效果

修改完成后：
- ✅ 不会重复下单
- ✅ 自动清理过期订单
- ✅ 网络抖动时自动重试
- ✅ 保持原有的交易逻辑和频率
- ✅ 更可靠和稳定
