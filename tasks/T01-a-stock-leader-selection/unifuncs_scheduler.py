"""
T01 选股系统 - Unifuncs 调度模块

每天19:30提前调用 Unifuncs 获取舆情分析结果
每隔5分钟查询一次，最多5次（25分钟超时）
结果保存到本地文件和 SQLite 数据库供 20:00 选股使用
"""

import os
import sys
import json
import time
import re
from datetime import datetime
from typing import Dict, Optional, List

sys.path.insert(0, os.path.dirname(__file__))
from data_fetcher import create_fetcher
from monitor import Monitor
from messenger import get_messenger
from database.dual_write_manager import get_dual_write_manager


# 文件存储路径
RESULT_FILE = os.path.join(
    os.path.dirname(__file__),
    'unifuncs_result.json'
)


def extract_structured_summary_with_llm(answer: str, model: str = "doubao-seed-1-6-lite-251015") -> Dict:
    """
    使用 LLM 大模型理解 Unifuncs 返回内容的语义，提取结构化摘要
    
    相比正则表达式，LLM 方式优势：
    1. 理解语义，不受格式变化影响
    2. 更灵活，能处理各种格式的返回内容
    3. 可以提取更丰富的信息
    4. 减少维护正则表达式的负担
    
    Args:
        answer: Unifuncs 返回的完整报告文本
        model: 使用的模型，默认 doubao-seed-1-6-lite-251015（快速、低成本）
        
    Returns:
        结构化摘要字典，包含热点板块和推荐股票
    """
    summary = {
        'hot_sectors': [],
        'recommendations': [],
        'extraction_method': 'llm',
        'model': model
    }
    
    if not answer:
        return summary
    
    try:
        from coze_coding_dev_sdk import LLMClient
        from langchain_core.messages import SystemMessage, HumanMessage
        
        # 定义系统提示词
        system_prompt = """你是一个专业的A股市场分析师助手。你的任务是从市场分析报告中提取结构化信息。

你需要提取两类信息：
1. **热点板块**：当前市场最热门的概念板块（如：F5G概念、算力租赁、6G概念等）
2. **推荐股票**：下一交易日继续涨停概率最大的股票

输出要求：
- 必须返回有效的 JSON 格式
- 不要输出任何额外的解释或说明
- 只输出 JSON 对象

输出格式：
{
  "hot_sectors": ["板块1", "板块2", "板块3"],
  "recommendations": [
    {"rank": 1, "name": "股票名", "code": "代码", "probability": "概率", "reason": "推荐理由"},
    {"rank": 2, "name": "股票名", "code": "代码", "probability": "概率", "reason": "推荐理由"},
    {"rank": 3, "name": "股票名", "code": "代码", "probability": "概率", "reason": "推荐理由"}
  ]
}

注意事项：
- hot_sectors 提取 3-5 个最热门的板块
- recommendations 最多 3-5 只股票
- probability 是涨停概率（如 "65%"）
- 如果报告中没有相关信息，返回空数组
- 股票代码必须是 6 位数字"""

        # 构建用户消息
        user_message = f"""请从以下 A股市场分析报告中提取热点板块和推荐股票：

---
{answer[:8000]}  # 限制长度避免超出 token 限制
---

请提取结构化信息并以 JSON 格式输出。"""

        # 调用 LLM
        client = LLMClient()
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ]
        
        response = client.invoke(
            messages=messages,
            model=model,
            temperature=0.1,  # 低温度保证稳定输出
            max_completion_tokens=2000
        )
        
        # 安全地获取响应内容
        if isinstance(response.content, str):
            content = response.content.strip()
        elif isinstance(response.content, list):
            # 处理列表格式响应
            if response.content and isinstance(response.content[0], str):
                content = " ".join(response.content).strip()
            else:
                text_parts = []
                for item in response.content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                content = " ".join(text_parts).strip()
        else:
            content = str(response.content)
        
        # 提取 JSON（处理可能的 markdown 代码块）
        if "```json" in content:
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content)
            if json_match:
                content = json_match.group(1)
        elif "```" in content:
            json_match = re.search(r'```\s*([\s\S]*?)\s*```', content)
            if json_match:
                content = json_match.group(1)
        
        # 解析 JSON
        parsed = json.loads(content)
        
        summary['hot_sectors'] = parsed.get('hot_sectors', [])
        summary['recommendations'] = parsed.get('recommendations', [])
        
        print(f"   🤖 LLM 解析完成 (模型: {model})")
        print(f"   📊 热点板块: {summary['hot_sectors']}")
        print(f"   📈 推荐股票: {[r['code'] + ' ' + r['name'] for r in summary['recommendations']]}")
        
    except Exception as e:
        print(f"   ⚠️ LLM 解析失败: {e}，回退到正则表达式方式")
        # 回退到正则表达式方式
        summary = extract_structured_summary(answer)
        summary['extraction_method'] = 'regex_fallback'
    
    return summary


def extract_structured_summary(answer: str) -> Dict:
    """
    从 Unifuncs 返回的完整报告中提取结构化摘要
    
    Args:
        answer: Unifuncs 返回的完整报告文本
        
    Returns:
        结构化摘要字典，包含热点板块和推荐股票
    """
    summary = {
        'hot_sectors': [],
        'recommendations': []
    }
    
    if not answer:
        return summary
    
    try:
        # 1. 提取热点板块
        sectors_found = []
        
        # 方法0：匹配编号列表格式（优先级最高，这是 Unifuncs 当前返回的格式）
        # 格式: 1. **F5G概念** - 涨幅4.84% 或 2. **算力租赁** - 涨幅3.94%
        numbered_pattern = r'\d+\.\s*\*\*([^*]+概念)\*\*'
        numbered_matches = re.findall(numbered_pattern, answer)
        for match in numbered_matches[:5]:
            sector = match.strip()
            if sector and len(sector) < 15 and sector not in sectors_found:
                sectors_found.append(sector)
        
        # 方法1：匹配 "主线一/二/三：" 格式
        if not sectors_found:
            mainline_pattern = r'\*\*主线[一二三四五六七八九十]+[：:]\s*([^*]+)\*\*'
            mainline_matches = re.findall(mainline_pattern, answer)
            for match in mainline_matches:
                # 清理括号内容，只保留核心板块名
                sector = match.strip()
                # 提取括号前的主体
                if '（' in sector:
                    sector = sector.split('（')[0].strip()
                elif '(' in sector:
                    sector = sector.split('(')[0].strip()
                if sector and len(sector) < 20 and sector not in sectors_found:
                    sectors_found.append(sector)
        
        # 方法2：匹配 "热点板块前三名" 格式
        if not sectors_found:
            top3_match = re.search(r'热点板块前三名.*?为[：:]?\s*(.+?)(?:\n|。)', answer)
            if top3_match:
                top3_text = top3_match.group(1)
                # 提取 **xxx** 格式
                sector_items = re.findall(r'\*\*([^*]+)\*\*', top3_text)
                for item in sector_items:
                    # 清理括号内容
                    sector = re.sub(r'[（(].*?[）)]', '', item).strip()
                    if sector and len(sector) < 15:
                        sectors_found.append(sector)
        
        # 方法3：从标题提取（第X热点：xxx）
        if not sectors_found:
            header_pattern = r'第[一二三🥇🥈🥉]+热点[：:]\s*([^\n\-]+)'
            header_matches = re.findall(header_pattern, answer)
            for match in header_matches:
                sector = match.strip()
                # 清理
                sector = re.sub(r'[（(].*?[）)]', '', sector).strip()
                sector = re.sub(r'\s*[-－]\s*.*$', '', sector).strip()
                if sector and len(sector) < 15:
                    sectors_found.append(sector)
        
        # 方法4：从章节标题提取（如 "一、化工板块"）
        if not sectors_found:
            chapter_pattern = r'[一二三四五六七八九十]+[、.．]\s*([^。\n]{2,10}板块)'
            chapter_matches = re.findall(chapter_pattern, answer)
            for match in chapter_matches:
                sector = match.strip()
                if sector and len(sector) < 15:
                    sectors_found.append(sector)
        
        # 方法5：通用的"板块"提取（兜底）
        if not sectors_found:
            sector_pattern = r'\*\*([^*]+板块)\*\*'
            all_sectors = re.findall(sector_pattern, answer)
            sectors_found = list(dict.fromkeys(all_sectors))[:5]  # 去重取前5
        
        # 去重并限制数量
        sectors_found = list(dict.fromkeys(sectors_found))[:5]
        summary['hot_sectors'] = sectors_found
        
        # 2. 提取推荐股票 - 同时执行多种方法，合并结果
        
        # 方法0：从"综合预测结论"部分提取（优先级最高）
        # 查找"下一交易日继续涨停概率最大的三只股票"或"综合预测结论"
        conclusion_markers = ['综合预测结论', '下一交易日继续涨停概率最大的三只股票', '最终结论与推荐排序']
        for marker in conclusion_markers:
            conclusion_start = answer.find(marker)
            if conclusion_start >= 0:
                conclusion_text = answer[conclusion_start:conclusion_start+3000]
                
                # 格式C: **第一名：华电辽能（600396）** （无 emoji，实际常见格式）
                no_emoji_pattern = r'\*\*第[一二三四五]名[：:]\s*([^*（(]+)[（(](\d{6})[）)]\*\*'
                no_emoji_matches = re.findall(no_emoji_pattern, conclusion_text)
                
                for match in no_emoji_matches:
                    name = match[0].strip()
                    code = match[1].strip()
                    
                    # 在结论文本中查找概率
                    prob_pattern = rf'{code}.*?继续涨停概率[：:]*\s*(\d+%-?\d*%?)'
                    prob_match = re.search(prob_pattern, conclusion_text, re.DOTALL)
                    probability = prob_match.group(1) if prob_match else ''
                    
                    existing_codes = [r['code'] for r in summary['recommendations']]
                    if code not in existing_codes:
                        summary['recommendations'].append({
                            'rank': len(summary['recommendations']) + 1,
                            'name': name,
                            'code': code,
                            'consecutive_boards': 0,
                            'probability': probability,
                            'reason': 'Unifuncs综合推荐',
                            'source': 'conclusion'
                        })
                
                # 格式B: **🥇 第一名：中国电建（601669）** （带 emoji）
                medal_pattern = r'\*\*[🥇🥈🥉]+\s*第[一二三四五]名[：:]\s*([^*（(]+)[（(](\d{6})[）)]\*\*'
                medal_matches = re.findall(medal_pattern, conclusion_text)
                
                for match in medal_matches:
                    name = match[0].strip()
                    code = match[1].strip()
                    
                    # 提取概率
                    prob_pattern = rf'{code}.*?次日涨停概率[：:]*\*\*(\d+%-?\d*%?)\*\*'
                    prob_match = re.search(prob_pattern, conclusion_text, re.DOTALL)
                    probability = prob_match.group(1) if prob_match else ''
                    
                    existing_codes = [r['code'] for r in summary['recommendations']]
                    if code not in existing_codes:
                        summary['recommendations'].append({
                            'rank': len(summary['recommendations']) + 1,
                            'name': name,
                            'code': code,
                            'consecutive_boards': 0,
                            'probability': probability,
                            'reason': 'Unifuncs最终推荐',
                            'source': 'conclusion'
                        })
                
                # 如果找到了，就不需要继续查找其他 marker
                if summary['recommendations']:
                    break
        
        # 方法1：匹配编号列表格式
        # 格式: 1. **协鑫能科（002015）** - 6天3板，虚拟电厂+液冷概念
        list_pattern = r'^\s*(\d+)\.\s*\*\*([^*（(]+)[（(](\d{6})[）)]\*\*\s*[-－]\s*(\d+天?\d*板|\d+连板)[，,]?\s*(.*)$'
        
        for line in answer.split('\n'):
            match = re.match(list_pattern, line.strip())
            if match:
                rank = int(match.group(1))
                name = match.group(2).strip()
                code = match.group(3).strip()
                board_status = match.group(4).strip()
                reason = match.group(5).strip() if match.group(5) else ''
                
                # 提取连板数
                board_match = re.search(r'(\d+)', board_status)
                consecutive_boards = int(board_match.group(1)) if board_match else 0
                
                summary['recommendations'].append({
                    'rank': rank,
                    'name': name,
                    'code': code,
                    'consecutive_boards': consecutive_boards,
                    'probability': '',  # 列表格式不包含概率
                    'reason': reason,
                    'source': 'list'  # 标记来源
                })
        
        # 方法2：匹配表格格式（同时执行，不是互斥）
        # 新格式: | 1 | **瑞斯康达（603803）** | 2板 | 核心驱动... | ￥12.10 | 关键价位... |
        # 或者: | **宁波建工** | 601789 | 4连板 | 75%-85% |
        
        # 尝试匹配新表格格式
        new_table_pattern = r'\|\s*(\d+)\s*\|\s*\*\*([^*（(]+)[（(](\d{6})[）)]\*\*\s*\|\s*(\d+板|\d+连板|\d+天\d+板)\s*\|\s*([^|]+)\s*\|'
        new_table_matches = re.findall(new_table_pattern, answer)
        
        for match in new_table_matches:
            rank = int(match[0])
            name = match[1].strip()
            code = match[2].strip()
            board_status = match[3].strip()
            reason = match[4].strip()
            
            # 提取连板数
            board_match = re.search(r'(\d+)', board_status)
            consecutive_boards = int(board_match.group(1)) if board_match else 0
            
            # 检查是否已存在（按代码去重）
            existing_codes = [r['code'] for r in summary['recommendations']]
            if code not in existing_codes:
                summary['recommendations'].append({
                    'rank': rank,
                    'name': name,
                    'code': code,
                    'consecutive_boards': consecutive_boards,
                    'probability': '',
                    'reason': reason,
                    'source': 'new_table'  # 标记来源
                })
        
        # 尝试匹配旧表格格式
        old_table_pattern = r'\|\s*\*{0,2}([^|]+)\*{0,2}\s*\|\s*(\d{6})\s*\|\s*(\d+连板|\d+天\d+板)\s*\|\s*\*{0,2}(\d+%-?\d*%?)\*{0,2}\s*\|\s*([^|]+)\s*\|'
        old_table_matches = re.findall(old_table_pattern, answer)
        
        for i, match in enumerate(old_table_matches):
            name = match[0].strip().replace('*', '')
            code = match[1].strip()
            board_status = match[2].strip()
            probability = match[3].strip()
            reason = match[4].strip()
            
            # 提取连板数
            board_match = re.search(r'(\d+)', board_status)
            consecutive_boards = int(board_match.group(1)) if board_match else 0
            
            # 检查是否已存在（按代码去重）
            existing_codes = [r['code'] for r in summary['recommendations']]
            if code not in existing_codes:
                summary['recommendations'].append({
                    'rank': len(summary['recommendations']) + 1,
                    'name': name,
                    'code': code,
                    'consecutive_boards': consecutive_boards,
                    'probability': probability,
                    'reason': reason,
                    'source': 'old_table'  # 标记来源
                })
        
        # 方法4：匹配中文顿号分隔的内联格式
        # 格式: **三安光电（600703）、绿发电力（000537）、郑州煤电（600121）**
        if not summary['recommendations']:
            # 先尝试匹配整段加粗的股票列表
            # 匹配 **股票A（代码A）、股票B（代码B）、股票C（代码C）**
            bold_block_pattern = r'\*\*([^*]+?)\*\*'
            bold_blocks = re.findall(bold_block_pattern, answer)
            
            for block in bold_blocks:
                # 在这个块中匹配所有（代码）
                stock_pattern = r'([^、，,\s（(]+)[（(](\d{6})[）)]'
                stock_matches = re.findall(stock_pattern, block)
                
                if len(stock_matches) >= 2:  # 至少2只股票才算列表
                    for i, match in enumerate(stock_matches[:6]):
                        name = match[0].strip()
                        code = match[1].strip()
                        
                        # 检查是否已存在
                        existing_codes = [r['code'] for r in summary['recommendations']]
                        if code not in existing_codes:
                            summary['recommendations'].append({
                                'rank': i + 1,
                                'name': name,
                                'code': code,
                                'consecutive_boards': 0,
                                'probability': '',
                                'reason': 'AI报告推荐',
                                'source': 'inline_bold'
                            })
                    break  # 只取第一个匹配的块
        
        # 按rank排序，保留前6个推荐（合并后可能是3-6只）
        summary['recommendations'] = sorted(summary['recommendations'], key=lambda x: x['rank'])[:6]
        
    except Exception as e:
        print(f"   ⚠️ 提取摘要失败: {e}")
    
    return summary


def create_unifuncs_task(date_str: str) -> str:
    """
    创建 Unifuncs 任务

    Args:
        date_str: 日期字符串 YYYY-MM-DD

    Returns:
        task_id
    """
    # 添加 unifuncs skill 路径
    unifuncs_path = '/workspace/projects/workspace/skills/unifuncs/scripts'
    if os.path.exists(unifuncs_path):
        sys.path.insert(0, unifuncs_path)

    try:
        from unifuncs_client import UnifuncsClient

        client = UnifuncsClient()

        # 构建提示词：热点板块（通达信概念）+ 连板概率分析
        prompt = f"{date_str}A股通达信概念板块的热点是什么？请使用通达信概念板块名称（如：稀土永磁、互联金融、数字货币等，不要用申万行业分类）。在{date_str}所有涨停股票中，剔除连板数大于3的涨停股后，在下一个交易日能继续涨停概率最大的三个股票是什么？"

        print(f"   创建 Unifuncs 任务...")
        print(f"   提示词: {prompt}")

        task_id = client.create_task(output_prompt=prompt)
        print(f"   ✅ 任务创建成功，ID: {task_id}")

        return task_id

    except Exception as e:
        print(f"   ❌ 创建任务失败: {e}")
        raise


def query_unifuncs_task(task_id: str):
    """
    查询 Unifuncs 任务状态

    Args:
        task_id: 任务ID

    Returns:
        TaskResult 对象，失败返回 None
    """
    unifuncs_path = '/workspace/projects/workspace/skills/unifuncs/scripts'
    if os.path.exists(unifuncs_path):
        sys.path.insert(0, unifuncs_path)

    try:
        from unifuncs_client import UnifuncsClient

        client = UnifuncsClient()
        result = client.query_task(task_id)

        return result

    except Exception as e:
        print(f"   ⚠️ 查询任务失败: {e}")
        return None


def save_result(date: str, result_data: Dict, use_llm: bool = True, llm_model: str = "doubao-seed-1-6-lite-251015"):
    """
    保存 Unifuncs 结果到本地文件和 SQLite 数据库
    
    结构化保存：
    - task_id: 任务ID
    - status: 状态
    - hot_sectors: 热点板块列表
    - recommendations: 推荐股票列表 [{name, code, consecutive_boards, probability, reason}]
    - created_at: 创建时间
    - extraction_method: 提取方式 (llm/regex)

    Args:
        date: 日期字符串 YYYYMMDD
        result_data: 结果数据（可以是字典或 TaskResult 对象）
        use_llm: 是否使用 LLM 解析（默认 True）
        llm_model: LLM 模型（默认 doubao-seed-1-6-lite-251015）
    """
    try:
        # 读取现有数据
        existing_data = {}
        if os.path.exists(RESULT_FILE):
            with open(RESULT_FILE, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)

        # 提取答案文本
        answer_text = ''
        raw_response = ''
        if hasattr(result_data, 'task_id'):
            # TaskResult 对象
            answer_text = result_data.answer or ''
            task_id = result_data.task_id
            status = result_data.status
            raw_response = getattr(result_data, 'raw_response', '') or ''
        else:
            # 普通字典
            answer_text = result_data.get('answer', '')
            task_id = result_data.get('task_id', '')
            status = result_data.get('status', '')
            raw_response = result_data.get('raw_response', '')

        # 选择解析方式
        if use_llm:
            structured = extract_structured_summary_with_llm(answer_text, model=llm_model)
        else:
            structured = extract_structured_summary(answer_text)
        
        # 构建结构化数据
        data_to_save = {
            'task_id': task_id,
            'status': status,
            'hot_sectors': structured['hot_sectors'],
            'recommendations': structured['recommendations'],
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'extraction_method': structured.get('extraction_method', 'regex')
        }

        # 更新当天的数据
        existing_data[date] = data_to_save

        # 写回文件
        with open(RESULT_FILE, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)

        print(f"   ✅ 结构化结果已保存到 {RESULT_FILE}")
        print(f"   📊 热点板块: {structured['hot_sectors']}")
        print(f"   📈 推荐股票: {[r['code'] + ' ' + r['name'] for r in structured['recommendations']]}")

        # ========== 双写数据库 (PostgreSQL + SQLite) ==========
        try:
            db_manager = get_dual_write_manager()
            
            # 准备数据库记录
            db_record = {
                'trade_date': date,
                'task_id': task_id,
                'status': status,
                'hot_sectors': json.dumps(structured['hot_sectors'], ensure_ascii=False),
                'recommendations': json.dumps(structured['recommendations'], ensure_ascii=False),
                'answer': answer_text[:10000] if answer_text else '',  # 限制长度
                'summary': '',
                'extraction_method': structured.get('extraction_method', 'regex'),
                'llm_model': llm_model if use_llm else '',
                'raw_response': json.dumps(raw_response, ensure_ascii=False)[:5000] if raw_response else ''
            }
            
            # 双写
            results = db_manager.save_unifuncs_result(db_record)
            
            pg_ok = results.get('postgres', False)
            sqlite_ok = results.get('sqlite', False)
            
            if pg_ok and sqlite_ok:
                print(f"   💾 双写结果: ✅ PostgreSQL ✅, SQLite ✅")
            elif pg_ok:
                print(f"   💾 双写结果: ✅ PostgreSQL ✅, SQLite ❌")
            elif sqlite_ok:
                print(f"   💾 双写结果: ❌ PostgreSQL ❌, SQLite ✅")
            else:
                print(f"   💾 双写结果: ❌ 都失败")
            
        except Exception as db_e:
            print(f"   ⚠️ 数据库写入失败: {db_e}")

    except Exception as e:
        print(f"   ❌ 保存结果失败: {e}")


def load_result(date: str) -> Optional[Dict]:
    """
    从本地文件读取 Unifuncs 结果

    Args:
        date: 日期字符串 YYYYMMDD

    Returns:
        结果数据字典，如果不存在返回 None
        字典结构: {task_id, status, answer, summary, ...}
    """
    try:
        if not os.path.exists(RESULT_FILE):
            return None

        with open(RESULT_FILE, 'r', encoding='utf-8') as f:
            all_data = json.load(f)

        return all_data.get(date)

    except Exception as e:
        print(f"   ⚠️ 读取结果失败: {e}")
        return None


def run_unifuncs_warmup(date: str = None):
    """
    执行 Unifuncs 预热任务

    19:30 运行，提前获取舆情分析结果

    流程：
    1. 检查是否为交易日
    2. 创建 Unifuncs 任务
    3. 轮询任务状态（5分钟间隔，最多5次）
    4. 保存结果或通知超时
    """
    monitor = Monitor()
    log_id = monitor.start_task('unifuncs_warmup', date)

    print(f"\n{'='*60}")
    print(f"Unifuncs 预热任务 - {datetime.now()}")
    print(f"{'='*60}\n")

    try:
        # 1. 确定日期
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        date_display = f"{date[:4]}-{date[4:6]}-{date[6:8]}"

        print(f"   📅 处理日期: {date_display}")

        # 2. 检查是否为交易日
        fetcher = create_fetcher()
        if not fetcher.is_trading_day(date):
            print(f"   ❌ {date_display} 不是交易日，跳过 Unifuncs 预热")
            monitor.end_task(log_id, 'success', result_count=0)
            return

        print(f"   ✅ {date_display} 是交易日")

        # 3. 创建 Unifuncs 任务
        print(f"   🚀 开始创建 Unifuncs 任务...")
        task_id = create_unifuncs_task(date_display)
        print(f"   ✅ 任务创建成功，ID: {task_id}")
        monitor.log_api_call('unifuncs_create', True, 0)

        # 4. 轮询任务状态
        max_attempts = 5
        wait_seconds = 5 * 60  # 5分钟

        print(f"\n   开始轮询任务状态（最多{max_attempts}次，间隔5分钟）...")

        result_data = None
        for attempt in range(1, max_attempts + 1):
            print(f"\n   第 {attempt}/{max_attempts} 次查询...")
            print(f"   🕒 当前时间: {datetime.now()}")

            result_data = query_unifuncs_task(task_id)
            monitor.log_api_call('unifuncs_query', True, 0)

            if result_data:
                status = result_data.status
                print(f"   📊 任务状态: {status}")

                if status == 'completed':
                    print(f"   ✅ 任务完成！")
                    answer = result_data.answer or ''
                    summary = result_data.summary or ''
                    print(f"   📝 答案长度: {len(answer)} 字符")
                    print(f"   📄 摘要: {summary[:100] if summary else '无'}..." if summary else '')

                    # 保存结果
                    print(f"   💾 开始保存结果...")
                    save_result(date, {
                        'task_id': task_id,
                        'status': status,
                        'answer': answer,
                        'summary': summary,
                        'raw_response': result_data.raw_response
                    })
                    print(f"   ✅ 结果保存完成")

                    monitor.end_task(log_id, 'success', result_count=1)
                    return

                elif status == 'failed':
                    error_msg = result_data.error or '未知错误'
                    print(f"   ❌ 任务失败: {error_msg}")
                    monitor.create_alert(
                        alert_type='unifuncs_failed',
                        severity='error',
                        title='Unifuncs 任务失败',
                        message=error_msg,
                        trade_date=date
                    )
                    monitor.end_task(log_id, 'failed', error_message='任务失败')
                    return
                elif status == 'pending':
                    print(f"   ⏳ 任务仍在处理中...")
                else:
                    print(f"   ℹ️ 任务状态: {status}")

            else:
                print(f"   ⚠️ 未获取到任务数据")

            # 等待下一次查询（最后一次不等待）
            if attempt < max_attempts:
                print(f"   ⏳ 等待 {wait_seconds//60} 分钟后继续查询...")
                time.sleep(wait_seconds)

        # 5. 超时处理
        print(f"\n   ⚠️ 超时！任务在 {max_attempts * 5} 分钟内未完成")

        # 保存超时状态
        save_result(date, {
            'task_id': task_id,
            'status': 'timeout',
            'answer': '',
            'summary': '',
            'error': '25分钟内未完成'
        })

        # 飞书通知
        messenger = get_messenger()
        try:
            message = f"""🦞 Unifuncs 预热超时提醒

日期: {date_display}
任务ID: {task_id}
状态: 超时（25分钟内未返回结果）

⚠️ 20:00 晚间选股将使用空结果继续执行"""
            # 使用 openclaw message send
            import subprocess
            subprocess.run([
                'openclaw', 'message', 'send',
                '--channel', 'feishu',
                '--target', 'ou_cf1fa11596236b5fb32fa3f4efec8d2a',
                '--message', message
            ], check=True)
            print(f"   ✅ 已发送飞书通知")
        except Exception as e:
            print(f"   ⚠️ 发送飞书通知失败: {e}")

        # 创建告警
        monitor.create_alert(
            alert_type='unifuncs_timeout',
            severity='warning',
            title='Unifuncs 预热超时',
            message=f'{date_display} 的舆情分析任务在25分钟内未完成',
            trade_date=date
        )

        monitor.end_task(log_id, 'failed', error_message='超时')

    except Exception as e:
        print(f"\n   ❌ Unifuncs 预热任务异常: {e}")
        monitor.end_task(log_id, 'failed', error_message=str(e))
        monitor.create_alert(
            alert_type='unifuncs_error',
            severity='error',
            title='Unifuncs 预热异常',
            message=str(e),
            trade_date=date
        )
        raise


if __name__ == '__main__':
    # 测试运行
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', type=str, help='日期 YYYYMMDD')
    args = parser.parse_args()

    run_unifuncs_warmup(args.date)
