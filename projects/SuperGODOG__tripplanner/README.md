# TripPlanner — 多智能体旅行规划系统

> 基于 LangGraph + ReAct 的多智能体旅行规划系统：输入出发地+目的地+天数+偏好，输出含预算/酒店/每日行程的 JSON 计划。
>
> 仓库：https://github.com/SuperGODOG/tripplanner

## 档案文件

| 文件 | 内容 |
|------|------|
| [项目画像.md](项目画像.md) | 技术栈、架构概览、核心设计决策、面试表述 |
| [面试题匹配表.md](面试题匹配表.md) | 240 题库中与本项目匹配的题目清单 |
| [项目内作答.md](项目内作答.md) | 针对匹配题目的完整作答（面试版） |

## 一句话亮点

LangGraph StateGraph 4 节点编排 + ReAct 循环 + MCP 工具封装 + 自研 MemoryManager 五因子记忆 + FastAPI SSE 流式输出。

## 面试常问方向

- 为什么用 LangGraph 而不是裸 ReAct 循环？conditional edge 解决了什么问题？
- 4 个 Agent 共享一个 AmapToolWrapper 单例，线程安全怎么保证？
- SqliteSaver checkpoint 断点续传的实现与失效场景？
- MemoryManager 五因子权重 + 双轨异常检测的设计动机？
