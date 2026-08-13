#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q↔L 映射: agent-review-audit 题卡 (Q001-Q243) ↔ 我方题库 items.json (L###)

匹配策略:
  1. 规范化标题 (去空白/标点/引号, 转小写)
  2. 双向包含匹配 (标题互相包含, 长度 >= 10)
  3. 输出 mapping.json: {qid: {"lid":..., "match": "exact|contain|near"}}
  4. 未匹配的两侧清单输出到 mapping_unmatched.json 供 subagent 人工归位
"""
import json
import os
import re
import sys

ROOT = "/home/caoruixin/桌面/面试文档裁切"
CARDS = "/home/caoruixin/.gemini/antigravity-cli/builtin/skills/agent-review-audit/references/03_Cards"

PUNCT = re.compile(r"[\s，。！？、；：""''（）()\[\]【】.,!?;:'\"\-—_…~～<>《》]+")


def norm(s: str) -> str:
    return PUNCT.sub("", s).lower()


def parse_card(path: str):
    """返回 (qid, title, answer_md, prereq, downstream)"""
    with open(path, encoding="utf-8") as f:
        txt = f.read()
    fm = {}
    m = re.match(r"^---\n(.*?)\n---\n", txt, re.S)
    body = txt
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                fm[k.strip()] = v.strip().strip('"')
        body = txt[m.end():]
    # 答题思路区: [!SUCCESS] 之后的引用块
    am = re.search(r"\[!SUCCESS\]\s*答题思路与知识点分析(.*?)(?:\n---|\Z)", body, re.S)
    answer = am.group(1).strip() if am else ""
    # 前置/后置 (frontmatter 里的纯文本或列表)
    def lst(v):
        if not v or v == "[]":
            return []
        return re.findall(r"Q\d+", v)
    return fm.get("qid"), fm.get("title", ""), answer, lst(fm.get("prerequisites", "")), lst(fm.get("downstream", ""))


def main():
    items = json.load(open(os.path.join(ROOT, "items.json"), encoding="utf-8"))
    our = {it["id"]: it for it in items if it["kind"] == "question"}
    cards = {}
    for fn in sorted(os.listdir(CARDS)):
        if fn.startswith("Q") and fn.endswith(".md"):
            qid, title, answer, pre, down = parse_card(os.path.join(CARDS, fn))
            if qid:
                cards[qid] = {"title": title, "answer": answer, "prereq": pre, "downstream": down,
                              "n_title": norm(title)}

    our_n = {lid: norm(it["text"]) for lid, it in our.items()}
    mapped, used_our = {}, set()
    # 先精确包含匹配
    for qid, c in sorted(cards.items()):
        cn, best, blen = c["n_title"], None, 0
        for lid, ln in our_n.items():
            if lid in used_our:
                continue
            if cn == ln:
                best, blen = lid, len(cn)
                break
            if len(cn) >= 10 and len(ln) >= 10 and (cn in ln or ln in cn):
                if len(cn) > blen:
                    best, blen = lid, len(cn)
        if best:
            mapped[qid] = {"lid": best, "match": "exact" if blen == len(cn) else "contain"}
            used_our.add(best)

    # 未匹配
    unmapped_q = [qid for qid in cards if qid not in mapped]
    unmapped_l = [lid for lid in our if lid not in used_our]

    out = os.path.join(ROOT, "mapping.json")
    json.dump({qid: {"lid": v["lid"], "match": v["match"],
                     "title": cards[qid]["title"],
                     "our_text": our[v["lid"]]["text"][:80]}
               for qid, v in mapped.items()},
              open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump({"unmapped_cards": [{"qid": q, "title": cards[q]["title"]} for q in unmapped_q],
               "unmapped_ours": [{"lid": l, "text": our[l]["text"][:80]} for l in unmapped_l]},
              open(os.path.join(ROOT, "mapping_unmatched.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"映射成功: {len(mapped)}/{len(cards)} 张卡 -> {len(mapped)} 题")
    print(f"未映射卡: {len(unmapped_q)} 张 | 我方未映射: {len(unmapped_l)} 题")
    if unmapped_q:
        print("未映射卡:", ", ".join(unmapped_q[:20]))
    if unmapped_l:
        print("我方未映射:", ", ".join(unmapped_l[:20]))


if __name__ == "__main__":
    main()
