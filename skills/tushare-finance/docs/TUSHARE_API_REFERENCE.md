# Tushare Pro API 完整文档

本文档包含 Tushare Pro 所有数据接口的详细说明，供技能调用时参考。

**生成日期**: 2026年2月24日  
**官方文档**: https://tushare.pro/document/2

---

## 目录

1. [股票数据](#1-股票数据)
2. [ETF专题](#2-etf专题)
3. [指数专题](#3-指数专题)
4. [债券专题](#4-债券专题)
5. [外汇数据](#5-外汇数据)
6. [美股数据](#6-美股数据)
7. [行业经济](#7-行业经济)
8. [宏观经济](#8-宏观经济)
9. [大模型语料专题数据](#9-大模型语料专题数据)

---

# 1. 股票数据

## 日线行情 (daily)

### 接口描述
获取股票行情数据，数据起始2015年，部分权重股可追溯更早。

### 调用方法
```python
pro.daily(ts_code='000001.SZ', start_date='20180701', end_date='20180718')
```

### 权限要求
用户需要至少120积分才可以调取，每分钟内最多调取200次，每次6000条数据。

### 输入参数
| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts_code | str | N | 股票代码（支持多只股票同时输入，用逗号分隔） |
| trade_date | str | N | 交易日期（YYYYMMDD） |
| start_date | str | N | 开始日期 |
| end_date | str | N | 结束日期 |

### 输出参数
| 名称 | 类型 | 描述 |
| --- | --- | --- |
| ts_code | str | 股票代码 |
| trade_date | str | 交易日期 |
| open | float | 开盘价 |
| high | float | 最高价 |
| low | float | 最低价 |
| close | float | 收盘价 |
| pre_close | float | 昨收价 |
| change | float | 涨跌额 |
| pct_chg | float | 涨跌幅（%） |
| vol | float | 成交量（手） |
| amount | float | 成交额（千元） |

---

## 周线行情 (weekly)

### 接口描述
获取A股周线行情，数据从2000年开始。

### 调用方法
```python
pro.weekly(ts_code='000001.SZ', start_date='20180101', end_date='20181101')
```

### 权限要求
用户需要至少120积分才可以调取。

### 输入参数
| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts_code | str | N | TS股票代码 |
| trade_date | str | N | 交易日期（YYYYMMDD格式，下同） |
| start_date | str | N | 开始日期 |
| end_date | str | N | 结束日期 |

### 输出参数
| 名称 | 类型 | 描述 |
| --- | --- | --- |
| ts_code | str | TS代码 |
| trade_date | str | 交易日期 |
| close | float | 周收盘价 |
| open | float | 周开盘价 |
| high | float | 周最高价 |
| low | float | 周最低价 |
| pre_close | float | 上一周收盘价 |
| change | float | 周涨跌额 |
| pct_chg | float | 周涨跌幅（%） |
| vol | float | 周成交量（手） |
| amount | float | 周成交额（千元） |

---

## 月线行情 (monthly)

### 接口描述
获取A股月线行情，数据从2000年开始。

### 调用方法
```python
pro.monthly(ts_code='000001.SZ', start_date='20180101', end_date='20181101')
```

### 权限要求
用户需要至少120积分才可以调取。

### 输入参数
| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts_code | str | N | TS股票代码 |
| trade_date | str | N | 交易日期（YYYYMMDD格式） |
| start_date | str | N | 开始日期 |
| end_date | str | N | 结束日期 |

### 输出参数
同周线行情。

---

## 复权数据 (pro_bar)

### 接口描述
获取股票复权行情，支持前复权、后复权和不复权。

### 调用方法
```python
pro.pro_bar(ts_code='000001.SZ', adj='qfq', start_date='20180101', end_date='20181011')
```

### 参数说明
- adj: 复权类型 qfq-前复权 hfq-后复权 None-不复权

---

## 股票列表 (stock_basic)

### 接口描述
获取基础信息数据，包括股票代码、名称、上市日期、退市日期等。

### 调用方法
```python
pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,list_date')
```

### 输入参数
| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts_code | str | N | TS代码 |
| exchange | str | N | 交易所 SSE上交所 SZSE深交所 BSE北交所 |
| list_status | str | N | 上市状态 L上市 D退市 P暂停上市 |
| limit | int | N | 单次返回数据长度 |
| offset | int | N | 请求数据的偏移量 |

### 输出参数
| 名称 | 类型 | 描述 |
| --- | --- | --- |
| ts_code | str | TS股票代码 |
| symbol | str | 股票代码 |
| name | str | 股票名称 |
| area | str | 地域 |
| industry | str | 所属行业 |
| market | str | 市场类型（主板/创业板/科创板/CDR） |
| exchange | str | 交易所代码 |
| list_status | str | 上市状态 L上市 D退市 P暂停上市 |
| list_date | str | 上市日期 |
| delist_date | str | 退市日期 |
| is_hs | str | 是否沪深港通标的，N否 H沪股通 S深股通 |

---

## 交易日历 (trade_cal)

### 接口描述
获取各大交易所交易日历数据。

### 调用方法
```python
pro.trade_cal(exchange='SSE', start_date='20180101', end_date='20181231')
```

### 输入参数
| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| exchange | str | N | 交易所 SSE上交所 SZSE深交所 CFFEX中金所 DCE大商所 CZCE郑商所 SHFE上期所 INE上期能源 XHKG港交所 |
| start_date | str | N | 开始日期 |
| end_date | str | N | 结束日期 |
| is_open | str | N | 是否交易 0休市 1交易 |

### 输出参数
| 名称 | 类型 | 描述 |
| --- | --- | --- |
| exchange | str | 交易所代码 |
| cal_date | str | 日历日期 |
| is_open | str | 是否交易 0休市 1交易 |
| pretrade_date | str | 上一交易日（TS自然日） |

---

## 指数基本信息 (index_basic)

### 接口描述
获取指数基础信息。

### 调用方法
```python
pro.index_basic(market='SSE')
```

### 输入参数
| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts_code | str | N | 指数代码 |
| market | str | N | 市场（SSE上交所 SZSE深交所） |
| publisher | str | N | 发布商 |

### 输出参数
| 名称 | 类型 | 描述 |
| --- | --- | --- |
| ts_code | str | 指数代码 |
| name | str | 指数名称 |
| market | str | 市场 |
| publisher | str | 发布商 |
| index_type | str | 指数类型 |
| category | str | 指数类别 |
| base_date | str | 基期 |
| base_point | float | 基点 |
| list_date | str | 发布日期 |

---

## 指数日线行情 (index_daily)

### 接口描述
获取指数每日行情。

### 调用方法
```python
pro.index_daily(ts_code='399300.SZ', start_date='20180101', end_date='20181010')
```

### 输入参数
| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts_code | str | Y | 指数代码 |
| trade_date | str | N | 交易日期 |
| start_date | str | N | 开始日期 |
| end_date | str | N | 结束日期 |

### 输出参数
| 名称 | 类型 | 描述 |
| --- | --- | --- |
| ts_code | str | TS指数代码 |
| trade_date | str | 交易日 |
| close | float | 收盘点位 |
| open | float | 开盘点位 |
| high | float | 最高点位 |
| low | float | 最低点位 |
| pre_close | float | 昨日收盘点 |
| change | float | 涨跌点 |
| pct_chg | float | 涨跌幅（%） |
| vol | float | 成交量（手） |
| amount | float | 成交额（千元） |

---

## 沪深港通资金流向 (moneyflow_hsgt)

### 接口描述
获取沪股通、深股通、港股通每日资金流向数据。

### 调用方法
```python
pro.moneyflow_hsgt(start_date='20180125', end_date='20180808')
```

### 权限要求
2000积分起。

### 输入参数
| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| trade_date | str | N | 交易日期 |
| start_date | str | N | 开始日期 |
| end_date | str | N | 结束日期 |

### 输出参数
| 名称 | 类型 | 描述 |
| --- | --- | --- |
| trade_date | str | 交易日期 |
| ggt_ss | float | 港股通（上海） |
| ggt_sz | float | 港股通（深圳） |
| hgt | float | 沪股通（百万元） |
| sgt | float | 深股通（百万元） |
| north_money | float | 北向资金（百万元） |
| south_money | float | 南向资金（百万元） |

---

## 个股资金流向 (moneyflow)

### 接口描述
获取沪深A股票资金流向数据，分析大单小单成交情况。

### 权限要求
用户需要至少2000积分才可以调取。

### 调用方法
```python
pro.moneyflow(ts_code='002149.SZ', start_date='20190115', end_date='20190315')
```

### 输出参数
| 名称 | 类型 | 描述 |
| --- | --- | --- |
| ts_code | str | TS代码 |
| trade_date | str | 交易日期 |
| buy_sm_vol | int | 小单买入量（手） |
| buy_sm_amount | float | 小单买入金额（万元） |
| sell_sm_vol | int | 小单卖出量（手） |
| sell_sm_amount | float | 小单卖出金额（万元） |
| buy_md_vol | int | 中单买入量（手） |
| buy_md_amount | float | 中单买入金额（万元） |
| sell_md_vol | int | 中单卖出量（手） |
| sell_md_amount | float | 中单卖出金额（万元） |
| buy_lg_vol | int | 大单买入量（手） |
| buy_lg_amount | float | 大单买入金额（万元） |
| sell_lg_vol | int | 大单卖出量（手） |
| sell_lg_amount | float | 大单卖出金额（万元） |
| buy_elg_vol | int | 特大单买入量（手） |
| buy_elg_amount | float | 特大单买入金额（万元） |
| sell_elg_vol | int | 特大单卖出量（手） |
| sell_elg_amount | float | 特大单卖出金额（万元） |
| net_mf_vol | int | 净流入量（手） |
| net_mf_amount | float | 净流入额（万元） |

---

## 财务数据 - 利润表 (income)

### 接口描述
获取上市公司利润表数据。

### 调用方法
```python
pro.income(ts_code='600000.SH', start_date='20180101', end_date='20181231')
```

### 权限要求
用户需要至少2000积分才可以调取。

### 主要输出参数
| 名称 | 类型 | 描述 |
| --- | --- | --- |
| ts_code | str | TS代码 |
| ann_date | str | 公告日期 |
| f_ann_date | str | 实际公告日期 |
| end_date | str | 报告期 |
| revenue | float | 营业收入 |
| operate_profit | float | 营业利润 |
| total_profit | float | 利润总额 |
| income_tax | float | 所得税费用 |
| n_income | float | 净利润 |
| n_income_attr_p | float | 归属于母公司所有者的净利润 |

---

## 财务数据 - 资产负债表 (balancesheet)

### 接口描述
获取上市公司资产负债表数据。

### 调用方法
```python
pro.balancesheet(ts_code='600000.SH', start_date='20180101', end_date='20181231')
```

---

## 财务数据 - 现金流量表 (cashflow)

### 接口描述
获取上市公司现金流量表数据。

### 调用方法
```python
pro.cashflow(ts_code='600000.SH', start_date='20180101', end_date='20181231')
```

---

## 财务指标 (fina_indicator)

### 接口描述
获取上市公司财务指标数据。

### 调用方法
```python
pro.fina_indicator(ts_code='600000.SH', start_date='20180101', end_date='20181231')
```

### 主要输出参数
| 名称 | 类型 | 描述 |
| --- | --- | --- |
| ts_code | str | TS代码 |
| ann_date | str | 公告日期 |
| end_date | str | 报告期 |
| roe | float | 净资产收益率 |
| roe_waa | float | 加权平均净资产收益率 |
| roe_dt | float | 净资产收益率(扣除非经常损益) |
| grossprofit_margin | float | 销售毛利率 |
| netprofit_margin | float | 销售净利率 |
| debt_to_assets | float | 资产负债率 |

---

## 概念板块分类 (concept)

### 接口描述
获取概念板块分类数据。

### 调用方法
```python
pro.concept(src='ts')
```

### 输入参数
| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| src | str | N | 概念来源（ts: Tushare自定义，ct: 东方财富） |

---

## 概念板块成分股 (concept_detail)

### 接口描述
获取概念板块成分股数据。

### 调用方法
```python
pro.concept_detail(id='ts', src='ts')
```

---

## 前十大股东 (top10_holders)

### 接口描述
获取上市公司前十大股东数据。

### 调用方法
```python
pro.top10_holders(ts_code='600000.SH', start_date='20170101', end_date='20171231')
```

### 权限要求
需要2000积分以上才能调用。

### 输出参数
| 名称 | 类型 | 描述 |
| --- | --- | --- |
| ts_code | str | TS股票代码 |
| ann_date | str | 公告日期 |
| end_date | str | 报告期 |
| holder_name | str | 股东名称 |
| hold_amount | float | 持有数量（股） |
| hold_ratio | float | 占总股本比例(%) |
| hold_float_ratio | float | 占流通股本比例(%) |

---

## 涨跌停列表 (limit_list_d)

### 接口描述
获取A股每日涨跌停、炸板数据。

### 权限要求
5000积分每分钟可以请求200次。

### 调用方法
```python
pro.limit_list_d(trade_date='20220615', limit_type='U')
```

### 输入参数
| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| trade_date | str | N | 交易日期 |
| ts_code | str | N | 股票代码 |
| limit_type | str | N | 涨跌停类型（U涨停D跌停Z炸板） |

---

## 龙虎榜每日明细 (top_list)

### 接口描述
获取龙虎榜每日交易明细数据。

### 权限要求
用户需要至少2000积分才可以调取。

### 调用方法
```python
pro.top_list(trade_date='20180928')
```

---

## 股票技术因子 (stk_factor_pro)

### 接口描述
获取股票每日技术面因子数据，包括MA、MACD、RSI、KDJ等技术指标。

### 权限要求
5000积分每分钟可以请求30次。

### 调用方法
```python
pro.stk_factor_pro(ts_code='000001.SZ', start_date='20240101', end_date='20240131')
```

### 主要输出参数
| 名称 | 类型 | 描述 |
| --- | --- | --- |
| ts_code | str | 股票代码 |
| trade_date | str | 交易日期 |
| ma_bfq_5 | float | 5日均线 |
| ma_bfq_10 | float | 10日均线 |
| ma_bfq_20 | float | 20日均线 |
| macd_bfq | float | MACD指标 |
| kdj_bfq | float | KDJ指标 |
| rsi_bfq_6 | float | 6日RSI |
| boll_upper_bfq | float | 布林带上轨 |
| boll_mid_bfq | float | 布林带中轨 |
| boll_lower_bfq | float | 布林带下轨 |

---

# 2. ETF专题

## ETF基础信息 (etf_basic)

### 接口描述
获取国内ETF基础信息。

### 权限要求
用户积8000积分可调取。

### 调用方法
```python
pro.etf_basic(list_status='L', fields='ts_code,extname,index_code,index_name,exchange,mgr_name')
```

---

## ETF日线行情 (fund_daily)

### 接口描述
获取ETF行情每日收盘后成交数据。

### 权限要求
需要至少5000积分才可以调取。

### 调用方法
```python
pro.fund_daily(ts_code='510330.SH', start_date='20250101', end_date='20250618')
```

---

## ETF份额规模 (etf_share_size)

### 接口描述
获取沪深ETF每日份额和规模数据。

### 权限要求
8000积分。

### 调用方法
```python
pro.etf_share_size(ts_code='510330.SH', start_date='20250101', end_date='20251224')
```

---

# 3. 指数专题

## 指数周线行情 (index_weekly)

### 接口描述
获取指数周线行情。

### 调用方法
```python
pro.index_weekly(ts_code='399300.SZ', start_date='20180101', end_date='20181010')
```

---

## 指数成分和权重 (index_weight)

### 接口描述
获取各类指数成分和权重，月度数据。

### 权限要求
用户需要至少2000积分才可以调取。

### 调用方法
```python
pro.index_weight(index_code='399300.SZ', start_date='20180901', end_date='20180930')
```

---

## 申万行业分类 (index_classify)

### 接口描述
获取申万行业分类。

### 调用方法
```python
pro.index_classify(level='L1', src='SW2021')
```

---

## 申万行业日线行情 (sw_daily)

### 接口描述
获取申万行业日线行情。

### 权限要求
5000积分可调取。

### 调用方法
```python
pro.sw_daily(trade_date='20230705', fields='ts_code,name,open,close,vol,pe,pb')
```

---

# 4. 债券专题

## 可转债基本信息 (cb_basic)

### 接口描述
获取可转债基本信息。

### 权限要求
用户需要至少2000积分才可以调取。

### 调用方法
```python
pro.cb_basic(ts_code='125002.SZ')
```

---

## 可转债行情 (cb_daily)

### 接口描述
获取可转债行情。

### 调用方法
```python
pro.cb_daily(trade_date='20190719', fields='ts_code,trade_date,pre_close,open,high,low,close')
```

---

# 5. 外汇数据

## 外汇日线行情 (fx_daily)

### 接口描述
获取外汇日线行情。

### 权限要求
用户需要至少2000积分才可以调取。

### 调用方法
```python
pro.fx_daily(ts_code='USDCNH.FXCM', start_date='20190101', end_date='20190524')
```

---

# 6. 美股数据

## 美股基础信息 (us_basic)

### 接口描述
获取美股列表信息。

### 权限要求
120积分可以试用，5000积分有正式权限。

### 调用方法
```python
pro.us_basic()
```

---

## 美股日线行情 (us_daily)

### 接口描述
获取美股行情（未复权）。

### 调用方法
```python
pro.us_daily(ts_code='AAPL', start_date='20190101', end_date='20190904')
```

---

## 美股复权行情 (us_daily_adj)

### 接口描述
获取美股复权行情。

### 调用方法
```python
pro.us_daily_adj(ts_code='AAPL', start_date='20240101', end_date='20240722')
```

---

# 7. 行业经济

## 电影日度票房 (bo_daily)

### 接口描述
获取电影日度票房。

### 权限要求
用户需要至少500积分才可以调取。

### 调用方法
```python
pro.bo_daily(date='20181014')
```

---

## 电影周度票房 (bo_weekly)

### 接口描述
获取周度票房数据。

### 调用方法
```python
pro.bo_weekly(date='20181008')
```

---

# 8. 宏观经济

## 居民消费价格指数 (cn_cpi)

### 接口描述
获取CPI居民消费价格数据。

### 权限要求
用户积累600积分可以使用。

### 调用方法
```python
pro.cn_cpi(start_m='201801', end_m='201903')
```

---

## 工业生产者出厂价格指数 (cn_ppi)

### 接口描述
获取PPI工业生产者出厂价格指数数据。

### 调用方法
```python
pro.cn_ppi(start_m='201905', end_m='202005')
```

---

## GDP数据 (cn_gdp)

### 接口描述
获取国民经济之GDP数据。

### 调用方法
```python
pro.cn_gdp(start_q='2018Q1', end_q='2019Q3')
```

---

## 货币供应量 (cn_m)

### 接口描述
获取货币供应量之月度数据。

### 调用方法
```python
pro.cn_m(start_m='201901', end_m='202003')
```

---

## Shibor利率数据 (shibor)

### 接口描述
获取shibor利率。

### 调用方法
```python
pro.shibor(start_date='20180101', end_date='20181101')
```

---

## LPR贷款基础利率 (shibor_lpr)

### 接口描述
获取LPR贷款基础利率。

### 调用方法
```python
pro.shibor_lpr(start_date='20180101', end_date='20181130')
```

---

# 9. 大模型语料专题数据

## 新闻快讯 (news)

### 接口描述
获取主流新闻网站的快讯新闻数据。

### 权限要求
本接口需单独开权限。

### 调用方法
```python
pro.news(src='sina', start_date='2018-11-21 09:00:00', end_date='2018-11-22 10:10:00')
```

---

## 券商研究报告 (research_report)

### 接口描述
获取券商研究报告。

### 权限要求
本接口需单独开权限。

### 调用方法
```python
pro.research_report(trade_date='20260121')
```

---

## 上证E互动 (irm_qa_sh)

### 接口描述
获取上交所e互动董秘问答文本数据。

### 权限要求
120积分可以试用，正式权限为10000积分。

### 调用方法
```python
pro.irm_qa_sh(ann_date='20250212')
```

---

## 深证互动易 (irm_qa_sz)

### 接口描述
获取深证互动易问答文本数据。

### 调用方法
```python
pro.irm_qa_sz(ann_date='20250212')
```

---

## 上市公司全量公告 (anns_d)

### 接口描述
获取全量公告数据，提供pdf下载URL。

### 权限要求
本接口为单独权限。

### 调用方法
```python
pro.anns_d(ann_date='20230621')
```

---

## 国家政策法规库 (npr)

### 接口描述
获取国家行政机关公开披露的各类法规、条例政策。

### 调用方法
```python
pro.npr(org='国务院')
```

---

## 每日技术因子接口参数说明

### STK_FACTOR_PRO（股票技术因子）
主要字段包括：
- ma_bfq_*: 简单移动平均（不复权）
- ema_bfq_*: 指数移动平均
- macd_*: MACD指标
- kdj_*: KDJ指标
- rsi_bfq_*: RSI指标
- boll_*: 布林带指标
- wr_bfq: 威廉指标
- cci_bfq: CCI指标

### IDX_FACTOR_PRO（指数技术因子）
与股票技术因子类似的字段结构。

### CB_FACTOR_PRO（可转债技术因子）
与股票技术因子类似的字段结构。

---

## 权限说明

| 积分等级 | 可访问接口 | 调用频率 |
| --- | --- | --- |
| 120+ | 基础行情数据 | 每分钟200次 |
| 2000+ | 财务数据、资金流向 | 每分钟200次 |
| 5000+ | 高级数据、分钟数据 | 每分钟500次 |
| 8000+ | 实时数据、ETF份额 | 每分钟500次 |
| 10000+ | 大模型语料、互动易 | 每分钟500次 |

---

*本文档由自动化工具从 [Tushare Pro 官网](https://tushare.pro/document/2) 采集生成，生成日期：2026年2月24日。如有更新，请以官网最新文档为准。*
