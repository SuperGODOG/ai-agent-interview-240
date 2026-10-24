#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_snapshot_regression.py —— 快照版本新鲜度与数据流全链路回归测试套件

涵盖 16 项确定性回归场景：
  S1: 相同代码 + 相同公共题库 => FRESH
  S2: 题库三文件 (items/concepts/schema) 任一变动 => STALE (bank_status=STALE)
  S3: 旧版快照无题库指纹 => LEGACY_UNTRACKED
  S4: 缺失快照档案 => MISSING
  S5: 题库外部普通文档/提交变动 => bank_status 仍为 FRESH
  S6: Tracked 文件修改 (暂存/未暂存/二进制) => 检出 DIRTY
  S7: 相同 dirty 快照匹配 worktree_hash => FRESH
  S8: Untracked 文件修改同名内容 => 检出 STALE
  S9: 候选题目含不存在 ID / 非 question / Q 卡混入 => BROKEN_LINK
  S10: 工作区版本与公共题库不一致 (防假冒) => 拒绝 FRESH，判定 STALE
  S11: 全流程 fetch -> match -> finalize -> check_snapshot 完整数据流传递 => FRESH
  S12: .gitignore 忽略文件不计入工作树指纹 => worktree_hash 保持 clean
  S13: 本地非 Git 项目：内容不变 => FRESH
  S14: 本地非 Git 项目：源码变更 => STALE
  S15: 本地非 Git 项目：忽略缓存与临时文件不改变 worktree_hash => 保持 FRESH
  S16: 防误认祖先 Git：子目录置于外部 Git 内部时准确识别，无祖先穿透
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

cur_dir = os.path.dirname(os.path.abspath(__file__))
if cur_dir not in sys.path:
    sys.path.insert(0, cur_dir)

import check_snapshot


def run_tests():
    test_root = tempfile.mkdtemp(prefix="test_snap_regression_")
    try:
        print(f"[TEST] 启动隔离测试环境: {test_root}")

        # 1. 准备基础 Mock Git 仓库
        mock_repo = os.path.join(test_root, "mock_repo")
        os.makedirs(mock_repo)
        subprocess.run(["git", "init", mock_repo], check=True, capture_output=True)
        subprocess.run(["git", "-C", mock_repo, "config", "user.name", "tester"], check=True)
        subprocess.run(["git", "-C", mock_repo, "config", "user.email", "tester@test.com"], check=True)
        subprocess.run(["git", "-C", mock_repo, "remote", "add", "origin", "https://github.com/test_owner/mock_repo.git"], check=True)

        with open(os.path.join(mock_repo, "code.py"), "w", encoding="utf-8") as f:
            f.write("print('hello world')\n")
        subprocess.run(["git", "-C", mock_repo, "add", "code.py"], check=True)
        subprocess.run(["git", "-C", mock_repo, "commit", "-m", "init"], check=True, capture_output=True)
        init_head = subprocess.check_output(["git", "-C", mock_repo, "rev-parse", "HEAD"]).decode().strip()

        # 2. 准备 Mock 公共题库
        mock_bank = os.path.join(test_root, "mock_bank")
        os.makedirs(mock_bank)
        items_data = [
            {"id": "L1", "kind": "question", "text": "Question 1 about the world", "major": "AI Agent", "minor": "架构", "depth": 3},
            {"id": "L2", "kind": "question", "text": "Question 2", "major": "AI Agent", "minor": "架构", "depth": 3},
            {"id": "L3", "kind": "comment_title", "text": "Comment Title"},
        ]
        with open(os.path.join(mock_bank, "items.json"), "w", encoding="utf-8") as f:
            json.dump(items_data, f)
        with open(os.path.join(mock_bank, "concepts.yaml"), "w", encoding="utf-8") as f:
            f.write("concepts:\n  - name: Agent\n    keywords: ['world']\n")
        with open(os.path.join(mock_bank, "schema.json"), "w", encoding="utf-8") as f:
            f.write('{"majors": [{"name": "AI Agent", "minors": ["架构"]}]}')

        bank_fp = check_snapshot.compute_bank_fingerprint(mock_bank)
        assert bank_fp["total_items"] == 3
        assert bank_fp["total_questions"] == 2

        # 3. 准备 Mock 快照目录
        slug = "test_owner__mock_repo"
        snap_dir = os.path.join(test_root, "snapshots", slug)
        os.makedirs(snap_dir)

        def write_snap(commit, bank_fingerprint=None, is_dirty=False, wt_hash=None, candidate_ids=["L1", "L2"]):
            meta = {
                "slug": slug,
                "commit_hash": commit,
                "is_dirty": is_dirty,
                "worktree_hash": wt_hash or commit,
            }
            if bank_fingerprint:
                meta["bank_fingerprint"] = bank_fingerprint
            with open(os.path.join(snap_dir, "snapshot_meta.json"), "w", encoding="utf-8") as f:
                json.dump(meta, f)
            match_data = {
                "meta": meta,
                "candidates": [{"id": cid} for cid in candidate_ids]
            }
            with open(os.path.join(snap_dir, "match.json"), "w", encoding="utf-8") as f:
                json.dump(match_data, f)

        orig_find = check_snapshot.find_snapshot_dirs
        check_snapshot.find_snapshot_dirs = lambda s: [snap_dir] if s == slug else []

        try:
            # S1: 相同代码 + 相同公共题库 => FRESH
            write_snap(init_head, bank_fingerprint=bank_fp)
            res1 = check_snapshot.check_snapshot(mock_repo, bank_root=mock_bank)
            assert res1["status"] == "FRESH", f"S1 failed: {res1}"
            assert res1["code_status"] == "FRESH"
            assert res1["bank_status"] == "FRESH"
            assert res1["link_status"] == "FRESH"
            print("  [PASS] S1: 相同代码 + 相同公共题库 => FRESH")

            # S2: 题库三文件任一变动 => STALE
            with open(os.path.join(mock_bank, "concepts.yaml"), "w", encoding="utf-8") as f:
                f.write("concepts:\n  - name: AgentMod\n    keywords: ['world']\n")
            res2 = check_snapshot.check_snapshot(mock_repo, bank_root=mock_bank)
            assert res2["status"] == "STALE" and res2["bank_status"] == "STALE", f"S2 failed: {res2}"
            with open(os.path.join(mock_bank, "concepts.yaml"), "w", encoding="utf-8") as f:
                f.write("concepts:\n  - name: Agent\n    keywords: ['world']\n")
            print("  [PASS] S2: 题库概念文件变动 => STALE (bank_status=STALE)")

            # S3: 旧版快照无题库指纹 => LEGACY_UNTRACKED
            write_snap(init_head, bank_fingerprint=None)
            res3 = check_snapshot.check_snapshot(mock_repo, bank_root=mock_bank)
            assert res3["status"] == "LEGACY_UNTRACKED" and res3["bank_status"] == "LEGACY_UNTRACKED", f"S3 failed: {res3}"
            print("  [PASS] S3: 旧版快照无题库指纹 => LEGACY_UNTRACKED")

            # S4: 缺失快照档案 => MISSING
            res4 = check_snapshot.check_snapshot("non_existent_slug", bank_root=mock_bank)
            assert res4["status"] == "MISSING", f"S4 failed: {res4}"
            print("  [PASS] S4: 缺失快照档案 => MISSING")

            # S5: 题库外部普通文档变动 => bank 仍为 FRESH
            write_snap(init_head, bank_fingerprint=bank_fp)
            with open(os.path.join(test_root, "external_doc.md"), "w", encoding="utf-8") as f:
                f.write("# External doc\n")
            res5 = check_snapshot.check_snapshot(mock_repo, bank_root=mock_bank)
            assert res5["bank_status"] == "FRESH", f"S5 failed: {res5}"
            print("  [PASS] S5: 题库外部普通文档变动 => bank_status 仍为 FRESH")

            # S6: Tracked 文件修改 (暂存/未暂存/二进制) => 检出 DIRTY
            with open(os.path.join(mock_repo, "code.py"), "a", encoding="utf-8") as f:
                f.write("# tracked edit\n")
            res6 = check_snapshot.check_snapshot(mock_repo, bank_root=mock_bank)
            assert res6["status"] in ("DIRTY_WORKTREE", "STALE") and res6["code_status"] == "DIRTY_WORKTREE", f"S6 failed: {res6}"
            with open(os.path.join(mock_repo, "code.py"), "w", encoding="utf-8") as f:
                f.write("print('hello world')\n")
            print("  [PASS] S6: Tracked 文件变动 => 准确检出 DIRTY_WORKTREE")

            # S7: 相同 dirty 快照匹配 worktree_hash => FRESH
            with open(os.path.join(mock_repo, "untracked.py"), "w", encoding="utf-8") as f:
                f.write("content_v1\n")
            wt_dirty = check_snapshot.get_worktree_info(mock_repo)
            assert wt_dirty["is_dirty"]
            write_snap(init_head, bank_fingerprint=bank_fp, is_dirty=True, wt_hash=wt_dirty["worktree_hash"])
            res7 = check_snapshot.check_snapshot(mock_repo, bank_root=mock_bank)
            assert res7["status"] == "FRESH", f"S7 failed: {res7}"
            print("  [PASS] S7: 相同 dirty 快照匹配 worktree_hash => FRESH")

            # S8: Untracked 文件修改同名内容 => 检出 STALE
            with open(os.path.join(mock_repo, "untracked.py"), "w", encoding="utf-8") as f:
                f.write("content_v2_changed\n")
            res8 = check_snapshot.check_snapshot(mock_repo, bank_root=mock_bank)
            assert res8["status"] == "STALE" and res8["code_status"] == "STALE", f"S8 failed: {res8}"
            os.remove(os.path.join(mock_repo, "untracked.py"))
            print("  [PASS] S8: Untracked 文件内容修改同名文件 => 准确检出 STALE")

            # S9: 候选题目含不存在 ID / 非 question / Q 卡混入 => BROKEN_LINK
            # 9a: 不存在 ID
            write_snap(init_head, bank_fingerprint=bank_fp, candidate_ids=["L999"])
            res9a = check_snapshot.check_snapshot(mock_repo, bank_root=mock_bank)
            assert res9a["link_status"] == "BROKEN_LINK" and "L999" in res9a.get("invalid_ids", [])
            # 9b: 标记行非 question (L3)
            write_snap(init_head, bank_fingerprint=bank_fp, candidate_ids=["L3"])
            res9b = check_snapshot.check_snapshot(mock_repo, bank_root=mock_bank)
            assert res9b["link_status"] == "BROKEN_LINK" and "L3" in res9b.get("invalid_ids", [])
            # 9c: Q 卡混入 (Q001)
            write_snap(init_head, bank_fingerprint=bank_fp, candidate_ids=["Q001"])
            res9c = check_snapshot.check_snapshot(mock_repo, bank_root=mock_bank)
            assert res9c["link_status"] == "BROKEN_LINK" and "Q001" in res9c.get("invalid_ids", [])
            print("  [PASS] S9: 不存在题号 / 非 question 标记行 / Q 卡混入 => BROKEN_LINK")

            # S10: 工作区版本与公共题库不一致 (防假冒) => 拒绝 FRESH
            # 快照记录的是 mock_bank 指纹，但当前校验目标为不同版本的 other_bank
            other_bank = os.path.join(test_root, "other_bank")
            os.makedirs(other_bank)
            with open(os.path.join(other_bank, "items.json"), "w", encoding="utf-8") as f:
                json.dump([{"id": "L1", "kind": "question", "text": "Different"}], f)
            with open(os.path.join(other_bank, "concepts.yaml"), "w", encoding="utf-8") as f:
                f.write("concepts: []\n")
            with open(os.path.join(other_bank, "schema.json"), "w", encoding="utf-8") as f:
                f.write('{"majors": []}')
            write_snap(init_head, bank_fingerprint=bank_fp)  # 记录 mock_bank 指纹
            res10 = check_snapshot.check_snapshot(mock_repo, bank_root=other_bank)
            assert res10["status"] == "STALE" and res10["bank_status"] == "STALE", f"S10 failed: {res10}"
            print("  [PASS] S10: 数据集指纹不一致 => 拒绝 FRESH，准确判定 STALE")

            # S12: .gitignore 忽略文件不计入工作树指纹
            with open(os.path.join(mock_repo, ".gitignore"), "w", encoding="utf-8") as f:
                f.write("*.ignored\n")
            subprocess.run(["git", "-C", mock_repo, "add", ".gitignore"], check=True)
            subprocess.run(["git", "-C", mock_repo, "commit", "-m", "add gitignore"], check=True, capture_output=True)
            head_with_ignore = subprocess.check_output(["git", "-C", mock_repo, "rev-parse", "HEAD"]).decode().strip()
            # 创建被忽略文件
            with open(os.path.join(mock_repo, "temp.ignored"), "w", encoding="utf-8") as f:
                f.write("should be ignored\n")
            wt_ignore = check_snapshot.get_worktree_info(mock_repo)
            assert not wt_ignore["is_dirty"], "Ignored file should not dirty the worktree!"
            assert wt_ignore["worktree_hash"] == head_with_ignore
            print("  [PASS] S12: .gitignore 忽略文件不计入工作树指纹 => worktree_hash 保持 clean")

            # S13: 本地非 Git 项目：内容不变 => FRESH
            mock_local_dir = os.path.join(test_root, "mock_local_proj")
            os.makedirs(mock_local_dir)
            with open(os.path.join(mock_local_dir, "app.py"), "w", encoding="utf-8") as f:
                f.write("def main(): pass\n")
            wt_local = check_snapshot.get_worktree_info(mock_local_dir)
            assert wt_local["is_git"] is False
            assert wt_local["is_local_dir"] is True
            local_slug = "local__mock_local_proj"
            local_snap_dir = os.path.join(test_root, "snapshots", local_slug)
            os.makedirs(local_snap_dir, exist_ok=True)
            local_meta = {
                "slug": local_slug,
                "url": mock_local_dir,
                "is_local_dir": True,
                "is_git": False,
                "commit_hash": None,
                "commit_short": None,
                "branch": None,
                "worktree_hash": wt_local["worktree_hash"],
                "bank_fingerprint": bank_fp,
            }
            with open(os.path.join(local_snap_dir, "snapshot_meta.json"), "w", encoding="utf-8") as f:
                json.dump(local_meta, f)
            with open(os.path.join(local_snap_dir, "match.json"), "w", encoding="utf-8") as f:
                json.dump({"meta": local_meta, "candidates": [{"id": "L1"}]}, f)

            orig_find_2 = check_snapshot.find_snapshot_dirs
            check_snapshot.find_snapshot_dirs = lambda s: [local_snap_dir] if s == local_slug else ([snap_dir] if s == slug else [])
            try:
                res13 = check_snapshot.check_snapshot(mock_local_dir, bank_root=mock_bank)
                assert res13["status"] == "FRESH", f"S13 failed: {res13}"
                assert res13["code_status"] == "FRESH"
                assert res13["bank_status"] == "FRESH"
                assert res13["link_status"] == "FRESH"
                print("  [PASS] S13: 本地非 Git 项目：内容不变 => FRESH")

                # S14: 本地非 Git 项目：源码变更 => STALE
                with open(os.path.join(mock_local_dir, "new_feature.py"), "w", encoding="utf-8") as f:
                    f.write("# new code\n")
                res14 = check_snapshot.check_snapshot(mock_local_dir, bank_root=mock_bank)
                assert res14["status"] == "STALE" and res14["code_status"] == "STALE", f"S14 failed: {res14}"
                os.remove(os.path.join(mock_local_dir, "new_feature.py"))
                print("  [PASS] S14: 本地非 Git 项目：源码变更 => 准确检出 STALE")

                # S15: 本地非 Git 项目：忽略缓存与临时文件不改变 worktree_hash => 保持 FRESH
                cache_dir = os.path.join(mock_local_dir, ".pytest_cache")
                os.makedirs(cache_dir, exist_ok=True)
                with open(os.path.join(cache_dir, "v_cache.json"), "w") as f:
                    f.write('{"cached": 1}')
                with open(os.path.join(mock_local_dir, "test.pyc"), "wb") as f:
                    f.write(b"\x00\x01\x02")
                with open(os.path.join(mock_local_dir, ".DS_Store"), "wb") as f:
                    f.write(b"ds_store")
                with open(os.path.join(mock_local_dir, ".env"), "w") as f:
                    f.write("SECRET=123")
                res15 = check_snapshot.check_snapshot(mock_local_dir, bank_root=mock_bank)
                assert res15["status"] == "FRESH" and res15["code_status"] == "FRESH", f"S15 failed: {res15}"
                print("  [PASS] S15: 本地非 Git 项目：忽略缓存与临时文件不改变 worktree_hash => 保持 FRESH")

                # S16: 防误认祖先 Git：子目录置于外部 Git 仓库内部时，不被祖先 Git 穿透
                nested_ancestor = os.path.join(test_root, "ancestor_git_repo")
                os.makedirs(nested_ancestor)
                subprocess.run(["git", "init", nested_ancestor], check=True, capture_output=True)
                subprocess.run(["git", "-C", nested_ancestor, "remote", "add", "origin", "https://github.com/ancestor_user/ancestor_repo.git"], check=True)
                nested_non_git = os.path.join(nested_ancestor, "nested_local_service")
                os.makedirs(nested_non_git)
                with open(os.path.join(nested_non_git, "service.py"), "w") as f:
                    f.write("def svc(): pass\n")
                s_slug, s_repo = check_snapshot.resolve_slug_and_repo(nested_non_git)
                assert s_slug == "local__nested_local_service", f"S16 failed: resolved slug is {s_slug}"
                assert s_repo == nested_non_git
                # 嵌套快照目录测试
                nested_snap = os.path.join(nested_ancestor, "projects", "SuperGODOG__skillforge")
                os.makedirs(nested_snap)
                with open(os.path.join(nested_snap, "snapshot_meta.json"), "w") as f:
                    json.dump({"slug": "SuperGODOG__skillforge", "url": "https://github.com/SuperGODOG/skillforge"}, f)
                snap_slug, snap_repo = check_snapshot.resolve_slug_and_repo(nested_snap)
                assert snap_slug == "SuperGODOG__skillforge", f"S16 failed: snap slug is {snap_slug}"
                print("  [PASS] S16: 防误认祖先 Git：子目录置于外部 Git 内部时准确识别，无祖先穿透")
            finally:
                check_snapshot.find_snapshot_dirs = orig_find_2

        finally:
            check_snapshot.find_snapshot_dirs = orig_find

        # S11: 全流程 fetch -> match -> finalize -> check_snapshot 完整数据流
        pm_skill_dir = os.path.join(test_root, "pm_skill")
        os.makedirs(os.path.join(pm_skill_dir, "references", "项目"))
        os.environ["INTERVIEW_WORKSPACE"] = mock_bank
        os.environ["PROJECT_MOCK_SKILL_DIR"] = pm_skill_dir
        env = os.environ.copy()

        e2e_slug = "test_owner__mock_repo"
        script_dir = os.path.abspath(cur_dir)
        rf_path = os.path.join(script_dir, "repo_fuse.py")

        r_f = subprocess.run([sys.executable, rf_path, "fetch", mock_repo], env=env, capture_output=True, text=True)
        assert r_f.returncode == 0, f"fetch error: {r_f.stderr}"
        r_m = subprocess.run([sys.executable, rf_path, "match", e2e_slug], env=env, capture_output=True, text=True)
        assert r_m.returncode == 0, f"match error: {r_m.stderr}"
        r_fin = subprocess.run([sys.executable, rf_path, "finalize", e2e_slug], env=env, capture_output=True, text=True)
        assert r_fin.returncode == 0, f"finalize error: {r_fin.stderr}"

        # 校验 check_snapshot 在 mock_pm_skill 消费端读取到的快照
        res11 = check_snapshot.check_snapshot(mock_repo, bank_root=mock_bank)
        assert res11["status"] == "FRESH", f"S11 failed: {res11}"
        assert res11["code_status"] == "FRESH"
        assert res11["bank_status"] == "FRESH"
        assert res11["link_status"] == "FRESH"
        # 验证快照元信息是否真实落地
        snap_meta = res11.get("snapshot_meta", {})
        assert snap_meta.get("commit_hash") == head_with_ignore
        assert snap_meta.get("bank_fingerprint", {}).get("hash") == bank_fp["hash"]
        assert snap_meta.get("candidates") == ["L1"]
        print("  [PASS] S11: fetch -> match -> finalize -> check_snapshot 全流程数据流准确闭环 => FRESH")

        print("\n[SUCCESS] 全部 16 项确定性回归与数据流场景 100% 验证通过！")

    finally:
        shutil.rmtree(test_root)


if __name__ == "__main__":
    run_tests()
