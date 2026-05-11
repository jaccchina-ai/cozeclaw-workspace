#!/bin/bash
# T01 选股系统调度器启动脚本

TUSHARE_TOKEN=870008d508d2b0e57ecf2ccc586c23c4ecc37522f5e93890fb3d56ab
export TUSHARE_TOKEN

cd /workspace/projects/workspace/tasks/T01-a-stock-leader-selection
exec /usr/bin/python3 main.py schedule
