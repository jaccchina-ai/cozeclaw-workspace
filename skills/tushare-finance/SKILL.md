---
name: tushare-finance
version: 1.0.0
description: "Tushare 金融数据接口集成 - 获取中国股市、基金、期货等实时和历史金融数据"
author: StanleyChanH
---

# Tushare Finance 📈

**By StanleyChanH**

专业的中国金融市场数据接口集成技能，支持股票、基金、期货、指数等全方位金融数据获取。

## Overview

Tushare 是中国最大的金融数据接口社区，提供：
- **A股市场数据** - 实时行情、历史K线、财务指标
- **基金数据** - 净值、持仓、业绩
- **期货数据** - 行情、持仓量、成交量
- **指数数据** - 上证指数、深证指数、行业指数
- **宏观经济** - GDP、CPI、货币供应等
- **公告数据** - 公司公告、财报信息

## Prerequisites

### Token Configuration

你提供的 Tushare Token 已配置：
```
870008d508d2b0e57ecf2ccc586c23c4ecc37522f5e93890fb3d56ab
```

### API 权限

根据你的 Token 权限，可访问的数据级别可能不同：
- **免费权限**: 基础行情数据
- **积分权限**: 更多历史数据、财务数据
- **高级权限**: 实时数据、高级指标

## Configuration

Token 已自动配置到:
```
/workspace/projects/.tushare-token
```

## Usage

### 股票数据

```bash
# 获取股票基本信息
openclaw tushare stock-basic --ts-code "000001.SZ"

# 获取日线行情
openclaw tushare daily --ts-code "000001.SZ" --start-date "20240101" --end-date "20241231"

# 获取实时行情
openclaw tushare realtime --ts-code "000001.SZ,600000.SH"

# 获取分钟线
openclaw tushare stock-min --ts-code "000001.SZ" --freq "1min"

# 获取周线/月线
openclaw tushare weekly --ts-code "000001.SZ"
openclaw tushare monthly --ts-code "000001.SZ"
```

### 指数数据

```bash
# 获取指数基本信息
openclaw tushare index-basic --market "SSE"  # 上海/深圳

# 获取指数日线
openclaw tushare index-daily --ts-code "000001.SH"

# 获取指数成分股
openclaw tushare index-weight --ts-code "000001.SH"
```

### 基金数据

```bash
# 获取基金基本信息
openclaw tushare fund-basic --market "E"

# 获取基金净值
openclaw tushare fund-nav --ts-code "000001.OF"

# 获取基金持仓
openclaw tushare fund-portfolio --ts-code "000001.OF"
```

### 期货数据

```bash
# 获取期货日线
openclaw tushare fut-daily --ts-code "IF2401.CFX"

# 获取期货持仓量
openclaw tushare fut-holding --ts-code "IF2401.CFX"
```

### 财务数据

```bash
# 获取利润表
openclaw tushare income --ts-code "000001.SZ" --period "20231231"

# 获取资产负债表
openclaw tushare balancesheet --ts-code "000001.SZ" --period "20231231"

# 获取现金流量表
openclaw tushare cashflow --ts-code "000001.SZ" --period "20231231"

# 获取财务指标
openclaw tushare fina-indicator --ts-code "000001.SZ" --period "20231231"
```

### 公告数据

```bash
# 获取公司公告
openclaw tushare ann-info --ts-code "000001.SZ" --ann-date "20240101"

# 获取财报数据
openclaw tushare report --ts-code "000001.SZ" --period "2023Q4"
```

## Advanced Features

### 数据分析

```bash
# 技术指标计算
openclaw tushare indicators --ts-code "000001.SZ" --indicators "MA,MACD,RSI"

# 股票排名
openclaw tushare ranking --date "20241231" --field "total_mv" --order "desc"

# 板块数据
openclaw tushare index-classify --level "L1" --src "SW"
```

### 批量操作

```bash
# 批量获取多只股票
openclaw tushare batch-stock --codes "000001.SZ,600000.SH,000002.SZ"

# 全市场扫描
openclaw tushare market-scan --date "20241231"
```

### 数据导出

```bash
# 导出到 CSV
openclaw tushare export --data-type "daily" --ts-code "000001.SZ" --format "csv"

# 导出到 Excel
openclaw tushare export --data-type "daily" --ts-code "000001.SZ" --format "xlsx"
```

## 常用股票代码

### 蓝筹股
- 000001.SZ - 平安银行
- 600000.SH - 浦发银行
- 600036.SH - 招商银行
- 601318.SH - 中国平安

### 科技股
- 000858.SZ - 五粮液
- 002475.SZ - 立讯精密
- 300750.SZ - 宁德时代

### 指数
- 000001.SH - 上证指数
- 399001.SZ - 深证成指
- 399006.SZ - 创业板指

## Integration with Other Skills

这个技能与以下技能配合良好：
- **visualization** - 绘制K线图、走势图
- **data-analysis** - 数据分析和建模
- **proactive-agent** - 主动监控市场变化
- **notification** - 重要行情提醒

## Best Practices

### 数据更新
- 盘后数据通常在 15:30 后更新
- 财报数据每季度更新
- 使用缓存减少API调用

### 性能优化
```bash
# 使用日期范围限制数据量
openclaw tushare daily --ts-code "000001.SZ" \
  --start-date "20240101" --end-date "20241231"

# 使用分页
openclaw tushare stock-basic --offset 0 --limit 100
```

### 错误处理
- Token 过期会返回错误
- 超出权限限制会被拒绝
- API有频率限制，注意控制调用频率

## API 限制

根据你的 Token 权限，可能存在以下限制：
- **每分钟调用次数**: 通常100-500次
- **每分钟数据量**: 通常10,000条
- **历史数据**: 免费Token通常只能获取近1年数据

## 实际应用场景

### 场景1：投资组合监控
```bash
# 获取持仓股票的最新价格
openclaw tushare portfolio --file "portfolio.csv"

# 计算组合收益
openclaw tushare portfolio-return --file "portfolio.csv"

# 风险分析
openclaw tushare portfolio-risk --file "portfolio.csv"
```

### 场景2：选股策略
```bash
# 筛选低估值股票
openclaw tushare screen-pe --max-pe 15 --min-pe 5

# 筛选高成长股票
openclaw tushare screen-growth --min-growth 20

# 技术分析选股
openclaw tushare screen-technical --condition "MA5 > MA10"
```

### 场景3：市场监控
```bash
# 市场总览
openclaw tushare market-overview

# 涨跌统计
openclaw tushare market-stat --date "20241231"

# 资金流向
openclaw tushare money-flow --date "20241231"
```

## Troubleshooting

### Token 无效
```
错误: 401 Unauthorized
解决: 检查 Token 是否正确
```

### 超出调用限制
```
错误: 429 Too Many Requests
解决: 降低调用频率，增加间隔
```

### 数据权限不足
```
错误: 403 Forbidden
解决: 升级 Token 权限或访问免费数据
```

## 数据质量说明

- **实时性**: 延迟通常为15分钟
- **准确性**: 官方数据源，经过校验
- **完整性**: 历史数据可能部分缺失
- **单位**: 价格单位为元，市值为万元

## Tushare 积分系统

- **免费积分**: 每日签到、完善信息
- **任务积分**: 邀请好友、贡献数据
- **付费积分**: 购买高级数据权限

## 相关链接

- Tushare 官网: https://tushare.pro
- API 文档: https://tushare.pro/document/2
- 积分规则: https://tushare.pro/document/1

---

**Note**: Token 已配置，可以直接使用。注意 API 调用频率限制，合理安排数据获取任务。
