#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""generate_baike.py —— 从公共真理源题库生成 ai-agent-interview-240 的八股文分卷与全景索引。

输入: items.json, concepts.yaml, schema.json (来自 --bank-dir 指定的真理源题库)
输出:
  - docs/01-面试八股文/00-核心专题索引与学习路线.md (13维多标签索引与核心递进学习路线)
  - docs/01-面试八股文/01-Agent应用开发.md (280 题)
  - docs/01-面试八股文/02-八股基础.md (145 题)
  - docs/01-面试八股文/03-Transformer与大模型.md (10 题)
  - docs/01-面试八股文/04-LeetCode算法.md (25 题)
  - docs/01-面试八股文/05-反问与国企特别版.md (8 题)
  - docs/01-面试八股文/06-AI_Infra与高性能算子.md (29 题)
共计 497 题完整收录，一视同仁，每题稳定 L 锚点与解析跳转，两次生成 0 字节差异。
"""

import argparse
import hashlib
import json
import os
import re
import sys
from collections import defaultdict, Counter

DEPTH_LABEL = {1: "概念定义", 2: "原理机制", 3: "设计与方案", 4: "落地与权衡", 5: "前沿与延伸"}

DEFAULT_BANK = "/Users/caoruixin/Desktop/skills/interview-mock-skill/agent-project-grill/references/题库"
DEFAULT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DST = os.path.join(DEFAULT_ROOT, "docs", "01-面试八股文")

def compute_bank_fingerprint(bank_dir: str) -> dict:
    hasher = hashlib.sha256()
    target_files = ["items.json", "concepts.yaml", "schema.json"]
    for fname in target_files:
        p = os.path.join(bank_dir, fname)
        if os.path.isfile(p):
            with open(p, "rb") as f:
                hasher.update(f"--- FILE: {fname} ---\n".encode("utf-8"))
                hasher.update(f.read())
                hasher.update(b"\n")
    return {
        "hash": hasher.hexdigest(),
        "files": target_files
    }

def gh_anchor(text: str) -> str:
    """锚点规则与 mkdocs pymdownx.slugs.slugify 对齐"""
    t = re.sub(r"[^\w\u4e00-\u9fff\s-]", "", text)
    t = t.replace(" ", "-")
    return t

def shorten_text(text: str, max_len: int = 24) -> str:
    text = text.strip().replace("\n", " ")
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."

def main():
    parser = argparse.ArgumentParser(description="生成八股文分卷与全景索引")
    parser.add_argument("--bank-dir", default=DEFAULT_BANK, help="公共题库真理源目录")
    parser.add_argument("--dst-dir", default=DEFAULT_DST, help="分卷输出目录")
    args = parser.parse_args()

    bank_dir = os.path.abspath(args.bank_dir)
    dst_dir = os.path.abspath(args.dst_dir)
    os.makedirs(dst_dir, exist_ok=True)

    items_path = os.path.join(bank_dir, "items.json")
    if not os.path.isfile(items_path):
        print(f"[ERROR] 找不到题库文件: {items_path}", file=sys.stderr)
        sys.exit(1)

    fp_info = compute_bank_fingerprint(bank_dir)
    bank_hash = fp_info["hash"]

    with open(items_path, "r", encoding="utf-8") as f:
        items = json.load(f)

    qs = [it for it in items if it.get("kind") == "question"]
    qs_dict = {q["id"]: q for q in qs}
    print(f"[INFO] 题库真理源载入成功: 总记录 {len(items)}, 题目 {len(qs)}, 指纹 {bank_hash[:16]}...")

    # 6大分卷定义
    VOLUMES_DEF = [
        ("01-Agent应用开发.md", lambda q: q.get("major") == "二_Agent应用开发相关",
         "Agent 应用开发",
         "大厂 AI Agent 岗核心战场：宏观认知、主流框架、工具调用、Prompt、记忆、架构设计、数据库、工程落地、业务评估与性能优化"),
        ("02-八股基础.md", lambda q: q.get("major") in ("四_八股相关", "五_业务流相关", "全栈与前端工程交互"),
         "八股基础与业务流",
         "操作系统底层/网络通讯/MySQL/Redis/消息队列/Java并发/高并发秒杀业务流与双层对账补偿机制"),
        ("03-Transformer与大模型.md", lambda q: q.get("major") == "三_transformer相关",
         "Transformer 与大模型",
         "注意力机制、长上下文、KV Cache、推理优化、微调对齐"),
        ("04-LeetCode算法.md", lambda q: q.get("major") == "Leetcode相关",
         "LeetCode 与算法",
         "大厂面试手撕代码与经典算法高频题"),
        ("05-反问与国企特别版.md", lambda q: q.get("major") in ("反问", "国企特别版", "反问与国企特别版"),
         "反问与国企特别版",
         "面试反问环节设计与国企/体制内技术面试特别准备"),
        ("06-AI_Infra与高性能算子.md", lambda q: q.get("major") == "六_AI_Infra与高性能算子",
         "AI Infra 与高性能算子",
         "投机解码（EAGLE3/DFlash/Tree Attention/拒绝采样）、模型量化（AWQ/GPTQ/SmoothQuant/MoE Router）、CUDA算子开发与张量并行通信优化"),
    ]

    id_to_vol = {}
    for fname, predicate, _, _ in VOLUMES_DEF:
        for q in qs:
            if predicate(q):
                id_to_vol[q["id"]] = fname

    assert len(id_to_vol) == len(qs), f"卷分配题目数不吻合: {len(id_to_vol)} vs {len(qs)}"

    def render_question(q, cur_vol):
        qid = q["id"]
        depth = q.get("depth") or 99
        if depth >= 99:
            depth_str = "**深度**: 综合（未分级）"
        else:
            depth_label = DEPTH_LABEL.get(depth, "综合")
            depth_str = f"**深度**: {depth}/5 · {depth_label}"

        lines = [f'<a id="{qid}"></a>', f"### {qid} · {q['text']}", ""]
        lines.append(depth_str)
        if q.get("fuzzy"):
            lines.append("**定位**: 模糊归位（按语义近似归类）")
        lines.append("")

        # 同题合并提示
        if q.get("is_duplicate"):
            can_id = q.get("canonical_id", "")
            can_vol = id_to_vol.get(can_id, cur_vol)
            can_link = f"#{can_id}" if can_vol == cur_vol else f"{can_vol}#{can_id}"
            lines.append(f"> [!NOTE]\n> **同题合并条目**：本题与主题目 [{can_id}]({can_link}) 题干完全一致。核心考点、作答框架与递进演进请参考主题目 [{can_id}]({can_link})。\n")
        elif q.get("is_canonical") and q.get("duplicate_aliases"):
            alias_links = []
            for aid in q["duplicate_aliases"]:
                avol = id_to_vol.get(aid, cur_vol)
                alink = f"#{aid}" if avol == cur_vol else f"{avol}#{aid}"
                alias_links.append(f"[{aid}]({alink})")
            lines.append(f"> [!TIP]\n> **同题合并标识**：本题为权威主条目，合并同题别名：{'、'.join(alias_links)}。\n")

        minor_tag = q.get("minor") or q.get("major") or "综合考点"
        lines.append(f"> **核心考点**：考察对 `{minor_tag}` 核心机制的理解与高并发/生产工程权衡能力。")
        lines.append("")

        lines.append("**答题框架（大厂四步）**：")
        lines.append("")
        lines.append("1. **概念澄清/场景切入**")
        lines.append("2. **架构/机制设计**")
        lines.append("3. **工程权衡与坑点**")
        lines.append("4. **生产实战经验**")
        lines.append("")

        # 渲染前置与后置跳转
        rels = q.get("relations", [])
        pre_links = []
        post_links = []
        for r in rels:
            tgt_id = r.get("target")
            if tgt_id not in qs_dict:
                continue
            tgt_q = qs_dict[tgt_id]
            tgt_vol = id_to_vol.get(tgt_id, cur_vol)
            target_short = shorten_text(tgt_q["text"])
            link = f"#{tgt_id}" if tgt_vol == cur_vol else f"{tgt_vol}#{tgt_id}"
            direction = r.get("direction")
            rel_type = r.get("type", "progressive")
            type_label = "前置基础" if rel_type == "hard_prereq" else "建议递进"
            reason = r.get("reason", "")
            reason_suffix = f"：{reason}" if reason else ""

            if direction == "in":
                pre_links.append(f"[{tgt_id} · {target_short}]({link})（{type_label}{reason_suffix}）")
            elif direction == "out":
                post_links.append(f"[{tgt_id} · {target_short}]({link})（{type_label}{reason_suffix}）")

        path_parts = []
        if pre_links:
            path_parts.append("前置: " + " ｜ ".join(pre_links))
        if post_links:
            path_parts.append("后置: " + " ｜ ".join(post_links))

        if path_parts:
            lines.append("**学习路径**：" + " ｜ ".join(path_parts))
            lines.append("")

        lines.append("---")
        lines.append("")
        return "\n".join(lines)

    # ---------- 生成 6 大分卷 ----------
    for fname, predicate, title, desc in VOLUMES_DEF:
        qlist = [q for q in qs if predicate(q)]
        # 稳定排序: 先 minor，再 depth，最后 ID
        minors = defaultdict(list)
        for q in qlist:
            minors[q.get("minor") or "未归类"].append(q)

        lines = [
            f"# {title}（{len(qlist)} 题）",
            "",
            f"> 真实大厂真题 {len(qlist)} 道 · {desc}",
            "",
            f"> 题库真理源指纹：`{bank_hash[:16]}` · 来源：大厂真实面试题与高频考点；每题附深度标签、四步答题框架与双向学习路径跳转。",
            "",
            "## 目录",
            "",
        ]
        for mi in sorted(minors):
            lines.append(f"- [{mi}（{len(minors[mi])} 题）](#{gh_anchor(mi)})")
        lines.append("")
        lines.append("---")
        lines.append("")

        for mi in sorted(minors):
            sub_qs = sorted(minors[mi], key=lambda x: (x.get("depth") or 99, int(x["id"][1:]) if x["id"][1:].isdigit() else x["id"]))
            lines.append(f"## {mi}")
            lines.append("")
            lines.append(f"共 {len(sub_qs)} 题，按逻辑深度由浅入深排序。")
            lines.append("")
            for q in sub_qs:
                lines.append(render_question(q, fname))

        out_path = os.path.join(dst_dir, fname)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines).rstrip() + "\n")
        print(f"[OK] 分卷落盘: {fname} (共 {len(qlist)} 题)")

    # ---------- 生成 00-核心专题索引与学习路线.md ----------
    idx_manifest_path = os.path.join(bank_dir, "索引", "index_manifest.json")
    idx_categories = {}
    if os.path.isfile(idx_manifest_path):
        with open(idx_manifest_path, "r", encoding="utf-8") as f:
            idx_categories = json.load(f).get("categories", {})

    domain_counts = Counter(q.get("domain", "A_AGENT") for q in qs)

    idx_lines = [
        "# 全景分类索引与核心学习路线",
        "",
        f"> 公共题库真理源全量 {len(qs)} 道面试真题（指纹 `{bank_hash[:16]}`）。所有题目一视同仁，涵盖 AI Agent、高并发后端、AI Infra 与经典算法。",
        "",
        "## 🏛️ 金字塔多叉树架构导航 (Pyramid Taxonomy)",
        "",
        "本题库采用工业级三层金字塔架构组织（Root 总纲 $\\rightarrow$ L1 核心板块 $\\rightarrow$ L2 专业流派 $\\rightarrow$ L3 题目实体带深度 1~5 梯度）：",
        "",
        "| 板块代码 | L1 核心板块 | 涵盖题数 | L2 专业流派细分 | 对应分卷入口 |",
        "|:---|:---|:---|:---|:---|",
        f"| **A_AGENT** | **Agent 开发板块** | **{domain_counts.get('A_AGENT', 0)} 题** | 宏观认知 / 主流框架 / 工具调用 / Prompt工程 / 记忆设计 / 情景架构 / 向量存储 / 工程落地 / 业务评估 | [01-Agent应用开发.md](01-Agent应用开发.md) |",
        f"| **B_BACKEND** | **高并发后端板块** | **{domain_counts.get('B_BACKEND', 0)} 题** | 操作系统底层 / 计算机网络 / 数据库与缓存 / 消息队列与异步流 / Java并发核心 / 高并发秒杀业务流 | [02-八股基础.md](02-八股基础.md) |",
        f"| **I_INFRA** | **AI Infra 算子底座** | **{domain_counts.get('I_INFRA', 0)} 题** | 算子编译优化CUDA / 分布式通信AllReduce / 硬件架构与投机解码 | [06-AI_Infra与高性能算子.md](06-AI_Infra与高性能算子.md) |",
        f"| **F_FRONTEND** | **全栈与前端工程交互** | **{domain_counts.get('F_FRONTEND', 0)} 题** | 前端流式长链接交互 / 页面渲染工程化 | [02-八股基础.md](02-八股基础.md) |",
        f"| **S_ALGO** | **算法手撕与综合面试** | **{domain_counts.get('S_ALGO_GENERAL', 0)} 题** | LeetCode 高频手撕 / Transformer底座 / 反问与国企特别版 | [03-Transformer与大模型.md](03-Transformer与大模型.md) ｜ [04-LeetCode算法.md](04-LeetCode算法.md) ｜ [05-反问与国企特别版.md](05-反问与国企特别版.md) |",
        "",
        "---",
        "",
        "## 📑 13 维官方多标签索引表",
        "",
        "本题库支持跨维度多标签检索，每道真题正本唯一归入相应分卷，在此提供 13 大主题维度的快速导航：",
        "",
        "| 维度编号 | 专题索引分类 | 覆盖题数 | 核心聚焦范围 |",
        "|:---|:---|:---|:---|",
    ]

    for cat_key, cat_info in idx_categories.items():
        title = cat_info.get("title", cat_key)
        count = cat_info.get("count", 0)
        idx_lines.append(f"| `{cat_key}` | [{title}](#{gh_anchor(title)}) | **{count} 题** | 见下方详细题目列表 |")

    idx_lines.append("")
    idx_lines.append("---")
    idx_lines.append("")
    idx_lines.append("## 🧭 4 大核心领域递进学习路线")
    idx_lines.append("")
    idx_lines.append("以下精选 4 条无环递进学习主线，点击题目编号可直接跨卷跳转：")
    idx_lines.append("")

    # 4 条路线
    ROUTES = [
        ("路线一：高并发秒杀与后端基建演进", [
            ("L566", "Redis 常用数据类型"),
            ("L445", "Redis 五大数据结构底层编码与内存淘汰"),
            ("L446", "Redis 事务限制与 Lua 脚本引入"),
            ("L471", "Redis+Lua 库存原子预扣全链路"),
            ("L397", "Redis Cluster 跨 slot 处理与 Hash Tag"),
            ("L473", "预扣成功但 MQ 发送失败重试与补偿"),
            ("L352", "消息队列引入场景与削峰痛点"),
            ("L518", "消息队列异步下单削峰解耦"),
            ("L403", "秒杀场景 RabbitMQ 选型权衡"),
            ("L404", "RabbitMQ 三端防丢失机制"),
            ("L399", "Redis 与 MySQL 最终一致性与状态机 CAS"),
            ("L409", "双层对账引擎与数据自愈闭环"),
        ]),
        ("路线二：Agent Harness 沙箱与控制循环工程", [
            ("L38", "AI Coding 领域 Harness 沙箱与 Loop Engineering 概念"),
            ("L34", "基于 Harness 的自动评估与执行框架 Prompt 设计"),
            ("L39", "构建 Agent 效果评估体系与主流 Benchmark 维度"),
            ("L40", "生产环境核心监控指标（Success Rate / Latency / Cost）"),
            ("L41", "Tool Use 准确率、轨迹冗余度与召回率评测"),
            ("L622", "手撕代码：基础 Agent Loop 控制循环"),
            ("L623", "多工具统一注册接口与依赖注入"),
            ("L624", "工具非法调用与参数校验错误容错"),
            ("L625", "read_file 工具防爆与上下文保护"),
            ("L626", "模型提前退出检测与自我反思机制"),
            ("L628", "引入独立 Judge 模型客观验收任务完成度"),
        ]),
        ("路线三：生产级 RAG 知识检索与切分重排", [
            ("L59", "文档语义边界切分 vs 固定长度切分"),
            ("L422", "章节与正文父子块划分，递归字符切分逻辑"),
            ("L424", "代码库专业切分：基于 AST 与 Mapper 语义块提取"),
            ("L54", "生产级 RAG 离线 Ingestion 到在线 Retrieval 流程"),
            ("L55", "混合检索 Hybrid Search 必要性（Dense + Sparse）"),
            ("L548", "Reciprocal Rank Fusion (RRF) 加权融合工程实现"),
            ("L108", "Cross-Encoder Rerank 重排模型与 Top-K 精度优化"),
        ]),
        ("路线四：AI Infra 推测解码与模型量化前沿", [
            ("L639", "Decode 阶段 Memory Bound 特性与算力利用率瓶颈"),
            ("L638", "Speculative Decoding 投机解码加速原理"),
            ("L629", "EAGLE3 / DFlash / DSpark 架构对比（注: DSpark版本待项目核对）"),
            ("L630", "DFlash / DSpark 推理输入流与 vLLM/SGLang 集成"),
            ("L634", "EAGLE3 Proposal → Verify → Accept 三阶段机制"),
            ("L635", "Tree Proposal 拓扑生成与剪枝约束策略"),
            ("L636", "Tree Attention Mask 矩阵构造与验证阶段并行 Attention"),
            ("L637", "非 Greedy 采样下 Rejection Sampling 严格分布保真"),
            ("L646", "AWQ 与 GPTQ 核心区别与实现方式"),
            ("L648", "量化目标函数推导：输出重构误差优于单纯权重误差"),
            ("L650", "MoE 量化中专家负载不均与 Router 保留 BF16 必要性"),
        ]),
    ]

    for r_title, steps in ROUTES:
        idx_lines.append(f"### {r_title}")
        idx_lines.append("")
        step_strs = []
        for qid, q_desc in steps:
            target_vol = id_to_vol.get(qid, "01-Agent应用开发.md")
            step_strs.append(f"[{qid} · {q_desc}]({target_vol}#{qid})")
        idx_lines.append(" ➔ ".join(step_strs))
        idx_lines.append("")

    idx_lines.append("---")
    idx_lines.append("")
    idx_lines.append("## 📚 13 维分类详细题目清单")
    idx_lines.append("")

    for cat_key, cat_info in idx_categories.items():
        title = cat_info.get("title", cat_key)
        jf = os.path.join(bank_dir, "索引", cat_info.get("json_index", ""))
        idx_lines.append(f"### {title}")
        idx_lines.append("")
        if os.path.isfile(jf):
            with open(jf, "r", encoding="utf-8") as f:
                cat_data = json.load(f)
            c_items = cat_data.get("items", [])
            idx_lines.append(f"共收录 **{len(c_items)} 题**：")
            idx_lines.append("")
            for it in c_items:
                qid = it["id"]
                target_vol = id_to_vol.get(qid, "01-Agent应用开发.md")
                idx_lines.append(f"- [{qid}]({target_vol}#{qid})：{it['text']}")
        idx_lines.append("")

    index_out = os.path.join(dst_dir, "00-核心专题索引与学习路线.md")
    with open(index_out, "w", encoding="utf-8") as f:
        f.write("\n".join(idx_lines).rstrip() + "\n")
    print(f"[OK] 全景索引与学习路线落盘: {index_out}")

if __name__ == "__main__":
    main()
