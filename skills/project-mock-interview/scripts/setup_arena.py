#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
setup_arena.py - 提问端「面试靶场 (Interview Arena)」与平台提示词三件套自动化生成脚本

功能：
1. 建立独立面试靶场工作区（默认 interview-mock-skill/arenas/<name>/）；
2. 软链接待测项目源码（project_repo/）以支持零污染现场 grep / 源码求证；
3. 同步软链接已有项目档案（project_ref/，如 match.json / 项目内作答.md）作为参考标准；
4. 软链接分类题库索引（bank_index/）；
5. 串联生产端轻量检索工具（bank_search.py），按 Query / README / 匹配表快速召回考题；
6. 自动渲染并分发平台提示词三件套（CLAUDE.md / GEMINI.md / AGENTS.md），锁定长上下文防漂移考题大纲与打分纪律。
"""

import os
import sys
import json
import shutil
import argparse
from typing import Dict, List, Any, Optional

# 动态定位核心路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PMI_DIR = os.path.dirname(SCRIPT_DIR)
SUITE_ROOT = os.path.dirname(PMI_DIR)

# 题库与检索脚本路径
PIPELINE_SCRIPTS = os.path.join(SUITE_ROOT, "interview-bank-pipeline", "scripts")
BANK_ROOT = os.path.join(SUITE_ROOT, "agent-project-grill", "references", "题库")
BANK_ITEMS_PATH = os.path.join(BANK_ROOT, "items.json")
BANK_INDEX_PATH = os.path.join(BANK_ROOT, "索引")
PROJECT_REFS_ROOT = os.path.join(PMI_DIR, "references", "项目")
DEFAULT_ARENAS_ROOT = os.path.join(SUITE_ROOT, "arenas")

# 引入 bank_search
if PIPELINE_SCRIPTS not in sys.path:
    sys.path.insert(0, PIPELINE_SCRIPTS)

try:
    import bank_search
except ImportError:
    bank_search = None


PROMPT_TEMPLATE = """# 🎯 面试靶场：{arena_title}

> **全局约束说明**：本文件为该面试靶场的常驻系统提示词（已同步分发至 CLAUDE.md / GEMINI.md / AGENTS.md）。
> 无论本轮面试会话持续多久、经历多少轮深挖追问（Grilling）或执行了上下文压缩（/compact），**考题大纲与考评纪律始终常驻生效，严禁偏离**。

---

## 📌 靶场上下文与代码锚定 (Context & Code Anchoring)

你当前扮演极其专业的大厂技术面试官与高阶系统架构师。
1. **真实源码软链接 (`project_repo/`)**：
   - 当前工作区目录下的 `project_repo/` 为考生的真实项目源码仓库。
   - 当考生陈述技术方案、代码实现细节、架构权衡或测试指标时，你**必须主动使用 grep / search / read_file 工具查阅 `project_repo/` 中的真实代码**进行现场求证。
   - 严禁凭空轻信考生表述；严禁编造代码行号与文件路径。未在代码中体现的声称一律视为“落地证据不足”。
{ref_instruction}

---

## 📋 本场面试考题大纲（核心锚点，严禁偏离）

本场面试**必须严格围绕以下检索生产的题目展开**。按顺序一题一问，完成当前题目的打分与必要深挖（Grilling）后方可推进下一题：

{question_agenda_markdown}

---

## ⚖️ 面试流程与 Grilling 考评纪律

1. **严格一次一问**：
   - 严禁一次抛出多个复杂问题或跨题提问。
   - 严禁私自编造考题大纲之外的无关题目（如勿对纯 Python Agent 项目提问 Java 秒杀 Redis 锁）。
2. **四维打分模板（Markdown 表格）**：
   每道题用户作答完毕后，必须输出以下打分表格与评语：
   | 维度 | 得分 (1-5) | 依据与真实代码事实 |
   | :--- | :---: | :--- |
   | **概念理解** | 1-5 | 是否准确抓准核心技术概念本质与边界 |
   | **原理深度** | 1-5 | 是否通晓底层运转机制、并发控制或控制流状态机 |
   | **落地证据** | 1-5 | 是否与 `project_repo/` 实际代码与测试事实吻合 |
   | **结构完整度** | 1-5 | 是否遵循“概念认知 → 机制设计 → 工程权衡 → 落地验证”闭环 |
   
   - **评分锚点**：1=答错或严重空泛；3=方向正确但缺细节/无工程权衡；5=准确深入且带真实代码证据。
3. **Grilling 深挖触发条件**：
   - 若考生在任一维度得分 ≤ 2 分，或核心实现含糊不清，**立即切入 Grilling 追问模式**；
   - 针对该薄弱点连续深挖 2~3 个具体追问（要求对方指出具体代码文件、边界异常处理机制或数据回滚策略）；
   - 追问完毕后公布答案核心要点，随后必须立即回归考题大纲，进入下一题。
4. **进度维护**：
   - 每题打分与点评完毕后，请主动将本提示词文件对应考题的 `- [ ]` 更新为 `- [x]` 并附上综合得分，方便长会话跨轮次追踪进度。
5. **复盘沉淀**：
   - 全场考题全部结束后，将最终成绩、追问记录与薄弱点总结保存至 `outputs/session_review.md`。
"""


def find_project_slug(repo_dir: str, slug: Optional[str] = None) -> Optional[str]:
    """尝试确定项目的 slug 标识"""
    if slug:
        return slug

    # 1. 尝试匹配 references/项目/ 下的已有目录
    if os.path.isdir(PROJECT_REFS_ROOT):
        existing_slugs = [d for d in os.listdir(PROJECT_REFS_ROOT) if not d.startswith(".")]
        repo_base = os.path.basename(os.path.abspath(repo_dir))
        
        # 精确匹配
        if repo_base in existing_slugs:
            return repo_base
            
        # 模糊匹配 (owner__repo 形式，如 SuperGODOG__skillforge 匹配 skillforge)
        for s in existing_slugs:
            if s.endswith("__" + repo_base) or s == repo_base:
                return s

    return os.path.basename(os.path.abspath(repo_dir))


def recall_questions_from_match_json(ref_dir: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """从已建档项目的 match.json 中提取题目"""
    match_file = os.path.join(ref_dir, "match.json")
    if not os.path.isfile(match_file):
        return []
    try:
        with open(match_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        candidates = data.get("candidates", [])
        return candidates[:top_k]
    except Exception:
        return []


def recall_questions(
    repo_dir: str,
    slug: Optional[str] = None,
    query: Optional[str] = None,
    doc_file: Optional[str] = None,
    items_list: Optional[List[str]] = None,
    top_k: int = 3,
    expand_hops: int = 1,
) -> List[Dict[str, Any]]:
    """生产端核心召回逻辑：优先使用 bank_search 或 match.json"""
    selected_items = []

    # 1. 显式指定了题目 ID 列表 (如 L137,L210)
    if items_list:
        if bank_search and os.path.isfile(BANK_ITEMS_PATH):
            index = bank_search.get_bank_index(BANK_ITEMS_PATH)
            for qid in items_list:
                item = index.by_id.get(qid.strip())
                if item:
                    selected_items.append(item)
        if selected_items:
            return selected_items

    # 2. 已有项目 slug 且未给 query/file，尝试从 match.json 读取
    if slug and not query and not doc_file:
        ref_dir = os.path.join(PROJECT_REFS_ROOT, slug)
        matched = recall_questions_from_match_json(ref_dir, top_k=top_k)
        if matched:
            return matched

    # 3. 准备检索词：如果没有 query，尝试读取 doc_file 或 repo 的 README.md
    search_query = query or ""
    if not search_query:
        readme_candidate = doc_file or os.path.join(repo_dir, "README.md")
        if os.path.isfile(readme_candidate):
            try:
                with open(readme_candidate, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    if bank_search:
                        content = bank_search.clean_markdown_content(content)
                    search_query = content[:1500]
            except Exception:
                pass

    if not search_query:
        search_query = os.path.basename(repo_dir)

    # 4. 执行 bank_search 检索
    if bank_search and os.path.isfile(BANK_ITEMS_PATH):
        res = bank_search.search_bank(
            query=search_query,
            top_k=top_k,
            expand_hops=expand_hops,
            items_path=BANK_ITEMS_PATH
        )
        # 优先使用构建好的 progressive_trees
        trees = res.get("progressive_trees", [])
        if trees:
            for tree in trees[:top_k]:
                anchor = tree.get("anchor", {})
                anchor_copy = dict(anchor)
                anchor_copy["followups"] = tree.get("followups", [])
                anchor_copy["boundaries"] = tree.get("boundaries", [])
                selected_items.append(anchor_copy)
        else:
            selected_items = res.get("tier1_anchors", [])[:top_k]

    return selected_items


def format_agenda_markdown(items: List[Dict[str, Any]]) -> str:
    """将选中的题目转化为 Markdown 考题看板格式"""
    if not items:
        return "- [ ] 题 1 (待定): 请面试官根据 project_repo/ 代码现场抽取核心架构问题。\n"

    lines = []
    for idx, item in enumerate(items, 1):
        qid = item.get("id", f"Q{idx}")
        major = item.get("major", item.get("domain", "综合领域"))
        depth = item.get("depth", 3)
        text = item.get("text", "").strip()
        tag = item.get("tag", "") or "/".join(item.get("hit_concepts", []))
        
        lines.append(f"### - [ ] 第 {idx} 题（题号: `{qid}` ｜ 领域: `{major}` ｜ 深度: `L{depth}`）")
        lines.append(f"- **核心题目**：{text}")
        if tag:
            lines.append(f"- **考察要点/关键词**：`{tag}`")
            
        followups = item.get("followups", [])
        if followups:
            f_strs = [f"`{f.get('id', '')}` {f.get('text', '')[:45]}..." for f in followups[:2]]
            lines.append(f"- **级联追问预测**：{' ； '.join(f_strs)}")
            
        boundaries = item.get("boundaries", [])
        if boundaries:
            b_strs = [f"`{b.get('id', '')}` {b.get('text', '')[:45]}..." for b in boundaries[:1]]
            lines.append(f"- **边界延伸考点**：{' ； '.join(b_strs)}")
            
        lines.append("")

    return "\n".join(lines).strip()


def setup_arena(
    repo_dir: str,
    name: Optional[str] = None,
    arena_base_dir: Optional[str] = None,
    slug: Optional[str] = None,
    query: Optional[str] = None,
    doc_file: Optional[str] = None,
    items_list: Optional[List[str]] = None,
    top_k: int = 3,
    expand_hops: int = 1,
    force: bool = False,
) -> str:
    """初始化靶场核心函数"""
    target_repo = os.path.abspath(repo_dir)
    if not os.path.isdir(target_repo):
        raise ValueError(f"目标项目代码目录不存在: {target_repo}")

    # 1. 识别或确认项目 slug
    project_slug = find_project_slug(target_repo, slug)

    # 2. 确定靶场名称与路径
    arena_name = name or project_slug or os.path.basename(target_repo)
    arenas_root = arena_base_dir or DEFAULT_ARENAS_ROOT
    arena_dir = os.path.join(arenas_root, arena_name)

    if os.path.exists(arena_dir):
        if not force:
            raise FileExistsError(f"靶场目录已存在: {arena_dir}。请使用 --force 参数覆盖或指定不同 --name。")
        else:
            if os.path.islink(arena_dir):
                os.unlink(arena_dir)
            else:
                shutil.rmtree(arena_dir)

    # 3. 创建靶场基础目录
    os.makedirs(arena_dir, exist_ok=True)
    outputs_dir = os.path.join(arena_dir, "outputs")
    os.makedirs(outputs_dir, exist_ok=True)

    # 4. 建立源码软链接 project_repo
    repo_symlink = os.path.join(arena_dir, "project_repo")
    os.symlink(target_repo, repo_symlink)

    # 5. 建立参考档案软链接 project_ref（如果存在对应的项目档案）
    ref_instruction = ""
    if project_slug:
        project_ref_source = os.path.join(PROJECT_REFS_ROOT, project_slug)
        if os.path.isdir(project_ref_source):
            ref_symlink = os.path.join(arena_dir, "project_ref")
            os.symlink(project_ref_source, ref_symlink)
            ref_instruction = (
                "2. **参考作答与画像档案 (`project_ref/`)**：\n"
                "   - 当前工作区软链接了该项目的标准档案库（`project_ref/项目内作答.md`、`project_ref/项目画像.md`）。\n"
                "   - 考评时可参考作答档中的标准技术事实与历史证据，但不允许替代对 `project_repo/` 现场代码的真实查阅。"
            )

    # 6. 建立题库索引软链接 bank_index（如果存在）
    if os.path.isdir(BANK_INDEX_PATH):
        bank_index_symlink = os.path.join(arena_dir, "bank_index")
        os.symlink(BANK_INDEX_PATH, bank_index_symlink)

    # 7. 生产端检索题目
    recalled_items = recall_questions(
        repo_dir=target_repo,
        slug=project_slug,
        query=query,
        doc_file=doc_file,
        items_list=items_list,
        top_k=top_k,
        expand_hops=expand_hops,
    )

    # 8. 渲染考题大纲
    agenda_md = format_agenda_markdown(recalled_items)

    # 9. 渲染系统提示词母版
    master_prompt = PROMPT_TEMPLATE.format(
        arena_title=arena_name,
        ref_instruction=ref_instruction,
        question_agenda_markdown=agenda_md,
    )

    # 10. 分发提示词三件套到当前靶场根目录
    prompt_files = ["CLAUDE.md", "GEMINI.md", "AGENTS.md"]
    for p_file in prompt_files:
        p_path = os.path.join(arena_dir, p_file)
        with open(p_path, "w", encoding="utf-8") as f:
            f.write(master_prompt)

    # 11. 初始化 outputs/session_review.md 空模板
    review_path = os.path.join(outputs_dir, "session_review.md")
    if not os.path.exists(review_path):
        with open(review_path, "w", encoding="utf-8") as f:
            f.write(f"# 面试复盘与成绩单：{arena_name}\n\n- 状态：进行中\n- 开始时间：待记录\n\n## 题目考核记录\n\n")

    return arena_dir


def main():
    parser = argparse.ArgumentParser(description="一键生成面试靶场 (Interview Arena) 与平台提示词三件套")
    parser.add_argument("--repo", required=True, help="待测项目代码库绝对路径 (必填)")
    parser.add_argument("--name", help="靶场名称 (默认项目 slug 或目录名)")
    parser.add_argument("--arena-dir", help="靶场存放基准目录 (默认 interview-mock-skill/arenas/)")
    parser.add_argument("--slug", help="项目档案 slug (如 SuperGODOG__skillforge)")
    parser.add_argument("--query", help="题目检索关键词")
    parser.add_argument("--file", help="用于提取关键词的项目 README 或技术文档路径")
    parser.add_argument("--items", help="显式指定的题目 ID 列表，用逗号分隔 (如 L137,L210,L305)")
    parser.add_argument("--top", type=int, default=3, help="主干考题数量 (默认 3)")
    parser.add_argument("--expand", type=int, default=1, help="追问拓扑跳数 (默认 1)")
    parser.add_argument("--force", action="store_true", help="如果靶场目录已存在则强制覆盖")

    args = parser.parse_args()

    items_list = [i.strip() for i in args.items.split(",") if i.strip()] if args.items else None

    try:
        arena_path = setup_arena(
            repo_dir=args.repo,
            name=args.name,
            arena_base_dir=args.arena_dir,
            slug=args.slug,
            query=args.query,
            doc_file=args.file,
            items_list=items_list,
            top_k=args.top,
            expand_hops=args.expand,
            force=args.force,
        )
        print("\n" + "=" * 65)
        print(f"🎉 提问端「面试靶场」创建成功！")
        print(f"📍 靶场路径: {arena_path}")
        print(f"🔗 代码软链: {os.path.join(arena_path, 'project_repo')}")
        if os.path.exists(os.path.join(arena_path, "project_ref")):
            print(f"📑 档案软链: {os.path.join(arena_path, 'project_ref')}")
        print(f"📄 提示词已分发: CLAUDE.md / GEMINI.md / AGENTS.md (内容完全一致)")
        print("-" * 65)
        print(f"🚀 下一步：进入靶场启动您的 Agent 进行长对话模拟练习：")
        print(f"   cd \"{arena_path}\"")
        print(f"   # 启动 Claude Code:  claude")
        print(f"   # 或启动 Gemini:     gemini")
        print(f"   # 或启动 Codex Agent")
        print("=" * 65 + "\n")
    except Exception as e:
        print(f"❌ 靶场创建失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
