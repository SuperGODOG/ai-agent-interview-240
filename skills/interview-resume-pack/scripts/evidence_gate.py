#!/usr/bin/env python3
"""证据门：校验备战包产物中的 文件:行号 证据锚点是否真实存在，并对账代码版本一致性。

用法: python3 evidence_gate.py <产物.md> <仓库根目录> [--strict-commit]
规则:
  - 提取 路径.ext:行号 形式锚点 → 文件必须存在、是普通文件、行号 >=1 且不超文件行数
  - 提取反引号内的裸路径 → 文件必须存在
  - 空产物 / 零锚点 → FAIL（产物必须有证据）
  - 自动检测 snapshot_meta.json 并校验仓库 Git HEAD 是否一致，防止代码版本漂移导致行号失效
  - 任一悬空 → exit 1（打回重修）；全部通过 → exit 0
"""
import json
import os
import pathlib
import re
import subprocess
import sys

EXT = r'(?:py|java|go|js|ts|jsx|tsx|md|yaml|yml|json|toml|xml|sh|sql|html|css)'
ANCHOR = re.compile(rf'([\w\-./]+?\.{EXT}):(\d+)')
BARE = re.compile(rf'`([\w\-./]+?\.{EXT})`')


def fail(msg):
    print(f'证据门 FAIL: {msg}')
    sys.exit(1)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    strict_commit = '--strict-commit' in sys.argv
    if len(args) != 2:
        print(__doc__)
        sys.exit(2)
    doc, root = pathlib.Path(args[0]), pathlib.Path(args[1])
    if not doc.exists():
        fail(f'产物不存在: {doc}')
    if not doc.is_file():          # 目录 → FAIL（原版 read_text 崩溃）
        fail(f'产物不是普通文件: {doc}')
    if not root.is_dir():
        fail(f'仓库根不存在: {root}')

    # 1. 检查快照 Commit 版本一致性（防代码漂移）
    meta_candidates = [
        doc.parent / "snapshot_meta.json",
        doc.parent.parent / "snapshot_meta.json",
    ]
    meta_file = next((p for p in meta_candidates if p.is_file()), None)
    if meta_file and (root / ".git").is_dir():
        try:
            snap_meta = json.loads(meta_file.read_text(encoding="utf-8"))
            snap_commit = snap_meta.get("commit_hash", "")
            if snap_commit:
                head_res = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                                          capture_output=True, text=True, check=False)
                head_commit = head_res.stdout.strip()
                if head_commit and snap_commit != head_commit:
                    warn_msg = (
                        f"⚠️  警告 [版本漂移]: 快照锁定 Commit ({snap_commit[:7]}) 与代码库当前 HEAD ({head_commit[:7]}) 不一致！\n"
                        f"    产物可能基于旧代码生成，文件行号或逻辑可能已发生位移。建议先重新建档刷新快照。"
                    )
                    if strict_commit:
                        fail(warn_msg)
                    else:
                        print(warn_msg)
        except Exception:
            pass

    raw = doc.read_bytes()
    if not raw.strip():            # 空产物 → FAIL（原版静默 exit 0）
        fail('产物为空，无任何证据')
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError:     # 二进制误入 → FAIL（原版崩溃/乱码）
        fail('产物不是 UTF-8 文本（可能误传二进制）')

    anchors = set(ANCHOR.findall(text))
    bad_anchors = {a for a in anchors if int(a[1]) < 1}   # 行号 0/负数 → 非法
    anchors = {a for a in anchors if int(a[1]) >= 1}
    anchor_paths = {p for p, _ in anchors}
    bares = {p for p in BARE.findall(text)} - anchor_paths

    for p, ln in sorted(bad_anchors):
        print(f'  FAIL 行号非法(须>=1): {p}:{ln}')

    oks, fails = 0, []
    for path, line in sorted(anchors):
        f = root / path
        if not f.is_file():
            fails.append(f'悬空文件: {path}:{line}')
            continue
        nlines = len(f.read_text(encoding='utf-8', errors='ignore').splitlines())
        if int(line) > max(nlines, 1):
            fails.append(f'行号越界: {path}:{line} (该文件共 {nlines} 行)')
        else:
            oks += 1
    for path in sorted(bares):
        if (root / path).is_file():
            oks += 1
        else:
            fails.append(f'悬空文件: {path}')

    if not anchors and not bares:  # 零锚点 → FAIL
        fails.append('产物中未发现任何 文件:行号 或 `路径` 证据锚点')

    total_fails = len(fails) + len(bad_anchors)
    print(f'证据门: {oks} 通过 / {total_fails} 悬空')
    for f in fails:
        print('  FAIL', f)
    sys.exit(1 if total_fails else 0)


if __name__ == '__main__':
    main()
