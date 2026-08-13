#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""蒸馏移植: agent-review-audit 题卡 -> items.json

为每道题附加:
  answer: 大厂四步答题框架 (核心考点 + 4 步逻辑梳理标签)
  prereq / downstream: 学习路径边 (Q 卡前置/后置 -> 我方 L id)
  status: 待复习 (复习状态机初始值)
"""
import json
import os
import re
import shutil

ROOT = "/home/caoruixin/桌面/面试文档裁切"
CARDS = "/home/caoruixin/.gemini/antigravity-cli/builtin/skills/agent-review-audit/references/03_Cards"

PUNCT = re.compile(r"[\s，。！？、；：\"\"''（）()\[\]【】.,!?;:'\"\-—_…~～<>《》]+")


def norm(s):
    return PUNCT.sub("", s).lower()


def parse_card(path):
    with open(path, encoding="utf-8") as f:
        txt = f.read()
    fm = {}
    m = re.match(r"^---\n(.*?)\n---\n", txt, re.S)
    body = txt
    if m:
        lines = m.group(1).splitlines()
        cur = None
        for line in lines:
            if ":" in line:
                k, v = line.split(":", 1)
                cur = k.strip()
                fm[cur] = v.strip().strip('"')
            elif line.strip().startswith("- ") and cur:
                fm[cur] = (fm[cur] + " " if fm[cur] else "") + line.strip()[2:].strip('"')
        body = txt[m.end():]
    am = re.search(r"\[!SUCCESS\]\s*答题思路与知识点分析(.*?)(?:\n---|\Z)", body, re.S)
    answer = am.group(1).strip() if am else ""

    core = re.search(r"\*\*核心考点\*\*\s*:\s*(.+)", answer)
    core_point = core.group(1).strip() if core else ""
    steps = re.findall(r"\*\*([^:]+)\*\*\s*:", answer)
    steps = [s.strip() for s in steps if s.strip() not in ("核心考点", "逻辑梳理")][:4]

    def lst(v):
        if not v or v == "[]":
            return []
        return re.findall(r"Q\d+", v)

    return fm.get("qid"), answer, core_point, steps, lst(fm.get("prerequisites", "")), lst(fm.get("downstream", ""))


def main():
    items_path = os.path.join(ROOT, "items.json")
    shutil.copy(items_path, items_path + ".bak")
    items = json.load(open(items_path, encoding="utf-8"))
    mapping = json.load(open(os.path.join(ROOT, "mapping.json"), encoding="utf-8"))

    q2l = {q: v["lid"] for q, v in mapping.items()}
    cards = {}
    for fn in sorted(os.listdir(CARDS)):
        if fn.startswith("Q") and fn.endswith(".md"):
            qid, answer, core, steps, pre, down = parse_card(os.path.join(CARDS, fn))
            if qid:
                cards[qid] = {"answer": answer, "core": core, "steps": steps, "pre": pre, "down": down}

    n_ans = n_edge = 0
    for it in items:
        if it["kind"] != "question":
            continue
        c = cards.get({v["lid"]: q for q, v in mapping.items()}.get(it["id"], ""), None)
        # 反查: lid -> qid
        qid = None
        for q, v in mapping.items():
            if v["lid"] == it["id"]:
                qid = q
                break
        if not qid or qid not in cards:
            continue
        c = cards[qid]
        it["answer"] = {"core": c["core"], "steps": c["steps"]}
        it["prereq"] = [q2l[q] for q in c["pre"] if q in q2l]
        it["downstream"] = [q2l[q] for q in c["down"] if q in q2l]
        it["status"] = "待复习"
        n_ans += 1
        n_edge += len(it["prereq"]) + len(it["downstream"])

    json.dump(items, open(items_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"已附加答题框架: {n_ans} 题 | 学习路径边: {n_edge} 条 | 全部 status=待复习")
    print(f"备份: items.json.bak")
    # 统计示例
    ex = next((it for it in items if it["kind"] == "question" and "answer" in it), None)
    if ex:
        print(f"示例 {ex['id']}: core={ex['answer']['core'][:50]} steps={ex['answer']['steps']}")


if __name__ == "__main__":
    main()
