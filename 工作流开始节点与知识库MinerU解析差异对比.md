# 工作流开始节点与知识库MinerU解析差异对比

## 概述

本文档详细对比了工作流开始节点（Begin Node）和知识库（Knowledge Base）在处理PDF文件时使用MinerU解析器的完整流程差异，包括配置来源、解析入口、数据处理、结果存储等方面的不同。

---

## 目录

1. [配置来源差异](#配置来源差异)
2. [解析入口差异](#解析入口差异)
3. [Parser Config构建差异](#parser-config构建差异)
4. [文件处理流程差异](#文件处理流程差异)
5. [结果处理差异](#结果处理差异)
6. [存储与索引差异](#存储与索引差异)
7. [分块策略差异](#分块策略差异)
8. [并发处理差异](#并发处理差异)
9. [错误处理差异](#错误处理差异)
10. [完整流程对比图](#完整流程对比图)

---

## 配置来源差异

### 工作流开始节点

**配置来源**: 前端用户输入，通过工作流执行请求传递

**配置路径**:
```
前端UI → Begin节点inputs → pdf_parser_config → parser_config
```

**配置位置**: 
- 前端: `web/src/pages/agent/form/begin-form/parameter-dialog.tsx`
- 后端: `agent/component/begin.py:55-83`

**配置特点**:
- 每次执行工作流时，用户在前端配置解析器选项
- 配置参数包括：
  - `parse_method`: "MinerU"
  - `mineru_parse_method`: "auto" | "txt" | "ocr"
  - `mineru_lang`: 语言选项（20种语言）
  - `mineru_formula_enable`: true/false
  - `mineru_table_enable`: true/false
  - `chunk_token_num`: 建议文本块大小
  - `delimiter`: 文本分段标识符
  - `enable_children`: 是否启用子块
  - `children_delimiter`: 子块分隔符

**代码示例**:
```python
# agent/component/begin.py
if v.get("type", "").lower() == "pdf":
    pdf_parser_config = {}
    if v.get("parse_method"):
        pdf_parser_config["parse_method"] = v.get("parse_method")
    if v.get("mineru_parse_method"):
        pdf_parser_config["mineru_parse_method"] = v.get("mineru_parse_method")
    # ... 其他配置
```

### 知识库

**配置来源**: 知识库的 `parser_config` 字段，存储在数据库中

**配置路径**:
```
知识库设置 → kb.parser_config → doc.parser_config → task["parser_config"] → parser_config
```

**配置位置**:
- 前端: `web/src/pages/dataset/dataset-setting/index.tsx`
- 后端: `api/db/services/file_service.py:471` (上传时复制到文档)
- 后端: `api/db/services/task_service.py:126-130` (任务执行时使用)

**配置特点**:
- 配置存储在知识库的 `parser_config` 字段中
- 上传文档时，文档的 `parser_config` 从知识库的 `parser_config` 复制
- 配置参数包括：
  - `layout_recognize`: "MinerU"
  - `mineru_parse_method`: "auto" | "txt" | "ocr"
  - `mineru_lang`: 语言选项
  - `mineru_formula_enable`: true/false
  - `mineru_table_enable`: true/false
  - `chunk_token_num`: 建议文本块大小
  - `delimiter`: 文本分段标识符
  - 其他知识库特定配置（如 `table_context_size`, `image_context_size` 等）

**代码示例**:
```python
# api/db/services/file_service.py:upload_document()
doc = {
    "id": doc_id,
    "kb_id": kb.id,
    "parser_id": self.get_parser(filetype, filename, kb.parser_id),
    "parser_config": kb.parser_config,  # 从知识库复制配置
    # ...
}

# api/db/services/task_service.py:get_task()
kb_config = docs[0]['kb_parser_config']  # 从知识库获取配置
mineru_method = kb_config.get('mineru_parse_method', 'auto')
mineru_formula = kb_config.get('mineru_formula_enable', True)
mineru_table = kb_config.get('mineru_table_enable', True)
```

---

## 解析入口差异

### 工作流开始节点

**入口函数**: `Begin._invoke()`

**调用链**:
```
Begin._invoke()
  → FileService.get_files([file_id], pdf_parser_config)
    → FileService.parse(filename, blob, pdf_parser_config=pdf_parser_config)
      → naive.chunk(filename, blob, parser_config=parser_config, **kwargs)
        → by_mineru(filename, binary, **kwargs)
          → MinerUParser.parse_pdf()
```

**文件路径**:
- `agent/component/begin.py:40-88`
- `api/db/services/file_service.py:698-715` (get_files)
- `api/db/services/file_service.py:514-569` (parse)

**特点**:
- 同步处理，直接返回结果
- 使用线程池并发处理多个文件（最多5个线程）
- 结果格式化为字符串返回

### 知识库

**入口函数**: `task_executor.build_chunks()`

**调用链**:
```
TaskService.queue_tasks()
  → 创建Task记录
    → Redis任务队列
      → task_executor.handle_task()
        → task_executor.build_chunks(task, progress_callback)
          → chunker.chunk(filename, binary, parser_config=task["parser_config"], **kwargs)
            → by_mineru(filename, binary, **kwargs)
              → MinerUParser.parse_pdf()
```

**文件路径**:
- `api/db/services/task_service.py:367-435` (queue_tasks)
- `rag/svr/task_executor.py:235-280` (build_chunks)
- `rag/app/naive.py:659-796` (chunk)

**特点**:
- 异步处理，通过任务队列执行
- 支持任务重试机制（最多3次）
- 支持进度回调，实时更新任务进度
- 支持任务取消

---

## Parser Config构建差异

### 工作流开始节点

**默认值**:
```python
# api/db/services/file_service.py:522
parser_config = {
    "chunk_token_num": 16096, 
    "delimiter": "\n!?;。；！？", 
    "layout_recognize": "Plain Text"
}
```

**更新逻辑**:
```python
# 如果提供了pdf_parser_config，更新parser_config
if pdf_parser_config:
    if pdf_parser_config.get("parse_method"):
        parser_config["layout_recognize"] = pdf_parser_config["parse_method"]
    
    # MinerU相关配置
    if pdf_parser_config.get("mineru_parse_method"):
        parser_config["mineru_parse_method"] = pdf_parser_config["mineru_parse_method"]
    if pdf_parser_config.get("mineru_formula_enable") is not None:
        parser_config["mineru_formula_enable"] = pdf_parser_config["mineru_formula_enable"]
    if pdf_parser_config.get("mineru_table_enable") is not None:
        parser_config["mineru_table_enable"] = pdf_parser_config["mineru_table_enable"]
    if pdf_parser_config.get("mineru_lang"):
        parser_config["mineru_lang"] = pdf_parser_config["mineru_lang"]
    
    # 文本分块配置
    if pdf_parser_config.get("chunk_token_num") is not None:
        parser_config["chunk_token_num"] = pdf_parser_config["chunk_token_num"]
    if pdf_parser_config.get("delimiter"):
        parser_config["delimiter"] = pdf_parser_config["delimiter"]
    if pdf_parser_config.get("enable_children") is not None:
        parser_config["enable_children"] = pdf_parser_config["enable_children"]
    if pdf_parser_config.get("children_delimiter"):
        parser_config["children_delimiter"] = pdf_parser_config["children_delimiter"]
```

**语言设置**:
```python
lang = "English"
if pdf_parser_config and pdf_parser_config.get("lang"):
    lang = pdf_parser_config["lang"]
elif pdf_parser_config and pdf_parser_config.get("mineru_lang"):
    lang = pdf_parser_config["mineru_lang"]
```

### 知识库

**配置来源**: 直接使用文档的 `parser_config`（来自知识库配置）

**更新逻辑**:
```python
# api/db/services/file_service.py:upload_document()
doc = {
    "parser_config": kb.parser_config,  # 直接使用知识库配置
    # ...
}

# rag/svr/task_executor.py:build_chunks()
cks = await asyncio.to_thread(
    chunker.chunk,
    task["name"],
    binary=binary,
    from_page=task["from_page"],
    to_page=task["to_page"],
    lang=task["language"],  # 来自知识库的language字段
    callback=progress_callback,
    kb_id=task["kb_id"],
    parser_config=task["parser_config"],  # 直接使用任务中的parser_config
    tenant_id=task["tenant_id"],
)
```

**语言设置**:
- 使用知识库的 `language` 字段（`task["language"]`）
- 如果知识库配置中有 `mineru_lang`，会从 `parser_config` 中获取

**配置合并**:
- 知识库的 `parser_config` 可能包含更多配置项，如：
  - `table_context_size`: 表格上下文窗口大小
  - `image_context_size`: 图片上下文窗口大小
  - `auto_keywords`: 自动关键词提取数量
  - `auto_questions`: 自动问题生成数量
  - `toc_extraction`: 是否提取目录
  - `raptor`: RAPTOR配置
  - `graphrag`: GraphRAG配置

---

## 文件处理流程差异

### 工作流开始节点

**文件获取**:
```python
# api/db/services/file_service.py:get_files()
for file in files:
    if file["mime_type"].find("pdf") >= 0 and pdf_parser_config:
        threads.append(exe.submit(
            FileService.parse, 
            file["name"], 
            FileService.get_blob(file["created_by"], file["id"]),  # 从用户下载存储获取
            True, 
            file["created_by"], 
            pdf_parser_config
        ))
```

**特点**:
- 文件存储在用户的下载存储中（`{user_id}-downloads`）
- 使用 `FileService.get_blob()` 获取文件二进制内容
- 同步处理，立即返回结果

### 知识库

**文件获取**:
```python
# rag/svr/task_executor.py:build_chunks()
bucket, name = File2DocumentService.get_storage_address(doc_id=task["doc_id"])
binary = await get_storage_binary(bucket, name)  # 从知识库存储获取
```

**特点**:
- 文件存储在知识库的存储桶中（`kb.id`）
- 使用 `File2DocumentService.get_storage_address()` 获取存储地址
- 异步处理，通过任务队列执行

---

## 结果处理差异

### 工作流开始节点

**结果格式**:
```python
# api/db/services/file_service.py:568-569
cks = naive.chunk(filename, blob, **kwargs)
return f"\n -----------------\nFile: {filename}\nContent as following: \n" + "\n".join([ck["content_with_weight"] for ck in cks])
```

**输出设置**:
```python
# agent/component/begin.py:87-88
self.set_output(k, v)  # 设置节点输出
self.set_input_value(k, v)  # 保存输入值
```

**特点**:
- 结果格式化为字符串
- 包含文件名和所有分块内容
- 通过 `set_output()` 传递给下一个节点
- 不进行存储，仅在工作流执行期间使用

**使用方式**:
- 下一个节点可以通过变量引用访问：`{Begin@variable_key}`
- Message节点可以将内容插入到消息模板中
- LLM节点可以将内容作为上下文使用

### 知识库

**结果处理**:
```python
# rag/svr/task_executor.py:build_chunks()
cks = await asyncio.to_thread(chunker.chunk, ...)  # 获取分块列表

# 构建文档chunk对象
docs = []
doc = {
    "doc_id": task["doc_id"],
    "kb_id": str(task["kb_id"])
}
for ck in cks:
    d = copy.deepcopy(doc)
    d.update(ck)
    d["id"] = xxhash.xxh64((ck["content_with_weight"] + str(d["doc_id"])).encode("utf-8")).hexdigest()
    d["create_time"] = str(datetime.now()).replace("T", " ")[:19]
    d["create_timestamp_flt"] = datetime.now().timestamp()
    # 处理图片
    if d.get("image"):
        await image2id(d, partial(settings.STORAGE_IMPL.put, tenant_id=task["tenant_id"]), d["id"], task["kb_id"])
    docs.append(d)
```

**后续处理**:
```python
# rag/svr/task_executor.py:1071-1103
# 1. 生成向量嵌入
token_count, vector_size = await embedding(docs, embedding_model, task_parser_config, progress_callback)

# 2. 存储到文档存储（ES/Infinity）
insert_result = await insert_es(task_id, task_tenant_id, task_dataset_id, docs, progress_callback)

# 3. 更新文档统计信息
DocumentService.increment_chunk_num(task_doc_id, task_dataset_id, token_count, chunk_count, 0)

# 4. 可选：生成关键词和问题
if task["parser_config"].get("auto_keywords", 0):
    # 为每个chunk生成关键词
    ...
if task["parser_config"].get("auto_questions", 0):
    # 为每个chunk生成问题
    ...
```

**特点**:
- 结果保存为chunk对象列表
- 每个chunk包含完整的元数据（doc_id, kb_id, id, create_time等）
- 进行向量嵌入（embedding）
- 存储到文档存储系统（Elasticsearch/Infinity）
- 支持后续检索和查询

---

## 存储与索引差异

### 工作流开始节点

**存储方式**: 不存储，仅在工作流执行期间使用

**数据流向**:
```
解析结果 → 格式化字符串 → Begin节点输出 → 下一个节点输入
```

**特点**:
- 结果不持久化
- 每次工作流执行时重新解析
- 结果仅在工作流执行期间可用

### 知识库

**存储方式**: 持久化存储到文档存储系统

**数据流向**:
```
解析结果 → Chunk对象 → 向量嵌入 → ES/Infinity索引 → 支持检索查询
```

**存储内容**:
- Chunk文本内容（`content_with_weight`）
- 向量嵌入（`q_*_vec`）
- 元数据（doc_id, kb_id, create_time等）
- 关键词（如果启用 `auto_keywords`）
- 问题（如果启用 `auto_questions`）
- 图片ID（如果有图片）

**索引字段**:
- `doc_id`: 文档ID
- `kb_id`: 知识库ID
- `id`: Chunk ID（基于内容hash生成）
- `content_with_weight`: 文本内容
- `content_ltks`: 内容token
- `title_tks`: 标题token
- `q_*_vec`: 向量嵌入
- `important_kwd`: 关键词（可选）
- `important_tks`: 关键词token（可选）

**特点**:
- 结果持久化存储
- 支持向量检索
- 支持关键词检索
- 支持后续更新和删除

---

## 分块策略差异

### 工作流开始节点

**分块处理**:
```python
# rag/app/naive.py:792-793
if name in ["tcadp", "docling", "mineru"]:
    parser_config["chunk_token_num"] = 0  # MinerU已经分块，不再合并

# 对于MinerU，每个section作为一个独立的chunk
res = tokenize_table(tables, doc, is_english)
```

**特点**:
- 对于MinerU，`chunk_token_num` 被设置为0
- 每个MinerU解析的section作为一个独立的chunk
- 不进行额外的文本合并
- 用户配置的 `chunk_token_num` 和 `delimiter` 对MinerU无效（但会传递给其他解析器）

### 知识库

**分块处理**:
```python
# rag/app/naive.py:792-793
if name in ["tcadp", "docling", "mineru"]:
    parser_config["chunk_token_num"] = 0  # MinerU已经分块，不再合并

# 对于MinerU，每个section作为一个独立的chunk
res = tokenize_table(tables, doc, is_english)
```

**特点**:
- 对于MinerU，`chunk_token_num` 也被设置为0
- 每个MinerU解析的section作为一个独立的chunk
- 不进行额外的文本合并
- 知识库配置的 `chunk_token_num` 和 `delimiter` 对MinerU无效

**相同点**:
- 两者对MinerU的分块策略相同
- 都设置 `chunk_token_num = 0`
- 都保持MinerU的原始分块结果

---

## 并发处理差异

### 工作流开始节点

**并发方式**:
```python
# api/db/services/file_service.py:705-715
exe = ThreadPoolExecutor(max_workers=5)  # 最多5个并发线程
threads = []
for file in files:
    threads.append(exe.submit(FileService.parse, ...))
return [th.result() for th in threads]  # 等待所有线程完成
```

**特点**:
- 使用线程池，最多5个并发线程
- 同步等待所有文件处理完成
- 适用于少量文件（通常1-2个文件）

### 知识库

**并发方式**:
```python
# api/db/services/document_service.py:1152-1166
exe = ThreadPoolExecutor(max_workers=12)  # 最多12个并发线程
threads = []
for d, blob in files:
    threads.append(exe.submit(FACTORY.get(d["parser_id"], naive).chunk, ...))

# 异步处理，通过任务队列
# rag/svr/task_executor.py:262
async with chunk_limiter:  # 限制并发数
    cks = await asyncio.to_thread(chunker.chunk, ...)
```

**特点**:
- 使用线程池，最多12个并发线程（上传时）
- 异步任务队列处理（实际解析时）
- 支持大量文件并发处理
- 支持任务优先级和重试

---

## 错误处理差异

### 工作流开始节点

**错误处理**:
```python
# agent/component/begin.py:40-42
def _invoke(self, **kwargs):
    if self.check_if_canceled("Begin processing"):
        return
    # ... 处理逻辑
```

**特点**:
- 简单的取消检查
- 错误会传播到工作流引擎
- 不进行重试
- 错误信息返回给前端

### 知识库

**错误处理**:
```python
# api/db/services/task_service.py:136-144
if docs[0]["retry_count"] >= 3:
    msg = "\nERROR: Task is abandoned after 3 times attempts."
    prog = -1
    return None

# rag/svr/task_executor.py:1164-1176
try:
    await do_handle_task(task)
except Exception as e:
    err_msg = str(e)
    set_progress(task_id, prog=-1, msg=f"[Exception]: {err_msg}")
    logging.exception(f"handle_task got exception for task {json.dumps(task)}")
```

**特点**:
- 支持任务重试（最多3次）
- 详细的错误日志记录
- 错误信息更新到任务进度
- 支持任务取消
- 错误信息持久化到数据库

---

## 完整流程对比图

### 工作流开始节点流程

```
┌─────────────────────────────────────────────────────────────┐
│                    前端用户操作                              │
│  1. 配置Begin节点：选择PDF类型，选择MinerU解析器            │
│  2. 配置MinerU选项和文本分块选项                            │
│  3. 上传PDF文件                                             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  前端请求发送                                │
│  构建请求：inputs包含文件ID和所有配置参数                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│               后端Begin节点处理                              │
│  Begin._invoke()                                            │
│  1. 提取PDF配置参数                                         │
│  2. 构建pdf_parser_config                                   │
│  3. 调用FileService.get_files()                             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                 文件服务处理                                │
│  FileService.get_files()                                    │
│  1. 从用户下载存储获取文件                                  │
│  2. 调用FileService.parse()，传递pdf_parser_config          │
│                                                                 │
│  FileService.parse()                                        │
│  1. 构建parser_config（默认值+用户配置）                    │
│  2. 调用naive.chunk()                                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                MinerU解析器处理                             │
│  naive.chunk() → by_mineru() → MinerUParser.parse_pdf()     │
│  1. 解析PDF，提取sections和tables                           │
│  2. 设置chunk_token_num=0                                   │
│  3. 每个section作为一个独立的chunk                          │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   结果格式化                                │
│  FileService.parse()                                        │
│  1. 格式化分块结果为字符串                                   │
│  2. 返回格式化的文本内容                                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   输出传递                                  │
│  Begin节点                                                  │
│  1. set_output() 设置输出变量                               │
│  2. 输出传递给下一个节点（Message/LLM等）                  │
└─────────────────────────────────────────────────────────────┘
```

### 知识库流程

```
┌─────────────────────────────────────────────────────────────┐
│                    前端用户操作                              │
│  1. 在知识库设置中配置MinerU解析器选项                      │
│  2. 上传PDF文件到知识库                                     │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  文件上传处理                                │
│  FileService.upload_document()                              │
│  1. 保存文件到知识库存储                                    │
│  2. 创建Document记录，复制kb.parser_config到doc.parser_config│
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  任务队列创建                                │
│  TaskService.queue_tasks()                                  │
│  1. 根据文档类型和配置创建Task记录                          │
│  2. 将任务加入Redis队列                                     │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  任务执行器处理                             │
│  task_executor.handle_task()                                │
│  1. 从Redis队列获取任务                                     │
│  2. 调用build_chunks()                                      │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                 文件获取与解析                              │
│  build_chunks()                                             │
│  1. 从知识库存储获取文件                                    │
│  2. 调用chunker.chunk()，传递task["parser_config"]         │
│                                                                 │
│  naive.chunk() → by_mineru() → MinerUParser.parse_pdf()   │
│  1. 解析PDF，提取sections和tables                           │
│  2. 设置chunk_token_num=0                                   │
│  3. 每个section作为一个独立的chunk                          │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  Chunk对象构建                              │
│  build_chunks()                                             │
│  1. 为每个chunk添加元数据（doc_id, kb_id, id等）           │
│  2. 处理图片，上传到存储                                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  向量嵌入生成                               │
│  embedding()                                                │
│  1. 为每个chunk生成向量嵌入                                 │
│  2. 计算token数量                                           │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  存储到文档索引                             │
│  insert_es()                                                │
│  1. 存储chunk到ES/Infinity                                   │
│  2. 更新文档统计信息                                        │
│  3. 可选：生成关键词和问题                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 关键差异总结表

| 对比项 | 工作流开始节点 | 知识库 |
|--------|--------------|--------|
| **配置来源** | 前端用户输入（每次执行时配置） | 知识库parser_config（存储在数据库） |
| **解析入口** | `Begin._invoke()` → `FileService.get_files()` → `FileService.parse()` | `TaskService.queue_tasks()` → `task_executor.build_chunks()` |
| **文件存储** | 用户下载存储（`{user_id}-downloads`） | 知识库存储（`kb.id`） |
| **处理方式** | 同步处理，立即返回 | 异步处理，任务队列执行 |
| **结果格式** | 格式化为字符串 | Chunk对象列表 |
| **结果存储** | 不存储，仅在工作流执行期间使用 | 持久化存储到ES/Infinity |
| **向量嵌入** | 不进行向量嵌入 | 进行向量嵌入，支持检索 |
| **分块策略** | `chunk_token_num=0`（MinerU已分块） | `chunk_token_num=0`（MinerU已分块） |
| **并发处理** | 线程池，最多5个线程 | 线程池，最多12个线程（上传时） |
| **错误处理** | 简单取消检查，不重试 | 支持重试（最多3次），详细错误日志 |
| **进度跟踪** | 无进度跟踪 | 支持进度回调，实时更新任务进度 |
| **任务管理** | 无任务管理 | 支持任务队列、优先级、取消 |
| **后续处理** | 直接传递给下一个节点 | 生成关键词、问题，支持检索查询 |

---

## 代码路径对比

### 工作流开始节点

1. **前端配置**: `web/src/pages/agent/form/begin-form/parameter-dialog.tsx`
2. **Begin节点**: `agent/component/begin.py`
3. **文件服务**: `api/db/services/file_service.py`
   - `get_files()`: 698-715
   - `parse()`: 514-569
4. **分块处理**: `rag/app/naive.py`
   - `chunk()`: 659-796
   - `by_mineru()`: 67-113
5. **MinerU解析器**: `deepdoc/parser/mineru_parser.py`
   - `parse_pdf()`: 543-635

### 知识库

1. **前端配置**: `web/src/pages/dataset/dataset-setting/index.tsx`
2. **文件上传**: `api/db/services/file_service.py`
   - `upload_document()`: 431-488
3. **任务创建**: `api/db/services/task_service.py`
   - `queue_tasks()`: 367-435
   - `get_task()`: 73-149
4. **任务执行**: `rag/svr/task_executor.py`
   - `build_chunks()`: 235-280
   - `do_handle_task()`: 896-1125
5. **分块处理**: `rag/app/naive.py`
   - `chunk()`: 659-796
   - `by_mineru()`: 67-113
6. **MinerU解析器**: `deepdoc/parser/mineru_parser.py`
   - `parse_pdf()`: 543-635

---

## 配置参数对比

### 工作流开始节点配置参数

| 参数名 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| `parse_method` | string | PDF解析方法 | "MinerU" |
| `mineru_parse_method` | enum | MinerU解析方法 | "auto" |
| `mineru_lang` | string | MinerU语言设置 | "Chinese" |
| `mineru_formula_enable` | boolean | 是否启用公式识别 | true |
| `mineru_table_enable` | boolean | 是否启用表格识别 | true |
| `chunk_token_num` | number | 建议文本块大小（对MinerU无效） | 512 |
| `delimiter` | string | 文本分段标识符（对MinerU无效） | "\n" |
| `enable_children` | boolean | 是否启用子块 | false |
| `children_delimiter` | string | 子块分隔符 | "\n" |

### 知识库配置参数

| 参数名 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| `layout_recognize` | string | PDF解析方法 | "MinerU" |
| `mineru_parse_method` | enum | MinerU解析方法 | "auto" |
| `mineru_lang` | string | MinerU语言设置 | 知识库language字段 |
| `mineru_formula_enable` | boolean | 是否启用公式识别 | true |
| `mineru_table_enable` | boolean | 是否启用表格识别 | true |
| `chunk_token_num` | number | 建议文本块大小（对MinerU无效） | 4096 |
| `delimiter` | string | 文本分段标识符（对MinerU无效） | "\n!?;。；！？" |
| `table_context_size` | number | 表格上下文窗口大小 | 0 |
| `image_context_size` | number | 图片上下文窗口大小 | 0 |
| `auto_keywords` | number | 自动关键词提取数量 | 0 |
| `auto_questions` | number | 自动问题生成数量 | 0 |
| `toc_extraction` | boolean | 是否提取目录 | false |

---

## 注意事项

### 工作流开始节点

1. **配置作用域**: 配置仅对当前工作流执行有效，不会持久化
2. **结果格式**: 结果是格式化的字符串，不是结构化的chunk对象
3. **性能考虑**: 每次执行工作流都会重新解析文件，不进行缓存
4. **文件限制**: 文件存储在用户下载存储中，有存储空间限制

### 知识库

1. **配置持久化**: 配置存储在知识库的 `parser_config` 字段中，对所有上传的文档生效
2. **结果存储**: 结果持久化存储，支持后续检索和查询
3. **性能优化**: 解析结果缓存，支持任务重试和错误恢复
4. **扩展功能**: 支持关键词提取、问题生成、向量检索等高级功能

---

## 总结

工作流开始节点和知识库在处理PDF文件时使用MinerU解析器的主要差异在于：

1. **配置管理**: 工作流开始节点使用临时配置（每次执行时配置），知识库使用持久化配置（存储在数据库中）
2. **处理方式**: 工作流开始节点同步处理，知识库异步任务队列处理
3. **结果处理**: 工作流开始节点格式化返回字符串，知识库生成chunk对象并存储
4. **存储策略**: 工作流开始节点不存储结果，知识库持久化存储并建立索引
5. **功能扩展**: 知识库支持更多高级功能（向量检索、关键词提取、问题生成等）

两者在MinerU解析器的核心解析逻辑上是相同的，差异主要体现在配置管理、结果处理和存储策略上。
