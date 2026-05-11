#!/bin/bash
# T01 选股系统 - OpenClaw Cron 任务脚本
# 这个脚本被 OpenClaw Cron 调用执行选股任务

TUSHARE_TOKEN=870008d508d2b0e57ecf2ccc586c23c4ecc37522f5e93890fb3d56ab
export TUSHARE_TOKEN

WORK_DIR=/workspace/projects/workspace/tasks/T01-a-stock-leader-selection
LOG_DIR=/workspace/projects/workspace/logs

cd $WORK_DIR

# 获取当前日期
DATE=$(date +%Y%m%d)

# 执行竞价选股
echo "[$DATE 09:25] 执行 T+1 竞价选股..."
python3 main.py t1-auction --date $DATE >> $LOG_DIR/t01_t1_auction_$DATE.log 2>&1
echo "竞价选股完成，退出码: $?"
