#!/usr/bin/env python3
"""查看本周选股胜率"""
import sys
sys.path.insert(0, '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection')

from database.dual_db_manager import _dual_db_manager as DualDBManager

def main():
    db = DualDBManager()
    
    # 查看本周胜率
    result = db.execute_query(
        '''SELECT COUNT(*) as total, SUM(profit > 0) as profitable 
           FROM tracked_results 
           WHERE date >= date('now', '-7 days')'''
    )
    
    if result:
        total = result[0][0]
        profitable = result[0][1]
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
    result = db.execute_query(
        '''SELECT DISTINCT date 
           FROM stock_selections 
           WHERE date >= date('now', '-10 days') 
           ORDER BY date DESC'''
    )
    
    if result:
        dates = [row[0] for row in result]
        print(f"\n近10天选股日期:")
        print(f"  {', '.join(dates)}")
        
        # 检查是否有连续3天无选股
        import datetime
        today = datetime.date.today()
        consecutive_days = 0
        for i in range(3):
            check_date = today - datetime.timedelta(days=i+1)
            check_date_str = check_date.strftime('%Y-%m-%d')
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

if __name__ == "__main__":
    main()