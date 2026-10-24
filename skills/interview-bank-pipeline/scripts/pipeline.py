#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""面试文档清洗分类管道 —— 机械部分（切分/合并/审计/校验）

用法:
  python3 pipeline.py split      # 切分源文档 -> items.json + batches/batch_XX.json
  python3 pipeline.py merge      # 汇总分类结果 -> categories/<大类>/<小类>.md
  python3 pipeline.py audit      # 审计: 覆盖/重复/空类/未分类 -> audit_report.md
  python3 pipeline.py validate   # 校验已提交的分类结果 JSON
  python3 pipeline.py export     # 导出图谱；无断链后同步题库到主入口
  python3 pipeline.py sync-bank  # 校验并同步 workspace 题库到主入口

判断部分（意图识别/递归细分/逻辑排序）由 subagent 完成，
subagent 只读写 batches/classified/ 与 categories/ 下的文件。
"""
import json
import os
import re
import sys

ROOT = os.environ.get("INTERVIEW_WORKSPACE") or (os.path.expanduser("~/.interview-workbench") if os.path.isdir(os.path.expanduser("~/.interview-workbench")) else os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "agent_review.md")

if not os.path.isdir(ROOT) or not (os.path.isfile(SRC) or os.path.isdir(os.path.join(ROOT, "categories"))):
    print(f"警告: 工作区 {ROOT} 中未找到 agent_review.md / categories/。"
          "请设置 INTERVIEW_WORKSPACE 指向真实数据目录（如 export INTERVIEW_WORKSPACE=$HOME/.interview-workbench），"
          "或确认旧路径 ~/.interview-workbench 存在。", file=sys.stderr)
BATCH_DIR = os.path.join(ROOT, "batches")
CLS_DIR = os.path.join(BATCH_DIR, "classified")
CAT_DIR = os.path.join(ROOT, "categories")
ITEMS_JSON = os.path.join(ROOT, "items.json")
SCHEMA_JSON = os.path.join(ROOT, "schema.json")
BATCH_SIZE = 48
DEPTH_LABELS = {1: "概念定义", 2: "原理机制", 3: "设计与方案", 4: "落地与权衡", 5: "前沿与延伸"}

# ---------------- 题库分发 ----------------

def sync_bank():
    """workspace 是编辑区；主入口保存唯一随包分发的题库。"""
    from pathlib import Path
    import tempfile

    # realpath 支持从 Hermes 等软链入口调用，不依赖当前工作目录。
    hub = Path(__file__).resolve().parents[2] / "agent-project-grill"
    if not (hub / "SKILL.md").is_file():
        print("降级: 未安装相邻 agent-project-grill，题库仅保留在 workspace；"
              "请整包安装后重跑 sync-bank。", file=sys.stderr)
        return False

    import yaml

    # 全部源文件读取、解析、基本结构校验通过后，才允许接触目标目录。
    names = ("items.json", "concepts.yaml", "schema.json")
    payloads = {}
    for name in names:
        source = Path(ROOT) / name
        try:
            payloads[name] = source.read_bytes()
        except OSError as exc:
            raise ValueError(f"题库同步取消: 无法读取 {source}；目标题库未修改") from exc
    try:
        items = json.loads(payloads["items.json"])
        schema = json.loads(payloads["schema.json"])
        concepts = yaml.safe_load(payloads["concepts.yaml"])
        if (not isinstance(items, list) or not items
                or not all(isinstance(it, dict) and isinstance(it.get("id"), str)
                           and isinstance(it.get("kind"), str)
                           and isinstance(it.get("text"), str) for it in items)
                or not any(it["kind"] == "question" for it in items)):
            raise ValueError("items.json 必须包含有效题目列表")
        if (not isinstance(schema, dict) or not isinstance(schema.get("majors"), list)
                or not schema["majors"]
                or not all(isinstance(m, dict) and isinstance(m.get("name"), str)
                           and isinstance(m.get("minors"), list) for m in schema["majors"])):
            raise ValueError("schema.json 必须包含 majors 分类列表")
        if (not isinstance(concepts, dict) or not isinstance(concepts.get("concepts"), list)
                or not concepts["concepts"]
                or not all(isinstance(c, dict) and isinstance(c.get("name"), str)
                           and isinstance(c.get("keywords"), list)
                           for c in concepts["concepts"])):
            raise ValueError("concepts.yaml 必须包含 concepts 概念列表")
    except (ValueError, UnicodeError, yaml.YAMLError) as exc:
        raise ValueError(f"题库同步取消: 源数据非法 ({exc})；目标题库未修改") from exc

    target = hub / "references" / "题库"
    target.mkdir(parents=True, exist_ok=True)
    # 先暂存完整三文件，再逐文件原子替换，避免写入被截断的文件。
    with tempfile.TemporaryDirectory(prefix=".sync-bank-", dir=target.parent) as stage:
        for name in names:
            (Path(stage) / name).write_bytes(payloads[name])
        for name in names:
            os.replace(Path(stage) / name, target / name)
    print(f"题库已同步到 {target}；请在真理源仓库审查并 git 提交。")
    return True


# ---------------- 文本处理 ----------------

HEADING_MAJOR_RE = re.compile(r"^[一二三四五六七八九十]+[、。:：]")
HEADING_ROMAN_RE = re.compile(r"^[IVX]+、")
HEADING_MINOR_RE = re.compile(r"^\d+\.\s*\S")
HEADING_NAMED_RE = re.compile(r"^(Leetcode相关|反问|国企特别版)[:：]?$")
TAG_RE = re.compile(r"^\(.*\)$")
Q_MARK = re.compile(r"[？?]")


def slug(text: str) -> str:
    s = re.sub(r"[、。：:：]+", "_", text.strip()).strip("_")
    s = re.sub(r"\s+", "_", s)
    return s


def clean_text(raw: str) -> str:
    t = raw.strip()
    if t.startswith("<!--"):
        t = t[4:].strip()
    if t.endswith("-->"):
        t = t[:-3].strip()
    return t


def classify_line(text: str):
    """返回 (kind, display)  kind: major|roman|minor|named|tag|question"""
    if HEADING_MAJOR_RE.match(text):
        return "major", text
    if HEADING_ROMAN_RE.match(text):
        return "roman", text
    if HEADING_MINOR_RE.match(text):
        return "minor", text
    if HEADING_NAMED_RE.match(text):
        return "named", text
    if TAG_RE.match(text):
        return "tag", text
    return "question", text


# ---------------- split ----------------

def split():
    with open(SRC, encoding="utf-8") as f:
        raw_lines = f.readlines()

    items = []
    in_comment = False
    comment_label = None

    for i, raw in enumerate(raw_lines, start=1):
        line = raw.rstrip("\n")
        if not line.strip():
            continue
        had_open = "<!--" in line
        had_close = "-->" in line
        if had_open and not in_comment:
            in_comment = True
            # 注释块标题: 去掉 <!-- 后若不像问题(无问号且较短)则记为标题
            rest = line.split("<!--", 1)[1].strip()
            if not Q_MARK.search(rest) and len(rest) <= 20:
                comment_label = rest.rstrip("：:")
                items.append({
                    "id": f"L{i}", "line": i, "kind": "comment_title",
                    "text": clean_text(line), "in_comment": True,
                    "comment_label": comment_label, "major": None, "minor": None,
                    "tag": None, "assigned": False, "depth": None,
                })
                if had_close:
                    in_comment = False
                    comment_label = None
                continue
            if comment_label is None:
                comment_label = "未命名注释块"
        text = clean_text(line)
        kind, disp = classify_line(text)
        item = {
            "id": f"L{i}", "line": i, "kind": kind,
            "text": text, "in_comment": in_comment,
            "comment_label": comment_label if in_comment else None,
            "major": None, "minor": None, "tag": None,
            "assigned": False, "depth": None,
        }
        items.append(item)
        if had_close:
            in_comment = False
            comment_label = None

    # 遍历: 为真实结构条目预分配 major/minor/tag (注释块内条目保持 assigned=False)
    major = minor = tag = None
    for it in items:
        if it["in_comment"]:
            continue
        if it["kind"] in ("major", "named"):
            major = it["text"]
            minor = None
            tag = None
        elif it["kind"] == "roman":
            major = it["text"]  # 理论上不会走到(roman 都在注释块内), 防御
            minor = None
        elif it["kind"] == "minor":
            minor = it["text"]
            tag = None
        elif it["kind"] == "tag":
            tag = it["text"].strip("()")
            continue
        if it["kind"] == "question" and major:
            it["major"] = slug(major)
            it["minor"] = slug(minor) if minor else slug(major)
            it["tag"] = tag
            it["assigned"] = True

    with open(ITEMS_JSON, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)

    # schema.json: 大类/小类清单 (由真实标题派生)
    majors = {}
    order = []
    cur = None
    for it in items:
        if it["kind"] == "major" and not it["in_comment"]:
            cur = slug(it["text"])
            if cur not in majors:
                majors[cur] = {"name": cur,
                               "display": it["text"].rstrip("：:").replace("。", "、"),
                               "minors": []}
                order.append(cur)
        elif it["kind"] == "named" and not it["in_comment"]:
            cur = slug(it["text"])
            if cur not in majors:
                majors[cur] = {"name": cur,
                               "display": it["text"].rstrip("：:"), "minors": []}
                order.append(cur)
        elif it["kind"] == "minor" and not it["in_comment"] and cur:
            mn = slug(it["text"])
            if mn not in majors[cur]["minors"]:
                majors[cur]["minors"].append(mn)
    for m in order:  # 无编号小类的大类, 用自身作小类
        if not majors[m]["minors"]:
            majors[m]["minors"].append(m)
    schema = {"majors": [majors[n] for n in order]}
    with open(SCHEMA_JSON, "w", encoding="utf-8") as f:
        json.dump(schema, f, ensure_ascii=False, indent=1)

    # 分批次: 需要判断的题目 = 所有 question 且 major 不在直接归档小类(反问/国企特别版)
    direct = {"反问", "国企特别版"}
    todo = [it for it in items if it["kind"] == "question"
            and not (it["assigned"] and it["major"] in {slug(d) for d in direct})]
    for it in items:
        if it["kind"] == "question" and it["assigned"] and it["major"] in {slug(d) for d in direct}:
            it["depth"] = 1  # 单题大类直接归档

    os.makedirs(CLS_DIR, exist_ok=True)
    for old in os.listdir(CLS_DIR):
        os.remove(os.path.join(CLS_DIR, old))
    nb = (len(todo) + BATCH_SIZE - 1) // BATCH_SIZE
    for b in range(nb):
        chunk = todo[b * BATCH_SIZE:(b + 1) * BATCH_SIZE]
        with open(os.path.join(BATCH_DIR, f"batch_{b + 1:02d}.json"), "w", encoding="utf-8") as f:
            json.dump(chunk, f, ensure_ascii=False, indent=1)

    q_total = sum(1 for it in items if it["kind"] == "question")
    print(f"总条目: {len(items)}  题目: {q_total}  需要分类: {len(todo)}  批次: {nb}")
    print("大类清单:")
    for m in schema["majors"]:
        print(f"  {m['display']}  (dir: {m['name']})  小类: {m['minors']}")
    print(f"items.json / schema.json 已生成; 批次写入 {BATCH_DIR}/")


# ---------------- merge ----------------

def merge():
    with open(ITEMS_JSON, encoding="utf-8") as f:
        items = json.load(f)
    with open(SCHEMA_JSON, encoding="utf-8") as f:
        schema = json.load(f)
    valid_majors = {m["name"] for m in schema["majors"]}
    valid_minors = {mn for m in schema["majors"] for mn in m["minors"]}

    # 先读全部分类结果
    classified = {}
    for cf in sorted(f for f in os.listdir(CLS_DIR)
                     if f.startswith("batch_") and f.endswith(".json")):
        with open(os.path.join(CLS_DIR, cf), encoding="utf-8") as f:
            data = json.load(f)
        for c in data["items"]:
            classified[c["id"]] = c

    result = {}      # (major, minor) -> {"groups": [(h3, [item...])], "seen": set()}
    unclassified = []

    def place(it, major, minor, h3):
        k = (major or "未分类", minor or "未分类")
        v = result.setdefault(k, {"groups": [], "seen": set()})
        if h3 not in v["seen"]:
            v["groups"].append([h3, []])
            v["seen"].add(h3)
        for g in v["groups"]:
            if g[0] == h3:
                g[1].append(it)
                break

    for it in items:
        if it["kind"] != "question":
            continue
        c = classified.get(it["id"])
        if c is not None:
            major, minor = c.get("major"), c.get("minor")
            if major not in valid_majors or minor not in valid_minors:
                unclassified.append({"id": it["id"], "text": it["text"],
                                     "reason": f"无效类目 {major}/{minor}"})
                continue
            it["major"], it["minor"] = major, minor
            it["depth"] = int(c.get("depth") or 99)
            it["fuzzy"] = bool(c.get("fuzzy", False))
            it["note"] = c.get("note", "")
            sub = c.get("subminor") or it.get("tag")
            if sub:
                h3 = sub
            elif it.get("comment_label"):
                h3 = f"补充：源自「{it['comment_label']}」"
            else:
                h3 = "其他"
            place(it, major, minor, h3)
        elif it.get("assigned"):
            h3 = it.get("tag") or "其他"
            place(it, it["major"], it["minor"], h3)
        else:
            unclassified.append({"id": it["id"], "text": it["text"],
                                 "reason": "无分类结果"})

    # 排序: 组内按 (depth, line); 组顺序: 常规组在前(源顺序), 补充组殿后
    for v in result.values():
        v["groups"].sort(key=lambda g: g[0].startswith("补充："))
        for g in v["groups"]:
            g[1].sort(key=lambda x: (x.get("depth") or 99, x["line"]))

    os.makedirs(CAT_DIR, exist_ok=True)
    for d in os.listdir(CAT_DIR):
        p = os.path.join(CAT_DIR, d)
        for f in os.listdir(p):
            os.remove(os.path.join(p, f))
        os.rmdir(p)

    display_of = {m["name"]: m["display"] for m in schema["majors"]}
    n_files = 0
    for (major, minor), v in sorted(result.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        d = os.path.join(CAT_DIR, major)
        os.makedirs(d, exist_ok=True)
        fp = os.path.join(d, f"{minor}.md")
        lines = [f"# {display_of.get(major, major)} · {minor}", ""]
        num = 0
        for h3, its in v["groups"]:
            lines.append(f"## {h3}")
            lines.append("")
            for it in its:
                num += 1
                lines.append(f"{num}. {it['text']}")
            lines.append("")
        with open(fp, "w", encoding="utf-8") as f:
            f.write("\n".join(lines).rstrip() + "\n")
        n_files += 1

    if unclassified:
        with open(os.path.join(ROOT, "unclassified.md"), "w", encoding="utf-8") as f:
            f.write("# 未分类条目\n\n")
            for u in unclassified:
                f.write(f"- {u['id']} ({u['reason']}): {u['text']}\n")

    # 大文件清单(供递归细分 subagent 使用)
    big = []
    for (major, minor), v in sorted(result.items(),
                                    key=lambda kv: -sum(len(g[1]) for g in kv[1]["groups"])):
        cnt = sum(len(g[1]) for g in v["groups"])
        if cnt >= 15:
            big.append({"major": major, "minor": minor, "count": cnt,
                        "path": os.path.join(CAT_DIR, major, f"{minor}.md")})
    with open(os.path.join(ROOT, "big_files.json"), "w", encoding="utf-8") as f:
        json.dump(big, f, ensure_ascii=False, indent=1)
    print(f"已生成 {n_files} 个小类文件; 大文件(>=15题, 需递归细分): {len(big)}")
    for b in big:
        print(f"  {b['major']}/{b['minor']}  {b['count']}题")


# ---------------- audit ----------------

def audit():
    with open(ITEMS_JSON, encoding="utf-8") as f:
        items = json.load(f)
    questions = [it for it in items if it["kind"] == "question"]

    # 合并分类结果: id -> 是否已分类
    classified_ids = set()
    for cf in os.listdir(CLS_DIR):
        if not cf.endswith(".json"):
            continue
        try:
            with open(os.path.join(CLS_DIR, cf), encoding="utf-8") as f:
                data = json.load(f)
            classified_ids.update(c["id"] for c in data["items"])
        except Exception:
            pass

    # 收集已落盘文本(规范化: 去掉编号前缀)
    norm = lambda t: re.sub(r"^\s*\d+\.\s*", "", t.strip())
    placed = {}  # id -> file
    for d in sorted(os.listdir(CAT_DIR)):
        dp = os.path.join(CAT_DIR, d)
        if not os.path.isdir(dp):
            continue
        for fn in sorted(os.listdir(dp)):
            fp = os.path.join(dp, fn)
            with open(fp, encoding="utf-8") as f:
                for ln in f:
                    ln = ln.strip()
                    if ln.startswith("#") or not ln or re.match(r"^\d+\.\s", ln) is None:
                        continue
                    # 只匹配题目行
                    if re.match(r"^\d+\.\s+\S", ln):
                        placed[ln] = f"{d}/{fn}"

    q_by_text = {}
    for it in questions:
        q_by_text.setdefault(it["text"], []).append(it["id"])

    lines = []
    lines.append("# 审计报告\n")
    lines.append(f"- 源文档: {SRC}")
    lines.append(f"- 题目总数: {len(questions)}")
    lines.append(f"- 落盘题目行数: {len(placed)}")
    dup_text = {t: ids for t, ids in q_by_text.items() if len(ids) > 1}
    lines.append(f"- 完全重复题目(组数): {len(dup_text)}")
    for t, ids in sorted(dup_text.items(), key=lambda kv: kv[1][0]):
        lines.append(f"  - {ids} : {t[:60]}")
    lines.append("")
    # 未分类: 既无分类结果、也无机械分配的题目
    un = [it for it in questions
          if it["id"] not in classified_ids and not it.get("assigned")]
    if un:
        lines.append(f"### 未分类 {len(un)} 条")
        for it in un:
            lines.append(f"- {it['id']}: {it['text'][:60]}")
    lines.append("")
    # 空文件
    lines.append("### 各小类文件题数")
    for d in sorted(os.listdir(CAT_DIR)):
        dp = os.path.join(CAT_DIR, d)
        if not os.path.isdir(dp):
            continue
        for fn in sorted(os.listdir(dp)):
            cnt = 0
            with open(os.path.join(dp, fn), encoding="utf-8") as f:
                for ln in f:
                    if re.match(r"^\d+\.\s+\S", ln.strip()):
                        cnt += 1
            flag = "  <-- 空" if cnt == 0 else ""
            lines.append(f"- {d}/{fn}: {cnt} 题{flag}")

    with open(os.path.join(ROOT, "audit_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


# ---------------- validate ----------------

def validate():
    with open(SCHEMA_JSON, encoding="utf-8") as f:
        schema = json.load(f)
    valid_majors = {m["name"] for m in schema["majors"]}
    valid_minors = {mn for m in schema["majors"] for mn in m["minors"]}
    ok = True
    for cf in sorted(os.listdir(CLS_DIR)):
        if not cf.endswith(".json"):
            continue
        fp = os.path.join(CLS_DIR, cf)
        try:
            data = json.load(open(fp, encoding="utf-8"))
        except Exception as e:
            print(f"[FAIL] {cf}: JSON 解析失败 - {e}")
            ok = False
            continue
        ids = [c["id"] for c in data["items"]]
        if len(ids) != len(set(ids)):
            print(f"[FAIL] {cf}: 重复 id")
            ok = False
        bad = []
        for c in data["items"]:
            if c.get("major") not in valid_majors:
                bad.append(f"{c['id']} 大类无效: {c.get('major')}")
            if c.get("minor") not in valid_minors:
                bad.append(f"{c['id']} 小类无效: {c.get('minor')}")
            if not isinstance(c.get("depth"), int) or not 1 <= c["depth"] <= 5:
                bad.append(f"{c['id']} depth 无效: {c.get('depth')}")
        if bad:
            print(f"[FAIL] {cf}: {len(bad)} 处问题")
            for b in bad[:10]:
                print(f"    {b}")
            ok = False
        else:
            print(f"[OK] {cf}: {len(ids)} 条")
    print("校验通过" if ok else "存在失败项")


# ---------------- export_obsidian ----------------

def export_obsidian():
    """单向生成 Obsidian 知识图谱: obsidian_vault/{00_MOC,10_概念,20_索引,30_手写笔记,99_dataview.md}
    依赖: concepts.yaml(概念词典,唯一需人工维护的文件), items.json, schema.json, batches/classified/"""
    import shutil
    import yaml

    with open(ITEMS_JSON, encoding="utf-8") as f:
        items = json.load(f)
    with open(SCHEMA_JSON, encoding="utf-8") as f:
        schema = json.load(f)
    with open(os.path.join(ROOT, "concepts.yaml"), encoding="utf-8") as f:
        concepts = yaml.safe_load(f)["concepts"]

    classified = {}
    for cf in os.listdir(CLS_DIR):
        if not cf.endswith(".json"):
            continue
        for c in json.load(open(os.path.join(CLS_DIR, cf), encoding="utf-8"))["items"]:
            classified[c["id"]] = c

    qs = []
    for it in items:
        if it["kind"] != "question":
            continue
        c = classified.get(it["id"])
        if c is not None:
            major, minor = c["major"], c["minor"]
            depth = int(c.get("depth") or 99)
            fuzzy = bool(c.get("fuzzy", False))
        elif it.get("assigned"):
            major, minor = it["major"], it["minor"]
            depth = int(it.get("depth") or 99)
            fuzzy = False
        else:
            continue
        qs.append({"id": it["id"], "line": it["line"], "text": it["text"],
                   "major": major, "minor": minor, "depth": depth, "fuzzy": fuzzy,
                   "comment_label": it.get("comment_label"),
                   "prereq": it.get("prereq", []),
                   "downstream": it.get("downstream", []),
                   "status": it.get("status", "待复习")})

    # 概念匹配: 每条题目最多连 6 个概念(按词典顺序取前6)
    for q in qs:
        tl = q["text"].lower()
        q["concepts"] = [c["name"] for c in concepts
                         if any(str(kw).lower() in tl for kw in c["keywords"])][:6]

    minors = {}
    for q in qs:
        minors.setdefault((q["major"], q["minor"]), []).append(q)
    for k in minors:
        minors[k].sort(key=lambda q: (q["depth"], q["line"]))

    VAULT = os.path.join(ROOT, "obsidian_vault")
    # 保留手写笔记与项目档案(人工/工具产物), 只重建生成区
    kept = {}
    for keep in ("30_手写笔记", "40_项目档案"):
        kp = os.path.join(VAULT, keep)
        if os.path.exists(kp):
            tmp = os.path.join(ROOT, f".vault_keep_{keep}")
            if os.path.exists(tmp):
                shutil.rmtree(tmp)
            shutil.move(kp, tmp)
            kept[keep] = tmp
    if os.path.exists(VAULT):
        shutil.rmtree(VAULT)
    for d in ("00_MOC", "10_概念", "20_索引", "30_手写笔记", "40_项目档案"):
        os.makedirs(os.path.join(VAULT, d), exist_ok=True)
    for keep, tmp in kept.items():
        dst = os.path.join(VAULT, keep)
        if os.path.isdir(dst) and not os.listdir(dst):
            os.rmdir(dst)  # shutil.move 遇已存在目录会嵌套进去, 先移除空壳
        shutil.move(tmp, dst)
    with open(os.path.join(VAULT, "30_手写笔记", "README.md"), "w", encoding="utf-8") as f:
        f.write("# 手写笔记（此目录永不被生成器覆盖）\n\n"
                "按题目 ID 命名，如 `L6 答题要点.md`；可在其中记录答案要点、复盘心得，"
                "重跑生成器不会动这个目录。\n")

    DEPTH_LABEL = {1: "概念定义", 2: "原理机制", 3: "设计与方案", 4: "落地与权衡", 5: "前沿与延伸"}
    index_rel = lambda major, minor: f"20_索引/{major}/{minor}.md"
    conc_rel = lambda name: f"10_概念/{name}.md"

    # ---------- 20_索引: 每小类一页, 题级锚点 ----------
    for (major, minor), qlist in minors.items():
        d = os.path.join(VAULT, "20_索引", major)
        os.makedirs(d, exist_ok=True)
        disp = {m["name"]: m["display"] for m in schema["majors"]}.get(major, major)
        lines = [f"---", f"major: {major}", f"minor: {minor}", f"count: {len(qlist)}",
                 f"tags: [review]", f"---", "",
                 f"# {disp} · {minor}", "",
                 f"> 共 {len(qlist)} 题 · 按逻辑深度排序（概念定义→原理机制→设计实现→落地与权衡→前沿延伸）", ""]
        id2mm = {q2["id"]: (q2["major"], q2["minor"]) for q2 in qs}
        for q in qlist:
            lines.append(f"### {q['id']}")
            lines.append("")
            lines.append(f"**题目**：{q['text']}")
            tags = []
            tags.append(f"{q['depth']}/5 · {DEPTH_LABEL.get(q['depth'], '?')}")
            if q["fuzzy"]:
                tags.append("模糊归位")
            if q.get("comment_label"):
                tags.append(f"源自注释块「{q['comment_label']}」")
            lines.append("")
            lines.append(f"**深度**：{tags[0]}")
            if len(tags) > 1:
                lines.append(f"**备注**：{' / '.join(tags[1:])}")
            if q["concepts"]:
                links = "、".join(f"[[{conc_rel(c)}|{c}]]" for c in q["concepts"])
                lines.append(f"**概念**：{links}")
            # 学习路径边 (前置/后置, 指向其他索引页锚点)
            pre = [f"[[{index_rel(*id2mm[p])}#{p}|{p}]]" for p in q.get("prereq", []) if p in id2mm]
            down = [f"[[{index_rel(*id2mm[d])}#{d}|{d}]]" for d in q.get("downstream", []) if d in id2mm]
            if pre:
                lines.append(f"**前置**：{'、'.join(pre)}")
            if down:
                lines.append(f"**后置**：{'、'.join(down)}")
            lines.append("")
        with open(os.path.join(d, f"{minor}.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines).rstrip() + "\n")

    # ---------- 10_概念 ----------
    concept_hits = {}
    for q in qs:
        for c in q["concepts"]:
            concept_hits.setdefault(c, []).append(q)
    concept_related = {}
    for c in concepts:
        concept_related[c["name"]] = [r for r in c.get("related", [])]
    for c in concepts:
        name = c["name"]
        hits = concept_hits.get(name, [])
        lines = ["---", f"type: concept", f"aliases: {json.dumps(c.get('aliases', []), ensure_ascii=False)}",
                 f"hits: {len(hits)}", f"related: {json.dumps(concept_related.get(name, []), ensure_ascii=False)}",
                 "tags: [review]", "---", "", f"# {name}", "", c["summary"], "", f"## 相关题目（{len(hits)}）", ""]
        if hits:
            for q in hits:
                label = f"{q['id']} · {q['text'][:40]}"
                lines.append(f"- [[{index_rel(q['major'], q['minor'])}#{q['id']}|{label}]]")
        else:
            lines.append("_（词典已收录，暂未命中题目——检查关键词或题库扩展）_")
        lines.append("")
        rel = concept_related.get(name, [])
        if rel:
            lines.append("## 相关概念")
            lines.append("")
            lines.append("、".join(f"[[{conc_rel(r)}|{r}]]" for r in rel))
            lines.append("")
        with open(os.path.join(VAULT, "10_概念", f"{name}.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines).rstrip() + "\n")

    # ---------- 00_MOC ----------
    disp_of = {m["name"]: m["display"] for m in schema["majors"]}
    major_stats = {}
    for (major, minor), qlist in minors.items():
        s = major_stats.setdefault(major, {"count": 0, "minors": [], "concepts": {}})
        s["count"] += len(qlist)
        s["minors"].append((minor, len(qlist)))
        for q in qlist:
            for c in q["concepts"]:
                s["concepts"][c] = s["concepts"].get(c, 0) + 1
    for major, s in major_stats.items():
        s["minors"].sort()
        s["top"] = sorted(s["concepts"].items(), key=lambda kv: -kv[1])[:8]
    for major in [m["name"] for m in schema["majors"]]:
        s = major_stats.get(major)
        fp = os.path.join(VAULT, "00_MOC", f"{major}.md")
        if s is None:
            with open(fp, "w", encoding="utf-8") as f:
                f.write(f"# {disp_of.get(major, major)}\n\n_源文档中该大类没有题目，暂无索引页。_\n")
            continue
        lines = ["---", f"type: moc", f"major: {major}", f"count: {s['count']}", "---", "",
                 f"# {disp_of.get(major, major)}", "", f"> 共 {s['count']} 题 · {len(s['minors'])} 个小类", ""]
        lines.append("## 小类导航")
        lines.append("")
        for minor, n in s["minors"]:
            lines.append(f"- [[{index_rel(major, minor)}|{minor}]]（{n} 题）")
        lines.append("")
        if s["top"]:
            lines.append("## 高频概念")
            lines.append("")
            lines.append("、".join(f"[[{conc_rel(c)}|{c}]]（{n}）" for c, n in s["top"]))
            lines.append("")
        lines.append("## 学习路径")
        lines.append("")
        lines.append("按小类顺序从浅入深过一遍：先看每个索引页的「概念定义」段，再做「设计与方案」，"
                     "最后对照「落地与权衡」自测；跨小类的概念用高频概念里的链接串起来。")
        lines.append("")
        with open(fp, "w", encoding="utf-8") as f:
            f.write("\n".join(lines).rstrip() + "\n")

    # ---------- 00_MOC/总览 ----------
    with open(os.path.join(VAULT, "00_MOC", "总览.md"), "w", encoding="utf-8") as f:
        f.write(f"""---
type: moc
count: {len(qs)}
---
# 面试题库总览

> 题库 {len(qs)} 题 · 概念 {len(concepts)} 个 · 索引页 {len(minors)} 个
> 由 pipeline.py export 单向生成，任何修改请回到源头（categories/ 或 concepts.yaml）后重跑

## 大类导航

""" + "\n".join(
            f"- [[00_MOC/{m}|{disp_of.get(m, m)}]]（{major_stats.get(m, {}).get('count', 0)} 题）"
            for m in [mm["name"] for mm in schema["majors"]]
        ) + f"""

## 项目档案

""" + ("\n".join(
            f"- [[40_项目档案/{d}/项目画像.md|{d}]]"
            for d in sorted(os.listdir(os.path.join(VAULT, "40_项目档案")))
            if os.path.isdir(os.path.join(VAULT, "40_项目档案", d))
        ) or "- _（暂无，用 repo_fuse 注入项目）_") + f"""

## 概念枢纽（按命中题数 Top 15）

""" + "\n".join(
            f"- [[10_概念/{c}|{c}]]（{len(concept_hits.get(c, []))} 题）"
            for c, _ in sorted(((c["name"], len(concept_hits.get(c["name"], []))) for c in concepts),
                               key=lambda kv: -kv[1])[:15]
        ) + f"""

## 使用说明

1. **阅读路径**：总览 → 大类 MOC → 索引页（题级锚点，已按深度排序）→ 概念笔记（跨主题串联）
2. **Graph view**：打开图谱后建议用过滤器 `path:obsidian_vault` 只看本库节点；节点按大类/概念自动聚类
3. **手写笔记**：`30_手写笔记/` 永不被覆盖，按 `L6 答题要点.md` 命名即可与题目锚点互链
4. **改词典**：编辑 `concepts.yaml`（加/删/改概念）→ `python3 pipeline.py export` 一键重生成
5. **改题库**：编辑 categories/ 或重跑整条清洗流水线 → 再 export

## 数据体检

- 重复题 {len(qs) - len({q['text'] for q in qs})} 组（源文档原文重复，详见 audit_report.md）
- 模糊归位（注释块题目按语义就近归类）：{sum(1 for q in qs if q['fuzzy'])} 题
""")

    # ---------- 99_dataview ----------
    with open(os.path.join(VAULT, "99_dataview.md"), "w", encoding="utf-8") as f:
        f.write("""# Dataview 增强页（可选）

> 需要安装 Dataview 社区插件才会渲染；不安装则本页显示为代码块，不影响其他功能。

## 概念按命中题数排序

```dataview
TABLE hits, aliases FROM "10_概念" SORT hits DESC
```

## 索引页按题数排序

```dataview
TABLE count, major FROM "20_索引" SORT major ASC, count DESC
```

## 手写笔记待办（按题目深度）

```dataview
LIST FROM "30_手写笔记" WHERE file.name != "README"
```
""")

    # ---------- 校验: 链接可解析 + 锚点存在 ----------
    broken, anchors_total = [], 0
    link_re = re.compile(r"\[\[([^\]|#]+?)(?:#([^\]|]+))?(?:\|[^\]]*)?\]\]")
    for d0, _, files in os.walk(VAULT):
        if "30_手写笔记" in d0:
            continue
        for fn in files:
            if not fn.endswith(".md"):
                continue
            with open(os.path.join(d0, fn), encoding="utf-8") as f:
                content = f.read()
            for target, anch in link_re.findall(content):
                # Obsidian 允许省略 .md 后缀, 校验时两种都试
                tpath = os.path.join(VAULT, target)
                if not os.path.exists(tpath) and not os.path.exists(tpath + ".md"):
                    broken.append(f"{os.path.relpath(os.path.join(d0, fn), VAULT)} -> {target} (文件不存在)")
                    continue
                if not os.path.exists(tpath):
                    tpath = tpath + ".md"
                if anch:
                    anchors_total += 1
                    heads = set()
                    for ln in open(tpath, encoding="utf-8"):
                        if ln.startswith("#"):
                            heads.add(ln.strip().lstrip("#").strip())
                    if anch not in heads:
                        broken.append(f"{os.path.relpath(os.path.join(d0, fn), VAULT)} -> {target}#{anch} (锚点不存在)")

    print(f"vault 生成完成: {len(qs)} 题 / {len(concepts)} 概念 / {len(minors)} 索引页 / {len(major_stats)} 大类 MOC")
    print(f"链接校验: 锚点链接 {anchors_total} 个, 断链 {len(broken)} 个")
    for b in broken[:10]:
        print("  [断链]", b)
    if broken:
        print("⚠ 存在断链, 请检查上面的列表；未同步题库")
        raise SystemExit(1)
    sync_bank()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "split"
    {"split": split, "merge": merge, "audit": audit, "validate": validate,
     "export": export_obsidian, "sync-bank": sync_bank}[cmd]()



