# OpenClaw 提示词设计文档

## 1. 日志类型识别提示词

### 场景：分析量化程序日志类型

**提示词模板：**
```
这是一个Freqtrade量化交易程序的日志片段。

请分析这段日志属于哪种类型：

类型定义：
- 正常：程序正常运行，执行交易策略，生成买卖信号或持仓检查
- 网络异常：网络连接问题、API超时、WebSocket断开、交易所接口错误等
- 其他异常：代码错误、配置错误、数据格式错误、策略计算错误等

日志内容：
{log_content}

请直接返回类型名称（正常/网络异常/其他异常），不要返回其他内容。
```

**示例输入：**
```
这是一个Freqtrade量化交易程序的日志片段。

请分析这段日志属于哪种类型：

类型定义：
- 正常：程序正常运行，执行交易策略，生成买卖信号或持仓检查
- 网络异常：网络连接问题、API超时、WebSocket断开、交易所接口错误等
- 其他异常：代码错误、配置错误、数据格式错误、策略计算错误等

日志内容：
2026-06-06 17:00:00 - freqtrade - INFO - Running strategy BTCFullPosition2_1
2026-06-06 17:00:05 - freqtrade - INFO - Analyzing pair BTC/USDT
2026-06-06 17:00:10 - freqtrade - INFO - No trade opportunity found

请直接返回类型名称（正常/网络异常/其他异常），不要返回其他内容。
```

**期望返回：**
```
正常
```

---

## 2. 其他异常分析提示词

### 场景：分析其他异常并生成解决方案

**提示词模板：**
```
Freqtrade量化交易程序遇到异常，需要分析和解决。

项目信息：
- 项目名称：Freqtrade量化交易
- 项目路径：/opt/git/freqtrade
- 策略文件：/opt/git/freqtrade/user_data/strategies/BTCFullPosition2_1.py
- 配置文件：/opt/git/freqtrade/user_data/btc_account1_alone_xql/config.json
- 启动脚本：/opt/git/freqtrade/run/btc_account1_alone_xql.sh

请按以下步骤分析：

1. 问题分析
   - 错误类型是什么？
   - 根本原因是什么？
   - 涉及哪些代码文件？

2. 解决方案
   - 需要修改哪些文件？
   - 具体修改内容是什么？
   - 是否需要重启服务？

异常日志：
{error_log}

请按以下格式返回：

## 问题分析
错误类型: xxx
根本原因: xxx
涉及文件: xxx

## 解决方案
修改文件: xxx
修改内容: xxx
是否重启: 是/否
```

**示例输入：**
```
Freqtrade量化交易程序遇到异常，需要分析和解决。

项目信息：
- 项目名称：Freqtrade量化交易
- 项目路径：/opt/git/freqtrade
- 策略文件：/opt/git/freqtrade/user_data/strategies/BTCFullPosition2_1.py
- 配置文件：/opt/git/freqtrade/user_data/btc_account1_alone_xql/config.json
- 启动脚本：/opt/git/freqtrade/run/btc_account1_alone_xql.sh

请按以下步骤分析：

1. 问题分析
   - 错误类型是什么？
   - 根本原因是什么？
   - 涉及哪些代码文件？

2. 解决方案
   - 需要修改哪些文件？
   - 具体修改内容是什么？
   - 是否需要重启服务？

异常日志：
2026-06-06 17:00:00 - freqtrade - ERROR - Strategy error: KeyError 'dataframe'
Traceback (most recent call last):
  File "/opt/git/freqtrade/user_data/strategies/BTCFullPosition2_1.py", line 123
    result = dataframe['close']
KeyError: 'dataframe'

请按以下格式返回：

## 问题分析
错误类型: xxx
根本原因: xxx
涉及文件: xxx

## 解决方案
修改文件: xxx
修改内容: xxx
是否重启: 是/否
```

**期望返回：**
```
## 问题分析
错误类型: KeyError 键不存在错误
根本原因: dataframe字典中没有'dataframe'键，可能变量名冲突或数据未初始化
涉及文件: /opt/git/freqtrade/user_data/strategies/BTCFullPosition2_1.py

## 解决方案
修改文件: /opt/git/freqtrade/user_data/strategies/BTCFullPosition2_1.py
修改内容: 将result = dataframe['dataframe']改为result = dataframe，或检查变量命名避免冲突
是否重启: 是
```

---

## 3. 自动修复执行提示词

### 场景：生成精确的修复代码

**提示词模板：**
```
需要精确修复Freqtrade策略代码。

已知信息：
- 问题类型：{error_type}
- 涉及文件：{file_path}
- 错误行号：{line_number}

请生成精确的修复代码，格式如下：

原代码（第X行）：
```python
xxx
```

修复后的代码：
```python
xxx
```

修改说明：
xxx

只返回以上内容，不要返回其他内容。
```

**示例输入：**
```
需要精确修复Freqtrade策略代码。

已知信息：
- 问题类型：KeyError
- 涉及文件：/opt/git/freqtrade/user_data/strategies/BTCFullPosition2_1.py
- 错误行号：第123行

请生成精确的修复代码，格式如下：

原代码（第123行）：
```python
xxx
```

修复后的代码：
```python
xxx
```

修改说明：
xxx

只返回以上内容，不要返回其他内容。
```

**期望返回：**
```
原代码（第123行）：
```python
result = dataframe['dataframe']
```

修复后的代码：
```python
result = dataframe  # dataframe已经是变量名，直接使用
```

修改说明：
变量名冲突导致错误，dataframe参数本身就是DataFrame对象，不需要再访问'dataframe'键。直接使用dataframe变量即可。
```

---

## 4. 测试验证提示词

### 场景：验证修复是否成功

**提示词模板：**
```
Freqtrade策略修复后需要验证。

请检查以下修复是否正确：

原问题：KeyError 'dataframe'
修复方案：将 dataframe['dataframe'] 改为 dataframe

验证要点：
1. 是否解决了KeyError问题？
2. 是否会影响其他逻辑？
3. 是否符合Freqtrade策略规范？

修复后的代码片段：
```python
def populate_indicators(self, dataframe, metadata):
    result = dataframe  # 直接使用dataframe
    return dataframe
```

请返回验证结果，格式如下：

验证状态: 成功/失败
验证说明: xxx
建议补充: xxx（如果需要）
```

**期望返回：**
```
验证状态: 成功
验证说明: 修复正确，dataframe变量直接使用避免了键不存在的问题，符合Freqtrade策略规范中populate_indicators返回完整dataframe的要求
建议补充: 无
```

---

## 5. 网络异常诊断提示词

### 场景：分析网络异常原因

**提示词模板：**
```
Freqtrade量化程序遇到网络异常，需要诊断。

异常信息：
{error_log}

请分析：

1. 网络异常类型
   - API超时？
   - WebSocket断开？
   - 连接失败？
   - 其他网络问题？

2. 可能原因
   - 交易所API限制？
   - 网络连接不稳定？
   - 代理配置问题？
   - 其他原因？

3. 建议操作
   - 是否需要重启服务？
   - 是否需要调整配置？
   - 是否需要等待恢复？

请按以下格式返回：

异常类型: xxx
可能原因: xxx
建议操作: xxx
```

**示例输入：**
```
Freqtrade量化程序遇到网络异常，需要诊断。

异常信息：
2026-06-06 17:00:00 - freqtrade - WARNING - Binance API timeout
2026-06-06 17:00:05 - freqtrade - ERROR - Failed to fetch ticker for BTC/USDT
TimeoutError: Connection timeout after 30s

请分析：

1. 网络异常类型
   - API超时？
   - WebSocket断开？
   - 连接失败？
   - 其他网络问题？

2. 可能原因
   - 交易所API限制？
   - 网络连接不稳定？
   - 代理配置问题？
   - 其他原因？

3. 建议操作
   - 是否需要重启服务？
   - 是否需要调整配置？
   - 是否需要等待恢复？

请按以下格式返回：

异常类型: xxx
可能原因: xxx
建议操作: xxx
```

**期望返回：**
```
异常类型: API超时
可能原因: Binance API响应超时，可能是网络延迟或API限制
建议操作: 等待恢复，如果频繁出现可检查网络代理配置或调整timeout参数
```

---

## 6. 进程启动失败分析提示词

### 场景：分析启动失败原因

**提示词模板：**
```
Freqtrade量化程序启动失败，需要分析原因。

启动命令：/opt/git/freqtrade/run/btc_account1_alone_xql.sh restart

失败信息：
{error_log}

请分析：

1. 启动失败原因
   - 配置错误？
   - 依赖缺失？
   - 权限问题？
   - 其他原因？

2. 解决方法
   - 需要修改什么？
   - 如何手动启动？

请按以下格式返回：

失败原因: xxx
解决方法: xxx
```

**示例输入：**
```
Freqtrade量化程序启动失败，需要分析原因。

启动命令：/opt/git/freqtrade/run/btc_account1_alone_xql.sh restart

失败信息：
bash: /opt/git/freqtrade/run/btc_account1_alone_xql.sh: Permission denied

请分析：

1. 启动失败原因
   - 配置错误？
   - 依赖缺失？
   - 权限问题？
   - 其他原因？

2. 解决方法
   - 需要修改什么？
   - 如何手动启动？

请按以下格式返回：

失败原因: xxx
解决方法: xxx
```

**期望返回：**
```
失败原因: 权限不足，脚本没有执行权限
解决方法: chmod +x /opt/git/freqtrade/run/btc_account1_alone_xql.sh 然后重新启动
```

---

## 提示词设计原则

### 1. **结构清晰**
- 使用明确的标题和分隔符
- 分步骤列出分析要求
- 指定返回格式

### 2. **信息完整**
- 提供项目路径和文件位置
- 说明错误上下文
- 列出相关配置文件

### 3. **返回格式标准化**
- 使用固定的格式模板
- 关键信息用冒号分隔
- 易于程序解析

### 4. **避免歧义**
- 明确类型定义（正常/网络/其他）
- 避免模糊的描述
- 使用具体的技术术语

### 5. **便于解析**
- 使用固定格式的返回模板
- 关键字段用标准标记（如 `错误类型:`）
- 便于Python代码解析

---

## 代码解析示例

### Python解析代码模板

```python
def parse_llm_response(response):
    """解析大模型返回结果"""
    
    result = {}
    lines = response.split('\n')
    
    for line in lines:
        # 使用冒号分隔解析
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            
            # 标准化字段名
            if '错误类型' in key or '异常类型' in key:
                result['error_type'] = value
            elif '根本原因' in key or '可能原因' in key:
                result['root_cause'] = value
            elif '涉及文件' in key or '修改文件' in key:
                result['file'] = value
            elif '修改内容' in key or '解决方法' in key:
                result['solution'] = value
            elif '是否重启' in key or '建议操作' in key:
                result['restart_needed'] = '是' in value or '重启' in value
    
    return result

# 示例解析
response = """
## 问题分析
错误类型: KeyError 键不存在错误
根本原因: dataframe字典中没有'dataframe'键
涉及文件: /opt/git/freqtrade/user_data/strategies/BTCFullPosition2_1.py

## 解决方案
修改文件: /opt/git/freqtrade/user_data/strategies/BTCFullPosition2_1.py
修改内容: 将result = dataframe['dataframe']改为result = dataframe
是否重启: 是
"""

result = parse_llm_response(response)
print(result)
# {
#   'error_type': 'KeyError 键不存在错误',
#   'root_cause': "dataframe字典中没有'dataframe'键",
#   'file': '/opt/git/freqtrade/user_data/strategies/BTCFullPosition2_1.py',
#   'solution': "将result = dataframe['dataframe']改为result = dataframe",
#   'restart_needed': True
# }
```

---

## 总结

✅ **提示词设计要点**：

1. **日志识别** - 直接返回类型名，无其他内容
2. **异常分析** - 分问题分析和解决方案两部分
3. **修复代码** - 提供原代码和修复后代码对比
4. **验证结果** - 明确成功/失败状态
5. **诊断建议** - 列出异常类型、原因、建议操作

✅ **返回格式标准化**：
- 使用固定格式模板
- 关键信息用 `xxx: xxx` 格式
- 易于Python解析

✅ **信息完整性**：
- 项目路径、文件位置
- 错误上下文、相关配置
- 便于大模型定位和修复

---

**提示词设计完成，等待需求确认后开始编写监控代码！** ✨