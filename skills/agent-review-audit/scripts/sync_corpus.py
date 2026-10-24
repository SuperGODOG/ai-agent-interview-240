#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""同步题卡语料 -> references/03_Cards（唯一规范目录）

用法: python3 sync_corpus.py [--source /path/to/03_Cards]

v3.1 修复: 源路径参数化（不再硬编码）; 同步目标改为唯一目录 03_Cards;
references/README.md 正常换行写入。
"""
import os
import shutil
import argparse

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARDS_TARGET = os.path.join(SKILL_ROOT, "references", "03_Cards")
DEFAULT_SOURCE = os.environ.get("AGENT_REVIEW_CARDS_SOURCE") or ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=DEFAULT_SOURCE, help="源题卡目录")
    args = ap.parse_args()
    if not args.source:
        raise SystemExit("请用 --source 指定源 03_Cards 目录，或设置 AGENT_REVIEW_CARDS_SOURCE")
    if not os.path.isdir(args.source):
        raise SystemExit(f"源目录不存在: {args.source}（可用 --source 指定）")

    os.makedirs(CARDS_TARGET, exist_ok=True)
    n = 0
    for fn in sorted(os.listdir(args.source)):
        if fn.endswith(".md"):
            shutil.copy2(os.path.join(args.source, fn), os.path.join(CARDS_TARGET, fn))
            n += 1

    readme = os.path.join(SKILL_ROOT, "references", "README.md")
    with open(readme, "w", encoding="utf-8") as f:
        f.write("# Agent Review Audit Skill 语料库\n\n"
                "- 包含 500 道带精准 YAML 锚点的大厂面试题卡（references/03_Cards/）\n"
                "- 包含 51 概念映射表（config/concepts.yaml）\n"
                "- 一键同步: `python3 scripts/sync_corpus.py --source <源目录>`\n"
                "- 链接自检: `python3 scripts/check_links.py --fix`\n")
    print(f"已同步 {n} 张题卡 -> {CARDS_TARGET}")


if __name__ == "__main__":
    main()
