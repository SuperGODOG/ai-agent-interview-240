# AI Agent 面试真题库 — 240 道真实大厂题 + 3 个亲手项目

> 面向大厂 **AI Agent 岗**的面试备战仓库：**240 道真实大厂真题**（附答题框架与学习路径）+ **3 个亲手实现的 Agent 项目档案**（画像/匹配表/项目内作答），形成"真题 → 项目 → 作答"的完整闭环。

---

## 项目亮点

- **240 道真实大厂真题**：AI Agent 岗面试中实际被问到的题（非通用八股），按 5 大卷分类：Agent 应用开发（182 题）、计算机八股（38 题）、Transformer 与大模型（10 题）、LeetCode 算法（8 题）、反问与国企特别版（2 题）
- **每题带答题框架**：核心考点 + 大厂四步答题框架（概念澄清 → 架构机制 → 工程权衡 → 实战经验）+ 学习路径（前置/后置题目）
- **3 个亲手项目档案**：TripPlanner（多智能体旅行规划）、SkillForge（Skill 自进化元 Agent）、JeecgBoot（低代码平台），每个含项目画像、240 题匹配表、项目内作答——面试讲自己的项目，扛得住追问
- **深度分级**：每道题按 1-5 级标注（概念定义 → 原理机制 → 设计与方案 → 落地与权衡 → 前沿与延伸），可按深度梯度刷题

---

## 目录导航

### 文档区

| 目录 | 内容 | 说明 |
|------|------|------|
| [01-面试八股文](docs/01-面试八股文/01-Agent应用开发.md) | 240 道真实大厂真题 | 5 大卷，按逻辑深度排序，附答题框架 |
| [02-语言八股](docs/02-语言八股/README.md) | Java / Python / Go 语言面试八股 | 19 篇手撕笔记，考点+要点+代码+追问 |
| [03-企业招聘分析](docs/03-企业招聘分析/README.md) | 大厂 AI Agent 岗分析 | 规划中 |
| [04-开源项目学习笔记](docs/04-开源项目学习笔记/README.md) | 优秀开源项目剖析 | 规划中 |
| [05-简历模板](docs/05-简历模板/README.md) | AI Agent 简历写法 | 规划中 |
| [06-STAR面试稿](docs/06-STAR面试稿/README.md) | 面试话术准备 | 规划中 |
| [07-面试问答集](docs/07-面试问答集/README.md) | 项目面试问答 | 规划中 |

### 实战项目档案

| 项目 | 技术栈 | 一句话定位 |
|------|--------|------------|
| [TripPlanner](projects/SuperGODOG__tripplanner/README.md) | LangGraph + ReAct + MCP + FastAPI | 多智能体旅行规划系统 |
| [SkillForge](projects/SuperGODOG__skillforge/README.md) | Python + bge + DeepSeek + SQLite | Agent Skill 自进化元 Agent 系统 |
| [JeecgBoot](projects/jeecgboot__JeecgBoot/README.md) | Java + 低代码平台 | 低代码平台二次开发与架构理解 |

---

## 八股文分卷

| 卷 | 题数 | 覆盖范围 |
|----|------|----------|
| [01-Agent应用开发](docs/01-面试八股文/01-Agent应用开发.md) | 182 | 宏观认知、主流框架、工具调用、Prompt、记忆、架构设计、数据库、工程落地、性能评估 |
| [02-八股基础](docs/01-面试八股文/02-八股基础.md) | 38 | JVM/并发/网络/OS/数据库/Redis |
| [03-Transformer与大模型](docs/01-面试八股文/03-Transformer与大模型.md) | 10 | 注意力、长上下文、KV Cache、推理优化、微调对齐 |
| [04-LeetCode算法](docs/01-面试八股文/04-LeetCode算法.md) | 8 | 手撕代码高频题 |
| [05-反问与国企特别版](docs/01-面试八股文/05-反问与国企特别版.md) | 2 | 反问环节与国企面试 |

---

## 项目架构

```
ai-agent-interview-240/
├── README.md                          # 本文件
├── docs/
│   ├── 01-面试八股文/                 # 240 道真实大厂真题（5 卷）
│   │   ├── 01-Agent应用开发.md        # 182 题 · 核心战场
│   │   ├── 02-八股基础.md             # 38 题
│   │   ├── 03-Transformer与大模型.md  # 10 题
│   │   ├── 04-LeetCode算法.md         # 8 题
│   │   └── 05-反问与国企特别版.md     # 2 题
│   ├── 02-语言八股/                   # Java/Python/Go 语言面试八股
│   │   ├── Java/                      # 11 篇 + 学习路线图
│   │   ├── Python/                    # 3 篇
│   │   └── Go/                        # 5 篇
├── projects/                          # 亲手项目档案（面试能扛追问）
│   ├── SuperGODOG__tripplanner/       # 项目画像 + 匹配表 + 项目内作答
│   ├── SuperGODOG__skillforge/
│   └── jeecgboot__JeecgBoot/
└── scripts/
    └── generate_baike.py              # 八股文生成脚本（题库→分卷）
```

---

## 快速开始

### 1. 刷题路径（按深度梯度）

1. 从 [01-Agent应用开发](docs/01-面试八股文/01-Agent应用开发.md) 开始，按小类顺序刷
2. 每道题先自己答，再对照"核心考点 + 答题框架"查漏
3. 按"学习路径"的前置/后置关系扩展

### 2. 项目准备路径

1. 每个项目先读 [项目画像](projects/SuperGODOG__tripplanner/README.md)，建立 30 秒自我介绍
2. 看 [面试题匹配表](projects/SuperGODOG__tripplanner/面试题匹配表.md)，了解该项目能扛哪些题
3. 用 [项目内作答](projects/SuperGODOG__tripplanner/项目内作答.md) 准备追问应答

### 3. 重新生成八股文

题库数据变更后，重跑生成脚本：

```bash
python3 scripts/generate_baike.py
```

---

## 题目深度分级说明

| 深度 | 含义 | 刷题策略 |
|------|------|----------|
| 1/5 | 概念定义 | 快速过，能一句话说清 |
| 2/5 | 原理机制 | 理解底层原理，能画图讲 |
| 3/5 | 设计与方案 | 重点刷，面试主战场 |
| 4/5 | 落地与权衡 | 结合项目讲 trade-off |
| 5/5 | 前沿与延伸 | 加分项，了解即可 |

---

## 免责声明

题目来源于本人面试经历与公开渠道搜集整理，仅供个人学习使用。

---

## SEO / 关键词索引

本仓库面向以下搜索场景（供搜索引擎与爬虫索引）：

- **AI Agent 面试题**：Agent 面试真题、大模型 Agent 岗面试、Agent 架构面试、Multi-Agent 面试、RAG 面试、MCP 面试、Prompt 工程面试、Agent 记忆系统面试、工具调用面试、AI Agent 八股文
- **大厂面试**：字节跳动面试、腾讯面试、阿里面试、百度面试、大模型应用开发面试、LLM 面试题、AI 工程面试
- **语言八股**：Java 八股文、Java 集合面试题、并发编程面试、JVM 面试题、Spring 面试、MySQL 面试、Redis 面试、计算机网络面试、操作系统面试、消息队列面试、设计模式面试、Python 面试题、Python GIL、Go 面试题、Go 并发 GMP、Go GC、Go channel
- **项目实战**：LangGraph 项目、ReAct Agent 项目、多智能体项目、MCP 项目、Skill 系统项目、低代码平台

> 提示：题库与语言八股均为 Markdown 纯文本，无 JS 渲染依赖，搜索引擎可直接抓取正文内容。
