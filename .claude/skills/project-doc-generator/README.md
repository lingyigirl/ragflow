# Project Doc Generator Skill

## Skill 命名和调用约定

### 命名规则

- 每个 skill 是一个**目录**，放在 `.claude/skills/<skill名>/` 下
- 目录内**必须**有一个 `SKILL.md` 作为入口文件
- **目录名 = skill 名**，调用时使用 `/<目录名>`

```
.claude/skills/
├── project-doc-generator/    ← 调用: /project-doc-generator
│   ├── SKILL.md              ← 必须有
│   └── README.md             ← 可选：使用说明
├── commit-code/              ← 调用: /commit-code
│   └── SKILL.md
└── package-project/          ← 调用: /package-project
    └── SKILL.md
```

### 调用方式

| 方式 | 示例 | 说明 |
|------|------|------|
| 斜杠命令 | `/project-doc-generator` | 直接调用，最明确 |
| 自然语言 | "帮我生成项目文档" | Claude 会匹配最合适的 skill |
| 明确指定 | "用 project-doc-generator 分析这个项目" | 多个 skill 时避免歧义 |

### 添加新 skill

```bash
mkdir -p .claude/skills/<新skill名>
# 在目录内创建 SKILL.md（入口）+ 可选 README.md
```

所有 skill 自动生效，无需额外配置。

---

## 使用方式

### 在当前项目使用

直接输入：

```
/project-doc-generator
```

或：

```
请用 project-doc-generator 分析本项目并生成开发文档。
```

### 迁移到其他项目

将整个 `.claude/skills/project-doc-generator/` 目录复制到目标项目的 `.claude/` 下，然后输入 `/project-doc-generator`。

### 只生成部分文档

```
请读取 .claude/skills/project-doc-generator/SKILL.md，只执行：
- Phase 1 中的 1.3（API Routes）和 1.6（Data Layer）
- Phase 2 中的 Document 3（接口说明.md）
```

## 生成目标（7 篇文档）

| # | 文档 | 路径 |
|---|------|------|
| 1 | 架构说明 | `docs/dev/架构说明.md` |
| 2 | 项目架构全览 | `docs/dev/项目架构全览.md` |
| 3 | 接口说明 | `docs/dev/接口说明.md` |
| 4 | 文件内容说明 | `docs/dev/文件内容说明.md` |
| 5 | 数据库表结构说明 | `docs/dev/数据库表结构说明.md` |
| 6 | 开发场景指南 | `docs/dev/开发场景指南.md` |
| 7 | 配置参数全解 | `docs/dev/配置参数全解.md` |

## 适用项目类型

- Python 后端 (Flask/Quart/FastAPI/Django)
- Node.js 后端 (Express/Koa/Fastify)
- Java/Kotlin 后端 (Spring Boot)
- Go 后端 (Gin/Echo/Chi)
- 全栈项目（前后端分离）
- 微服务项目
