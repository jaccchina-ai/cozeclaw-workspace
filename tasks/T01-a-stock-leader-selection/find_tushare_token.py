#!/usr/bin/env python3
"""
T01 选股系统 - Tushare Token 查找工具
"""

import os
import json
import re

def find_tushare_token():
    """全面查找Tushare Token"""
    print('=== 开始全面查找Tushare Token ===\n')
    
    tokens_found = []
    
    # 1. 环境变量
    env_token = os.environ.get('TUSHARE_TOKEN', '')
    if env_token and env_token != '请替换为你的Tushare token':
        tokens_found.append(('环境变量TUSHARE_TOKEN', env_token))
        print(f'✅ 1. 环境变量TUSHARE_TOKEN: {env_token[:10]}...')
    else:
        print(f'🔍 1. 环境变量TUSHARE_TOKEN: {"未找到" if not env_token else "占位符未替换"}')
    
    # 2. 常见配置文件位置
    config_paths = [
        'config.json',
        '../../config.json',
        '../config.json',
        '../../../config.json',
        'database/config.json',
        'tushare_config.json',
        'token_config.json'
    ]
    
    for i, path in enumerate(config_paths, start=2):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                token = config.get('tushare_token', '')
                if token and token != '请替换为你的Tushare token':
                    tokens_found.append((f'配置文件 {path}', token))
                    print(f'✅ {i}. 配置文件 {path}: {token[:10]}...')
                else:
                    print(f'🔍 {i}. 配置文件 {path}: {"未找到" if not token else "占位符未替换"}')
        except FileNotFoundError:
            print(f'🔍 {i}. 配置文件 {path}: 文件不存在')
        except json.JSONDecodeError:
            print(f'🔍 {i}. 配置文件 {path}: JSON解析错误')
        except Exception as e:
            print(f'🔍 {i}. 配置文件 {path}: 读取失败 - {str(e)}')
    
    # 3. 数据库配置文件
    try:
        with open('database/db_config.py', 'r', encoding='utf-8') as f:
            content = f.read()
            matches = re.findall(r'(TUSHARE_TOKEN|tushare_token)[\s]*=[\s]*[\"\']([^\"\']+)[\"\']', content)
            if matches:
                for match in matches:
                    token_name, token = match
                    if token and token != '请替换为你的Tushare token':
                        tokens_found.append((f'数据库配置 {token_name}', token))
                        print(f'✅ {len(config_paths)+1}. 数据库配置文件: {token[:10]}...')
            else:
                print(f'🔍 {len(config_paths)+1}. 数据库配置文件: 未找到')
    except FileNotFoundError:
        print(f'🔍 {len(config_paths)+1}. 数据库配置文件: 文件不存在')
    except Exception as e:
        print(f'🔍 {len(config_paths)+1}. 数据库配置文件: 读取失败 - {str(e)}')
    
    # 4. Python模块中的Token
    try:
        import sys
        sys.path.insert(0, os.path.dirname(__file__))
        
        # 尝试导入main.py
        try:
            from main import TUSHARE_TOKEN
            if TUSHARE_TOKEN and TUSHARE_TOKEN != '请替换为你的Tushare token':
                tokens_found.append(('main.py TUSHARE_TOKEN', TUSHARE_TOKEN))
                print(f'✅ {len(config_paths)+2}. main.py: {TUSHARE_TOKEN[:10]}...')
        except ImportError:
            pass
        except Exception as e:
            pass
            
        # 尝试导入tushare相关模块
        try:
            import tushare as ts
            if hasattr(ts, 'get_token'):
                token = ts.get_token()
                if token:
                    tokens_found.append(('Tushare模块缓存', token))
                    print(f'✅ {len(config_paths)+2}. Tushare模块缓存: {token[:10]}...')
        except Exception as e:
            pass
            
    except Exception as e:
        pass
    
    # 5. 其他可能的Python文件
    try:
        for root, dirs, files in os.walk('.'):
            for file in files:
                if file.endswith('.py') and file not in ['__pycache__', '__init__.py']:
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                            content = f.read()
                            matches = re.findall(r'(TUSHARE_TOKEN|tushare_token)[\s]*=[\s]*[\"\']([^\"\']+)[\"\']', content)
                            if matches:
                                for match in matches:
                                    token_name, token = match
                                    if token and token != '请替换为你的Tushare token' and token not in [t[1] for t in tokens_found]:
                                        tokens_found.append((f'Python文件 {os.path.join(root, file)}', token))
                                        print(f'✅ 找到额外Token: {token[:10]}... in {os.path.join(root, file)}')
                    except Exception as e:
                        pass
    except Exception as e:
        pass
    
    print('\n=== 查找完成 ===')
    
    if tokens_found:
        print(f'\n总共找到 {len(tokens_found)} 个有效Token:')
        for name, token in tokens_found:
            print(f'  - {name}: {token[:10]}...')
        return True
    else:
        print('\n❌ 未找到有效Tushare Token')
        print('\n请通过以下方式之一配置Token:')
        print('1. 设置环境变量: export TUSHARE_TOKEN="你的token"')
        print('2. 在config.json中配置: {"tushare_token": "你的token"}')
        print('3. 在database/db_config.py中添加: TUSHARE_TOKEN="你的token"')
        return False

if __name__ == '__main__':
    find_tushare_token()