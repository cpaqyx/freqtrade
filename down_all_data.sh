#!/bin/bash
# ========================================
# 下载所有现货与合约数据
# ========================================
# 
# 数据范围说明:
# - 日线:   2500天 (约7年)
# - 4小时:  1825天 (约5年)
# - 1小时:  1095天 (约3年)
# - 15分钟: 730天 (约2年)
# - 5分钟:  500天 (约1.4年)
#
# 交易对: BTC, ETH, SOL, XRP, ADA, DOGE, SUI, TRX, ENA
# ========================================

SCRIPT_DIR="/opt/git/freqtrade/user_data/common"
LOG_FILE="/var/log/freqtrade-download.log"

# 创建日志目录
mkdir -p /var/log

# 日志函数
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 执行下载脚本
run_download() {
  local script="$1"
  local name="$2"
  
  log "========================================"
  log "开始下载: $name"
  log "========================================"
  
  if [ -f "$script" ]; then
    bash "$script" 2>&1 | while read line; do
      log "$line"
    done
    
    if [ $? -eq 0 ]; then
      log "✅ $name 下载完成"
    else
      log "❌ $name 下载失败"
      return 1
    fi
  else
    log "❌ 脚本不存在: $script"
    return 1
  fi
  
  return 0
}

# 主程序
main() {
  log "========================================"
  log "开始下载所有数据"
  log "========================================"
  log "开始时间: $(date)"
  log ""
  
  # 现货数据
  log "========== 现货数据 =========="
  
  run_download "$SCRIPT_DIR/download_spot_1d.sh" "现货日线数据"
  run_download "$SCRIPT_DIR/download_spot_4h.sh" "现货4小时数据"
  run_download "$SCRIPT_DIR/download_spot_1h.sh" "现货1小时数据"
  run_download "$SCRIPT_DIR/download_spot_15m.sh" "现货15分钟数据"
  run_download "$SCRIPT_DIR/download_spot_5m.sh" "现货5分钟数据"
  
  log ""
  
  # 合约数据
  log "========== 合约数据 =========="
  
  run_download "$SCRIPT_DIR/download_futures_1d.sh" "合约日线数据"
  run_download "$SCRIPT_DIR/download_futures_4h.sh" "合约4小时数据"
  run_download "$SCRIPT_DIR/download_futures_1h.sh" "合约1小时数据"
  run_download "$SCRIPT_DIR/download_futures_15m.sh" "合约15分钟数据"
  run_download "$SCRIPT_DIR/download_futures_5m.sh" "合约5分钟数据"
  
  log ""
  log "========================================"
  log "所有数据下载完成！"
  log "结束时间: $(date)"
  log "========================================"
  log ""
  log "数据保存位置:"
  log "  现货: /opt/git/freqtrade/user_data/data/binance/spot/"
  log "  合约: /opt/git/freqtrade/user_data/data/binance/futures/"
  log ""
  log "日志文件: $LOG_FILE"
}

# 执行主程序
main
