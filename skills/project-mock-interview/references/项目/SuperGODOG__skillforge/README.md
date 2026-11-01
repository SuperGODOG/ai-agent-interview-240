# SkillForge — Agent Skill 自进化元 Agent 系统

> "生产 Skill 的元 Agent 工厂"：让 Skill 本身可评测、可版本管理、可自动改进的闭环系统。
> 4 周独立完成，4907 行 Python（1600 核心 + 3300 tests/scripts），pytest 74/74。
>
> 仓库：https://github.com/SuperGODOG/skillforge

## 档案文件

| 文件 | 内容 |
|------|------|
| [项目画像.md](项目画像.md) | 技术栈、架构概览、核心设计决策、面试表述 |
| [面试题匹配表.md](面试题匹配表.md) | 240 题库中与本项目匹配的题目清单 |
| [项目内作答.md](项目内作答.md) | 针对匹配题目的完整作答（面试版） |

## 一句话亮点

SkillRegistry 渐进式披露（use_skill 归因）→ IntentRouter 三层级联路由（R@1 62%→98%）→ SkillEvaluator 八维评估 + 棘轮 → SkillEvolver 元 Agent 六步闭环 → ReleaseStateMachine SQLite 发布状态机。

## 面试常问方向（钩子清单）

- 渐进式披露 + use_skill 归因：为什么不让框架自动注入 Skill？token 成本怎么算？
- Judge 配对比较 vs 绝对打分：怎么防 LLM-as-a-Judge 分数漂移？
- 三层路由"规则不独占 + Not For 检索卡片"：为什么早期规则独占会让 17/18 硬负例误命中？
- 元 Agent 分级发布 L1/L2/L3：AI 改 AI 的信任边界？
- SQLite 唯一发布事实源 + 原子切换：三处存储一致性怎么保证？
