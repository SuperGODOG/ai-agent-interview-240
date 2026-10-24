#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验 categories/ 下递归细分后的文件: 题数 + 文本逐字保留 (对照 classified + items)

用法: python3 verify_categories.py [文件相对路径...]   # 缺省=全部
"""
import json
import os
import re
import sys

ROOT = os.environ.get("INTERVIEW_WORKSPACE") or (os.path.expanduser("~/.interview-workbench") if os.path.isdir(os.path.expanduser("~/.interview-workbench")) else os.path.dirname(os.path.abspath(__file__)))
CAT_DIR = os.path.join(ROOT, "categories")
CLS_DIR = os.path.join(ROOT, "batches", "classified")
ITEMS_JSON = os.path.join(ROOT, "items.json")

Q_RE = re.compile(r"^\d+\.\s+(.+)$")


def expected_map():
    items = json.load(open(ITEMS_JSON, encoding="utf-8"))
    classified = {}
    for cf in os.listdir(CLS_DIR):
        if not cf.endswith(".json"):
            continue
        for c in json.load(open(os.path.join(CLS_DIR, cf), encoding="utf-8"))["items"]:
            classified[c["id"]] = c
    exp = {}  # (major, minor) -> list of texts
    for it in items:
        if it["kind"] != "question":
            continue
        c = classified.get(it["id"])
        if c is not None:
            key = (c["major"], c["minor"])
        elif it.get("assigned"):
            key = (it["major"], it["minor"])
        else:
            continue  # 未分类的不管
        exp.setdefault(key, []).append(it["text"])
    return exp


def check_file(rel, exp):
    if rel.startswith(CAT_DIR + os.sep):
        rel = rel[len(CAT_DIR) + 1:]
    elif rel.startswith("categories" + os.sep):
        rel = rel[len("categories") + 1:]
    fp = os.path.join(CAT_DIR, rel)
    if not os.path.exists(fp):
        return f"[缺失] {rel}"
    texts = []
    for ln in open(fp, encoding="utf-8"):
        m = Q_RE.match(ln.strip())
        if m:
            texts.append(m.group(1).strip())
    parts = rel.split("/")
    key = (parts[0], parts[1][:-3]) if len(parts) == 2 else None
    expect = exp.get(key, []) if key else []
    n_exp, n_got = len(expect), len(texts)
    if n_exp != n_got:
        return f"[FAIL] {rel}: 题数 {n_got}/{n_exp}"
    miss = [t for t in expect if t not in texts]
    extra = [t for t in texts if t not in expect]
    if miss or extra:
        return f"[FAIL] {rel}: 文本不符 缺{len(miss)} 多{len(extra)}  e.g. 缺:{miss[:1]} 多:{extra[:1]}"
    return f"[OK] {rel}: {n_got} 题全部保留"


def main():
    exp = expected_map()
    targets = sys.argv[1:] or [
        os.path.join(d, f) for d in sorted(os.listdir(CAT_DIR))
        if os.path.isdir(os.path.join(CAT_DIR, d))
        for f in sorted(os.listdir(os.path.join(CAT_DIR, d)))
    ]
    ok = fail = 0
    for rel in targets:
        r = check_file(rel, exp)
        print(r)
        if r.startswith("[OK]"):
            ok += 1
        else:
            fail += 1
    print(f"\n{ok} 个文件通过, {fail} 个有问题")


if __name__ == "__main__":
    main()
