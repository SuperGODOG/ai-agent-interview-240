---
name: agent-review-audit
description: 基于项目代码特征自动路由匹配 500 道大厂高品质 AI Agent、RAG & AI Infra 面试审查题，进行硬核代码诊断、架构 Gap 分析与交互提问。
version: 3.1.0
---

# Agent Review Audit Skill (大厂 AI Agent & RAG 审查技能 3.1 修复版)

## 📌 加载规约（防上下文爆炸）

分层加载，整场上下文 ≤16K tokens：

- **L0 路由**：运行 `python3 scripts/route_project.py --path <代码路径>`，读取输出的 matched_concept / target_cards / candidates / evidence_anchors（约 400 tokens）
- **L1 题卡**：按需读取 Top2 题卡全文 `references/03_Cards/Qxxx.md`（每张约 1.5KB）
- **L2 证据切片**：对 evidence_anchors 中的文件运行 `python3 scripts/slice_code.py <file> <start_line>`，每片 ≤150 行（约 1,200 tokens）
- **禁止**：整读 references/03_Cards 全量（500 张）、对未命中文件全量扫描、一次性读入多个大文件

## 🎯 审查 SOP（严格按序执行）

1. **路由**：`python3 scripts/route_project.py --path <代码路径或文件>`，读取输出
2. **读卡**：target_cards 非空时读取 Top2 题卡全文；为空则按下方兜底规则执行
3. **切片**：对 evidence_anchors 逐文件切片（每个锚点取 1 片，起始行取锚点 matched_line）
4. **打分**：依据 `config/rubrics.yaml` 的扣分项，对切片做三维打分（Architectural_Soundness / Production_Readiness / Robustness_Guardrails，各 100 分起扣），每项扣分必须对应切片证据
5. **输出**：按下方 JSON 模板输出打分与证据；随后以题卡为纲向用户提出 2-3 个交互式追问
6. **复盘**：`python3 scripts/update_profile.py --path <代码路径> --tags <薄弱概念id,逗号分隔>` 更新项目 `.agent-audit/profile.json`；下场路由时薄弱概念自动加权（+5）

**兜底规则**：
- target_cards 为空 / 置信度 < 3.0：按「通用架构审查」执行——直接三维打分 + 通用追问，不强行出题
- 命中概念但题卡为空：按该概念的核心审查维度提问（见 `config/concepts.yaml` 的 name 字段）

## 🔒 证据铁律（防幻觉，违反即不合格）

1. **只准引用切片中实际存在的行号**；引用格式 `file://<绝对路径>#L<起>-L<止>`，行号必须来自 slice_code.py 输出
2. **禁止断言"整个项目缺乏 X"**——切片 ≤150 行无法证明全局缺失；只能断言"切片范围内未见 X"
3. 下方输出模板的字段仅为**格式示范，不是代码证据**；所有 issue 必须能对应切片原文
4. 打分扣分必须有证据锚点支撑；无锚点的扣分最多 -5 并标注"疑似，待核实"

## 📤 输出模板（JSON）

```json
{
  "audit_summary": {
    "architectural_soundness": 85,
    "production_readiness": 70,
    "robustness_guardrails": 60
  },
  "matched_concept": "concept_xxx",
  "evidence_anchors": [
    {
      "file": "file://<切片文件绝对路径>#L<起>-L<止>",
      "issue": "<基于切片原文的问题描述，禁止照抄本模板>"
    }
  ],
  "weakness_tags": ["concept_xxx"]
}
```

## 🧠 交互提问

- 以题卡问题为纲，结合切片证据提问（例：Q001 的 Execution Loop 对照切片中的循环/工具调用实现）
- 用户回答后给出修正与建议，并将薄弱概念写入 profile（见 SOP 第 6 步）

## 依赖与整包安装

本仓库按 **1 主入口 + 5 依赖**整包安装，勿单拆或单独关闭组件；六个目录必须位于同一个 skills 父目录。以下相对路径均以本 SKILL.md 所在目录为基准。缺失组件时先明确报告降级，按下列内联规则继续可执行部分，不虚构题号、项目档案或已完成步骤。

本 skill 是 `agent-project-grill` 的可选体检依赖，仅在用户要求审查时使用。500 题卡、schema 与三维打分体系是独立语料，不读取公共 497 道题（共 557 条记录）题库。

单件安装缺主入口或其余组件时，直接按本 SKILL 的路由、证据切片、打分与复盘流程执行；无须调用缺失组件。题卡未命中按上文既有通用架构审查兜底，不用公共题库替换独立题卡。
