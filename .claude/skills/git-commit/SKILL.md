---
name: git-commit
description: Git commit — 只提交不推送，message 简洁（≤20字中文），使用 feat:/fix:/refactor: 前缀。
---

# Git Commit

## When to Use

代码修改完成、需要提交时调用。

## Rules

1. **只 commit，不 push** — 用户自行决定何时 push，别问
2. **message 简洁** — 中文 ≤20字，英文 ≤50 chars
3. **使用前缀** — feat: / fix: / refactor: / docs: / chore:
4. **不问"要不要 push"**

## Workflow

```bash
git add <files>
git commit -m "<prefix>: <简述>"
```

## Examples

| 场景 | message |
|------|---------|
| 新增功能 | `feat: 支持MinerU v2解析` |
| 修复bug | `fix: document_app路由匹配错误` |
| 重构 | `refactor: 提取mineru公共方法` |
| 文档 | `docs: 更新开发环境搭建说明` |
