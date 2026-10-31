#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_bank_search.py - bank_search.py 单元测试与基准评测套件
"""

import os
import sys
import time
import json
import unittest

# 将当前目录加入 sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bank_search import search_bank, tokenize, expand_query_tokens, DEFAULT_ITEMS_PATH


class TestBankSearch(unittest.TestCase):

    def test_01_tokenization(self):
        """测试分词与中英文混合提取"""
        q = "Harness 双智能体 审核 有界循环 redis"
        toks = tokenize(q)
        self.assertIn("harness", toks)
        self.assertIn("redis", toks)
        self.assertTrue(any("审核" in t for t in toks))
        self.assertTrue(any("循环" in t for t in toks))

    def test_02_synonym_expansion(self):
        """测试派生词与同义词映射规则"""
        toks = ["harness"]
        expanded = expand_query_tokens(toks)
        self.assertIn("审核", expanded)
        self.assertIn("有界循环", expanded)

    def test_03_harness_search_and_graph_hop(self):
        """测试 Harness 搜索与核心追问的拓扑级联召回"""
        t0 = time.time()
        res = search_bank("Harness 审核智能体 有界循环", domain="A_AGENT", top_k=3, expand_hops=1)
        latency_ms = (time.time() - t0) * 1000

        self.assertGreater(res["total_anchors"], 0, "主干题召回数应 > 0")
        self.assertGreater(res["total_cascaded"], 0, "图谱级联追问数应 > 0")

        anchor_ids = [a["id"] for a in res["anchors"]]
        cascaded_ids = [c["id"] for c in res["cascaded"]]
        all_ids = set(anchor_ids + cascaded_ids)

        print(f"\n[Test 03] Harness 查询耗时: {latency_ms:.2f}ms")
        print(f"  主干题: {anchor_ids}")
        print(f"  级联追问: {cascaded_ids[:5]}...")

        # 验证核心主干 L805 或 L830 是否被捕获
        self.assertTrue("L805" in all_ids or "L830" in all_ids or "L761" in all_ids, "应当捕获 Harness/审核核心题")
        # 验证追问题是否被级联带出 (例如 L760, L761, L762, L870 等)
        has_followup = any(id_ in all_ids for id_ in ["L760", "L761", "L762", "L763", "L811", "L870", "L874"])
        self.assertTrue(has_followup, "应当通过拓扑级联召回深度追问题")
        self.assertLess(latency_ms, 50, "执行耗时应严格小于 50ms")

    def test_04_backend_miaosha_search(self):
        """测试高并发后端秒杀场景的主干与追问检索"""
        res = search_bank("秒杀 Lua 预扣库存 延时双删", domain="B_BACKEND", top_k=3, expand_hops=1)
        self.assertGreater(res["total_anchors"], 0)
        self.assertGreater(res["total_cascaded"], 0)
        all_ids = set([a["id"] for a in res["anchors"]] + [c["id"] for c in res["cascaded"]])
        # 检查是否关联出秒杀、缓存一致性等经典题
        print(f"\n[Test 04] 后端秒杀场景捕获题号: {list(all_ids)[:6]}")

    def test_05_algo_search(self):
        """测试算法题精确检索（如大数加法）"""
        res = search_bank("大数加法 字符串相加", top_k=3, expand_hops=0)
        self.assertGreater(res["total_anchors"], 0)
        anchor_texts = [a["text"] for a in res["anchors"]]
        self.assertTrue(any("大数加法" in t for t in anchor_texts))
        self.assertEqual(res["anchors"][0]["id"], "L882")

    def test_06_domain_filtering_strictness(self):
        """测试板块隔离的严谨性"""
        res_backend = search_bank("MySQL 事务 隔离级别", domain="B_BACKEND", top_k=5)
        for a in res_backend["anchors"]:
            self.assertEqual(a["domain"], "B_BACKEND")

    def test_07_empty_query_robustness(self):
        """测试空查询或无匹配词的边界容错"""
        res = search_bank("xyzabcdefg_non_existent_token_9999", top_k=5)
        self.assertEqual(res["total_anchors"], 0)
        self.assertEqual(res["total_cascaded"], 0)


if __name__ == "__main__":
    unittest.main()
