"""
MinerU V2 API 路由。

提供 V2 数据的独立查询接口，与 V1 /mineru_section/* 完全独立。

路由前缀: /v1/document/mineru_v2/
"""

import logging
from quart import Blueprint, request

from api.utils.api_utils import get_json_result, server_error_response, get_request_json
from api.utils.json_encode import normalize_parent_chain_for_storage
from common.constants import RetCode
from custom.mineru_v2.service import MineruV2Service

logger = logging.getLogger(__name__)

# 创建独立的 Blueprint
mineru_v2_bp = Blueprint("mineru_v2", __name__)


@mineru_v2_bp.route("/doc_chunk_datas", methods=["POST"])
async def mineru_v2_doc_chunk_datas():
    """
    获取文档的所有 V2 块数据。

    请求参数:
        doc_id: str  文档 ID（必填）

    返回:
        {
            "doc_id": "...",
            "count": 块数量,
            "sections": [
                {
                    "chunk_id": "...",
                    "type": "title|paragraph|list|table|image|code|equation|page_footer",
                    "data": "纯文本内容",
                    "content": "图片描述等",
                    "bbox": [x0,y0,x1,y1],
                    "page_idx": 页码,
                    "text_level": 标题层级,
                    "img_path": "图片路径",
                    "table_html": "表格HTML",
                    "table_caption": "表格标题",
                    "table_footnote": "表格脚注",
                    "list_items": [{...}],
                    "list_type": "列表类型",
                    "inline_formula": [{...}],
                    "span_json": "原始span数组"
                }
            ]
        }
    """
    try:
        req = await get_request_json()
        doc_id = (req.get("doc_id") or "").strip()
        if not doc_id:
            return get_json_result(
                data=False, message="doc_id 不能为空", code=RetCode.ARGUMENT_ERROR
            )

        rows = MineruV2Service.get_chunk_ids_by_doc_id(doc_id)
        result = []
        for row in rows:
            row_type = str(row.get("type") or "").strip().lower()

            # 按类型决定 data 字段的值（便捷字段，供前端快速展示）
            if row_type == "table":
                data = row.get("table_html") or row.get("text")
            elif row_type == "image":
                data = row.get("img_path") or row.get("content") or row.get("text")
            elif row_type == "list":
                data = row.get("text")
            else:
                data = row.get("text") or row.get("content")

            item = {
                "chunk_id": row.get("chunk_id"),
                "type": row.get("type"),
                "data": data,
                "bbox": row.get("bbox"),          # 原始 bbox（MinerU 输出，原生 list[int]）
                "is_rotated": bool(row.get("is_rotated", False)),  # MinerU 是否对 PDF 做了自动摆正
                "page_idx": row.get("page_idx"),
            }

            # bbox_rotated：旋转修正后的 bbox（仅当 PDF 有 /Rotate 时非空）
            if row.get("bbox_rotated") is not None:
                item["bbox_rotated"] = row.get("bbox_rotated")

            # 可选字段 — 使用 is not None 判断，因为空 list/空字符串是合法值
            if row.get("text_level") is not None:
                item["text_level"] = row.get("text_level")
            if row.get("img_path"):
                item["img_path"] = row.get("img_path")
            if row.get("content") is not None:
                item["content"] = row.get("content")
            if row.get("table_html") is not None:
                item["table_html"] = row.get("table_html")
            if row.get("table_caption") is not None:
                item["table_caption"] = row.get("table_caption")
            if row.get("table_footnote") is not None:
                item["table_footnote"] = row.get("table_footnote")
            if row.get("list_items") is not None:
                item["list_items"] = row.get("list_items")
            if row.get("list_type") is not None:
                item["list_type"] = row.get("list_type")
            if row.get("inline_formula") is not None:
                item["inline_formula"] = row.get("inline_formula")
            if row.get("span_json") is not None:
                item["span_json"] = row.get("span_json")
            if row.get("sub_type") is not None:
                item["sub_type"] = row.get("sub_type")
            if row.get("image_caption") is not None:
                item["image_caption"] = row.get("image_caption")
            if row.get("image_footnote") is not None:
                item["image_footnote"] = row.get("image_footnote")

            result.append(item)

        return get_json_result(
            data={"doc_id": doc_id, "sections": result, "count": len(result)}
        )
    except Exception as e:
        return server_error_response(e)


@mineru_v2_bp.route("/get_field", methods=["POST"])
async def mineru_v2_get_field():
    """
    按 chunk_id 获取 V2 块的指定字段。

    请求参数:
        chunk_id: str|list[str]  块 ID（必填，支持单值或数组）
        field_name: str|list[str] 字段名（必填）

    允许的字段:
        type, text, content, bbox, page_idx, text_level,
        img_path, table_html, table_caption, table_footnote,
        list_items, list_type, inline_formula, span_json,
        sub_type, kb_id, doc_id
    """
    try:
        req = await get_request_json()
        raw_chunk = req.get("chunk_id")
        raw_field = req.get("field_name")

        if not raw_chunk:
            return get_json_result(
                data=False, message="chunk_id 不能为空", code=RetCode.ARGUMENT_ERROR
            )
        if not raw_field:
            return get_json_result(
                data=False, message="field_name 不能为空", code=RetCode.ARGUMENT_ERROR
            )

        is_multi_chunk = isinstance(raw_chunk, list)
        is_multi_field = isinstance(raw_field, list)

        chunk_ids = []
        if is_multi_chunk:
            for c in raw_chunk:
                cid = (str(c or "")).strip()
                if cid:
                    chunk_ids.append(cid)
        else:
            cid = (str(raw_chunk or "")).strip()
            if cid:
                chunk_ids.append(cid)

        if not chunk_ids:
            return get_json_result(
                data=False, message="chunk_id 不能为空", code=RetCode.ARGUMENT_ERROR
            )

        field_names = []
        if is_multi_field:
            for f in raw_field:
                fn = (str(f or "")).strip().lower()
                if fn:
                    field_names.append(fn)
        else:
            fn = (str(raw_field or "")).strip().lower()
            if fn:
                field_names.append(fn)

        if not field_names:
            return get_json_result(
                data=False, message="field_name 不能为空", code=RetCode.ARGUMENT_ERROR
            )

        # V2 允许的字段（比 V1 多了 table_html, inline_formula, span_json, list_type, content）
        allowed_fields = {
            "type", "text", "content", "bbox", "page_idx", "text_level",
            "img_path", "table_html", "table_caption", "table_footnote",
            "list_items", "list_type", "inline_formula", "span_json",
            "sub_type", "kb_id", "doc_id",
        }
        for fn in field_names:
            if fn not in allowed_fields:
                return get_json_result(
                    data=False,
                    message=f"field_name 不合法：{fn}，允许的字段：{', '.join(sorted(allowed_fields))}",
                    code=RetCode.ARGUMENT_ERROR,
                )

        def _normalize_value(field_name, value):
            if field_name == "parent_chain":
                return normalize_parent_chain_for_storage(value)
            return value

        missing_chunk_ids = []
        chunk_data = {}
        for cid in chunk_ids:
            section = MineruV2Service.get_by_chunk_id(cid)
            if not section:
                missing_chunk_ids.append(cid)
                continue
            if is_multi_field:
                chunk_data[cid] = {
                    fn: _normalize_value(fn, getattr(section, fn, None))
                    for fn in field_names
                }
            else:
                chunk_data[cid] = _normalize_value(
                    field_names[0], getattr(section, field_names[0], None)
                )

        if not is_multi_chunk and not is_multi_field:
            if missing_chunk_ids:
                return get_json_result(
                    data=False,
                    message="未找到对应 chunk_id 的 mineru_section_v2 记录",
                    code=RetCode.NOT_FOUND,
                )
            cid = chunk_ids[0]
            return get_json_result(
                data={
                    "chunk_id": cid,
                    "field_name": field_names[0],
                    "field_value": chunk_data.get(cid),
                }
            )

        return get_json_result(
            data={
                "chunk_data": chunk_data,
                "missing_chunk_ids": missing_chunk_ids,
            }
        )
    except Exception as e:
        return server_error_response(e)



@mineru_v2_bp.route("/submit", methods=["POST"])
async def submit_mineru_v2_section():
    """
    提交 V2 数据到检索索引。

    流程：
    1. 从 mineru_section_v2 表读取数据
    2. 转换为 V1 content_list 兼容格式
    3. 写入 MinIO: {doc_id}/content_list.json
    4. 设置 parser_config 触发重新解析
    5. 调用 DocumentService.run() 重建向量索引

    请求参数:
        kb_id: str      知识库 ID（必填）
        doc_id: str     文档 ID（必填）
        batch_size: int 分批大小，默认 500（可选，1-5000）

    返回:
        {
            "kb_id": "...",
            "doc_id": "...",
            "record_count": 处理记录数,
            "content_changed": true/false,
            "reparse_triggered": true/false
        }
    """
    temp_file_path = None
    temp_file = None
    try:
        from api.db.services.knowledgebase_service import KnowledgebaseService
        from api.db.services.document_service import DocumentService
        from api.db.services.task_service import TaskService, has_canceled, CANVAS_DEBUG_DOC_ID
        from api.db.db_models import TaskStatus
        from api.apps.document_app import _mineru_json_list_or_empty
        from common import settings
        from api.apps.sdk.doc import search
        from rag.svr.task_executor import cancel_all_task_of
        import tempfile, os, json

        req = await get_request_json()
        kb_id = (req.get("kb_id") or "").strip()
        doc_id = (req.get("doc_id") or "").strip()
        if not kb_id or not doc_id:
            return get_json_result(
                data=False, message="kb_id 或 doc_id 不能为空", code=RetCode.ARGUMENT_ERROR
            )

        try:
            batch_size = int(req.get("batch_size") or 500)
        except Exception:
            return get_json_result(
                data=False, message="batch_size 必须为整数", code=RetCode.ARGUMENT_ERROR
            )
        if batch_size <= 0 or batch_size > 5000:
            return get_json_result(
                data=False, message="batch_size 取值范围应为 1-5000", code=RetCode.ARGUMENT_ERROR
            )

        # 权限校验
        e, kb = KnowledgebaseService.get_by_id(kb_id)
        if not e:
            return get_json_result(data=False, message="知识库不存在", code=RetCode.NOT_FOUND)

        from api.apps import current_user
        from api.apps.document_app import check_kb_team_permission
        if not check_kb_team_permission(kb, current_user.id):
            return get_json_result(
                data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR
            )

        e, doc = DocumentService.get_by_id(doc_id)
        if not e:
            return get_json_result(data=False, message="文档不存在", code=RetCode.NOT_FOUND)
        if str(doc.kb_id) != kb_id:
            return get_json_result(
                data=False, message="doc_id 不属于当前知识库", code=RetCode.ARGUMENT_ERROR
            )

        # 从 mineru_section_v2 表读取数据
        rows = MineruV2Service.get_chunk_ids_by_doc_id(doc_id)
        if not rows:
            return get_json_result(
                data=False, message="未找到可提交的 mineru_section_v2 数据", code=RetCode.NOT_FOUND
            )

        # 转换为 V1 content_list 兼容格式
        def _convert_v2_row_to_content_item(row):
            """将 mineru_section_v2 行转换为 content_list 格式（V1 兼容）。"""
            row_type = str(row.get("type") or "").strip() or "unknown"
            row_type_norm = row_type.lower()
            item = {
                "type": row_type,
                "chunk_id": str(row.get("chunk_id") or "").strip(),
                "bbox": row.get("bbox"),
                "page_idx": row.get("page_idx"),
            }

            # 图片类型
            if row_type_norm == "image":
                if row.get("img_path"):
                    item["img_path"] = row.get("img_path")
                item["image_caption"] = row.get("image_caption") or []
                item["image_footnote"] = row.get("image_footnote") or []
                if row.get("content"):
                    item["text"] = row.get("content")
                elif row.get("text"):
                    item["text"] = row.get("text")
                return item

            # 表格类型（V2: table_html → V1: table_body）
            if row_type_norm == "table":
                if row.get("img_path"):
                    item["img_path"] = row.get("img_path")
                item["table_caption"] = row.get("table_caption") or []
                item["table_footnote"] = row.get("table_footnote") or []
                if row.get("table_html"):
                    item["table_body"] = row.get("table_html")
                return item

            # 标题类型（V2: title → V1: text + text_level）
            if row_type_norm == "title":
                item["type"] = "text"
                if row.get("text"):
                    item["text"] = row.get("text")
                if row.get("text_level") is not None:
                    item["text_level"] = row.get("text_level")
                return item

            # 段落类型（V2: paragraph → V1: text）
            if row_type_norm == "paragraph":
                item["type"] = "text"
                if row.get("text"):
                    item["text"] = row.get("text")
                return item

            # 列表类型
            if row_type_norm == "list":
                item["list_items"] = row.get("list_items") or []
                if row.get("text"):
                    item["text"] = row.get("text")
                return item

            # 页眉/页脚
            if row_type_norm in ("page_header", "header"):
                item["type"] = "header"
                if row.get("text"):
                    item["text"] = row.get("text")
                return item
            if row_type_norm in ("page_footer", "footer"):
                item["type"] = "footer"
                if row.get("text"):
                    item["text"] = row.get("text")
                return item

            # 代码类型
            if row_type_norm == "code":
                if row.get("text"):
                    item["code_body"] = row.get("text")
                return item

            # 公式类型
            if row_type_norm == "equation":
                if row.get("text"):
                    item["text"] = row.get("text")
                return item

            # 未知类型：兜底
            if row.get("text"):
                item["text"] = row.get("text")
            if row.get("img_path"):
                item["img_path"] = row.get("img_path")
            if row.get("sub_type"):
                item["sub_type"] = row.get("sub_type")
            if row.get("list_items"):
                item["list_items"] = row.get("list_items")
            return item

        # 写入临时文件（content_list.json 格式）
        target_key = f"{doc_id}/content_list.json"
        temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json", encoding="utf-8")
        temp_file_path = temp_file.name

        content_items = []
        for row in rows:
            item = _convert_v2_row_to_content_item(row)
            content_items.append(item)

        json.dump(content_items, temp_file, ensure_ascii=False)
        temp_file.flush()
        temp_file.close()
        temp_file = None

        with open(temp_file_path, "rb") as f:
            payload = f.read()

        # 检查内容是否变化
        old_payload = None
        try:
            old_payload = settings.STORAGE_IMPL.get(kb_id, target_key)
        except Exception:
            old_payload = None

        content_changed = old_payload != payload
        if content_changed:
            settings.STORAGE_IMPL.put(kb_id, target_key, payload)
        else:
            return get_json_result(data={
                "kb_id": kb_id,
                "doc_id": doc_id,
                "target_path": target_key,
                "record_count": len(content_items),
                "batch_size": batch_size,
                "content_changed": False,
                "reparse_triggered": False,
            })

        # 获取 tenant_id
        tenant_id = DocumentService.get_tenant_id(doc_id)
        if not tenant_id:
            return get_json_result(
                data=False, message="Tenant not found!", code=RetCode.NOT_FOUND
            )

        # 如果正在运行，先取消
        from api.db.db_models import TaskStatus as _TaskStatus
        from api.apps.document_app import cancel_all_task_of as _cancel_all
        if str(doc.run) == _TaskStatus.RUNNING.value:
            _cancel_all(doc_id)

        # 清除旧索引（如果已完成）
        if str(doc.run) == _TaskStatus.DONE.value:
            DocumentService.clear_chunk_num_when_rerun(doc.id)

        # 设置 parser_config：跳过 MinerU API，直接从 MinIO 读取 content_list
        parser_cfg = doc.parser_config if isinstance(doc.parser_config, dict) else {}
        parser_cfg = dict(parser_cfg)
        parser_cfg["use_submitted_content_list"] = True
        parser_cfg["skip_mineru_output_upload"] = True
        parser_cfg["skip_mineru_section_persist"] = True
        DocumentService.update_parser_config(doc.id, parser_cfg)

        # 重置文档状态
        info = {"run": _TaskStatus.RUNNING.value, "progress": 0, "progress_msg": "", "chunk_num": 0, "token_num": 0}
        DocumentService.update_by_id(doc_id, info)

        # 删除旧任务和索引
        TaskService.filter_delete([TaskService.model.doc_id == doc_id])
        from api.apps.sdk.doc import search as _search_module
        if settings.docStoreConn.index_exist(_search_module.index_name(tenant_id), doc.kb_id):
            settings.docStoreConn.delete({"doc_id": doc_id}, _search_module.index_name(tenant_id), doc.kb_id)

        # 触发重新解析
        kb_table_num_map = {}
        doc_dict = doc.to_dict()
        doc_dict["parser_config"] = parser_cfg
        DocumentService.run(tenant_id, doc_dict, kb_table_num_map)

        return get_json_result(data={
            "kb_id": kb_id,
            "doc_id": doc_id,
            "target_path": target_key,
            "record_count": len(content_items),
            "batch_size": batch_size,
            "content_changed": True,
            "reparse_triggered": True,
        })
    except Exception as e:
        return server_error_response(e)
    finally:
        if temp_file is not None:
            try:
                temp_file.close()
            except Exception:
                pass
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception:
                logging.warning("[custom.mineru_v2] 清理临时 content_list 文件失败: %s", temp_file_path)



def register_mineru_v2_api(app):
    """
    注册 V2 API 路由到 Quart app。

    在 api/apps/__init__.py 或 api/ragflow_server.py 中调用:

        from custom.mineru_v2.api import register_mineru_v2_api
        register_mineru_v2_api(app)

    路由前缀: /v1/document/mineru_v2/
    """
    from api.constants import API_VERSION
    app.register_blueprint(
        mineru_v2_bp, url_prefix=f"/{API_VERSION}/document/mineru_v2"
    )
    logger.info("[custom.mineru_v2] API 路由已注册: /%s/document/mineru_v2/", API_VERSION)
