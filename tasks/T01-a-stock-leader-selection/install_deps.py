#!/usr/bin/env python3
"""
T01 选股系统 - 依赖安装脚本

用法:
    python3 install_deps.py          # 安装所有依赖
    python3 install_deps.py --check  # 检查依赖是否已安装
"""

import sys
import subprocess
import importlib.util
from pathlib import Path

# 依赖列表
REQUIRED_PACKAGES = {
    # 核心数据处理
    'pandas': 'pandas>=1.5.0',
    'numpy': 'numpy>=1.24.0',
    # 数据库
    'sqlalchemy': 'SQLAlchemy>=2.0.0',
    'psycopg2': 'psycopg2-binary>=2.9.0',  # PostgreSQL 驱动
    # 任务调度
    'schedule': 'schedule>=1.2.0',
    # 财经数据
    'tushare': 'tushare>=1.2.0',
    # 机器学习/数据分析
    'sklearn': 'scikit-learn>=1.3.0',
    'scipy': 'scipy>=1.10.0',
    # 遗传算法优化
    'deap': 'deap>=1.4.0',
    # HTTP请求
    'requests': 'requests>=2.28.0',
    # LLM 解析 (用于 Unifuncs 结果语义理解)
    'coze_coding_dev_sdk': 'coze-coding-dev-sdk>=0.5.0',
    'pptx': 'python-pptx>=1.0.0',
    'langchain_core': 'langchain-core>=0.1.0',
}


def check_package(package_name):
    """检查包是否已安装"""
    spec = importlib.util.find_spec(package_name)
    return spec is not None


def install_package(package_spec):
    """安装包"""
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package_spec, '-q'])
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ❌ 安装失败: {e}")
        return False


def check_dependencies():
    """检查所有依赖"""
    print("=" * 60)
    print("检查依赖状态...")
    print("=" * 60)
    
    missing = []
    installed = []
    
    for import_name, package_spec in REQUIRED_PACKAGES.items():
        if check_package(import_name):
            installed.append(import_name)
            print(f"  ✅ {import_name}")
        else:
            missing.append((import_name, package_spec))
            print(f"  ❌ {import_name} (未安装)")
    
    print(f"\n已安装: {len(installed)}/{len(REQUIRED_PACKAGES)}")
    
    return missing


def install_dependencies(missing=None):
    """安装所有依赖"""
    if missing is None:
        missing = check_dependencies()
    
    if not missing:
        print("\n✅ 所有依赖已安装！")
        return True
    
    print(f"\n开始安装 {len(missing)} 个缺失的依赖...")
    print("-" * 60)
    
    success_count = 0
    for import_name, package_spec in missing:
        print(f"  📦 安装 {package_spec}...", end=' ')
        if install_package(package_spec):
            print("✅")
            success_count += 1
        else:
            print("❌")
    
    print("-" * 60)
    print(f"\n安装完成: {success_count}/{len(missing)} 成功")
    
    # 再次检查
    remaining = check_dependencies()
    if remaining:
        print(f"\n⚠️ 仍有 {len(remaining)} 个依赖未安装")
        return False
    
    print("\n✅ 所有依赖安装完成！")
    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description='T01 选股系统依赖管理')
    parser.add_argument('--check', action='store_true', help='仅检查，不安装')
    parser.add_argument('--force', action='store_true', help='强制重新安装')
    args = parser.parse_args()
    
    if args.check:
        missing = check_dependencies()
        sys.exit(0 if not missing else 1)
    
    if args.force:
        # 强制安装所有
        missing = [(k, v) for k, v in REQUIRED_PACKAGES.items()]
    else:
        missing = check_dependencies()
    
    success = install_dependencies(missing)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
