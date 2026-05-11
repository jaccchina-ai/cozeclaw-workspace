#!/bin/bash
# T01 A股龙头选股系统 - 部署脚本
# 用法: ./deploy.sh

set -e

echo "============================================================"
echo "🚀 T01 A股龙头选股系统 - 部署脚本"
echo "============================================================"

PROJECT_DIR="/workspace/projects/workspace/tasks/T01-a-stock-leader-selection"
LOGS_DIR="/workspace/projects/workspace/logs/t01"

cd "$PROJECT_DIR"

# 1. 检查Python版本
echo ""
echo "📋 步骤 1/5: 检查Python版本..."
python3 --version || { echo "❌ Python3 未安装"; exit 1; }

# 2. 创建日志目录
echo ""
echo "📋 步骤 2/5: 创建日志目录..."
mkdir -p "$LOGS_DIR"
mkdir -p "/workspace/projects/workspace/logs/messages/sent"
echo "✅ 日志目录已创建: $LOGS_DIR"

# 3. 安装依赖
echo ""
echo "📋 步骤 3/5: 安装Python依赖..."
python3 "$PROJECT_DIR/install_deps.py"

# 4. 初始化数据库
echo ""
echo "📋 步骤 4/5: 初始化数据库..."
python3 -c "
import sys
sys.path.insert(0, '$PROJECT_DIR')
from database.models import init_db
init_db()
print('✅ 数据库初始化完成')
"

# 5. 测试运行
echo ""
echo "📋 步骤 5/5: 运行健康检查..."
python3 -c "
import sys
sys.path.insert(0, '$PROJECT_DIR')
from logging_config import get_logs_summary
from install_deps import check_dependencies

print('')
print('依赖检查:')
missing = check_dependencies()
if missing:
    print('❌ 有依赖未安装')
    sys.exit(1)
else:
    print('✅ 所有依赖已安装')

print('')
print('日志系统检查:')
summary = get_logs_summary()
print(f'✅ 日志目录: {summary[\"log_dir\"]}')
"

echo ""
echo "============================================================"
echo "✅ 部署完成!"
echo "============================================================"
echo ""
echo "常用命令:"
echo "  查看日志摘要:  python3 logs_viewer.py --summary"
echo "  查看今日日志:  python3 logs_viewer.py --today"
echo "  查看错误日志:  python3 logs_viewer.py --errors"
echo "  运行T日选股:   python3 main.py t-day"
echo "  运行T+1选股:   python3 main.py t1-auction"
echo ""
echo "定时任务配置:"
echo "  查看: openclaw cron list"
echo "  已在运行的任务:"
echo "    - T01-T1-Auction (09:25 工作日)"
echo "    - T01-Track (15:45 工作日)"
echo "    - T01-T-Day (20:00 工作日)"
echo "    - T01-Evolution (20:00 周日)"
echo ""
