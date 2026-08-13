#!/usr/bin/env python3
"""从文件系统自动生成 mkdocs.yml + docs/index.md（保证 nav 与真实文件一致）。

docs_dir 固定为 docs/（mkdocs 不允许指向仓库根）；
projects/ 与 skills/ 在站点导航中以 GitHub blob 绝对链接呈现
（内容本身仍由仓库提供，避免复制造成双份维护）。
"""
import os
import re
import yaml

ROOT = "/home/caoruixin/桌面/ai-agent-interview-240"
DOCS = os.path.join(ROOT, "docs")
GH = "https://github.com/SuperGODOG/ai-agent-interview-240/blob/main"

# ---------- 扫描 ----------
def scan(dirpath, prefix):
    out = {}
    for fn in sorted(os.listdir(dirpath)):
        p = os.path.join(dirpath, fn)
        if os.path.isfile(p) and fn.endswith(".md"):
            out[fn] = f"{prefix}/{fn}"
    return out

baike = scan(os.path.join(DOCS, "01-面试八股文"), "01-面试八股文")
lang = scan(os.path.join(DOCS, "02-语言八股"), "02-语言八股")
kejian = scan(os.path.join(DOCS, "02-语言八股", "Java", "课件"), "02-语言八股/Java/课件")
python_dir = scan(os.path.join(DOCS, "02-语言八股", "Python"), "02-语言八股/Python")
go_dir = scan(os.path.join(DOCS, "02-语言八股", "Go"), "02-语言八股/Go")
java_dir = scan(os.path.join(DOCS, "02-语言八股", "Java"), "02-语言八股/Java")

# ---------- nav ----------
# docs/index.md 是自动主页, 不在 nav 中重复声明
nav = []

nav.append({"面试八股文": [
    {os.path.splitext(fn)[0]: rel} for fn, rel in sorted(baike.items()) if fn != "README.md"
]})

lang_nav = [{"总览": "02-语言八股/README.md"}]
java_hand = {fn: rel for fn, rel in java_dir.items() if fn != "README.md"}
if java_hand:
    lang_nav.append({"Java 手撕笔记": [
        {os.path.splitext(fn)[0]: rel} for fn, rel in sorted(java_hand.items())
    ]})
if kejian:
    lang_nav.append({"Java 体系化课件（66 篇）": [
        {os.path.splitext(fn)[0]: rel} for fn, rel in sorted(kejian.items()) if fn != "README.md"
    ] + [{"课件索引": "02-语言八股/Java/课件/README.md"}]})
if python_dir:
    lang_nav.append({"Python 八股": [
        {os.path.splitext(fn)[0]: rel} for fn, rel in sorted(python_dir.items())
    ]})
if go_dir:
    lang_nav.append({"Go 八股": [
        {os.path.splitext(fn)[0]: rel} for fn, rel in sorted(go_dir.items())
    ]})
nav.append({"语言八股": lang_nav})

# 项目档案 / Skill: GitHub blob 绝对链接
nav.append({"项目档案": [
    {"TripPlanner": f"{GH}/projects/SuperGODOG__tripplanner/README.md"},
    {"SkillForge": f"{GH}/projects/SuperGODOG__skillforge/README.md"},
    {"JeecgBoot": f"{GH}/projects/jeecgboot__JeecgBoot/README.md"},
]})
nav.append({"模拟面试 Skill": [
    {"项目拷问引擎": f"{GH}/skills/project-mock-interview/SKILL.md"},
    {"大厂模拟面试官": f"{GH}/skills/interview-skills/SKILL.md"},
]})

# ---------- mkdocs.yml ----------
cfg = {
    "site_name": "AI Agent 面试真题库 · 240 道大厂真实面试题",
    "site_description": "240 道真实大厂 AI Agent 面试题（附答题框架）+ Java/Python/Go 语言八股文 + 3 个亲手 Agent 项目档案。AI Agent 面试准备、大模型应用开发面试、后端面试八股。",
    "site_url": "https://supergodog.github.io/ai-agent-interview-240/",
    "repo_url": "https://github.com/SuperGODOG/ai-agent-interview-240",
    "repo_name": "ai-agent-interview-240",
    "edit_uri": "blob/main/docs/",
    "theme": {
        "name": "material",
        "language": "zh",
        "features": [
            "navigation.instant", "navigation.tracking", "navigation.expand",
            "navigation.top", "search.suggest", "search.highlight",
            "toc.follow", "content.code.copy",
        ],
        "palette": [
            {"scheme": "default", "primary": "indigo", "accent": "indigo",
             "toggle": {"icon": "material/weather-night", "name": "切换暗色模式"}},
            {"scheme": "slate", "primary": "indigo", "accent": "indigo",
             "toggle": {"icon": "material/weather-sunny", "name": "切换亮色模式"}},
        ],
    },
    "plugins": [
        {"search": {"lang": ["zh", "en"]}},
    ],
    "extra": {"social": [{"icon": "fontawesome/brands/github",
                          "link": "https://github.com/SuperGODOG"}]},
    "copyright": "Copyright &copy; 2026 SuperGODOG · 仅供学习使用",
    "markdown_extensions": [
        "admonition", "pymdownx.details", "pymdownx.superfences",
        "pymdownx.highlight", "pymdownx.inlinehilite", "pymdownx.tabbed",
        {"toc": {"permalink": True,
                 "slugify": "!!python/object/apply:pymdownx.slugs.slugify {case: lower}"}},
    ],
    "nav": nav,
}

with open(os.path.join(ROOT, "mkdocs.yml"), "w", encoding="utf-8") as f:
    yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False, width=120)

# 还原 !!python/object/apply 标签（safe_dump 会加引号, mkdocs 需要裸标签）
mkdocs_path = os.path.join(ROOT, "mkdocs.yml")
with open(mkdocs_path, encoding="utf-8") as f:
    content = f.read()
content = content.replace("'!!python/object/apply:pymdownx.slugs.slugify {case: lower}'",
                          "!!python/object/apply:pymdownx.slugs.slugify {case: lower}")
with open(mkdocs_path, "w", encoding="utf-8") as f:
    f.write(content)

# ---------- docs/index.md（从 README 生成，链接适配站点） ----------
with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as f:
    readme = f.read()

# 站点内相对链接: "docs/xxx" -> "xxx"
idx = re.sub(r"\]\((docs/)?(?!#|http)", "](./", readme)
# 修正 ./ 后的路径: 原本 (docs/01-...) 现在 (./01-...) ✓; 原本 (projects/...) 现在 (./projects/...) ——
# projects/skills 在站点外, 改回 GitHub blob 链接
idx = re.sub(r"\]\(\./projects/", f"]({GH}/projects/", idx)
idx = re.sub(r"\]\(\./skills/", f"]({GH}/skills/", idx)
# 徽章行保留

with open(os.path.join(DOCS, "index.md"), "w", encoding="utf-8") as f:
    f.write(idx)
print("docs/index.md 已生成")

# 统计
print(f"  八股文卷: {len(baike)-1} 篇")
print(f"  课件: {len(kejian)-1} 篇")
print(f"  Java 手撕: {len(java_hand)} 篇")
print(f"  Python: {len(python_dir)} 篇")
print(f"  Go: {len(go_dir)} 篇")
print(f"  nav 顶层: {len(nav)}")
