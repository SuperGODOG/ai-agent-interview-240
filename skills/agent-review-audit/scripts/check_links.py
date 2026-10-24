#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查并修复 references/ 内的 wiki 链接断链

用法:
  python3 check_links.py            # 只报告
  python3 check_links.py --fix      # 为缺失目标自动生成 stub 笔记（使链接可达）

修复点（v3.1）: 原实现循环体为空, 永远 PASS; 现真正解析 [[...]] 并对照 references/ 实际文件。
"""
import os
import re
import glob
import argparse

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = os.path.join(SKILL_ROOT, "references")

LINK_RE = re.compile(r"\[\[([^\]|#]+?)(?:#[^\]|]+)?(?:\|[^\]]*)?\]\]")


def existing_targets():
    """references/ 下所有可链接笔记名（去 .md，含 basename 与相对路径两种解析）"""
    names = set()
    for p in glob.glob(os.path.join(REF, "**", "*.md"), recursive=True):
        rel = os.path.relpath(p, REF)
        names.add(rel[:-3])
        names.add(os.path.basename(rel)[:-3])
    return names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true", help="为缺失目标生成 stub 笔记")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    exist = existing_targets()
    missing, total = {}, 0
    for p in glob.glob(os.path.join(REF, "**", "*.md"), recursive=True):
        content = open(p, encoding="utf-8", errors="ignore").read()
        for m in LINK_RE.finditer(content):
            total += 1
            t = m.group(1).strip()
            if not t or t.startswith("#"):
                continue
            if t not in exist and t + ".md" not in exist:
                missing.setdefault(t, []).append(os.path.relpath(p, REF))

    if args.fix:
        for t in missing:
            fp = os.path.join(REF, t + ".md")
            os.makedirs(os.path.dirname(fp), exist_ok=True)
            if not os.path.exists(fp):
                with open(fp, "w", encoding="utf-8") as f:
                    f.write(f"# {t}\n\n> 由 check_links.py --fix 自动生成的占位笔记。\n")
        print(f"[fix] 已生成 {len(missing)} 个缺失笔记")
        return

    print(f"总链接 {total} 个, 断链 {len(missing)} 个")
    for t in sorted(missing)[:25]:
        print(f"  [[{t}]] <- {', '.join(missing[t][:3])}")
    if missing and not args.quiet:
        print("提示: 运行 check_links.py --fix 自动生成占位笔记")
    return 1 if missing else 0


if __name__ == "__main__":
    sys_exit = main()
    raise SystemExit(sys_exit or 0)
