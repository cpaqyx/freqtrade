#!/usr/bin/env python3
"""
Freqtrade量化交易程序监控脚本
功能：
1. 检测量化进程是否运行，异常则尝试重启（最多3次）
2. 分析日志，使用大模型智能识别正常/网络异常/其他异常
3. 网络异常次数过多发送邮件
4. 其他异常调用大模型分析并提供解决方案
5. 超过15分钟无日志发送邮件
"""

import os
import sys
import json
import time
import subprocess
import smtplib
import requests
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
import re

# 项目路径
PROJECT_DIR = "/opt/git/freqtrade"
CHECK_DIR = os.path.join(PROJECT_DIR, "check")
DATA_DIR = os.path.join(CHECK_DIR, "data")
LOG_DIR = os.path.join(CHECK_DIR, "logs")

# 确保目录存在
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# 配置文件
MEMORY_FILE = os.path.join(DATA_DIR, "memory.json")
LOCK_FILE = os.path.join(DATA_DIR, "check.lock")
LAST_LINE_FILE = os.path.join(DATA_DIR, "last_line.txt")
EMAIL_SENT_FILE = os.path.join(DATA_DIR, "email_sent.json")

# 进程和日志配置
START_SCRIPT = "/opt/git/freqtrade/run/btc_account1_alone_xql.sh"
LOG_FILE = "/opt/git/freqtrade/user_data/logs/btc_account1_alone_xql.log"
PID_FILE = "/opt/git/freqtrade/user_data/logs/btc_account1_alone_xql.pid"
PROCESS_NAME = "freqtrade"
CONFIG_FILE = "btc_account1_alone_xql"

# 邮件配置
SMTP_SERVER = "smtp.aliyun.com"
SMTP_PORT = 465
SMTP_USER = "cpaqyx@aliyun.com"
SMTP_PASSWORD = "no0523cp"
ALERT_EMAILS = ["363642626@qq.com", "cpaqyx@aliyun.com"]

# OpenClaw API配置
OPENCLAW_API_URL = "http://127.0.0.1:18789"
OPENCLAW_GATEWAY_TOKEN = "97557c251d01890c7be034544a5862b259ce7c70c5b3e3ae"
USE_LLM_ANALYSIS = True

# 内存字典配置
MAX_MEMORY_SIZE = 1000
MAX_TIME_GAP = 15 * 60  # 15分钟无日志视为异常


def log_message(msg):
    """记录日志"""
    log_file = os.path.join(LOG_DIR, f"check_{datetime.now().strftime('%Y%m%d')}.log")
    with open(log_file, 'a') as f:
        f.write(f"[{datetime.now()}] {msg}\n")
    print(f"[{datetime.now()}] {msg}")


class CircularBuffer:
    """定长循环数组"""
    
    def __init__(self, max_size):
        self.buffer = []
        self.max_size = max_size
        self.index = 0
    
    def append(self, item):
        if len(self.buffer) < self.max_size:
            self.buffer.append(item)
        else:
            self.buffer[self.index] = item
            self.index = (self.index + 1) % self.max_size
    
    def get_recent_24h(self):
        """获取最近24小时的记录"""
        now = datetime.now()
        cutoff = now - timedelta(hours=24)
        
        recent = []
        for item in self.buffer:
            if 'timestamp' in item:
                try:
                    ts = datetime.fromisoformat(item['timestamp'])
                    if ts > cutoff:
                        recent.append(item)
                except:
                    pass
        return recent
    
    def to_list(self):
        return self.buffer.copy()


class EmailSender:
    """邮件发送器"""
    
    def __init__(self):
        self.server = SMTP_SERVER
        self.port = SMTP_PORT
        self.user = SMTP_USER
        self.password = SMTP_PASSWORD
    
    def send(self, subject, content, to_emails):
        """发送邮件"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.user
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = subject
            
            msg.attach(MIMEText(content, 'plain', 'utf-8'))
            
            with smtplib.SMTP_SSL(self.server, self.port) as server:
                server.login(self.user, self.password)
                server.sendmail(self.user, to_emails, msg.as_string())
            
            log_message(f"邮件发送成功: {subject}")
            return True
        except Exception as e:
            log_message(f"邮件发送失败: {e}")
            return False


class EmailSentTracker:
    """邮件发送频率跟踪器"""
    
    def __init__(self):
        self.sent = {
            'network_error': None,
            'other_error': None,
            'process_down': None,
            'no_response': None
        }
        self.load()
    
    def load(self):
        if os.path.exists(EMAIL_SENT_FILE):
            try:
                with open(EMAIL_SENT_FILE, 'r') as f:
                    data = json.load(f)
                    self.sent = data.get('sent', self.sent)
            except Exception as e:
                log_message(f"加载邮件发送记录失败: {e}")
    
    def save(self):
        try:
            with open(EMAIL_SENT_FILE, 'w') as f:
                json.dump({'sent': self.sent}, f, indent=2)
        except Exception as e:
            log_message(f"保存邮件发送记录失败: {e}")
    
    def can_send(self, alert_type):
        today = datetime.now().strftime('%Y-%m-%d')
        last_sent = self.sent.get(alert_type)
        return last_sent is None or last_sent != today
    
    def mark_sent(self, alert_type):
        today = datetime.now().strftime('%Y-%m-%d')
        self.sent[alert_type] = today
        self.save()


class MemoryManager:
    """内存字典管理"""
    
    def __init__(self):
        self.memory = {
            'normal': CircularBuffer(MAX_MEMORY_SIZE),
            'network_error': CircularBuffer(MAX_MEMORY_SIZE),
            'other_error': CircularBuffer(MAX_MEMORY_SIZE)
        }
        self.load()
    
    def load(self):
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, 'r') as f:
                    data = json.load(f)
                    for key in self.memory:
                        if key in data:
                            for item in data[key]:
                                self.memory[key].append(item)
            except Exception as e:
                log_message(f"加载内存文件失败: {e}")
    
    def save(self):
        try:
            data = {
                'normal': self.memory['normal'].to_list(),
                'network_error': self.memory['network_error'].to_list(),
                'other_error': self.memory['other_error'].to_list()
            }
            with open(MEMORY_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            log_message(f"保存内存文件失败: {e}")
    
    def add_normal(self, log_line):
        self.memory['normal'].append({
            'timestamp': datetime.now().isoformat(),
            'log': log_line
        })
        self.save()
    
    def add_network_error(self, log_line):
        self.memory['network_error'].append({
            'timestamp': datetime.now().isoformat(),
            'error': log_line
        })
        self.save()
    
    def add_other_error(self, log_line):
        self.memory['other_error'].append({
            'timestamp': datetime.now().isoformat(),
            'error': log_line
        })
        self.save()
    
    def get_network_stats_24h(self):
        network_count = len(self.memory['network_error'].get_recent_24h())
        normal_count = len(self.memory['normal'].get_recent_24h())
        return network_count, normal_count
    
    def get_other_error_count_24h(self):
        return len(self.memory['other_error'].get_recent_24h())


class LLMAnalyzer:
    """大模型分析器"""
    
    def __init__(self):
        self.api_url = OPENCLAW_API_URL
        self.gateway_token = OPENCLAW_GATEWAY_TOKEN
        self.enabled = USE_LLM_ANALYSIS
    
    def call_llm(self, prompt):
        """调用大模型"""
        try:
            response = requests.post(
                f"{self.api_url}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.gateway_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "openclaw",
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content'].strip()
            else:
                log_message(f"调用大模型失败: {response.status_code}")
                return None
        except Exception as e:
            log_message(f"调用大模型异常: {e}")
            return None
    
    def analyze_log(self, log_content):
        """使用大模型分析日志类型"""
        if not self.enabled:
            return None
        
        prompt = f"""这是一个Freqtrade量化交易程序的日志片段。

请分析这段日志属于哪种类型：

类型定义：
- 正常：程序正常运行，执行交易策略，生成买卖信号或持仓检查
- 网络异常：网络连接问题、API超时、WebSocket断开、交易所接口错误等
- 其他异常：代码错误、配置错误、数据格式错误、策略计算错误等

日志内容：
{log_content}

请直接返回类型名称（正常/网络异常/其他异常），不要返回其他内容。"""
        
        result = self.call_llm(prompt)
        if not result:
            return None
        
        if '正常' in result:
            return 'normal'
        elif '网络异常' in result:
            return 'network_error'
        elif '其他异常' in result:
            return 'other_error'
        else:
            log_message(f"大模型返回无法识别: {result}")
            return 'unknown'
    
    def analyze_error(self, error_log):
        """分析其他异常并生成解决方案"""
        prompt = f"""Freqtrade量化交易程序遇到异常，需要分析和解决。

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
是否重启: 是/否"""
        
        result = self.call_llm(prompt)
        if not result:
            return None
        
        # 解析结果
        analysis = {
            'raw_response': result,
            'error_type': '',
            'root_cause': '',
            'involved_files': '',
            'solution': ''
        }
        
        lines = result.split('\n')
        for line in lines:
            if '错误类型' in line:
                analysis['error_type'] = line.split(':', 1)[-1].strip()
            elif '根本原因' in line:
                analysis['root_cause'] = line.split(':', 1)[-1].strip()
            elif '涉及文件' in line:
                analysis['involved_files'] = line.split(':', 1)[-1].strip()
            elif '修改文件' in line or '修改内容' in line:
                analysis['solution'] += line + '\n'
        
        return analysis


def acquire_lock():
    """获取锁"""
    try:
        if os.path.exists(LOCK_FILE):
            with open(LOCK_FILE, 'r') as f:
                pid = f.read().strip()
            if pid and os.path.exists(f"/proc/{pid}"):
                return False
        with open(LOCK_FILE, 'w') as f:
            f.write(str(os.getpid()))
        return True
    except Exception as e:
        log_message(f"创建锁文件失败: {e}")
        return False


def release_lock():
    """释放锁"""
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except Exception:
        pass


def check_process_alive():
    """检查进程是否运行"""
    # 方式1：通过PID文件检查
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, 'r') as f:
                pid = f.read().strip()
            if pid and os.path.exists(f"/proc/{pid}"):
                # 验证是否是freqtrade进程
                with open(f"/proc/{pid}/cmdline", 'r') as f:
                    cmdline = f.read()
                if PROCESS_NAME in cmdline and CONFIG_FILE in cmdline:
                    return True, pid
        except:
            pass
    
    # 方式2：通过进程名检查
    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True
        )
        
        for line in result.stdout.split('\n'):
            if PROCESS_NAME in line and CONFIG_FILE in line and 'grep' not in line:
                parts = line.split()
                if len(parts) > 1:
                    pid = parts[1]
                    return True, pid
    except Exception as e:
        log_message(f"检查进程失败: {e}")
    
    return False, None


def start_freqtrade_process():
    """启动Freqtrade进程"""
    try:
        if not os.path.exists(START_SCRIPT):
            log_message(f"启动脚本不存在: {START_SCRIPT}")
            return False
        
        result = subprocess.run(
            ["bash", START_SCRIPT, "start"],
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            log_message("启动进程成功")
            time.sleep(5)
            alive, _ = check_process_alive()
            return alive
        else:
            log_message(f"启动进程失败: {result.stderr}")
            return False
    except Exception as e:
        log_message(f"启动进程异常: {e}")
        return False


def save_last_read_position(log_file, position):
    """保存日志读取位置"""
    try:
        with open(LAST_LINE_FILE, 'w') as f:
            f.write(f"{log_file}\n{position}")
    except Exception as e:
        log_message(f"保存读取位置失败: {e}")


def load_last_read_position():
    """加载日志读取位置"""
    try:
        if os.path.exists(LAST_LINE_FILE):
            with open(LAST_LINE_FILE, 'r') as f:
                lines = f.read().strip().split('\n')
                if len(lines) >= 2:
                    return lines[0], int(lines[1])
    except:
        pass
    return None, 0


def check_log_time_gap(log_file):
    """检查日志时间间隔"""
    try:
        result = subprocess.run(
            ["stat", "-c", "%Y", log_file],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            mtime = int(result.stdout.strip())
            now = int(time.time())
            return now - mtime
    except:
        pass
    return None


def analyze_logs(memory_manager):
    """分析日志"""
    if not os.path.exists(LOG_FILE):
        log_message("日志文件不存在")
        return
    
    # 检查日志时间间隔
    time_gap = check_log_time_gap(LOG_FILE)
    if time_gap is not None and time_gap > MAX_TIME_GAP:
        log_message(f"超过{time_gap/60:.1f}分钟无日志输出")
        return "no_response"
    
    # 获取上次读取位置
    last_file, last_position = load_last_read_position()
    
    # 如果日志文件变化，从头开始
    if last_file != LOG_FILE:
        last_position = 0
    
    try:
        with open(LOG_FILE, 'r') as f:
            # 移动到上次读取位置
            f.seek(last_position)
            
            # 读取新内容
            new_lines = []
            for line in f:
                new_lines.append(line)
            
            if not new_lines:
                log_message("无新日志内容")
                return
            
            # 分析新日志
            llm_analyzer = LLMAnalyzer()
            
            for line in new_lines:
                line = line.strip()
                if not line:
                    continue
                
                # 使用大模型分析
                result = llm_analyzer.analyze_log(line)
                
                if result == 'normal':
                    memory_manager.add_normal(line[:100])
                elif result == 'network_error':
                    memory_manager.add_network_error(line[:200])
                    log_message(f"网络异常: {line[:100]}")
                elif result == 'other_error':
                    memory_manager.add_other_error(line[:200])
                    log_message(f"其他异常: {line[:100]}")
            
            # 保存新的读取位置
            new_position = f.tell()
            save_last_read_position(LOG_FILE, new_position)
            
            log_message(f"分析了 {len(new_lines)} 行新日志")
    
    except Exception as e:
        log_message(f"分析日志失败: {e}")


def check_network_errors(memory_manager, email_tracker):
    """检查网络异常次数"""
    network_count, normal_count = memory_manager.get_network_stats_24h()
    
    log_message(f"最近24小时 - 网络异常: {network_count}次, 正常: {normal_count}次")
    
    if network_count > normal_count and normal_count < 5 and network_count > 0:
        if email_tracker.can_send('network_error'):
            error_msg = f"最近24小时网络异常次数({network_count}) > 正常次数({normal_count})"
            log_message(error_msg)
            
            email_sender = EmailSender()
            email_sender.send(
                subject="【警告】Freqtrade量化网络异常频繁",
                content=f"错误详情:\n{error_msg}\n\n检测时间: {datetime.now()}\n\n建议检查网络连接和代理配置。",
                to_emails=ALERT_EMAILS
            )
            
            email_tracker.mark_sent('network_error')
        else:
            log_message("今天已发送过网络异常告警邮件，跳过")


def check_other_errors(memory_manager, email_tracker):
    """检查其他异常次数"""
    other_error_count = memory_manager.get_other_error_count_24h()
    
    log_message(f"最近24小时 - 其他异常: {other_error_count}次")
    
    if other_error_count > 10:
        if email_tracker.can_send('other_error'):
            # 获取最近的其他异常
            recent_errors = memory_manager.memory['other_error'].get_recent_24h()
            last_error = recent_errors[-1] if recent_errors else {}
            error_log = last_error.get('error', 'N/A')
            
            # 调用大模型分析
            log_message("调用大模型分析其他异常...")
            llm_analyzer = LLMAnalyzer()
            analysis = llm_analyzer.analyze_error(error_log)
            
            if analysis:
                # 保存分析结果到文档
                analysis_file = os.path.join(LOG_DIR, f"error_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
                with open(analysis_file, 'w') as f:
                    f.write(f"# Freqtrade量化异常分析\n\n")
                    f.write(f"**分析时间**: {datetime.now()}\n\n")
                    f.write(f"**异常日志**:\n```\n{error_log}\n```\n\n")
                    f.write(f"**大模型分析**:\n\n{analysis.get('raw_response', 'N/A')}\n")
                
                log_message(f"分析结果已保存: {analysis_file}")
            
            # 发送邮件
            email_sender = EmailSender()
            email_sender.send(
                subject="【警告】Freqtrade量化程序异常频繁",
                content=f"错误详情:\n最近24小时其他异常次数: {other_error_count}次\n\n最后一次错误:\n{error_log}\n\n分析结果:\n{analysis.get('raw_response', 'N/A') if analysis else '分析失败'}\n\n检测时间: {datetime.now()}",
                to_emails=ALERT_EMAILS
            )
            
            email_tracker.mark_sent('other_error')
        else:
            log_message("今天已发送过其他异常告警邮件，跳过")


def main():
    """主函数"""
    log_message("=" * 70)
    log_message("Freqtrade量化监控脚本启动")
    log_message("=" * 70)
    
    # 获取锁
    if not acquire_lock():
        log_message("另一个检测进程正在运行，跳过本次检查")
        return
    
    try:
        memory_manager = MemoryManager()
        email_tracker = EmailSentTracker()
        
        # 1. 检查进程是否运行
        alive, pid = check_process_alive()
        
        if not alive:
            log_message("量化进程未运行")
            
            # 尝试启动进程（最多3次）
            success = False
            for i in range(3):
                log_message(f"尝试启动进程（第{i+1}次）...")
                if start_freqtrade_process():
                    success = True
                    break
                time.sleep(10)
            
            if not success:
                if email_tracker.can_send('process_down'):
                    log_message("启动进程失败，发送邮件通知")
                    email_sender = EmailSender()
                    email_sender.send(
                        subject="【严重】Freqtrade量化进程启动失败",
                        content=f"量化进程启动失败，已尝试3次。\n\n检测时间: {datetime.now()}\n\n请手动检查服务状态。",
                        to_emails=ALERT_EMAILS
                    )
                    email_tracker.mark_sent('process_down')
                return
        
        if pid:
            log_message(f"进程运行中，PID: {pid}")
        
        # 2. 分析日志
        result = analyze_logs(memory_manager)
        
        if result == "no_response":
            if email_tracker.can_send('no_response'):
                email_sender = EmailSender()
                email_sender.send(
                    subject="【警告】Freqtrade量化服务长时间无响应",
                    content=f"超过15分钟无日志输出，可能服务已停止。\n\n日志文件: {LOG_FILE}\n检测时间: {datetime.now()}",
                    to_emails=ALERT_EMAILS
                )
                email_tracker.mark_sent('no_response')
        
        # 3. 检查网络异常
        check_network_errors(memory_manager, email_tracker)
        
        # 4. 检查其他异常
        check_other_errors(memory_manager, email_tracker)
        
        log_message("监控检查完成")
    
    finally:
        release_lock()


if __name__ == "__main__":
    main()
