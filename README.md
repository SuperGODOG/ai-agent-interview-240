<div align="center">

# 🎯 AI Agent 面试真题库 · 318 道公共题库

**大模型 Agent 岗面试准备 | 大厂真题 + 语言八股 + 当前项目范式 + 模拟面试**

[![GitHub stars](https://img.shields.io/github/stars/SuperGODOG/ai-agent-interview-240?style=flat-square&color=7c3aed)](https://github.com/SuperGODOG/ai-agent-interview-240/stargazers)
[![Questions](https://img.shields.io/badge/公共题库-318%20道-3b82f6?style=flat-square)](https://github.com/SuperGODOG/interview-mock-skill)
[![八股文](https://img.shields.io/badge/语言八股-85%20篇-10b981?style=flat-square)](docs/02-语言八股/README.md)
[![Projects](https://img.shields.io/badge/当前主线项目-2%20个-f59e0b?style=flat-square)](https://github.com/SuperGODOG/skillforge)
[![License](https://img.shields.io/badge/License-MIT-gray?style=flat-square)](LICENSE)

**318 道公共面试题（原 240 道题持续扩展，新增部分更侧重后端）· Java/Python/Go 语言八股 · 2 个当前主线项目 · 模拟面试拷问引擎**

</div>

---

## ✨ 项目亮点

- 🏆 **318 道公共真题**：完整题库由 [interview-mock-skill](https://github.com/SuperGODOG/interview-mock-skill) 统一维护；本仓库当前保留首批 240 道五卷文档，扩展题与原题属于同一题库，新增部分更侧重秒杀、Redis、MQ、MySQL 等后端高频考点
- 📝 **每题带答题框架**：核心考点 + 大厂四步答题框架（概念澄清 → 架构机制 → 工程权衡 → 实战经验）+ 学习路径（前置/后置题目）
- 📚 **85 篇语言八股**：Java 77 篇（含 66 篇体系化课件）、Python 3 篇、Go 5 篇，覆盖 JVM/并发/集合/Spring/MySQL/Redis/网络/OS/GMP/GC/GIL
- 🛠 **2 个当前主线项目**：[SkillForge](https://github.com/SuperGODOG/skillforge)（Skill 注册、路由、评测与受控演化）与 [miaosha](https://github.com/SuperGODOG/miaosha)（限流、Redis Lua 预扣库存、RabbitMQ 异步削峰、条件扣库与订单落库）；旧版项目档案仍保留在 `projects/` 供历史对照
- 🎤 **模拟面试引擎**：内置大厂 AI 模拟面试官 Skill（出题→作答→四维点评→复盘）与项目拷问引擎，可直接驱动 AI 进行模拟面试
- 🗂 **深度分级**：每道题 1-5 级标注（概念定义 → 原理机制 → 设计与方案 → 落地与权衡 → 前沿与延伸），按梯度刷题

---

## 📖 目录导航

| 模块 | 内容 | 说明 |
|------|------|------|
| [📌 01-面试八股文](docs/01-面试八股文/01-Agent应用开发.md) | **240 道首批真题文档** | 5 大卷 · 深度分级 · 答题框架 · 学习路径 |
| [📚 02-语言八股](docs/02-语言八股/README.md) | **Java / Python / Go 面试八股** | 85 篇 · 考点+要点+代码+追问 |
| [🏢 03-企业招聘分析](docs/03-企业招聘分析/README.md) | 大厂 AI Agent 岗分析 | 规划中 |
| [📖 04-开源项目学习笔记](docs/04-开源项目学习笔记/README.md) | 优秀开源项目剖析 | 规划中 |
| [📄 05-简历模板](docs/05-简历模板/README.md) | AI Agent 简历写法 | 规划中 |
| [🗣 06-STAR面试稿](docs/06-STAR面试稿/README.md) | 面试话术准备 | 规划中 |
| [❓ 07-面试问答集](docs/07-面试问答集/README.md) | 项目面试问答 | 规划中 |
| [🤖 skills/](skills/project-mock-interview/SKILL.md) | **模拟面试 Skill 包** | 拷问引擎 + 大厂模拟面试官 |

---

## 🗂 八股文分卷（首批 240 道真题）

| 卷 | 题数 | 覆盖范围 |
|----|------|----------|
| [01-Agent应用开发](docs/01-面试八股文/01-Agent应用开发.md) | **182** | 宏观认知、主流框架、工具调用、Prompt、记忆、架构设计、数据库、工程落地、性能评估 |
| [02-八股基础](docs/01-面试八股文/02-八股基础.md) | **38** | JVM/并发/网络/OS/数据库/Redis |
| [03-Transformer与大模型](docs/01-面试八股文/03-Transformer与大模型.md) | **10** | 注意力、长上下文、KV Cache、推理优化、微调对齐 |
| [04-LeetCode算法](docs/01-面试八股文/04-LeetCode算法.md) | **8** | 手撕代码高频题 |
| [05-反问与国企特别版](docs/01-面试八股文/05-反问与国企特别版.md) | **2** | 反问环节与国企面试 |

## 📚 语言八股（85 篇）

| 语言 | 篇数 | 内容 |
|------|------|------|
| [Java](docs/02-语言八股/Java/00-学习路线图.md) | **77** | [11 篇手撕笔记](docs/02-语言八股/README.md)（集合/并发/JVM/Spring/MySQL/Redis/网络/OS/MQ/锁/设计模式）+ [66 篇体系化课件](docs/02-语言八股/Java/课件/README.md)（面试场景+追问+代码+自测） |
| [Python](docs/02-语言八股/Python/01-Python基础.md) | **3** | 基础（GIL/可变不可变）/ 并发与异步 / 进阶陷阱 |
| [Go](docs/02-语言八股/Go/01-Go基础.md) | **5** | 基础（slice/map）/ 并发（GMP）/ 内存与 GC / 进阶陷阱 / Go与Python对比 |

## 🛠 当前项目范式（2 个主线项目）

| 项目 | 技术栈 | 一句话定位 |
|------|--------|------------|
| [SkillForge](https://github.com/SuperGODOG/skillforge) | Python + SQLite + Embedding + LangGraph sidecar | Skill 注册、级联路由、评测与受控自进化平台 |
| [miaosha](https://github.com/SuperGODOG/miaosha) | Java + Spring Boot + Dubbo + RabbitMQ + Redis + MySQL | 限流、Redis Lua 预扣库存、异步削峰、条件扣库与订单落库 |

> `projects/` 下的 TripPlanner、SkillForge、JeecgBoot 是早期静态项目档案。当前项目表达与面试准备以两个源仓库的最新代码为准；Java 项目主线已切换为 `miaosha`。

## 🧭 题库口径与更新

- **公共题库**：当前由 [interview-mock-skill](https://github.com/SuperGODOG/interview-mock-skill) 统一维护，共 318 道题；六件套 Skill 共享同一份题库，新增题与原 240 道题权重相同，只是新增部分更侧重后端。
- **本仓库文档**：`docs/01-面试八股文/` 是首批 240 道题的静态文档，不代表题库中的优先级，也不会自动随公共题库增长。
- **项目匹配**：题库扩充后，已有项目的 `match.json` 仍是静态候选快照；重新执行项目的 `match/finalize`，新题才会进入候选列表。

---

## 🚀 快速开始

### 1. 刷题路径（按深度梯度）

1. 从 [01-Agent应用开发](docs/01-面试八股文/01-Agent应用开发.md) 开始，按小类顺序刷
2. 每道题先自己答，再对照"核心考点 + 答题框架"查漏
3. 按"学习路径"的前置/后置关系扩展

### 2. 项目准备路径

1. 先读 [SkillForge 当前源码](https://github.com/SuperGODOG/skillforge) 和 [miaosha 当前源码](https://github.com/SuperGODOG/miaosha)，各写出 30 秒项目介绍
2. 再用 [interview-mock-skill](https://github.com/SuperGODOG/interview-mock-skill) 按项目重新匹配公共题库
3. 需要查看早期答题材料时，再进入 `projects/` 下对应的历史静态档案

### 3. 用 AI 模拟面试（Skill 包）

推荐从 [interview-mock-skill](https://github.com/SuperGODOG/interview-mock-skill) **整包安装**到你的 AI 助手（Claude Code / Hermes / Antigravity 等）。它是“1 个主入口 + 5 个依赖”的完整 Skill 包，请不要只拆装其中一个子 Skill；本仓库 `skills/` 下的文件仅作为早期兼容材料保留。

- 大厂 AI 模拟面试官：覆盖阿里/腾讯/字节/百度/美团等大厂，逐题提问 + 四维点评
- 项目拷问引擎：基于公共题库按项目匹配，对当前主线项目进行深度拷问

### 4. 重新生成八股文

题库数据变更后，重跑生成脚本：

```bash
python3 scripts/generate_baike.py   # 生成本仓库首批 240 道题的分卷文档
python3 scripts/html2md.py          # HTML 课件转 Markdown
```

---

## 🏗 项目架构

```
ai-agent-interview-240/
├── README.md                          # 本文件
├── docs/
│   ├── 01-面试八股文/                 # 首批 240 道真题文档（5 卷）
│   │   ├── 01-Agent应用开发.md        # 182 题 · 核心战场
│   │   ├── 02-八股基础.md             # 38 题
│   │   ├── 03-Transformer与大模型.md  # 10 题
│   │   ├── 04-LeetCode算法.md         # 8 题
│   │   └── 05-反问与国企特别版.md     # 2 题
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
│   ├── SuperGODOG__tripplanner/       # 早期项目画像 + 匹配表 + 项目内作答
│   ├── SuperGODOG__skillforge/        # 早期 SkillForge 静态档案
│   └── jeecgboot__JeecgBoot/          # 早期 Java 静态档案
├── skills/                            # 早期兼容 Skill 材料（当前整包见 interview-mock-skill）
│   ├── project-mock-interview/        # 项目拷问引擎（公共题库匹配 + 四维点评）
│   └── interview-skills/              # 大厂 AI 模拟面试官
└── scripts/
    ├── generate_baike.py              # 八股文生成脚本（题库→分卷）
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
