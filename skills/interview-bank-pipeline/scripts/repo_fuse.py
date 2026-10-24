#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""repo_fuse —— GitHub 项目 × 面试题库 融合工具（机械部分）

用法:
  python3 repo_fuse.py fetch <url_or_dir>     # 克隆/同步 + 项目画像 + 版本快照元数据 -> repos_cache/<slug>/profile.json
  python3 repo_fuse.py match <slug>           # 命中概念 -> 题库候选题目 -> match.json (内嵌 meta)
  python3 repo_fuse.py finalize <slug>        # 汇总 subagent 产出的 sections/ -> vault 档案 + 仓库 INTERVIEW_DESIGN_MAP.md + 同步拷打快照
  python3 repo_fuse.py check <target>         # 检查项目快照版本新鲜度 (调用 check_snapshot.py)

判断部分（项目画像润色/逐题作答）由主会话派 subagent 完成，
subagent 只读写 repos_cache/<slug>/sections/ 与 obsidian_vault/40_项目档案/<slug>/。
"""
from datetime import datetime
import json
import os
import re
import shutil
import subprocess
import sys

cur_dir = os.path.dirname(os.path.abspath(__file__))
if cur_dir not in sys.path:
    sys.path.insert(0, cur_dir)
import check_snapshot

try:
    import yaml
except ImportError:
    yaml = None

def _find_bank_root():
    ws = os.environ.get("INTERVIEW_WORKSPACE")
    if ws and os.path.isfile(os.path.join(ws, "concepts.yaml")):
        return ws
    legacy = os.path.expanduser("~/.interview-workbench")
    if os.path.isfile(os.path.join(legacy, "concepts.yaml")):
        return legacy
    cur = os.path.dirname(os.path.abspath(__file__))
    sibling_bank = os.path.abspath(os.path.join(cur, "..", "..", "agent-project-grill", "references", "题库"))
    if os.path.isfile(os.path.join(sibling_bank, "concepts.yaml")):
        return sibling_bank
    return cur

ROOT = _find_bank_root()
CACHE = os.path.join(ROOT, "repos_cache")
VAULT = os.path.join(ROOT, "obsidian_vault")
ARCHIVE = os.path.join(VAULT, "40_项目档案")

def check_concepts_workspace():
    if not os.path.isfile(os.path.join(ROOT, "concepts.yaml")):
        print(f"警告: 工作区 {ROOT} 中未找到 concepts.yaml。"
              "请设置 INTERVIEW_WORKSPACE 指向真实数据目录（如 export INTERVIEW_WORKSPACE=$HOME/.interview-workbench），"
              "或确认旧路径 ~/.interview-workbench 存在。", file=sys.stderr)

SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build",
             "target", ".idea", ".vscode", "assets", "images", "docs", ".github"}
SKIP_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".lock", ".min.js",
             ".map", ".woff", ".woff2", ".ttf", ".pyc", ".pdf", ".zip"}
MANIFESTS = ("README", "readme", "package.json", "pyproject.toml", "requirements.txt",
             "go.mod", "Cargo.toml", "pom.xml", "build.gradle", "composer.json", "Gemfile")


def slug_of(url: str) -> str:
    url = url.strip()
    if os.path.isdir(url):
        base = os.path.basename(os.path.abspath(url))
        if os.path.isdir(os.path.join(url, ".git")):
            r = run(["git", "-C", url, "remote", "get-url", "origin"])
            if r.returncode == 0 and r.stdout.strip():
                m = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$", r.stdout.strip())
                if m:
                    return f"{m.group(1)}__{m.group(2)}"
        return f"local__{base}"
    m = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$", url)
    if not m:
        raise SystemExit(f"无法解析 GitHub 链接或本地目录: {url}")
    return f"{m.group(1)}__{m.group(2)}"


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


# ---------------- fetch ----------------

def fetch(url: str):
    check_concepts_workspace()
    url = url.strip()
    is_local = os.path.isdir(url)
    local_src = os.path.abspath(url) if is_local else None
    slug = slug_of(url)
    rdir = os.path.join(CACHE, slug)
    os.makedirs(CACHE, exist_ok=True)

    if is_local:
        if os.path.isdir(os.path.join(rdir, ".git")):
            run(["git", "-C", rdir, "fetch", "--depth", "1", local_src, "HEAD", "--quiet"])
            run(["git", "-C", rdir, "reset", "--hard", "FETCH_HEAD", "--quiet"])
            print(f"本地缓存已同步: {rdir} (源自 {local_src})")
        else:
            r = run(["git", "clone", "--depth", "1", "--quiet", local_src, rdir])
            if r.returncode != 0:
                shutil.copytree(local_src, rdir, dirs_exist_ok=True,
                                ignore=shutil.ignore_patterns(*SKIP_DIRS))
            print(f"本地目录已同步至缓存: {rdir}")
    else:
        if os.path.isdir(os.path.join(rdir, ".git")):
            run(["git", "-C", rdir, "pull", "--depth", "1", "--quiet"])
            print(f"已存在, 更新: {rdir}")
        else:
            r = run(["git", "clone", "--depth", "1", "--quiet", url, rdir])
            if r.returncode != 0:
                raise SystemExit(f"克隆失败: {r.stderr[-500:]}")
            print(f"克隆完成: {rdir}")

    # 获取 Git 版本指纹
    git_head, git_branch, git_date, git_msg = "", "", "", ""
    if os.path.exists(os.path.join(rdir, ".git")):
        git_head = run(["git", "-C", rdir, "rev-parse", "HEAD"]).stdout.strip()
        git_branch = run(["git", "-C", rdir, "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
        git_date = run(["git", "-C", rdir, "log", "-1", "--format=%cd"]).stdout.strip()
        git_msg = run(["git", "-C", rdir, "log", "-1", "--format=%s"]).stdout.strip()

    # ---- 指纹: 语言/框架/树 ----
    ext_count, tree, manifests = {}, [], {}
    for d0, dirs, files in os.walk(rdir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        rel = os.path.relpath(d0, rdir)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        for fn in files:
            p = os.path.join(d0, fn)
            rp = os.path.relpath(p, rdir)
            ext = os.path.splitext(fn)[1].lower()
            if ext in SKIP_EXTS or fn.endswith((".md", ".txt")) and fn not in ("README.md", "README.txt"):
                continue
            tree.append(rp)
            if ext:
                ext_count[ext] = ext_count.get(ext, 0) + 1
            if fn in MANIFESTS or fn.lower() in ("readme.md", "readme.txt"):
                try:
                    manifests[fn] = open(p, encoding="utf-8", errors="ignore").read(6000)
                except Exception:
                    pass
            if depth >= 5:
                dirs[:] = []

    readme = next((v for k, v in manifests.items() if "readme" in k.lower()), "")
    all_manifests = " ".join(manifests.values())

    # ---- 框架识别 ----
    known = {"langgraph": "LangGraph", "langchain": "LangChain", "autogen": "AutoGen",
             "crewai": "CrewAI", "fastapi": "FastAPI", "flask": "Flask", "django": "Django",
             "react": "React", "vue": "Vue", "next": "Next.js", "streamlit": "Streamlit",
             "gradio": "Gradio", "spring": "Spring", "pytorch": "PyTorch", "tensorflow": "TF",
             "transformers": "HuggingFace Transformers", "llamaindex": "LlamaIndex",
             "haystack": "Haystack", "redis": "Redis", "postgres": "PostgreSQL",
             "pgvector": "pgvector", "qdrant": "Qdrant", "milvus": "Milvus",
             "weaviate": "Weaviate", "chromadb": "ChromaDB", "sqlite": "SQLite",
             "opencv": "OpenCV", "whisper": "Whisper", "vllm": "vLLM", "dify": "Dify",
             "coze": "Coze", "mcp": "MCP", "docker": "Docker", "k8s": "K8s",
             "kubernetes": "K8s", "kafka": "Kafka", "rabbitmq": "RabbitMQ",
             "celery": "Celery", "pydantic": "Pydantic", "tortoise": "TortoiseORM"}
    blob = (readme + "\n" + all_manifests + "\n" + " ".join(tree)).lower()
    frameworks = sorted({v for k, v in known.items() if k in blob},
                        key=lambda v: -blob.count(v.lower()))
    top_ext = sorted(ext_count.items(), key=lambda kv: -kv[1])[:6]

    # ---- 概念匹配: README + manifests + 文件路径 + 抽样内容 ----
    if yaml is None:
        raise SystemExit("错误: 缺少 pyyaml 依赖，请在有 PyYAML 的环境中运行 (如 .venv)")
    with open(os.path.join(ROOT, "concepts.yaml"), encoding="utf-8") as f:
        concepts = yaml.safe_load(f)["concepts"]

    # 抽样内容: 树内文件采样(上限 400 个) + 各扩展名最大文件
    sampled = {}
    for rp in tree:
        if not os.path.splitext(rp)[1] or len(sampled) >= 400:
            continue
        try:
            sampled[rp] = open(os.path.join(rdir, rp), encoding="utf-8",
                               errors="ignore").read(3000)
        except Exception:
            pass
    big_files = {}
    for d0, dirs, files in os.walk(rdir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in files:
            p = os.path.join(d0, fn)
            ext = os.path.splitext(fn)[1].lower()
            if ext in SKIP_EXTS:
                continue
            try:
                sz = os.path.getsize(p)
            except Exception:
                continue
            if sz > big_files.get(ext, (0, ""))[0] and sz < 300_000:
                big_files[ext] = (sz, p)
    for (sz, p) in big_files.values():
        rp = os.path.relpath(p, rdir)
        if rp not in sampled:
            try:
                sampled[rp] = open(p, encoding="utf-8", errors="ignore").read(3000)
            except Exception:
                pass

    path_blob = " ".join(tree).lower()
    concept_hits = {}
    for c in concepts:
        files_hit = []
        for rp in tree:
            rpl = rp.lower()
            if any(str(kw).lower() in rpl for kw in c["keywords"]):
                files_hit.append(rp)
        body = readme.lower() + "\n" + all_manifests.lower()
        for rp, txt in sampled.items():
            body += "\n" + txt.lower()
        if len(body) > 4_000_000:
            body = body[:4_000_000]
        if any(str(kw).lower() in body for kw in c["keywords"]):
            files_hit = files_hit or ["<内容命中>"]
            concept_hits[c["name"]] = files_hit[:8]

    # 生成版本元数据
    src_for_wt = local_src if (is_local and local_src) else rdir
    wt_info = check_snapshot.get_worktree_info(src_for_wt)
    is_dirty = wt_info.get("is_dirty", False)
    if wt_info.get("is_local_dir"):
        git_head = None
        git_branch = None
        git_date = None
        git_msg = "Local non-git workspace (SHA-256 file manifest verification)"
    else:
        git_head = wt_info.get("commit_hash", git_head) or git_head
        git_branch = wt_info.get("branch", git_branch) or git_branch
        git_date = wt_info.get("commit_date", git_date) or git_date
        git_msg = wt_info.get("commit_message", git_msg) or git_msg
    wt_hash = wt_info.get("worktree_hash", git_head)

    meta = {
        "slug": slug,
        "url": url,
        "is_local_dir": is_local and not wt_info.get("is_git", False),
        "is_git": wt_info.get("is_git", not is_local),
        "commit_hash": git_head,
        "commit_short": git_head[:7] if git_head else None,
        "branch": git_branch,
        "commit_date": git_date,
        "commit_message": git_msg,
        "is_dirty": is_dirty,
        "worktree_hash": wt_hash,
        "synced_at": datetime.now().isoformat(),
        "file_count": len(tree),
        "pipeline_version": "1.2.0"
    }
    with open(os.path.join(rdir, "snapshot_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    profile = {
        "meta": meta,
        "slug": slug, "url": url, "dir": rdir,
        "ext_count": top_ext, "frameworks": frameworks[:10],
        "file_count": len(tree), "readme_head": readme[:1500],
        "tree": tree[:300], "concept_hits": concept_hits,
    }
    with open(os.path.join(rdir, "profile.json"), "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=1)
    commit_label = git_head[:7] if git_head else "local"
    print(f"画像完成: {len(tree)} 文件 / Commit `{commit_label}` / 框架 {frameworks[:6]} / 命中概念 {len(concept_hits)}")
    for c, files in sorted(concept_hits.items(), key=lambda kv: -len(kv[1]))[:12]:
        print(f"  {c}: {len(files)} 个证据文件")


# ---------------- match ----------------

def load_bank():
    items = json.load(open(os.path.join(ROOT, "items.json"), encoding="utf-8"))
    classified = {}
    cdir = os.path.join(ROOT, "batches", "classified")
    if os.path.isdir(cdir):
        for cf in os.listdir(cdir):
            if cf.endswith(".json"):
                for c in json.load(open(os.path.join(cdir, cf), encoding="utf-8"))["items"]:
                    classified[c["id"]] = c
    if yaml is None:
        raise SystemExit("错误: 缺少 pyyaml 依赖，请在有 PyYAML 的环境中运行 (如 .venv)")
    with open(os.path.join(ROOT, "concepts.yaml"), encoding="utf-8") as f:
        concepts = yaml.safe_load(f)["concepts"]
    qs = []
    for it in items:
        if it.get("kind") != "question":
            continue
        c = classified.get(it["id"])
        if c is not None:
            major, minor = c.get("major"), c.get("minor")
            depth = int(c.get("depth") or 3)
        else:
            major = it.get("major") or "通用"
            minor = it.get("minor") or "基础"
            depth = int(it.get("depth") or 3)
        tl = it.get("text", "").lower()
        q_concepts = [cc["name"] for cc in concepts
                      if any(str(kw).lower() in tl for kw in cc.get("keywords", []))]
        qs.append({"id": it["id"], "text": it.get("text", ""), "major": major,
                   "minor": minor, "depth": depth, "concepts": q_concepts})
    return qs


def match(slug: str):
    check_concepts_workspace()
    rdir = os.path.join(CACHE, slug)
    profile = json.load(open(os.path.join(rdir, "profile.json"), encoding="utf-8"))
    meta = profile.get("meta", {})
    bank_fp = check_snapshot.compute_bank_fingerprint(ROOT)
    qs = load_bank()
    hits = profile.get("concept_hits", {})
    cands, per_concept = [], {}
    for q in qs:
        c_hit = [c for c in q["concepts"] if c in hits]
        if c_hit:
            cands.append({**q, "hit_concepts": c_hit})
            for c in c_hit:
                per_concept.setdefault(c, []).append(q["id"])
    # 每个概念最多 4 题(按深度分布取), 总候选上限 30
    chosen, seen = [], set()
    for c, ids in per_concept.items():
        for q in cands:
            if q["id"] in ids and q["id"] not in seen:
                seen.add(q["id"])
                chosen.append({**q, "evidence": hits[c][:5]})
                break
    chosen.sort(key=lambda q: (q["major"], q["minor"], q["depth"], q["line"] if "line" in q else 0))
    chosen = chosen[:30]
    with open(os.path.join(rdir, "match.json"), "w", encoding="utf-8") as f:
        json.dump({"meta": {**meta, "bank_fingerprint": bank_fp}, "candidates": chosen, "per_concept": per_concept}, f,
                  ensure_ascii=False, indent=1)
    print(f"命中概念 {len(hits)} 个 -> 候选题目 {len(chosen)} 道")
    for q in chosen:
        print(f"  {q['id']} [{q['major']}/{q['minor']} d{q['depth']}] {q['text'][:50]}"
              f" <- {','.join(q['hit_concepts'])}")


# ---------------- finalize ----------------

def finalize(slug: str):
    rdir = os.path.join(CACHE, slug)
    profile = json.load(open(os.path.join(rdir, "profile.json"), encoding="utf-8"))
    matchd = json.load(open(os.path.join(rdir, "match.json"), encoding="utf-8"))
    meta = profile.get("meta", {})
    sec = os.path.join(rdir, "sections")
    out = os.path.join(ARCHIVE, slug)
    os.makedirs(out, exist_ok=True)

    # 复制 snapshot_meta.json 到 vault
    if os.path.isfile(os.path.join(rdir, "snapshot_meta.json")):
        shutil.copy2(os.path.join(rdir, "snapshot_meta.json"), os.path.join(out, "snapshot_meta.json"))

    # 画像: 机械部分 + subagent 润色(如有 sections/00_画像.md)
    intro = open(os.path.join(sec, "00_画像.md"), encoding="utf-8").read() \
        if os.path.exists(os.path.join(sec, "00_画像.md")) else ""
    lang = "、".join(f"{e[0].lstrip('.')}×{e[1]}" for e in profile["ext_count"])
    
    commit_str = meta.get("commit_short", "untracked")
    commit_hash = meta.get("commit_hash", "")
    branch_str = meta.get("branch", "")
    synced_str = meta.get("synced_at", "")

    profile_md = f"""---
type: project
slug: {slug}
commit: {commit_hash}
branch: {branch_str}
synced_at: {synced_str}
url: {profile['url']}
frameworks: {json.dumps(profile['frameworks'], ensure_ascii=False)}
concepts: {json.dumps(list(profile['concept_hits'].keys()), ensure_ascii=False)}
---
# 项目档案：{slug}

> 来源：{profile['url']} ｜ Commit：`{commit_str}` ｜ 分支：`{branch_str}` ｜ 文件 {profile['file_count']} 个 ｜ 语言 {lang}

## 技术栈
{('、'.join(profile['frameworks'])) if profile['frameworks'] else '_无主流框架识别结果_'}
""" + (f"""
## 画像（subagent 润色版）

{intro}
""" if intro else "") + f"""
## 命中概念与证据文件

""" + "\n".join(
        f"- **{c}**：{', '.join(files[:4])}" for c, files in profile["concept_hits"].items()
    ) + "\n"

    # 匹配表
    rows = []
    for q in matchd["candidates"]:
        rows.append(f"| {q['id']} | {q['text'][:45]} | {q['depth']}/5 | "
                    f"{'、'.join(q['hit_concepts'])} | {'、'.join(q.get('evidence', [])[:2])} |")
    match_md = f"""---
type: question_map
project: {slug}
commit: {commit_hash}
synced_at: {synced_str}
---
# 面试题匹配表：{slug}

> 快照版本：`{commit_str}` ｜ 同步时间：{synced_str}

命中概念 {len(profile['concept_hits'])} 个，候选题目 {len(matchd['candidates'])} 道。
（完整作答见《项目内作答.md》；每题的证据锚点由 subagent 在作答时从代码中定位）

| 题号 | 题目 | 深度 | 命中概念 | 证据文件 |
|---|---|---|---|---|
""" + "\n".join(rows) + "\n"

    # 项目内作答: 合并 sections (按文件名排序, 00_画像 除外)
    ans_parts = []
    if os.path.isdir(sec):
        for fn in sorted(os.listdir(sec)):
            if fn.endswith(".md") and fn != "00_画像.md":
                ans_parts.append(open(os.path.join(sec, fn), encoding="utf-8").read())
    ans_md = (f"---\ntype: project_qa\nproject: {slug}\ncommit: {commit_hash}\nsynced_at: {synced_str}\n---\n# 项目内作答：{slug}\n\n"
              + "\n\n---\n\n".join(ans_parts) + "\n" if ans_parts
              else f"# 项目内作答：{slug}\n\n_尚无作答草稿，先运行 fuse 流程生成。_\n")

    for name, content in (("项目画像.md", profile_md), ("面试题匹配表.md", match_md),
                          ("项目内作答.md", ans_md)):
        with open(os.path.join(out, name), "w", encoding="utf-8") as f:
            f.write(content)
    print(f"vault 档案已写入: {out} (Commit `{commit_str}`)")

    # 仓库注入: docs/INTERVIEW_DESIGN_MAP.md (若源目录可写且存在 docs/)
    target_docdir = os.path.join(profile["dir"], "docs")
    if os.path.isdir(target_docdir) and os.environ.get("INJECT_REPO_DOCS") == "1":
        top = []
        for q in matchd["candidates"]:
            if q["hit_concepts"][0] not in {t[0] for t in top}:
                top.append((q["hit_concepts"][0], q.get("evidence", [])[:3]))
        map_md = f"""# Interview Design Map — {slug}

> 由 repo_fuse 自动生成（面试题库 × 本仓库设计映射）。用于把本项目的设计决策与面试高频设计主题对齐。
> 当前快照对应 Commit：`{commit_str}` ｜ 生成时间：{synced_str}

## 项目技术画像

- 框架/技术栈：{('、'.join(profile['frameworks'])) if profile['frameworks'] else '未识别'}
- 文件规模：{profile['file_count']} 个源文件
- 与面试题库命中 {len(profile['concept_hits'])} 个设计主题

## 设计主题 ↔ 仓库实现映射

| 面试设计主题 | 仓库中的实现/证据 | 对应题库位置 |
|---|---|---|
""" + "\n".join(
            f"| {c} | {', '.join(files)} | 见题库「{c}」概念笔记 |" for c, files in top
        ) + f"""

## 建议的面试切入点

- 本仓库最能体现设计深度的模块（按命中概念与证据文件定位，建议对照《项目内作答》准备）
- 每个主题准备"框架给的 vs 我设计的"对照

---
生成时间：由 repo_fuse 生成，随题库/仓库变化可重跑更新。
"""
        with open(os.path.join(target_docdir, "INTERVIEW_DESIGN_MAP.md"), "w", encoding="utf-8") as f:
            f.write(map_md)
        print(f"仓库注入完成: {os.path.join(target_docdir, 'INTERVIEW_DESIGN_MAP.md')}")

    sync_snapshot(slug)


def _find_project_mock_skill_dir():
    if os.environ.get("PROJECT_MOCK_SKILL_DIR") and os.path.isdir(os.environ["PROJECT_MOCK_SKILL_DIR"]):
        return os.environ["PROJECT_MOCK_SKILL_DIR"]
    cur = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.abspath(os.path.join(cur, "..", "..", "project-mock-interview")),
        os.path.abspath(os.path.join(cur, "..", "project-mock-interview")),
        os.path.expanduser("~/.cc-switch/skills/project-mock-interview"),
        os.path.expanduser("~/.gemini/skills/project-mock-interview"),
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    return None

def sync_snapshot(slug: str):
    """建档后自动同步快照到 project-mock-interview（拷打引擎消费端）。"""
    pm_dir = _find_project_mock_skill_dir()
    if not pm_dir:
        print(f"警告: 未找到 project-mock-interview skill 目录（{pm_dir}），跳过快照同步。"
              "可用 PROJECT_MOCK_SKILL_DIR 指定，或手动按 references/README.md 同步。", file=sys.stderr)
        return
    dst = os.path.join(pm_dir, "references", "项目", slug)
    os.makedirs(dst, exist_ok=True)
    
    copied = []
    for fname in ("match.json", "snapshot_meta.json"):
        src_f = os.path.join(CACHE, slug, fname)
        if os.path.isfile(src_f):
            shutil.copy2(src_f, os.path.join(dst, fname))
            copied.append(fname)

    src = os.path.join(ARCHIVE, slug)
    for name in ("项目画像.md", "面试题匹配表.md", "项目内作答.md", "snapshot_meta.json"):
        f = os.path.join(src, name)
        if os.path.isfile(f) and name not in copied:
            shutil.copy2(f, os.path.join(dst, name))
            copied.append(name)
    print(f"快照已同步到拷打引擎: {dst}（{', '.join(copied)}）")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "fetch"
    if cmd == "fetch":
        fetch(sys.argv[2])
    elif cmd == "match":
        match(sys.argv[2])
    elif cmd == "finalize":
        finalize(sys.argv[2])
    elif cmd in ("check", "check-snapshot"):
        import check_snapshot
        sys.argv.pop(1)
        check_snapshot.main()
    else:
        raise SystemExit(__doc__)
