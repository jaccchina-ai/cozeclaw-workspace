#!/bin/bash
# T01 选股系统 - 定时任务执行脚本
# 使用方法: 添加到系统的定时任务中

TUSHARE_TOKEN=870008d508d2b0e57ecf2ccc586c23c4ecc37522f5e93890fb3d56ab
export TUSHARE_TOKEN

WORK_DIR=/workspace/projects/workspace/tasks/T01-a-stock-leader-selection
LOG_DIR=/workspace/projects/workspace/logs

cd $WORK_DIR

# 获取当前时间
HOUR=$(date +%H)
MIN=$(date +%M)
DATE=$(date +%Y%m%d)
DAY_OF_WEEK=$(date +%w)

# 判断是否是工作日（简化判断，实际需要查询交易日历）
# 这里假设周一至周五为工作日
if [ $DAY_OF_WEEK -eq 0 ] || [ $DAY_OF_WEEK -eq 6 ]; then
    echo "周末，跳过交易任务"
    exit 0
fi

# 09:25 - T+1竞价选股
if [ "$HOUR$MIN" = "0925" ]; then
    echo "[$DATE 09:25] 执行 T+1 竞价选股..."
    python3 main.py t1-auction --date $DATE >> $LOG_DIR/t01_t1_auction_$DATE.log 2>&1
fi

# 15:05 - 结果跟踪
if [ "$HOUR$MIN" = "1505" ]; then
    echo "[$DATE 15:05] 执行结果跟踪..."
    python3 main.py track >> $LOG_DIR/t01_track_$DATE.log 2>&1
fi

# 20:00 - T日选股
if [ "$HOUR$MIN" = "2000" ]; then
    echo "[$DATE 20:00] 执行 T日选股..."
    python3 main.py t-day --date $DATE >> $LOG_DIR/t01_t_day_$DATE.log 2>&1
fi

# 20:00 周日 - 策略进化
if [ "$HOUR$MIN" = "2000" ] && [ $DAY_OF_WEEK -eq 0 ]; then
    echo "[$DATE 20:00] 执行策略进化..."
    python3 main.py evolution >> $LOG_DIR/t01_evolution_$DATE.log 2>&1
fi
