#!/usr/bin/env python3
"""查看本周选股胜率"""
import sqlite3
import os
import datetime

def main():
    # 连接SQLite数据库
    db_path = '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection/database/t01_stocks.db'
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 查看本周胜率
    cursor.execute(
        '''SELECT COUNT(*) as total, SUM(is_win) as profitable 
           FROM tracked_results 
           WHERE t_day >= date('now', '-7 days')'''
    )
    result = cursor.fetchone()
    
    if result:
        total = result[0]
        profitable = result[1]
        print(f"本周选股统计:")
        print(f"  总交易数: {total}")
        print(f"  盈利交易数: {profitable}")
        if total > 0:
            win_rate = (profitable / total) * 100
            print(f"  胜率: {win_rate:.2f}%")
        else:
            print(f"  胜率: 0% (无交易记录)")
    else:
        print("无交易数据")
    
    # 检查连续3天无选股告警
    cursor.execute(
        '''SELECT DISTINCT t_day 
           FROM selection_results 
           WHERE t_day >= date('now', '-10 days') 
           ORDER BY t_day DESC'''
    )
    results = cursor.fetchall()
    
    if results:
        dates = [row[0] for row in results]
        print(f"\n近10天选股日期:")
        print(f"  {', '.join(dates)}")
        
        # 检查是否有连续3天无选股
        today = datetime.date.today()
        consecutive_days = 0
        for i in range(3):
            check_date = today - datetime.timedelta(days=i+1)
            check_date_str = check_date.strftime('%Y%m%d')  # 注意格式是YYYYMMDD
            if check_date_str not in dates:
                consecutive_days += 1
            else:
                break
        
        if consecutive_days >= 3:
            print(f"\n⚠️ 告警: 已连续{consecutive_days}天无选股记录")
        else:
            print(f"\n✅ 无连续3天无选股告警")
    else:
        print(f"\n⚠️ 告警: 近10天无选股记录")
    
    # 关闭连接
    conn.close()

if __name__ == "__main__":
    main()