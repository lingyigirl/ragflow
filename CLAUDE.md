# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RAGFlow is an open-source RAG (Retrieval-Augmented Generation) engine based on deep document understanding. It's a full-stack application with:
- Python backend (Quart-based API server — **not** Flask, all route handlers are `async def`)
- React/TypeScript frontend (built with UmiJS)
- Microservices architecture with Docker deployment
- Multiple data stores (MySQL/PostgreSQL, Elasticsearch/Infinity, Redis, MinIO)

## Process Architecture

The backend runs **two types of processes** (launched by `docker/launch_backend_service.sh`):
- **API Server**: `api/ragflow_server.py` — the main Quart HTTP server
- **Task Executors**: `rag/svr/task_executor.py` — `WS` worker processes (default 2) that run document parsing pipelines asynchronously

These communicate via **Redis** (queue, cache, distributed locks, session storage) and share the MySQL/PostgreSQL database. Document processing tasks are submitted by the server and picked up by task executors.

## Architecture

### Backend (`/api/`)
- **Entry Point**: `api/ragflow_server.py` — Quart app initialization, DB setup, signal handlers, Nacos service registration
- **App Factory**: `api/apps/__init__.py` — auto-registers Flask-style Blueprints from `api/apps/*_app.py` files. Each `*_app.py` file defines a `manager` (Blueprint) that gets mounted at `/<API_VERSION>/<page_name>`. SDK endpoints live in `api/apps/sdk/`.
- **Services**: Business logic in `api/db/services/` (one service per domain: `document_service.py`, `dialog_service.py`, etc.)
- **Models**: Peewee ORM models in `api/db/db_models.py` — supports MySQL (`PooledMySQLDatabase`) and PostgreSQL (`PooledPostgresqlDatabase`), switched via `DATABASE_TYPE` env var. Uses custom field types (`JSONField`, `ListField`, `LongTextField`).
- **Auth**: Token-based via `quart_auth` + `itsdangerous` serializers. `login_required` and `api_key_required` decorators in `api/apps/__init__.py`.

### Core Processing (`/rag/`)
- **Document Processing**: `deepdoc/` — PDF parsing, OCR, layout analysis, vision models
- **LLM Integration**: `rag/llm/` — Model abstractions for chat (`chat_model.py`), embedding (`embedding_model.py`), reranking (`rerank_model.py`), CV (`cv_model.py`), OCR (`ocr_model.py`), TTS (`tts_model.py`), and sequence-to-text (`sequence2txt_model.py`). Use `LLMBundle` from `api/db/services/llm_service.py` to access models in components.
- **RAG Pipeline**: `rag/flow/` — The ingestion pipeline. `pipeline.py` defines `Pipeline` which **extends** `agent/canvas.py:Graph`. It's composed of parsers (`parser/`), splitters (`splitter/`), and extractors. The pipeline DSL is a JSON graph of components.
- **NLP**: `rag/nlp/` — Tokenization (`rag_tokenizer.py`), synonym handling, query classification, term weighting
- **Graph RAG**: `graphrag/` — Two modes: **general** (`general/` — full knowledge graph with entity extraction, community reports, Leiden clustering, mind map extraction) and **light** (`light/` — lighter graph extraction). Entry point: `graphrag/general/index.py::run_graphrag_for_kb`.

### Agent System (`/agent/`)
- **Canvas/DSL**: `agent/canvas.py` — `Graph` class parses a JSON DSL defining a directed graph of components with `upstream`/`downstream` edges. The graph is executed by traversing components in order.
- **Components**: `agent/component/` — Each component has two classes: a `ComponentParamBase` subclass (parameter definition/validation) and a `ComponentBase` subclass (runtime logic with `_invoke`/`_invoke_async` methods). Key components: `begin.py`, `llm.py`, `retrieval.py` (in tools), `categorize.py`, `switch.py`, `iteration.py`, `loop.py`, `message.py`.
- **Tools**: `agent/tools/` — External integrations callable from agent workflows: `tavily.py`, `wikipedia.py`, `duckduckgo.py`, `code_exec.py`, `email.py`, `github.py`, etc.
- **Templates**: `agent/templates/` — Pre-built agent workflow JSON definitions.
- **Agentic Reasoning**: `agentic_reasoning/` — Deep research reasoning loop (`deep_research.py`).

### Data Source Connectors (`/common/data_source/`)
Extensible connector framework for ingesting data from third-party services: Confluence, SharePoint, Google Drive, Dropbox, Slack, Notion, Discord, Jira, Airtable, Asana, Box, GitLab, IMAP, WebDAV, Zendesk, Moodle, and more. Each connector implements the interfaces in `interfaces.py`.

### Document Store (`/common/doc_store/`)
Abstraction layer for full-text and vector search storage. Supports Elasticsearch (`es_conn_pool.py`) and Infinity (`infinity_conn_pool.py`), switched via `DOC_ENGINE` env var.

### Plugin System (`/plugin/`)
`plugin_manager.py` provides a global plugin loader. Plugins can be bundled in `embedded_plugins/` or loaded dynamically. `llm_tool_plugin.py` handles LLM-based tool plugins.

### MCP Integration
- **Server**: `mcp/server/server.py` — exposes RAGFlow as an MCP server
- **Client**: `common/mcp_tool_call_conn.py` — manages MCP client sessions for connecting to external MCP tools

### Frontend (`/web/`)
- React/TypeScript with UmiJS framework
- Ant Design + shadcn/ui components
- State management with Zustand
- Tailwind CSS for styling

### Common (`/common/`)
Shared infrastructure: `settings.py` (global config), `constants.py` (enums like `LLMType`, `ParserType`, `PipelineTaskType`), `doc_store/` (ES/Infinity abstraction), `data_source/` (connectors), `crypto_utils.py`, `http_client.py`, `connection_utils.py`.

## Common Development Commands

### Backend Development
```bash
# Install Python dependencies
uv sync --python 3.12 --all-extras
uv run download_deps.py
pre-commit install

# Start dependent services (MinIO, Elasticsearch, Redis, MySQL)
docker compose -f docker/docker-compose-base.yml up -d

# Run backend (requires services to be running)
source .venv/bin/activate
export PYTHONPATH=$(pwd)
bash docker/launch_backend_service.sh

# Run all tests
uv run pytest

# Run a single test file
uv run pytest test/testcases/test_http_api/test_file_management.py

# Run tests by priority marker
uv run pytest -m p1
uv run pytest -m "p1 or p2"

# Run with coverage
uv run pytest --cov

# Linting
ruff check
ruff format
```

### Frontend Development
```bash
cd web
npm install
npm run dev        # Development server
npm run build      # Production build
npm run lint       # ESLint
npm run test       # Jest tests
```

### Docker Development
```bash
# Full stack with Docker
cd docker
docker compose -f docker-compose.yml up -d

# Check server status
docker logs -f ragflow-server

# Rebuild images
docker build --platform linux/amd64 -f Dockerfile -t infiniflow/ragflow:nightly .
```

## Key Configuration Files

- `docker/.env` — Environment variables for Docker deployment
- `docker/service_conf.yaml.template` — Backend service configuration (LLM factories, API keys)
- `pyproject.toml` — Python dependencies, pytest config (markers p1/p2/p3), ruff config, coverage config
- `web/package.json` — Frontend dependencies and scripts

## Testing

- **Python**: pytest with priority markers (`p1`/`p2`/`p3`). Tests in `test/testcases/` (HTTP API, SDK API, Web API) and `test/unit_test/`.
- **Frontend**: Jest with React Testing Library
- **SDK Tests**: Python SDK tests in `sdk/python/test/`

## Database Engines

RAGFlow supports MySQL (default) and PostgreSQL — set `DATABASE_TYPE=postgres` in `docker/.env`.

For document store, supports Elasticsearch (default) and Infinity:
- Set `DOC_ENGINE=infinity` in `docker/.env`
- Requires container restart: `docker compose down -v && docker compose up -d`

## Key Design Patterns

- **LLM Access**: Always use `LLMBundle(tenant_id, llm_type)` from `api/db/services/llm_service.py` to obtain LLM instances. It resolves the tenant's configured model factory and API key.
- **Async-first**: The Quart server uses `async def` route handlers. Agent canvas execution is async (`Graph.run()`).
- **Component Pattern**: Agent components declare parameters via `ComponentParamBase` subclass and implement logic in `ComponentBase` subclass. Components register with `@component_class` decorator.
- **Redis Communication**: Server and task executors communicate via Redis queues. The `REDIS_CONN` singleton from `rag/utils/redis_conn.py` is the shared client. `RedisDistributedLock` provides distributed mutual exclusion.
- **Pipeline Inheritance**: The ingestion pipeline (`rag/flow/pipeline.py`) inherits from the agent canvas (`agent/canvas.py:Graph`), so document processing pipelines use the same component DSL as agent workflows.

## Development Environment Requirements

- Python 3.10-3.12
- Node.js >=18.20.4
- Docker & Docker Compose
- uv package manager
- 16GB+ RAM, 50GB+ disk space
