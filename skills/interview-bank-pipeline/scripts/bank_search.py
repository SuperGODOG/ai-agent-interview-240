#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bank_search.py - 题库轻量级分层检索与拓扑递进树重组引擎 (方案 A: 内存三层索引加速与拓扑双向无损补齐)

设计哲学（遵循《Memory Tax》与 Raw-Evidence 原则）：
1. 零外部依赖：纯 Python 标准库（json, re, math, sys, os, argparse）。
2. 零数据污染：不改动现有 items.json 结构与 16 项回归测试。
3. 内存三层索引化架构（BankMemoryIndex - 方案 A）：
   - Layer 1: 实体与正交属性分桶 (by_id, domain_index, depth_index, minor_index) -> O(1) 实体速查与属性过滤；
   - Layer 2: 词法倒排索引 (inverted_index) -> 单词/短语倒排映射，彻底跳过不相关题目的全表扫描；
   - Layer 3: 拓扑双向无损图谱 (graph_upstream, graph_downstream) -> 内存中自动对称修复 13 处 downstream 缺失 prereq 和 45 处 prereq 缺失 downstream 的断链盲区。
4. 双输入源支持：
   - 输入源 A（简历模式）：直接输入项目描述或简历核心卖点（--query "..."）。
   - 输入源 B（工程模式）：直接输入项目 README 或画像文档路径（--file README.md），自动清洗 Markdown 杂音提取核心技术特征。
5. 板块分桶与自适应动态配额（Adaptive Domain-Partitioned Recall）：
   - 主业务战场（如 Agent，得分优势明显）：自动配额 Primary K=20；
   - 次级系统支撑（如后端高并发/缓存/存储）：自动配额 Secondary K=10；
   - 辅助选型与综合考点：自动配额 Tertiary K=3~5；
   - 无关弱相关板块自动归零拦截。
6. 宽门高召回 + 拓扑递进树重组（Progressive Question Tree Assembly）：
   - 破除文本字面限制，将低文本相关率但处于关键考点链路上的题目合法装配；
   - 每一棵专题题树包含：
     * ├── 破冰前置（Prerequisites / d1~d2）
     * 🎯 核心主干（Core Anchor / d2~d3）
     * ├── 递进深挖（Progressive Follow-ups / d3~d4）
     * └── 极限防线（Boundary & Extreme Defense / d4~d5）
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

# 板块中文名称映射
DOMAIN_NAMES = {
    "A_AGENT": "A_AGENT (大模型应用开发)",
    "B_BACKEND": "B_BACKEND (高并发后端与存储)",
    "S_ALGO_GENERAL": "S_ALGO_GENERAL (算法与综合选型)",
    "I_INFRA": "I_INFRA (底层算子与高性能计算)",
    "F_FRONTEND": "F_FRONTEND (全栈与前端工程交互)",
}

# 边界、容错、极端防线关键词
BOUNDARY_KEYWORDS = [
    "边界", "误改", "熔断", "反思", "失败", "安全", "死锁", "降级",
    "自愈", "自满", "对账", "oom", "防爆", "超时", "重试", "越权",
    "漂移", "回滚", "幂等"
]

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
        if line.startswith(">") or line.startswith("|") or line.startswith("```"):
            continue
        if "github.com" in line or line.startswith("http://") or line.startswith("https://"):
            continue
        if line.startswith("pip install") or line.startswith("npm install"):
            continue
        line = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', line)
        line = re.sub(r'!\[[^\]]*\]\([^\)]+\)', '', line)
        clean_lines.append(line)
    return " ".join(clean_lines)


_RE_EN = re.compile(r'[a-zA-Z0-9_\-\.\@]+')
_RE_CN = re.compile(r'[\u4e00-\u9fa5]+')


def tokenize(text: str) -> List[str]:
    """轻量分词：支持中英文混排、专业术语保留"""
    text = text.lower().strip()
    en_words = _RE_EN.findall(text)
    cn_chunks = _RE_CN.findall(text)

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


def extract_index_tokens(text: str) -> Set[str]:
    """为倒排索引全面提取关键词、专业术语与 n-gram"""
    text = text.lower().strip()
    en_words = _RE_EN.findall(text)
    cn_chunks = _RE_CN.findall(text)

    tokens: Set[str] = set(en_words)
    # 英文基础前缀派生（如 redisson -> redis）
    for ew in en_words:
        if len(ew) >= 5 and ew.endswith("s"):
            tokens.add(ew[:-1])

    # 中文整段与 2~3 字符 n-gram
    for chunk in cn_chunks:
        if len(chunk) <= 4:
            tokens.add(chunk)
        else:
            tokens.add(chunk)
            for i in range(len(chunk) - 1):
                tokens.add(chunk[i:i+2])
                if i + 3 <= len(chunk):
                    tokens.add(chunk[i:i+3])
    return tokens


class BankMemoryIndex:
    """
    题库内存三层索引结构（方案 A 架构实现）：
    1. 实体与正交属性分桶 (by_id, domain_index, depth_index, minor_index)
    2. 词法倒排索引 (inverted_index)
    3. 拓扑双向无损图谱 (graph_upstream, graph_downstream，自动对称修复断链)
    """

    def __init__(self, items_path: str):
        if not os.path.exists(items_path):
            raise FileNotFoundError(f"题库主文件未找到: {items_path}")

        with open(items_path, "r", encoding="utf-8") as f:
            bank = json.load(f)

        self.items_path = items_path
        self.by_id: Dict[str, Dict[str, Any]] = {}
        self.domain_index: Dict[str, Set[str]] = {}
        self.depth_index: Dict[int, Set[str]] = {}
        self.minor_index: Dict[str, Set[str]] = {}

        self.inverted_index: Dict[str, Set[str]] = {}
        self.graph_upstream: Dict[str, Set[str]] = {}
        self.graph_downstream: Dict[str, Set[str]] = {}

        # 1. 遍历题目实体，建立属性分桶与倒排索引
        for it in bank:
            if it.get("kind") != "question":
                continue
            qid = it["id"]
            self.by_id[qid] = it

            # 属性分桶
            d = it.get("domain", "")
            if d:
                self.domain_index.setdefault(d, set()).add(qid)

            dp = it.get("depth", 1)
            self.depth_index.setdefault(dp, set()).add(qid)

            mn = it.get("minor", "")
            if mn:
                self.minor_index.setdefault(mn, set()).add(qid)

            # 词法倒排索引
            tag = it.get("tag") or ""
            minor = it.get("minor") or ""
            text = it.get("text") or ""
            corpus = f"{text} {tag} {minor}"

            for tok in extract_index_tokens(corpus):
                self.inverted_index.setdefault(tok, set()).add(qid)

        # 2. 建立拓扑双向无损图（对称化修复）
        for it in self.by_id.values():
            qid = it["id"]
            for d in (it.get("downstream") or []):
                if d in self.by_id:
                    self.graph_downstream.setdefault(qid, set()).add(d)
                    self.graph_upstream.setdefault(d, set()).add(qid)

            for p in (it.get("prereq") or []):
                if p in self.by_id:
                    self.graph_upstream.setdefault(qid, set()).add(p)
                    self.graph_downstream.setdefault(p, set()).add(qid)

            for rel in (it.get("relations") or []):
                if isinstance(rel, dict):
                    t = rel.get("target")
                    if t and t in self.by_id:
                        rtype = rel.get("type", "progressive")
                        rdir = rel.get("direction", "out")
                        if rdir == "in" or rtype in ("prereq", "hard_prereq"):
                            self.graph_upstream.setdefault(qid, set()).add(t)
                            self.graph_downstream.setdefault(t, set()).add(qid)
                        else:
                            self.graph_downstream.setdefault(qid, set()).add(t)
                            self.graph_upstream.setdefault(t, set()).add(qid)

    def get_candidate_ids(
        self,
        query_tokens: Set[str],
        domain_filter: Optional[str] = None,
        depth_filter: Optional[int] = None,
        minor_filter: Optional[str] = None,
    ) -> Set[str]:
        """通过倒排索引与正交属性分桶快速求交集，缩小候选打分集"""
        if not query_tokens:
            return set()

        hits: Set[str] = set()
        for tok in query_tokens:
            if tok in self.inverted_index:
                hits.update(self.inverted_index[tok])

        if not hits:
            return set()

        # 属性过滤快速求交
        if domain_filter:
            hits = hits.intersection(self.domain_index.get(domain_filter, set()))
        if depth_filter:
            hits = hits.intersection(self.depth_index.get(depth_filter, set()))
        if minor_filter:
            matching_minors: Set[str] = set()
            for m_key, qids in self.minor_index.items():
                if minor_filter in m_key:
                    matching_minors.update(qids)
            hits = hits.intersection(matching_minors)

        return hits


# 模块级单例缓存
_MEMORY_INDEX_CACHE: Dict[str, BankMemoryIndex] = {}


def get_bank_index(items_path: str = DEFAULT_ITEMS_PATH) -> BankMemoryIndex:
    """获取或初始化题库内存索引（单例高速缓存）"""
    norm_path = os.path.normpath(items_path)
    if norm_path not in _MEMORY_INDEX_CACHE:
        _MEMORY_INDEX_CACHE[norm_path] = BankMemoryIndex(norm_path)
    return _MEMORY_INDEX_CACHE[norm_path]


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


def assemble_progressive_trees(
    scored_candidates: List[Tuple[float, Dict[str, Any]]],
    by_id: Dict[str, Dict[str, Any]],
    score_map: Dict[str, float],
    graph_upstream: Dict[str, Set[str]],
    graph_downstream: Dict[str, Set[str]],
    max_trees: int = 5,
    max_prereqs: int = 3,
    max_followups: int = 5,
    max_boundaries: int = 3,
    expand_hops: int = 2,
    domain_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    拓扑递进树重组引擎（Assembler）：
    基于对称化内存图谱，将高召回候选池中的离散题目装配成连环专题树。
    """
    global_visited: Set[str] = set()
    trees: List[Dict[str, Any]] = []

    for sc, anc in scored_candidates:
        anc_id = anc["id"]
        if anc_id in global_visited:
            continue
        if domain_filter and anc.get("domain") != domain_filter:
            continue

        tree_members: Set[str] = {anc_id}

        # 1. 向上回溯破冰前置 (Prerequisites) —— 走对称化 graph_upstream
        prereqs = []
        for pid in graph_upstream.get(anc_id, set()):
            if pid in by_id and pid not in global_visited and pid not in tree_members:
                prereqs.append(by_id[pid])
                tree_members.add(pid)

        prereqs.sort(key=lambda x: x.get("depth", 1))
        prereqs = prereqs[:max_prereqs]

        # 2. 向下深挖递进追问 (Downstream) —— 走对称化 graph_downstream 与 2-hop 扩展
        followups = []
        boundaries = []

        down_pool: Set[str] = set(graph_downstream.get(anc_id, set()))

        # 如果开启 2-hop，沿对称化下游扩展第二层
        extended_down: Set[str] = set(down_pool)
        if expand_hops >= 2:
            for did in down_pool:
                if did in by_id:
                    for d2 in graph_downstream.get(did, set()):
                        extended_down.add(d2)

        for did in extended_down:
            if did in by_id and did not in global_visited and did not in tree_members:
                item = by_id[did]
                tag = (item.get("tag", "") or "").lower()
                txt = (item.get("text", "") or "").lower()
                is_boundary = any(w in tag or w in txt for w in BOUNDARY_KEYWORDS)

                if is_boundary and item.get("depth", 1) >= 3:
                    boundaries.append(item)
                else:
                    followups.append(item)
                tree_members.add(did)

        # 排序：优先排在 query 中有分数的题，次之按深度升序
        followups.sort(key=lambda x: (-score_map.get(x["id"], 0), x.get("depth", 1)))
        boundaries.sort(key=lambda x: (-score_map.get(x["id"], 0), x.get("depth", 1)))

        followups = followups[:max_followups]
        boundaries = boundaries[:max_boundaries]

        global_visited.update(tree_members)

        # 综合树热度：主干得分 + 0.3 * 各子题在项目中的命中分
        child_score_sum = sum(score_map.get(m["id"], 0) for m in prereqs + followups + boundaries)
        tree_score = sc + 0.3 * child_score_sum

        theme_name = anc.get("minor", "核心架构")
        if theme_name and "." in theme_name:
            theme_name = theme_name.split(".", 1)[-1]

        trees.append({
            "tree_id": len(trees) + 1,
            "theme": theme_name,
            "domain": anc.get("domain", "A_AGENT"),
            "anchor": {
                "id": anc["id"],
                "score": round(sc, 2),
                "depth": anc.get("depth", 1),
                "domain": anc.get("domain", ""),
                "minor": anc.get("minor", ""),
                "text": anc.get("text", ""),
                "tag": anc.get("tag", ""),
            },
            "anchor_score": round(sc, 2),
            "tree_score": round(tree_score, 2),
            "prereqs": [{
                "id": p["id"],
                "depth": p.get("depth", 1),
                "minor": p.get("minor", ""),
                "text": p.get("text", ""),
                "tag": p.get("tag", ""),
                "score": round(score_map.get(p["id"], 0), 2)
            } for p in prereqs],
            "followups": [{
                "id": f["id"],
                "depth": f.get("depth", 1),
                "minor": f.get("minor", ""),
                "text": f.get("text", ""),
                "tag": f.get("tag", ""),
                "score": round(score_map.get(f["id"], 0), 2)
            } for f in followups],
            "boundaries": [{
                "id": b["id"],
                "depth": b.get("depth", 1),
                "minor": b.get("minor", ""),
                "text": b.get("text", ""),
                "tag": b.get("tag", ""),
                "score": round(score_map.get(b["id"], 0), 2)
            } for b in boundaries],
            "total_questions": 1 + len(prereqs) + len(followups) + len(boundaries)
        })

        if len(trees) >= max_trees:
            break

    trees.sort(key=lambda t: -t["tree_score"])
    for idx, t in enumerate(trees, 1):
        t["tree_id"] = idx
    return trees


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
    单板块题库检索核心函数（方案 A 倒排索引 + 双向图加速）：
    1. 倒排索引与属性分桶 O(1) 召回命中候选池
    2. 对称化图谱展开高价值追问与前置基础（零拓扑断链）
    3. 自动结构化分组：Tier 1 (主干题), Tier 2 (连带追问题), Tier 3 (边界防御题)
    4. 拓扑递进重组：输出连贯的专题递进树 (Progressive Trees)
    """
    index = get_bank_index(items_path)

    tokens = tokenize(query)
    expanded_tokens = expand_query_tokens(tokens)

    # 1. 倒排索引初筛候选集合
    candidate_ids = index.get_candidate_ids(
        expanded_tokens,
        domain_filter=domain,
        depth_filter=depth,
        minor_filter=minor
    )

    # 2. 仅对倒排命中的候选题目打分
    scored_items: List[Tuple[float, Dict[str, Any]]] = []
    score_map: Dict[str, float] = {}

    for qid in candidate_ids:
        item = index.by_id[qid]
        s = score_item(item, query, expanded_tokens, domain_filter=domain)
        if s > 0:
            scored_items.append((s, item))
            score_map[qid] = s

    scored_items.sort(key=lambda x: -x[0])
    anchors = scored_items[:top_k]
    anchor_ids = set(q["id"] for _, q in anchors)

    # 3. 对称化图谱拓扑扩散 (Graph Hop Expansion - 兼容扁平模式)
    direct_followups: List[Dict[str, Any]] = []
    boundary_cases: List[Dict[str, Any]] = []
    visited_ids = set(anchor_ids)

    if expand_hops > 0:
        for score, anchor in anchors:
            anc_id = anchor["id"]
            # 顺着对称化下游图获取追问
            for down_id in index.graph_downstream.get(anc_id, set()):
                if down_id in index.by_id and down_id not in visited_ids:
                    visited_ids.add(down_id)
                    target_item = index.by_id[down_id]
                    info = {
                        "id": down_id,
                        "source_id": anc_id,
                        "relation_type": "downstream (递进后置)",
                        "reason": f"从主干题 [{anc_id}] 顺延的递进深入考点",
                        "depth": target_item.get("depth", 1),
                        "minor": target_item.get("minor", ""),
                        "text": target_item.get("text", ""),
                        "tag": target_item.get("tag", ""),
                    }
                    if target_item.get("depth", 1) >= 3 and any(w in (target_item.get("tag") or "") for w in BOUNDARY_KEYWORDS):
                        boundary_cases.append(info)
                    else:
                        direct_followups.append(info)

            # 顺着对称化上游图获取前置
            for prereq_id in index.graph_upstream.get(anc_id, set()):
                if prereq_id in index.by_id and prereq_id not in visited_ids:
                    visited_ids.add(prereq_id)
                    target_item = index.by_id[prereq_id]
                    info = {
                        "id": prereq_id,
                        "source_id": anc_id,
                        "relation_type": "prereq (前置基础)",
                        "reason": f"理解主干题 [{anc_id}] 所需的前置基础",
                        "depth": target_item.get("depth", 1),
                        "minor": target_item.get("minor", ""),
                        "text": target_item.get("text", ""),
                        "tag": target_item.get("tag", ""),
                    }
                    direct_followups.append(info)

    # 包装扁平主干结果
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

    # 4. 拓扑递进树重组 (Progressive Trees Assembly)
    trees = assemble_progressive_trees(
        scored_candidates=scored_items,
        by_id=index.by_id,
        score_map=score_map,
        graph_upstream=index.graph_upstream,
        graph_downstream=index.graph_downstream,
        max_trees=5,
        expand_hops=expand_hops if expand_hops > 1 else 2,
        domain_filter=domain
    )

    return {
        "query_preview": query[:80] + ("..." if len(query) > 80 else ""),
        "domain": domain or "ALL",
        "total_anchors": len(anchor_results),
        "total_followups": len(direct_followups),
        "total_boundary": len(boundary_cases),
        "total_recalled": len(anchor_results) + len(direct_followups) + len(boundary_cases),
        "total_trees": len(trees),
        "tier1_anchors": anchor_results,
        "tier2_followups": direct_followups,
        "tier3_boundary": boundary_cases,
        "progressive_trees": trees,
    }


def search_bank_partitioned(
    query: str,
    domain_quotas: Optional[Dict[str, int]] = None,
    adaptive: bool = True,
    primary_k: int = 20,
    secondary_k: int = 10,
    tertiary_k: int = 5,
    expand_hops: int = 2,
    items_path: str = DEFAULT_ITEMS_PATH,
) -> Dict[str, Any]:
    """
    多板块自适应分桶召回与拓扑递进树重组（方案 A 极速版）：
    1. 通过倒排索引一次性计算各板块聚合得分
    2. 自适应分配 K 额度（主战场 K=20，次要支撑 K=10，辅助 K=3~5）
    3. 各板块独立召回并重组成该板块专属的递进专题题树
    """
    index = get_bank_index(items_path)

    tokens = tokenize(query)
    expanded_tokens = expand_query_tokens(tokens)

    # 倒排索引快速召回全部候选，计算各板块聚合契合度
    candidate_ids = index.get_candidate_ids(expanded_tokens)
    domain_scores: Dict[str, float] = {}

    for qid in candidate_ids:
        item = index.by_id[qid]
        d = item.get("domain")
        if not d:
            continue
        sc = score_item(item, query, expanded_tokens)
        if sc > 0:
            domain_scores[d] = domain_scores.get(d, 0.0) + sc

    # 确定各板块配额
    effective_quotas: Dict[str, int] = {}
    if domain_quotas:
        effective_quotas = domain_quotas
    elif adaptive and domain_scores:
        sorted_domains = sorted(domain_scores.items(), key=lambda x: -x[1])
        top_score = sorted_domains[0][1]
        for i, (d, sc) in enumerate(sorted_domains):
            if i == 0 and sc > 30:
                effective_quotas[d] = primary_k
            elif i == 1 and sc > 0.10 * top_score:
                effective_quotas[d] = secondary_k
            elif i == 2 and sc > 0.04 * top_score:
                effective_quotas[d] = tertiary_k
    else:
        effective_quotas = {"A_AGENT": primary_k}

    # 各板块独立召回与递进树重组
    buckets: Dict[str, Dict[str, Any]] = {}
    total_recalled_all = 0
    all_trees = []

    for d, k in effective_quotas.items():
        if k <= 0:
            continue
        res = search_bank(
            query=query,
            domain=d,
            top_k=k,
            expand_hops=expand_hops,
            items_path=items_path,
        )
        buckets[d] = res
        total_recalled_all += res["total_recalled"]
        for tr in res.get("progressive_trees", []):
            all_trees.append(tr)

    return {
        "query_preview": query[:80] + ("..." if len(query) > 80 else ""),
        "domain_scores": {d: round(s, 1) for d, s in domain_scores.items()},
        "effective_quotas": effective_quotas,
        "total_recalled_all_domains": total_recalled_all,
        "total_trees_all_domains": len(all_trees),
        "buckets": buckets,
        "all_progressive_trees": all_trees,
    }


def format_cli_output(result: Dict[str, Any], show_trees: bool = True) -> str:
    """格式化报告：支持视觉递进树与三层指标结构"""
    lines = []
    lines.append("=" * 76)
    lines.append(f"【题库轻量分层检索与拓扑递进树报告】")
    lines.append(f"检索输入摘要: {result['query_preview']}")
    lines.append("=" * 76)

    # 如果是多板块分桶结果
    if "buckets" in result:
        lines.append("\n📈 板块综合契合度与自适应配额:")
        for d, k in result["effective_quotas"].items():
            name = DOMAIN_NAMES.get(d, d)
            score = result["domain_scores"].get(d, 0.0)
            tag_name = "主业务战场" if k >= 15 else ("核心支撑战场" if k >= 8 else "辅助选型战场")
            lines.append(f"  • {name:32} [契合度 {score:6.1f}] -> 配额 K={k:2d} ({tag_name})")

        for d, res in result["buckets"].items():
            name = DOMAIN_NAMES.get(d, d)
            lines.append("\n" + "#" * 76)
            lines.append(f"### 【板块分桶】: {name}")
            lines.append("#" * 76)

            trees = res.get("progressive_trees", [])
            if show_trees and trees:
                lines.append(f"\n🌲 专题递进题目树 (Progressive Question Trees，共 {len(trees)} 组连环考点):")
                for t in trees:
                    anc = t["anchor"]
                    lines.append("\n" + "┌" + "─" * 72 + "┐")
                    lines.append(f"│ 专题树 {t['tree_id']}: {t['theme']} (综合热度: {t['tree_score']})")
                    lines.append("├" + "─" * 72 + "┤")
                    if t["prereqs"]:
                        lines.append("│ ├── 破冰前置 (Prerequisites):")
                        for p in t["prereqs"]:
                            lines.append(f"│ │     [{p['id']}] (d{p['depth']}): {p['text']}")
                    lines.append(f"│ 🎯 核心主干 (Core Anchor):")
                    lines.append(f"│       [{anc['id']}] (d{anc['depth']} | 得分 {anc['score']}): {anc['text']}")
                    if t["followups"]:
                        lines.append("│ ├── 递进深挖 (Progressive Follow-ups):")
                        for f in t["followups"]:
                            lines.append(f"│ │     [{f['id']}] (d{f['depth']}): {f['text']}")
                    if t["boundaries"]:
                        lines.append("│ └── 极限防线 (Boundary & Defense):")
                        for b in t["boundaries"]:
                            lines.append(f"│       [{b['id']}] (d{b['depth']}): {b['text']}")
                    lines.append("└" + "─" * 72 + "┘")

            lines.append(f"\n📊 板块初筛概览: 核心主干 {len(res['tier1_anchors'])} 题 | 级联追问 {len(res['tier2_followups'])} 题 | 边界防御 {len(res['tier3_boundary'])} 题")

        lines.append("\n" + "=" * 76)
        lines.append(f"📊 全板块汇总: 跨 {len(result['buckets'])} 个板块共召回 {result['total_recalled_all_domains']} 道定制题，重组成 {result.get('total_trees_all_domains', 0)} 棵完整专题递进树")
        lines.append("=" * 76)
        return "\n".join(lines)

    # 单板块结果呈现
    trees = result.get("progressive_trees", [])
    if show_trees and trees:
        lines.append(f"\n🌲 专题递进题目树 (Progressive Question Trees，共 {len(trees)} 组连环考点):")
        for t in trees:
            anc = t["anchor"]
            lines.append("\n" + "┌" + "─" * 72 + "┐")
            lines.append(f"│ 专题树 {t['tree_id']}: {t['theme']} (综合热度: {t['tree_score']})")
            lines.append("├" + "─" * 72 + "┤")
            if t["prereqs"]:
                lines.append("│ ├── 破冰前置 (Prerequisites):")
                for p in t["prereqs"]:
                    lines.append(f"│ │     [{p['id']}] (d{p['depth']}): {p['text']}")
            lines.append(f"│ 🎯 核心主干 (Core Anchor):")
            lines.append(f"│       [{anc['id']}] (d{anc['depth']} | 得分 {anc['score']}): {anc['text']}")
            if t["followups"]:
                lines.append("│ ├── 递进深挖 (Progressive Follow-ups):")
                for f in t["followups"]:
                    lines.append(f"│ │     [{f['id']}] (d{f['depth']}): {f['text']}")
            if t["boundaries"]:
                lines.append("│ └── 极限防线 (Boundary & Defense):")
                for b in t["boundaries"]:
                    lines.append(f"│       [{b['id']}] (d{b['depth']}): {b['text']}")
            lines.append("└" + "─" * 72 + "┘")

    lines.append(f"\n🎯 核心主干初筛列表（板块: {result.get('domain', 'ALL')}）:")
    if not result["tier1_anchors"]:
        lines.append("  (未找到匹配的主干题，请检查查询词或放宽分类条件)")
    else:
        for i, a in enumerate(result["tier1_anchors"], 1):
            lines.append(f"  {i}. [{a['id']}] 得分: {a['score']} | 深度: {a['depth']}/5 | 流派: {a['minor']}")
            lines.append(f"     题干: {a['text']}")

    lines.append("\n" + "=" * 76)
    lines.append(f"📊 汇总结构: 核心主干 {result['total_anchors']} 题 + 级联追问 {result['total_followups']} 题 + 边界防御 {result['total_boundary']} 题 = 共 {result['total_recalled']} 道结构化定制题")
    lines.append("=" * 76)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="题库轻量级分层检索与拓扑递进树重组引擎 (方案 A: 内存三层索引加速)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--query", "-q", help="检索查询语句或技术关键词（面向简历/对话模式）")
    group.add_argument("--file", "-f", help="项目文档路径（如 README.md 或 项目画像.md，面向代码全貌模式）")

    parser.add_argument("--domain", "-d", choices=["A_AGENT", "B_BACKEND", "S_ALGO_GENERAL", "I_INFRA", "F_FRONTEND"], help="限制单个板块")
    parser.add_argument("--buckets", "-b", help="指定多板块配额（格式如 'A_AGENT:20,B_BACKEND:10'）")
    parser.add_argument("--adaptive", "-a", action="store_true", help="启用全自动板块自适应配额分桶召回 (推荐)")
    parser.add_argument("--minor", "-m", help="过滤细分流派（如 '8.工程落地'）")
    parser.add_argument("--depth", type=int, choices=[1, 2, 3, 4, 5], help="指定题目深度")
    parser.add_argument("--top", "-k", type=int, default=10, help="主干题目初筛池上限 (默认 10)")
    parser.add_argument("--expand", "-e", type=int, default=2, help="图谱拓扑扩散步数 (0=关闭, 1=1跳, 2=2跳深入追问，默认 2)")
    parser.add_argument("--flat", action="store_true", help="仅显示平铺三层列表，不渲染递进专题树")
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

    # 解析多板块配额参数
    domain_quotas = None
    if args.buckets:
        domain_quotas = {}
        for pair in args.buckets.split(","):
            if ":" in pair:
                d, k = pair.split(":")
                domain_quotas[d.strip()] = int(k.strip())

    # 路由单板块还是多板块分桶
    if args.adaptive or domain_quotas or (not args.domain and not args.minor):
        result = search_bank_partitioned(
            query=search_query,
            domain_quotas=domain_quotas,
            adaptive=True,
            primary_k=args.top if args.top != 10 else 20,
            secondary_k=10,
            tertiary_k=5,
            expand_hops=args.expand,
            items_path=args.path,
        )
    else:
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
        print(format_cli_output(result, show_trees=not args.flat))


if __name__ == "__main__":
    main()
