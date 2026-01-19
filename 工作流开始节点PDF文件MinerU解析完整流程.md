# 工作流开始节点PDF文件MinerU解析完整流程

## 概述

本文档详细描述了在工作流开始节点（Begin Node）中，任务模式下上传PDF文件并选择MinerU解析器后的完整工作流程，包括文件上传、解析处理、数据传递和最终回传给前端回复消息节点的全过程。

---

## 目录

1. [前端用户操作](#前端用户操作)
2. [前端请求发送](#前端请求发送)
3. [后端Begin节点处理](#后端begin节点处理)
4. [文件服务处理](#文件服务处理)
5. [MinerU解析器处理](#mineru解析器处理)
6. [文本分块处理](#文本分块处理)
7. [结果返回与传递](#结果返回与传递)
8. [前端接收与显示](#前端接收与显示)
9. [流程图](#流程图)
10. [关键代码路径](#关键代码路径)

---

## 前端用户操作

### 1.1 配置工作流开始节点

**位置**: `web/src/pages/agent/form/begin-form/parameter-dialog.tsx`

用户在任务模式下配置工作流开始节点：

1. **选择变量类型**: 选择 `PDF` 类型
2. **配置变量信息**:
   - 设置变量键（key）
   - 设置变量名称（name）
   - 设置是否可选（optional）

3. **选择PDF解析器**: 在解析方法下拉框中选择 `MinerU`

4. **配置MinerU选项**:
   - **解析方法（mineru_parse_method）**: 
     - `auto`（自动检测，默认值）
     - `txt`（文本提取）
     - `ocr`（光学字符识别）
   - **语言（mineru_lang）**: 
     - 支持20种语言选项（English、Chinese、Traditional Chinese、Russian等）
     - 默认值：`Chinese`
   - **公式识别（mineru_formula_enable）**: 
     - 开关按钮，默认值：`true`
   - **表格识别（mineru_table_enable）**: 
     - 开关按钮，默认值：`true`

5. **配置文本分块选项**:
   - **建议文本块大小（chunk_token_num）**: 
     - 滑块输入，范围1-2048，默认值：512
   - **文本分段标识符（delimiter）**: 
     - 分隔符输入框，默认值：`\n`
   - **Child chunk are used for retrieval（enable_children）**: 
     - 开关按钮，默认值：`false`
   - **Delimiter for text（children_delimiter）**: 
     - 仅在 `enable_children` 为true时显示，默认值：`\n`

### 1.2 上传PDF文件

用户在工作流执行时上传PDF文件，文件通过前端API上传到服务器，返回文件元数据（包含文件ID、名称、MIME类型等）。

---

## 前端请求发送

### 2.1 构建请求数据

**位置**: `web/src/pages/agent/chat/use-send-agent-message.ts`

前端构建工作流执行请求，包含：

```typescript
{
  inputs: {
    [variable_key]: {
      type: "pdf",
      value: file_id,  // 上传后返回的文件ID
      optional: false,
      name: "文件变量名称",
      // MinerU配置
      parse_method: "MinerU",
      mineru_parse_method: "auto",
      mineru_lang: "Chinese",
      mineru_formula_enable: true,
      mineru_table_enable: true,
      // 文本分块配置
      chunk_token_num: 512,
      delimiter: "\n",
      enable_children: false,
      children_delimiter: "\n"
    }
  },
  mode: "task"  // 任务模式
}
```

### 2.2 发送API请求

前端通过SSE（Server-Sent Events）或HTTP请求将数据发送到后端工作流执行接口。

---

## 后端Begin节点处理

### 3.1 Begin节点初始化

**文件路径**: `agent/component/begin.py`

**类**: `Begin` (继承自 `UserFillUp`)

当工作流开始执行时，`Begin` 节点的 `_invoke()` 方法被调用。

### 3.2 提取PDF配置

**代码位置**: `agent/component/begin.py:40-85`

```python
def _invoke(self, **kwargs):
    # 遍历所有输入参数
    for k, v in kwargs.get("inputs", {}).items():
        # 检查是否为文件类型或PDF类型
        if isinstance(v, dict) and (
            v.get("type", "").lower().find("file") >= 0 or 
            v.get("type", "").lower() == "pdf"
        ):
            # 构建PDF解析器配置
            pdf_parser_config = None
            if v.get("type", "").lower() == "pdf":
                pdf_parser_config = {}
                # 提取所有配置参数
                if v.get("parse_method"):
                    pdf_parser_config["parse_method"] = v.get("parse_method")
                # MinerU配置
                if v.get("mineru_parse_method"):
                    pdf_parser_config["mineru_parse_method"] = v.get("mineru_parse_method")
                if v.get("mineru_formula_enable") is not None:
                    pdf_parser_config["mineru_formula_enable"] = v.get("mineru_formula_enable")
                if v.get("mineru_table_enable") is not None:
                    pdf_parser_config["mineru_table_enable"] = v.get("mineru_table_enable")
                if v.get("mineru_lang"):
                    pdf_parser_config["mineru_lang"] = v.get("mineru_lang")
                # 文本分块配置
                if v.get("chunk_token_num") is not None:
                    pdf_parser_config["chunk_token_num"] = v.get("chunk_token_num")
                if v.get("delimiter"):
                    pdf_parser_config["delimiter"] = v.get("delimiter")
                if v.get("enable_children") is not None:
                    pdf_parser_config["enable_children"] = v.get("enable_children")
                if v.get("children_delimiter"):
                    pdf_parser_config["children_delimiter"] = v.get("children_delimiter")
            
            # 调用FileService.get_files()处理文件
            v = FileService.get_files([v["value"]], pdf_parser_config)
        
        # 设置输出
        self.set_output(k, v)
        self.set_input_value(k, v)
```

**关键步骤**:
1. 检查输入参数是否为PDF类型
2. 提取所有PDF解析器配置参数（MinerU配置、文本分块配置等）
3. 构建 `pdf_parser_config` 字典
4. 调用 `FileService.get_files()` 处理文件，传递配置

---

## 文件服务处理

### 4.1 FileService.get_files()

**文件路径**: `api/db/services/file_service.py:698-715`

```python
@staticmethod
def get_files(files: Union[None, list[dict]], pdf_parser_config: Union[None, dict] = None) -> list[str]:
    if not files:
        return []
    
    exe = ThreadPoolExecutor(max_workers=5)
    threads = []
    for file in files:
        # 如果是PDF文件且提供了解析器配置，传递配置
        if file["mime_type"].find("pdf") >= 0 and pdf_parser_config:
            threads.append(exe.submit(
                FileService.parse, 
                file["name"], 
                FileService.get_blob(file["created_by"], file["id"]), 
                True, 
                file["created_by"], 
                pdf_parser_config
            ))
        else:
            threads.append(exe.submit(
                FileService.parse, 
                file["name"], 
                FileService.get_blob(file["created_by"], file["id"]), 
                True, 
                file["created_by"]
            ))
    return [th.result() for th in threads]
```

**关键步骤**:
1. 使用线程池并发处理文件（最多5个线程）
2. 从存储中获取文件二进制内容（`FileService.get_blob()`）
3. 如果是PDF文件且提供了解析器配置，调用 `FileService.parse()` 并传递配置
4. 返回解析后的文本内容列表

### 4.2 FileService.parse()

**文件路径**: `api/db/services/file_service.py:514-569`

```python
@staticmethod
def parse(filename, blob, img_base64=True, tenant_id=None, pdf_parser_config=None):
    from rag.app import audio, email, naive, picture, presentation
    from api.apps import current_user
    
    # 构建parser_config，如果提供了PDF解析器配置则使用，否则使用默认值
    parser_config = {
        "chunk_token_num": 16096, 
        "delimiter": "\n!?;。；！？", 
        "layout_recognize": "Plain Text"
    }
    
    # 如果提供了PDF解析器配置，更新parser_config
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
    
    # 确定语言设置
    lang = "English"
    if pdf_parser_config and pdf_parser_config.get("lang"):
        lang = pdf_parser_config["lang"]
    elif pdf_parser_config and pdf_parser_config.get("mineru_lang"):
        lang = pdf_parser_config["mineru_lang"]
    
    # 构建kwargs
    kwargs = {
        "lang": lang, 
        "callback": dummy, 
        "parser_config": parser_config, 
        "from_page": 0, 
        "to_page": 100000, 
        "tenant_id": current_user.id if current_user else tenant_id
    }
    
    # 调用naive.chunk()进行文件分块处理
    cks = naive.chunk(filename, blob, **kwargs)
    
    # 格式化返回结果
    return f"\n -----------------\nFile: {filename}\nContent as following: \n" + "\n".join([ck["content_with_weight"] for ck in cks])
```

**关键步骤**:
1. 构建默认的 `parser_config`
2. 如果提供 `pdf_parser_config`，更新 `parser_config` 中的相关配置
3. 确定语言设置（优先使用 `lang`，其次使用 `mineru_lang`）
4. 构建 `kwargs`，包含语言、回调函数、解析器配置、租户ID等
5. 调用 `naive.chunk()` 进行文件分块处理
6. 格式化返回结果，将分块内容拼接成字符串

---

## MinerU解析器处理

### 5.1 naive.chunk() - PDF处理入口

**文件路径**: `rag/app/naive.py:659-796`

```python
def chunk(filename, binary=None, from_page=0, to_page=100000, lang="Chinese", callback=None, **kwargs):
    parser_config = kwargs.get("parser_config", {
        "chunk_token_num": 512, 
        "delimiter": "\n!?。；！？", 
        "layout_recognize": "DeepDOC"
    })
    
    # 识别PDF文件
    if re.search(r"\.pdf$", filename, re.IGNORECASE):
        # 规范化布局识别器名称
        layout_recognizer, parser_model_name = normalize_layout_recognizer(
            parser_config.get("layout_recognize", "DeepDOC")
        )
        
        # 获取解析器函数（MinerU对应by_mineru）
        name = layout_recognizer.strip().lower()
        parser = PARSERS.get(name, by_plaintext)  # PARSERS["mineru"] = by_mineru
        
        callback(0.1, "Start to parse.")
        
        # 调用解析器函数
        sections, tables, pdf_parser = parser(
            filename=filename,
            binary=binary,
            from_page=from_page,
            to_page=to_page,
            lang=lang,
            callback=callback,
            layout_recognizer=layout_recognizer,
            mineru_llm_name=parser_model_name,
            **kwargs
        )
        
        # 处理表格上下文
        if table_context_size or image_context_size:
            tables = append_context2table_image4pdf(sections, tables, image_context_size)
        
        # 对于MinerU，设置chunk_token_num为0（不进行额外分块）
        if name in ["tcadp", "docling", "mineru"]:
            parser_config["chunk_token_num"] = 0
        
        # 对表格进行tokenize处理
        res = tokenize_table(tables, doc, is_english)
        callback(0.8, "Finish parsing.")
```

**关键步骤**:
1. 识别文件类型为PDF
2. 从 `parser_config` 中获取 `layout_recognize`（此时为 "MinerU"）
3. 从 `PARSERS` 字典中获取对应的解析器函数 `by_mineru`
4. 调用 `by_mineru()` 进行PDF解析
5. 处理解析结果（sections和tables）
6. 对于MinerU，设置 `chunk_token_num` 为0（因为MinerU已经进行了分块）
7. 对表格进行tokenize处理

### 5.2 by_mineru() - MinerU解析入口

**文件路径**: `rag/app/naive.py:67-113`

```python
def by_mineru(
    filename,
    binary=None,
    from_page=0,
    to_page=100000,
    lang="Chinese",
    callback=None,
    pdf_cls=None,
    parse_method: str = "raw",
    mineru_llm_name: str | None = None,
    tenant_id: str | None = None,
    **kwargs,
):
    pdf_parser = None
    if tenant_id:
        # 如果没有指定mineru_llm_name，尝试从环境或数据库获取
        if not mineru_llm_name:
            try:
                from api.db.services.tenant_llm_service import TenantLLMService
                
                env_name = TenantLLMService.ensure_mineru_from_env(tenant_id)
                candidates = TenantLLMService.query(
                    tenant_id=tenant_id, 
                    llm_factory="MinerU", 
                    model_type=LLMType.OCR
                )
                if candidates:
                    mineru_llm_name = candidates[0].llm_name
                elif env_name:
                    mineru_llm_name = env_name
            except Exception as e:
                logging.warning(f"fallback to env mineru: {e}")
        
        # 创建MinerU解析器实例
        if mineru_llm_name:
            try:
                ocr_model = LLMBundle(
                    tenant_id=tenant_id, 
                    llm_type=LLMType.OCR, 
                    llm_name=mineru_llm_name, 
                    lang=lang
                )
                pdf_parser = ocr_model.mdl
                
                # 调用MinerU解析器的parse_pdf方法
                sections, tables = pdf_parser.parse_pdf(
                    filepath=filename,
                    binary=binary,
                    callback=callback,
                    parse_method=parse_method,
                    lang=lang,
                    **kwargs
                )
                return sections, tables, pdf_parser
            except Exception as e:
                logging.error(f"Failed to parse pdf via LLMBundle MinerU ({mineru_llm_name}): {e}")
    
    if callback:
        callback(-1, "MinerU not found.")
    return None, None, None
```

**关键步骤**:
1. 检查是否有 `tenant_id`
2. 如果没有指定 `mineru_llm_name`，尝试从环境变量或数据库获取
3. 创建 `LLMBundle` 实例，获取MinerU解析器模型
4. 调用 `pdf_parser.parse_pdf()` 进行PDF解析
5. 返回解析结果（sections和tables）

### 5.3 MinerUParser.parse_pdf() - MinerU核心解析

**文件路径**: `deepdoc/parser/mineru_parser.py:543-635`

```python
def parse_pdf(
    self,
    filepath: str | PathLike[str],
    binary: BytesIO | bytes,
    callback: Optional[Callable] = None,
    *,
    output_dir: Optional[str] = None,
    backend: str = "pipeline",
    server_url: Optional[str] = None,
    delete_output: bool = True,
    parse_method: str = "raw",
    **kwargs,
) -> tuple:
    # 从kwargs中获取parser_config
    parser_cfg = kwargs.get('parser_config', {})
    lang = parser_cfg.get('mineru_lang') or kwargs.get('lang', 'English')
    mineru_lang_code = LANGUAGE_TO_MINERU_MAP.get(lang, 'ch')  # 映射到MinerU语言代码
    mineru_method_raw_str = parser_cfg.get('mineru_parse_method', 'auto')
    enable_formula = parser_cfg.get('mineru_formula_enable', True)
    enable_table = parser_cfg.get('mineru_table_enable', True)
    
    # 处理文件路径（移除空格，避免MinerU崩溃）
    file_path = Path(filepath)
    pdf_file_name = file_path.stem.replace(" ", "") + ".pdf"
    pdf_file_path_valid = os.path.join(file_path.parent, pdf_file_name)
    
    # 如果是二进制数据，创建临时文件
    if binary:
        temp_dir = Path(tempfile.mkdtemp(prefix="mineru_bin_pdf_"))
        temp_pdf = temp_dir / pdf_file_name
        with open(temp_pdf, "wb") as f:
            f.write(binary)
        pdf = temp_pdf
    else:
        # 处理文件路径
        if pdf_file_path_valid != filepath:
            shutil.move(filepath, pdf_file_path_valid)
        pdf = Path(pdf_file_path_valid)
    
    # 创建输出目录
    if output_dir:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
    else:
        out_dir = Path(tempfile.mkdtemp(prefix="mineru_pdf_"))
        created_tmp_dir = True
    
    # 提取PDF中的图片
    self.__images__(pdf, zoomin=1)
    
    try:
        # 构建MinerU解析选项
        options = MinerUParseOptions(
            backend=MinerUBackend(backend),
            lang=MinerULanguage(mineru_lang_code),
            method=MinerUParseMethod(mineru_method_raw_str),
            server_url=server_url,
            delete_output=delete_output,
            parse_method=parse_method,
            formula_enable=enable_formula,
            table_enable=enable_table,
        )
        
        # 运行MinerU解析
        final_out_dir = self._run_mineru(pdf, out_dir, options, callback=callback)
        
        # 读取解析输出
        outputs = self._read_output(final_out_dir, pdf.stem, method=mineru_method_raw_str, backend=backend)
        
        # 转换为sections和tables格式
        return self._transfer_to_sections(outputs, parse_method), self._transfer_to_tables(outputs)
    finally:
        # 清理临时文件
        if temp_pdf and temp_pdf.exists():
            temp_pdf.unlink()
            temp_pdf.parent.rmdir()
        if delete_output and created_tmp_dir and out_dir.exists():
            shutil.rmtree(out_dir)
```

**关键步骤**:
1. 从 `parser_config` 中提取MinerU配置参数：
   - `mineru_lang` → 映射到MinerU语言代码
   - `mineru_parse_method` → 解析方法（auto/txt/ocr）
   - `mineru_formula_enable` → 是否启用公式识别
   - `mineru_table_enable` → 是否启用表格识别
2. 处理PDF文件路径（移除空格，创建临时文件等）
3. 创建输出目录
4. 提取PDF中的图片
5. 构建 `MinerUParseOptions` 对象
6. 调用 `_run_mineru()` 执行MinerU解析
7. 调用 `_read_output()` 读取解析结果
8. 调用 `_transfer_to_sections()` 和 `_transfer_to_tables()` 转换结果格式
9. 清理临时文件

**返回结果**:
- `sections`: 列表，每个元素为 `(section_text, bbox)` 元组
- `tables`: 列表，包含表格数据

---

## 文本分块处理

### 6.1 tokenize_table() - 表格处理

**文件路径**: `rag/app/naive.py:795-796`

对于MinerU解析器，由于已经进行了分块处理，`chunk_token_num` 被设置为0，因此不会对sections进行额外的分块。主要处理表格数据：

```python
# 对于MinerU，设置chunk_token_num为0
if name in ["tcadp", "docling", "mineru"]:
    parser_config["chunk_token_num"] = 0

# 对表格进行tokenize处理
res = tokenize_table(tables, doc, is_english)
```

### 6.2 构建最终分块结果

**文件路径**: `rag/app/naive.py:934-1036`

```python
# 处理sections（对于MinerU，chunk_token_num=0，不进行合并）
if sections:
    # 如果chunk_token_num为0，每个section作为一个独立的chunk
    if parser_config.get("chunk_token_num", 0) == 0:
        for section_text, bbox in sections:
            chunk = {
                "content_with_weight": section_text,
                "content": section_text,
                "bbox": bbox,
                "weight": 1.0,
                # ... 其他字段
            }
            res.append(chunk)
    else:
        # 否则按照chunk_token_num和delimiter进行分块合并
        # ...
```

**关键步骤**:
1. 对于MinerU，`chunk_token_num` 为0，每个section作为一个独立的chunk
2. 处理表格数据，生成表格chunk
3. 构建最终的分块结果列表，每个chunk包含：
   - `content_with_weight`: 带权重的文本内容
   - `content`: 原始文本内容
   - `bbox`: 边界框信息（如果有）
   - `weight`: 权重值
   - 其他元数据

---

## 结果返回与传递

### 7.1 FileService.parse() 格式化结果

**文件路径**: `api/db/services/file_service.py:568-569`

```python
cks = naive.chunk(filename, blob, **kwargs)
return f"\n -----------------\nFile: {filename}\nContent as following: \n" + "\n".join([ck["content_with_weight"] for ck in cks])
```

将分块结果格式化为字符串，格式为：
```
 -----------------
File: filename.pdf
Content as following: 
[chunk1 content]
[chunk2 content]
...
```

### 7.2 Begin节点设置输出

**文件路径**: `agent/component/begin.py:87-88`

```python
self.set_output(k, v)
self.set_input_value(k, v)
```

- `set_output(k, v)`: 将解析后的文本内容设置为节点的输出变量
- `set_input_value(k, v)`: 保存输入值，供后续节点使用

### 7.3 输出传递给下一个节点

**文件路径**: `agent/canvas.py:235-253`

工作流引擎会根据节点之间的连接关系，将Begin节点的输出传递给下一个节点（如Message节点、LLM节点等）。

下一个节点可以通过变量引用访问Begin节点的输出：
- 变量引用格式：`{Begin@variable_key}`
- 例如：`{Begin@pdf_file}`

---

## 前端接收与显示

### 8.1 Message节点使用输出

**文件路径**: `agent/component/message.py:109-170`

如果工作流中包含Message节点，它会从Begin节点的输出中获取文件内容：

```python
async def _stream(self, rand_cnt:str):
    # 解析变量引用，如 {Begin@pdf_file}
    for r in re.finditer(self.variable_ref_patt, rand_cnt, flags=re.DOTALL):
        exp = r.group(1)  # 例如: "Begin@pdf_file"
        # 从工作流上下文中获取变量值
        v = self._canvas.get_variable_value(exp)
        # 将变量值插入到消息内容中
        yield v
    
    # 设置最终输出
    self.set_output("content", all_content)
```

### 8.2 前端SSE接收

**文件路径**: `web/src/pages/agent/chat/use-send-agent-message.ts`

前端通过SSE（Server-Sent Events）实时接收工作流执行结果：

1. **接收流式输出**: 如果Message节点使用流式输出，前端会实时接收并显示
2. **接收最终结果**: 工作流执行完成后，接收最终的输出结果
3. **更新UI**: 将结果显示在聊天界面中

### 8.3 显示格式

前端显示的文件解析结果格式：
```
 -----------------
File: example.pdf
Content as following: 
[第一个文本块内容]
[第二个文本块内容]
[表格内容]
...
```

---

## 流程图

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端用户操作                              │
│  1. 配置Begin节点：选择PDF类型，选择MinerU解析器                │
│  2. 配置MinerU选项：解析方法、语言、公式识别、表格识别           │
│  3. 配置文本分块选项：chunk_token_num、delimiter等             │
│  4. 上传PDF文件                                                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      前端请求发送                                │
│  构建请求数据：inputs包含文件ID和所有配置参数                   │
│  通过SSE/HTTP发送到后端工作流执行接口                           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   后端Begin节点处理                              │
│  Begin._invoke()                                                │
│  1. 提取PDF配置参数                                             │
│  2. 构建pdf_parser_config字典                                   │
│  3. 调用FileService.get_files()                                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     文件服务处理                                │
│  FileService.get_files()                                        │
│  1. 从存储获取文件二进制内容                                    │
│  2. 调用FileService.parse()，传递pdf_parser_config             │
│                                                                 │
│  FileService.parse()                                            │
│  1. 构建parser_config，更新MinerU配置                          │
│  2. 确定语言设置                                                │
│  3. 调用naive.chunk()                                           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   MinerU解析器处理                              │
│  naive.chunk()                                                  │
│  1. 识别PDF文件                                                 │
│  2. 获取by_mineru解析器函数                                     │
│  3. 调用by_mineru()                                             │
│                                                                 │
│  by_mineru()                                                    │
│  1. 获取MinerU模型实例                                          │
│  2. 调用pdf_parser.parse_pdf()                                 │
│                                                                 │
│  MinerUParser.parse_pdf()                                      │
│  1. 提取配置参数（语言、解析方法、公式/表格识别）               │
│  2. 处理PDF文件（创建临时文件等）                               │
│  3. 运行MinerU解析                                              │
│  4. 读取解析结果                                                │
│  5. 转换为sections和tables格式                                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     文本分块处理                                 │
│  naive.chunk() 继续处理                                         │
│  1. 对于MinerU，设置chunk_token_num=0                           │
│  2. 每个section作为一个独立的chunk                             │
│  3. 处理表格数据                                                │
│  4. 构建最终分块结果列表                                        │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     结果返回与传递                               │
│  FileService.parse()                                            │
│  1. 格式化分块结果为字符串                                      │
│  2. 返回格式化的文本内容                                        │
│                                                                 │
│  Begin节点                                                      │
│  1. set_output() 设置输出变量                                   │
│  2. 输出传递给下一个节点                                        │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     前端接收与显示                               │
│  Message节点（如果存在）                                        │
│  1. 从Begin节点输出获取文件内容                                 │
│  2. 插入到消息模板中                                            │
│  3. 流式输出或最终输出                                          │
│                                                                 │
│  前端SSE接收                                                    │
│  1. 实时接收流式输出                                            │
│  2. 接收最终结果                                                │
│  3. 更新UI显示                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 关键代码路径

### 前端代码路径

1. **变量配置UI**: `web/src/pages/agent/form/begin-form/parameter-dialog.tsx`
   - MinerU配置选项UI
   - 文本分块配置UI

2. **请求发送**: `web/src/pages/agent/chat/use-send-agent-message.ts`
   - 构建工作流执行请求
   - SSE连接管理

3. **结果接收**: `web/src/pages/agent/chat/use-send-agent-message.ts`
   - SSE事件处理
   - UI更新

### 后端代码路径

1. **Begin节点**: `agent/component/begin.py`
   - `Begin._invoke()`: 处理输入，提取配置，调用文件服务

2. **文件服务**: `api/db/services/file_service.py`
   - `FileService.get_files()`: 获取文件并调用解析
   - `FileService.parse()`: 解析文件，调用分块处理

3. **分块处理**: `rag/app/naive.py`
   - `chunk()`: PDF文件分块入口
   - `by_mineru()`: MinerU解析器调用入口

4. **MinerU解析器**: `deepdoc/parser/mineru_parser.py`
   - `MinerUParser.parse_pdf()`: MinerU核心解析逻辑

5. **节点输出**: `agent/component/base.py`
   - `ComponentBase.set_output()`: 设置节点输出
   - `ComponentBase.output()`: 获取节点输出

6. **工作流引擎**: `agent/canvas.py`
   - 节点执行调度
   - 变量传递

---

## 配置参数说明

### MinerU配置参数

| 参数名 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| `parse_method` | string | PDF解析方法 | "MinerU" |
| `mineru_parse_method` | enum | MinerU解析方法：auto/txt/ocr | "auto" |
| `mineru_lang` | string | MinerU语言设置 | "Chinese" |
| `mineru_formula_enable` | boolean | 是否启用公式识别 | true |
| `mineru_table_enable` | boolean | 是否启用表格识别 | true |

### 文本分块配置参数

| 参数名 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| `chunk_token_num` | number | 建议文本块大小（对于MinerU会被设置为0） | 512 |
| `delimiter` | string | 文本分段标识符 | "\n" |
| `enable_children` | boolean | 是否启用子块检索 | false |
| `children_delimiter` | string | 子块分隔符 | "\n" |

---

## 注意事项

1. **MinerU模型要求**: 
   - 需要正确配置MinerU模型（通过环境变量或数据库配置）
   - 如果MinerU模型不可用，解析会失败

2. **文件路径处理**: 
   - MinerU要求PDF文件名不能包含空格
   - 系统会自动处理文件名，移除空格

3. **临时文件清理**: 
   - MinerU解析过程中会创建临时文件
   - 解析完成后会自动清理临时文件

4. **分块策略**: 
   - 对于MinerU，`chunk_token_num` 会被设置为0
   - 每个MinerU解析的section作为一个独立的chunk
   - 不会进行额外的文本合并

5. **并发处理**: 
   - `FileService.get_files()` 使用线程池并发处理多个文件
   - 最多5个并发线程

6. **错误处理**: 
   - 如果MinerU解析失败，会返回错误信息
   - 错误信息会通过callback传递给前端

---

## 总结

本文档详细描述了工作流开始节点在任务模式下上传PDF文件并选择MinerU解析器后的完整工作流程。整个流程包括：

1. **前端配置**: 用户在前端配置Begin节点，选择PDF类型和MinerU解析器，设置相关参数
2. **文件上传**: PDF文件上传到服务器，返回文件元数据
3. **后端处理**: Begin节点提取配置，调用文件服务处理文件
4. **MinerU解析**: 使用MinerU解析器解析PDF，提取文本和表格
5. **文本分块**: 将解析结果分块处理，构建最终的分块列表
6. **结果返回**: 格式化结果并返回给Begin节点
7. **数据传递**: Begin节点设置输出，传递给下一个节点
8. **前端显示**: 前端接收结果并显示在UI中

整个流程确保了PDF文件能够被正确解析，解析结果能够正确传递给后续节点，最终在前端正确显示。
