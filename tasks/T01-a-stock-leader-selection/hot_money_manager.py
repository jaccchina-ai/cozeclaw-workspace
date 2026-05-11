"""
T01 选股系统 - 游资画像管理模块

功能：
1. 游资画像数据库管理
2. 游资席位识别与匹配
3. 游资操作追踪与统计
4. 游资信号评分
"""

import os
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))

from database.models import (
    get_session, init_db,
    HotMoneyProfile, HotMoneySeat, HotMoneyTrade, HotMoneyStats
)


# ==================== 初始游资数据库 ====================

# 知名游资画像数据（精选市场主流游资）
INITIAL_HOT_MONEY_PROFILES = [
    {
        'hot_money_id': 'zhangmengzhu',
        'hot_money_name': '章盟主',
        'style_tags': ['打板', '连板', '大市值'],
        'position_style': '短线',
        'preferred_mv': '大盘',
        'preferred_sector': ['科技', '新能源', '军工'],
        'description': '市场顶级游资，擅长大市值股票打板，资金实力雄厚',
        'influence_score': 10,
        'follow_value': 9,
        'typical_stocks': ['东方财富', '中信证券', '宁德时代']
    },
    {
        'hot_money_id': 'hujialou',
        'hot_money_name': '呼家楼',
        'style_tags': ['打板', '连板', '龙头'],
        'position_style': '短线',
        'preferred_mv': '中盘',
        'preferred_sector': ['科技', '新能源', '医药'],
        'description': '北京顶级游资，擅长龙头股接力，操作果断',
        'influence_score': 10,
        'follow_value': 9,
        'typical_stocks': ['省广集团', '道恩股份']
    },
    {
        'hot_money_id': 'niusan',
        'hot_money_name': '炒股养家',
        'style_tags': ['首板', '低吸', '情绪'],
        'position_style': '短线',
        'preferred_mv': '中盘',
        'preferred_sector': ['科技', '医药', '消费'],
        'description': '养家心法创始人，擅长情绪博弈和低吸',
        'influence_score': 9,
        'follow_value': 8,
        'typical_stocks': ['九安医疗', '以岭药业']
    },
    {
        'hot_money_id': 'zhaolaoge',
        'hot_money_name': '赵老哥',
        'style_tags': ['打板', '连板', '龙头'],
        'position_style': '短线',
        'preferred_mv': '中小盘',
        'preferred_sector': ['科技', '新能源'],
        'description': '八年一万倍传奇，擅长龙头战法',
        'influence_score': 10,
        'follow_value': 9,
        'typical_stocks': ['省广集团', '星期六']
    },
    {
        'hot_money_id': '92kebi',
        'hot_money_name': '92科比',
        'style_tags': ['打板', '连板', '龙头'],
        'position_style': '短线',
        'preferred_mv': '中小盘',
        'preferred_sector': ['科技', '新能源', '医药'],
        'description': '新生代游资代表，擅长龙头接力',
        'influence_score': 9,
        'follow_value': 8,
        'typical_stocks': []
    },
    {
        'hot_money_id': 'qiaobangzhu',
        'hot_money_name': '乔帮主',
        'style_tags': ['打板', '首板', '低吸'],
        'position_style': '短线',
        'preferred_mv': '中小盘',
        'preferred_sector': ['科技', '医药'],
        'description': '深圳顶级游资，擅长首板和低吸',
        'influence_score': 8,
        'follow_value': 7,
        'typical_stocks': []
    },
    {
        'hot_money_id': 'foshanwuyingjiao',
        'hot_money_name': '佛山无影脚',
        'style_tags': ['打板', '首板', '撬板'],
        'position_style': '超短线',
        'preferred_mv': '中小盘',
        'preferred_sector': ['科技', '医药', '消费'],
        'description': '佛山系游资领袖，擅长撬板和首板',
        'influence_score': 9,
        'follow_value': 8,
        'typical_stocks': []
    },
    {
        'hot_money_id': 'xiaoyaozi',
        'hot_money_name': '逍遥子',
        'style_tags': ['打板', '连板', '龙头'],
        'position_style': '短线',
        'preferred_mv': '中盘',
        'preferred_sector': ['科技', '新能源'],
        'description': '杭州顶级游资，擅长龙头股操作',
        'influence_score': 8,
        'follow_value': 7,
        'typical_stocks': []
    },
    {
        'hot_money_id': 'wulinmengzhu',
        'hot_money_name': '武林盟主',
        'style_tags': ['打板', '连板'],
        'position_style': '短线',
        'preferred_mv': '中盘',
        'preferred_sector': ['科技', '新能源'],
        'description': '浙江系游资代表',
        'influence_score': 7,
        'follow_value': 6,
        'typical_stocks': []
    },
    {
        'hot_money_id': 'zuoyouhufu',
        'hot_money_name': '左右护法',
        'style_tags': ['打板', '连板'],
        'position_style': '短线',
        'preferred_mv': '中小盘',
        'preferred_sector': ['科技', '医药'],
        'description': '新生代游资，操作风格犀利',
        'influence_score': 7,
        'follow_value': 6,
        'typical_stocks': []
    },
]

# 游资席位映射表（席位名称 -> 游资ID）
INITIAL_HOT_MONEY_SEATS = [
    # 章盟主
    {'seat_name': '国泰君安证券上海江苏路证券营业部', 'hot_money_id': 'zhangmengzhu', 'is_primary': True},
    {'seat_name': '国泰君安证券上海分公司', 'hot_money_id': 'zhangmengzhu', 'is_primary': False},
    
    # 呼家楼
    {'seat_name': '中国国际金融股份有限公司北京建国门外大街证券营业部', 'hot_money_id': 'hujialou', 'is_primary': True},
    {'seat_name': '中信证券北京总部', 'hot_money_id': 'hujialou', 'is_primary': False},
    {'seat_name': '中信证券北京金融大街证券营业部', 'hot_money_id': 'hujialou', 'is_primary': False},
    {'seat_name': '瑞银证券有限责任公司北京金融大街证券营业部', 'hot_money_id': 'hujialou', 'is_primary': False},
    
    # 炒股养家
    {'seat_name': '华鑫证券有限责任公司上海分公司', 'hot_money_id': 'niusan', 'is_primary': True},
    {'seat_name': '华鑫证券上海茅台路证券营业部', 'hot_money_id': 'niusan', 'is_primary': False},
    
    # 赵老哥
    {'seat_name': '银河证券绍兴证券营业部', 'hot_money_id': 'zhaolaoge', 'is_primary': True},
    {'seat_name': '浙商证券绍兴分公司', 'hot_money_id': 'zhaolaoge', 'is_primary': False},
    {'seat_name': '银河证券北京阜成路证券营业部', 'hot_money_id': 'zhaolaoge', 'is_primary': False},
    
    # 92科比
    {'seat_name': '中国中投证券南京太平南路证券营业部', 'hot_money_id': '92kebi', 'is_primary': True},
    {'seat_name': '中天证券股份有限公司南京太平南路证券营业部', 'hot_money_id': '92kebi', 'is_primary': False},
    
    # 乔帮主
    {'seat_name': '招商证券深圳蛇口工业七路证券营业部', 'hot_money_id': 'qiaobangzhu', 'is_primary': True},
    {'seat_name': '国泰君安证券深圳登良路证券营业部', 'hot_money_id': 'qiaobangzhu', 'is_primary': False},
    
    # 佛山无影脚
    {'seat_name': '光大证券佛山绿景路证券营业部', 'hot_money_id': 'foshanwuyingjiao', 'is_primary': True},
    {'seat_name': '光大证券佛山季华六路证券营业部', 'hot_money_id': 'foshanwuyingjiao', 'is_primary': False},
    {'seat_name': '湘财证券佛山祖庙路证券营业部', 'hot_money_id': 'foshanwuyingjiao', 'is_primary': False},
    
    # 逍遥子
    {'seat_name': '财通证券杭州体育场路证券营业部', 'hot_money_id': 'xiaoyaozi', 'is_primary': True},
    
    # 武林盟主（改为不同席位）
    {'seat_name': '浙商证券绍兴人民东路证券营业部', 'hot_money_id': 'wulinmengzhu', 'is_primary': True},
    
    # 左右护法
    {'seat_name': '中国银河证券股份有限公司北京建国门证券营业部', 'hot_money_id': 'zuoyouhufu', 'is_primary': True},
]

# 量化席位名单（跟随价值低，甚至减分）
QUANT_SEATS = [
    '华鑫证券上海分公司',  # 华鑫上海分（量化集中营）
    '华鑫证券有限责任公司上海分公司',
    '中信证券西安朱雀大街证券营业部',  # 朱雀大街
    '华泰证券股份有限公司总部',
    '中国国际金融股份有限公司上海分公司',
]

# 机构席位关键词
INSTITUTION_KEYWORDS = [
    '机构专用',
    '沪股通',
    '深股通',
    '港资',
]


class HotMoneyManager:
    """游资画像管理器"""
    
    def __init__(self):
        self.session = get_session()
        self._seat_cache = None
        self._profile_cache = None
        
    def initialize_database(self):
        """初始化游资数据库"""
        print("🔧 初始化游资画像数据库...")
        
        # 检查是否已有数据
        existing = self.session.query(HotMoneyProfile).count()
        if existing > 0:
            print(f"   游资数据库已存在 {existing} 条记录，跳过初始化")
            return
        
        try:
            # 插入游资画像
            for profile_data in INITIAL_HOT_MONEY_PROFILES:
                # 检查是否已存在
                existing_profile = self.session.query(HotMoneyProfile).filter(
                    HotMoneyProfile.hot_money_id == profile_data['hot_money_id']
                ).first()
                
                if not existing_profile:
                    profile = HotMoneyProfile(
                        hot_money_id=profile_data['hot_money_id'],
                        hot_money_name=profile_data['hot_money_name'],
                        style_tags=json.dumps(profile_data.get('style_tags', []), ensure_ascii=False),
                        position_style=profile_data.get('position_style', '短线'),
                        preferred_mv=profile_data.get('preferred_mv', ''),
                        preferred_sector=json.dumps(profile_data.get('preferred_sector', []), ensure_ascii=False),
                        description=profile_data.get('description', ''),
                        influence_score=profile_data.get('influence_score', 5),
                        follow_value=profile_data.get('follow_value', 5),
                        typical_stocks=json.dumps(profile_data.get('typical_stocks', []), ensure_ascii=False),
                        is_active=True
                    )
                    self.session.add(profile)
            
            # 插入席位数据
            for seat_data in INITIAL_HOT_MONEY_SEATS:
                # 检查是否已存在
                existing_seat = self.session.query(HotMoneySeat).filter(
                    HotMoneySeat.seat_name == seat_data['seat_name']
                ).first()
                
                if not existing_seat:
                    seat = HotMoneySeat(
                        seat_name=seat_data['seat_name'],
                        hot_money_id=seat_data['hot_money_id'],
                        is_primary=seat_data.get('is_primary', False),
                        seat_type='知名游资'
                    )
                    self.session.add(seat)
            
            # 插入量化席位
            for seat_name in QUANT_SEATS:
                existing_seat = self.session.query(HotMoneySeat).filter(
                    HotMoneySeat.seat_name == seat_name
                ).first()
                
                if not existing_seat:
                    seat = HotMoneySeat(
                        seat_name=seat_name,
                        hot_money_id='quant',
                        seat_type='量化'
                    )
                    self.session.add(seat)
            
            self.session.commit()
            print(f"   ✅ 初始化完成：{len(INITIAL_HOT_MONEY_PROFILES)} 个游资画像，"
                  f"{len(INITIAL_HOT_MONEY_SEATS) + len(QUANT_SEATS)} 个席位")
        
        except Exception as e:
            self.session.rollback()
            print(f"   ⚠️ 初始化部分失败（可能已有数据）: {e}")
    
    def _load_seat_cache(self):
        """加载席位缓存"""
        if self._seat_cache is not None:
            return self._seat_cache
            
        seats = self.session.query(HotMoneySeat).all()
        self._seat_cache = {}
        
        for seat in seats:
            self._seat_cache[seat.seat_name] = {
                'hot_money_id': seat.hot_money_id,
                'seat_type': seat.seat_type,
                'is_primary': seat.is_primary
            }
        
        return self._seat_cache
    
    def _load_profile_cache(self):
        """加载游资画像缓存"""
        if self._profile_cache is not None:
            return self._profile_cache
            
        profiles = self.session.query(HotMoneyProfile).all()
        self._profile_cache = {}
        
        for profile in profiles:
            self._profile_cache[profile.hot_money_id] = {
                'name': profile.hot_money_name,
                'style_tags': json.loads(profile.style_tags) if profile.style_tags else [],
                'influence_score': profile.influence_score,
                'follow_value': profile.follow_value,
                'win_rate': profile.win_rate,
                'position_style': profile.position_style,
                'preferred_mv': profile.preferred_mv,
                'preferred_sector': json.loads(profile.preferred_sector) if profile.preferred_sector else []
            }
        
        return self._profile_cache
    
    def identify_seats(self, exalter_list: List[str]) -> Dict:
        """
        识别龙虎榜席位类型
        
        Args:
            exalter_list: 席位名称列表
            
        Returns:
            识别结果字典
        """
        result = {
            'hot_money_seats': [],      # 知名游资席位
            'hot_money_ids': [],        # 游资ID列表
            'institution_seats': [],    # 机构席位
            'quant_seats': [],          # 量化席位
            'unknown_seats': [],        # 未识别席位
            'top_influence': 0,         # 最高影响力评分
            'total_follow_value': 0     # 总跟随价值
        }
        
        seat_cache = self._load_seat_cache()
        profile_cache = self._load_profile_cache()
        
        identified_ids = set()
        
        for exalter in exalter_list:
            if not exalter:
                continue
                
            # 1. 精确匹配席位
            if exalter in seat_cache:
                seat_info = seat_cache[exalter]
                seat_type = seat_info['seat_type']
                hm_id = seat_info['hot_money_id']
                
                if seat_type == '量化' or hm_id == 'quant':
                    result['quant_seats'].append(exalter)
                elif seat_type == '知名游资':
                    result['hot_money_seats'].append(exalter)
                    identified_ids.add(hm_id)
            else:
                # 2. 关键词匹配
                matched = False
                
                # 机构席位
                for keyword in INSTITUTION_KEYWORDS:
                    if keyword in exalter:
                        result['institution_seats'].append(exalter)
                        matched = True
                        break
                
                # 量化席位关键词
                if not matched:
                    for keyword in QUANT_SEATS:
                        if keyword in exalter:
                            result['quant_seats'].append(exalter)
                            matched = True
                            break
                
                # 知名游资名称匹配
                if not matched:
                    for profile_id, profile_info in profile_cache.items():
                        if profile_info['name'] in exalter:
                            result['hot_money_seats'].append(exalter)
                            identified_ids.add(profile_id)
                            matched = True
                            break
                
                # 知名游资地址匹配（处理券商改名问题）
                if not matched:
                    # 成都北一环路 - 知名游资聚集地
                    if '成都北一环路' in exalter or '成都北一环' in exalter:
                        result['hot_money_seats'].append(exalter)
                        # 默认关联到活跃游资（无法确定具体是谁）
                        matched = True
                    # 拉萨系列 - 散户集中地（东方财富）
                    elif '拉萨' in exalter and ('东环路' in exalter or '团结路' in exalter or '金融城' in exalter):
                        result['quant_seats'].append(exalter)
                        matched = True
                    # 其他知名地址
                    elif any(addr in exalter for addr in ['绍兴营业部', '深圳蛇口', '上海江苏路', '北京金融大街']):
                        result['hot_money_seats'].append(exalter)
                        matched = True
                
                if not matched:
                    result['unknown_seats'].append(exalter)
        
        # 计算影响力评分
        result['hot_money_ids'] = list(identified_ids)
        for hm_id in identified_ids:
            if hm_id in profile_cache:
                profile = profile_cache[hm_id]
                result['top_influence'] = max(result['top_influence'], profile['influence_score'])
                result['total_follow_value'] += profile['follow_value']
        
        return result
    
    def get_hot_money_score(self, dragon_tiger_data: Dict, stock_mv: float = 0) -> Tuple[float, Dict]:
        """
        计算游资信号评分
        
        Args:
            dragon_tiger_data: 龙虎榜数据
            stock_mv: 股票市值（亿）
            
        Returns:
            (评分, 详细信息)
        """
        score = 5  # 基础分
        details = {
            'hot_money_names': [],
            'hot_money_seats': [],
            'institution_seats': [],
            'quant_seats': [],
            'style_match': False,
            'top_influence': 0,
            'total_follow_value': 0
        }
        
        if not dragon_tiger_data:
            return score, details
        
        # 获取席位列表
        top_inst = dragon_tiger_data.get('top_inst', [])
        if not top_inst:
            # 使用原始数据中的席位
            details['hot_money_seats'] = dragon_tiger_data.get('hot_money_seats', [])
            details['institution_seats'] = dragon_tiger_data.get('institution_seats', [])
            details['quant_seats'] = dragon_tiger_data.get('quant_seats', [])
        else:
            # 重新识别
            exalter_list = [inst.get('exalter', '') for inst in top_inst if inst.get('exalter')]
            identified = self.identify_seats(exalter_list)
            details['hot_money_seats'] = identified['hot_money_seats']
            details['institution_seats'] = identified['institution_seats']
            details['quant_seats'] = identified['quant_seats']
            details['top_influence'] = identified['top_influence']
            details['total_follow_value'] = identified['total_follow_value']
            
            # 获取游资名称
            profile_cache = self._load_profile_cache()
            for hm_id in identified['hot_money_ids']:
                if hm_id in profile_cache:
                    details['hot_money_names'].append(profile_cache[hm_id]['name'])
        
        # 评分规则
        # 1. 知名游资：每个+2分，最高+6分
        hot_money_count = len(details['hot_money_seats'])
        score += min(hot_money_count * 2, 6)
        
        # 2. 机构席位：每个+1分，最高+3分
        institution_count = len(details['institution_seats'])
        score += min(institution_count, 3)
        
        # 3. 量化席位：每个-2分，最低-6分
        quant_count = len(details['quant_seats'])
        score -= min(quant_count * 2, 6)
        
        # 4. 影响力加成
        if details['top_influence'] >= 9:
            score += 2
        elif details['top_influence'] >= 8:
            score += 1
        
        # 5. 净买入金额
        net_buy = dragon_tiger_data.get('net_buy', 0) or 0
        if net_buy > 5000:  # 净买入>5000万
            score += 2
        elif net_buy > 3000:  # 净买入>3000万
            score += 1
        elif net_buy < -3000:  # 净卖出>3000万
            score -= 2
        
        # 限制分数范围
        score = max(0, min(15, score))
        
        return score, details
    
    def record_hot_money_trade(self, trade_date: str, ts_code: str, stock_name: str,
                                seat_name: str, buy_amount: float, sell_amount: float,
                                stock_status: str = ''):
        """
        记录游资操作
        
        Args:
            trade_date: 交易日期
            ts_code: 股票代码
            stock_name: 股票名称
            seat_name: 席位名称
            buy_amount: 买入金额（万元）
            sell_amount: 卖出金额（万元）
            stock_status: 股票状态（首板/2板/3板等）
        """
        # 识别席位
        identified = self.identify_seats([seat_name])
        
        if not identified['hot_money_ids'] and not identified['seat_type'] == '知名游资':
            return  # 非知名游资，不记录
        
        hm_id = identified['hot_money_ids'][0] if identified['hot_money_ids'] else 'unknown'
        
        # 检查是否已存在
        existing = self.session.query(HotMoneyTrade).filter(
            HotMoneyTrade.trade_date == trade_date,
            HotMoneyTrade.ts_code == ts_code,
            HotMoneyTrade.seat_name == seat_name
        ).first()
        
        if existing:
            return
        
        # 创建记录
        trade = HotMoneyTrade(
            trade_date=trade_date,
            ts_code=ts_code,
            stock_name=stock_name,
            hot_money_id=hm_id,
            seat_name=seat_name,
            trade_type='买入' if buy_amount > sell_amount else '卖出',
            buy_amount=buy_amount,
            sell_amount=sell_amount,
            net_buy=buy_amount - sell_amount,
            stock_status=stock_status,
            source='龙虎榜'
        )
        
        self.session.add(trade)
        self.session.commit()
    
    def update_hot_money_stats(self, hot_money_id: str, days: int = 30):
        """
        更新游资统计数据
        
        Args:
            hot_money_id: 游资ID
            days: 统计天数
        """
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
        
        # 查询操作记录
        trades = self.session.query(HotMoneyTrade).filter(
            HotMoneyTrade.hot_money_id == hot_money_id,
            HotMoneyTrade.trade_date >= start_date,
            HotMoneyTrade.trade_date <= end_date
        ).all()
        
        if not trades:
            return
        
        # 计算统计指标
        total_trades = len(trades)
        win_count = sum(1 for t in trades if t.is_win)
        loss_count = total_trades - win_count
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0
        
        avg_return = sum(t.t2_return or 0 for t in trades) / total_trades if total_trades > 0 else 0
        
        # 更新画像
        profile = self.session.query(HotMoneyProfile).filter(
            HotMoneyProfile.hot_money_id == hot_money_id
        ).first()
        
        if profile:
            profile.total_trades = total_trades
            profile.win_count = win_count
            profile.loss_count = loss_count
            profile.win_rate = win_rate
            profile.avg_return = avg_return
            profile.last_trade_date = max(t.trade_date for t in trades)
            
        self.session.commit()
    
    def get_hot_money_ranking(self, days: int = 30, top_n: int = 10) -> List[Dict]:
        """
        获取游资排行榜
        
        Args:
            days: 统计天数
            top_n: 返回数量
            
        Returns:
            游资排行列表
        """
        profiles = self.session.query(HotMoneyProfile).filter(
            HotMoneyProfile.is_active == True
        ).order_by(HotMoneyProfile.follow_value.desc()).limit(top_n).all()
        
        result = []
        for profile in profiles:
            result.append({
                'hot_money_id': profile.hot_money_id,
                'name': profile.hot_money_name,
                'win_rate': profile.win_rate,
                'total_trades': profile.total_trades,
                'influence_score': profile.influence_score,
                'follow_value': profile.follow_value,
                'style_tags': json.loads(profile.style_tags) if profile.style_tags else []
            })
        
        return result
    
    def close(self):
        """关闭数据库会话"""
        self.session.close()


def create_hot_money_manager() -> HotMoneyManager:
    """创建游资管理器实例"""
    manager = HotMoneyManager()
    manager.initialize_database()
    return manager


if __name__ == '__main__':
    # 测试
    manager = create_hot_money_manager()
    
    print("\n=== 游资排行榜 ===")
    ranking = manager.get_hot_money_ranking()
    for i, hm in enumerate(ranking):
        print(f"{i+1}. {hm['name']}: 胜率{hm['win_rate']:.1f}%, 影响力{hm['influence_score']}, 风格{hm['style_tags']}")
    
    # 测试席位识别
    print("\n=== 席位识别测试 ===")
    test_seats = [
        '国泰君安证券上海江苏路证券营业部',
        '中国国际金融股份有限公司北京建国门外大街证券营业部',
        '华鑫证券有限责任公司上海分公司',
        '机构专用',
        '未知席位'
    ]
    
    identified = manager.identify_seats(test_seats)
    print(f"知名游资席位: {identified['hot_money_seats']}")
    print(f"机构席位: {identified['institution_seats']}")
    print(f"量化席位: {identified['quant_seats']}")
    print(f"游资ID: {identified['hot_money_ids']}")
    print(f"最高影响力: {identified['top_influence']}")
    
    manager.close()
