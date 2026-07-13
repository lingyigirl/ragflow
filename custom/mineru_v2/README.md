# MinerU V2 扩展模块

## 设计原则

1. **完全独立于 V1 链路** — 不修改 `mineru_parser.py`、`_transfer_to_sections`、`MineruSection` 表
2. **通过 Hook 注入** — 在 `parse_pdf` 流程中通过 try/except import 调用
3. **新表新字段** — `mineru_section_v2` 表专为 V2 数据结构设计
4. **Span 聚合策略** — V2 的 span 级文本按 type 聚合为 block 级内容

## 架构图

```
MinerU API (加 "return_content_list_v2": True)
        │
        ▼
_content_list_v2.json（V2 格式）
        │
        ▼
MinerUV2Parser.parse_content_list()  ← 本模块
        │
        ├── span 聚合：inline 公式合并为 LaTeX
        ├── block 转换：title/paragraph/list → 统一 V2Block
        │
        ▼
MineruSectionV2 表  ← models.py
        │
        ▼
MineruV2API (/mineru_v2/*)  ← api.py
```

## 使用方式

### 1. API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /v1/document/mineru_v2/doc_chunk_datas | 获取文档的所有 V2 块 |
| POST | /v1/document/mineru_v2/get_field | 按 chunk_id 获取指定字段 |
| POST | /v1/document/mineru_v2/submit | 提交 V2 数据到检索索引 |

### 2. 解析流程

Hook 自动注入到 `MinerUParser.parse_pdf()` 中：
- 当 MinerU API 返回 zip 时，同时查找 `_content_list_v2.json`
- 如果存在，解析并存入 `mineru_section_v2` 表
- 如不存在，静默跳过（不影响 V1 流程）
