---
name: project-doc-generator
description: Analyze any codebase and auto-generate 7 comprehensive developer documentation files (architecture, API reference, file map, DB schema, dev guide, config reference, project overview).
---

# Project Doc Generator

Analyze any codebase and auto-generate 7 comprehensive developer documentation files.

Invoke via `/project-doc-generator` or "请用 project-doc-generator 分析本项目".

## When to Use

- Initializing documentation for a new or existing codebase
- Onboarding a new project where developer docs are missing or outdated
- Migrating documentation between projects — the generated docs are based on **actual code**, not assumptions

## What It Generates

| # | Document | Purpose | Key Content | Generic? |
|---|----------|---------|-------------|----------|
| 1 | `架构说明.md` | Complete system architecture | Process model, data flows, service dependencies, deployment, concurrency | ✅ Universal template |
| 2 | `项目架构全览.md` | High-level overview | One-sentence summary, core data flows, layered architecture, middleware formats, tech stack | ✅ Universal template |
| 3 | `接口说明.md` | Complete API reference | Auth model, every HTTP endpoint grouped by domain, request/response formats, env vars | ✅ Universal template |
| 4 | `文件内容说明.md` | File-level code map | Every directory and key file, one-line purpose, "quick find" index | ✅ Universal template |
| 5 | `数据库表结构说明.md` | Database schema reference | ER diagram, all tables with fields/types/descriptions, custom field types | ✅ Universal template |
| 6 | `开发场景指南.md` | Development how-to guide | Step-by-step for adding parsers/components/tools/connectors/LLM providers | ✅ Universal template |
| 7 | `配置参数全解.md` | Configuration reference | Every env var, config file entry, runtime JSON config with defaults and descriptions | ✅ Universal template |

## Instructions

You MUST follow these steps in order. Do NOT skip the discovery phase.

---

### Phase 0: Setup

1. Determine the target output directory (default: `docs/dev/`, or ask the user).
2. Determine the project version (from `pyproject.toml`, `package.json`, `Cargo.toml`, `pom.xml`, or git tags).
3. Check if any of the 4 docs already exist. If they do, note what needs updating vs. rewriting.

### Phase 1: Discovery — Gather Raw Information

Run these discovery steps IN PARALLEL using subagents where possible. The goal is to collect facts, not write docs yet.

#### 1.1 Entry Points & Process Model
- Find the main entry point(s): `main()`, `app.run()`, server startup scripts, Docker entrypoints
- Identify ALL processes that run (API server, workers, cron jobs, etc.)
- Find the process launcher (shell script, docker-compose, supervisor, systemd)
- Understand how processes communicate (Redis queues, gRPC, message bus, shared DB)

#### 1.2 External Dependencies
- Find `docker-compose*.yml` or `docker-compose*.yaml` files
- Extract all services (DB, cache, queue, object storage, search engine, etc.)
- For each service, note what it's used for

#### 1.3 API Routes (if web application)
- Find the web framework (Flask, Quart, FastAPI, Express, Gin, Spring, etc.)
- Find ALL route definitions — use grep for `@app.route`, `@router.get`, `app.get`, `@Get`, `@RequestMapping`, etc.
- Group routes by Blueprint / Router / Controller module
- Note the auth model (JWT, session, API key, OAuth)
- Note the response format (unified wrapper, error codes)

#### 1.4 Core Business Logic
- Identify the "main pipeline" — what happens when the primary user action is triggered
- Trace one complete flow end-to-end through the code
- Find where the "magic happens" (the processing engine, the core algorithm)
- Identify key abstractions (base classes, interfaces, strategy patterns)

#### 1.5 Component/Plugin/Tool Systems (if applicable)
- Search for plugin registries, component decorators, tool registrations
- List all registered components/tools/plugins
- Find the base class/interface and the registration mechanism

#### 1.6 Data Layer
- Find ORM models / database schema / migrations
- List all tables/collections with a brief description
- Find the document store / search engine abstraction
- Note any external data connectors

#### 1.7 File System Map
- List the top-level directory structure
- For each major directory (>3 files), list its files with one-line purposes
- Identify the key files (>500 lines or obviously important)
- Note shared/common infrastructure directories

#### 1.8 Frontend (if applicable)
- Identify the frontend framework (React, Vue, Angular, etc.)
- Identify UI libraries, state management, routing, build tool
- Map `src/` directories to features

#### 1.9 Database Schema (if applicable)
- Find all ORM models / database table definitions
- For each table: extract all field names, types, constraints, and help text
- Identify foreign key relationships and composite primary keys
- Note custom field types and their purpose
- Draw an ER relationship diagram (tables grouped by domain)

#### 1.10 Extension Patterns (if applicable)
- Find how to add a new parser / plugin / component / tool / connector
- Identify base classes, registration decorators, auto-discovery mechanisms
- Trace one example end-to-end to document the step-by-step pattern
- Note any initialization data that needs updating (enums, DB seed data)

#### 1.11 Configuration System
- Find all configuration files (`.env`, `.yaml`, `.json`, `.toml`, `.properties`)
- Extract every configuration key with its default value
- Note which configs are build-time vs runtime
- Find runtime JSON config schemas (parser_config, llm_setting, prompt_config, etc.)

---

### Phase 2: Write the 7 Documents

Write each document using the collected information. The key principle is: **every claim must be verifiable in the actual code**.

#### Document 1: `架构说明.md`

Structure:
```
# 架构说明 (Architecture)

## 一、进程架构
- Process model diagram
- What each process does
- How they communicate

## 二、依赖服务
- Service dependency table
- What each service stores/does

## 三、核心处理链路 (the "main pipeline")
- Step-by-step data flow diagram
- What happens at each stage
- File locations for each stage

## 四、[Component/Agent/Plugin] 系统 (if applicable)
- Architecture diagram
- Component type table (category, location, description)
- Key design patterns (base class, registration, lifecycle)

## 五、[Additional Subsystems] (as applicable)
- Graph processing, caching, real-time updates, etc.

## 六、部署方式
- Docker vs source development
- Key commands for each
- Critical environment variables

## 七、线程安全与并发
- Async/sync model
- Connection pooling
- Distributed locks
```

#### Document 2: `项目架构全览.md`

Structure:
```
# 项目架构全览

> 一键概述，供 AI/新人 快速理解。

## 一句话概述

## 核心数据流 (ASCII art flow diagram)

## N 层架构
### 第 1 层：[External/Access] 层
### 第 2 层：[Business] 层
### 第 3 层：[Data] 层
### 第 4 层：[Infrastructure] 层

## 关键中间格式 (if applicable: DSL, JSON schema, protobuf)

## 前端架构 (if applicable)

## 技术栈概要
```

#### Document 3: `接口说明.md`

Structure:
```
# 接口说明 (API)

## 一、认证方式
- Auth mechanisms with code examples

## 二、[Domain Group 1] API
| 方法 | 路径 | 说明 |

## 三、[Domain Group 2] API
...

## 四、统一响应格式
- JSON structure
- Error code enum

## 五、关键请求参数
- Important request body fields

## 六、环境变量
| 变量 | 默认值 | 说明 |
```

**Critical**: Every route listed MUST actually exist in the code. Use grep to verify. Do NOT invent routes.

#### Document 4: `文件内容说明.md`

Structure:
```
# 文件内容说明 (File Map)

## 根目录
| 路径 | 功能 |

## [每个一级目录]
### [子目录]
| 文件 | 核心类/函数 | 功能 |

## 快速索引：按功能查找
| 想做什么 | 去哪里 |
```

**Critical**: Every file listed MUST actually exist. List directories first, then files within. The quick-find index should map developer intents ("how do I add X") to file paths.

#### Document 5: `数据库表结构说明.md`

Structure:
```
# 数据库表结构说明 (Database Schema)

## 一、基础模型
- Base model inheritance chain
- Common auto-fields (create_time, update_time, etc.)
- Primary key convention

## 二、ER 关系图
- ASCII art diagram showing table relationships
- Group tables by domain (user/auth, content, workflow, etc.)

## 三、核心表详解
For each table:
- Table name and purpose
- Field table (name, type, constraints, description)
- Foreign key relationships

## 四、自定义字段类型 (if applicable)
- Custom ORM field types and their purpose
```

**Critical**: Every table MUST come from actual ORM model classes. Use `grep` to extract class definitions and field names. Draw the ER diagram by tracing foreign key fields.

#### Document 6: `开发场景指南.md`

Structure:
```
# 开发场景指南 (Development Guide)

## 一、如何添加新的 [Parser / Component / Tool / Connector / Provider]
### 场景 → 步骤 1..N (with code snippets from actual patterns found in codebase)

## 二、如何添加新的 [Extension Type 2]
...

## 三、组件生命周期 / 重试和异常处理

## 四、数据库连接管理

## 五、[Framework-specific patterns] (Redis, message queue, caching, etc.)
```

**Critical**: Each "how to add X" guide must be based on tracing an EXISTING example. Show the actual registration mechanism (decorator, auto-discovery, enum, dict mapping). Do NOT invent patterns.

#### Document 7: `配置参数全解.md`

Structure:
```
# 配置参数全解 (Configuration Reference)

## 一、配置体系
- Configuration hierarchy diagram (.env → config file → runtime API)

## 二、[Config Source 1] (e.g., Docker 环境变量)
| 变量 | 默认值 | 说明 |
(Group by category: database, cache, storage, ports, limits)

## 三、[Config Source 2] (e.g., service_conf.yaml)
...

## 四、运行时配置
- JSON config schemas for API parameters
- Key fields with types, defaults, descriptions

## 五、日志配置
```

**Critical**: Every config key MUST be found in actual `.env` / `.yaml` / `.json` files. Note which are build-time vs runtime. Include the full default value exactly as written.

---

### Phase 3: Validation

Before finalizing, verify:
1. Every route in the API doc matches `grep '@route\|@app\.'` output
2. Every file path in the file map actually exists
3. Every service/dependency mentioned is referenced in docker-compose or config files
4. Architecture claims (e.g., "inherits from X") are backed by actual `class Foo(Bar)` in the code
5. Every table in the DB doc matches actual ORM model classes
6. Every config key in the config doc comes from actual `.env` / `.yaml` / `.json` files
7. Development patterns (registration mechanisms) are verified against actual code (decorators, auto-discovery loops, enum registrations)
8. Remove any template residue from a previous project (wrong project name, wrong version, wrong module paths)

---

### Phase 4: Summary

Report:
- What was discovered (process count, route count, table count, file count, config key count)
- What 7 documents were generated/updated
- What the user should review (uncertain areas, complex parts that need human confirmation)
