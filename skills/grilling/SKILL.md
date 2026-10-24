---
name: grilling
description: Interview the user relentlessly about a plan or design. Use when the user wants to stress-test a plan before building, or uses any 'grill' trigger phrases.
---

Interview me relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.

Ask the questions one at a time, waiting for feedback on each question before continuing. Asking multiple questions at once is bewildering.

If a question can be answered by exploring the codebase, explore the codebase instead.

## 依赖与整包安装

本仓库按 **1 主入口 + 5 依赖**整包安装，勿单拆或单独关闭组件；六个目录必须位于同一个 skills 父目录。以下相对路径均以本 SKILL.md 所在目录为基准。缺失组件时先明确报告降级，按下列内联规则继续可执行部分，不虚构题号、项目档案或已完成步骤。

本 skill 是 `agent-project-grill` 依赖的深挖原语，不直接读取公共题库。单件安装缺主入口或其他组件时，按本文一次一问、逐个解决设计依赖、给推荐答案、能查代码先查代码的规则独立执行；没有编排者时在会话中记录结论，不宣称已写入项目复盘。主入口找不到本 skill 时也内联执行这些规则。
