
"""
MinerU V2 扩展模块。

本模块实现 MinerU content_list_v2.json 的独立解析与存储链路。

版本: 1.0.0
依赖: RAGFlow v0.23.1

## V1 vs V2 区别

| 维度        | V1 (content_list.json)     | V2 (content_list_v2.json)        |
|------------|----------------------------|----------------------------------|
| 顶层结构    | 扁平 list[block]           | list[1] → list[block]            |
| 文本粒度    | block 级 text 字段          | span 级数组 [{type, content}]    |
| 块类型      | text/table/image/list/...  | title/paragraph/list/table/...  |
| 表格 HTML   | table_body 字段             | table_content.html_body          |
| 内联公式    | 无                         | span type="inline_equation"      |
| 图片路径    | img_path 字段               | image_source.path                |

## 新增数据表

mineru_section_v2 — 与 mineru_section 完全独立，存储 V2 解析结果。

## 新增 API

/v1/document/mineru_v2/doc_chunk_datas  — 按 doc_id 获取 V2 块列表
/v1/document/mineru_v2/get_field         — 按 chunk_id 获取 V2 字段
/v1/document/mineru_v2/submit            — 提交 V2 数据到检索索引
"""
