#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""更新项目薄弱主题档案 .agent-audit/profile.json（复习闭环）

用法: python3 update_profile.py --path <项目路径> --tags concept_a,concept_b

路由时 route_project.py 会读取该 profile 对薄弱概念加权（+5），
实现"下场优先审查薄弱项"。
"""
import os
import json
import argparse
import datetime


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", required=True, help="项目路径（route_project.py 的 --path 同值）")
    ap.add_argument("--tags", required=True, help="薄弱概念 id，逗号分隔，如 concept_mcp_core,concept_eval_metrics")
    args = ap.parse_args()
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    if not tags:
        raise SystemExit("--tags 不能为空")

    d = os.path.join(args.path, ".agent-audit")
    os.makedirs(d, exist_ok=True)
    pf = os.path.join(d, "profile.json")
    old = {}
    if os.path.exists(pf):
        try:
            old = json.load(open(pf, encoding="utf-8"))
        except Exception:
            old = {}
    old["weakness_tags"] = sorted(set(old.get("weakness_tags", [])) | set(tags))
    old["updated_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    with open(pf, "w", encoding="utf-8") as f:
        json.dump(old, f, ensure_ascii=False, indent=1)
    print(f"profile 已更新: {pf}（薄弱项 {len(old['weakness_tags'])} 个）")


if __name__ == "__main__":
    main()
