"""
T01 选股系统 - Heartbeat 任务处理

用于检查并发送待发送的消息文件
"""

import os
import glob
from datetime import datetime

def check_and_send_pending_messages():
    """
    检查并发送待发送的消息文件
    
    此函数由 OpenClaw heartbeat 调用
    返回消息列表，供外部发送
    """
    message_dir = '/workspace/projects/workspace/logs/messages'
    
    if not os.path.exists(message_dir):
        return []
    
    # 获取所有待发送的消息文件
    pattern = os.path.join(message_dir, '*.txt')
    files = glob.glob(pattern)
    
    if not files:
        return []
    
    # 按时间排序
    files.sort()
    
    messages = []
    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析文件名获取类型
            filename = os.path.basename(filepath)
            parts = filename.replace('.txt', '').split('_')
            msg_type = parts[0] if parts else 'unknown'
            
            messages.append({
                'type': msg_type,
                'content': content,
                'file': filepath
            })
            
        except Exception as e:
            print(f"读取消息文件失败 {filepath}: {e}")
    
    return messages


def mark_message_sent(filepath: str):
    """标记消息已发送（移动文件到 sent 目录）"""
    try:
        message_dir = '/workspace/projects/workspace/logs/messages'
        sent_dir = os.path.join(message_dir, 'sent')
        os.makedirs(sent_dir, exist_ok=True)
        
        filename = os.path.basename(filepath)
        new_path = os.path.join(sent_dir, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}")
        
        os.rename(filepath, new_path)
        print(f"✅ 消息已标记为已发送: {new_path}")
        return True
    except Exception as e:
        print(f"❌ 标记消息失败: {e}")
        return False


def get_heartbeat_status():
    """获取心跳任务状态"""
    message_dir = '/workspace/projects/workspace/logs/messages'
    
    pending_count = 0
    if os.path.exists(message_dir):
        pattern = os.path.join(message_dir, '*.txt')
        pending_count = len(glob.glob(pattern))
    
    return {
        'pending_messages': pending_count,
        'message_dir': message_dir
    }


if __name__ == '__main__':
    # 测试
    status = get_heartbeat_status()
    print(f"待发送消息: {status['pending_messages']}")
    
    messages = check_and_send_pending_messages()
    for msg in messages:
        print(f"\n{'='*60}")
        print(f"类型: {msg['type']}")
        print(f"文件: {msg['file']}")
        print(f"内容:\n{msg['content'][:200]}...")
