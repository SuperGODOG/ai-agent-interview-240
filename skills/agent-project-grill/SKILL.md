---
name: agent-project-grill
description: Agent 项目面试拷打引擎。默认用 project-mock-interview 按项目题库出题、四维点评、复盘沉淀，对低分题用 grilling 深挖；未建档项目自动经 interview-bank-pipeline 建档并同步快照；全程过程落文档，回答一般的题自动生成学习卡供下次复习。当用户说"开一场 / 拷打我 / 针对我的 Agent 项目模拟面试 / 项目拷打练习"时使用。
---

# Agent 项目拷打（建档检查 → 出题 → 拷打 → 深挖 → 复盘）

整场上下文预算 ≤20K tokens。五个依赖 skill 的分工：interview-bank-pipeline 建档（生产端），interview-resume-pack 备战包/漏斗稿（生产端，拷打前置，见其 SKILL.md），project-mock-interview 出题点评（主循环），agent-review-audit 代码体检（按需），grilling 深挖（补课）。核心承诺：**每题有记录、低分有 grilling、场场有复盘、复习有学习卡**。

## 依赖与整包安装

本仓库按 **1 主入口 + 5 依赖**整包安装，勿单拆或单独关闭组件；六个目录必须位于同一个 skills 父目录。以下相对路径均以本 SKILL.md 所在目录为基准。缺失组件时先明确报告降级，按下列内联规则继续可执行部分，不虚构题号、项目档案或已完成步骤。

本 skill 是主入口与公共语料枢纽，题库唯一仓库副本位于 `references/题库/`。五个依赖：`interview-bank-pipeline`（建档与题库生产）、`interview-resume-pack`（备战包）、`project-mock-interview`（读题与点评）、`agent-review-audit`（可选代码体检）、`grilling`（深挖）。安装依赖齐全不代表每场都调用，体检仍仅按用户要求触发。

缺失时的内联兜底（优先于下文对应依赖调用）：
- 缺 pipeline：已有项目档案照常使用；未建档时基于用户提供的代码与公共题库按题提问，标注“未建档临时练习”，不声称建档或同步成功。
- 缺 resume-pack：使用已有完整备战包；没有则跳过表达材料前置，正常练习。
- 缺 project-mock-interview：从本 skill 公共题库按 id 提取单题，一次一问；按概念理解、原理深度、落地证据、结构完整度各 1–5 分点评（1=错误/空泛，3=方向对但缺细节，5=准确且有证据）；无档案则仅用实际代码证据，继续阶段 2–3。
- 缺 agent-review-audit：日常练习不受影响；用户要求体检时按架构、生产就绪、健壮性检查给定代码片段，记录证据与待核实项，不冒充 500 题卡审查。
- 缺 grilling：执行阶段 2 的一次一问、推荐答案、先查代码内联规则。
- 工作区不可用且 pipeline 缺失：仅在会话内记录复盘与学习卡，明确尚未落盘，待提供可写工作区后保存。

### 题库索引与检索路由（references/题库/索引/）

为加速出题与检索分类，在 `references/题库/索引/` 下维护稳定分类索引（不冗余复制答案正文）：
- `01_business_projects.json`：业务线与项目实战题（秒杀、分片上传、多集群）
- `02_frontend.json`：前端工程、渲染与页面交互题（URL到渲染、分片上传前端流、E2E/前端影响测试）
- `02_backend_os.json` / `02_backend_network.json` / `02_backend_database.json` / `02_backend_mq.json`：后端基础（操作系统、网络、数据库与存储、消息队列）
- `03_agent_harness.json`：Agent Harness 评测、沙箱与测试闭环题
- `04_agent_architecture.json` / `05_rag_retrieval.json` / `06_backend_java.json` / `07_algorithms.json` / `08_general_behavior.json`：其余专业分类
- `09_ai_infra.json`：AI Infra、高性能算子开发与编译、分布式并行（TP/EP/All-to-All）与加速卡架构题
- **降级回退**：若索引文件缺失或不可读，出题与检索模块自动回退遍历 `items.json` 全量语料或使用 `concepts.yaml` 关键词匹配。

## 0. 环境与建档自检（开工前必做）

1. 解析工作区并绑定 `WORKSPACE_ROOT`：`INTERVIEW_WORKSPACE` 非空时使用它；未设置时仅在 `$HOME/.interview-workbench` 已存在时使用该兼容目录。两者都不可用则先按 interview-bank-pipeline 的「跨平台部署」设置/初始化后再继续；禁止把空变量拼成 `/obsidian_vault/...`，也禁止自动创建兼容目录
2. 定位项目 slug（`owner__repo`），**运行快照版本新鲜度检查**：
   运行 `python3 <interview-bank-pipeline>/scripts/check_snapshot.py <target_path_or_slug>`：
   - **FRESH**（快照代码与公共题库指纹双向 100% 一致且题目链接有效）→ 直接进入阶段 1，interview-bank-pipeline 不参与；若为 **DIRTY_WORKTREE** 提示工作区未提交状态后按需继续；
   - **MISSING**（未建档）→ 触发建档流水线（按 interview-bank-pipeline 阶段三执行）：`repo_fuse.py fetch <url_or_dir>` → `match <slug>` → 派 subagent 写画像/作答 → `finalize <slug>`（自动记录 commit_hash 与快照元数据并同步）→ 校验 `check_snapshot.py` 返回 FRESH 后进入阶段 1；
   - **STALE**（快照过时：代码漂移或题库扩容未对齐）或 **LEGACY_UNTRACKED**（旧版无版本快照）→ **严禁读取过时快照！** 向用户明确警示版本差距（如代码落后或题库扩容待对齐），提示用户必须先刷新快照建档，防止因旧代码/旧题库产生模型幻觉与误判。
3. **备战包软前置**：检查 `$WORKSPACE_ROOT/obsidian_vault/40_项目档案/<slug>/备战包/README.md` 存在且含 `完整性状态: 完整`，并确认其六类正文相对链接均存在。否则按备战包缺失处理，提示一次："该项目还没有完整备战包（漏斗稿+深钻点+不会题防守）。建议先说『生成备战包』由 interview-resume-pack 生成——漏斗稿是表达地图，深钻点 L3 会成为本场优先出题源。" 用户坚持直接开打则照常继续，不阻塞
4. 读复习源：`$WORKSPACE_ROOT/obsidian_vault/40_项目档案/<slug>/学习卡.md` 与 `面试复盘.md` 的待复习清单，有则阶段 1 复习优先（先清未复习的学习卡）

## 1. 模拟拷打（project-mock-interview）

读取 project-mock-interview 的 SKILL.md，按其拷问模式执行：

- 出题策略：备战包优先（备战包 README 状态为「完整」且索引文件齐全时，深钻点 L3 问题与不会题清单为优先出题/检验源）+ 薄弱优先（有体检时用 weakness_tags）+ 复习优先（学习卡/待复习清单）；都没有则按深度递进
- 一次一题，用户答完做四维点评（概念理解 / 原理深度 / 落地证据 / 结构完整度），默认 3 题/场
- **每题当场记录**（供阶段 3 落档）：题 id、用户作答摘要、四维得分、点评要点
- 点评只引用作答档已有的证据锚点；证据不足就诚实说明，禁止编造

## 2. grilling 深挖

对四维任一 ≤2 或用户答不出的题，切到 grilling 深挖：

1. grilling 已随仓库/本地附带（`grilling/SKILL.md`，来自 mattpocock/skills）→ 读取其 SKILL.md，按原版追问节奏执行
2. 环境没有 grilling → 按内联规则执行：**一次只问一个问题**（同时问多个会让人懵）；每题给出推荐答案；能查代码库就先查代码库再问；逐条追问直到该薄弱点挖透

**逐问记录**：追问内容、用户回答、agent 给的要点，全部记入场次记录（阶段 3 落档），不留在聊天里丢失。

## 3. 复盘与学习卡（有文档可循）

每场结束写两处文档，都是纯 markdown，Obsidian 只是可选的查看方式，不依赖它：

1. **场次复盘**：`$WORKSPACE_ROOT/obsidian_vault/40_项目档案/<slug>/面试复盘.md`，追加本场记录：
   - 场次信息（日期 / 项目 / 题数）
   - 题目清单 + 四维得分表
   - grilling 记录（追问链 + 要点）
2. **备战包反馈（存在备战包时）**：本场暴露的薄弱点若落在漏斗稿/不会题覆盖范围内，在复盘文件末尾追加一行 `- [ ] 备战包修订建议：<哪份产物><哪个点><怎么改>`；interview-resume-pack 只读取未勾选项，成功吸收并通过证据门后才改为 `[x]`
3. **学习卡**：`$WORKSPACE_ROOT/obsidian_vault/40_项目档案/<slug>/学习卡.md`，对任一维 ≤2 或触发过 grilling 的题追加一行：
   - 格式：`- [ ] Lxx ｜ 薄弱维度:xxx ｜ 一句话记忆点:xxx ｜ 下次复习`
   - 下一场阶段 0 优先复习；复习过关后勾掉 `[x]`，保留为已掌握记录

## 纪律

- 分层加载：只按需读题卡 / 题段 / 证据切片，禁止整读题库或全量代码
- 体检阶段只读路由输出，不读题卡全量
- 子 skill（project-mock-interview / grilling / interview-bank-pipeline / interview-resume-pack）都按各自 SKILL.md 执行；建档与备战包是生产端：建档只在未建档或项目大改时跑，备战包只在缺失或未勾选的复盘修订建议积累 ≥3 条时重生成
- grilling 已内置（来源 mattpocock/skills，MIT）；若被移除，按阶段 2 内联规则兜底，不影响流程
- 跨平台：后续所有数据路径只使用阶段 0 解析后的 `WORKSPACE_ROOT`；兼容目录必须已存在，禁止写死或猜测其他用户目录
