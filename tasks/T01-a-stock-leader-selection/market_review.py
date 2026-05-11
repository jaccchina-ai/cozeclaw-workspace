#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T01 每日市场复盘分析

使用 mx_search 分析当日热点板块，评估持续性，生成投资参考报告

执行时间: 21:00 (工作日)
API配额: 约 6-8 次/天
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection')
from mx_search_integration import MxSearchIntegration


def analyze_market_review():
    """
    执行市场复盘分析
    
    分析流程:
    1. 获取大盘整体点评
    2. 分析热点行业板块持续性
    3. 分析热点概念板块持续性
    4. 生成投资参考报告
    """
    print("="*60)
    print("T01 每日市场复盘分析")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # 初始化 mx_search
    mx = MxSearchIntegration()
    
    # 检查配额
    if not mx.check_quota(8):
        print(f"\n⚠️ API配额不足 (剩余{mx.get_remaining_quota()}次)，跳过分析")
        return
    
    report = []
    report.append("📊 **T01每日市场复盘报告**")
    report.append(f"\n分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append("\n" + "="*50)
    
    # ===== 第一步: 大盘整体点评 =====
    print("\n🔍 步骤1: 获取大盘整体点评...")
    try:
        result = mx.client.search("今日A股大盘点评 热点板块分析")
        items = result.get('results', [])
        
        if items:
            first = items[0]
            market_summary = first.get('content', first.get('title', ''))[:500]
            report.append("\n**📈 大盘综述**")
            report.append(f"{market_summary}...")
            print(f"   ✅ 获取成功: {first.get('title', '')[:50]}...")
        else:
            report.append("\n**📈 大盘综述**")
            report.append("暂无大盘点评数据")
            print("   ⚠️ 无数据")
    except Exception as e:
        report.append(f"\n**📈 大盘综述**")
        report.append(f"获取失败: {e}")
        print(f"   ❌ 错误: {e}")
    
    # ===== 第二步: 热点行业板块分析 =====
    print("\n🔍 步骤2: 分析热点行业板块...")
    hot_sectors = [
        "电力板块", "新能源板块", "半导体板块", 
        "银行板块", "通信设备板块"
    ]
    
    sector_analysis = []
    for sector in hot_sectors[:3]:  # 只分析前3个，控制API消耗
        if not mx.check_quota(1):
            break
            
        try:
            print(f"   分析 {sector}...")
            result = mx.get_sector_hot_reason(sector)
            
            if result.get('has_reason'):
                # 评估持续性 (基于新闻数量和时效性)
                news_count = result.get('news_count', 0)
                if news_count >= 10:
                    sustainability = "🔥 高"
                elif news_count >= 5:
                    sustainability = "⚡ 中"
                else:
                    sustainability = "📉 低"
                
                sector_analysis.append({
                    'name': sector,
                    'news_count': news_count,
                    'sustainability': sustainability,
                    'reason': result.get('reason', '')[:100] + '...'
                })
                print(f"   ✅ {sector}: {sustainability} (新闻{news_count}条)")
            else:
                print(f"   ⚠️ {sector}: 无数据")
                
        except Exception as e:
            print(f"   ❌ {sector}: {e}")
    
    # 添加行业板块分析到报告
    if sector_analysis:
        report.append("\n" + "="*50)
        report.append("\n**🏭 热点行业板块分析**")
        report.append("\n| 板块 | 持续性 | 新闻数 | 要点 |")
        report.append("|------|--------|--------|------|")
        
        for sector in sorted(sector_analysis, 
                           key=lambda x: x['news_count'], 
                           reverse=True)[:3]:
            report.append(f"| {sector['name']} | {sector['sustainability']} | {sector['news_count']} | {sector['reason'][:50]}... |")
    
    # ===== 第三步: 热点概念板块分析 =====
    print("\n🔍 步骤3: 分析热点概念板块...")
    hot_concepts = [
        "商业航天概念", "人工智能概念", "数字经济概念",
        "国企改革概念", "智能制造概念"
    ]
    
    concept_analysis = []
    for concept in hot_concepts[:3]:  # 只分析前3个
        if not mx.check_quota(1):
            break
            
        try:
            print(f"   分析 {concept}...")
            result = mx.get_sector_hot_reason(concept)
            
            if result.get('has_reason'):
                news_count = result.get('news_count', 0)
                if news_count >= 10:
                    sustainability = "🔥 高"
                elif news_count >= 5:
                    sustainability = "⚡ 中"
                else:
                    sustainability = "📉 低"
                
                concept_analysis.append({
                    'name': concept,
                    'news_count': news_count,
                    'sustainability': sustainability,
                    'reason': result.get('reason', '')[:100] + '...'
                })
                print(f"   ✅ {concept}: {sustainability} (新闻{news_count}条)")
            else:
                print(f"   ⚠️ {concept}: 无数据")
                
        except Exception as e:
            print(f"   ❌ {concept}: {e}")
    
    # 添加概念板块分析到报告
    if concept_analysis:
        report.append("\n" + "="*50)
        report.append("\n**💡 热点概念板块分析**")
        report.append("\n| 概念 | 持续性 | 新闻数 | 要点 |")
        report.append("|------|--------|--------|------|")
        
        for concept in sorted(concept_analysis, 
                            key=lambda x: x['news_count'], 
                            reverse=True)[:3]:
            report.append(f"| {concept['name']} | {concept['sustainability']} | {concept['news_count']} | {concept['reason'][:50]}... |")
    
    # ===== 第四步: 投资建议 =====
    print("\n🔍 步骤4: 生成投资建议...")
    
    # 综合所有分析，推荐高持续性板块
    all_analysis = sector_analysis + concept_analysis
    high_sustainability = [x for x in all_analysis if "🔥" in x['sustainability']]
    medium_sustainability = [x for x in all_analysis if "⚡" in x['sustainability']]
    
    report.append("\n" + "="*50)
    report.append("\n**🎯 投资建议**")
    report.append("\n**重点关注 (高持续性):**")
    
    if high_sustainability:
        for item in high_sustainability[:3]:
            report.append(f"\n- **{item['name']}**: {item['sustainability']} - 新闻{item['news_count']}条")
    else:
        report.append("\n- 暂无高持续性板块")
    
    report.append("\n**适度关注 (中持续性):**")
    if medium_sustainability:
        for item in medium_sustainability[:3]:
            report.append(f"\n- **{item['name']}**: {item['sustainability']} - 新闻{item['news_count']}条")
    else:
        report.append("\n- 暂无中持续性板块")
    
    report.append("\n" + "="*50)
    report.append("\n⚠️ 以上分析仅供参考，不构成投资建议。")
    report.append(f"\n📅 报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # ===== 保存报告 =====
    report_text = '\n'.join(report)
    
    # 保存到文件
    report_file = f"/workspace/projects/workspace/logs/market_review_{datetime.now().strftime('%Y%m%d')}.md"
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_text)
        print(f"\n✅ 报告已保存: {report_file}")
    except Exception as e:
        print(f"\n⚠️ 保存报告失败: {e}")
    
    # 发送飞书消息（使用卡片格式）
    try:
        from messenger import get_messenger
        messenger = get_messenger()
        
        # 构建卡片元素
        elements = []
        
        # 大盘综述
        if '大盘综述' in report_text:
            import re
            summary_match = re.search(r'\*\*📈 大盘综述\*\*\n(.+?)(?:\n\n|=)', report_text, re.DOTALL)
            if summary_match:
                summary = summary_match.group(1).replace('**', '').strip()[:500]
                elements.append({
                    'tag': 'div',
                    'text': {'tag': 'lark_md', 'content': f"**📈 大盘综述**\n{summary}"}
                })
                elements.append({'tag': 'hr'})
        
        # 热点行业板块表格
        if sector_analysis:
            sector_table = "| 板块 | 持续性 | 新闻数 |\n|:---:|:---:|:---:|\n"
            for s in sorted(sector_analysis, key=lambda x: x['news_count'], reverse=True)[:5]:
                sector_table += f"| {s['name'][:4]} | {s['sustainability']} | {s['news_count']} |\n"
            elements.append({
                'tag': 'div',
                'text': {'tag': 'lark_md', 'content': f"**🏭 热点行业板块**\n{sector_table}"}
            })
            elements.append({'tag': 'hr'})
        
        # 热点概念板块表格
        if concept_analysis:
            concept_table = "| 概念 | 持续性 | 新闻数 |\n|:---:|:---:|:---:|\n"
            for c in sorted(concept_analysis, key=lambda x: x['news_count'], reverse=True)[:5]:
                concept_table += f"| {c['name'][:4]} | {c['sustainability']} | {c['news_count']} |\n"
            elements.append({
                'tag': 'div',
                'text': {'tag': 'lark_md', 'content': f"**💡 热点概念板块**\n{concept_table}"}
            })
            elements.append({'tag': 'hr'})
        
        # 投资建议
        all_analysis = sector_analysis + concept_analysis
        high_sus = [x for x in all_analysis if "🔥" in x['sustainability']]
        
        suggest_content = "**🎯 投资建议**\n"
        if high_sus:
            suggest_content += "**重点关注**: " + "、".join([x['name'][:4] for x in high_sus[:3]]) + "\n"
        else:
            suggest_content += "**重点关注**: 暂无高持续性板块\n"
        
        elements.append({
            'tag': 'div',
            'text': {'tag': 'lark_md', 'content': suggest_content}
        })
        
        # 底部备注
        elements.append({
            'tag': 'note',
            'elements': [{'tag': 'plain_text', 'content': f'⚠️ 仅供参考，不构成投资建议 | {datetime.now().strftime("%Y-%m-%d %H:%M")}'}]
        })
        
        # 发送卡片消息
        messenger.send_card(
            title=f"📊 T01每日市场复盘 - {datetime.now().strftime('%Y-%m-%d')}",
            elements=elements,
            template='blue'
        )
        print(f"✅ 飞书卡片消息已发送")
    except Exception as e:
        print(f"⚠️ 飞书发送失败: {e}")
        # 备用：保存到消息队列
        try:
            msg_file = f"/workspace/projects/workspace/logs/messages/market_review_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(msg_file, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"✅ 消息已保存到队列: {msg_file}")
        except Exception as e2:
            print(f"⚠️ 保存消息也失败: {e2}")
    
    # 输出报告
    print("\n" + "="*60)
    print("分析报告:")
    print("="*60)
    print(report_text)
    
    # 显示API使用情况
    usage_report = mx.get_usage_report()
    print("\n" + "="*60)
    print(f"API使用统计: {usage_report['used_today']}/{usage_report['total_quota']} ({usage_report['usage_rate']})")
    print("="*60)
    
    return report_text


if __name__ == '__main__':
    analyze_market_review()
