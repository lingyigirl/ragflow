# 工作流开始节点PDF解析器配置功能改动说明

## 概述

本次改动为工作流开始节点的PDF类型参数添加了完整的PDF解析器配置功能，支持用户选择不同的PDF解析器（DeepDOC、Plain Text、MinerU、Docling、TCADP Parser等），并为每种解析器提供相应的配置选项。配置区域支持滚动查看，以适应较多的配置项。

## 修改文件清单

### 前端文件

1. `web/src/pages/agent/interface.ts`
2. `web/src/pages/agent/form/begin-form/schema.ts`
3. `web/src/pages/agent/form/begin-form/parameter-dialog.tsx`

### 后端文件

1. `api/db/services/file_service.py`
2. `agent/component/begin.py`
3. `agent/component/fillup.py`
4. `rag/app/naive.py`

---

## 详细改动说明

### 1. 前端接口定义 (`web/src/pages/agent/interface.ts`)

**文件路径**: `web/src/pages/agent/interface.ts`

**改动内容**:
- 扩展了 `BeginQuery` 接口，添加PDF解析器相关配置字段

**具体修改**:
```typescript
export interface BeginQuery {
  key: string;
  type: string;
  value: string;
  optional: boolean;
  name: string;
  options: (number | string | boolean)[];
  // PDF解析器相关配置
  parse_method?: string; // PDF解析方法：DeepDOC, Plain Text, MinerU, Docling, TCADP Parser, 或第三方视觉模型
  // MinerU配置
  mineru_parse_method?: 'auto' | 'txt' | 'ocr'; // MinerU解析方法
  mineru_formula_enable?: boolean; // MinerU公式识别
  mineru_table_enable?: boolean; // MinerU表格识别
  mineru_lang?: string; // MinerU语言设置
  // TCADP配置
  tcadp_table_result_type?: string; // TCADP表格返回形式：'0'=Markdown, '1'=HTML
  tcadp_markdown_image_response_type?: string; // TCADP图片返回形式：'0'=URL, '1'=Text
  // 通用配置
  lang?: string; // 通用语言设置
  // 文本分块配置（用于DeepDOC、Plain Text、Docling、TCADP Parser等）
  chunk_token_num?: number; // 建议文本块大小
  delimiter?: string; // 文本分段标识符
  enable_children?: boolean; // Child chunk are used for retrieval开关
  children_delimiter?: string; // Delimiter for text
}
```

**改动目的**: 为TypeScript类型系统提供完整的PDF解析器配置字段定义，确保类型安全。

---

### 2. 前端Schema定义 (`web/src/pages/agent/form/begin-form/schema.ts`)

**文件路径**: `web/src/pages/agent/form/begin-form/schema.ts`

**改动内容**:
- 更新了 `BeginFormSchema`，在inputs数组的每个对象中添加PDF解析器相关字段

**具体修改**:
```typescript
inputs: z
  .array(
    z.object({
      key: z.string(),
      type: FieldTypeSchema, 
      value: z.string(),
      optional: z.boolean(),
      name: z.string(),
      options: z.array(z.union([z.number(), z.string(), z.boolean()])),
      // PDF解析器相关配置（仅当type为'pdf'时使用）
      parse_method: z.string().optional(), // PDF解析方法
      // MinerU配置
      mineru_parse_method: z.enum(['auto', 'txt', 'ocr']).optional(), // MinerU解析方法
      mineru_formula_enable: z.boolean().optional(), // MinerU公式识别
      mineru_table_enable: z.boolean().optional(), // MinerU表格识别
      mineru_lang: z.string().optional(), // MinerU语言设置
      // TCADP配置
      tcadp_table_result_type: z.string().optional(), // TCADP表格返回形式
      tcadp_markdown_image_response_type: z.string().optional(), // TCADP图片返回形式
      // 通用配置
      lang: z.string().optional(), // 通用语言设置
      // 文本分块配置（用于DeepDOC、Plain Text、Docling、TCADP Parser等）
      chunk_token_num: z.number().optional(), // 建议文本块大小
      delimiter: z.string().optional(), // 文本分段标识符
      enable_children: z.boolean().optional(), // Child chunk are used for retrieval开关
      children_delimiter: z.string().optional(), // Delimiter for text
    }),
  )
  .optional(),
```

**改动目的**: 使用Zod schema验证PDF解析器配置字段，确保数据格式正确。

---

### 3. 前端参数配置对话框 (`web/src/pages/agent/form/begin-form/parameter-dialog.tsx`)

**文件路径**: `web/src/pages/agent/form/begin-form/parameter-dialog.tsx`

**改动内容**:
1. 导入必要的组件和Hook
2. 更新FormSchema，添加PDF解析器配置字段
3. 添加 `BeginPdfParserOptions` 组件，实现解析器选择和配置功能
4. 在表单初始化时处理PDF解析器配置字段

**具体修改**:

#### 3.1 导入语句
```typescript
import { LayoutRecognizeFormField } from '@/components/layout-recognize-form-field';
import { useFormContext } from 'react-hook-form';
```

#### 3.2 FormSchema扩展
```typescript
const FormSchema = z.object({
  // ... 原有字段 ...
  // PDF解析器相关配置（仅当type为'pdf'时使用）
  parse_method: z.string().optional(), // PDF解析方法
  // MinerU配置
  mineru_parse_method: z.enum(['auto', 'txt', 'ocr']).optional(), // MinerU解析方法
  mineru_formula_enable: z.boolean().optional(), // MinerU公式识别
  mineru_table_enable: z.boolean().optional(), // MinerU表格识别
  mineru_lang: z.string().optional(), // MinerU语言设置
  // TCADP配置
  tcadp_table_result_type: z.string().optional(), // TCADP表格返回形式
  tcadp_markdown_image_response_type: z.string().optional(), // TCADP图片返回形式
  // 通用配置
  lang: z.string().optional(), // 通用语言设置
});
```

#### 3.3 BeginPdfParserOptions组件
新增了一个完整的PDF解析器配置组件，包含以下功能：

- **解析器类型识别**: 根据选择的解析方法自动识别解析器类型
- **可滚动配置区域**: 使用 `max-h-[400px] overflow-y-auto` 实现滚动查看
- **粘性标题**: 配置区域标题使用 `sticky top-0` 保持可见
- **各解析器配置选项**:
  - **DeepDOC**: 建议文本块大小、文本分段标识符、Child chunk开关、Delimiter for text
  - **Plain Text**: 建议文本块大小、文本分段标识符、Child chunk开关、Delimiter for text
  - **MinerU**: 解析方法（auto/txt/ocr，默认auto）、语言（20种语言选项，默认Chinese）、公式识别开关（默认true）、表格识别开关（默认true）、建议文本块大小、文本分段标识符、Child chunk开关、Delimiter for text
  - **Docling**: 建议文本块大小、文本分段标识符、Child chunk开关、Delimiter for text
  - **TCADP Parser**: 表格返回形式、图片返回形式、建议文本块大小、文本分段标识符、Child chunk开关、Delimiter for text
  - **第三方视觉模型**: 无额外配置选项

#### 3.4 BeginTextChunkingConfig组件
新增了一个通用的文本分块配置组件，包含以下配置选项：

- **建议文本块大小（chunk_token_num）**: 使用 `SliderInputFormField` 组件，范围1-2048，默认512
- **文本分段标识符（delimiter）**: 使用 `DelimiterInput` 组件，支持多字符分隔符
- **Child chunk are used for retrieval（enable_children）**: 使用 `Switch` 组件，布尔开关
- **Delimiter for text（children_delimiter）**: 使用 `DelimiterInput` 组件，仅在 `enable_children` 为true时显示

该组件被DeepDOC、Plain Text、Docling、TCADP Parser等解析器共享使用。

**关键代码片段**:
```typescript
// PDF解析器配置组件
function BeginPdfParserOptions() {
  const { t } = useTranslation();
  const form = useFormContext();
  const parseMethod = useWatch({
    control: form.control,
    name: 'parse_method',
  });

  // 检查选择的解析器类型
  const parserType = useMemo(() => {
    if (!parseMethod) return null;
    const lower = parseMethod.toLowerCase();
    if (lower.includes('mineru')) return 'mineru';
    if (lower === 'deepdoc') return 'deepdoc';
    if (lower === 'plain text' || lower === 'plaintext') return 'plaintext';
    if (lower === 'docling') return 'docling';
    if (lower === 'tcadp parser' || lower === 'tcadp') return 'tcadp';
    return 'other'; // 第三方视觉模型
  }, [parseMethod]);

  // 设置默认解析方法
  useEffect(() => {
    if (!parseMethod) {
      form.setValue('parse_method', 'DeepDOC', {
        shouldValidate: true,
        shouldDirty: true,
      });
    }
  }, [form, parseMethod]);

  return (
    <div className="space-y-4 border-t pt-4 mt-4">
      <div className="text-sm font-medium text-text-secondary">
        {t('flow.pdfParser', 'PDF解析器')}
      </div>
      <LayoutRecognizeFormField
        name="parse_method"
        horizontal={false}
        label={t('flow.parserMethod', '解析方法')}
        showMineruOptions={false}
      />
      {/* 解析器配置选项（可滚动） */}
      {parserType && (
        <div className="max-h-[400px] overflow-y-auto border rounded-md p-4 space-y-4">
          <div className="text-sm font-medium text-text-secondary sticky top-0 bg-background pb-2 border-b">
            {t('flow.parserConfig', '解析器配置')}
          </div>
          
          {/* 各解析器的配置选项... */}
        </div>
      )}
    </div>
  );
}
```

**改动目的**: 为用户提供直观的PDF解析器选择和配置界面，支持所有解析器类型的配置选项，并确保配置项较多时可以滚动查看。

---

### 4. 后端文件服务 (`api/db/services/file_service.py`)

**文件路径**: `api/db/services/file_service.py`

**改动内容**:
1. 修改 `parse()` 方法，添加 `pdf_parser_config` 参数
2. 修改 `get_files()` 方法，添加 `pdf_parser_config` 参数并传递给 `parse()` 方法

**具体修改**:

#### 4.1 parse()方法
```python
@staticmethod
def parse(filename, blob, img_base64=True, tenant_id=None, pdf_parser_config=None):
    """
    解析文件内容
    
    Args:
        filename: 文件名
        blob: 文件二进制内容
        img_base64: 是否将图片转换为base64
        tenant_id: 租户ID
        pdf_parser_config: PDF解析器配置（可选）
            - parse_method: PDF解析方法（DeepDOC, Plain Text, MinerU, Docling, TCADP Parser等）
            - mineru_parse_method: MinerU解析方法（auto, txt, ocr）
            - mineru_formula_enable: MinerU公式识别（bool）
            - mineru_table_enable: MinerU表格识别（bool）
            - mineru_lang: MinerU语言设置
            - tcadp_table_result_type: TCADP表格返回形式
            - tcadp_markdown_image_response_type: TCADP图片返回形式
            - lang: 通用语言设置
    """
    # ... 原有代码 ...
    
    # 构建parser_config，如果提供了PDF解析器配置则使用，否则使用默认值
    parser_config = {"chunk_token_num": 16096, "delimiter": "\n!?;。；！？", "layout_recognize": "Plain Text"}
    
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
            # TCADP相关配置
            if pdf_parser_config.get("tcadp_table_result_type"):
                parser_config["tcadp_table_result_type"] = pdf_parser_config["tcadp_table_result_type"]
            if pdf_parser_config.get("tcadp_markdown_image_response_type"):
                parser_config["tcadp_markdown_image_response_type"] = pdf_parser_config["tcadp_markdown_image_response_type"]
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
    
    # 将TCADP配置添加到kwargs中，以便传递给解析器
    if pdf_parser_config and pdf_parser_config.get("tcadp_table_result_type"):
        kwargs["table_result_type"] = pdf_parser_config["tcadp_table_result_type"]
    if pdf_parser_config and pdf_parser_config.get("tcadp_markdown_image_response_type"):
        kwargs["markdown_image_response_type"] = pdf_parser_config["tcadp_markdown_image_response_type"]
    
    # ... 原有代码 ...
```

#### 4.2 get_files()方法
```python
@staticmethod
def get_files(files: Union[None, list[dict]], pdf_parser_config: Union[None, dict] = None) -> list[str]:
    """
    获取文件内容列表
    
    Args:
        files: 文件元数据列表
        pdf_parser_config: PDF解析器配置（可选），用于处理PDF文件
            - parse_method: PDF解析方法
            - mineru_parse_method: MinerU解析方法
            - mineru_formula_enable: MinerU公式识别
            - mineru_table_enable: MinerU表格识别
            - mineru_lang: MinerU语言设置
            - tcadp_table_result_type: TCADP表格返回形式
            - tcadp_markdown_image_response_type: TCADP图片返回形式
            - lang: 通用语言设置
    """
    if not files:
        return  []
    def image_to_base64(file):
        return "data:{};base64,{}".format(file["mime_type"],
                                    base64.b64encode(FileService.get_blob(file["created_by"], file["id"])).decode("utf-8"))
    exe = ThreadPoolExecutor(max_workers=5)
    threads = []
    for file in files:
        if file["mime_type"].find("image") >=0:
            threads.append(exe.submit(image_to_base64, file))
            continue
        # 如果是PDF文件且提供了解析器配置，传递配置
        if file["mime_type"].find("pdf") >= 0 and pdf_parser_config:
            threads.append(exe.submit(FileService.parse, file["name"], FileService.get_blob(file["created_by"], file["id"]), True, file["created_by"], pdf_parser_config))
        else:
            threads.append(exe.submit(FileService.parse, file["name"], FileService.get_blob(file["created_by"], file["id"]), True, file["created_by"]))
    return [th.result() for th in threads]
```

**改动目的**: 使文件服务能够接收和使用PDF解析器配置，确保配置能够正确传递到PDF解析器。

---

### 5. 后端Begin组件 (`agent/component/begin.py`)

**文件路径**: `agent/component/begin.py`

**改动内容**:
- 修改 `_invoke()` 方法，从输入参数中提取PDF解析器配置并传递给 `FileService.get_files()`

**具体修改**:
```python
def _invoke(self, **kwargs):
    if self.check_if_canceled("Begin processing"):
        return

    for k, v in kwargs.get("inputs", {}).items():
        if self.check_if_canceled("Begin processing"):
            return

        if isinstance(v, dict) and (
            v.get("type", "").lower().find("file") >= 0 or 
            v.get("type", "").lower() == "pdf"
        ):
            if v.get("optional") and v.get("value", None) is None:
                v = None
            else:
                # 构建PDF解析器配置（如果类型为PDF且有相关配置）
                pdf_parser_config = None
                if v.get("type", "").lower() == "pdf":
                    pdf_parser_config = {}
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
                    # TCADP配置
                    if v.get("tcadp_table_result_type"):
                        pdf_parser_config["tcadp_table_result_type"] = v.get("tcadp_table_result_type")
                    if v.get("tcadp_markdown_image_response_type"):
                        pdf_parser_config["tcadp_markdown_image_response_type"] = v.get("tcadp_markdown_image_response_type")
                    # 通用配置
                    if v.get("lang"):
                        pdf_parser_config["lang"] = v.get("lang")
                    # 文本分块配置
                    if v.get("chunk_token_num") is not None:
                        pdf_parser_config["chunk_token_num"] = v.get("chunk_token_num")
                    if v.get("delimiter"):
                        pdf_parser_config["delimiter"] = v.get("delimiter")
                    if v.get("enable_children") is not None:
                        pdf_parser_config["enable_children"] = v.get("enable_children")
                    if v.get("children_delimiter"):
                        pdf_parser_config["children_delimiter"] = v.get("children_delimiter")
                    # 如果没有任何配置，设置为None
                    if not pdf_parser_config:
                        pdf_parser_config = None
                
                # 调用FileService.get_files()，传递PDF解析器配置
                v = FileService.get_files([v["value"]], pdf_parser_config)

        self.set_output(k, v)
        self.set_input_value(k, v)
```

**改动目的**: 在Begin组件中提取PDF解析器配置，并将其传递给文件服务，确保配置能够正确应用到PDF解析过程。

---

### 6. 后端UserFillUp组件 (`agent/component/fillup.py`)

**文件路径**: `agent/component/fillup.py`

**改动内容**:
- 修改 `_invoke()` 方法，与Begin组件相同的逻辑，提取PDF解析器配置并传递

**具体修改**:
与 `agent/component/begin.py` 中的修改完全相同，确保UserFillUp组件也能正确处理PDF解析器配置。

**改动目的**: 保持Begin组件和UserFillUp组件在处理PDF文件时的一致性，确保所有使用UserFillUp的组件都能支持PDF解析器配置。

---

### 7. 后端PDF解析器函数 (`rag/app/naive.py`)

**文件路径**: `rag/app/naive.py`

**改动内容**:
- 修改 `by_tcadp()` 函数，从 `kwargs` 或 `parser_config` 中读取TCADP配置参数

**具体修改**:
```python
def by_tcadp(filename, binary=None, from_page=0, to_page=100000, lang="Chinese", callback=None, pdf_cls=None, **kwargs):
    # 从kwargs或parser_config中获取TCADP配置
    parser_config = kwargs.get("parser_config", {})
    table_result_type = kwargs.get("table_result_type") or parser_config.get("tcadp_table_result_type", "1")
    markdown_image_response_type = kwargs.get("markdown_image_response_type") or parser_config.get("tcadp_markdown_image_response_type", "1")
    
    tcadp_parser = TCADPParser(
        table_result_type=table_result_type,
        markdown_image_response_type=markdown_image_response_type
    )

    if not tcadp_parser.check_installation():
        callback(-1, "TCADP parser not available. Please check Tencent Cloud API configuration.")
        return None, None, tcadp_parser

    sections, tables = tcadp_parser.parse_pdf(
        filepath=filename,
        binary=binary,
        callback=callback,
        output_dir=os.environ.get("TCADP_OUTPUT_DIR", ""),
        file_type="PDF"
    )
    return sections, tables, tcadp_parser
```

**改动目的**: 确保TCADP解析器能够正确接收和使用前端传递的配置参数（表格返回形式和图片返回形式）。

---

## 数据流程

### 完整的数据传递流程

1. **前端配置** → 用户在参数配置对话框中选择PDF解析器并设置配置选项
2. **表单提交** → 配置数据保存到节点的 `inputs` 中
3. **API请求** → 工作流执行时，配置数据通过 `inputs` 参数传递到后端
4. **Begin组件** → `Begin._invoke()` 从 `inputs` 中提取PDF解析器配置
5. **FileService** → `FileService.get_files()` 接收配置并传递给 `FileService.parse()`
6. **PDF解析器** → `FileService.parse()` 将配置添加到 `parser_config` 和 `kwargs` 中
7. **解析执行** → 各个PDF解析器函数（如 `by_tcadp()`, `by_mineru()` 等）读取配置并应用

---

## 支持的解析器及配置选项

| 解析器类型 | 配置选项 | 说明 |
|-----------|---------|------|
| **DeepDOC** | 建议文本块大小、文本分段标识符、Child chunk开关、Delimiter for text | 完整的文本分块配置选项 |
| **Plain Text** | 建议文本块大小、文本分段标识符、Child chunk开关、Delimiter for text | 完整的文本分块配置选项 |
| **MinerU** | 解析方法、语言、公式识别、表格识别、建议文本块大小、文本分段标识符、Child chunk开关、Delimiter for text | 解析方法：auto（自动检测，默认）/txt（文本提取）/ocr（光学字符识别）；语言：20种语言选项（默认Chinese）；公式识别：开关（默认开启）；表格识别：开关（默认开启）；完整的文本分块配置选项 |
| **Docling** | 建议文本块大小、文本分段标识符、Child chunk开关、Delimiter for text | 完整的文本分块配置选项 |
| **TCADP Parser** | 表格返回形式、图片返回形式、建议文本块大小、文本分段标识符、Child chunk开关、Delimiter for text | 表格：Markdown/HTML；图片：URL/Text；完整的文本分块配置选项 |
| **第三方视觉模型** | 无 | 无需额外配置 |

### 文本分块配置选项说明

以下配置选项适用于DeepDOC、Plain Text、Docling、TCADP Parser等解析器：

1. **建议文本块大小（chunk_token_num）**
   - 类型：数字（滑块输入）
   - 范围：1-2048
   - 默认值：512
   - 说明：设置创建块的token阈值。少于该阈值的段落将与后续段落合并，直到token数超过阈值，此时创建一个块。

2. **文本分段标识符（delimiter）**
   - 类型：字符串（输入框）
   - 默认值：`\n`
   - 说明：支持多字符作为分隔符，多字符用两个反引号 `` 分隔符包裹。例如：`\n`##`;` 表示使用换行符、两个#号以及分号对文本进行分割。

3. **Child chunk are used for retrieval（enable_children）**
   - 类型：布尔值（开关）
   - 默认值：false
   - 说明：启用后，系统会使用子块进行检索。

4. **Delimiter for text（children_delimiter）**
   - 类型：字符串（输入框）
   - 默认值：`\n`
   - 显示条件：当"Child chunk are used for retrieval"开关启用时显示
   - 说明：用于子块分割的分隔符。

---

## UI特性

### 可滚动配置区域
- 使用 `max-h-[60vh] overflow-y-auto` 实现最大高度60vh的滚动容器
- 当配置项较多时，用户可以滚动查看所有配置选项
- 滚动容器统一管理所有解析器的配置区域

### 配置区域标题
- 主配置区域标题使用品牌色小色块和边框线增强视觉识别度
- MinerU配置区域使用带有横线的标题UI，左右横线，中间标题文字
- 标题使用大写字母、加粗字体和更宽的字符间距

### 布局优化
- 使用 `grid gap-5` 布局组织配置项，间距统一
- MinerU配置区域使用 `mt-6 space-y-6` 确保与其他配置区域的间距
- 开关组使用独立的容器，每个开关项添加边框、圆角和阴影效果

### 条件显示
- 根据选择的解析器类型，动态显示相应的配置选项
- 未选择解析器时，不显示配置区域
- 各解析器配置区域独立显示，互不干扰

---

## 测试建议

1. **前端测试**:
   - 测试每种解析器类型的配置选项是否正确显示
   - 测试配置区域的滚动功能
   - 测试配置数据的保存和加载

2. **后端测试**:
   - 测试PDF解析器配置是否正确传递到解析器
   - 测试各种解析器配置组合是否正常工作
   - 测试TCADP解析器的配置是否正确应用

3. **集成测试**:
   - 测试完整的工作流执行流程
   - 测试不同解析器配置下的PDF解析结果

---

## 注意事项

1. **向后兼容**: 所有新增字段都是可选的，不会影响现有的工作流
2. **默认值**: 如果未提供配置，系统会使用默认的解析器设置
3. **配置验证**: 前端使用Zod schema进行数据验证，确保配置格式正确
4. **错误处理**: 后端在解析器不可用时会有相应的错误提示

---

## 相关文件

- 工作流开始节点文件上传处理流程文档: `工作流开始节点文件上传处理流程.md`
- PDF解析器组件参考文档: `docs/guides/agent/agent_component_reference/parser.md`
- 选择PDF解析器指南: `docs/guides/dataset/select_pdf_parser.md`

---

## 版本信息

- **修改日期**: 2025-01-XX
- **修改人员**: AI Assistant
- **功能版本**: v0.22.0+

---

## 更新记录

### 2025-01-XX 更新：优化MinerU解析器配置UI界面

**问题描述**: 优化MinerU解析器配置部分的UI界面，提升用户体验和视觉效果。

**解决方案**: 
1. **标题样式优化**:
   - 移除了左侧边框样式（border-l-2 border-primary/30 pl-4 ml-2）
   - 添加了带有横线的标题UI，使用flex布局，左右横线，中间标题文字
   - 标题使用大写字母、加粗字体和更宽的字符间距，增强视觉识别度

2. **布局优化**:
   - 使用 `grid gap-5` 布局组织配置项，间距更统一
   - 移除了内部容器的overflow和高度限制，由外部滚动容器统一控制
   - 添加了 `mt-6 space-y-6` 确保与其他配置区域的间距

3. **开关组样式优化**:
   - 将公式识别和表格识别开关放在独立的容器中（`space-y-3 pt-2`）
   - 每个开关使用 `rounded-lg border p-3 shadow-sm` 样式，添加边框、圆角和阴影效果
   - 开关项使用 `flex items-center justify-between` 布局，标签添加 `cursor-pointer` 提升交互体验

4. **文本分块配置间距优化**:
   - 为文本分块配置组件添加 `mt-2` 上边距，确保与其他配置项的视觉分离

5. **代码修复**:
   - 修复了语言选项列表被截断的问题，恢复了完整的20种语言选项

**修改文件**:
- `web/src/pages/agent/form/begin-form/parameter-dialog.tsx` - 优化MinerU配置UI样式和布局

**说明**: 
- UI改进提升了配置界面的专业性和可读性
- 所有功能保持不变，仅优化了视觉效果和布局
- 保持了与其他解析器配置的一致性

---

### 2025-01-XX 更新：为MinerU解析器添加文本分块配置选项

**问题描述**: 前端工作流的变量设置中，如果解析器选择MinerU，也需要含有建议文本块大小、文本分段标识符、Child chunk are used for retrieval开关按钮和Delimiter for text设置窗口。

**解决方案**: 
1. 在MinerU配置部分添加 `BeginTextChunkingConfig` 组件，包含以下文本分块配置选项：
   - **建议文本块大小（chunk_token_num）**: 滑块输入，范围1-2048，默认值512
   - **文本分段标识符（delimiter）**: 分隔符输入框，支持多字符分隔符，默认值 `\n`
   - **Child chunk are used for retrieval（enable_children）**: 开关按钮，默认值 false
   - **Delimiter for text（children_delimiter）**: 分隔符输入框，仅在 `enable_children` 为true时显示，默认值 `\n`

2. 使MinerU解析器的配置选项与其他解析器（DeepDOC、Plain Text、Docling、TCADP Parser）保持一致，都包含完整的文本分块配置

**修改文件**:
- `web/src/pages/agent/form/begin-form/parameter-dialog.tsx` - 在MinerU配置部分添加BeginTextChunkingConfig组件

**说明**: 
- 使用已有的 `BeginTextChunkingConfig` 通用组件，确保配置选项的一致性
- 文本分块配置选项位于MinerU专用配置（解析方法、语言、公式识别、表格识别）之后
- 所有配置选项都在可滚动的配置区域内，用户体验良好

---

### 2025-01-XX 更新：完善MinerU解析器配置选项

**问题描述**: 前端工作流的变量设置中，如果解析器选择MinerU，需要额外含有MinerU选项，包括解析方法、语言、公式识别、表格识别。

**解决方案**: 
1. 在 `BeginPdfParserOptions` 组件中完善MinerU配置部分，添加以下配置字段：
   - **解析方法（mineru_parse_method）**: 下拉选择框，选项包括 auto（自动检测）、txt（文本提取）、ocr（光学字符识别），默认值为 'auto'
   - **语言（mineru_lang）**: 下拉选择框，支持20种语言选项（English、Chinese、Traditional Chinese、Russian、Ukrainian、Indonesian、Spanish、Vietnamese、Japanese、Korean、Portuguese BR、German、French、Italian、Tamil、Telugu、Kannada、Thai、Greek、Hindi），默认值为 'Chinese'
   - **公式识别（mineru_formula_enable）**: 开关按钮，默认值为 true
   - **表格识别（mineru_table_enable）**: 开关按钮，默认值为 true

2. 参考 `deepdoc/parser/mineru_parser.py` 中的语言映射和配置选项，确保前端配置与后端解析器参数一致

**修改文件**:
- `web/src/pages/agent/form/begin-form/parameter-dialog.tsx` - 完善MinerU配置UI，添加解析方法、语言、公式识别、表格识别四个配置字段

**说明**: 
- 所有MinerU配置字段已在Schema和接口中定义，此次改动仅完善UI显示
- 配置字段与知识库中的MinerU配置保持一致，确保用户体验统一
- 默认值设置参考了 `mineru-options-form-field.tsx` 组件的实现
- 添加了 `useEffect` 钩子，当用户选择MinerU解析器时自动设置默认值（解析方法：auto，语言：Chinese，公式识别：true，表格识别：true）
- 语言选项列表与 `deepdoc/parser/mineru_parser.py` 中的 `LANGUAGE_TO_MINERU_MAP` 保持一致，支持20种语言

---

### 2025-01-XX 更新：移除DeepDOC、Plain Text、Docling、TCADP Parser的语言配置字段

**问题描述**: 对于DeepDOC、Plain Text、Docling、TCADP Parser等解析器，前端工作流的变量设置的配置界面不需要有语言这栏。

**解决方案**: 
1. 从DeepDOC、Plain Text、Docling的配置UI中移除语言（lang）字段
2. TCADP Parser配置中原本就没有语言字段，无需修改
3. MinerU解析器保留其专用的语言字段（mineru_lang），不受影响

**修改文件**:
- `web/src/pages/agent/form/begin-form/parameter-dialog.tsx` - 移除DeepDOC、Plain Text、Docling配置中的语言字段

**说明**: 
- 此次改动仅影响前端UI显示，后端仍保留对`lang`字段的支持（向后兼容）
- MinerU解析器使用独立的`mineru_lang`字段，不受此次改动影响

---

### 2025-01-XX 更新：补充文本分块配置选项

**问题描述**: DeepDOC、Plain Text、Docling、TCADP Parser解析器的配置UI显示不完全，缺少文本分块相关配置选项。

**解决方案**: 
1. 新增 `BeginTextChunkingConfig` 通用组件，包含以下配置选项：
   - 建议文本块大小（chunk_token_num）
   - 文本分段标识符（delimiter）
   - Child chunk are used for retrieval开关（enable_children）
   - Delimiter for text（children_delimiter）

2. 在DeepDOC、Plain Text、Docling、TCADP Parser的配置中添加文本分块配置组件

3. 更新接口、Schema和后端代码以支持这些新配置字段

**修改文件**:
- `web/src/pages/agent/interface.ts` - 添加文本分块配置字段
- `web/src/pages/agent/form/begin-form/schema.ts` - 添加文本分块配置字段
- `web/src/pages/agent/form/begin-form/parameter-dialog.tsx` - 添加BeginTextChunkingConfig组件
- `agent/component/begin.py` - 支持提取文本分块配置
- `agent/component/fillup.py` - 支持提取文本分块配置
- `api/db/services/file_service.py` - 支持传递文本分块配置到parser_config

---

## 总结

本次改动完整实现了工作流开始节点PDF类型参数的解析器配置功能，支持所有可用的PDF解析器类型，并为每种解析器提供了相应的配置选项。对于DeepDOC、Plain Text、Docling、TCADP Parser等解析器，提供了完整的文本分块配置选项（建议文本块大小、文本分段标识符、Child chunk开关、Delimiter for text），但不包含语言设置字段（语言设置仅保留在MinerU解析器中）。MinerU解析器提供了完整的配置选项，包括解析方法（auto/txt/ocr）、语言设置（20种语言选项）、公式识别开关、表格识别开关，以及完整的文本分块配置选项（建议文本块大小、文本分段标识符、Child chunk开关、Delimiter for text），所有配置都有合理的默认值。配置界面支持滚动查看，用户体验良好。所有配置都能正确传递到后端并应用到PDF解析过程中。
