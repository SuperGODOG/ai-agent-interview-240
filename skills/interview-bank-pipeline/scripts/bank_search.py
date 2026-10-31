#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bank_search.py - 题库轻量级分层检索与图谱级联引擎

设计哲学（遵循《Memory Tax》与 Raw-Evidence 原则）：
1. 零外部依赖：纯 Python 标准库（json, re, math, sys, os, argparse），执行耗时 < 15ms。
2. 零数据污染：不改动现有 items.json 结构与 16 项回归测试。
3. 双输入源支持：
   - 输入源 A（简历模式）：直接输入项目描述或简历核心卖点（--query "..."）。
   - 输入源 B（工程模式）：直接输入项目 README 或画像文档路径（--file README.md），自动清洗 Markdown 杂音提取核心技术特征。
4. 三层面试题结构化分组：
   - Tier 1: 🎯 核心主干题（Core Anchors）—— 开场必问架构大题
   - Tier 2: 🔍 核心追问题（Direct Follow-ups）—— 顺着图谱级联挂载在各自主干下的连环考点
   - Tier 3: 💡 边界防御题（Boundary & Edge Cases）—— 真实生产中的高危陷阱、环境污染、自评偏差
"""

import os
import sys
import json
import re
import argparse
from typing import List, Dict, Any, Set, Tuple, Optional

# 默认主库路径
DEFAULT_ITEMS_PATH = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../agent-project-grill/references/题库/items.json")
)

# 常见同义词/派生词映射表（轻量规则字典，辅助查询扩展）
SYNONYMS_MAP = {
    "harness": ["审核", "双智能体", "双agent", "audit", "有界循环", "guardrail"],
    "双智能体": ["harness", "审核智能体", "audit", "主智能体", "两个agent"],
    "审核": ["harness", "audit", "guardrail", "风控", "拦截", "打分偏差"],
    "有界循环": ["langgraph", "recursion_limit", "停止条件", "预算", "死循环", "反思"],
    "langgraph": ["有界循环", "stategraph", "checkpointer", "条件边"],
    "秒杀": ["lua", "预扣库存", "rabbitmq", "异步削峰", "对账", "超卖"],
    "一致性": ["延时双删", "canal", "binlog", "cache-aside", "双写"],
    "rag": ["切片", "chunking", "rerank", "重排", "混合检索", "rrf", "ragas"],
    "自进化": ["skillforge", "动态生成", "代码评测", "回归验证"],
    "渐进式披露": ["progressive disclosure", "use_skill", "按需加载", "token优化"],
    "评测": ["llm-as-a-judge", "pairwise", "配对比较", "打分漂移", "棘轮", "ratchet"],
}


def clean_markdown_content(raw_text: str) -> str:
    """提取 Markdown 文档中的核心技术事实，剔除链接、徽章、安装命令等杂音"""
    clean_lines = []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        # 过滤 Markdown 引用/表格语法/纯链接/命令
        if line.startswith(">") or line.startswith("|") or line.startswith("```"):
            continue
        if "github.com" in line or line.startswith("http://") or line.startswith("https://"):
            continue
        if line.startswith("pip install") or line.startswith("npm install"):
            continue
        # 移除 markdown 图片和超链接标签，保留文字
        line = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', line)
        line = re.sub(r'!\[[^\]]*\]\([^\)]+\)', '', line)
        clean_lines.append(line)
    return " ".join(clean_lines)


def tokenize(text: str) -> List[str]:
    """轻量分词：支持中英文混排、专业术语保留"""
    text = text.lower().strip()
    # 提取英文单词/标识符
    en_words = re.findall(r'[a-zA-Z0-9_\-\.\@]+', text)
    # 提取中文字符块
    cn_chunks = re.findall(r'[\u4e00-\u9fa5]+', text)
    
    tokens = list(en_words)
    for chunk in cn_chunks:
        if len(chunk) <= 4:
            tokens.append(chunk)
        else:
            tokens.append(chunk)
            for i in range(len(chunk) - 1):
                tokens.append(chunk[i:i+2])
                if i + 3 <= len(chunk):
                    tokens.append(chunk[i:i+3])
    return list(set(tokens))


def expand_query_tokens(tokens: List[str]) -> Set[str]:
    """利用轻量映射表扩展派生词"""
    expanded = set(tokens)
    for tok in tokens:
        for k, syns in SYNONYMS_MAP.items():
            if k in tok or tok in k:
                expanded.update(syns)
    return expanded


def score_item(item: Dict[str, Any], query_raw: str, query_tokens: Set[str], domain_filter: Optional[str] = None) -> float:
    """对单道题目进行多维加权打分"""
    if item.get("kind") != "question":
        return 0.0

    domain = item.get("domain", "")
    if domain_filter and domain != domain_filter:
        return 0.0

    tag = (item.get("tag") or "").lower()
    text = (item.get("text") or "").lower()
    minor = (item.get("minor") or "").lower()
    raw_lower = query_raw.lower()

    score = 0.0

    # 1. 完整短语匹配奖励 (Phrase Match Boost)
    if len(raw_lower) >= 2 and len(raw_lower) <= 50:
        if raw_lower in tag:
            score += 15.0
        elif raw_lower in text:
            score += 8.0

    # 2. Token 加权匹配
    matched_tokens = 0
    for tok in query_tokens:
        tok_score = 0.0
        if tok in tag:
            tok_score += 4.0
        elif tok in minor:
            tok_score += 3.0
        elif tok in text:
            tok_score += 1.5

        if tok_score > 0:
            score += tok_score
            matched_tokens += 1

    # 3. 覆盖度奖励 (Coverage Ratio Boost)
    if matched_tokens > 0 and query_tokens:
        coverage = matched_tokens / len(query_tokens)
        score *= (1.0 + coverage)

        # 4. 深度偏好：仅在有匹配命中时，深度 2~4 的核心大题给予微调权重
        depth = item.get("depth", 1)
        if depth in [2, 3]:
            score += 0.5

    return score


def search_bank(
    query: str,
    domain: Optional[str] = None,
    minor: Optional[str] = None,
    depth: Optional[int] = None,
    top_k: int = 10,
    expand_hops: int = 1,
    items_path: str = DEFAULT_ITEMS_PATH,
) -> Dict[str, Any]:
    """
    题库检索核心函数：
    1. 粗排加权打分获取 Top-K 候选池
    2. 沿着图谱边（downstream / prereq / relations）展开高价值追问题
    3. 自动结构化分组：Tier 1 (主干题), Tier 2 (连带追问题), Tier 3 (边界防御题)
    """
    if not os.path.exists(items_path):
        raise FileNotFoundError(f"题库主文件未找到: {items_path}")

    with open(items_path, "r", encoding="utf-8") as f:
        bank = json.load(f)

    by_id = {item["id"]: item for item in bank if "id" in item}

    tokens = tokenize(query)
    expanded_tokens = expand_query_tokens(tokens)

    # 第一阶段：文本加权打分
    scored_items: List[Tuple[float, Dict[str, Any]]] = []
    for item in bank:
        if depth is not None and item.get("depth") != depth:
            continue
        if minor is not None and minor not in (item.get("minor") or ""):
            continue

        s = score_item(item, query, expanded_tokens, domain_filter=domain)
        if s > 0:
            scored_items.append((s, item))

    scored_items.sort(key=lambda x: -x[0])
    anchors = scored_items[:top_k]

    anchor_ids = set(q["id"] for _, q in anchors)

    # 第二阶段：图谱拓扑扩散 (Graph Hop Expansion)
    direct_followups: List[Dict[str, Any]] = []
    boundary_cases: List[Dict[str, Any]] = []
    visited_ids = set(anchor_ids)

    if expand_hops > 0:
        for score, anchor in anchors:
            # 1. 递归向下找后置递进题 (downstream)
            for down_id in (anchor.get("downstream") or []):
                if isinstance(down_id, str) and down_id in by_id and down_id not in visited_ids:
                    visited_ids.add(down_id)
                    target_item = by_id[down_id]
                    info = {
                        "id": down_id,
                        "source_id": anchor["id"],
                        "relation_type": "downstream (递进后置)",
                        "reason": f"从主干题 [{anchor['id']}] 顺延的递进深入考点",
                        "depth": target_item.get("depth", 1),
                        "minor": target_item.get("minor", ""),
                        "text": target_item.get("text", ""),
                        "tag": target_item.get("tag", ""),
                    }
                    if target_item.get("depth", 1) >= 3 and any(w in (target_item.get("tag") or "") for w in ["边界", "误改", "熔断", "反思", "失败", "安全"]):
                        boundary_cases.append(info)
                    else:
                        direct_followups.append(info)

            # 2. 查找双向关联题 (relations)
            for rel in (anchor.get("relations") or []):
                rel_id = rel.get("target") if isinstance(rel, dict) else rel
                rel_reason = rel.get("reason") if isinstance(rel, dict) else "知识图谱关联延伸"
                if rel_id and rel_id in by_id and rel_id not in visited_ids:
                    visited_ids.add(rel_id)
                    target_item = by_id[rel_id]
                    info = {
                        "id": rel_id,
                        "source_id": anchor["id"],
                        "relation_type": "relation (关联延伸)",
                        "reason": rel_reason,
                        "depth": target_item.get("depth", 1),
                        "minor": target_item.get("minor", ""),
                        "text": target_item.get("text", ""),
                        "tag": target_item.get("tag", ""),
                    }
                    direct_followups.append(info)

            # 3. 前置基础支撑题 (prereq)
            for prereq_id in (anchor.get("prereq") or []):
                if isinstance(prereq_id, str) and prereq_id in by_id and prereq_id not in visited_ids:
                    visited_ids.add(prereq_id)
                    target_item = by_id[prereq_id]
                    info = {
                        "id": prereq_id,
                        "source_id": anchor["id"],
                        "relation_type": "prereq (前置基础)",
                        "reason": f"理解主干题 [{anchor['id']}] 所需的前置基础",
                        "depth": target_item.get("depth", 1),
                        "minor": target_item.get("minor", ""),
                        "text": target_item.get("text", ""),
                        "tag": target_item.get("tag", ""),
                    }
                    direct_followups.append(info)

    # 包装主干结果
    anchor_results = []
    for sc, q in anchors:
        anchor_results.append({
            "id": q["id"],
            "score": round(sc, 2),
            "depth": q.get("depth", 1),
            "domain": q.get("domain", ""),
            "minor": q.get("minor", ""),
            "text": q.get("text", ""),
            "tag": q.get("tag", ""),
        })

    return {
        "query_preview": query[:80] + ("..." if len(query) > 80 else ""),
        "total_anchors": len(anchor_results),
        "total_followups": len(direct_followups),
        "total_boundary": len(boundary_cases),
        "total_recalled": len(anchor_results) + len(direct_followups) + len(boundary_cases),
        "tier1_anchors": anchor_results,
        "tier2_followups": direct_followups,
        "tier3_boundary": boundary_cases,
    }


def format_cli_output(result: Dict[str, Any]) -> str:
    """格式化为结构化三层面试题单报告"""
    lines = []
    lines.append("=" * 72)
    lines.append(f"【题库轻量分层检索与拓扑图谱报告】")
    lines.append(f"检索输入摘要: {result['query_preview']}")
    lines.append("=" * 72)

    lines.append("\n🎯 【第一层：核心主干题（Core Anchors）】（开场必问核心架构与业务系统）:")
    if not result["tier1_anchors"]:
        lines.append("  (未找到匹配的主干题，请检查查询词或放宽分类条件)")
    else:
        for i, a in enumerate(result["tier1_anchors"], 1):
            lines.append(f"  {i}. [{a['id']}] 得分: {a['score']} | 深度: {a['depth']}/5 | 流派: {a['minor']}")
            lines.append(f"     题干: {a['text']}")
            if a.get("tag"):
                lines.append(f"     标签: {a['tag']}")

    lines.append("\n🔍 【第二层：直接追问题（Direct Follow-ups）】（顺着图谱深入考察原理机制）:")
    if not result["tier2_followups"]:
        lines.append("  (无图谱级联追问)")
    else:
        for i, c in enumerate(result["tier2_followups"], 1):
            lines.append(f"  {i}. [{c['id']}] 来源: {c['source_id']} ({c['relation_type']}) | 深度: {c['depth']}/5 | 流派: {c['minor']}")
            lines.append(f"     依据: {c['reason']}")
            lines.append(f"     追问: {c['text']}")

    if result["tier3_boundary"]:
        lines.append("\n💡 【第三层：边界与防御延伸题（Boundary & Edge Cases）】（考察高危陷阱与故障防御）:")
        for i, b in enumerate(result["tier3_boundary"], 1):
            lines.append(f"  {i}. [{b['id']}] 来源: {b['source_id']} | 深度: {b['depth']}/5 | 流派: {b['minor']}")
            lines.append(f"     高危维度: {b['reason']}")
            lines.append(f"     题干: {b['text']}")

    lines.append("\n" + "=" * 72)
    lines.append(f"📊 汇总结构: 核心主干 {result['total_anchors']} 题 + 级联追问 {result['total_followups']} 题 + 边界防御 {result['total_boundary']} 题 = 共 {result['total_recalled']} 道结构化定制题")
    lines.append("=" * 72)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="题库轻量级分层检索与图谱级联引擎")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--query", "-q", help="检索查询语句或技术关键词（面向简历/对话模式）")
    group.add_argument("--file", "-f", help="项目文档路径（如 README.md 或 项目画像.md，面向代码全貌模式）")

    parser.add_argument("--domain", "-d", choices=["A_AGENT", "B_BACKEND", "S_ALGO_GENERAL", "I_INFRA", "F_FRONTEND"], help="限制板块")
    parser.add_argument("--minor", "-m", help="过滤细分流派（如 '8.工程落地'）")
    parser.add_argument("--depth", type=int, choices=[1, 2, 3, 4, 5], help="指定题目深度")
    parser.add_argument("--top", "-k", type=int, default=10, help="主干题目初筛池上限 (默认 10)")
    parser.add_argument("--expand", "-e", type=int, default=1, choices=[0, 1], help="是否进行图谱拓扑扩散追问 (0=关闭, 1=开启)")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出供 Agent 程序化调用")
    parser.add_argument("--path", default=DEFAULT_ITEMS_PATH, help="指定 items.json 路径")

    args = parser.parse_args()

    # 处理输入源
    if args.file:
        if not os.path.exists(args.file):
            print(f"[ERROR] 指定的文件不存在: {args.file}", file=sys.stderr)
            sys.exit(1)
        with open(args.file, "r", encoding="utf-8", errors="ignore") as f:
            raw_content = f.read()
        search_query = clean_markdown_content(raw_content)
    else:
        search_query = args.query

    result = search_bank(
        query=search_query,
        domain=args.domain,
        minor=args.minor,
        depth=args.depth,
        top_k=args.top,
        expand_hops=args.expand,
        items_path=args.path,
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_cli_output(result))


if __name__ == "__main__":
    main()
