---
name: moa
version: 1.0.0
description: "Mixture of Agents - Use multiple AI models collaboratively to improve response quality. Leverages diverse model strengths through a layered aggregation approach."
author: jscianna
---

# Mixture of Agents (MOA) 🧩

**By jscianna**

A Mixture of Agents architecture that leverages multiple AI models to improve response quality through collaborative reasoning.

## Overview

MOA uses a layered approach where multiple models work together:
- **Layer 1**: Proposer models generate diverse initial responses
- **Layer 2-3**: Reviewer models critique and refine responses
- **Layer 4**: Aggregator synthesizes the best output

## When to Use

Use MOA when:
- Complex reasoning tasks require multiple perspectives
- You want higher quality outputs through consensus
- Critical decisions benefit from model diversity
- Tasks involving ambiguity or multiple valid approaches

## How It Works

### Architecture

```
User Query
    ↓
Layer 1: Proposers (3-4 models)
    ↓  (Generate diverse responses)
Layer 2: Reviewers (2-3 models)
    ↓  (Critique and improve)
Layer 3: Synthesizer (1-2 models)
    ↓  (Combine best elements)
Final Response
```

### Available Models

Use models from your configured providers:
- **coze/kimi-k2-5-260127** - Strong reasoning
- **coze/deepseek-r1-250528** - Logical analysis
- **coze/deepseek-v3-2-251201** - General purpose
- **coze/glm-4-7-251222** - Chinese language
- **coze/doubao-seed-1-8-251228** - Creative tasks

### Usage Pattern

For complex queries, the agent will:
1. Route query to 3-4 different models (Layer 1)
2. Collect and compare responses
3. Feed responses to reviewer models (Layer 2)
4. Synthesize final output (Layer 3)

## Configuration

### Model Selection

Configure which models to use in each layer:

**Proposers (Layer 1)**:
- `coze/deepseek-r1-250528` - Deep reasoning
- `coze/kimi-k2-5-260127` - Contextual understanding
- `coze/glm-4-7-251222` - Alternative perspective

**Reviewers (Layer 2)**:
- `coze/deepseek-v3-2-251201` - Critical analysis
- `coze/kimi-k2-5-260127` - Quality assessment

**Synthesizer (Layer 3)**:
- `coze/kimi-k2-5-260127` - Final aggregation

### Parameters

Adjust based on task complexity:
- **Simple queries**: Skip MOA, use single model
- **Medium complexity**: 2 proposers, 1 reviewer, 1 synthesizer
- **High complexity**: 4 proposers, 2 reviewers, 1 synthesizer

## Best Practices

### When to Enable MOA

✅ Use MOA for:
- Complex problem solving
- Multi-step reasoning
- Ambiguous requirements
- High-stakes decisions
- Creative synthesis tasks

❌ Skip MOA for:
- Simple factual queries
- Routine tasks
- Time-sensitive requests (MOA takes longer)
- Resource-constrained environments

### Quality Indicators

MOA improves:
- **Accuracy**: Multiple perspectives reduce errors
- **Depth**: Layered analysis uncovers nuances
- **Robustness**: Consensus filtering improves reliability
- **Completeness**: Different models catch different aspects

### Performance Trade-offs

**Pros**:
- Higher quality outputs
- Reduced hallucinations
- Better handling of edge cases

**Cons**:
- Increased latency (3-5x)
- Higher token usage
- More complex coordination

## Integration with Other Skills

MOA works well with:
- **proactive-agent**: Enhanced decision-making
- **self-improvement**: Better learning from diverse outputs
- **code review**: Multi-model code analysis

## Example Workflow

**Query**: "How should I refactor this complex codebase?"

1. **Layer 1 - Proposers**:
   - Model A: Suggests modular design
   - Model B: Proposes incremental approach
   - Model C: Recommends rewrite with tests

2. **Layer 2 - Reviewers**:
   - Model D: Analyzes each proposal for risks
   - Model E: Evaluates effort and timeline

3. **Layer 3 - Synthesizer**:
   - Model F: Combines best elements:
     - Start with Model B's incremental approach
     - Apply Model A's modular design patterns
     - Follow Model C's test-first methodology

## Troubleshooting

**Issue**: Responses take too long
- **Solution**: Reduce number of models in Layer 1

**Issue**: Conflicting responses
- **Solution**: Add more reviewers to build consensus

**Issue**: No quality improvement
- **Solution**: Check if task benefits from diversity (some tasks are straightforward)

## Metrics to Track

Monitor:
- Response time vs. single model
- Quality improvement (user feedback)
- Token usage efficiency
- Consensus rate (how often models agree)

---

**Note**: This skill automatically activates for complex queries. For simple tasks, single-model responses are used for efficiency.
