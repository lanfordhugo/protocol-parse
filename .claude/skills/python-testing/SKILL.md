---
name: python-testing
description: Use when verifying Python module functionality with pytest after AI development, validating against issue/PRD requirements, or needing Mock/Fixture isolation with 85%+ coverage targets
---

# Python Testing (AI自验证回归测试)

## Overview

基于 pytest 的 AI 自验证测试框架，确保 AI 开发的模块功能满足需求规格。

**核心方法论：需求驱动验证** - AI 编写测试验证自己开发的代码，基于 issue/PRD 文档进行功能验证。

## When to Use

✅ **使用场景：**

- AI 完成模块开发后需要验证功能正确性
- 基于 issue/PRD 文档进行需求验证
- 需要使用 Mock/Fixture 隔离外部依赖
- 需要达到 85%+ 测试覆盖率目标
- 编写遵循 AAA 模式的 pytest 测试
- 执行测试并检查覆盖率

❌ **不适用于：**

- 非 Python 项目（使用相应的测试框架）
- 简单脚本（手动测试即可）
- 性能测试（使用性能测试工具）

## Quick Reference

| 任务 | 方法 | 参考 |
| :--- | :--- | :--- |
| 编写测试 | AAA 模式、参数化测试 | [PATTERNS.md](references/PATTERNS.md) |
| 运行测试 | pytest 命令组合 | [EXECUTION.md](references/EXECUTION.md) |
| Mock 依赖 | unittest.mock、pytest fixture | [PATTERNS.md](references/PATTERNS.md) |
| 诊断问题 | 需求理解→基础设施→技术实现 | [DIAGNOSTICS.md](references/DIAGNOSTICS.md) |
| 文件组织 | 命名规则、目录结构 | [TEST_STRUCTURE.md](references/TEST_STRUCTURE.md) |

## Core Constraints

**严禁行为：**

- 创建简单能通过但验证不充分的测试
- 跳过需求分析直接创建简单测试
- 为了快速通过而创建空测试或无意义断言
- 寻求绕过问题的简单方案而非分析根本原因

**强制要求：**

- 必须先深入分析 issue/PRD 文档
- 必须确保测试真正验证业务价值
- 必须达到 85%+ 测试覆盖率（核心业务 >90%）
- 必须遵循 pytest 最佳实践和 Python 编码规范

## AI Execution Strategy

**自动验证循环：**

```text
需求分析 → 深度调研 → 编写测试 → 执行测试 → 根因分析 → 修复
```

**连续 3 次失败处理：**

1. 重新深入分析 issue/PRD 需求规格
2. 全面分析项目结构、依赖、接口、类型提示
3. 分析模块设计实现，确定问题根因
4. 运用第一性原理分析
5. 重新审视验证策略和测试设计
6. 提出新策略后重新尝试

## Coverage Targets

| 代码类型 | 目标覆盖率 |
| :--- | :--- |
| 核心业务逻辑 | > 90% |
| 工具/辅助函数 | > 80% |
| 分支覆盖率 | > 80% |
| **整体覆盖率** | **> 85%** |

## Detailed References

**测试模式和最佳实践：**

- **[PATTERNS.md](references/PATTERNS.md)** - AAA 模式、测试策略、Mock/Fixture 使用、参数化测试

**诊断流程：**

- **[DIAGNOSTICS.md](references/DIAGNOSTICS.md)** - 需求理解诊断、基础设施诊断、技术实现诊断

**测试文件组织：**

- **[TEST_STRUCTURE.md](references/TEST_STRUCTURE.md)** - 文件命名、目录结构、pytest 配置、conftest.py 使用

**执行命令：**

- **[EXECUTION.md](references/EXECUTION.md)** - 测试执行命令、覆盖率检查、标记过滤、并行执行

## Common Mistakes

| 错误 | 后果 | 修正 |
| :--- | :--- | :--- |
| 测试只验证代码能运行 | 无法发现业务逻辑错误 | 验证业务价值，而非代码路径 |
| 跳过需求分析 | 测试覆盖不足 | 必须先分析 issue/PRD |
| 忽略覆盖率 | 遗留隐藏 bug | 确保 85%+ 覆盖率 |
| 过度使用 Mock | 测试变成 Mock 配置 | 只隔离外部依赖 |
| 测试私有方法 | 耦合实现细节 | 测试公共 API |

## Red Flags - STOP and Start Over

- "这个测试太简单，肯定能通过"
- "我已经手动测试过了"
- "先写代码，回头再补测试"
- "测试通过就行，不用管覆盖率"
- "需求很明确，不用分析了"

**所有这些都意味着：停止当前工作，重新按照正确的流程开始。**

## Testing Commands

**快速验证：**
```bash
pytest -x -v tests/unit/                    # 第一个失败后停止
pytest --cov=src --cov-report=html          # 生成覆盖率报告
pytest -m "not slow" -n auto                # 并行运行（跳过慢速测试）
```

**完整验证：**
```bash
pytest --cov=src --cov-report=html --cov-report=term-missing --cov-fail-under=85 -v
```

详见 [EXECUTION.md](references/EXECUTION.md) 获取完整命令参考。
