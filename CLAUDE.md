# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **编码规范与行为准则**：请同时读取并严格遵守 [.claudecode-rules.md](.claudecode-rules.md)，包括：中文交互、最小改动优先、完整可替换代码输出、Google 风格 Docstring 等。

## Project Overview

RAGFlow is an open-source RAG (Retrieval-Augmented Generation) engine based on deep document understanding. It's a full-stack application with:
- Python backend (Quart-based API server — **not** Flask, all route handlers are `async def`)
- React/TypeScript frontend (built with UmiJS)
- Microservices architecture with Docker deployment
- Multiple data stores (MySQL/PostgreSQL, Elasticsearch/Infinity/OpenSearch/OceanBase, Redis/Valkey, MinIO)

## Process Architecture

The backend runs **two types of processes** (launched by `docker/launch_backend_service.sh`):
- **API Server**: `api/ragflow_server.py` — the main Quart HTTP server
- **Task Executors**: `rag/svr/task_executor.py` — `WS` worker processes (default 2) that run document parsing pipelines asynchronously

These communicate via **Redis** (queue, cache, distributed locks, session storage) and share the MySQL/PostgreSQL database. Document processing tasks are submitted by the server and picked up by task executors.

## Architecture

### Backend (`/api/`)
- **Entry Point**: `api/ragflow_server.py` — Quart app initialization, DB setup, signal handlers, Nacos service registration. The `RuntimeConfig` class (`api/db/runtime_config.py`) manages runtime settings (debug mode, HTTP port, env vars).
- **App Factory**: `api/apps/__init__.py` — auto-registers Flask-style Blueprints from `api/apps/*_app.py` files. Each `*_app.py` file defines a `manager` (Blueprint) that gets mounted at `/<API_VERSION>/<page_name>`. SDK endpoints live in `api/apps/sdk/` and are mounted at `/api/<API_VERSION>/...` (note the `/api/` prefix, unlike regular pages).
- **Services**: Business logic in `api/db/services/` (one service per domain: `document_service.py`, `dialog_service.py`, etc.). Joint services in `api/db/joint_services/` handle cross-domain logic (e.g., `memory_message_service.py`).
- **Models**: Peewee ORM models in `api/db/db_models.py` — supports MySQL (`PooledMySQLDatabase`) and PostgreSQL (`PooledPostgresqlDatabase`), switched via `DB_TYPE` env var. Uses custom field types (`JSONField`, `ListField`, `LongTextField`).
- **Auth**: Token-based via `quart_auth` + `itsdangerous` serializers. `login_required` and `api_key_required` decorators in `api/apps/__init__.py`.
- **Nacos**: `api/utils/nacos_registry.py` — optional service registration/discovery via Nacos, configurable via `NACOS_ENABLED`, `NACOS_SERVER_ADDR` env vars. Handles heartbeat, registration, and deregistration lifecycle.

### API Conventions
- All route handlers are `async def` (Quart).
- Standard response codes come from `RetCode` enum in `common/constants.py` (`SUCCESS = 0`, `ARGUMENT_ERROR = 101`, `DATA_ERROR = 102`, `AUTHENTICATION_ERROR = 109`, etc.).
- Enums use `CustomEnum` base class (in `common/constants.py`) which provides `.valid(value)`, `.values()`, and `.names()` convenience methods.
- Upload size limit is controlled by `MAX_CONTENT_LENGTH` env var (default 1GB).
- Quart response/body timeouts default to 600s (configurable via `QUART_RESPONSE_TIMEOUT` / `QUART_BODY_TIMEOUT` env vars) to accommodate slow LLM backends.

### Settings (`/common/settings.py`)
Settings are accessed as **module-level variables** (not a class instance): `settings.LLM`, `settings.CHAT_MDL`, `settings.SECRET_KEY`, etc. They are initialized by calling `settings.init_settings()`. The pattern is:
```python
from common import settings
settings.init_settings()
# Now use settings.LLM, settings.DOC_ENGINE, etc.
```
Database configs are decrypted at import time via `settings.decrypt_database_config(name=...)`.

### Core Processing (`/rag/`)
- **Document Processing**: `deepdoc/` — PDF parsing, OCR, layout analysis, vision models
- **LLM Integration**: `rag/llm/` — Model abstractions for chat (`chat_model.py`), embedding (`embedding_model.py`), reranking (`rerank_model.py`), CV (`cv_model.py`), OCR (`ocr_model.py`), TTS (`tts_model.py`), and sequence-to-text (`sequence2txt_model.py`). Use `LLMBundle(tenant_id, llm_type)` from `api/db/services/llm_service.py` to access models in components.
- **RAG Pipeline**: `rag/flow/` — The ingestion pipeline. `pipeline.py` defines `Pipeline` which **extends** `agent/canvas.py:Graph`. It's composed of parsers (`parser/`), splitters (`splitter/`), and extractors. The pipeline DSL is a JSON graph of components.
- **NLP**: `rag/nlp/` — Tokenization (`rag_tokenizer.py`), synonym handling, query classification, term weighting
- **Graph RAG**: `graphrag/` — Two modes: **general** (`general/` — full knowledge graph with entity extraction, community reports, Leiden clustering, mind map extraction) and **light** (`light/` — lighter graph extraction). Entry point: `graphrag/general/index.py::run_graphrag_for_kb`.

### Document Parsing (`/deepdoc/`)
- **Parsers** (`deepdoc/parser/`): One parser per document type — `pdf_parser.py`, `docx_parser.py`, `excel_parser.py`, `ppt_parser.py`, `html_parser.py`, `markdown_parser.py`, `json_parser.py`, `txt_parser.py`
- **MinerU** (`deepdoc/parser/mineru_parser.py`): External PDF parsing microservice. Configured via `MINERU_APISERVER`, `MINERU_BACKEND` (hybrid-auto-engine default), `MINERU_DELETE_OUTPUT` env vars. Uses `pdfplumber` for fallback extraction with a global lock (`LOCK_KEY_pdfplumber` stored in `sys.modules`).
- **DocLing** (`deepdoc/parser/docling_parser.py`): IBM DocLing-based parser, enabled via `USE_DOCLING=true`
- **Vision** (`deepdoc/vision/`): OCR engines (`ocr.py`, `t_ocr.py`), layout recognition, table structure recognition, image operators
- **Resume parser** (`deepdoc/parser/resume/`): Specialized entity extraction for resumes (corporations, schools, degrees, industries)
- **pdfplumber global lock**: Multiple modules (`pdf_parser.py`, `mineru_parser.py`, `deepdoc/vision/__init__.py`) use `sys.modules["global_shared_lock_pdfplumber"]` as a process-wide mutex for pdfplumber operations.

### Agent System (`/agent/`)
- **Canvas/DSL**: `agent/canvas.py` — `Graph` class parses a JSON DSL defining a directed graph of components with `upstream`/`downstream` edges. The graph is executed by traversing components in order.
- **Components**: `agent/component/` — Each component has two classes: a `ComponentParamBase` subclass (parameter definition/validation) and a `ComponentBase` subclass (runtime logic with `_invoke`/`_invoke_async` methods). Key components: `begin.py`, `llm.py`, `retrieval.py` (in tools), `categorize.py`, `switch.py`, `iteration.py`, `loop.py`, `message.py`.
- **Tools**: `agent/tools/` — External integrations callable from agent workflows: `tavily.py`, `wikipedia.py`, `duckduckgo.py`, `code_exec.py`, `email.py`, `github.py`, etc.
- **Templates**: `agent/templates/` — Pre-built agent workflow JSON definitions.
- **Agentic Reasoning**: `agentic_reasoning/` — Deep research reasoning loop (`deep_research.py`).

### Memory Module (`/memory/`)
Conversation memory system with its **own** ES/Infinity connectors (separate from the main doc store in `rag/utils/`):
- `memory/utils/es_conn.py` and `memory/utils/infinity_conn.py` — memory-specific search backends
- `memory/services/query.py` — memory query/retrieval logic
- `memory/services/messages.py` — message storage for conversations
- `memory/utils/prompt_util.py` and `memory/utils/msg_util.py` — prompt and message utilities

### Python SDK (`/sdk/python/`)
- `ragflow_sdk/ragflow.py` — main `RAGFlow` client class
- `ragflow_sdk/modules/` — domain modules: `dataset.py`, `document.py`, `chunk.py`, `chat.py`, `session.py`, `agent.py`
- SDK tests: `sdk/python/test/` (frontend API, HTTP API, SDK API test suites)

### Data Source Connectors (`/common/data_source/`)
Extensible connector framework for ingesting data from third-party services: Confluence, SharePoint, Google Drive, Dropbox, Slack, Notion, Discord, Jira, Airtable, Asana, Box, GitLab, IMAP, WebDAV, Zendesk, Moodle, and more. Each connector implements the interfaces in `interfaces.py`.

### Document Store (`/common/doc_store/`)
Abstraction layer for full-text and vector search storage. Supports Elasticsearch (`es_conn_pool.py`), Infinity (`infinity_conn_pool.py`), OpenSearch, and OceanBase, switched via `DOC_ENGINE` env var.

### Storage Backends (`/rag/utils/`)
Multiple storage backends for file/blob storage, configured via `STORAGE_IMPL` env var:
- **MinIO** (default): `minio_conn.py`
- **S3**: `s3_conn.py`
- **OSS** (Alibaba Cloud): `oss_conn.py`
- **Azure SAS**: `azure_sas_conn.py`
- **Azure SPN**: `azure_spn_conn.py`
- **GCS** (Google Cloud Storage): `gcs_conn.py`
- **OpenDAL**: `opendal_conn.py` — Apache OpenDAL-based unified multi-cloud storage (can wrap MySQL table, S3, OSS, Azure, etc.)

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

# Start dependent services (MinIO, Elasticsearch/Infinity, Redis/Valkey, MySQL)
docker compose -f docker/docker-compose-base.yml up -d

# Run backend (requires services to be running)
source .venv/bin/activate
export PYTHONPATH=$(pwd)
bash docker/launch_backend_service.sh

# Run with debug mode and remote debugging
python api/ragflow_server.py --debug
RAGFLOW_DEBUGPY_LISTEN=5678 python api/ragflow_server.py  # attach debugpy on port 5678

# Run all tests
uv run pytest

# Run a single test file
uv run pytest test/testcases/test_http_api/test_file_management/test_upload_documents.py

# Run tests by priority marker
uv run pytest -m p1
uv run pytest -m "p1 or p2"

# Run with coverage
uv run pytest --cov

# Linting
ruff check
ruff format

# Pre-commit (run all hooks manually)
pre-commit run --all-files
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
- `conf/service_conf.yaml` — Runtime config (copied from template, gitignored)
- `pyproject.toml` — Python dependencies, pytest config (markers p1/p2/p3), ruff config, coverage config
- `web/package.json` — Frontend dependencies and scripts
- `AGENTS.md` — GitHub Copilot instructions (defines project structure and coding standards)

## Testing

- **Python**: pytest with priority markers (`p1`/`p2`/`p3`). Tests in `test/testcases/` organized into three suites:
  - `test_http_api/` — HTTP API integration tests
  - `test_sdk_api/` — SDK API integration tests
  - `test_web_api/` — Web frontend API tests
  - `test/unit_test/` — Unit tests
  - Each test suite uses its own `conftest.py` for fixtures and has subdirectories per domain (e.g., `test_file_management_within_dataset/`, `test_chunk_management_within_dataset/`).
- **Frontend**: Jest with React Testing Library
- **SDK Tests**: Python SDK tests in `sdk/python/test/`

## Database Engines

RAGFlow supports MySQL (default) and PostgreSQL — set `DB_TYPE=postgres` in `docker/.env`.

For document store, supports Elasticsearch (default), Infinity, OpenSearch, and OceanBase:
- Set `DOC_ENGINE=infinity|oceanbase|opensearch` in `docker/.env`
- Requires container restart: `docker compose down -v && docker compose up -d`

## Key Design Patterns

- **LLM Access**: Always use `LLMBundle(tenant_id, llm_type)` from `api/db/services/llm_service.py` to obtain LLM instances. It resolves the tenant's configured model factory and API key.
- **Async-first**: The Quart server uses `async def` route handlers. Agent canvas execution is async (`Graph.run()`).
- **Component Pattern**: Agent components declare parameters via `ComponentParamBase` subclass and implement logic in `ComponentBase` subclass. Components register with `@component_class` decorator.
- **Redis Communication**: Server and task executors communicate via Redis queues. The `REDIS_CONN` singleton from `rag/utils/redis_conn.py` is the shared client. `RedisDistributedLock` provides distributed mutual exclusion.
- **Pipeline Inheritance**: The ingestion pipeline (`rag/flow/pipeline.py`) inherits from the agent canvas (`agent/canvas.py:Graph`), so document processing pipelines use the same component DSL as agent workflows.
- **Global Lock via sys.modules**: The pdfplumber library is not thread-safe, so RAGFlow uses `sys.modules["global_shared_lock_pdfplumber"]` as a process-wide `threading.Lock()`. When adding parsers with thread-unsafe dependencies, follow this pattern.
- **Task Cancellation**: Long-running operations (pipelines, Graph RAG) periodically check `has_canceled(task_id)` from `api/db/services/task_service.py`. When a task is canceled, they should raise `TaskCanceledException` from `common/exceptions.py`.

## Key Environment Variables (Runtime)

| Variable | Default | Purpose |
|----------|---------|---------|
| `DB_TYPE` | `mysql` | Database type: `mysql` or `postgres` |
| `DOC_ENGINE` | `elasticsearch` | Document store: `elasticsearch`, `infinity`, `oceanbase`, `opensearch` |
| `STORAGE_IMPL` | (MinIO) | Object storage: `OSS`, `S3`, `AZURE_SAS`, `AZURE_SPN`, `GCS`, `OPENDAL` |
| `NACOS_ENABLED` | — | Enable Nacos service registration |
| `NACOS_SERVER_ADDR` | — | Nacos server `host:port` |
| `MINERU_APISERVER` | — | MinerU PDF parsing service URL |
| `MINERU_BACKEND` | `hybrid-auto-engine` | MinerU parsing engine |
| `USE_DOCLING` | `false` | Enable IBM DocLing parser |
| `SANDBOX_ENABLED` | — | Enable code execution sandbox |
| `RAGFLOW_DEBUGPY_LISTEN` | `0` | Enable debugpy remote debugging port |
| `QUART_RESPONSE_TIMEOUT` | `600` | Quart response timeout in seconds (for slow LLM backends) |
| `QUART_BODY_TIMEOUT` | `600` | Quart body timeout in seconds |
| `MAX_CONTENT_LENGTH` | `1073741824` | Max upload size in bytes (default 1GB) |
| `DOC_BULK_SIZE` | `32` | Chunks per batch during document processing |
| `EMBEDDING_BATCH_SIZE` | `32` | Chunks per embedding API batch |

## Development Environment Requirements

- Python 3.10-3.12
- Node.js >=18.20.4
- Docker & Docker Compose
- uv package manager
- 16GB+ RAM, 50GB+ disk space
