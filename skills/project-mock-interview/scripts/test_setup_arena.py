#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_setup_arena.py - setup_arena.py 的单元测试与功能验证套件
"""

import os
import sys
import shutil
import tempfile
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import setup_arena


class TestSetupArena(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 创建临时模拟代码仓库
        cls.temp_dir = tempfile.mkdtemp(prefix="test_arena_env_")
        cls.mock_repo = os.path.join(cls.temp_dir, "mock_agent_repo")
        os.makedirs(cls.mock_repo, exist_ok=True)
        
        # 写入一个简单的 mock 文件与 README
        with open(os.path.join(cls.mock_repo, "README.md"), "w", encoding="utf-8") as f:
            f.write("# Mock Agent Project\n\n基于 ReAct 范式与 SQLite 记忆机制的 Agent 系统。\n")
        with open(os.path.join(cls.mock_repo, "main.py"), "w", encoding="utf-8") as f:
            f.write("def run_agent(): pass\n")
            
        cls.custom_arena_base = os.path.join(cls.temp_dir, "custom_arenas")

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.temp_dir):
            shutil.rmtree(cls.temp_dir)

    def test_01_create_arena_with_items_list(self):
        """测试指定题目 ID 列表建场，并验证软链接与三份提示词"""
        arena_dir = setup_arena.setup_arena(
            repo_dir=self.mock_repo,
            name="test_arena_items",
            arena_base_dir=self.custom_arena_base,
            items_list=["L137", "L870"],
            force=True
        )

        self.assertTrue(os.path.isdir(arena_dir))
        
        # 验证软链接
        repo_link = os.path.join(arena_dir, "project_repo")
        self.assertTrue(os.path.islink(repo_link))
        self.assertTrue(os.path.isfile(os.path.join(repo_link, "main.py")))

        # 验证 outputs 目录
        self.assertTrue(os.path.isdir(os.path.join(arena_dir, "outputs")))
        self.assertTrue(os.path.isfile(os.path.join(arena_dir, "outputs", "session_review.md")))

        # 验证三份提示词存在且内容完全一致
        claude_path = os.path.join(arena_dir, "CLAUDE.md")
        gemini_path = os.path.join(arena_dir, "GEMINI.md")
        agents_path = os.path.join(arena_dir, "AGENTS.md")

        self.assertTrue(os.path.isfile(claude_path))
        self.assertTrue(os.path.isfile(gemini_path))
        self.assertTrue(os.path.isfile(agents_path))

        with open(claude_path, "r", encoding="utf-8") as f:
            claude_content = f.read()
        with open(gemini_path, "r", encoding="utf-8") as f:
            gemini_content = f.read()
        with open(agents_path, "r", encoding="utf-8") as f:
            agents_content = f.read()

        self.assertEqual(claude_content, gemini_content)
        self.assertEqual(claude_content, agents_content)

        # 验证题目注入
        self.assertIn("L137", claude_content)
        self.assertIn("L870", claude_content)
        self.assertIn("project_repo/", claude_content)
        self.assertIn("四维打分模板", claude_content)

    def test_02_query_search_and_expansion(self):
        """测试通过关键词检索建场与拓扑追问渲染"""
        arena_dir = setup_arena.setup_arena(
            repo_dir=self.mock_repo,
            name="test_arena_query",
            arena_base_dir=self.custom_arena_base,
            query="LangGraph 状态机",
            top_k=2,
            expand_hops=1,
            force=True
        )

        claude_path = os.path.join(arena_dir, "CLAUDE.md")
        with open(claude_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("第 1 题", content)
        self.assertIn("核心题目", content)

    def test_03_project_ref_symlink_for_existing_slug(self):
        """测试对已有项目 slug (如 SuperGODOG__skillforge) 自动软链接 project_ref"""
        arena_dir = setup_arena.setup_arena(
            repo_dir=self.mock_repo,
            name="test_arena_slug",
            arena_base_dir=self.custom_arena_base,
            slug="SuperGODOG__skillforge",
            top_k=2,
            force=True
        )

        ref_link = os.path.join(arena_dir, "project_ref")
        self.assertTrue(os.path.islink(ref_link))
        # 验证能读取项目内作答.md
        self.assertTrue(os.path.isfile(os.path.join(ref_link, "项目画像.md")))

        claude_path = os.path.join(arena_dir, "CLAUDE.md")
        with open(claude_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("project_ref/", content)
        self.assertIn("参考作答与画像档案", content)

    def test_04_force_overwrite_protection(self):
        """测试已存在靶场的覆盖保护与 --force 行为"""
        arena_name = "test_arena_overwrite"
        # 首次创建
        setup_arena.setup_arena(
            repo_dir=self.mock_repo,
            name=arena_name,
            arena_base_dir=self.custom_arena_base,
            top_k=1,
            force=True
        )

        # 未提供 force 再次创建，预期引发 FileExistsError
        with self.assertRaises(FileExistsError):
            setup_arena.setup_arena(
                repo_dir=self.mock_repo,
                name=arena_name,
                arena_base_dir=self.custom_arena_base,
                top_k=1,
                force=False
            )

        # 提供 force=True 覆盖创建，预期成功
        arena_dir = setup_arena.setup_arena(
            repo_dir=self.mock_repo,
            name=arena_name,
            arena_base_dir=self.custom_arena_base,
            top_k=1,
            force=True
        )
        self.assertTrue(os.path.isdir(arena_dir))


if __name__ == "__main__":
    unittest.main()
