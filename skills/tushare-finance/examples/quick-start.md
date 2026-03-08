# Tushare Finance - Quick Start Examples

## Token 配置

你的 Tushare Token 已成功配置并验证：

```
Token: 870008d508d2b0e57ecf2ccc586c23c4ecc37522f5e93890fb3d56ab
状态: ✓ 连接成功
权限: 已验证可用
```

## 常用示例

### 1. 查询股票基本信息

```bash
# 查询平安银行
openclaw tushare stock-basic --ts-code "000001.SZ"

# 查询所有股票列表
openclaw tushare stock-basic
```

### 2. 获取历史行情数据

```bash
# 获取最近30天数据
openclaw tushare daily --ts-code "000001.SZ" --start-date "20241125" --end-date "20241225"

# 获取单日数据
openclaw tushare daily --ts-code "600000.SH" --start-date "20241225" --end-date "20241225"
```

### 3. 实时行情查询

```bash
# 查询多只股票
openclaw tushare realtime --ts-code "000001.SZ,600000.SH,000002.SZ"
```

### 4. 指数数据

```bash
# 上证指数
openclaw tushare index-daily --ts-code "000001.SH" --start-date "20241201" --end-date "20241225"

# 深证成指
openclaw tushare index-daily --ts-code "399001.SZ" --start-date "20241201" --end-date "20241225"
```

### 5. 财务数据

```bash
# 查看财务指标
openclaw tushare fina-indicator --ts-code "000001.SZ" --period "20241130"

# 查看利润表
openclaw tushare income --ts-code "000001.SZ" --period "20241130"

# 查看资产负债表
openclaw tushare balancesheet --ts-code "000001.SZ" --period "20241130"
```

### 6. 基金数据

```bash
# 基金基本信息
openclaw tushare fund-basic --market "E"

# 基金净值
openclaw tushare fund-nav --ts-code "000001.OF"
```

## 实际应用场景

### 场景1：股票监控

```bash
# 监控持仓股票
openclaw tushare portfolio-monitor --file "my_portfolio.csv"

# 设置价格提醒
openclaw tushare price-alert --ts-code "000001.SZ" --target-price 12.00
```

### 场景2：市场分析

```bash
# 市场总览
openclaw tushare market-overview

# 热门股票
openclaw tushare top-stocks --date "20241225"

# 板块排行
openclaw tushare sector-ranking
```

### 场景3：投资研究

```bash
# 财务分析
openclaw tushare financial-analysis --ts-code "000001.SZ"

# 行业对比
openclaw tushare industry-compare --industry "银行"

# 估值分析
openclaw tushare valuation --ts-code "000001.SZ"
```

## 常用股票代码速查

### 银行股
- 000001.SZ - 平安银行
- 600000.SH - 浦发银行
- 600036.SH - 招商银行
- 601398.SH - 工商银行

### 科技股
- 000858.SZ - 五粮液
- 002415.SZ - 海康威视
- 002475.SZ - 立讯精密
- 300750.SZ - 宁德时代

### 指数
- 000001.SH - 上证指数
- 399001.SZ - 深证成指
- 399006.SZ - 创业板指
- 000300.SH - 沪深300

## 注意事项

1. **API 限制**: 每分钟有调用次数限制，建议合理控制频率
2. **数据延迟**: 实时数据通常有15分钟延迟
3. **权限等级**: 免费Token只能获取部分数据，高级数据需要付费权限
4. **数据范围**: 免费账户通常只能获取近1年的历史数据

## 验证命令

```bash
# 测试连接
cd /workspace/projects/workspace/skills/tushare-finance/scripts
python3 tushare_client.py

# 查看技能状态
openclaw skills info tushare-finance
```

## 下一步

现在你可以在 OpenClaw 中直接使用 Tushare 金融数据：

1. 在飞书/钉钉中询问股票信息
2. 让 OpenClaw 分析市场趋势
3. 自动获取财务数据进行分析
4. 设置股票价格提醒

享受你的金融数据查询体验！📈
