# T01 - A股龙头选股策略系统

## 📋 项目简介

AI驱动的A股龙头选股策略系统，实现自动化选股、回测和决策支持。

## 🗂️ 目录结构

```
T01/
├── src/                    # 源代码
│   ├── config.py          # 配置文件
│   ├── data_provider.py   # 数据获取模块
│   └── leader_selector.py # 龙头股筛选器
├── data/                   # 数据目录
├── backtest/              # 回测结果
├── logs/                  # 日志文件
├── EVOLUTION-ROADMAP.md   # 进化路线图
├── STATUS.md              # 项目状态
├── SESSION-STATE.md       # 会话状态
├── requirements.txt       # Python依赖
└── README.md              # 项目说明
```

## 🚀 快速开始

### 1. 安装依赖

```bash
cd T01
pip install -r requirements.txt
```

### 2. 配置数据接口

编辑 `src/config.py`，填入您的Tushare Token：

```python
TUSHARE_TOKEN = "your_token_here"
```

### 3. 测试数据连接

```bash
python src/data_provider.py
```

## 📊 项目进度

| Phase | 描述 | 进度 |
|-------|------|------|
| Phase 1 | 基础架构搭建 | 20% |
| Phase 2 | 龙头筛选逻辑 | 0% |
| Phase 3 | 回测框架 | 0% |
| Phase 4 | 策略优化与风控 | 0% |
| Phase 5 | 自动化与部署 | 0% |

## 📝 待办事项

- [ ] 配置Tushare数据接口
- [ ] 实现基础数据获取模块
- [ ] 建立数据库连接
- [ ] 实现龙头股评分算法
- [ ] 搭建回测框架
- [ ] 添加风险控制模块
- [ ] 配置自动化通知

## 🔗 相关文档

- [EVOLUTION-ROADMAP.md](./EVOLUTION-ROADMAP.md) - 详细进化计划
- [STATUS.md](./STATUS.md) - 当前项目状态

---

*创建日期: 2026-03-22*
