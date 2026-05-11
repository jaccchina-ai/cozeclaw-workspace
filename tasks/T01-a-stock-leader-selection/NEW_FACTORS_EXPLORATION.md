# T01 新因子探索报告

> **任务**: 探索三个潜在新因子  
> **时间**: 2026-03-15  
> **阶段**: Phase 5 - Alpha 挖掘新因子

---

## 📊 因子概览

| 因子名称 | 代码 | 类型 | 预期价值 | 数据难度 |
|---------|------|------|---------|---------|
| 资金流入时序 | `capital_flow_timeseries` | 时序动量 | ⭐⭐⭐⭐⭐ | 中 |
| 板块联动强度 | `sector_linkage` | 网络效应 | ⭐⭐⭐⭐ | 中 |
| 市场微观结构 | `microstructure` | 订单簿 | ⭐⭐⭐⭐⭐ | 高 |

---

## 因子一：资金流入时序 (Capital Flow Timeseries)

### 1.1 因子定义

分析资金流入的时间序列特征，识别"聪明钱"的入场模式。

**核心洞察**: 
- 大单流入的时序分布比总量更重要
- 早盘大单流入 vs 尾盘大单流入 预示不同走势
- 连续多日资金流入的持续性信号

### 1.2 计算维度

#### 维度A: 日内资金分布 (Intraday Distribution)
```python
# 早盘资金占比
morning_flow_ratio = (09:30-10:30资金流入) / (全天资金流入)

# 尾盘资金占比  
afternoon_flow_ratio = (14:00-15:00资金流入) / (全天资金流入)

# 资金集中度
flow_concentration = 大单成交金额 / 总成交金额
```

**评分规则建议**:
```python
score_rules = [
    (0.6, 10),   # 早盘占比>60%，主动进攻
    (0.4, 8),    # 早盘占比>40%，正常
    (0.2, 6),    # 早盘占比>20%，偏被动
    (0, 4),      # 早盘占比<20%，尾盘突袭，可能诱多
]
```

#### 维度B: 资金持续性 (Flow Persistence)
```python
# N日资金流入连续性
flow_streak = 连续资金净流入天数

# 资金加速度
flow_acceleration = (今日净流入 - 昨日净流入) / 昨日净流入

# 资金流向一致性
flow_consistency = 近5日净流入标准差 / 近5日净流入均值
```

**评分规则建议**:
```python
score_rules = [
    (3, 10),   # 连续3天以上流入
    (2, 8),
    (1, 6),
    (0, 4),
]
```

#### 维度C: 主动买卖力量 (Active Order Imbalance)
```python
# 主买/主卖比率
active_buy_ratio = 主动买入金额 / 主动卖出金额

# 大单净买入占比
large_order_imbalance = (大单买入 - 大单卖出) / 成交量

# 盘口吃货强度
eat_intensity = 买一成交量 / 卖一成交量
```

### 1.3 数据需求

| 数据项 | 来源 | 频率 | 备注 |
|--------|------|------|------|
| 分时资金流向 | Tushare moneyflow | 1分钟 | 需要Pro权限 |
| 大单明细 | Tushare moneyflow | 日线 | 已有 |
| 主动买卖数据 | Tushare daily | 日线 | 已有 |

### 1.4 实现代码框架

```python
class CapitalFlowTimeseriesFactor:
    """资金流入时序因子"""
    
    def __init__(self, ts_code, trade_date):
        self.ts_code = ts_code
        self.trade_date = trade_date
        
    def calculate_morning_ratio(self) -> float:
        """早盘资金占比 (09:30-10:30)"""
        morning_flow = get_moneyflow(
            ts_code=self.ts_code,
            start_time=f"{self.trade_date} 09:30:00",
            end_time=f"{self.trade_date} 10:30:00"
        )
        daily_flow = get_daily_moneyflow(self.ts_code, self.trade_date)
        
        if daily_flow == 0:
            return 0
        return morning_flow / daily_flow
    
    def calculate_flow_streak(self, n=5) -> int:
        """N日资金流入连续性"""
        flows = []
        for i in range(n):
            date = get_trade_date_offset(self.trade_date, -i)
            flow = get_daily_moneyflow(self.ts_code, date)
            flows.append(flow)
        
        # 计算连续净流入天数
        streak = 0
        for flow in flows:
            if flow > 0:
                streak += 1
            else:
                break
        return streak
    
    def calculate_active_imbalance(self) -> float:
        """主动买卖失衡度"""
        buy_vol = get_active_buy_volume(self.ts_code, self.trade_date)
        sell_vol = get_active_sell_volume(self.ts_code, self.trade_date)
        
        if sell_vol == 0:
            return 1.0
        return (buy_vol - sell_vol) / (buy_vol + sell_vol)
    
    def get_factor_values(self) -> Dict[str, float]:
        """获取所有因子值"""
        return {
            'morning_ratio': self.calculate_morning_ratio(),
            'flow_streak': self.calculate_flow_streak(),
            'active_imbalance': self.calculate_active_imbalance(),
            'flow_acceleration': self.calculate_flow_acceleration(),
        }
```

### 1.5 因子配置

```python
# factor_config.py 添加
'capital_flow_timeseries': FactorDefinition(
    code='capital_flow_timeseries',
    name='资金流入时序',
    type=FactorType.BOTH,
    weight=10.0,
    description='早盘资金占比、资金持续性、主动买卖失衡综合评分',
    score_rules=[
        (80, 10),   # 综合得分>80
        (60, 8),
        (40, 6),
        (0, 4),
    ]
)
```

---

## 因子二：板块联动强度 (Sector Linkage Strength)

### 2.1 因子定义

衡量个股与其所属板块之间的联动强度，识别"龙头效应"和"跟风股"。

**核心洞察**:
- 龙头股与板块联动强度高，且领先板块启动
- 跟风股联动强度高，但滞后板块启动
- 独立股联动强度低，可能走独立行情

### 2.2 计算维度

#### 维度A: 价格联动 (Price Correlation)
```python
# 个股与板块指数相关系数 (20日)
price_correlation = corr(stock_return, sector_return, 20)

# 相对强度
relative_strength = stock_return / sector_return

# 贝塔系数
beta = cov(stock_return, sector_return) / var(sector_return)
```

**评分规则建议**:
```python
score_rules = [
    (0.8, 10),   # 高度相关，板块龙头
    (0.6, 8),    # 中度相关，正常跟风
    (0.3, 6),    # 低相关，独立行情
    (0, 4),      # 负相关，异常
]
```

#### 维度B: 领先/滞后关系 (Lead-Lag)
```python
# 个股领先板块天数
lead_days = 计算个股涨停早于板块指数的天数

# 领先幅度
lead_magnitude = 个股涨幅 - 板块涨幅

# 同步性得分
sync_score = 1 / (1 + 个股与板块时间序列的DTW距离)
```

**评分规则建议**:
```python
score_rules = [
    (2, 10),   # 领先2天以上，真龙头
    (1, 8),    # 领先1天
    (0, 6),    # 同步
    (-999, 4), # 滞后，跟风
]
```

#### 维度C: 板块内地位 (Sector Rank)
```python
# 板块内涨幅排名
rank_in_sector = 个股在板块内涨幅排名

# 板块内成交额占比
amount_share = 个股成交额 / 板块总成交额

# 板块内涨停序位
limit_up_order = 个股是板块内第几个涨停的
```

### 2.3 数据需求

| 数据项 | 来源 | 频率 | 备注 |
|--------|------|------|------|
| 板块指数 | Tushare index_daily | 日线 | 需要行业分类 |
| 个股行业 | Tushare stock_basic | 静态 | 已有 |
| 个股日行情 | Tushare daily | 日线 | 已有 |

### 2.4 实现代码框架

```python
class SectorLinkageFactor:
    """板块联动强度因子"""
    
    def __init__(self, ts_code, trade_date, sector_code):
        self.ts_code = ts_code
        self.trade_date = trade_date
        self.sector_code = sector_code
        
    def calculate_price_correlation(self, window=20) -> float:
        """个股与板块价格相关系数"""
        stock_returns = get_stock_returns(self.ts_code, self.trade_date, window)
        sector_returns = get_sector_returns(self.sector_code, self.trade_date, window)
        
        return np.corrcoef(stock_returns, sector_returns)[0, 1]
    
    def calculate_beta(self, window=20) -> float:
        """贝塔系数"""
        stock_returns = get_stock_returns(self.ts_code, self.trade_date, window)
        sector_returns = get_sector_returns(self.sector_code, self.trade_date, window)
        
        covariance = np.cov(stock_returns, sector_returns)[0, 1]
        variance = np.var(sector_returns)
        
        if variance == 0:
            return 1.0
        return covariance / variance
    
    def calculate_lead_lag(self, n_days=5) -> int:
        """计算个股领先板块的天数"""
        lead_days = 0
        
        for i in range(n_days):
            date = get_trade_date_offset(self.trade_date, -i)
            
            # 检查个股是否涨停
            stock_limit = is_limit_up(self.ts_code, date)
            
            # 检查板块指数是否大涨(>3%)
            sector_chg = get_sector_change(self.sector_code, date)
            sector_surge = sector_chg > 0.03
            
            if stock_limit and not sector_surge:
                lead_days += 1
            elif sector_surge:
                break
                
        return lead_days
    
    def calculate_sector_rank(self) -> int:
        """板块内涨幅排名"""
        sector_stocks = get_sector_stocks(self.sector_code)
        
        performances = []
        for stock in sector_stocks:
            perf = get_stock_performance(stock, self.trade_date, 5)
            performances.append((stock, perf))
        
        # 排序获取排名
        performances.sort(key=lambda x: x[1], reverse=True)
        
        for rank, (stock, _) in enumerate(performances, 1):
            if stock == self.ts_code:
                return rank
        return len(performances)
    
    def get_factor_values(self) -> Dict[str, float]:
        """获取所有因子值"""
        return {
            'price_correlation': self.calculate_price_correlation(),
            'beta': self.calculate_beta(),
            'lead_days': self.calculate_lead_lag(),
            'sector_rank': self.calculate_sector_rank(),
        }
```

### 2.5 因子配置

```python
# factor_config.py 添加
'sector_linkage': FactorDefinition(
    code='sector_linkage',
    name='板块联动强度',
    type=FactorType.BOTH,
    weight=8.0,
    description='个股与板块价格相关性、领先滞后关系、板块内地位综合评分',
    score_rules=[
        (80, 10),
        (60, 8),
        (40, 6),
        (0, 4),
    ]
)
```

---

## 因子三：市场微观结构 (Market Microstructure)

### 3.1 因子定义

基于订单簿和交易明细的微观结构特征，识别"聪明钱"和"噪声交易者"。

**核心洞察**:
- 大单占比高 + 波动率适中 = 机构进场信号
- 小单密集成交 + 价格上涨 = 散户追涨，风险高
- 盘口挂单深度变化 = 供需力量变化

### 3.2 计算维度

#### 维度A: 订单簿不平衡 (Order Book Imbalance)
```python
# 盘口失衡度 (Level 1)
ob_imbalance = (买一量 - 卖一量) / (买一量 + 卖一量)

# 深度失衡度 (Level 5)
depth_imbalance = sum(买1-5量) / sum(卖1-5量)

# 价差变化
spread_change = 当前价差 / 平均价差 - 1
```

**评分规则建议**:
```python
score_rules = [
    (0.5, 10),   # 买盘明显占优
    (0.2, 8),
    (-0.2, 6),
    (-999, 4),   # 卖盘占优
]
```

#### 维度B: 成交量分布 (Volume Profile)
```python
# 大单占比
large_order_ratio = 大单成交量 / 总成交量

# 主动买/卖比率
active_ratio = 主动买入量 / 主动卖出量

# 成交量加权平均价格偏离
vwap_deviation = (最新价 - VWAP) / VWAP
```

**评分规则建议**:
```python
score_rules = [
    (2.0, 10),   # 主动买是卖的2倍以上
    (1.5, 8),
    (1.0, 6),
    (0, 4),      # 主动卖占优
]
```

#### 维度C: 流动性指标 (Liquidity Metrics)
```python
# Amihud 非流动性指标
amihud = abs(收益率) / (成交额 / 市值)

# 价格冲击成本
price_impact = (大单买入后价格变化) / 大单金额

# 换手率分布
turnover_skewness = 换手率分布的偏度
```

#### 维度D: 波动率特征 (Volatility Signature)
```python
# 已实现波动率
realized_vol = sqrt(sum(日内收益率^2))

# 波动率微笑偏离
skewness = 收益率分布的偏度

# 波动率聚集
vol_clustering = 自回归系数
```

### 3.3 数据需求

| 数据项 | 来源 | 频率 | 备注 |
|--------|------|------|------|
| 逐笔成交 | Tushare tick | 逐笔 | 需要Pro权限 |
| 十档行情 | 券商Level2 | 实时 | 需要接入 |
| 分时数据 | Tushare minute | 1分钟 | 需要Pro权限 |

**数据限制说明**:
- Tushare 免费版不提供逐笔数据
- 需要购买 Pro 权限或使用其他数据源
- 可以先实现基于日线的简化版本

### 3.4 实现代码框架 (简化版)

```python
class MicrostructureFactor:
    """市场微观结构因子 (简化版，基于日线数据)"""
    
    def __init__(self, ts_code, trade_date):
        self.ts_code = ts_code
        self.trade_date = trade_date
        
    def calculate_large_order_ratio(self) -> float:
        """大单成交占比 (使用龙虎榜数据估算)"""
        dragon_tiger = get_dragon_tiger_data(self.ts_code, self.trade_date)
        daily_amount = get_daily_amount(self.ts_code, self.trade_date)
        
        if daily_amount == 0:
            return 0
        
        large_order_amount = sum([item['buy_amount'] for item in dragon_tiger])
        return large_order_amount / daily_amount
    
    def calculate_amihud_illiquidity(self, window=20) -> float:
        """Amihud 非流动性指标 (低=流动性好)"""
        returns = get_stock_returns(self.ts_code, self.trade_date, window)
        amounts = get_daily_amounts(self.ts_code, self.trade_date, window)
        market_values = get_market_values(self.ts_code, self.trade_date, window)
        
        amihud_values = []
        for ret, amount, mv in zip(returns, amounts, market_values):
            if amount > 0:
                amihud_values.append(abs(ret) / (amount / mv))
        
        return np.mean(amihud_values) if amihud_values else 0
    
    def calculate_price_efficiency(self, window=20) -> float:
        """价格效率 (方差比检验)"""
        # 计算方差比
        returns = get_stock_returns(self.ts_code, self.trade_date, window)
        
        var_1day = np.var(returns)
        var_5day = np.var([sum(returns[i:i+5]) for i in range(0, len(returns)-4, 5)])
        
        if var_1day == 0:
            return 1.0
        
        variance_ratio = var_5day / (5 * var_1day)
        
        # 接近1表示价格有效，偏离1可能有动量或反转
        return 1 - abs(variance_ratio - 1)
    
    def calculate_volatility_skew(self, window=20) -> float:
        """波动率偏度 (正=上涨波动大，负=下跌波动大)"""
        returns = get_stock_returns(self.ts_code, self.trade_date, window)
        
        positive_returns = [r for r in returns if r > 0]
        negative_returns = [r for r in returns if r < 0]
        
        if not positive_returns or not negative_returns:
            return 0
        
        vol_up = np.std(positive_returns)
        vol_down = np.std(negative_returns)
        
        return (vol_up - vol_down) / (vol_up + vol_down)
    
    def get_factor_values(self) -> Dict[str, float]:
        """获取所有因子值"""
        return {
            'large_order_ratio': self.calculate_large_order_ratio(),
            'amihud_illiquidity': self.calculate_amihud_illiquidity(),
            'price_efficiency': self.calculate_price_efficiency(),
            'volatility_skew': self.calculate_volatility_skew(),
        }
```

### 3.5 完整版微观结构因子 (需要Level2数据)

```python
class MicrostructureFactorL2:
    """市场微观结构因子 (完整版，需要Level2数据)"""
    
    def __init__(self, ts_code, trade_date, tick_data):
        self.ts_code = ts_code
        self.trade_date = trade_date
        self.tick_data = tick_data  # 逐笔成交数据
        
    def calculate_order_book_imbalance(self) -> float:
        """订单簿失衡度"""
        # 需要实时十档数据
        bid_volume = sum(self.tick_data['bid_volumes'])
        ask_volume = sum(self.tick_data['ask_volumes'])
        
        if bid_volume + ask_volume == 0:
            return 0
        return (bid_volume - ask_volume) / (bid_volume + ask_volume)
    
    def calculate_trade_direction_imbalance(self) -> float:
        """成交方向失衡度 (使用Lee-Ready算法)"""
        active_buys = 0
        active_sells = 0
        
        for trade in self.tick_data['trades']:
            # Lee-Ready 分类
            if trade['price'] > trade['mid_price']:
                active_buys += trade['volume']
            elif trade['price'] < trade['mid_price']:
                active_sells += trade['volume']
            else:
                # 等于中间价，用前一笔价格判断
                pass
        
        total = active_buys + active_sells
        if total == 0:
            return 0
        return (active_buys - active_sells) / total
    
    def calculate_vp_pin(self) -> float:
        """VPIN (Volume-Synchronized Probability of Informed Trading)"""
        # 基于成交量的知情交易概率
        # 需要高频数据计算
        pass
    
    def calculate_realized_volatility(self) -> float:
        """已实现波动率"""
        returns = self.tick_data['returns']
        return np.sqrt(np.sum(np.square(returns)))
```

### 3.6 因子配置

```python
# factor_config.py 添加
'microstructure': FactorDefinition(
    code='microstructure',
    name='市场微观结构',
    type=FactorType.BOTH,
    weight=10.0,
    description='订单簿失衡、大单占比、价格效率、波动率特征综合评分',
    score_rules=[
        (80, 10),
        (60, 8),
        (40, 6),
        (0, 4),
    ]
)
```

---

## 📈 数据获取方案

### 方案A: Tushare Pro (推荐)

```python
import tushare as ts

# 需要购买Pro权限
pro = ts.pro_api('your_token')

# 资金流向 (1分钟)
df = pro.moneyflow(ts_code='000001.SZ', start_date='20260101', end_date='20260315')

# 逐笔成交 (需要更高级权限)
df = pro.tick(ts_code='000001.SZ', trade_date='20260315')
```

### 方案B: 现有数据近似

```python
# 使用已有的大单数据近似计算
# data_fetcher.py 中已实现
large_order_data = fetch_large_order_data(ts_code, trade_date)

# 使用龙虎榜数据估算机构参与度
dragon_tiger_data = fetch_dragon_tiger_data(ts_code, trade_date)
```

### 方案C: 未来扩展

```python
# 接入券商Level2数据
# 或购买第三方高频数据服务
```

---

## 🎯 实施建议

### 优先级排序

| 优先级 | 因子 | 原因 |
|--------|------|------|
| ⭐⭐⭐⭐⭐ | 板块联动强度 | 数据已有，实现简单，效果明显 |
| ⭐⭐⭐⭐ | 资金流入时序 | 需要Pro权限，但价值高 |
| ⭐⭐⭐ | 市场微观结构 | 需要高频数据，可先实现简化版 |

### 实施步骤

1. **Week 1**: 实现板块联动强度因子
   - 使用现有数据计算价格相关性
   - 实现领先滞后分析
   - 添加数据库字段并测试

2. **Week 2**: 实现资金流入时序因子
   - 申请/购买Tushare Pro权限
   - 获取分时资金流向数据
   - 实现日内分布和持续性分析

3. **Week 3**: 实现微观结构简化版
   - 基于龙虎榜和日频数据
   - 计算大单占比和价格效率
   - 评估效果后决定是否升级

4. **Week 4**: 回测验证
   - 将新因子纳入评分模型
   - 回测历史数据验证效果
   - 调整权重和评分规则

---

## 📊 预期效果

### 板块联动强度
- **预期IC值**: 0.05-0.08
- **预期提升**: 识别真龙头，减少跟风股选择
- **风险控制**: 避免板块退潮时的追高

### 资金流入时序
- **预期IC值**: 0.06-0.10
- **预期提升**: 捕捉"聪明钱"入场时机
- **风险控制**: 识别尾盘诱多陷阱

### 市场微观结构
- **预期IC值**: 0.04-0.07 (简化版) / 0.08-0.12 (完整版)
- **预期提升**: 识别机构vs散户行为模式
- **风险控制**: 避开散户情绪过热标的

---

## 📝 下一步行动

1. ✅ **本报告完成** - 三个新因子的详细设计
2. ⬜ **数据准备** - 确认Tushare Pro权限或替代数据源
3. ⬜ **代码实现** - 按优先级逐个实现三个因子
4. ⬜ **数据库迁移** - 添加新因子字段
5. ⬜ **回测验证** - 验证新因子的有效性
6. ⬜ **集成上线** - 纳入正式选股流程

---

*报告生成时间: 2026-03-15*  
*报告状态: 待实施*
