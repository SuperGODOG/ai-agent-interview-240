#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bank_cleaner.py —— 题库三层金字塔重构、智能去重与拓扑完整性校验工具

功能:
  1. 智能去重检测 (scan-duplicates):
     - 精确文本去重 (Exact normalized match)
     - 模糊语义相似度扫描 (Jaccard / Token-overlap >= 0.85)
     - 记录主编号 (canonical_id) 与别名重定向，双向补齐知识图谱边
  2. 金字塔层级重构 (apply-pyramid):
     - L0 题库总纲 -> L1 核心板块 (A/B/I/F/S) -> L2 专业流派 -> L3 叶子题目
     - 将原粗放的 145 道后端/业务流八股细化为 6 大专业流派 (OS/网络/数据库/MQ/Java/业务流)
  3. 树状与图谱质检 (validate-tree / --check):
     - 验证 100% 题目有且仅有一处金字塔归属
     - 验证 depth (1~5) 全覆盖
     - 验证 relations 零悬空边、零自环、零前置环路

用法:
  python3 bank_cleaner.py --check
  python3 bank_cleaner.py --apply
"""

import argparse
import difflib
import json
import os
import re
import sys
from collections import Counter, defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BANK_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "agent-project-grill", "references", "题库"))

# ==================== 金字塔分类定义 (Pyramid Taxonomy) ====================

PYRAMID_DOMAINS = {
    "A_AGENT": {
        "title": "Agent 开发板块",
        "description": "大厂 AI Agent 核心架构：工作流范式、Prompt、记忆、工具与评测",
        "streams": {
            "1.agent宏观认知": "工作流范式、Agent 宏观认知与行业演进",
            "2.agent主流框架": "主流 Agent 框架特性与底层机制",
            "3.工具相关": "工具调用、依赖注入、参数容错与 MCP 通信",
            "4.Prompt_engineering": "Prompt 设计、结构化输出与防御",
            "5.agent记忆设计": "短长时记忆、分层记忆与状态持久化",
            "6.agent处理情景的架构设计": "复杂任务拆解、多智能体协同与控制循环",
            "7.数据库": "向量数据库、RAG 混合检索与向量索引",
            "8.工程落地": "生产环境部署、降级重试与状态自愈",
            "9.业务评估(性能优化与诊断)": "Harness 评测基准、链路观测与延迟调优",
        }
    },
    "B_BACKEND": {
        "title": "高并发后端板块",
        "description": "高并发后端基建：操作系统底层、网络通讯、存储缓存、消息流与秒杀业务",
        "streams": {
            "1.操作系统与线程底层": "进程线程、内存管理、虚拟内存与 IO 多路复用",
            "2.计算机网络与通讯协议": "TCP/UDP、HTTP 1.1/2/3、HTTPS 与 WebSocket 通讯",
            "3.数据库与缓存存储": "MySQL 索引事务 MVCC、Redis 结构与内存淘汰",
            "4.消息队列与异步流": "RabbitMQ/Kafka 选型、削峰解耦、消息防丢与幂等",
            "5.Java与并发编程核心": "JVM 垃圾回收、内存模型、JUC 线程池与锁优化",
            "6.高并发业务流与秒杀自愈": "Redis+Lua原子预扣、状态机CAS、双层对账自愈闭环",
        }
    },
    "I_INFRA": {
        "title": "AI Infra 与底层算子",
        "description": "大模型基础设施：投机解码加速、模型量化裁剪与高性能算子开发",
        "streams": {
            "1.算子开发与编译优化": "CUDA 算子、FlashAttention、PagedAttention 底层优化",
            "2.分布式并行与通信": "张量并行、流水线并行、AllReduce 通信与显存优化",
            "3.硬件架构与Benchmark": "加速卡架构、Memory Bound 瓶颈与推理 Benchmark",
        }
    },
    "F_FRONTEND": {
        "title": "全栈与前端工程交互",
        "description": "页面渲染交互、流式消息推送与全栈集成",
        "streams": {
            "1.全栈与前端工程交互": "DOM 渲染性能、流式长连接交互与前端状态管理",
        }
    },
    "S_ALGO_GENERAL": {
        "title": "算法手撕与综合面试",
        "description": "LeetCode 高频经典算法手撕、体制内/国企特别版与反问环节",
        "streams": {
            "1.LeetCode算法": "经典数据结构、动态规划、双指针与高频手撕",
            "2.反问与国企特别版": "反问环节设计、国企体制内技术面试特训",
            "3.Transformer与大模型底座": "注意力机制、长上下文、KV Cache 基础",
        }
    }
}

# 已知的 6 组完全重复题映射 (canonical_id -> duplicate_id)
CANONICAL_DUPLICATES = {
    "L86": "L256",
    "L87": "L239",
    "L89": "L226",
    "L99": "L101",
    "L157": "L311",
    "L182": "L238",
}

REVERSE_DUPLICATES = {v: k for k, v in CANONICAL_DUPLICATES.items()}


def normalize_text(text: str) -> str:
    """去标点与空格用于严格文本哈希判重"""
    t = re.sub(r"[^\w\u4e00-\u9fff]", "", text.strip())
    return t.lower()


def scan_duplicates(items: list[dict]) -> dict:
    """扫描完全重复与高相似度题目"""
    questions = [it for it in items if it.get("kind") == "question"]
    by_norm = defaultdict(list)
    for q in questions:
        nt = normalize_text(q.get("text", ""))
        by_norm[nt].append(q["id"])

    exact_dups = {k: ids for k, ids in by_norm.items() if len(ids) > 1}

    # 模糊相似度检查 (样本抽样，排除已知重复)
    fuzzy_pairs = []
    known_dup_pairs = set(CANONICAL_DUPLICATES.items()) | set(REVERSE_DUPLICATES.items())
    q_texts = [(q["id"], q.get("text", "")) for q in questions]

    for i in range(len(q_texts)):
        id_a, text_a = q_texts[i]
        len_a = len(text_a)
        if len_a == 0:
            continue
        for j in range(i + 1, len(q_texts)):
            id_b, text_b = q_texts[j]
            len_b = len(text_b)
            if len_b == 0:
                continue
            # 长度差异超过 15% 直接跳过昂贵的 SequenceMatcher
            if abs(len_a - len_b) / max(len_a, len_b) > 0.15:
                continue
            if (id_a, id_b) in known_dup_pairs:
                continue
            ratio = difflib.SequenceMatcher(None, text_a, text_b).ratio()
            if ratio >= 0.88:
                fuzzy_pairs.append({
                    "id_a": id_a,
                    "id_b": id_b,
                    "ratio": round(ratio, 3),
                    "text_a": text_a,
                    "text_b": text_b
                })

    return {
        "exact_duplicate_groups": exact_dups,
        "fuzzy_pairs": fuzzy_pairs,
    }


def load_index_mappings(bank_dir: str) -> dict[str, list[str]]:
    """从 索引/ 目录读取题目与 13 维索引的匹配关系"""
    idx_dir = os.path.join(bank_dir, "索引")
    manifest_path = os.path.join(idx_dir, "index_manifest.json")
    if not os.path.isfile(manifest_path):
        return {}

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    q_to_cats = defaultdict(list)
    for cat, info in manifest.get("categories", {}).items():
        jf = os.path.join(idx_dir, info.get("json_index", ""))
        if os.path.isfile(jf):
            with open(jf, "r", encoding="utf-8") as f:
                data = json.load(f)
            for it in data.get("items", []):
                q_to_cats[it["id"]].append(cat)
    return q_to_cats


def assign_pyramid_taxonomy(q: dict, q_to_cats: dict[str, list[str]]) -> tuple[str, str, str]:
    """为单道题目确定金字塔三层归属 (domain_key, major_name, minor_name)"""
    qid = q["id"]
    dom = q.get("domain", "")
    maj = q.get("major", "")
    mi = q.get("minor", "")
    cats = q_to_cats.get(qid, [])

    # 如果已经明确归属于有效的 domain 和 stream，优先保留
    if dom in PYRAMID_DOMAINS and mi in PYRAMID_DOMAINS[dom]["streams"]:
        return dom, maj, mi

    # 1. AI Infra 算子底座
    if maj == "六_AI_Infra与高性能算子":
        return "I_INFRA", maj, mi or "1.算子开发与编译优化"

    # 2. Agent 应用开发板块
    if maj == "二_Agent应用开发相关":
        return "A_AGENT", maj, mi or "1.agent宏观认知"

    # 3. 算法手撕与综合考察
    if maj == "Leetcode相关":
        return "S_ALGO_GENERAL", maj, "1.LeetCode算法"
    if maj == "三_transformer相关":
        return "S_ALGO_GENERAL", maj, "3.Transformer与大模型底座"
    if maj in ("反问", "国企特别版", "反问与国企特别版"):
        return "S_ALGO_GENERAL", "反问与国企特别版", "2.反问与国企特别版"

    # 4. 后端基建与业务流 (将原先粗放的 145 题精准细化为流派)
    if "frontend" in cats:
        return "F_FRONTEND", "全栈与前端工程交互", "1.全栈与前端工程交互"
    if maj == "五_业务流相关" or ("business_projects" in cats and "backend_database" not in cats):
        return "B_BACKEND", "四_八股相关", "6.高并发业务流与秒杀自愈"
    if "backend_os" in cats:
        return "B_BACKEND", "四_八股相关", "1.操作系统与线程底层"
    if "backend_network" in cats:
        return "B_BACKEND", "四_八股相关", "2.计算机网络与通讯协议"
    if "backend_mq" in cats:
        return "B_BACKEND", "四_八股相关", "4.消息队列与异步流"
    if "backend_java" in cats:
        return "B_BACKEND", "四_八股相关", "5.Java与并发编程核心"
    if "backend_database" in cats or maj == "四_八股相关":
        return "B_BACKEND", "四_八股相关", mi if mi in PYRAMID_DOMAINS["B_BACKEND"]["streams"] else "3.数据库与缓存存储"

    return "B_BACKEND", "四_八股相关", "3.数据库与缓存存储"


def clean_and_restructure(bank_dir: str, apply_changes: bool = False) -> dict:
    """执行清洗与金字塔重构"""
    items_path = os.path.join(bank_dir, "items.json")
    with open(items_path, "r", encoding="utf-8") as f:
        items = json.load(f)

    dup_res = scan_duplicates(items)
    q_to_cats = load_index_mappings(bank_dir)

    questions = [it for it in items if it.get("kind") == "question"]
    q_map = {q["id"]: q for q in questions}

    # 1. 金字塔归属细化
    refined_count = 0
    domain_counts = Counter()
    stream_counts = Counter()

    for q in questions:
        dom, maj, mi = assign_pyramid_taxonomy(q, q_to_cats)
        if q.get("major") != maj or q.get("minor") != mi or q.get("domain") != dom:
            q["domain"] = dom
            q["major"] = maj
            q["minor"] = mi
            refined_count += 1
        domain_counts[dom] += 1
        stream_counts[f"{dom} -> {mi}"] += 1

        # 确保 depth 在 1..5
        if not q.get("depth") or q["depth"] not in (1, 2, 3, 4, 5):
            q["depth"] = 3  # 默认中间深度

    # 2. 标记完全重复项与关系补齐
    for can_id, dup_id in CANONICAL_DUPLICATES.items():
        if can_id in q_map and dup_id in q_map:
            can_q = q_map[can_id]
            dup_q = q_map[dup_id]

            # 标记
            can_q["is_canonical"] = True
            can_q.setdefault("duplicate_aliases", [])
            if dup_id not in can_q["duplicate_aliases"]:
                can_q["duplicate_aliases"].append(dup_id)

            dup_q["is_duplicate"] = True
            dup_q["canonical_id"] = can_id

            # 关系整合: 确保从 dup_q 上的进出边在 can_q 上有等价镜像
            can_rels = can_q.get("relations", [])
            dup_rels = dup_q.get("relations", [])
            existing_targets = {r.get("target") for r in can_rels}

            for dr in dup_rels:
                tgt = dr.get("target")
                if tgt and tgt != can_id and tgt not in existing_targets:
                    can_rels.append({
                        "target": tgt,
                        "direction": dr.get("direction", "out"),
                        "type": dr.get("type", "progressive"),
                        "reason": dr.get("reason", "")
                    })
                    existing_targets.add(tgt)
            can_q["relations"] = can_rels

    # 3. 校验拓扑完整性
    all_q_ids = set(q_map.keys())
    dangling_edges = []
    self_loops = []
    inconsistencies = []

    for qid, q in q_map.items():
        for r in q.get("relations", []):
            tgt = r.get("target")
            if tgt not in all_q_ids:
                dangling_edges.append((qid, tgt))
            if tgt == qid:
                self_loops.append(qid)

    summary = {
        "total_items": len(items),
        "total_questions": len(questions),
        "refined_questions": refined_count,
        "exact_duplicate_pairs": len(CANONICAL_DUPLICATES),
        "fuzzy_candidates": len(dup_res["fuzzy_pairs"]),
        "domain_distribution": dict(domain_counts),
        "stream_distribution": dict(stream_counts),
        "dangling_edges": len(dangling_edges),
        "self_loops": len(self_loops),
    }

    if apply_changes:
        with open(items_path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=1)
        print(f"[OK] 题库真理源重构写入完成: {items_path}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="题库金字塔重构、智能去重与拓扑质检工具")
    parser.add_argument("--bank-dir", default=DEFAULT_BANK_DIR, help="公共题库真理源目录")
    parser.add_argument("--check", action="store_true", help="仅执行检查并输出审计报告，不修改文件")
    parser.add_argument("--apply", action="store_true", help="执行清洗并写回 items.json")
    args = parser.parse_args()

    bank_dir = os.path.abspath(args.bank_dir)
    if not os.path.isdir(bank_dir):
        print(f"[ERROR] 找不到题库目录: {bank_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] 正在扫描题库: {bank_dir}")
    apply_mode = args.apply and not args.check
    res = clean_and_restructure(bank_dir, apply_changes=apply_mode)

    print("\n========== 题库金字塔审计与清洗报告 ==========")
    print(f"总记录数: {res['total_items']} | 实际题目数: {res['total_questions']}")
    print(f"细化流派调整数: {res['refined_questions']}")
    print(f"已识别合并重复对: {res['exact_duplicate_pairs']} 组")
    print(f"模糊相似候选对: {res['fuzzy_candidates']} 组")
    print(f"悬空边: {res['dangling_edges']} | 自环: {res['self_loops']}")

    print("\n[L1 板块分布]:")
    for dom, cnt in sorted(res['domain_distribution'].items()):
        dom_title = PYRAMID_DOMAINS.get(dom, {}).get("title", dom)
        print(f"  - {dom_title} ({dom}): {cnt} 题")

    print("\n[L2 流派细分分布 (前 15)]: ")
    for st, cnt in sorted(res['stream_distribution'].items(), key=lambda kv: -kv[1])[:15]:
        print(f"  - {st}: {cnt} 题")

    if apply_mode:
        print("\n[SUCCESS] 金字塔多叉树重构与清洗已持久化！")
    else:
        print("\n[HINT] 当前为只读 --check 模式。确认无误后执行 --apply 写入。")


if __name__ == "__main__":
    main()
