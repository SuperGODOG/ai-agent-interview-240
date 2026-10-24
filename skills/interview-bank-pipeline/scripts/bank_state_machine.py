#!/usr/bin/env python3
"""
bank_state_machine.py - 题库读写状态机引擎 (Interview Bank State Machine)

架构模式：
  1. READY 状态 (服务/读取态)：
     - items.json 四端镜像 100% SHA-256 强一致
     - 供模拟面试引擎、题库查询、文档站点使用
  2. INGESTING 状态 (写入/暂存态)：
     - 极轻量 Append-Only 到 .staging/ 缓冲区 (秒级落盘，杜绝网络长连接断流)
     - 仅做基础 Schema 快速校验与初步语义查重提示
  3. COMPILING 状态 (编译合并态)：
     - 全局汇总暂存池，统一分配 L{ID}
     - 跨批次全局双向关系边推导与闭环
     - 四端镜像同步 + 16项快照回归测试 + 百科与站点自动生成
     - 校验通过后原子发布，恢复 READY 状态
"""

import os
import sys
import json
import glob
import time
import shutil
import hashlib
import argparse
import subprocess
from pathlib import Path

# 基础路径配置
CANONICAL_ITEMS = Path("/Users/caoruixin/Desktop/skills/interview-mock-skill/agent-project-grill/references/题库/items.json")
STAGING_DIR = Path("/Users/caoruixin/Desktop/skills/interview-mock-skill/agent-project-grill/references/题库/.staging")

MIRRORS = [
    Path("/Users/caoruixin/Desktop/project/ai-agent-interview-240/skills/agent-project-grill/references/题库/items.json"),
    Path("/Users/caoruixin/.cc-switch/skills/agent-project-grill/references/题库/items.json"),
    Path("/Users/caoruixin/.hermes/skills/agent-project-grill/references/题库/items.json"),
]

SCRIPT_DIR = Path(__file__).resolve().parent
CLEANER_SCRIPT = SCRIPT_DIR / "bank_cleaner.py"
REGRESSION_SCRIPT = SCRIPT_DIR / "test_snapshot_regression.py"
BAIKE_SCRIPT = Path("/Users/caoruixin/Desktop/project/ai-agent-interview-240/scripts/generate_baike.py")
MKDOCS_SCRIPT = Path("/Users/caoruixin/Desktop/project/ai-agent-interview-240/scripts/gen_mkdocs.py")

VALID_DOMAINS = {
    "A_AGENT": "二_Agent应用开发相关",
    "B_BACKEND": "四_八股相关",
    "F_FRONTEND": "全栈与前端工程交互",
    "I_INFRA": "六_AI_Infra与高性能算子",
    "S_ALGO_GENERAL": "Leetcode相关",
}

def compute_sha256(filepath: Path) -> str:
    """计算文件 SHA-256 指纹"""
    if not filepath.exists():
        return "FILE_NOT_FOUND"
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def ensure_dirs():
    """确保 staging 目录及其归档目录存在"""
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    (STAGING_DIR / "archive").mkdir(parents=True, exist_ok=True)
    (STAGING_DIR / "aborted").mkdir(parents=True, exist_ok=True)

def get_staged_files():
    """获取所有待编译的暂存批次文件"""
    ensure_dirs()
    files = sorted(glob.glob(str(STAGING_DIR / "batch_*.json")))
    return [Path(p) for p in files]

def load_canonical_items():
    """读取主库 items.json"""
    if not CANONICAL_ITEMS.exists():
        raise FileNotFoundError(f"主库文件不存在: {CANONICAL_ITEMS}")
    with open(CANONICAL_ITEMS, "r", encoding="utf-8") as f:
        return json.load(f)

def get_max_question_id(items):
    """获取现有题库中的最大 L 编号"""
    max_id = 0
    for it in items:
        qid = it.get("id", "")
        if qid.startswith("L") and qid[1:].isdigit():
            max_id = max(max_id, int(qid[1:]))
    return max_id

def cmd_status():
    """查询状态机状态与题库健康度"""
    ensure_dirs()
    staged_files = get_staged_files()
    total_staged_questions = 0
    staged_details = []
    for sf in staged_files:
        try:
            with open(sf, "r", encoding="utf-8") as f:
                data = json.load(f)
                count = len(data) if isinstance(data, list) else 1
                total_staged_questions += count
                staged_details.append(f"  - {sf.name}: {count} 题")
        except Exception as e:
            staged_details.append(f"  - {sf.name}: 解析错误 ({e})")

    items = load_canonical_items()
    max_id = get_max_question_id(items)
    q_count = sum(1 for it in items if it.get("kind") == "question")
    total_records = len(items)

    canonical_hash = compute_sha256(CANONICAL_ITEMS)
    hash_matched = True
    mirror_hashes = []
    for m in MIRRORS:
        h = compute_sha256(m)
        mirror_hashes.append((m, h))
        if h != canonical_hash:
            hash_matched = False

    state = "INGESTING (写入暂存中)" if total_staged_questions > 0 else "READY (读就绪)"
    
    print("=" * 60)
    print(f"【题库状态机状态】: {state}")
    print("=" * 60)
    print(f"主库记录总数: {total_records} | 实际题目数: {q_count} | 当前最高编号: L{max_id}")
    print(f"暂存池 (.staging): 共有 {len(staged_files)} 个批次文件，累计 {total_staged_questions} 道待合并题目")
    for d in staged_details:
        print(d)
    
    print("-" * 60)
    print(f"主库指纹 (Canonical SHA-256): {canonical_hash[:16]}...")
    if hash_matched:
        print("四端同步状态: [PASS] 4 处镜像 100% SHA-256 完全一致")
    else:
        print("四端同步状态: [WARNING] 镜像文件存在指纹偏差，需在 compile 时同步：")
        for m, h in mirror_hashes:
            match_str = "MATCH" if h == canonical_hash else "MISMATCH"
            print(f"  - {m.parent.parent.name}: {h[:16]}... [{match_str}]")
    print("=" * 60)

def cmd_stage(input_path_str: str):
    """将新题目文件推入 .staging 暂存区"""
    ensure_dirs()
    input_path = Path(input_path_str)
    if not input_path.exists():
        print(f"[ERROR] 输入文件不存在: {input_path}")
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        if "items" in data:
            data = data["items"]
        elif "questions" in data:
            data = data["questions"]
        else:
            data = [data]

    if not isinstance(data, list) or len(data) == 0:
        print("[ERROR] 输入数据必须是非空题目列表")
        sys.exit(1)

    # 基础 schema 快速校验
    canonical_items = load_canonical_items()
    existing_texts = {it.get("text", "")[:40]: it.get("id") for it in canonical_items if it.get("text")}

    validated_questions = []
    for idx, q in enumerate(data):
        text = q.get("text", "").strip()
        domain = q.get("domain", "").strip()
        depth = q.get("depth", 2)
        minor = q.get("minor", "").strip()
        major = q.get("major", "").strip()

        if not text:
            print(f"[ERROR] 第 {idx+1} 题缺失 text 内容")
            sys.exit(1)
        if domain not in VALID_DOMAINS:
            print(f"[ERROR] 第 {idx+1} 题 domain 无效: '{domain}'. 有效领域: {list(VALID_DOMAINS.keys())}")
            sys.exit(1)
        if depth not in [1, 2, 3, 4]:
            print(f"[ERROR] 第 {idx+1} 题 depth 无效: {depth}. 必须是 1~4 整数")
            sys.exit(1)
        if not minor:
            print(f"[ERROR] 第 {idx+1} 题缺失 minor 流派分类")
            sys.exit(1)
        if not major:
            major = VALID_DOMAINS[domain]

        # 查重预警 (不阻断，但提示)
        prefix = text[:40]
        if prefix in existing_texts:
            print(f"[WARN] 第 {idx+1} 题与已有题号 {existing_texts[prefix]} 高度相似: {prefix}...")

        # 归一化 tag 与 关系列表
        tag = q.get("tag", "")
        if isinstance(tag, list):
            tag = "/".join(tag)

        clean_q = {
            "text": text,
            "domain": domain,
            "major": major,
            "minor": minor,
            "depth": depth,
            "tag": tag,
            "prereq": q.get("prereq", []),
            "downstream": q.get("downstream", []),
            "relations": q.get("relations", []),
        }
        validated_questions.append(clean_q)

    timestamp = int(time.time())
    stem = input_path.stem.replace(" ", "_")
    target_file = STAGING_DIR / f"batch_{timestamp}_{stem}.json"

    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(validated_questions, f, ensure_ascii=False, indent=2)

    print(f"[STAGE SUCCESS] 成功暂存 {len(validated_questions)} 道题目 -> {target_file.name}")
    print("状态机已进入: INGESTING (写入暂存态)")

def cmd_compile(sync: bool = True, run_tests: bool = True, gen_docs: bool = True):
    """编译合并所有暂存题目，更新图谱，并执行全流程校验"""
    ensure_dirs()
    staged_files = get_staged_files()
    if not staged_files:
        print("[INFO] 暂存池为空，没有需要编译的题目。状态保持 READY。")
        return

    print("=" * 60)
    print("【开始编译合并 (COMPILING)】")
    print(f"检测到 {len(staged_files)} 个暂存批次文件，开始加载...")
    print("=" * 60)

    # 1. 创建备份
    bak_path = CANONICAL_ITEMS.with_suffix(".json.bak")
    shutil.copy2(CANONICAL_ITEMS, bak_path)
    print(f"[BACKUP] 已创建灾备文件: {bak_path.name}")

    try:
        canonical_items = load_canonical_items()
        item_by_id = {it.get("id"): it for it in canonical_items if "id" in it}
        max_id = get_max_question_id(canonical_items)
        next_id = max_id + 1

        all_new_questions = []
        for sf in staged_files:
            with open(sf, "r", encoding="utf-8") as f:
                batch = json.load(f)
                all_new_questions.extend(batch)

        print(f"[ID ALLOCATION] 将为 {len(all_new_questions)} 道新题目分配编号: L{next_id} ~ L{next_id + len(all_new_questions) - 1}")

        # 2. 分配 ID 并推导双向边
        assigned_items = []
        for q in all_new_questions:
            qid = f"L{next_id}"
            next_id += 1
            
            line_no = len(canonical_items) + len(assigned_items) + 1
            item_entry = {
                "id": qid,
                "kind": "question",
                "domain": q["domain"],
                "major": q["major"],
                "minor": q["minor"],
                "depth": q["depth"],
                "text": q["text"],
                "tag": q["tag"],
                "status": "ready",
                "prereq": q.get("prereq", []),
                "downstream": q.get("downstream", []),
                "relations": q.get("relations", []),
                "line": line_no,
                "assigned": True,
                "in_comment": False,
                "comment_label": ""
            }
            assigned_items.append(item_entry)
            item_by_id[qid] = item_entry

        # 3. 补全双向 reciprocal 关系边
        print("[GRAPH LINKING] 自动补全图谱双向边与 reciprocal 关系...")
        for item in assigned_items:
            qid = item["id"]
            # 处理 prereq 目标节点：给前置节点补上 downstream = qid
            for pre in item.get("prereq", []):
                if pre in item_by_id:
                    target_item = item_by_id[pre]
                    target_downstream = target_item.setdefault("downstream", [])
                    if qid not in target_downstream:
                        target_downstream.append(qid)
                    # 补齐 target 的 relations
                    target_rels = target_item.setdefault("relations", [])
                    if not any(r.get("target") == qid for r in target_rels):
                        target_rels.append({
                            "target": qid,
                            "type": "progressive",
                            "direction": "out",
                            "reason": f"从前置问题进阶拓展至 {qid}"
                        })

            # 处理 downstream 目标节点：给后置节点补上 prereq = qid
            for down in item.get("downstream", []):
                if down in item_by_id:
                    target_item = item_by_id[down]
                    target_prereq = target_item.setdefault("prereq", [])
                    if qid not in target_prereq:
                        target_prereq.append(qid)
                    # 补齐 target 的 relations
                    target_rels = target_item.setdefault("relations", [])
                    if not any(r.get("target") == qid for r in target_rels):
                        target_rels.append({
                            "target": qid,
                            "type": "progressive",
                            "direction": "in",
                            "reason": f"由前置问题 {qid} 引申至当前问题"
                        })

        # 4. 追加写入主库
        canonical_items.extend(assigned_items)
        with open(CANONICAL_ITEMS, "w", encoding="utf-8") as f:
            json.dump(canonical_items, f, ensure_ascii=False, indent=2)
        print(f"[CANONICAL SAVED] 主库已写入完成，当前总记录: {len(canonical_items)}")

        # 5. 四端镜像同步
        if sync:
            print("[SYNC] 正在执行四端镜像哈希对齐同步...")
            for mirror in MIRRORS:
                mirror.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(CANONICAL_ITEMS, mirror)
            
            # SHA-256 校验
            c_hash = compute_sha256(CANONICAL_ITEMS)
            for m in MIRRORS:
                m_hash = compute_sha256(m)
                if m_hash != c_hash:
                    raise RuntimeError(f"四端同步校验失败: {m} 哈希不匹配！")
            print(f"[SYNC PASS] 四端镜像 SHA-256 100% 对齐 ({c_hash[:16]}...)")

        # 6. 回归测试
        if run_tests:
            print("[TEST] 运行金字塔结构与快照回归测试...")
            res_cleaner = subprocess.run([sys.executable, str(CLEANER_SCRIPT), "--check"], capture_output=True, text=True)
            if res_cleaner.returncode != 0:
                print(res_cleaner.stderr)
                raise RuntimeError("bank_cleaner 校验未通过！")

            res_reg = subprocess.run([sys.executable, str(REGRESSION_SCRIPT)], capture_output=True, text=True)
            if res_reg.returncode != 0:
                print(res_reg.stderr)
                raise RuntimeError("test_snapshot_regression 回归测试失败！")
            print("[TEST PASS] 16 项快照回归测试与图谱完整性 100% 通过！")

        # 7. 文档生成
        if gen_docs:
            print("[DOCS] 重新生成百科与静态文档站点...")
            if BAIKE_SCRIPT.exists():
                subprocess.run([sys.executable, str(BAIKE_SCRIPT)], check=True, capture_output=True)
            if MKDOCS_SCRIPT.exists():
                subprocess.run([sys.executable, str(MKDOCS_SCRIPT)], check=True, capture_output=True)
            print("[DOCS PASS] 百科 Markdown 分卷与 MkDocs 站点重新构建完成！")

        # 8. 归档暂存批次
        for sf in staged_files:
            archive_target = STAGING_DIR / "archive" / sf.name
            shutil.move(str(sf), str(archive_target))
        print(f"[ARCHIVE] 已归档 {len(staged_files)} 个批次文件至 .staging/archive/")

        # 9. 移除备份
        if bak_path.exists():
            bak_path.unlink()

        print("=" * 60)
        print(f"【编译发布完成 (SUCCESS)】新增 {len(assigned_items)} 道题目，最新题号 L{next_id - 1}")
        print("状态机恢复为: READY (读就绪态)")
        print("=" * 60)

    except Exception as e:
        print(f"\n[COMPILE ERROR] 编译过程中断: {e}")
        print("[ROLLBACK] 正在从备份文件自动恢复主库...")
        if bak_path.exists():
            shutil.copy2(bak_path, CANONICAL_ITEMS)
            for m in MIRRORS:
                shutil.copy2(bak_path, m)
            bak_path.unlink()
            print("[ROLLBACK SUCCESS] 已完全回滚至编译前状态。")
        sys.exit(1)

def cmd_abort():
    """中止并清空当前暂存区"""
    ensure_dirs()
    staged_files = get_staged_files()
    if not staged_files:
        print("[INFO] 暂存池无待清空内容。")
        return
    for sf in staged_files:
        target = STAGING_DIR / "aborted" / sf.name
        shutil.move(str(sf), str(target))
    print(f"[ABORT] 已将 {len(staged_files)} 个暂存批次移入 .staging/aborted/，状态恢复为 READY。")

def main():
    parser = argparse.ArgumentParser(description="题库读写状态机引擎")
    subparsers = parser.add_subparsers(dest="command")

    # status
    subparsers.add_parser("status", help="查看当前状态机状态与健康度")

    # stage
    stage_parser = subparsers.add_parser("stage", help="暂存一批题目进 .staging 缓冲池")
    stage_parser.add_argument("file", help="JSON 题目文件路径")

    # compile
    compile_parser = subparsers.add_parser("compile", help="编译合并暂存区题目至主库并同步测试")
    compile_parser.add_argument("--no-sync", action="store_true", help="跳过四端同步")
    compile_parser.add_argument("--no-test", action="store_true", help="跳过回归测试")
    compile_parser.add_argument("--no-docs", action="store_true", help="跳过百科与站点文档生成")

    # abort
    subparsers.add_parser("abort", help="废弃当前暂存池内容")

    args = parser.parse_args()
    if args.command == "status" or not args.command:
        cmd_status()
    elif args.command == "stage":
        cmd_stage(args.file)
    elif args.command == "compile":
        cmd_compile(sync=not args.no_sync, run_tests=not args.no_test, gen_docs=not args.no_docs)
    elif args.command == "abort":
        cmd_abort()

if __name__ == "__main__":
    main()
