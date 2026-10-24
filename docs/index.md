<div align="center">

# 🎯 AI Agent 面试真题库 · 543 道公共题库

**大模型 Agent 岗面试准备 | 大厂真题 + 语言八股 + 当前项目范式 + 模拟面试**

[![GitHub stars](https://img.shields.io/github/stars/SuperGODOG/ai-agent-interview-240?style=flat-square&color=7c3aed)](https://github.com/SuperGODOG/ai-agent-interview-240/stargazers)
[![Questions](https://img.shields.io/badge/公共题库-543%20道-3b82f6?style=flat-square)](https://github.com/SuperGODOG/interview-mock-skill)
[![八股文](https://img.shields.io/badge/语言八股-85%20篇-10b981?style=flat-square)](./02-语言八股/README.md)
[![Projects](https://img.shields.io/badge/当前主线项目-2%20个-f59e0b?style=flat-square)](https://github.com/SuperGODOG/skillforge)
[![License](https://img.shields.io/badge/License-MIT-gray?style=flat-square)](./LICENSE)

**543 道公共面试题（涵盖 Agent、高并发后端、AI Infra、算法与全栈等 5 大核心板块、21 个专业流派）· 三层金字塔架构 · 语言八股 · 2 个主线项目 · 模拟面试拷问引擎**

</div>

---

## ✨ 项目亮点

- 🏆 **543 道公共真题**：完整题库由 [interview-mock-skill](https://github.com/SuperGODOG/interview-mock-skill) 统一维护，涵盖 Agent 应用开发 (300 题)、高并发后端 (165 题)、AI Infra 与底层算子 (29 题)、算法与综合 (47 题)、全栈工程 (2 题)；全卷通过三层金字塔架构（L1 板块 $\rightarrow$ L2 专业流派 $\rightarrow$ L3 深度梯度 1~5）重构，支持精确/模糊智能去重与双向知识图谱导引；另有独立 schema 的 [agent-review-audit](https://github.com/SuperGODOG/interview-mock-skill/tree/main/agent-review-audit) 420 张审查题卡
- 📝 **每题带答题框架**：核心考点 + 大厂四步答题框架（概念澄清 → 架构机制 → 工程权衡 → 实战经验）+ 前置/后置学习路径与别名重定向
- 📚 **85 篇语言八股**：Java 77 篇（含 66 篇体系化课件）、Python 3 篇、Go 5 篇，覆盖 JVM/并发/集合/Spring/MySQL/Redis/网络/OS/GMP/GC/GIL
- 🛠 **2 个当前主线项目**：[SkillForge](https://github.com/SuperGODOG/skillforge)（Skill 注册、级联路由、评测与受控自进化平台）与 [miaosha](https://github.com/SuperGODOG/miaosha)（限流、Redis Lua 预扣库存、RabbitMQ 异步削峰、条件扣库与订单落库）；旧版项目档案仍保留在 `projects/` 供历史对照
- 🎤 **模拟面试与拷问引擎**：完整六件套 Skill 集成（`project-mock-interview`, `agent-project-grill`, `agent-review-audit`, `grilling`, `interview-bank-pipeline`, `interview-resume-pack`），支持逐题提问、四维点评、高频错题自愈与断点恢复
- 🗂 **三层金字塔体系**：全景金字塔导航 + 1~5 级深度分级（概念定义 → 原理机制 → 设计与方案 → 落地与权衡 → 前沿与延伸），支持按梯度与流派刷题

---

## 📖 目录导航

| 模块 | 内容 | 说明 |
|------|------|------|
| [📌 01-面试八股文](./01-面试八股文/00-核心专题索引与学习路线.md) | **543 道全量真题分卷与金字塔索引** | 6 大分卷 + 1 全景索引 · 深度分级 · 答题框架 · 学习路径 |
| [📚 02-语言八股](./02-语言八股/README.md) | **Java / Python / Go 面试八股** | 85 篇 · 考点+要点+代码+追问 |
| [🏢 03-企业招聘分析](./03-企业招聘分析/README.md) | 大厂 AI Agent 岗分析 | 规划中 |
| [📖 04-开源项目学习笔记](./04-开源项目学习笔记/README.md) | 优秀开源项目剖析 | 规划中 |
| [📄 05-简历模板](./05-简历模板/README.md) | AI Agent 简历写法 | 规划中 |
| [🗣 06-STAR面试稿](./06-STAR面试稿/README.md) | 面试话术准备 | 规划中 |
| [❓ 07-面试问答集](./07-面试问答集/README.md) | 项目面试问答 | 规划中 |
| [🤖 skills/](https://github.com/SuperGODOG/ai-agent-interview-240/blob/main/skills/project-mock-interview/SKILL.md) | **模拟面试 Skill 包** | 拷问引擎 + 大厂模拟面试官 (六件套同源同步) |

---

## 🗂 八股文分卷（543 道全量真题）

| 卷 | 题数 | 覆盖范围 |
|----|------|----------|
| [00-核心专题索引与学习路线](./01-面试八股文/00-核心专题索引与学习路线.md) | **索引** | 5 大核心板块、21 个专业流派全景图谱与学习路线指南 |
| [01-Agent应用开发](./01-面试八股文/01-Agent应用开发.md) | **300** | 宏观认知、主流框架、工具调用、Prompt、记忆、架构设计、数据库、工程落地、性能评估 |
| [02-八股基础](./01-面试八股文/02-八股基础.md) | **167** | 操作系统与线程底层、计算机网络、数据库与缓存存储、消息队列、Java与并发核心、高并发秒杀业务流 |
| [03-Transformer与大模型](./01-面试八股文/03-Transformer与大模型.md) | **10** | 注意力、长上下文、KV Cache、推理优化、微调对齐 |
| [04-LeetCode算法](./01-面试八股文/04-LeetCode算法.md) | **28** | 手撕代码高频题、二叉树、动态规划、哈希表、栈与队列、字符串解码、SQL 手撕 |
| [05-反问与国企特别版](./01-面试八股文/05-反问与国企特别版.md) | **9** | 反问环节策略、技术选型权衡、国企求职特别篇、技术学习方法论 |
| [06-AI_Infra与高性能算子](./01-面试八股文/06-AI_Infra与高性能算子.md) | **29** | CUDA 算子开发、Triton、FlashAttention、算子融合与编译优化 |

## 📚 语言八股（85 篇）

| 语言 | 篇数 | 内容 |
|------|------|------|
| [Java](./02-语言八股/Java/00-学习路线图.md) | **77** | [11 篇手撕笔记](./02-语言八股/README.md)（集合/并发/JVM/Spring/MySQL/Redis/网络/OS/MQ/锁/设计模式）+ [66 篇体系化课件](./02-语言八股/Java/课件/README.md)（面试场景+追问+代码+自测） |
| [Python](./02-语言八股/Python/01-Python基础.md) | **3** | 基础（GIL/可变不可变）/ 并发与异步 / 进阶陷阱 |
| [Go](./02-语言八股/Go/01-Go基础.md) | **5** | 基础（slice/map）/ 并发（GMP）/ 内存与 GC / 进阶陷阱 / Go与Python对比 |

## 🛠 当前项目范式（2 个主线项目）

| 项目 | 技术栈 | 一句话定位 |
|------|--------|------------|
| [SkillForge](https://github.com/SuperGODOG/skillforge) | Python + SQLite + Embedding + LangGraph sidecar | Skill 注册、级联路由、评测与受控自进化平台 |
| [miaosha](https://github.com/SuperGODOG/miaosha) | Java + Spring Boot + Dubbo + RabbitMQ + Redis + MySQL | 限流、Redis Lua 预扣库存、异步削峰、条件扣库与订单落库 |

> `projects/` 下的 TripPlanner、SkillForge、JeecgBoot 是早期静态项目档案。当前项目表达与面试准备以两个源仓库的最新代码为准；Java 项目主线已切换为 `miaosha`。

## 🧭 题库口径与更新

- **公共题库**：当前由 [interview-mock-skill](https://github.com/SuperGODOG/interview-mock-skill) 统一维护，共 543 道题；六件套 Skill 共享同一份题库，全量真题通过金字塔架构与双向图谱紧密相连。
- **独立审查语料**：`agent-review-audit` 维护 420 张独立 schema 的 Agent/RAG 审查题卡，服务代码体检与架构 Gap 分析，不与公共题库合并。
- **本仓库文档**：`docs/01-面试八股文/` 由脚本从真理源编译，涵盖全量 543 道题的分卷文档与金字塔索引，保持 100% 数据指纹一致。
- **项目匹配**：题库扩充后，已有项目的 `match.json` 仍是静态候选快照；重新执行项目的 `match/finalize`，新题才会进入候选列表。

本仓库提供展示百科与文档壳；动态公共题库、六件套 Skill 及更新流程以 [interview-mock-skill](https://github.com/SuperGODOG/interview-mock-skill) 为准。

---

## 🚀 快速开始

### 1. 刷题路径（按深度梯度）

1. 从 [00-核心专题索引与学习路线](./01-面试八股文/00-核心专题索引与学习路线.md) 获取全局拓扑
2. 进入 [01-Agent应用开发](./01-面试八股文/01-Agent应用开发.md) 或 [02-八股基础](./01-面试八股文/02-八股基础.md)，按流派与深度递进刷题
3. 每道题先自己答，再对照"核心考点 + 答题框架"查漏
4. 按"学习路径"的前置/后置与别名重定向关系扩展

### 2. 项目准备路径

1. 先读 [SkillForge 当前源码](https://github.com/SuperGODOG/skillforge) 和 [miaosha 当前源码](https://github.com/SuperGODOG/miaosha)，各写出 30 秒项目介绍
2. 再用 [interview-mock-skill](https://github.com/SuperGODOG/interview-mock-skill) 按项目重新匹配公共题库
3. 需要查看早期答题材料时，再进入 `projects/` 下对应的历史静态档案

### 3. 用 AI 模拟面试（Skill 包）

推荐从 [interview-mock-skill](https://github.com/SuperGODOG/interview-mock-skill) **整包安装**到你的 AI 助手（Claude Code / Hermes / Antigravity 等）。它是“1 个主入口 + 5 个依赖”的完整 Skill 包，请不要只拆装其中一个子 Skill；本仓库 `skills/` 与之一致同步。

- 大厂 AI 模拟面试官：覆盖阿里/腾讯/字节/百度/美团等大厂，逐题提问 + 四维点评
- 项目拷问引擎：基于公共题库按项目匹配，对当前主线项目进行深度拷问

### 4. 重新生成八股文

题库数据变更后，重跑生成脚本：

```bash
python3 scripts/generate_baike.py   # 从题库真理源编译全量 543 道真题分卷与金字塔索引
python3 scripts/html2md.py          # HTML 课件转 Markdown
```

---

## 🏗 项目架构

```
ai-agent-interview-240/
├── README.md                          # 本文件
├── docs/
│   ├── 01-面试八股文/                 # 全量 543 道真题分卷与索引
│   │   ├── 00-核心专题索引与学习路线.md  # 全景金字塔索引 (5 大板块 · 21 个流派)
│   │   ├── 01-Agent应用开发.md        # 300 题 · 核心战场
│   │   ├── 02-八股基础.md             # 167 题 · 操作系统/计网/数据库/MQ/并发/秒杀
│   │   ├── 03-Transformer与大模型.md  # 10 题
│   │   ├── 04-LeetCode算法.md         # 28 题
│   │   ├── 05-反问与国企特别版.md     # 9 题
│   │   └── 06-AI_Infra与高性能算子.md # 29 题 · CUDA/Triton/算子优化
│   ├── 02-语言八股/                   # Java/Python/Go 语言面试八股
│   │   ├── Java/                      # 11 篇手撕 + 66 篇课件 + 学习路线图
│   │   ├── Python/                    # 3 篇
│   │   └── Go/                        # 5 篇
│   ├── 03-企业招聘分析/               # 规划中
│   ├── 04-开源项目学习笔记/           # 规划中
│   ├── 05-简历模板/                   # 规划中
│   ├── 06-STAR面试稿/                 # 规划中
│   └── 07-面试问答集/                 # 规划中
├── projects/                          # 早期静态项目档案（当前主线见源仓库链接）
│   ├── SuperGODOG__skillforge/        # SkillForge 静态档案
│   └── local__miaosha_fastapi/        # 秒杀系统静态档案
├── skills/                            # 同步部署的六件套 Skill 包 (共享 543 题库与工具链)
│   ├── project-mock-interview/        # 项目拷问引擎（公共题库匹配 + 四维点评）
│   ├── agent-project-grill/           # 核心公共题库真理源与拷打引擎
│   ├── agent-review-audit/            # 420 张大厂 Agent/RAG 架构审查
│   ├── grilling/                      # 深度追问与多维度压力测试
│   ├── interview-bank-pipeline/       # 题库清洗、快照比对与回归流水线
│   └── interview-resume-pack/         # 简历 Bullet 与话术提炼
└── scripts/
    ├── generate_baike.py              # 八股文编译生成脚本（金字塔重排 + 双向链接）
    ├── gen_mkdocs.py                  # MkDocs 文档目录自动生成脚本
    └── html2md.py                     # HTML 课件转 Markdown
```

---

## 📈 题目深度分级说明

| 深度 | 含义 | 刷题策略 |
|------|------|----------|
| 1/5 | 概念定义 | 快速过，能一句话说清 |
| 2/5 | 原理机制 | 理解底层原理，能画图讲 |
| 3/5 | 设计与方案 | 重点刷，面试主战场 |
| 4/5 | 落地与权衡 | 结合项目讲 trade-off |
| 5/5 | 前沿与延伸 | 加分项，了解即可 |

---

## 🔍 SEO / 关键词索引

本仓库面向以下搜索场景（供搜索引擎与爬虫索引）：

- **AI Agent 面试题**：Agent 面试真题、大模型 Agent 岗面试、Agent 架构面试、Multi-Agent 面试、RAG 面试、MCP 面试、Prompt 工程面试、Agent 记忆系统面试、工具调用面试、AI Agent 八股文、大模型应用开发面试题
- **大厂面试**：字节跳动面试、腾讯面试、阿里面试、百度面试、美团面试、LLM 面试题、AI 工程面试、后端面试真题
- **语言八股**：Java 八股文、Java 集合面试题、并发编程面试、JVM 面试题、Spring 面试、MySQL 面试、Redis 面试、计算机网络面试、操作系统面试、消息队列面试、设计模式面试、Python 面试题、Python GIL、asyncio、Go 面试题、Go 并发 GMP、Go GC、Go channel
- **项目实战**：Skill 系统与受控自进化、秒杀系统、LangGraph、ReAct Agent、多智能体、MCP、RAG、Java 后端

> 提示：题库与语言八股均为 Markdown 纯文本，无 JS 渲染依赖，搜索引擎可直接抓取正文内容。

---

## 📄 License

MIT

## 🙏 免责声明

题目来源于本人面试经历与公开渠道搜集整理，仅供个人学习使用。
