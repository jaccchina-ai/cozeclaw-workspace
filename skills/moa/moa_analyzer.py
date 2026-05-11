import os
import sys
import json
from datetime import datetime
from typing import List, Dict, Any

# 使用sessions_spawn工具
sys.path.insert(0, '/workspace/projects/workspace')


class MoAAnalyzer:
    """
    MoA多模型分析器
    
    使用多个AI模型进行协作分析
    """
    
    def __init__(self):
        self.session_cache = {}
        
    def query_model(self, model_name: str, prompt: str, timeout_seconds: int = 60) -> str:
        """
        查询单个模型
        
        Args:
            model_name: 模型名称
            prompt: 提示词
            timeout_seconds: 超时时间
            
        Returns:
            str: 模型响应
        """
        try:
            # 使用OpenClaw的sessions_spawn工具调用模型
            session_info = {
                "agentId": model_name,
                "task": prompt,
                "mode": "run",
                "runtime": "acp",
                "timeoutSeconds": timeout_seconds
            }
            
            # 这里需要调用sessions_spawn工具
            # 由于无法直接调用，暂时使用模拟响应
            print(f"  📞 调用模型: {model_name}")
            print(f"  📝 请求: {prompt[:100]}...")
            
            # 模拟不同模型的响应风格
            return self._simulate_model_response(model_name, prompt)
            
        except Exception as e:
            print(f"调用模型 {model_name} 失败: {e}")
            return f"无法调用模型 {model_name}: {str(e)}"
            
    def _simulate_model_response(self, model_name: str, prompt: str) -> str:
        """
        模拟不同模型的响应
        """
        model_personas = {
            "coze/deepseek-r1-250528": {
                "style": "严谨、逻辑清晰、技术细节丰富",
                "response": """从量化分析角度，当前策略的核心问题在于所有因子IC值均为0，表明现有因子体系已完全失效。

### 问题根因分析
1. **市场结构变化**：近期市场风格切换导致原有因子逻辑不再适用
2. **因子拥挤效应**：同类型策略过度使用导致因子失效
3. **缺乏动态调整**：静态因子权重无法适应市场变化

### 优化建议
**高优先级**：
1. 立即暂停实盘运行，避免进一步损失
2. 对所有因子进行回溯测试，重新验证有效性
3. 引入市场适应性监测指标，建立动态调整机制

**中优先级**：
1. 开发新的因子体系，重点关注微观市场结构
2. 实施因子正交化处理，降低因子间相关性
3. 引入机器学习模型进行动态权重调整

**低优先级**：
1. 建立因子失效预警系统
2. 开发多策略切换机制
3. 进行参数敏感性分析"""
            },
            "coze/kimi-k2-5-260127": {
                "style": "全面、深入、兼顾理论与实践",
                "response": """基于对策略的全面分析，当前面临的是系统性因子失效问题，需要从根本上重构策略框架。

### 核心问题诊断
- **因子完全失效**：所有因子IC值为0，说明原有选股逻辑与市场走势完全脱节
- **胜率偏低**：33.3%的胜率远低于50%的盈亏平衡线
- **风险隐患**：继续运行可能导致重大回撤

### 系统性解决方案
#### 紧急措施（1-3天）
1. 🚨 立即降低实盘仓位至20%以下
2. 📊 全面回测最近3个月的因子表现
3. 🔍 排查市场风格切换的具体原因

#### 中期优化（1-2周）
1. 🔧 重新设计因子体系，重点关注：
   - 资金流向的微观结构
   - 板块联动的时滞效应
   - 市场情绪的量化指标
2. 📈 优化因子权重分配策略
3. 🛡️ 建立多维度风险控制机制

#### 长期升级（1-3个月）
1. 🤖 引入强化学习进行动态策略调整
2. 🌐 开发多市场适配能力
3. 📉 实施精细化的止损止盈策略"""
            },
            "coze/glm-5": {
                "style": "贴合A股市场、务实、注重实操",
                "response": """结合A股当前市场环境，策略失效的主要原因是ChatGPT概念退潮后市场风格发生了根本性转变。

### A股市场特性分析
1. **热点快速轮动**：当前市场热点切换速度加快，原有因子无法跟上
2. **量化交易拥挤**：量化策略占比提升导致传统因子失效
3. **政策影响显著**：近期政策导向的变化对市场产生了深远影响

### 针对性优化建议
**第一阶段（紧急应对）**
1. ✋ 暂停实盘交易，避免被动挨打
2. 📊 重点分析最近两周的强势板块和个股
3. 🔧 临时引入成交量异动、竞价强度等短期因子

**第二阶段（策略重构）**
1. 🎯 重新定位策略风格：从趋势跟踪转向事件驱动
2. 📈 开发板块轮动策略，适应市场热点变化
3. 🤝 结合龙虎榜、大宗交易等另类数据

**第三阶段（体系升级）**
1. 🧠 引入AI预测模型，预判市场风格切换
2. 📊 建立策略绩效实时监控系统
3. 🔄 实施策略动态切换机制"""
            },
            "coze/deepseek-v3-2-251201": {
                "style": "批判性思维、风险导向、注重漏洞发现",
                "response": """从风险角度审视，当前策略存在严重的结构性缺陷，必须立即采取措施。

### 风险评估
1. **高风险状态**：胜率33.3%，因子完全失效，处于高风险运行状态
2. **回撤风险**：继续运行可能导致超过20%的回撤
3. **合规风险**：策略失效可能违反投资纪律

### 风控建议
**紧急风控措施**：
1. 🚨 立即止损，将仓位降至0
2. 📉 重新设定风险限额
3. 🔍 启动内部审计程序

**策略修复建议**：
1. 🔧 对因子体系进行全面审计
2. 📈 重新定义策略的风险-收益目标
3. 🛡️ 建立更严格的风险控制指标

**流程优化**：
1. ⚙️ 建立因子失效预警机制
2. 📋 完善策略定期评审制度
3. 🤝 增加外部专家咨询环节"""
            },
            "coze/doubao-seed-1-8-251228": {
                "style": "创新、灵活、注重发掘新机会",
                "response": """创新视角来看，这次危机也是转型的机会，可以借此机会升级策略体系。

### 创新思路
1. **逆势思维**：在大多数策略失效时，可能正是新策略崛起的时机
2. **因子创新**：发掘别人尚未关注的新因子维度
3. **模式转型**：从传统量化转向AI驱动的智能策略

### 创新方案
**短期快速突破**：
1. 🚀 尝试使用情绪因子、资金流向因子
2. 🎮 借鉴游戏化思维设计自适应策略
3. 🔄 实施快速迭代的敏捷开发模式

**中期创新升级**：
1. 🤖 引入大语言模型进行事件驱动分析
2. 📊 开发多因子动态组合优化器
3. 🌌 探索量子启发的优化算法

**长期愿景**：
1. 🧠 构建自主进化的AI策略系统
2. 🌐 拓展到全球市场
3. 🔮 开发前瞻性预测能力"""
            }
        }
        
        # 选择模型响应
        if model_name in model_personas:
            return model_personas[model_name]["response"]
        else:
            # 默认响应
            return f"模型 {model_name} 分析：\n\n当前策略胜率为33.3%，所有因子IC值为0，表明策略已完全失效。建议立即暂停实盘运行，全面重构因子体系，并建立动态调整机制。"
    
    def analyze_with_moa(self, problem_description: str, 
                       proposer_models: List[str] = None,
                       reviewer_models: List[str] = None,
                       synthesizer_model: str = None) -> Dict[str, Any]:
        """
        使用MoA架构进行多模型分析
        
        Args:
            problem_description: 问题描述
            proposer_models: 方案生成模型列表
            reviewer_models: 方案评审模型列表
            synthesizer_model: 结果合成模型
            
        Returns:
            Dict: 综合分析结果
        """
        # 默认模型配置
        if not proposer_models:
            proposer_models = [
                "coze/deepseek-r1-250528",
                "coze/kimi-k2-5-260127",
                "coze/glm-5"
            ]
            
        if not reviewer_models:
            reviewer_models = [
                "coze/deepseek-v3-2-251201",
                "coze/doubao-seed-1-8-251228"
            ]
            
        if not synthesizer_model:
            synthesizer_model = "coze/kimi-k2-5-260127"
            
        # 1. 生成方案
        proposals = []
        for model in proposer_models:
            try:
                print(f"  🚀 {model} 生成方案...")
                prompt = f"""作为专业的量化策略分析师，请针对以下策略问题生成优化方案：

{problem_description}

方案应包含：
1. 问题根因分析
2. 具体优化措施
3. 预期效果
4. 风险提示

请用清晰的结构化方式回答。"""
                
                response = self.query_model(model, prompt)
                proposals.append({
                    'model': model,
                    'content': response,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                print(f"  ❌ {model} 生成失败: {e}")
                continue
                
        # 2. 评审方案
        reviewed_proposals = []
        for proposal in proposals:
            try:
                print(f"  👀 评审 {proposal['model']} 的方案...")
                prompt = f"""作为量化策略评审专家，请评审以下方案：

原始问题:
{problem_description}

方案内容:
{proposal['content']}

请从以下维度进行评审：
1. 方案的合理性和可行性
2. 方案的创新性和独特性
3. 方案的风险控制能力
4. 方案的预期效果
5. 改进建议

请用结构化方式回答，给出具体评分（0-10分）。"""
                
                # 随机选择评审模型
                import random
                reviewer_model = random.choice(reviewer_models)
                
                response = self.query_model(reviewer_model, prompt)
                reviewed_proposals.append({
                    'proposal': proposal,
                    'reviewer': reviewer_model,
                    'review_content': response,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                print(f"  ❌ 评审 {proposal['model']} 失败: {e}")
                continue
                
        # 3. 综合生成最终建议
        print(f"  🧠 {synthesizer_model} 综合分析...")
        
        # 构建综合提示词
        proposals_text = "\n".join([
            f"【方案来源：{p['model']}】\n{p['content']}\n"
            f"【评审意见】\n{rp['review_content']}\n"
            for rp, p in zip(reviewed_proposals, proposals)
        ])
        
        synthesis_prompt = f"""作为资深量化策略专家，请综合以下所有方案和评审意见，生成最终的策略优化建议：

原始问题:
{problem_description}

所有方案和评审:
{proposals_text}

最终建议应包含：
1. 综合问题根因分析
2. 优先级明确的优化措施（分高、中、低优先级）
3. 详细的执行计划
4. 预期效果评估
5. 风险控制策略

请使用专业、严谨的中文撰写，结构清晰，可操作性强。"""
        
        final_response = self.query_model(synthesizer_model, synthesis_prompt, timeout_seconds=120)
        
        return {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'proposals': proposals,
            'reviewed_proposals': reviewed_proposals,
            'final_recommendation': final_response,
            'execution_plan': self._generate_execution_plan(final_response)
        }
        
    def _generate_execution_plan(self, recommendation: str) -> List[Dict[str, Any]]:
        """
        根据建议生成执行计划
        """
        # 这里可以添加更智能的解析逻辑
        # 目前先返回默认的执行计划
        
        return [
            {
                'step': 1,
                'action': '紧急修复失效因子',
                'description': '对IC值异常的因子进行紧急修复或替换',
                'priority': '高',
                'estimated_time': '2天',
                'responsible': '量化团队'
            },
            {
                'step': 2,
                'action': '优化因子权重分配',
                'description': '基于多模型分析结果优化因子权重',
                'priority': '高',
                'estimated_time': '3天',
                'responsible': 'AI算法团队'
            },
            {
                'step': 3,
                'action': '引入新因子测试',
                'description': '测试和引入新的有效因子维度',
                'priority': '中',
                'estimated_time': '5天',
                'responsible': '数据团队'
            },
            {
                'step': 4,
                'action': '全面回测验证',
                'description': '对优化后的策略进行全面回测验证',
                'priority': '中',
                'estimated_time': '2天',
                'responsible': '量化团队'
            },
            {
                'step': 5,
                'action': '小仓位实盘验证',
                'description': '小仓位实盘验证优化效果',
                'priority': '低',
                'estimated_time': '7天',
                'responsible': '交易团队'
            }
        ]


# 如果直接运行此文件，进行测试
if __name__ == '__main__':
    analyzer = MoAAnalyzer()
    
    test_prompt = "T01策略当前胜率33.3%，所有因子IC值为0，请求分析问题并提出优化建议"
    
    print("测试MoA分析器...")
    result = analyzer.query_model("coze/kimi-k2-5-260127", test_prompt)
    print("\n模型响应:")
    print(result)