#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Agent Review Audit v3.1 Precision Router

v3.1 修复（多 Agent 评审）:
  1. 英文关键词改词边界正则匹配（\b），杜绝短英文词子串误伤（如 rm 命中 norm）
  2. 短英文关键词(<3字符)默认忽略，白名单显式放行
  3. 扫描跳过 .git/node_modules/dist 等噪音目录，文件数/大小封顶
  4. 读取项目 .agent-audit/profile.json 薄弱概念加权（复习闭环）
  5. 输出 Top3 概念候选 + 分数；出题卡从有卡的候选里按序取，空卡概念自动跳过
  6. 空卡/低置信度兜底：通用架构审查

用法: python3 route_project.py --path <代码文件或目录>
"""
import sys
import os
import json
import re
import yaml
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(SCRIPT_DIR)
CONCEPTS_YAML_PATH = os.path.join(SKILL_ROOT, "config", "concepts.yaml")

CONFIDENCE_FLOOR = 3.0
SKIP_DIRS = {".git", "node_modules", "dist", "build", "__pycache__", ".venv", "venv",
             "target", ".idea", ".vscode", ".agent-audit"}
SCAN_EXTS = (".py", ".js", ".ts", ".jsx", ".tsx", ".vue", ".md", ".json", ".java",
             ".go", ".yml", ".yaml")
MAX_FILES = 300
MAX_FILE_SIZE = 500_000
ASCII_MIN_LEN = 3  # 纯英文关键词短于该长度默认忽略
ALLOWED_SHORT = {"kv", "io", "os"}  # 仅 2 字符关键词需要显式放行


def load_concepts():
    if os.path.exists(CONCEPTS_YAML_PATH):
        with open(CONCEPTS_YAML_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}


def make_matcher(kw):
    """英文关键词 -> 词边界正则；中文/混合 -> 子串匹配"""
    if re.fullmatch(r"[A-Za-z0-9\-\.]+", kw):
        if len(kw) < ASCII_MIN_LEN and kw.lower() not in ALLOWED_SHORT:
            return None
        return re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)
    return re.compile(re.escape(kw), re.IGNORECASE)


def scan_file_anchors(file_path, matchers):
    anchors = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception:
        return anchors
    for idx, line in enumerate(lines, 1):
        for kw, m in matchers:
            if m.search(line):
                start = max(1, idx - 2)
                end = min(len(lines), idx + 5)
                anchors.append({
                    "file": file_path,
                    "matched_line": idx,
                    "line_range": f"L{start}-L{end}",
                    "keyword": kw,
                    "snippet": "".join(lines[start - 1:end]).strip(),
                })
                if len(anchors) >= 2:
                    return anchors
    return anchors


def collect_files(target_path):
    files = []
    if os.path.isfile(target_path):
        try:
            return [target_path] if os.path.getsize(target_path) <= MAX_FILE_SIZE else []
        except OSError:
            return []
    for root, dirs, names in os.walk(target_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in names:
            if not fn.endswith(SCAN_EXTS):
                continue
            p = os.path.join(root, fn)
            try:
                if os.path.getsize(p) > MAX_FILE_SIZE:
                    continue
            except OSError:
                continue
            files.append(p)
            if len(files) >= MAX_FILES:
                return files
    return files


def load_weak_tags(target_path):
    pf = os.path.join(target_path, ".agent-audit", "profile.json")
    try:
        return set(json.load(open(pf, encoding="utf-8")).get("weakness_tags", []))
    except Exception:
        return set()


def route_project_advanced(target_path):
    concepts_data = load_concepts()
    weak = load_weak_tags(target_path)
    matchers = {}
    for cid, info in concepts_data.items():
        ms = []
        for kw in info.get("keywords", []):
            m = make_matcher(kw)
            if m is not None:
                ms.append((kw, m))
        matchers[cid] = ms

    scores, anchors_by = {}, {}
    for f_path in collect_files(target_path):
        for cid, ms in matchers.items():
            if not ms:
                continue
            anc = scan_file_anchors(f_path, ms)
            if anc:
                scores[cid] = scores.get(cid, 0) + len(anc) * 3.5
                anchors_by.setdefault(cid, []).extend(anc[:2])
    for cid in weak:
        scores[cid] = scores.get(cid, 0) + 5.0

    ranked = sorted(scores.items(), key=lambda x: -x[1])
    if not ranked or ranked[0][1] < CONFIDENCE_FLOOR:
        return {
            "matched_concept_id": None,
            "concept_name": "通用架构审查",
            "confidence_score": 0.0,
            "target_cards": [],
            "candidates": [],
            "evidence_anchors": [],
            "status": "无高置信概念匹配，按通用架构审查执行（rubrics 三维打分，不强行出题）",
        }

    candidates = [{"concept_id": cid, "name": concepts_data[cid].get("name", cid),
                   "score": round(s, 2)} for cid, s in ranked[:3]]
    best_id = ranked[0][0]
    cards, card_source = [], None
    for cid, _s in ranked:
        cl = concepts_data[cid].get("cards", [])
        if cl:
            card_source, cards = cid, cl[:3]
            break
    matched_anchors = anchors_by.get(best_id, [])[:2]
    if card_source is None:
        return {
            "matched_concept_id": best_id,
            "concept_name": concepts_data[best_id].get("name", best_id),
            "confidence_score": round(ranked[0][1], 2),
            "target_cards": [],
            "candidates": candidates,
            "evidence_anchors": matched_anchors,
            "status": f"命中概念但题卡为空，按该概念核心审查维度提问（{concepts_data[best_id].get('name', '')}）",
        }
    return {
        "matched_concept_id": best_id,
        "concept_name": concepts_data[best_id].get("name", best_id),
        "confidence_score": round(ranked[0][1], 2),
        "target_cards": cards,
        "card_source_concept": card_source,
        "candidates": candidates,
        "evidence_anchors": matched_anchors,
        "status": "ok",
    }


def main():
    parser = argparse.ArgumentParser(description="Agent Review Audit v3.1 Precision Router")
    parser.add_argument("--path", type=str, required=True, help="Path to code file or project dir")
    args = parser.parse_args()
    res = route_project_advanced(args.path)
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
