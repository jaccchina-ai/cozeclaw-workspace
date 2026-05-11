# Unifuncs 集成优化方案
## 1. 联动机制优化
### 1.1 实时数据同步机制
- 新增 `unifuncs_sync.py` 模块，负责Unifuncs预热结果与选股任务的实时同步
- 修改 `cron_runner.py`，在T日选股任务前强制等待Unifuncs预热完成
- 实现超时重试机制，最多等待30分钟，每5分钟检查一次结果

### 1.2 数据交互协议
```python
# unifuncs_sync.py
class UnifuncsSync:
    def wait_for_completion(self, timeout=1800):
        """等待Unifuncs预热任务完成"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = self.get_unifuncs_status()
            if status == "completed":
                return True
            elif status == "failed":
                raise Exception("Unifuncs预热任务失败")
            time.sleep(300)  # 每5分钟检查一次
        return False
    
    def sync_results(self, date):
        """同步Unifuncs推荐结果到本地数据库"""
        # 从本地文件读取Unifuncs结果
        result = load_result(date)
        if result and result['status'] == 'completed':
            # 保存到SQLite数据库
            self.save_to_database(result['recommendations'], date)
            return True
        return False
```

## 2. 匹配度增强优化
### 2.1 多维度匹配算法
- 基于板块、市值、流通盘、行业等维度增强匹配
- 新增 `stock_matcher.py` 模块，实现智能匹配逻辑

```python
# stock_matcher.py
class StockMatcher:
    def match(self, stock, recommendations):
        """找到最匹配的推荐股票"""
        best_match = None
        max_score = 0
        
        for rec in recommendations:
            score = 0
            # 代码完全匹配
            if self._code_match(stock['ts_code'], rec['code']):
                score += 100
                best_match = rec
                break
            # 名称匹配
            if self._name_match(stock['stock_name'], rec['name']):
                score += 50
            # 板块匹配
            if self._sector_match(stock['sector'], rec['sector']):
                score += 30
            # 市值匹配（10%误差范围内）
            if self._market_cap_match(stock['float_mv'], rec['float_mv']):
                score += 20
                
            if score > max_score:
                max_score = score
                best_match = rec
                
        return best_match if max_score >= 30 else None
```

### 2.2 动态评分调整
- 根据Unifuncs推荐股票与选股结果的匹配度动态调整评分
- 匹配度越高，加分权重越大

```python
# 在_selection_engine.py中修改_score_all_stocks方法
for stock in scored_stocks:
    matched_rec = self.stock_matcher.match(stock, unifuncs_recommendations)
    if matched_rec:
        match_score = self._calculate_match_score(stock, matched_rec)
        stock['unifuncs_recommended'] = True
        stock['total_score'] += 5 + (match_score * 5)  # 5-10分动态调整
        stock['unifuncs_match_score'] = match_score
```

## 3. 异常监控与告警
### 3.1 状态监控
- 新增 `unifuncs_monitor.py` 模块，实现实时监控
- 监控指标包括：任务状态、API调用次数、匹配率、超时情况

### 3.2 告警机制
- 实现飞书告警推送
- 告警触发条件：任务超时、调用失败、匹配率低于50%

```python
# unifuncs_monitor.py
class UnifuncsMonitor:
    def check_health(self):
        """检查Unifuncs集成健康状态"""
        status = self.get_status()
        if status['task_status'] == 'failed':
            self.send_alert("Unifuncs预热任务失败", status)
            return False
        if status['match_rate'] < 0.5:
            self.send_alert("Unifuncs推荐匹配率过低", status)
            return False
        return True
        
    def send_alert(self, title, details):
        """发送飞书告警"""
        from messenger import get_messenger
        messenger = get_messenger()
        messenger.send_text(f"⚠️ {title}\n详情: {details}")
```

## 4. 用户体验优化
### 4.1 推荐结果展示增强
- 在选股报告中突出显示Unifuncs推荐标记
- 显示匹配度评分和推荐理由

```python
# 在messenger.py中修改_format_t_day_message方法
for stock in stocks:
    if stock.get('unifuncs_recommended'):
        match_score = stock.get('unifuncs_match_score', 0)
        match_text = f" 🤖【AI推荐: {match_score*100:.0f}%匹配】"
        # 在股票名称后添加推荐标记
        stock_card['content'] += match_text
        # 在详情中显示推荐理由
        matched_rec = stock.get('unifuncs_recommendation')
        if matched_rec:
            stock_card['content'] += f"\n📰 推荐理由: {matched_rec.get('reason', '')}"
```

### 4.2 统计报告优化
- 新增Unifuncs推荐统计板块
- 显示推荐股票数量、匹配率、平均匹配度

```python
# 在t_day_selection.py中添加统计
recommended_count = sum(1 for s in top_stocks if s.get('unifuncs_recommended'))
match_rate = recommended_count / len(unifuncs_recommendations) if unifuncs_recommendations else 0

sentiment['unifuncs_stats'] = {
    'recommended_count': len(unifuncs_recommendations),
    'matched_count': recommended_count,
    'match_rate': match_rate
}
```

## 5. 系统集成方案
### 5.1 代码结构调整
```
tasks/T01-a-stock-leader-selection/
├── unifuncs_sync.py      # 数据同步模块
├── stock_matcher.py      # 股票匹配模块
├── unifuncs_monitor.py   # 监控告警模块
├── selection_engine.py   # 修改原选股引擎
├── messenger.py          # 修改原消息模块
└── cron_runner.py        # 修改原Cron调度
```

### 5.2 配置文件修改
```yaml
# config.yaml
unifuncs:
  enabled: true
  timeout: 1800  # 30分钟超时
  retry_count: 3
  match_threshold: 0.3  # 30%匹配度阈值
  alert_enabled: true
  alert_channel: "feishu"
```

## 6. 实施计划
### 6.1 第一阶段（1-2天）
- 完成Unifuncs同步机制和匹配算法开发
- 修改选股引擎和消息推送模块

### 6.2 第二阶段（3-4天）
- 完成监控告警模块开发
- 实现飞书告警推送

### 6.3 第三阶段（5-6天）
- 完成用户体验优化
- 进行全面测试和调试

### 6.4 第四阶段（7天）
- 上线部署
- 性能监控和优化

## 7. 预期效果
- 推荐股票匹配率提升至80%以上
- 数据同步延迟减少至15分钟以内
- 集成问题发现时间从24小时缩短至实时
- 用户对AI推荐的感知度提升50%