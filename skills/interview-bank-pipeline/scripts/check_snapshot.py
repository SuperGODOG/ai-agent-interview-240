#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_snapshot.py —— 检查项目面试快照版本新鲜度（Commit Hash、工作树状态、题库指纹与题目链接）

用法:
  python3 check_snapshot.py <target_path_or_url_or_slug> [--json] [--fail-on-stale]

状态码 (Exit code):
  0: FRESH (快照与当前代码、工作树及公共题库指纹完全一致)
  1: STALE / LEGACY_UNTRACKED / DIRTY (快照过时、题库扩容、或存在未追踪改动)
  2: MISSING / CORRUPTED (快照完全不存在或损坏)
"""
import argparse
from datetime import datetime
import hashlib
import json
import os
import re
import subprocess
import sys


def run_cmd(cmd, cwd=None):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except Exception as e:
        return -1, "", str(e)


def compute_bank_fingerprint(bank_root: str) -> dict:
    """计算公共题库确定性 64 字符 SHA256 指纹及统计（涵盖 items.json, concepts.yaml, schema.json）"""
    if not bank_root or not os.path.isdir(bank_root):
        return {}
    target_files = ["items.json", "concepts.yaml", "schema.json"]
    hasher = hashlib.sha256()
    for fname in target_files:
        fpath = os.path.join(bank_root, fname)
        if not os.path.isfile(fpath):
            return {}
        with open(fpath, "rb") as f:
            content = f.read()
        hasher.update(f"--- FILE: {fname} ---\n".encode("utf-8"))
        hasher.update(content)
        hasher.update(b"\n")

    items_path = os.path.join(bank_root, "items.json")
    try:
        with open(items_path, "r", encoding="utf-8") as f:
            items = json.load(f)
        total_items = len(items)
        real_questions = sum(1 for it in items if it.get("kind") == "question")
    except Exception:
        total_items, real_questions = 0, 0

    return {
        "hash": hasher.hexdigest(),
        "total_items": total_items,
        "total_questions": real_questions,
        "files": target_files
    }


def get_worktree_info(repo_dir: str) -> dict:
    """提取本地 Git 仓库的提交与精确工作树指纹（覆盖暂存、未暂存及非忽略的未跟踪文件）；支持非Git本地目录内容哈希"""
    info = {"is_git": False}
    if not repo_dir or not os.path.isdir(repo_dir):
        return info

    if not os.path.isdir(os.path.join(repo_dir, ".git")):
        # 非 Git 目录：计算源码/配置文件的确定性组合哈希
        exclude_dirs = {'.git', '.venv', 'venv', '__pycache__', '.pytest_cache', '.idea', '.vscode'}
        exclude_exts = {'.pyc', '.png', '.jpg', '.jpeg', '.db', '.sqlite', '.log'}
        exclude_files = {'.DS_Store', '.env', '.env.local', '.env.production'}
        hasher = hashlib.sha256()
        count = 0
        for root, dirs, files in os.walk(repo_dir):
            dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith('.')]
            for fn in sorted(files):
                if fn in exclude_files or fn.startswith('.env'):
                    continue
                ext = os.path.splitext(fn)[1].lower()
                if ext in exclude_exts:
                    continue
                fp = os.path.join(root, fn)
                rel = os.path.relpath(fp, repo_dir)
                try:
                    with open(fp, 'rb') as f:
                        f_sha = hashlib.sha256(f.read()).digest()
                    hasher.update(rel.encode('utf-8') + b'\0' + f_sha + b'\n')
                    count += 1
                except Exception:
                    pass
        return {
            "is_git": False,
            "is_local_dir": True,
            "worktree_hash": hasher.hexdigest(),
            "file_count": count,
            "commit_hash": None,
            "commit_short": "local",
            "branch": "local",
            "is_dirty": False,
        }

    code, head, _ = run_cmd(["git", "-C", repo_dir, "rev-parse", "HEAD"])
    if code != 0 or not head:
        return info

    info["is_git"] = True
    info["commit_hash"] = head
    info["commit_short"] = head[:7]

    _, branch, _ = run_cmd(["git", "-C", repo_dir, "rev-parse", "--abbrev-ref", "HEAD"])
    _, date, _ = run_cmd(["git", "-C", repo_dir, "log", "-1", "--format=%cd"])
    _, msg, _ = run_cmd(["git", "-C", repo_dir, "log", "-1", "--format=%s"])
    info["branch"] = branch
    info["commit_date"] = date
    info["commit_message"] = msg

    # Tracked diff (staged + unstaged against HEAD)
    r_diff = subprocess.run(["git", "-C", repo_dir, "diff-index", "--binary", "HEAD"], capture_output=True)
    tracked_diff = r_diff.stdout if r_diff.returncode == 0 else b""

    # Untracked files (excluding .gitignore ignored)
    r_untracked = subprocess.run(["git", "-C", repo_dir, "ls-files", "--others", "--exclude-standard", "-z"], capture_output=True)
    untracked_files = [f for f in r_untracked.stdout.split(b"\0") if f] if r_untracked.returncode == 0 else []

    is_dirty = bool(tracked_diff or untracked_files)
    info["is_dirty"] = is_dirty

    if not is_dirty:
        info["worktree_hash"] = head
        info["tracked_diff_bytes"] = 0
        info["untracked_count"] = 0
        return info

    hasher = hashlib.sha256()
    hasher.update(b"HEAD:" + head.encode("ascii") + b"\n")
    hasher.update(b"TRACKED:\n" + tracked_diff + b"\n")
    hasher.update(b"UNTRACKED:\n")
    for uf in sorted(untracked_files):
        p = os.path.join(repo_dir.encode("utf-8"), uf)
        if os.path.isfile(p):
            try:
                with open(p, "rb") as f:
                    file_sha = hashlib.sha256(f.read()).digest()
            except Exception:
                file_sha = b"ERR"
        else:
            file_sha = b"NON_FILE"
        hasher.update(uf + b"\0" + file_sha + b"\n")

    info["worktree_hash"] = hasher.hexdigest()
    info["tracked_diff_bytes"] = len(tracked_diff)
    info["untracked_count"] = len(untracked_files)
    return info


def get_repo_git_info(repo_dir: str) -> dict:
    """兼容旧接口"""
    return get_worktree_info(repo_dir)


def find_bank_root() -> str | None:
    """定位公共题库真理源根目录（优先包内当前公共真理源，防旧工作区假冒 FRESH）"""
    cur = os.path.dirname(os.path.abspath(__file__))
    sibling_bank = os.path.abspath(os.path.join(cur, "..", "..", "agent-project-grill", "references", "题库"))
    if os.path.isfile(os.path.join(sibling_bank, "concepts.yaml")):
        return sibling_bank
    cc_switch_bank = os.path.expanduser("~/.cc-switch/skills/agent-project-grill/references/题库")
    if os.path.isfile(os.path.join(cc_switch_bank, "concepts.yaml")):
        return cc_switch_bank
    ws = os.environ.get("INTERVIEW_WORKSPACE")
    if ws and os.path.isfile(os.path.join(ws, "concepts.yaml")):
        return ws
    legacy = os.path.expanduser("~/.interview-workbench")
    if os.path.isfile(os.path.join(legacy, "concepts.yaml")):
        return legacy
    return None


def resolve_slug_and_repo(target: str) -> tuple[str, str | None]:
    """解析目标，返回 (slug, local_repo_dir)"""
    target = target.strip()
    
    # 1. 如果是本地目录
    if os.path.isdir(target):
        target_abs = os.path.abspath(target)
        snap_meta_path = os.path.join(target_abs, "snapshot_meta.json")
        match_path = os.path.join(target_abs, "match.json")
        # 1.1 如果该目录本身就是快照归档目录（包含 snapshot_meta.json 或 match.json）
        if os.path.isfile(snap_meta_path) or os.path.isfile(match_path):
            slug = None
            code_url = None
            if os.path.isfile(snap_meta_path):
                try:
                    with open(snap_meta_path, encoding="utf-8") as f:
                        meta_obj = json.load(f)
                        slug = meta_obj.get("slug")
                        code_url = meta_obj.get("url")
                except Exception:
                    pass
            if not slug and os.path.isfile(match_path):
                try:
                    with open(match_path, encoding="utf-8") as f:
                        meta_obj = json.load(f).get("meta", {})
                        slug = meta_obj.get("slug")
                        code_url = code_url or meta_obj.get("url")
                except Exception:
                    pass
            if not slug:
                slug = os.path.basename(target_abs)

            repo_dir = None
            if code_url and os.path.isdir(code_url):
                repo_dir = code_url
            else:
                repo_dir = find_local_repo_for_slug(slug)
            return slug, repo_dir

        # 1.2 如果是本地源码目录：仅在目标目录自身包含 .git 时才查询 Git，严防向上误认祖先 Git 仓库
        if os.path.exists(os.path.join(target_abs, ".git")):
            code, url, _ = run_cmd(["git", "-C", target_abs, "remote", "get-url", "origin"])
            if code == 0 and url:
                m = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$", url)
                if m:
                    return f"{m.group(1)}__{m.group(2)}", target_abs
        base = os.path.basename(target_abs)
        return f"local__{base}", target_abs

    # 2. 如果是 GitHub URL
    m = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$", target)
    if m:
        return f"{m.group(1)}__{m.group(2)}", None

    # 3. 假设直接输入的是 slug (owner__repo)
    return target, None


def find_snapshot_dirs(slug: str) -> list[str]:
    """寻找可能存放该项目快照的目录"""
    candidates = []
    
    pm_dir = os.environ.get("PROJECT_MOCK_SKILL_DIR")
    if pm_dir:
        candidates.append(os.path.join(pm_dir, "references", "项目", slug))
    
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.abspath(os.path.join(cur_dir, "..", "..", "project-mock-interview", "references", "项目", slug)))
    
    candidates.append(os.path.expanduser(f"~/.gemini/skills/project-mock-interview/references/项目/{slug}"))
    candidates.append(os.path.expanduser(f"~/.cc-switch/skills/project-mock-interview/references/项目/{slug}"))
    
    vault_root = os.environ.get("INTERVIEW_WORKSPACE") or os.path.expanduser("~/.interview-workbench")
    candidates.append(os.path.join(vault_root, "obsidian_vault", "40_项目档案", slug))

    candidates.append(os.path.expanduser(f"~/Desktop/project/ai-agent-interview-240/projects/{slug}"))

    seen = set()
    result = []
    for c in candidates:
        norm = os.path.normpath(c)
        if norm not in seen and os.path.isdir(norm):
            seen.add(norm)
            result.append(norm)
    return result


def extract_snapshot_metadata(snap_dir: str) -> dict:
    """提取快照中的版本元数据（合并 snapshot_meta.json 与 match.json）"""
    meta = {}
    
    # 1. 从 snapshot_meta.json 读
    meta_file = os.path.join(snap_dir, "snapshot_meta.json")
    if os.path.isfile(meta_file):
        try:
            with open(meta_file, encoding="utf-8") as f:
                meta = json.load(f)
                meta["source"] = "snapshot_meta.json"
        except Exception:
            pass

    # 2. 从 match.json 读 (补全 bank_fingerprint 与 candidates)
    match_file = os.path.join(snap_dir, "match.json")
    if os.path.isfile(match_file):
        try:
            with open(match_file, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    m_meta = data.get("meta", {})
                    for k, v in m_meta.items():
                        if k not in meta or meta[k] is None:
                            meta[k] = v
                    if "bank_fingerprint" in m_meta and "bank_fingerprint" not in meta:
                        meta["bank_fingerprint"] = m_meta["bank_fingerprint"]
                    meta["candidates"] = [c.get("id") if isinstance(c, dict) else str(c) for c in data.get("candidates", [])]
                    if "source" not in meta:
                        meta["source"] = "match.json:meta"
        except Exception:
            pass

    # 3. 从 项目画像.md 的 frontmatter 读 (补漏 commit)
    profile_file = os.path.join(snap_dir, "项目画像.md")
    if os.path.isfile(profile_file) and not meta.get("commit_hash"):
        try:
            with open(profile_file, encoding="utf-8") as f:
                content = f.read(2048)
                m = re.search(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
                if m:
                    fm = m.group(1)
                    c_match = re.search(r"^commit:\s*([a-f0-9]+)", fm, re.MULTILINE)
                    if c_match:
                        meta["commit_hash"] = c_match.group(1)
                        meta["commit_short"] = meta["commit_hash"][:7]
                        b_match = re.search(r"^branch:\s*(.+)", fm, re.MULTILINE)
                        if b_match:
                            meta["branch"] = b_match.group(1).strip()
                        meta["source"] = "项目画像.md:frontmatter"
        except Exception:
            pass

    return meta


def find_local_repo_for_slug(slug: str) -> str | None:
    """尝试自动推断本地对应的工作区仓库目录"""
    root_ws = os.environ.get("INTERVIEW_WORKSPACE") or os.path.expanduser("~/.interview-workbench")
    cached_repo = os.path.join(root_ws, "repos_cache", slug)
    if os.path.isdir(cached_repo):
        return cached_repo

    if "__" in slug:
        prefix, repo_name = slug.split("__", 1)
        search_dirs = [
            os.path.expanduser(f"~/Desktop/project/{repo_name}"),
            os.path.expanduser(f"~/Desktop/projects/{repo_name}"),
        ]
        for p in search_dirs:
            if not os.path.isdir(p):
                continue
            if prefix == "local":
                return p
            else:
                if os.path.exists(os.path.join(p, ".git")):
                    code, url, _ = run_cmd(["git", "-C", p, "remote", "get-url", "origin"])
                    if code == 0 and url:
                        m = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$", url)
                        if m and f"{m.group(1)}__{m.group(2)}" == slug:
                            return p
    return None


def find_all_known_slugs() -> list[str]:
    """发现当前环境中所有已知快照及已知的重点项目 slug"""
    slugs = set()
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    search_dirs = [
        os.environ.get("PROJECT_MOCK_SKILL_DIR"),
        os.path.abspath(os.path.join(cur_dir, "..", "..", "project-mock-interview", "references", "项目")),
        os.path.expanduser("~/.gemini/skills/project-mock-interview/references/项目"),
        os.path.expanduser("~/.cc-switch/skills/project-mock-interview/references/项目"),
        os.path.join(os.environ.get("INTERVIEW_WORKSPACE") or os.path.expanduser("~/.interview-workbench"), "obsidian_vault", "40_项目档案"),
    ]
    for sdir in search_dirs:
        if sdir and os.path.isdir(sdir):
            for entry in os.listdir(sdir):
                if not entry.startswith(".") and os.path.isdir(os.path.join(sdir, entry)):
                    slugs.add(entry)

    # 包含已知本地待建档项目 (如 miaosha)
    miaosha_path = os.path.expanduser("~/Desktop/project/miaosha")
    if os.path.isdir(miaosha_path):
        slugs.add("SuperGODOG__miaosha")

    return sorted(list(slugs))


def check_snapshot(target: str, bank_root: str = None) -> dict:
    target_abs = os.path.abspath(target) if (isinstance(target, str) and os.path.isdir(target)) else None
    slug, repo_dir = resolve_slug_and_repo(target)
    snap_dirs = find_snapshot_dirs(slug)
    
    if target_abs and (os.path.isfile(os.path.join(target_abs, "match.json")) or os.path.isfile(os.path.join(target_abs, "snapshot_meta.json"))):
        if target_abs not in snap_dirs:
            snap_dirs.insert(0, target_abs)

    if not repo_dir:
        repo_dir = find_local_repo_for_slug(slug)

    repo_git = get_worktree_info(repo_dir) if repo_dir else {"is_git": False}

    result = {
        "slug": slug,
        "target": target,
        "repo_dir": repo_dir,
        "repo_git": repo_git,
        "snapshot_dirs": snap_dirs,
        "status": "UNKNOWN",
        "code_status": "UNKNOWN",
        "bank_status": "UNKNOWN",
        "link_status": "UNKNOWN",
        "reason": "",
        "message": "",
        "diff_summary": None,
    }

    if not snap_dirs:
        result["status"] = "MISSING"
        result["code_status"] = "MISSING" if not repo_git.get("is_git") else "FRESH_OR_UNTRACKED"
        result["bank_status"] = "MISSING"
        result["link_status"] = "MISSING"
        result["reason"] = f"未找到项目 [{slug}] 的快照档案。需要先运行 interview-bank-pipeline 建档。"
        result["message"] = result["reason"]
        return result

    primary_snap_dir = snap_dirs[0]
    result["active_snapshot_dir"] = primary_snap_dir
    files = [f for f in os.listdir(primary_snap_dir) if not f.startswith(".")]
    result["snapshot_files"] = files

    if "match.json" not in files:
        result["status"] = "CORRUPTED"
        result["code_status"] = "CORRUPTED"
        result["bank_status"] = "CORRUPTED"
        result["link_status"] = "CORRUPTED"
        result["reason"] = "快照目录存在但缺少核心路由文件 match.json。"
        result["message"] = result["reason"]
        return result

    snap_meta = extract_snapshot_metadata(primary_snap_dir)
    result["snapshot_meta"] = snap_meta

    # 1. 判定 code_status
    if not snap_meta or (not snap_meta.get("commit_hash") and not snap_meta.get("is_local_dir")):
        result["code_status"] = "LEGACY_UNTRACKED"
    elif repo_git.get("is_local_dir"):
        if snap_meta.get("worktree_hash") and snap_meta.get("worktree_hash") == repo_git.get("worktree_hash"):
            result["code_status"] = "FRESH"
        else:
            result["code_status"] = "STALE"
    elif not repo_git.get("is_git"):
        result["code_status"] = "UNVERIFIABLE_REPO"
    else:
        snap_commit = snap_meta["commit_hash"]
        head_commit = repo_git["commit_hash"]
        if snap_commit != head_commit:
            result["code_status"] = "STALE"
            code_ahead, ahead_out, _ = run_cmd(["git", "-C", repo_dir, "rev-list", "--count", f"{snap_commit}..{head_commit}"])
            code_behind, behind_out, _ = run_cmd(["git", "-C", repo_dir, "rev-list", "--count", f"{head_commit}..{snap_commit}"])
            ahead = int(ahead_out) if code_ahead == 0 and ahead_out.isdigit() else "?"
            behind = int(behind_out) if code_behind == 0 and behind_out.isdigit() else "?"
            _, log_diff, _ = run_cmd(["git", "-C", repo_dir, "log", "--oneline", "-n", "5", f"{snap_commit}..{head_commit}"])
            result["diff_summary"] = {
                "snapshot_commit": snap_commit[:7],
                "head_commit": head_commit[:7],
                "ahead_commits": ahead,
                "behind_commits": behind,
                "recent_commits_ahead": log_diff.splitlines() if log_diff else []
            }
        else:
            # commit 相同，校验工作树状态
            if snap_meta.get("is_dirty"):
                if repo_git.get("is_dirty") and snap_meta.get("worktree_hash") == repo_git.get("worktree_hash"):
                    result["code_status"] = "FRESH"
                else:
                    result["code_status"] = "STALE"
            else:
                if repo_git.get("is_dirty"):
                    result["code_status"] = "DIRTY_WORKTREE"
                else:
                    result["code_status"] = "FRESH"

    # 2. 判定 bank_status
    if bank_root is None:
        bank_root = find_bank_root()
    curr_bank_fp = compute_bank_fingerprint(bank_root) if bank_root else {}
    result["current_bank_fingerprint"] = curr_bank_fp

    snap_bank_fp = snap_meta.get("bank_fingerprint")
    if not curr_bank_fp:
        result["bank_status"] = "BANK_NOT_FOUND"
    elif not snap_bank_fp or not snap_bank_fp.get("hash"):
        result["bank_status"] = "LEGACY_UNTRACKED"
    elif snap_bank_fp.get("hash") == curr_bank_fp.get("hash"):
        result["bank_status"] = "FRESH"
    else:
        result["bank_status"] = "STALE"

    # 3. 判定 link_status
    candidates = snap_meta.get("candidates", [])
    if not candidates:
        result["link_status"] = "EMPTY_CANDIDATES"
    elif not bank_root or not os.path.isfile(os.path.join(bank_root, "items.json")):
        result["link_status"] = "BANK_NOT_FOUND"
    else:
        try:
            with open(os.path.join(bank_root, "items.json"), "r", encoding="utf-8") as f:
                bank_items = json.load(f)
            bank_item_map = {it.get("id"): it for it in bank_items}
            invalid_ids = []
            for cid in candidates:
                if not cid or cid.startswith("Q") or cid not in bank_item_map or bank_item_map[cid].get("kind") != "question":
                    invalid_ids.append(cid)
            if invalid_ids:
                result["link_status"] = "BROKEN_LINK"
                result["invalid_ids"] = invalid_ids
            else:
                result["link_status"] = "FRESH"
        except Exception as e:
            result["link_status"] = f"ERROR: {e}"

    # 4. 综合状态判定
    if result["code_status"] == "FRESH" and result["bank_status"] == "FRESH" and result["link_status"] == "FRESH":
        result["status"] = "FRESH"
        head_s = repo_git.get("commit_short", "")
        result["reason"] = f"快照 100% 同步！代码版本 ({head_s})、工作树与公共题库指纹均证实一致，题目链接全部有效。"
    elif result["code_status"] == "LEGACY_UNTRACKED" or result["bank_status"] == "LEGACY_UNTRACKED":
        result["status"] = "LEGACY_UNTRACKED"
        parts = []
        if result["code_status"] == "LEGACY_UNTRACKED":
            parts.append("代码未追踪commit")
        if result["bank_status"] == "LEGACY_UNTRACKED":
            parts.append("题库版本未追踪")
        extra_drift = ""
        if result["code_status"] == "STALE" and result.get("diff_summary"):
            ahead = result["diff_summary"].get("ahead_commits", "?")
            snap_c = result["diff_summary"].get("snapshot_commit", "")
            head_c = result["diff_summary"].get("head_commit", "")
            extra_drift = f"，且本地代码已漂移（领先 {ahead} 个提交: {head_c} vs {snap_c}）"
        result["reason"] = f"快照属于旧版流水线遗留物（{', '.join(parts)}{extra_drift}），无法验证一致性，建议重新建档刷新。"
    elif result["code_status"] == "DIRTY_WORKTREE":
        result["status"] = "DIRTY_WORKTREE"
        result["reason"] = "快照 commit 与 HEAD 匹配，但本地工作区存在未建档的修改 (Dirty)。"
    elif result["code_status"] == "UNVERIFIABLE_REPO":
        result["status"] = "UNVERIFIABLE_REPO"
        result["reason"] = "本地目录非 Git 仓库或无法读取 Git 信息，无法核对代码新鲜度。"
    else:
        result["status"] = "STALE"
        stale_reasons = []
        if result["code_status"] == "STALE":
            if result.get("diff_summary"):
                ahead = result["diff_summary"].get("ahead_commits", "?")
                stale_reasons.append(f"本地代码与快照版本不一致(代码领先 {ahead} 提交)")
            else:
                stale_reasons.append("本地代码与快照版本不一致/工作区漂移")
        if result["bank_status"] == "STALE":
            stale_reasons.append("公共题库已扩容或更新")
        if result["link_status"] != "FRESH":
            stale_reasons.append(f"候选题目ID失效({result.get('invalid_ids', [])})")
        result["reason"] = f"快照已过时（{'; '.join(stale_reasons)}），严禁直接复用，请重新运行 pipeline 刷新。"

    result["message"] = result["reason"]
    return result


def main():
    parser = argparse.ArgumentParser(description="检查项目面试快照版本新鲜度")
    parser.add_argument("target", nargs="?", default=None, help="本地仓库路径、GitHub URL 或项目 slug（若使用 --all 或省略则检查全量已知项目）")
    parser.add_argument("--all", action="store_true", help="检视所有已知项目快照")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    parser.add_argument("--fail-on-stale", action="store_true", help="若过时或未追踪则以非0退出")
    parser.add_argument("--bank-root", default=None, help="指定公共题库根目录（覆盖默认查找）")
    args = parser.parse_args()

    if args.all or not args.target:
        targets = find_all_known_slugs()
        results = [check_snapshot(t, bank_root=args.bank_root) for t in targets]
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            print("\n" + "=" * 70)
            print(f"全量已知项目快照版本校验总览（共 {len(results)} 个项目）")
            print("=" * 70)
            status_icons = {
                "FRESH": "✅ [FRESH 100%同步]",
                "DIRTY_WORKTREE": "🟡 [DIRTY 工作区未提交]",
                "STALE": "❌ [STALE 快照已过时]",
                "LEGACY_UNTRACKED": "⚠️ [LEGACY 旧版快照]",
                "MISSING": "⚪ [MISSING 未建档]",
                "CORRUPTED": "💔 [CORRUPTED 文件损坏]",
                "UNVERIFIABLE_REPO": "❓ [UNVERIFIABLE 无法核对]",
            }
            for res in results:
                icon = status_icons.get(res["status"], f"[{res['status']}]")
                print(f"• {res['slug']:<26} {icon:<26} code={res['code_status']:<16} bank={res['bank_status']:<16} link={res['link_status']}")
                print(f"  说明: {res['message']}")
            print("=" * 70 + "\n")

        has_critical = any(r["status"] in ("MISSING", "CORRUPTED") for r in results)
        has_stale = any(r["status"] in ("STALE", "LEGACY_UNTRACKED") for r in results)
        if has_critical:
            sys.exit(2)
        elif has_stale and args.fail_on_stale:
            sys.exit(1)
        else:
            sys.exit(0)
    else:
        res = check_snapshot(args.target, bank_root=args.bank_root)

        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            status_icons = {
                "FRESH": "✅ [FRESH 100%同步]",
                "DIRTY_WORKTREE": "🟡 [DIRTY 工作区有未提交代码]",
                "STALE": "❌ [STALE 快照已过时]",
                "LEGACY_UNTRACKED": "⚠️ [LEGACY 旧版快照无版本信息]",
                "MISSING": "⚪ [MISSING 未建档]",
                "CORRUPTED": "💔 [CORRUPTED 快照文件损坏]",
                "UNVERIFIABLE_REPO": "❓ [UNVERIFIABLE 无法核对Git]",
            }
            icon = status_icons.get(res["status"], f"[{res['status']}]")
            print("\n" + "=" * 60)
            print(f"项目快照版本校验报告: {res['slug']}")
            print(f"状态判定: {icon}")
            print("=" * 60)
            print(res["message"])
            print(f"  - 代码状态 (code): {res['code_status']}")
            print(f"  - 题库状态 (bank): {res['bank_status']}")
            print(f"  - 链接状态 (link): {res['link_status']}")
            if res.get("active_snapshot_dir"):
                print(f"快照路径: {res['active_snapshot_dir']}")
            if res.get("diff_summary") and res["diff_summary"]["recent_commits_ahead"]:
                print("\n近期领先提交:")
                for line in res["diff_summary"]["recent_commits_ahead"]:
                    print(f"  * {line}")
            print("=" * 60 + "\n")

        # 状态码映射
        if res["status"] == "FRESH":
            sys.exit(0)
        elif res["status"] in ("DIRTY_WORKTREE", "UNVERIFIABLE_REPO"):
            sys.exit(0 if not args.fail_on_stale else 1)
        elif res["status"] in ("STALE", "LEGACY_UNTRACKED"):
            sys.exit(1)
        else:
            sys.exit(2)


if __name__ == "__main__":
    main()
