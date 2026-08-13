#!/usr/bin/env python3
"""从 面试文档裁切 题库生成 ai-agent-interview-240 的八股文分卷。

输入: items.json(题目+answer框架) + batches/classified/*.json(最终分类)
输出: docs/01-面试八股文/{01-Agent应用开发,02-八股基础,03-Transformer,04-LeetCode算法}.md
"""
import json
import os
from collections import defaultdict

SRC = "/home/caoruixin/桌面/面试文档裁切"
DST = "/home/caoruixin/桌面/ai-agent-interview-240/docs/01-面试八股文"

DEPTH_LABEL = {1: "概念定义", 2: "原理机制", 3: "设计与方案", 4: "落地与权衡", 5: "前沿与延伸"}

# ---------- 1. 读题目 ----------
with open(os.path.join(SRC, "items.json"), encoding="utf-8") as f:
    items = json.load(f)
qs = [it for it in items if it.get("kind") == "question"]
print(f"题目总数: {len(qs)}")

# ---------- 2. 读最终分类 ----------
classified = {}
for cf in os.listdir(os.path.join(SRC, "batches", "classified")):
    if not cf.endswith(".json"):
        continue
    with open(os.path.join(SRC, "batches", "classified", cf), encoding="utf-8") as f:
        for c in json.load(f)["items"]:
            classified[c["id"]] = c
print(f"classified: {len(classified)}")

# ---------- 3. 合并 ----------
merged = []
for q in qs:
    c = classified.get(q["id"], {})
    major = c.get("major") or q.get("major") or "未分类"
    minor = c.get("minor") or q.get("minor") or major
    depth = int(c.get("depth") or q.get("depth") or 99)
    merged.append({
        "id": q["id"],
        "text": q["text"],
        "major": major,
        "minor": minor,
        "depth": depth,
        "fuzzy": bool(c.get("fuzzy", False)),
        "answer": q.get("answer"),
        "prereq": q.get("prereq", []),
        "downstream": q.get("downstream", []),
        "status": q.get("status", "待复习"),
    })

# ---------- 4. 分卷定义 ----------
VOLUMES = [
    ("01-Agent应用开发.md", "二_Agent应用开发相关", "Agent 应用开发（182 题）",
     "大厂 AI Agent 岗核心战场：宏观认知、主流框架、工具调用、Prompt、记忆、架构设计、数据库、工程落地、性能评估"),
    ("02-八股基础.md", "四_八股相关", "计算机八股（38 题）",
     "JVM/并发/网络/OS/数据库索引/Redis 等基础八股"),
    ("03-Transformer与大模型.md", "三_transformer相关", "Transformer 与大模型（10 题）",
     "注意力机制、长上下文、KV Cache、推理优化、微调对齐"),
    ("04-LeetCode算法.md", "Leetcode相关", "LeetCode 与算法（8 题）",
     "手撕代码高频题"),
    ("05-反问与国企特别版.md", None, "反问与国企特别版（2 题）",
     "反问环节与国企面试特别准备"),
]

# 处理反问/国企: 归入第五卷
def volume_major(m):
    return m if m else None

def q_in_volume(q, major):
    if major is None:
        return q["major"] in ("反问", "国企特别版")
    return q["major"] == major


def render_question(q):
    """渲染单题 markdown"""
    depth = DEPTH_LABEL.get(q["depth"], "综合")
    lines = [f"### {q['id']} · {q['text']}"]
    lines.append("")
    meta = [f"**深度**: {q['depth']}/5 · {depth}"]
    if q["fuzzy"]:
        meta.append("**定位**: 模糊归位（按语义近似归类）")
    lines.append("  \n".join(meta) if len(meta) > 1 else meta[0])
    lines.append("")
    if q.get("answer"):
        core = q["answer"].get("core", "")
        steps = q["answer"].get("steps", [])
        if core:
            lines.append(f"> **核心考点**：{core}")
            lines.append("")
        if steps:
            lines.append("**答题框架（大厂四步）**：")
            lines.append("")
            for i, s in enumerate(steps, 1):
                lines.append(f"1. **{s.split('：')[0]}**" + (f"：{s.split('：', 1)[1]}" if "：" in s else ""))
            lines.append("")
    # 学习路径
    path = []
    if q.get("prereq"):
        path.append("前置: " + ", ".join(q["prereq"]))
    if q.get("downstream"):
        path.append("后置: " + ", ".join(q["downstream"]))
    if path:
        lines.append("**学习路径**：" + " ｜ ".join(path))
        lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)

# ---------- 5. 生成分卷 ----------
for fname, major, title, desc in VOLUMES:
    qlist = [q for q in merged if q_in_volume(q, major)]
    qlist.sort(key=lambda q: (q["depth"], q["id"]))
    if not qlist:
        print(f"[跳过] {fname}: 无题目")
        continue
    # 按 minor 分组
    minors = defaultdict(list)
    for q in qlist:
        minors[q["minor"]].append(q)

    def gh_anchor(text: str) -> str:
        """GitHub 锚点规则: 小写, 移除标点(保留字母数字空格连字符), 空格转连字符"""
        import re as _re
        t = text.lower()
        t = _re.sub(r"[^\w\u4e00-\u9fff\s-]", "", t)
        t = t.replace(" ", "-")
        return t

    lines = [f"# {title}", "",
             f"> 真实大厂真题 {len(qlist)} 道 · {desc}", "",
             f"> 题目来源：本人搜集整理的大厂 AI Agent 岗真实面试题；每题附深度标签与答题框架。", "",
             "## 目录", ""]
    for mi in sorted(minors):
        lines.append(f"- [{mi}（{len(minors[mi])} 题）](#{gh_anchor(mi)})")
    lines.append("")
    lines.append("---")
    lines.append("")
    for mi in sorted(minors):
        lines.append(f"## {mi}")
        lines.append("")
        lines.append(f"共 {len(minors[mi])} 题，按逻辑深度排序。")
        lines.append("")
        for q in sorted(minors[mi], key=lambda q: (q["depth"], q["id"])):
            lines.append(render_question(q))

    out = os.path.join(DST, fname)
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")
    print(f"[OK] {fname}: {len(qlist)} 题 -> {out}")

# ---------- 6. 统计未入卷题目 ----------
unvol = [q for q in merged if not any(q_in_volume(q, m) for _, m, _, _ in VOLUMES)]
print(f"\n未入卷题目: {len(unvol)}")
for q in unvol:
    print(f"  {q['id']} [{q['major']}]: {q['text'][:60]}")
