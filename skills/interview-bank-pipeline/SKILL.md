---
name: interview-bank-pipeline
description: 面试题库文档清洗分类 + Obsidian 知识图谱 + GitHub 项目融合三合一流水线。当用户要求清洗/分类面试文档、把题库建成 Obsidian 图谱、或根据 GitHub 项目链接生成面试设计档案时使用。脚本已内嵌于本 skill 的 scripts/，数据工作区由 INTERVIEW_WORKSPACE 指定（未设置时回退 ~/.interview-workbench）。
version: 1.1.0
---

# 面试题库清洗与知识图谱流水线

三阶段流水线，判断活全部交给 subagent（隔离上下文），机械活全部脚本化。主会话只接触统计、校验结果与审计报告。

## 依赖与整包安装

本仓库按 **1 主入口 + 5 依赖**整包安装，勿单拆或单独关闭组件；六个目录必须位于同一个 skills 父目录。以下相对路径均以本 SKILL.md 所在目录为基准。本节降级分支优先于下文对应依赖调用。缺失组件时先明确报告降级，按下列内联规则继续可执行部分，不虚构题号、项目档案或已完成步骤。

本 skill 是 `agent-project-grill` 依赖的生产端，也为 `project-mock-interview` 与 `interview-resume-pack` 提供题库/建档输入。公共题库发布目标为 `../agent-project-grill/references/题库/`。

单件安装缺主入口时，清洗、分类与图谱生成继续写 workspace；题库同步明确跳过，不创建空壳 skill，不写引擎旧题库位置。缺 project-mock-interview 时仍可生成工作区档案，明确消费端不可用，不宣称完成整包联动；已有项目档案同步机制保持原样。缺 resume-pack/grilling/audit 不影响生产阶段，不尝试调用它们。

## 工作区（INTERVIEW_WORKSPACE）

- 生产数据（源文档/题库中间态/图谱/缓存）在**数据工作区**；发布题库仅同步到主入口的公共目录
- 解析顺序：环境变量 `INTERVIEW_WORKSPACE` → 未设置时回退 `~/.interview-workbench`（旧本机默认，仅为兼容）
- 跨平台/新设备：先设置 `INTERVIEW_WORKSPACE`（如 `export INTERVIEW_WORKSPACE=$HOME/.interview-workbench`），再按「跨平台部署」初始化数据
- 脚本已内嵌于本 skill 的 `scripts/`（pipeline.py / repo_fuse.py / verify_categories.py），通过环境变量定位工作区，可在任意目录执行

## 项目布局（$INTERVIEW_WORKSPACE/）

- `agent_review.md` 源文档（唯一输入）
- `concepts.yaml` 概念词典（图谱与融合的桥梁，唯一需人工维护的文件）
- `items.json` / `schema.json` / `batches/classified/` 中间态（checkpoint，可断点续跑）
- `categories/` 清洗产物（大类目录/小类文件）
- `obsidian_vault/` 知识图谱（00_MOC / 10_概念 / 20_索引 / 30_手写笔记 / 40_项目档案）
- `repos_cache/<owner>__<repo>/` 克隆缓存 + profile.json / match.json / sections/
- 旧工作区可能还有 pipeline.py / repo_fuse.py / verify_categories.py 的旧副本，可忽略；一律使用本 skill `scripts/` 下的版本

## 题库发布链路

首次工作区缺少题库时，从同包 `../agent-project-grill/references/题库/` 复制 items.json、concepts.yaml、schema.json 中缺失的文件到 workspace，不覆盖已有文件，不从不完整 workspace 反向覆盖仓库。

写侧固定为：pipeline 写 workspace → `python3 <本skill>/scripts/pipeline.py sync-bank` 同步三文件到主入口 → 在真理源仓库审查并 git 提交。`export` 无断链成功后也执行同一同步；缺少源文件则报错且不覆盖公共题库。发布时从仓库版本运行脚本；部署副本有更新时须先回收至仓库审查，提交后再整包分发。扩题后已有项目需重新 match/finalize 才能更新候选路由，项目档案同步机制不变。

## 阶段一：文档清洗分类（源文档 → categories/）

1. 在 `$INTERVIEW_WORKSPACE` 下执行 `python3 <本skill>/scripts/pipeline.py split` — 切分条目（行号做稳定 ID，识别 标题/编号小类/括号子标签/HTML注释块），注释块内题目标记为自由分类
2. 派 subagent 分类批次（每批 ~48 条，最多 3 个并行）：
   - assigned=true 的条目保留机械分配的 major/minor，只补 depth(1-5) 和 subminor
   - assigned=false（注释块）按语义相似度归位，fuzzy=true + note 理由
   - 输出 JSON 到 batches/classified/，每批一个文件；用 `pipeline.py validate` 校验
3. `python3 <本skill>/scripts/pipeline.py merge` — 汇总生成 categories/<大类>/<小类>.md
4. ≥15 题的大文件派 subagent 递归细分：合并相近 H2 组、拆分超载组、删除"补充：源自「xxx」"组并入主题组、组内按逻辑深度排序（概念定义→原理机制→设计实现→落地与权衡→前沿延伸）；要求逐字保留题目
5. `python3 <本skill>/scripts/verify_categories.py` + `python3 <本skill>/scripts/pipeline.py audit` — 全绿才算完成

## 阶段二：Obsidian 知识图谱（categories/ → obsidian_vault/）

1. 编辑 `concepts.yaml`（概念名/aliases/keywords/summary/related；关键词注意 YAML 会把 "503" 解析成 int，必须加引号）
2. `python3 <本skill>/scripts/pipeline.py export` — 生成 00_MOC（总览+大类）、10_概念、20_索引（题级锚点 `### L6`）、99_dataview.md；内置断链校验
3. 保留区：30_手写笔记 与 40_项目档案 重跑时自动保留（内部实现：先移到 vault 外再 rmtree，注意 shutil.move 遇已存在目录会嵌套进去，移回前需 rmdir 空壳）
4. 概念笔记链接用 `[[20_索引/<大类>/<小类>.md#L6|L6 · 摘要]]` 锚点直达题目

## 阶段三：GitHub 项目融合（URL/本地路径 → 双落点档案 + 版本快照）

0. **快照版本检查（前置）**：`python3 <本skill>/scripts/check_snapshot.py <url_or_dir>` — 检查是否已建档及代码与题库双向新鲜度（`FRESH` / `STALE` / `MISSING` / `LEGACY_UNTRACKED`）。
   - **关联生命周期与语义审查**：只有代码（commit 一致且工作树 clean）与公共题库（items/concepts/schema 指纹一致）双 FRESH，且题目链接全部有效时，快照才可免重算复用。注意：`FRESH` 仅代表代码/题库/题号版本联通，不等于每个答案语义与代码证据已审查完毕。公共题库每次扩容后，旧项目关联自动变为待刷新（`STALE`），需按项目实际技术栈重新运行 match 对齐新题，无关的 Infra 新题绝不强挂在普通 Agent/秒杀项目上。
   - **项目作答资产保护与代码变更约束**：已生成的《项目内作答.md》属于项目专有资产（包含文件:行号真实证据锚点与定制解答）。若代码发生变更，旧证据与旧答案必须先经过审查刷新后方可用于当前项目；只有在代码证据依然有效的前提下，才可保留原有成熟作答并增量提示追加新题，严禁在代码未变时因题库变动被机械整篇覆盖。
   - **严格区分 L 题与 Q 卡空间**：项目 match.json 与匹配表只关联公共真题 L 编号（来自 items.json 的有效 question 条目），严禁混用 03_Cards 中的 Qxxx 题卡编号，两者属于独立空间。
1. `python3 <本skill>/scripts/repo_fuse.py fetch <url_or_dir>` — 支持 Git URL 或本地仓库路径，浅克隆/同步 + 提取 Git commit hash、分支、时间戳与树指纹 → `snapshot_meta.json` + `profile.json`
2. `python3 <本skill>/scripts/repo_fuse.py match <slug>` — 命中概念 → 候选题目 → match.json（内嵌版本 meta）
3. 派 subagent（3 个并行）：
   - 画像：自研项目写 30秒介绍+钩子+框架给的 vs 我设计的；第三方项目写"学习谈资档案"，必须排查概念误报
   - 作答（按大类分组）：每题 = 一句话回答 + 展开细节一/二/三，必须引用真实 文件:行号，未实现的部分诚实标注"对应物+一般方向"，无关题可弃（末尾弃题说明）
4. `python3 <本skill>/scripts/repo_fuse.py finalize <slug>` — 汇总 sections/ → obsidian_vault/40_项目档案/<slug>/（写入 commit/synced_at 元数据的前置头，产出项目画像/匹配表/项目内作答/snapshot_meta.json）+ 仓库 docs/INTERVIEW_DESIGN_MAP.md
5. **同步快照到拷打引擎（联动，必做）**：把建档产物同步到 project-mock-interview 的 `references/项目/<slug>/`（match.json + snapshot_meta.json + 项目画像/面试题匹配表/项目内作答）。目标目录按当前 agent 解析：统一入口 `~/.cc-switch/skills/project-mock-interview`（Codex/Claude/Gemini/Hermes 均软链于此）。命令见 project-mock-interview 的 `references/README.md`；编排 skill（agent-project-grill）会在建档后自动执行
6. `python3 <本skill>/scripts/pipeline.py export` 刷新总览（项目档案区）
7. 推送（可选）：自己的仓库 push_files 到 master；第三方仓库先 fork → create_branch → push_files → 验证 get_file_contents

## 关键坑（都踩过）

- subagent 批量分类最多 3 个并发（delegate_task 限制），分波派发
- 每波 subagent 回来后立即 validate/verify，防坏 JSON 级联
- 机械关键词匹配必然有噪声（如"上下文"误命中"上下文切换"、"状态"误命中"状态码"），由作答 subagent 精选过滤——不要试图把词典调到零噪声
- 概念 related 引用必须精确匹配概念 name，否则产生断链（校验器会报）
- 大仓库（1809 文件实测）：树深度限 5、内容采样限 400 文件/4MB，克隆用 --depth 1
- 审计"未分类"要读 classified 结果，不能只看 items.json（depth/分类在 classified 里）
- 脚本里 `ROOT` 优先读 `INTERVIEW_WORKSPACE`：工作区换位置后必须重设环境变量，否则会落到脚本所在目录

## 跨平台部署（GitHub 分发后）

本 skill 自包含（scripts/ 已内嵌），新设备三步：

1. 设环境变量：`export INTERVIEW_WORKSPACE=<数据目录>`（写入 shell 配置或 agent 环境，长期生效）
2. 初始化数据：创建目录并放入 `agent_review.md`、`concepts.yaml`、`items.json`、`schema.json`、`categories/`、`obsidian_vault/`（题库与图谱可整体迁移；`repos_cache/` 可留空按需重建）
3. 装依赖：python3、PyYAML、git、jq（jq 仅 project-mock-interview 路由提取用）

不要上传 GitHub 的内容：`repos_cache/`（含第三方仓库克隆）、原始面经文档（如 `agent_review.md`）、含个人笔记的 `30_手写笔记`——仓库只放 skill 文件夹。Windows 建议用 Git Bash / WSL 运行 shell 步骤。

## 验证清单

- [ ] pipeline.py validate 全 OK（major/minor 与 schema 精确匹配、depth 1-5）
- [ ] verify_categories.py 全部 [OK]（题数 + 文本多重集一致）
- [ ] audit_report.md：题目总数 = 落盘数，无未分类
- [ ] export 链接校验 0 断链
- [ ] subagent 作答摘要包含每题证据文件列表（自报不可全信，抽查 2-3 处行号）
- [ ] GitHub 推送后用 get_file_contents 验证文件存在
- [ ] check_snapshot.py 校验返回 FRESH（commit_hash/工作树指纹与代码库 100% 对齐，且 bank_fingerprint 与当前公共题库一致，候选题目链接全部有效）
- [ ] 建档后快照已同步到 project-mock-interview `references/项目/<slug>/`（包含 snapshot_meta.json）
