# 语料同步说明（project-mock-interview skill）

本目录是快照，源在 `~/桌面/面试文档裁切/`。题库或项目档案更新后，在项目目录执行：

```bash
S=~/.hermes/skills/project-mock-interview
# 题库层
cp items.json concepts.yaml schema.json $S/references/题库/
# 项目层（slug 逐个）
for slug in SuperGODOG__tripplanner SuperGODOG__skillforge jeecgboot__JeecgBoot; do
  cp repos_cache/$slug/match.json $S/references/项目/$slug/
  cp obsidian_vault/40_项目档案/$slug/*.md $S/references/项目/$slug/
done
```

## 文件清单

- `题库/items.json` — 240 题（id/line/text/major/minor/depth/concepts），唯一题目原文来源
- `题库/concepts.yaml` — 33 概念词典（含 aliases/keywords/summary/related）
- `题库/schema.json` — 7 大类/14 小类骨架
- `项目/<slug>/match.json` — 路由表（候选题目 + hit_concepts + evidence + depth）
- `项目/<slug>/项目画像.md` — 技术档案（自研项目含钩子，第三方项目含谈资点+误报清单）
- `项目/<slug>/面试题匹配表.md` — 题目×概念×证据对照
- `项目/<slug>/项目内作答.md` — 逐题作答 + 文件:行号 证据锚点（点评依据）
- 复盘文件不在此目录（写在用户 vault 的 40_项目档案/<slug>/面试复盘.md）

## 约定

- 语料只增改不删题（大厂面试题合集，质量高）
- 新增项目：跑 repo_fuse（见 interview-bank-pipeline skill）后按上面命令同步
- **运行期状态不回流**：复习状态（待复习/已掌握）写在 vault 的 40_项目档案/<slug>/面试复盘.md，不写 items.json——同步命令会覆盖 skill 内快照，status 字段只是初始值
