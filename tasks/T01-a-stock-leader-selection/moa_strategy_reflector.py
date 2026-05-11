import json
import sys
from datetime import datetime
from typing import List, Dict, Any

# 添加技能路径
sys.path.insert(0, '/workspace/projects/workspace')
from skills.moa import MoAAnalyzer


class MoAStrategyReflector:
    """
    MoA多模型策略反思器
    
    使用多个AI模型进行策略分析，综合生成优化建议
    """
    
    def __init__(self):
        self.moa_analyzer = MoAAnalyzer()
        
        # 配置参与分析的模型
        self.proposer_models = [
            "coze/deepseek-r1-250528",  # 深度推理
            "coze/kimi-k2-5-260127",    # 上下文理解
            "coze/glm-5",               # 中文场景
            "openrouter/qwen/qwen-3.5-72b-instruct"  # 多样化视角
        ]
        
        self.reviewer_models = [
            "coze/deepseek-v3-2-251201",  # 批判分析
            "coze/doubao-seed-1-8-251228"  # 创意视角
        ]
        
        self.synthesizer_model = "coze/kimi-k2-5-260127"  # 最终整合
        
    def reflect_strategy(self, strategy_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行策略反思
        
        Args:
            strategy_data: 策略数据，包含胜率、因子IC、优化建议等
            
        Returns:
            Dict: 综合分析结果
        """
        print("\n" + "="*60)
        print("🔍 MoA多模型策略反思启动")
        print("="*60)
        
        # 1. 生成策略问题描述
        problem_description = self._generate_problem_description(strategy_data)
        print("\n📝 问题描述生成完成")
        
        # 2. 使用多个模型生成优化方案
        print("\n🤖 多模型方案生成...")
        proposals = self._generate_proposals(problem_description)
        print(f"✅ 已生成 {len(proposals)} 个方案")
        
        # 3. 模型评审方案
        print("\n👩⚖️ 方案评审中...")
        reviewed_proposals = self._review_proposals(proposals, problem_description)
        print("✅ 方案评审完成")
        
        # 4. 综合所有方案生成最终建议
        print("\n🧠 综合分析生成最终建议...")
        final_recommendation = self._synthesize_recommendations(reviewed_proposals, problem_description)
        print("✅ 最终建议生成完成")
        
        # 5. 格式化输出结果
        result = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'strategy_data': strategy_data,
            'proposals': proposals,
            'reviewed_proposals': reviewed_proposals,
            'final_recommendation': final_recommendation,
            'execution_plan': self._generate_execution_plan(final_recommendation)
        }
        
        return result
        
    def _generate_problem_description(self, strategy_data: Dict[str, Any]) -> str:
        """生成问题描述"""
        win_rate = strategy_data.get('win_rate', 0)
        invalid_factors = strategy_data.get('invalid_factors', [])
        recommendations = strategy_data.get('recommendations', [])
        
        description = f"""T01 A股龙头选股策略反思报告

当前策略胜率: {win_rate*100:.1f}%

失效因子: {', '.join(invalid_factors) if invalid_factors else '无'}

现有建议:
{chr(10).join(f'- {rec}' for rec in recommendations)}

请分析当前策略存在的问题，并提出具体的优化建议和执行方案。"""
        
        return description
        
    def _generate_proposals(self, problem_description: str) -> List[Dict[str, Any]]:
        """使用多个模型生成优化方案"""
        proposals = []
        
        for model_name in self.proposer_models:
            try:
                print(f"  🚀 {model_name} 生成方案...")
                
                prompt = f"""作为专业的量化策略分析师，请针对以下策略问题生成优化方案：

{problem_description}

方案应包含：
1. 问题根因分析
2. 具体优化措施
3. 预期效果
4. 风险提示

请用清晰的结构化方式回答。"""
                
                response = self.moa_analyzer.query_model(
                    model_name=model_name,
                    prompt=prompt,
                    timeout_seconds=60
                )
                
                proposals.append({
                    'model': model_name,
                    'content': response,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                print(f"  ❌ {model_name} 生成失败: {e}")
                continue
        
        return proposals
        
    def _review_proposals(self, proposals: List[Dict[str, Any]], problem_description: str) -> List[Dict[str, Any]]:
        """评审生成的方案"""
        reviewed = []
        
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
                
                # 随机选择一个评审模型
                import random
                reviewer_model = random.choice(self.reviewer_models)
                
                response = self.moa_analyzer.query_model(
                    model_name=reviewer_model,
                    prompt=prompt,
                    timeout_seconds=60
                )
                
                reviewed.append({
                    'proposal': proposal,
                    'reviewer': reviewer_model,
                    'review_content': response,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                print(f"  ❌ 评审 {proposal['model']} 失败: {e}")
                continue
        
        return reviewed
        
    def _synthesize_recommendations(self, reviewed_proposals: List[Dict[str, Any]], problem_description: str) -> str:
        """综合所有方案生成最终建议"""
        # 收集所有方案和评审
        all_content = []
        
        for reviewed in reviewed_proposals:
            all_content.append(f"""
【方案来源】{reviewed['proposal']['model']}
【方案内容】
{reviewed['proposal']['content']}

【评审意见】
{reviewed['review_content']}
""")
        
        synthesis_prompt = f"""作为资深量化策略专家，请综合以下所有方案和评审意见，生成最终的策略优化建议：

原始问题:
{problem_description}

所有方案和评审:
{chr(10).join(all_content)}

最终建议应包含：
1. 综合问题根因分析
2. 优先级明确的优化措施（分高、中、低优先级）
3. 详细的执行计划
4. 预期效果评估
5. 风险控制策略

请使用专业、严谨的中文撰写，结构清晰，可操作性强。"""
        
        response = self.moa_analyzer.query_model(
            model_name=self.synthesizer_model,
            prompt=synthesis_prompt,
            timeout_seconds=120
        )
        
        return response
        
    def _generate_execution_plan(self, recommendation: str) -> List[Dict[str, Any]]:
        """生成可执行的计划"""
        # 这里可以根据最终建议生成结构化的执行计划
        # 目前简化处理，后续可以添加更智能的解析
        
        return [
            {
                'step': 1,
                'action': '紧急修复失效因子',
                'description': '对IC值为0的因子进行紧急修复或替换',
                'priority': '高',
                'estimated_time': '2天',
                'responsible': '量化团队'
            },
            {
                'step': 2,
                'action': '优化因子权重',
                'description': '基于遗传算法和MoA分析结果优化因子权重',
                'priority': '高',
                'estimated_time': '3天',
                'responsible': 'AI算法团队'
            },
            {
                'step': 3,
                'action': '引入新因子',
                'description': '测试和引入资金流入时序、市场微观结构等新因子',
                'priority': '中',
                'estimated_time': '5天',
                'responsible': '数据团队'
            },
            {
                'step': 4,
                'action': '回测验证',
                'description': '对优化后的策略进行全面回测验证',
                'priority': '中',
                'estimated_time': '2天',
                'responsible': '量化团队'
            },
            {
                'step': 5,
                'action': '实盘验证',
                'description': '小仓位实盘验证优化效果',
                'priority': '低',
                'estimated_time': '7天',
                'responsible': '交易团队'
            }
        ]


# 测试代码
if __name__ == '__main__':
    # 模拟策略数据
    mock_strategy_data = {
        'win_rate': 0.333,
        'factor_ics': [
            {'name': 'limit_quality_score', 'ic': 0.0, 'valid': False},
            {'name': 'seal_ratio_score', 'ic': 0.0, 'valid': False},
            {'name': 'volume_ratio_score', 'ic': 0.0, 'valid': False}
        ],
        'invalid_factors': ['limit_quality_score', 'seal_ratio_score', 'volume_ratio_score'],
        'recommendations': [
            '⚠️ 胜率低于50%，建议暂停策略或大幅降低仓位',
            '🔧 建议替换或优化失效因子: limit_quality_score, seal_ratio_score, volume_ratio_score'
        ]
    }
    
    # 执行MoA策略反思
    reflector = MoAStrategyReflector()
    result = reflector.reflect_strategy(mock_strategy_data)
    
    print("\n" + "="*60)
    print("📊 MoA策略反思结果")
    print("="*60)
    print("\n📝 最终优化建议:")
    print(result['final_recommendation'])
    
    print("\n📋 执行计划:")
    for step in result['execution_plan']:
        print(f"  {step['step']}. [{step['priority']}] {step['action']} - {step['estimated_time']}")