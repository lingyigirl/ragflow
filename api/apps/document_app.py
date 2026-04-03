#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License
#
import asyncio
import json
import logging
import os.path
import pathlib
import re
from pathlib import Path
from quart import request, make_response
from api.apps import current_user, login_required
from api.common.check_team_permission import check_kb_team_permission
from api.constants import FILE_NAME_LEN_LIMIT, IMG_BASE64_PREFIX
from api.db import VALID_FILE_TYPES, FileType
from api.db.db_models import Task
from api.db.services import duplicate_name
from api.db.services.document_service import DocumentService, doc_upload_and_parse
from common.metadata_utils import meta_filter, convert_conditions
from api.db.services.file2document_service import File2DocumentService
from api.db.services.file_service import FileService
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.task_service import TaskService, cancel_all_task_of
from api.db.services.user_service import UserTenantService
from api.db.services.llm_service import LLMBundle
from common.misc_utils import get_uuid
from api.utils.api_utils import (
    get_data_error_result,
    get_json_result,
    server_error_response,
    validate_request, get_request_json,
)
from api.utils.file_utils import filename_type, thumbnail
from common.file_utils import get_project_base_directory
from common.constants import RetCode, VALID_TASK_STATUS, ParserType, TaskStatus, LLMType
from api.utils.web_utils import CONTENT_TYPE_MAP, html2pdf, is_valid_url
from deepdoc.parser.html_parser import RAGFlowHtmlParser
from rag.nlp import search, rag_tokenizer
from rag.utils.voucher_classifier import (
    build_voucher_classify_content,
    build_voucher_classify_content_from_content_list,
    classify_voucher_content,
    get_failed_voucher_payload,
)
from common import settings
import requests
import os
import tempfile
import zipfile
import base64
import shutil
from urllib.parse import quote


async def _classify_voucher_type_for_mineru_doc(kb_id: str, doc_id: str):
    failed_payload = get_failed_voucher_payload()
    try:
        content_bin = await asyncio.to_thread(settings.STORAGE_IMPL.get, kb_id, f"{doc_id}/content_list.json")
        content_list = json.loads((content_bin or b"[]").decode("utf-8")) if content_bin else []
    except Exception:
        content_list = []
    content = build_voucher_classify_content_from_content_list(content_list)
    if not content:
        DocumentService.update_by_id(doc_id, failed_payload)
        return
    e, kb = KnowledgebaseService.get_by_id(kb_id)
    if not e:
        return
    chat_mdl = LLMBundle(kb.tenant_id, LLMType.CHAT, llm_name=None, lang=kb.language or "Chinese")
    try:
        logging.info("[voucher_type_llm] 开始判断文档类型 doc_id=%s", doc_id)
        payload = await classify_voucher_content(chat_mdl, content, timeout=45)
        if payload["llm_classify_success"]:
            logging.info("[voucher_type_llm] 判断类型结果 doc_id=%s voucher_type=%s", doc_id, payload["voucher_type"])
            logging.info("[voucher_type_llm] 开始写入数据库 doc_id=%s", doc_id)
            ok = DocumentService.update_by_id(doc_id, payload)
            if ok:
                logging.info("[voucher_type_llm] 数据库写入成功 doc_id=%s", doc_id)
            else:
                logging.warning("[voucher_type_llm] 数据库写入失败 doc_id=%s", doc_id)
            return
        DocumentService.update_by_id(doc_id, failed_payload)
    except Exception as ex:
        logging.warning("[voucher_type_llm] 分类异常 doc_id=%s err=%s", doc_id, ex)
        DocumentService.update_by_id(doc_id, failed_payload)


async def _fetch_doc_content_for_voucher_classify(doc, tenant_id: str) -> str:
    # 优先从 MinerU content_list 读取正文；无结果则回退到向量库 chunk 文本。
    try:
        content_bin = await asyncio.to_thread(settings.STORAGE_IMPL.get, doc.kb_id, f"{doc.id}/content_list.json")
        content_list = json.loads((content_bin or b"[]").decode("utf-8")) if content_bin else []
    except Exception:
        content_list = []
    content = build_voucher_classify_content_from_content_list(content_list)
    if content:
        return content

    index_name = search.index_name(tenant_id)
    if not settings.docStoreConn.index_exist(index_name, doc.kb_id):
        return ""
    query = {
        "doc_ids": [doc.id],
        "page": 1,
        "size": 50,
        "question": "",
        "sort": True,
    }
    sres = settings.retriever.search(query, index_name, [doc.kb_id], emb_mdl=None, highlight=False)
    chunks = []
    for cid in getattr(sres, "ids", []):
        text = (getattr(sres, "field", {}) or {}).get(cid, {}).get("content_with_weight", "")
        if text:
            chunks.append({"content_with_weight": text})
    return build_voucher_classify_content(chunks)


async def _classify_voucher_type_for_doc(doc, tenant_id: str):
    failed_payload = get_failed_voucher_payload()
    e, kb = KnowledgebaseService.get_by_id(doc.kb_id)
    if not e:
        return False, failed_payload, "Dataset not found."
    content = await _fetch_doc_content_for_voucher_classify(doc, tenant_id)
    if not content:
        DocumentService.update_by_id(doc.id, failed_payload)
        return True, failed_payload, "No available content for classification."

    chat_mdl = LLMBundle(tenant_id, LLMType.CHAT, llm_name=None, lang=kb.language or "Chinese")
    try:
        logging.info("[voucher_type_llm] 开始判断文档类型 doc_id=%s", doc.id)
        payload = await classify_voucher_content(chat_mdl, content, timeout=45)
        if payload["llm_classify_success"]:
            logging.info("[voucher_type_llm] 判断类型结果 doc_id=%s voucher_type=%s", doc.id, payload["voucher_type"])
            logging.info("[voucher_type_llm] 开始写入数据库 doc_id=%s", doc.id)
            ok = DocumentService.update_by_id(doc.id, payload)
            if ok:
                logging.info("[voucher_type_llm] 数据库写入成功 doc_id=%s", doc.id)
                return True, payload, None
            logging.warning("[voucher_type_llm] 数据库写入失败 doc_id=%s", doc.id)
            return False, payload, "Database error (voucher_type update)!"
        DocumentService.update_by_id(doc.id, failed_payload)
        return True, failed_payload, None
    except Exception as ex:
        logging.warning("[voucher_type_llm] 分类异常 doc_id=%s err=%s", doc.id, ex)
        DocumentService.update_by_id(doc.id, failed_payload)
        return True, failed_payload, str(ex)


@manager.route("/upload", methods=["POST"])  # noqa: F821
@login_required
@validate_request("kb_id")
async def upload():
    form = await request.form
    kb_id = form.get("kb_id")
    if not kb_id:
        return get_json_result(data=False, message='Lack of "KB ID"', code=RetCode.ARGUMENT_ERROR)
    files = await request.files
    if "file" not in files:
        return get_json_result(data=False, message="No file part!", code=RetCode.ARGUMENT_ERROR)

    file_objs = files.getlist("file")
    for file_obj in file_objs:
        if file_obj.filename == "":
            return get_json_result(data=False, message="No file selected!", code=RetCode.ARGUMENT_ERROR)
        if len(file_obj.filename.encode("utf-8")) > FILE_NAME_LEN_LIMIT:
            return get_json_result(data=False, message=f"File name must be {FILE_NAME_LEN_LIMIT} bytes or less.", code=RetCode.ARGUMENT_ERROR)

    e, kb = KnowledgebaseService.get_by_id(kb_id)
    if not e:
        raise LookupError("Can't find this dataset!")
    if not check_kb_team_permission(kb, current_user.id):
        return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)

    err, files = await asyncio.to_thread(FileService.upload_document, kb, file_objs, current_user.id)
    if err:
        return get_json_result(data=files, message="\n".join(err), code=RetCode.SERVER_ERROR)

    if not files:
        return get_json_result(data=files, message="There seems to be an issue with your file format. Please verify it is correct and not corrupted.", code=RetCode.DATA_ERROR)
    files = [f[0] for f in files]  # remove the blob

    return get_json_result(data=files)


@manager.route("/web_crawl", methods=["POST"])  # noqa: F821
@login_required
@validate_request("kb_id", "name", "url")
async def web_crawl():
    form = await request.form
    kb_id = form.get("kb_id")
    if not kb_id:
        return get_json_result(data=False, message='Lack of "KB ID"', code=RetCode.ARGUMENT_ERROR)
    name = form.get("name")
    url = form.get("url")
    if not is_valid_url(url):
        return get_json_result(data=False, message="The URL format is invalid", code=RetCode.ARGUMENT_ERROR)
    e, kb = KnowledgebaseService.get_by_id(kb_id)
    if not e:
        raise LookupError("Can't find this dataset!")
    if check_kb_team_permission(kb, current_user.id):
        return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)

    blob = html2pdf(url)
    if not blob:
        return server_error_response(ValueError("Download failure."))

    root_folder = FileService.get_root_folder(current_user.id)
    pf_id = root_folder["id"]
    FileService.init_knowledgebase_docs(pf_id, current_user.id)
    kb_root_folder = FileService.get_kb_folder(current_user.id)
    kb_folder = FileService.new_a_file_from_kb(kb.tenant_id, kb.name, kb_root_folder["id"])

    try:
        filename = duplicate_name(DocumentService.query, name=name + ".pdf", kb_id=kb.id)
        filetype = filename_type(filename)
        if filetype == FileType.OTHER.value:
            raise RuntimeError("This type of file has not been supported yet!")

        location = filename
        while settings.STORAGE_IMPL.obj_exist(kb_id, location):
            location += "_"
        settings.STORAGE_IMPL.put(kb_id, location, blob)
        doc = {
            "id": get_uuid(),
            "kb_id": kb.id,
            "parser_id": kb.parser_id,
            "parser_config": kb.parser_config,
            "created_by": current_user.id,
            "type": filetype,
            "name": filename,
            "location": location,
            "size": len(blob),
            "thumbnail": thumbnail(filename, blob),
            "suffix": Path(filename).suffix.lstrip("."),
        }
        if doc["type"] == FileType.VISUAL:
            doc["parser_id"] = ParserType.PICTURE.value
        if doc["type"] == FileType.AURAL:
            doc["parser_id"] = ParserType.AUDIO.value
        if re.search(r"\.(ppt|pptx|pages)$", filename):
            doc["parser_id"] = ParserType.PRESENTATION.value
        if re.search(r"\.(eml)$", filename):
            doc["parser_id"] = ParserType.EMAIL.value
        DocumentService.insert(doc)
        FileService.add_file_from_kb(doc, kb_folder["id"], kb.tenant_id)
    except Exception as e:
        return server_error_response(e)
    return get_json_result(data=True)


@manager.route("/create", methods=["POST"])  # noqa: F821
@login_required
@validate_request("name", "kb_id")
async def create():
    req = await get_request_json()
    kb_id = req["kb_id"]
    if not kb_id:
        return get_json_result(data=False, message='Lack of "KB ID"', code=RetCode.ARGUMENT_ERROR)
    if len(req["name"].encode("utf-8")) > FILE_NAME_LEN_LIMIT:
        return get_json_result(data=False, message=f"File name must be {FILE_NAME_LEN_LIMIT} bytes or less.", code=RetCode.ARGUMENT_ERROR)

    if req["name"].strip() == "":
        return get_json_result(data=False, message="File name can't be empty.", code=RetCode.ARGUMENT_ERROR)
    req["name"] = req["name"].strip()

    try:
        e, kb = KnowledgebaseService.get_by_id(kb_id)
        if not e:
            return get_data_error_result(message="Can't find this dataset!")

        if DocumentService.query(name=req["name"], kb_id=kb_id):
            return get_data_error_result(message="Duplicated document name in the same dataset.")

        kb_root_folder = FileService.get_kb_folder(kb.tenant_id)
        if not kb_root_folder:
            return get_data_error_result(message="Cannot find the root folder.")
        kb_folder = FileService.new_a_file_from_kb(
            kb.tenant_id,
            kb.name,
            kb_root_folder["id"],
        )
        if not kb_folder:
            return get_data_error_result(message="Cannot find the kb folder for this file.")

        doc = DocumentService.insert(
            {
                "id": get_uuid(),
                "kb_id": kb.id,
                "parser_id": kb.parser_id,
                "pipeline_id": kb.pipeline_id,
                "parser_config": kb.parser_config,
                "created_by": current_user.id,
                "type": FileType.VIRTUAL,
                "name": req["name"],
                "suffix": Path(req["name"]).suffix.lstrip("."),
                "location": "",
                "size": 0,
            }
        )

        FileService.add_file_from_kb(doc.to_dict(), kb_folder["id"], kb.tenant_id)

        return get_json_result(data=doc.to_json())
    except Exception as e:
        return server_error_response(e)


@manager.route("/list", methods=["POST"])  # noqa: F821
@login_required
async def list_docs():
    kb_id = request.args.get("kb_id")
    if not kb_id:
        return get_json_result(data=False, message='Lack of "KB ID"', code=RetCode.ARGUMENT_ERROR)
    tenants = UserTenantService.query(user_id=current_user.id)
    for tenant in tenants:
        if KnowledgebaseService.query(tenant_id=tenant.tenant_id, id=kb_id):
            break
    else:
        return get_json_result(data=False, message="Only owner of dataset authorized for this operation.", code=RetCode.OPERATING_ERROR)
    keywords = request.args.get("keywords", "")

    page_number = int(request.args.get("page", 0))
    items_per_page = int(request.args.get("page_size", 0))
    orderby = request.args.get("orderby", "create_time")
    if request.args.get("desc", "true").lower() == "false":
        desc = False
    else:
        desc = True
    create_time_from = int(request.args.get("create_time_from", 0))
    create_time_to = int(request.args.get("create_time_to", 0))

    req = await get_request_json()

    return_empty_metadata = req.get("return_empty_metadata", False)
    if isinstance(return_empty_metadata, str):
        return_empty_metadata = return_empty_metadata.lower() == "true"

    run_status = req.get("run_status", [])
    if run_status:
        invalid_status = {s for s in run_status if s not in VALID_TASK_STATUS}
        if invalid_status:
            return get_data_error_result(message=f"Invalid filter run status conditions: {', '.join(invalid_status)}")

    types = req.get("types", [])
    if types:
        invalid_types = {t for t in types if t not in VALID_FILE_TYPES}
        if invalid_types:
            return get_data_error_result(message=f"Invalid filter conditions: {', '.join(invalid_types)} type{'s' if len(invalid_types) > 1 else ''}")

    suffix = req.get("suffix", [])
    metadata_condition = req.get("metadata_condition", {}) or {}
    metadata = req.get("metadata", {}) or {}
    if isinstance(metadata, dict) and metadata.get("empty_metadata"):
        return_empty_metadata = True
        metadata = {k: v for k, v in metadata.items() if k != "empty_metadata"}
    if return_empty_metadata:
        metadata_condition = {}
        metadata = {}
    else:
        if metadata_condition and not isinstance(metadata_condition, dict):
            return get_data_error_result(message="metadata_condition must be an object.")
        if metadata and not isinstance(metadata, dict):
            return get_data_error_result(message="metadata must be an object.")

    doc_ids_filter = None
    metas = None
    if metadata_condition or metadata:
        metas = DocumentService.get_flatted_meta_by_kbs([kb_id])

    if metadata_condition:
        doc_ids_filter = set(meta_filter(metas, convert_conditions(metadata_condition), metadata_condition.get("logic", "and")))
        if metadata_condition.get("conditions") and not doc_ids_filter:
            return get_json_result(data={"total": 0, "docs": []})

    if metadata:
        metadata_doc_ids = None
        for key, values in metadata.items():
            if not values:
                continue
            if not isinstance(values, list):
                values = [values]
            values = [str(v) for v in values if v is not None and str(v).strip()]
            if not values:
                continue
            key_doc_ids = set()
            for value in values:
                key_doc_ids.update(metas.get(key, {}).get(value, []))
            if metadata_doc_ids is None:
                metadata_doc_ids = key_doc_ids
            else:
                metadata_doc_ids &= key_doc_ids
            if not metadata_doc_ids:
                return get_json_result(data={"total": 0, "docs": []})
        if metadata_doc_ids is not None:
            if doc_ids_filter is None:
                doc_ids_filter = metadata_doc_ids
            else:
                doc_ids_filter &= metadata_doc_ids
            if not doc_ids_filter:
                return get_json_result(data={"total": 0, "docs": []})

    if doc_ids_filter is not None:
        doc_ids_filter = list(doc_ids_filter)

    try:
        docs, tol = DocumentService.get_by_kb_id(
            kb_id,
            page_number,
            items_per_page,
            orderby,
            desc,
            keywords,
            run_status,
            types,
            suffix,
            doc_ids_filter,
            return_empty_metadata=return_empty_metadata,
        )

        if create_time_from or create_time_to:
            filtered_docs = []
            for doc in docs:
                doc_create_time = doc.get("create_time", 0)
                if (create_time_from == 0 or doc_create_time >= create_time_from) and (create_time_to == 0 or doc_create_time <= create_time_to):
                    filtered_docs.append(doc)
            docs = filtered_docs

        for doc_item in docs:
            if doc_item["thumbnail"] and not doc_item["thumbnail"].startswith(IMG_BASE64_PREFIX):
                doc_item["thumbnail"] = f"/v1/document/image/{kb_id}-{doc_item['thumbnail']}"
            if doc_item.get("source_type"):
                doc_item["source_type"] = doc_item["source_type"].split("/")[0]

        return get_json_result(data={"total": tol, "docs": docs})
    except Exception as e:
        return server_error_response(e)


@manager.route("/classify_voucher_type", methods=["POST"])  # noqa: F821
@login_required
@validate_request("doc_id")
async def classify_voucher_type():
    req = await get_request_json()
    doc_id = req["doc_id"]
    if not DocumentService.accessible(doc_id, current_user.id):
        return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)
    e, doc = DocumentService.get_by_id(doc_id)
    if not e:
        return get_data_error_result(message="Document not found!")
    tenant_id = DocumentService.get_tenant_id(doc_id)
    if not tenant_id:
        return get_data_error_result(message="Tenant not found!")

    ok, payload, err = await _classify_voucher_type_for_doc(doc, tenant_id)
    if not ok:
        return get_data_error_result(message=err or "Database error (voucher_type update)!")
    return get_json_result(data=payload, message=err or "")


@manager.route("/filter", methods=["POST"])  # noqa: F821
@login_required
async def get_filter():
    req = await get_request_json()

    kb_id = req.get("kb_id")
    if not kb_id:
        return get_json_result(data=False, message='Lack of "KB ID"', code=RetCode.ARGUMENT_ERROR)
    tenants = UserTenantService.query(user_id=current_user.id)
    for tenant in tenants:
        if KnowledgebaseService.query(tenant_id=tenant.tenant_id, id=kb_id):
            break
    else:
        return get_json_result(data=False, message="Only owner of dataset authorized for this operation.", code=RetCode.OPERATING_ERROR)

    keywords = req.get("keywords", "")

    suffix = req.get("suffix", [])

    run_status = req.get("run_status", [])
    if run_status:
        invalid_status = {s for s in run_status if s not in VALID_TASK_STATUS}
        if invalid_status:
            return get_data_error_result(message=f"Invalid filter run status conditions: {', '.join(invalid_status)}")

    types = req.get("types", [])
    if types:
        invalid_types = {t for t in types if t not in VALID_FILE_TYPES}
        if invalid_types:
            return get_data_error_result(message=f"Invalid filter conditions: {', '.join(invalid_types)} type{'s' if len(invalid_types) > 1 else ''}")

    try:
        filter, total = DocumentService.get_filter_by_kb_id(kb_id, keywords, run_status, types, suffix)
        return get_json_result(data={"total": total, "filter": filter})
    except Exception as e:
        return server_error_response(e)


@manager.route("/infos", methods=["POST"])  # noqa: F821
@login_required
async def doc_infos():
    req = await get_request_json()
    doc_ids = req["doc_ids"]
    for doc_id in doc_ids:
        if not DocumentService.accessible(doc_id, current_user.id):
            return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)
    docs = DocumentService.get_by_ids(doc_ids)
    return get_json_result(data=list(docs.dicts()))


@manager.route("/metadata/summary", methods=["POST"])  # noqa: F821
@login_required
async def metadata_summary():
    req = await get_request_json()
    kb_id = req.get("kb_id")
    if not kb_id:
        return get_json_result(data=False, message='Lack of "KB ID"', code=RetCode.ARGUMENT_ERROR)

    tenants = UserTenantService.query(user_id=current_user.id)
    for tenant in tenants:
        if KnowledgebaseService.query(tenant_id=tenant.tenant_id, id=kb_id):
            break
    else:
        return get_json_result(data=False, message="Only owner of dataset authorized for this operation.", code=RetCode.OPERATING_ERROR)

    try:
        summary = DocumentService.get_metadata_summary(kb_id)
        return get_json_result(data={"summary": summary})
    except Exception as e:
        return server_error_response(e)


@manager.route("/metadata/update", methods=["POST"])  # noqa: F821
@login_required
async def metadata_update():
    req = await get_request_json()
    kb_id = req.get("kb_id")
    if not kb_id:
        return get_json_result(data=False, message='Lack of "KB ID"', code=RetCode.ARGUMENT_ERROR)

    tenants = UserTenantService.query(user_id=current_user.id)
    for tenant in tenants:
        if KnowledgebaseService.query(tenant_id=tenant.tenant_id, id=kb_id):
            break
    else:
        return get_json_result(data=False, message="Only owner of dataset authorized for this operation.", code=RetCode.OPERATING_ERROR)

    selector = req.get("selector", {}) or {}
    updates = req.get("updates", []) or []
    deletes = req.get("deletes", []) or []

    if not isinstance(selector, dict):
        return get_json_result(data=False, message="selector must be an object.", code=RetCode.ARGUMENT_ERROR)
    if not isinstance(updates, list) or not isinstance(deletes, list):
        return get_json_result(data=False, message="updates and deletes must be lists.", code=RetCode.ARGUMENT_ERROR)

    metadata_condition = selector.get("metadata_condition", {}) or {}
    if metadata_condition and not isinstance(metadata_condition, dict):
        return get_json_result(data=False, message="metadata_condition must be an object.", code=RetCode.ARGUMENT_ERROR)

    document_ids = selector.get("document_ids", []) or []
    if document_ids and not isinstance(document_ids, list):
        return get_json_result(data=False, message="document_ids must be a list.", code=RetCode.ARGUMENT_ERROR)

    for upd in updates:
        if not isinstance(upd, dict) or not upd.get("key") or "value" not in upd:
            return get_json_result(data=False, message="Each update requires key and value.", code=RetCode.ARGUMENT_ERROR)
    for d in deletes:
        if not isinstance(d, dict) or not d.get("key"):
            return get_json_result(data=False, message="Each delete requires key.", code=RetCode.ARGUMENT_ERROR)

    kb_doc_ids = KnowledgebaseService.list_documents_by_ids([kb_id])
    target_doc_ids = set(kb_doc_ids)
    if document_ids:
        invalid_ids = set(document_ids) - set(kb_doc_ids)
        if invalid_ids:
            return get_json_result(data=False, message=f"These documents do not belong to dataset {kb_id}: {', '.join(invalid_ids)}", code=RetCode.ARGUMENT_ERROR)
        target_doc_ids = set(document_ids)

    if metadata_condition:
        metas = DocumentService.get_flatted_meta_by_kbs([kb_id])
        filtered_ids = set(meta_filter(metas, convert_conditions(metadata_condition), metadata_condition.get("logic", "and")))
        target_doc_ids = target_doc_ids & filtered_ids
        if metadata_condition.get("conditions") and not target_doc_ids:
            return get_json_result(data={"updated": 0, "matched_docs": 0})

    target_doc_ids = list(target_doc_ids)
    updated = DocumentService.batch_update_metadata(kb_id, target_doc_ids, updates, deletes)
    return get_json_result(data={"updated": updated, "matched_docs": len(target_doc_ids)})


@manager.route("/update_metadata_setting", methods=["POST"])  # noqa: F821
@login_required
@validate_request("doc_id", "metadata")
async def update_metadata_setting():
    req = await get_request_json()
    if not DocumentService.accessible(req["doc_id"], current_user.id):
        return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)

    e, doc = DocumentService.get_by_id(req["doc_id"])
    if not e:
        return get_data_error_result(message="Document not found!")

    DocumentService.update_parser_config(doc.id, {"metadata": req["metadata"]})
    e, doc = DocumentService.get_by_id(doc.id)
    if not e:
        return get_data_error_result(message="Document not found!")

    return get_json_result(data=doc.to_dict())


@manager.route("/thumbnails", methods=["GET"])  # noqa: F821
# @login_required
def thumbnails():
    doc_ids = request.args.getlist("doc_ids")
    if not doc_ids:
        return get_json_result(data=False, message='Lack of "Document ID"', code=RetCode.ARGUMENT_ERROR)

    try:
        docs = DocumentService.get_thumbnails(doc_ids)

        for doc_item in docs:
            if doc_item["thumbnail"] and not doc_item["thumbnail"].startswith(IMG_BASE64_PREFIX):
                doc_item["thumbnail"] = f"/v1/document/image/{doc_item['kb_id']}-{doc_item['thumbnail']}"

        return get_json_result(data={d["id"]: d["thumbnail"] for d in docs})
    except Exception as e:
        return server_error_response(e)


@manager.route("/change_status", methods=["POST"])  # noqa: F821
@login_required
@validate_request("doc_ids", "status")
async def change_status():
    req = await get_request_json()
    doc_ids = req.get("doc_ids", [])
    status = str(req.get("status", ""))

    if status not in ["0", "1"]:
        return get_json_result(data=False, message='"Status" must be either 0 or 1!', code=RetCode.ARGUMENT_ERROR)

    result = {}
    for doc_id in doc_ids:
        if not DocumentService.accessible(doc_id, current_user.id):
            result[doc_id] = {"error": "No authorization."}
            continue

        try:
            e, doc = DocumentService.get_by_id(doc_id)
            if not e:
                result[doc_id] = {"error": "No authorization."}
                continue
            e, kb = KnowledgebaseService.get_by_id(doc.kb_id)
            if not e:
                result[doc_id] = {"error": "Can't find this dataset!"}
                continue
            if not DocumentService.update_by_id(doc_id, {"status": str(status)}):
                result[doc_id] = {"error": "Database error (Document update)!"}
                continue

            status_int = int(status)
            if not settings.docStoreConn.update({"doc_id": doc_id}, {"available_int": status_int}, search.index_name(kb.tenant_id), doc.kb_id):
                result[doc_id] = {"error": "Database error (docStore update)!"}
            result[doc_id] = {"status": status}
        except Exception as e:
            result[doc_id] = {"error": f"Internal server error: {str(e)}"}

    return get_json_result(data=result)


@manager.route("/rm", methods=["POST"])  # noqa: F821
@login_required
@validate_request("doc_id")
async def rm():
    req = await get_request_json()
    doc_ids = req["doc_id"]
    if isinstance(doc_ids, str):
        doc_ids = [doc_ids]

    for doc_id in doc_ids:
        if not DocumentService.accessible4deletion(doc_id, current_user.id):
            return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)

    errors = await asyncio.to_thread(FileService.delete_docs, doc_ids, current_user.id)

    if errors:
        return get_json_result(data=False, message=errors, code=RetCode.SERVER_ERROR)

    return get_json_result(data=True)


@manager.route("/run", methods=["POST"])  # noqa: F821
@login_required
@validate_request("doc_ids", "run")
async def run():
    req = await get_request_json()
    try:
        classify_switch = req.get("enable_voucher_type_classify", False)
        if isinstance(classify_switch, str):
            classify_switch = classify_switch.lower() == "true"
        classify_switch = bool(classify_switch)

        def _run_sync():
            for doc_id in req["doc_ids"]:
                if not DocumentService.accessible(doc_id, current_user.id):
                    return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)

            kb_table_num_map = {}
            for id in req["doc_ids"]:
                info = {"run": str(req["run"]), "progress": 0}
                if str(req["run"]) == TaskStatus.RUNNING.value and req.get("delete", False):
                    info["progress_msg"] = ""
                    info["chunk_num"] = 0
                    info["token_num"] = 0

                tenant_id = DocumentService.get_tenant_id(id)
                if not tenant_id:
                    return get_data_error_result(message="Tenant not found!")
                e, doc = DocumentService.get_by_id(id)
                if not e:
                    return get_data_error_result(message="Document not found!")

                if str(req["run"]) == TaskStatus.CANCEL.value:
                    if str(doc.run) == TaskStatus.RUNNING.value:
                        cancel_all_task_of(id)
                    else:
                        return get_data_error_result(message="Cannot cancel a task that is not in RUNNING status")
                if all([("delete" not in req or req["delete"]), str(req["run"]) == TaskStatus.RUNNING.value, str(doc.run) == TaskStatus.DONE.value]):
                    DocumentService.clear_chunk_num_when_rerun(doc.id)

                DocumentService.update_by_id(id, info)
                if req.get("delete", False):
                    TaskService.filter_delete([Task.doc_id == id])
                    if settings.docStoreConn.index_exist(search.index_name(tenant_id), doc.kb_id):
                        settings.docStoreConn.delete({"doc_id": id}, search.index_name(tenant_id), doc.kb_id)

                if str(req["run"]) == TaskStatus.RUNNING.value:
                    if req.get("apply_kb"):
                        e, kb = KnowledgebaseService.get_by_id(doc.kb_id)
                        if not e:
                            raise LookupError("Can't find this dataset!")
                        doc.parser_config["enable_metadata"] = kb.parser_config.get("enable_metadata", False)
                        doc.parser_config["metadata"] = kb.parser_config.get("metadata", {})
                        DocumentService.update_parser_config(doc.id, doc.parser_config)
                    doc.parser_config["enable_voucher_type_classify"] = classify_switch
                    DocumentService.update_parser_config(doc.id, doc.parser_config)
                    doc_dict = doc.to_dict()
                    DocumentService.run(tenant_id, doc_dict, kb_table_num_map)

            return get_json_result(data=True)

        return await asyncio.to_thread(_run_sync)
    except Exception as e:
        return server_error_response(e)


@manager.route("/rename", methods=["POST"])  # noqa: F821
@login_required
@validate_request("doc_id", "name")
async def rename():
    req = await get_request_json()
    try:
        def _rename_sync():
            if not DocumentService.accessible(req["doc_id"], current_user.id):
                return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)

            e, doc = DocumentService.get_by_id(req["doc_id"])
            if not e:
                return get_data_error_result(message="Document not found!")
            if pathlib.Path(req["name"].lower()).suffix != pathlib.Path(doc.name.lower()).suffix:
                return get_json_result(data=False, message="The extension of file can't be changed", code=RetCode.ARGUMENT_ERROR)
            if len(req["name"].encode("utf-8")) > FILE_NAME_LEN_LIMIT:
                return get_json_result(data=False, message=f"File name must be {FILE_NAME_LEN_LIMIT} bytes or less.", code=RetCode.ARGUMENT_ERROR)

            for d in DocumentService.query(name=req["name"], kb_id=doc.kb_id):
                if d.name == req["name"]:
                    return get_data_error_result(message="Duplicated document name in the same dataset.")

            if not DocumentService.update_by_id(req["doc_id"], {"name": req["name"]}):
                return get_data_error_result(message="Database error (Document rename)!")

            informs = File2DocumentService.get_by_document_id(req["doc_id"])
            if informs:
                e, file = FileService.get_by_id(informs[0].file_id)
                FileService.update_by_id(file.id, {"name": req["name"]})

            tenant_id = DocumentService.get_tenant_id(req["doc_id"])
            title_tks = rag_tokenizer.tokenize(req["name"])
            es_body = {
                "docnm_kwd": req["name"],
                "title_tks": title_tks,
                "title_sm_tks": rag_tokenizer.fine_grained_tokenize(title_tks),
            }
            if settings.docStoreConn.index_exist(search.index_name(tenant_id), doc.kb_id):
                settings.docStoreConn.update(
                    {"doc_id": req["doc_id"]},
                    es_body,
                    search.index_name(tenant_id),
                    doc.kb_id,
                )
            if "voucher_type" in req:
                voucher_type = req.get("voucher_type")
                if voucher_type is None:
                    return get_json_result(
                        data=False,
                        message='Lack of valid "voucher_type".',
                        code=RetCode.ARGUMENT_ERROR,
                    )
                voucher_type = str(voucher_type).strip()
                payload = {
                    "voucher_type": voucher_type,
                    "voucher_type_confidence": None,
                    "llm_classify_success": True,
                    "voucher_type_source": "manual",
                }
                if not DocumentService.update_by_id(req["doc_id"], payload):
                    return get_data_error_result(message="Database error (voucher_type update)!")
            return get_json_result(data=True)

        return await asyncio.to_thread(_rename_sync)

    except Exception as e:
        return server_error_response(e)


@manager.route("/get/<doc_id>", methods=["GET"])  # noqa: F821
# @login_required
async def get(doc_id):
    try:
        e, doc = DocumentService.get_by_id(doc_id)
        if not e:
            return get_data_error_result(message="Document not found!")

        b, n = File2DocumentService.get_storage_address(doc_id=doc_id)
        data = await asyncio.to_thread(settings.STORAGE_IMPL.get, b, n)
        response = await make_response(data)
        logging.info("开始下载pdf....")
        ext = re.search(r"\.([^.]+)$", doc.name.lower())
        ext = ext.group(1) if ext else None
        if ext:
            if doc.type == FileType.VISUAL.value:

                content_type = CONTENT_TYPE_MAP.get(ext, f"image/{ext}")
            else:
                content_type = CONTENT_TYPE_MAP.get(ext, f"application/{ext}")
            response.headers.set("Content-Type", content_type)
        return response
    except Exception as e:
        return server_error_response(e)


@manager.route("/download/<attachment_id>", methods=["GET"])  # noqa: F821
@login_required
async def download_attachment(attachment_id):
    try:
        ext = request.args.get("ext", "markdown")
        bucket = request.args.get("bucket", current_user.id)
        key = attachment_id
        try:
            pad = 4 - len(attachment_id) % 4
            if pad != 4:
                key = attachment_id + ("=" * pad)
            decoded = base64.urlsafe_b64decode(key)
            key = decoded.decode("utf-8")
        except Exception:
            pass
        data = await asyncio.to_thread(settings.STORAGE_IMPL.get, bucket, key)
        response = await make_response(data)
        response.headers.set("Content-Type", CONTENT_TYPE_MAP.get(ext, f"application/{ext}"))

        return response

    except Exception as e:
        return server_error_response(e)

# 代码功能同上，去除鉴权需求，用于下载图片链接
@manager.route("/public_download/<attachment_id>", methods=["GET"])  # noqa: F821
async def public_download_attachment(attachment_id):
    try:
        ext = request.args.get("ext", "markdown") 
        bucket = request.args.get("bucket", "")  
        key = attachment_id 
        try:
            pad = 4 - len(attachment_id) % 4  
            if pad != 4: 
                key = attachment_id + ("=" * pad) 
            decoded = base64.urlsafe_b64decode(key)  
            key = decoded.decode("utf-8")  
        except Exception:
            pass
        data = await asyncio.to_thread(settings.STORAGE_IMPL.get, bucket, key) 
        response = await make_response(data) 
        response.headers.set("Content-Type", CONTENT_TYPE_MAP.get(ext, f"application/{ext}")) 

        return response

    except Exception as e:
        return server_error_response(e) 


@manager.route("/change_parser", methods=["POST"])  # noqa: F821
@login_required
@validate_request("doc_id")
async def change_parser():

    req = await get_request_json()
    if not DocumentService.accessible(req["doc_id"], current_user.id):
        return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)

    e, doc = DocumentService.get_by_id(req["doc_id"])
    if not e:
        return get_data_error_result(message="Document not found!")

    def reset_doc():
        nonlocal doc
        e = DocumentService.update_by_id(doc.id, {"pipeline_id": req["pipeline_id"], "parser_id": req["parser_id"], "progress": 0, "progress_msg": "", "run": TaskStatus.UNSTART.value})
        if not e:
            return get_data_error_result(message="Document not found!")
        if doc.token_num > 0:
            e = DocumentService.increment_chunk_num(doc.id, doc.kb_id, doc.token_num * -1, doc.chunk_num * -1, doc.process_duration * -1)
            if not e:
                return get_data_error_result(message="Document not found!")
            tenant_id = DocumentService.get_tenant_id(req["doc_id"])
            if not tenant_id:
                return get_data_error_result(message="Tenant not found!")
            DocumentService.delete_chunk_images(doc, tenant_id)
            if settings.docStoreConn.index_exist(search.index_name(tenant_id), doc.kb_id):
                settings.docStoreConn.delete({"doc_id": doc.id}, search.index_name(tenant_id), doc.kb_id)
        return None

    try:
        if "pipeline_id" in req and req["pipeline_id"] != "":
            if doc.pipeline_id == req["pipeline_id"]:
                return get_json_result(data=True)
            DocumentService.update_by_id(doc.id, {"pipeline_id": req["pipeline_id"]})
            reset_doc()
            return get_json_result(data=True)

        if doc.parser_id.lower() == req["parser_id"].lower():
            if "parser_config" in req:
                if req["parser_config"] == doc.parser_config:
                    return get_json_result(data=True)
            else:
                return get_json_result(data=True)

        if (doc.type == FileType.VISUAL and req["parser_id"] != "picture") or (re.search(r"\.(ppt|pptx|pages)$", doc.name) and req["parser_id"] != "presentation"):
            return get_data_error_result(message="Not supported yet!")
        if "parser_config" in req:
            DocumentService.update_parser_config(doc.id, req["parser_config"])
        reset_doc()
        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)


@manager.route("/image/<image_id>", methods=["GET"])  # noqa: F821
# @login_required
async def get_image(image_id):
    try:
        arr = image_id.split("-")
        if len(arr) != 2:
            return get_data_error_result(message="Image not found.")
        bkt, nm = image_id.split("-")
        data = await asyncio.to_thread(settings.STORAGE_IMPL.get, bkt, nm)
        response = await make_response(data)
        response.headers.set("Content-Type", "image/JPEG")
        return response
    except Exception as e:
        return server_error_response(e)


@manager.route("/upload_and_parse", methods=["POST"])  # noqa: F821
@login_required
@validate_request("conversation_id")
async def upload_and_parse():
    files = await request.files
    if "file" not in files:
        return get_json_result(data=False, message="No file part!", code=RetCode.ARGUMENT_ERROR)

    file_objs = files.getlist("file")
    for file_obj in file_objs:
        if file_obj.filename == "":
            return get_json_result(data=False, message="No file selected!", code=RetCode.ARGUMENT_ERROR)

    form = await request.form
    doc_ids = doc_upload_and_parse(form.get("conversation_id"), file_objs, current_user.id)
    return get_json_result(data=doc_ids)


@manager.route("/parse", methods=["POST"])  # noqa: F821
@login_required
async def parse():
    req = await get_request_json()
    url = req.get("url", "")
    if url:
        if not is_valid_url(url):
            return get_json_result(data=False, message="The URL format is invalid", code=RetCode.ARGUMENT_ERROR)
        download_path = os.path.join(get_project_base_directory(), "logs/downloads")
        os.makedirs(download_path, exist_ok=True)
        from seleniumwire.webdriver import Chrome, ChromeOptions

        options = ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_experimental_option("prefs", {"download.default_directory": download_path, "download.prompt_for_download": False, "download.directory_upgrade": True, "safebrowsing.enabled": True})
        driver = Chrome(options=options)
        driver.get(url)
        res_headers = [r.response.headers for r in driver.requests if r and r.response]
        if len(res_headers) > 1:
            sections = RAGFlowHtmlParser().parser_txt(driver.page_source)
            driver.quit()
            return get_json_result(data="\n".join(sections))

        class File:
            filename: str
            filepath: str

            def __init__(self, filename, filepath):
                self.filename = filename
                self.filepath = filepath

            def read(self):
                with open(self.filepath, "rb") as f:
                    return f.read()

        r = re.search(r"filename=\"([^\"]+)\"", str(res_headers))
        if not r or not r.group(1):
            return get_json_result(data=False, message="Can't not identify downloaded file", code=RetCode.ARGUMENT_ERROR)
        f = File(r.group(1), os.path.join(download_path, r.group(1)))
        txt = FileService.parse_docs([f], current_user.id)
        return get_json_result(data=txt)

    files = await request.files
    if "file" not in files:
        return get_json_result(data=False, message="No file part!", code=RetCode.ARGUMENT_ERROR)

    file_objs = files.getlist("file")
    txt = FileService.parse_docs(file_objs, current_user.id)

    return get_json_result(data=txt)


@manager.route("/set_meta", methods=["POST"])  # noqa: F821
@login_required
@validate_request("doc_id", "meta")
async def set_meta():
    req = await get_request_json()
    if not DocumentService.accessible(req["doc_id"], current_user.id):
        return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)
    try:
        meta = json.loads(req["meta"])
        if not isinstance(meta, dict):
            return get_json_result(data=False, message="Only dictionary type supported.", code=RetCode.ARGUMENT_ERROR)
        for k, v in meta.items():
            if isinstance(v, list):
                if not all(isinstance(i, (str, int, float)) for i in v):
                    return get_json_result(data=False, message=f"The type is not supported in list: {v}", code=RetCode.ARGUMENT_ERROR)
            elif not isinstance(v, (str, int, float)):
                return get_json_result(data=False, message=f"The type is not supported: {v}", code=RetCode.ARGUMENT_ERROR)
    except Exception as e:
        return get_json_result(data=False, message=f"Json syntax error: {e}", code=RetCode.ARGUMENT_ERROR)
    if not isinstance(meta, dict):
        return get_json_result(data=False, message='Meta data should be in Json map format, like {"key": "value"}', code=RetCode.ARGUMENT_ERROR)

    try:
        e, doc = DocumentService.get_by_id(req["doc_id"])
        if not e:
            return get_data_error_result(message="Document not found!")

        if not DocumentService.update_by_id(req["doc_id"], {"meta_fields": meta}):
            return get_data_error_result(message="Database error (meta updates)!")

        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)

@manager.route("/upload_info", methods=["POST"])  # noqa: F821
async def upload_info():
    files = await request.files
    file = files['file'] if files and files.get("file") else None
    try:
        return get_json_result(data=FileService.upload_info(current_user.id, file, request.args.get("url")))
    except Exception as e:
        return  server_error_response(e)


@manager.route("/mineru_parse", methods=["POST"])  # noqa: F821
@login_required
async def mineru_parse():
    try:
        form = await request.form
        files_data = await request.files
        has_file = "file" in files_data and files_data["file"] and getattr(files_data["file"], "filename", "") != ""
        doc_id = (form.get("doc_id") or "").strip()
        kb_id = (form.get("kb_id") or "").strip()
        has_doc_kb = bool(doc_id and kb_id)

        if not has_file and has_doc_kb:
            e, kb = KnowledgebaseService.get_by_id(kb_id)
            if not e:
                return get_json_result(data=False, message="知识库不存在", code=RetCode.NOT_FOUND)
            check_kb_team_permission(kb, current_user.id)
            e, doc = DocumentService.get_by_id(doc_id)
            if not e or not doc:
                return get_json_result(data=False, message="文档不存在", code=RetCode.NOT_FOUND)
            if str(doc.kb_id) != str(kb_id):
                return get_json_result(data=False, message="文档不属于该知识库", code=RetCode.ARGUMENT_ERROR)
            content_list_location = f"{doc_id}/content_list.json"
            if not settings.STORAGE_IMPL.obj_exist(kb_id, content_list_location):
                return get_json_result(
                    data=False,
                    message="该文档暂无 MinerU 解析产物（未解析或非 MinerU 解析）",
                    code=RetCode.NOT_FOUND
                )
            def _minio_path(bkt, key):
                return f"{bkt}/{key}"

            content_list_url = _minio_path(kb_id, content_list_location)
            markdown_url = None
            image_urls = []
            pdf_minio_path = None
            list_fn = getattr(settings.STORAGE_IMPL, "list_objects", None)
            if callable(list_fn):
                keys = list_fn(kb_id, f"{doc_id}/")
                image_extensions = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")
                pdf_extensions = (".pdf",)
                for key in keys:
                    key_lower = key.lower()
                    if key_lower.endswith(".md") and markdown_url is None:
                        markdown_url = _minio_path(kb_id, key)
                    elif any(key_lower.endswith(ext) for ext in image_extensions):
                        image_urls.append({
                            "url": _minio_path(kb_id, key),
                            "path": key,
                            "filename": Path(key).name,
                            "location": key,
                            "size": 0,
                            "source_key": "image",
                            "content_type": "image",
                            "page_idx": -1,
                        })
                    elif any(key_lower.endswith(ext) for ext in pdf_extensions) and pdf_minio_path is None:
                        pdf_minio_path = _minio_path(kb_id, key)
            try:
                content_list_bin = await asyncio.to_thread(settings.STORAGE_IMPL.get, kb_id, content_list_location)
                content_list = json.loads((content_list_bin or b"[]").decode("utf-8")) if content_list_bin else []
            except Exception:
                content_list = []
            
            return get_json_result(data={
                "content_list_url": content_list_url,
                "markdown_url": markdown_url,
                "image_urls": image_urls,
                "image_count": len(image_urls),
                "count": len(content_list),
                "source": "kb_doc",
                "pdf_minio_path": pdf_minio_path,
            })

        if not has_file:
            return get_json_result(
                data=False,
                message="请提供 PDF 文件（file）或文档 id 与知识库 id（doc_id、kb_id）",
                code=RetCode.ARGUMENT_ERROR
            )
        mineru_api = os.environ.get("MINERU_APISERVER", "").rstrip("/")
        if not mineru_api:
            return get_json_result(
                data=False,
                message="MinerU API server not configured. Please set MINERU_APISERVER environment variable.",
                code=RetCode.SERVER_ERROR
            )

        file_obj = files_data["file"]
        if hasattr(file_obj, 'seek'):
            file_obj.seek(0)
        file_content = await asyncio.to_thread(file_obj.read)
        
        user_id = current_user.id
        parse_id = get_uuid()
        
        pdf_minio_path = None
        try:
            pdf_location = f"mineru_parse/{parse_id}/original_{file_obj.filename}"
            settings.STORAGE_IMPL.put(user_id, pdf_location, file_content)
            pdf_minio_path = f"{user_id}/{pdf_location}"
        except Exception:
            pass
        
        if hasattr(file_obj, 'seek'):
            file_obj.seek(0)
        
        files = {
            "files": (
                file_obj.filename,
                file_content,
                "application/pdf"
            )
        }
        data = {
            "output_dir": form.get("output_dir", "./output"),
            "lang_list": form.get("lang_list") or None, 
            "backend": form.get("backend", "pipeline"),
            "parse_method": form.get("parse_method", "auto"), 
            "formula_enable": form.get("formula_enable", "true").lower() == "true", 
            "table_enable": form.get("table_enable", "true").lower() == "true", 
            "server_url": form.get("server_url") or None, 
            "return_md": form.get("return_md", "true").lower() == "true", 
            "return_middle_json": form.get("return_middle_json", "true").lower() == "true", 
            "return_model_output": form.get("return_model_output", "true").lower() == "true", 
            "return_content_list": form.get("return_content_list", "true").lower() == "true",
            "return_images": form.get("return_images", "true").lower() == "true", 
            "response_format_zip": form.get("response_format_zip", "true").lower() == "true", 
            "start_page_id": int(form.get("start_page_id", 0)), 
            "end_page_id": int(form.get("end_page_id", 99999)), 
        }

        if not data["server_url"]:
            mineru_server_url = os.environ.get("MINERU_SERVER_URL", "").rstrip("/")
            if mineru_server_url:
                data["server_url"] = mineru_server_url

        headers = {"Accept": "application/json"}
        mineru_api_url = f"{mineru_api}/file_parse"
        response = requests.post(
            url=mineru_api_url,
            files=files,
            data=data,
            headers=headers,
            timeout=1800 
        )

        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        
        def _process_mineru_zip_response(zip_content: bytes, original_filename: str, user_id: str, parse_id: str, pdf_path: str = None, kb_id: str | None = None, doc_id: str | None = None) -> dict:
            temp_dir = tempfile.mkdtemp(prefix="mineru_parse_")
            zip_path = os.path.join(temp_dir, "response.zip")
            extract_dir = os.path.join(temp_dir, "extracted")
            
            try:
                base_prefix = f"mineru_parse/{parse_id}"
                
                with open(zip_path, "wb") as f:
                    f.write(zip_content)
                
                os.makedirs(extract_dir, exist_ok=True)
                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                extract_path = Path(extract_dir)
                content_list = None
                content_list_file = None
                file_stem = Path(original_filename).stem.replace(" ", "")
                
                possible_names = [
                    f"{file_stem}_content_list.json",
                    f"{Path(original_filename).stem}_content_list.json",
                ]
                
                for name in possible_names:
                    for json_file in extract_path.rglob(name):
                        with open(json_file, "r", encoding="utf-8") as f:
                            content_list = json.load(f)
                            content_list_file = json_file
                            break
                    if content_list:
                        break
                
                if not content_list:
                    for json_file in extract_path.rglob("*_content_list.json"):
                        with open(json_file, "r", encoding="utf-8") as f:
                            content_list = json.load(f)
                            content_list_file = json_file
                            break

                _PUBLIC_DOWNLOAD_PREFIX = "/v1/document/public_download"
                _IMG_KEYS_NORM = ("img_path", "table_img_path", "equation_img_path")
                def _normalize_download_to_public(obj):
                    if isinstance(obj, dict):
                        for k in list(obj.keys()):
                            if k in _IMG_KEYS_NORM and obj[k] and isinstance(obj[k], str) and "/v1/document/download/" in obj[k]:
                                obj[k] = obj[k].replace("/v1/document/download/", f"{_PUBLIC_DOWNLOAD_PREFIX}/", 1)
                            else:
                                _normalize_download_to_public(obj[k])
                    elif isinstance(obj, list):
                        for v in obj:
                            _normalize_download_to_public(v)
                if content_list:
                    for item in content_list:
                        _normalize_download_to_public(item)
                
                content_list_url = None
                markdown_url = None
                markdown_file = None
                for md_file in extract_path.rglob("*.md"):
                    markdown_file = md_file
                    with open(md_file, "r", encoding="utf-8") as f:
                        markdown_content = f.read()

                        markdown_location = f"{base_prefix}/{md_file.name}"
                        settings.STORAGE_IMPL.put(user_id, markdown_location, markdown_content.encode("utf-8"))

                        if kb_id and doc_id:
                            kb_md_location = f"{doc_id}/{md_file.name}"
                            settings.STORAGE_IMPL.put(kb_id, kb_md_location, markdown_content.encode("utf-8"))

                        markdown_location_encoded = base64.urlsafe_b64encode(markdown_location.encode("utf-8")).decode("utf-8").rstrip("=")
                        markdown_url = f"/v1/document/download/{markdown_location_encoded}?ext=markdown"
                        break
                
                image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
                processed_image_paths = set()
                image_files_to_upload = []
                img_path_to_url: dict[str, str] = {}
                
                def _collect_img_paths(obj):
                    if isinstance(obj, dict):
                        for k in list(obj.keys()):
                            if k in ("img_path", "table_img_path", "equation_img_path") and obj[k] and isinstance(obj[k], str):
                                yield obj[k]
                            else:
                                yield from _collect_img_paths(obj[k])
                    elif isinstance(obj, list):
                        for v in obj:
                            yield from _collect_img_paths(v)

                if content_list and content_list_file:
                    for item in content_list:
                        for img_path_str in _collect_img_paths(item):
                            if os.path.isabs(img_path_str):
                                img_path = Path(img_path_str)
                            else:
                                img_path = content_list_file.parent / img_path_str
                            if not img_path.exists():
                                img_filename = Path(img_path_str).name
                                found_img = None
                                for possible_img in extract_path.rglob(img_filename):
                                    found_img = possible_img
                                    break
                                if found_img:
                                    img_path = found_img
                            if img_path.exists() and img_path.is_file() and img_path.suffix.lower() in image_extensions:
                                img_relative_path = str(img_path.relative_to(extract_path))
                                if img_relative_path not in processed_image_paths:
                                    processed_image_paths.add(img_relative_path)
                                    image_files_to_upload.append({
                                        "path": img_path,
                                        "relative_path": img_relative_path,
                                        "source_key": "image",
                                        "content_type": "image",
                                        "page_idx": -1
                                    })
                
                for img_file in extract_path.rglob("*"):
                    if img_file.is_file() and img_file.suffix.lower() in image_extensions:
                        img_relative_path = str(img_file.relative_to(extract_path))
                        
                        if img_relative_path not in processed_image_paths:
                            processed_image_paths.add(img_relative_path)
                            image_files_to_upload.append({
                                "path": img_file,
                                "relative_path": img_relative_path,
                                "source_key": "standalone",
                                "content_type": "image",
                                "page_idx": -1
                            })
                
                image_urls = []
                for img_info in image_files_to_upload:
                    img_path = img_info["path"]
                    img_filename = img_path.name
                    
                    with open(img_path, "rb") as img_file:
                        img_data = img_file.read()
                    
                    img_location = f"{base_prefix}/images/{img_filename}"
                    settings.STORAGE_IMPL.put(user_id, img_location, img_data)

                    if kb_id and doc_id:
                        kb_img_location = f"{doc_id}/images/{img_filename}"
                        settings.STORAGE_IMPL.put(kb_id, kb_img_location, img_data)
                    
                    img_location_encoded = base64.urlsafe_b64encode(img_location.encode("utf-8")).decode("utf-8").rstrip("=")
                    img_url = f"{_PUBLIC_DOWNLOAD_PREFIX}/{img_location_encoded}?ext={img_path.suffix[1:] if img_path.suffix else 'png'}&bucket={user_id}"
                    img_path_to_url[img_info["relative_path"]] = img_url
                    img_path_to_url[img_filename] = img_url
                    image_urls.append({
                        "url": img_url,
                        "path": img_info["relative_path"],
                        "filename": img_filename,
                        "location": img_location,
                        "size": len(img_data),
                        "source_key": img_info["source_key"],
                        "content_type": img_info["content_type"],
                        "page_idx": img_info["page_idx"]
                    })
                
                IMG_KEYS = ("img_path", "table_img_path", "equation_img_path")
                _IMG_KEY_SET = {k.lower() for k in IMG_KEYS}

                def _replace_img_paths_in_obj(obj):
                    if isinstance(obj, dict):
                        for k in list(obj.keys()):
                            if (k in IMG_KEYS or k.lower() in _IMG_KEY_SET) and obj[k] and isinstance(obj[k], str):
                                raw_val = str(obj[k]).strip()
                                cands = [raw_val, raw_val.replace("\\", "/"), str(Path(raw_val).name)]
                                replaced = False
                                for ck in cands:
                                    if ck and ck in img_path_to_url:
                                        obj[k] = img_path_to_url[ck]
                                        replaced = True
                                        break
                                if not replaced:
                                    for part in raw_val.replace("\\", "/").split("/"):
                                        if part and any(part.lower().endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")):
                                            if part in img_path_to_url:
                                                obj[k] = img_path_to_url[part]
                                                replaced = True
                                            break
                            else:
                                _replace_img_paths_in_obj(obj[k])
                    elif isinstance(obj, list):
                        for v in obj:
                            _replace_img_paths_in_obj(v)

                if content_list:
                    for item in content_list:
                        _replace_img_paths_in_obj(item)

                def _normalize_to_public_download(obj):
                    if isinstance(obj, dict):
                        for k in list(obj.keys()):
                            if k in IMG_KEYS and obj[k] and isinstance(obj[k], str) and "/v1/document/download/" in obj[k]:
                                obj[k] = obj[k].replace("/v1/document/download/", f"{_PUBLIC_DOWNLOAD_PREFIX}/", 1)
                            else:
                                _normalize_to_public_download(obj[k])
                    elif isinstance(obj, list):
                        for v in obj:
                            _normalize_to_public_download(v)

                if content_list:
                    for item in content_list:
                        _normalize_to_public_download(item)

                if content_list and content_list_file:
                    content_list_location = f"{base_prefix}/content_list.json"
                    content_list_json_str = json.dumps(content_list, ensure_ascii=False, indent=2)
                    settings.STORAGE_IMPL.put(user_id, content_list_location, content_list_json_str.encode("utf-8"))

                    if kb_id and doc_id:
                        kb_json_location = f"{doc_id}/content_list.json"
                        settings.STORAGE_IMPL.put(kb_id, kb_json_location, content_list_json_str.encode("utf-8"))

                    content_list_location_encoded = base64.urlsafe_b64encode(content_list_location.encode("utf-8")).decode("utf-8").rstrip("=")
                    content_list_url = f"/v1/document/download/{content_list_location_encoded}?ext=json"
                
                result = {
                    "content_list_url": content_list_url,
                    "markdown_url": markdown_url,
                    "image_urls": image_urls,
                    "image_count": len(image_urls),
                    "count": len(content_list) if content_list else 0,
                    "source": "file_parse",
                    "pdf_minio_path": pdf_path,
                }
                return result
                
            except Exception as e:
                return {
                    "content_list_url": None,
                    "markdown_url": None,
                    "image_urls": [],
                    "image_count": 0,
                    "count": 0,
                    "pdf_minio_path": pdf_path,
                    "error": f"Failed to process ZIP response: {str(e)}"
                }
            finally:
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception:
                    pass        

        if "application/zip" in content_type:
            result_data = await asyncio.to_thread(
                _process_mineru_zip_response,
                response.content,
                file_obj.filename,
                user_id,
                parse_id,
                pdf_minio_path,
                kb_id if has_doc_kb else None,
                doc_id if has_doc_kb else None,
            )
            if has_doc_kb:
                try:
                    await _classify_voucher_type_for_mineru_doc(kb_id, doc_id)
                except Exception as e:
                    logging.warning("[voucher_type_llm] MinerU 回写分类失败 doc_id=%s err=%s", doc_id, e)
            return get_json_result(data=result_data)
        else:
            try:
                json_data = response.json()
                if isinstance(json_data, dict):
                    json_data["pdf_minio_path"] = pdf_minio_path
                return get_json_result(data=json_data)
            except json.JSONDecodeError:
                return get_json_result(data={"content": response.text, "pdf_minio_path": pdf_minio_path})

    except requests.exceptions.RequestException as e:
        return get_json_result(
            data=False,
            message=f"MinerU API request failed: {str(e)}",
            code=RetCode.SERVER_ERROR
        )
    except Exception as e:
        return server_error_response(e)


@manager.route("/mineru_download/<file_type>", methods=["GET"])  # noqa: F821
@login_required
async def mineru_download(file_type):
    try:
        kb_id_raw = request.args.get("kb_id")
        doc_id_raw = request.args.get("doc_id")
        
        kb_id = (kb_id_raw or "").strip() if kb_id_raw is not None else ""
        doc_id = (doc_id_raw or "").strip() if doc_id_raw is not None else ""
        file_type = (file_type or "").strip().lower()

        if not kb_id or not doc_id:
            missing_params = []
            if not kb_id:
                missing_params.append("kb_id")
            if not doc_id:
                missing_params.append("doc_id")
            received_params = list(request.args.keys())
            return get_json_result(
                data=False,
                message=f"请提供知识库ID（kb_id）和文档ID（doc_id）。缺少参数：{', '.join(missing_params)}。"
                       f"当前接收到的查询参数：{', '.join(received_params) if received_params else '无'}。"
                       f"请确保使用 GET 请求，并将 kb_id 和 doc_id 作为 URL 查询参数传递，例如："
                       f"/v1/document/mineru_download/json?kb_id=xxx&doc_id=yyy",
                code=RetCode.ARGUMENT_ERROR
            )

        valid_file_types = ["json", "markdown", "pdf"]
        if file_type not in valid_file_types:
            return get_json_result(
                data=False,
                message=f"文件类型必须是以下之一：{', '.join(valid_file_types)}",
                code=RetCode.ARGUMENT_ERROR
            )

        e, kb = KnowledgebaseService.get_by_id(kb_id)
        if not e:
            return get_json_result(data=False, message="知识库不存在", code=RetCode.NOT_FOUND)
        check_kb_team_permission(kb, current_user.id)

        e, doc = DocumentService.get_by_id(doc_id)
        if not e or not doc:
            return get_json_result(data=False, message="文档不存在", code=RetCode.NOT_FOUND)
        if str(doc.kb_id) != str(kb_id):
            return get_json_result(data=False, message="文档不属于该知识库", code=RetCode.ARGUMENT_ERROR)

        file_location = None
        list_fn = getattr(settings.STORAGE_IMPL, "list_objects", None)
        if callable(list_fn):
            keys = list_fn(kb_id, f"{doc_id}/")

            if file_type == "json":
                target_file = f"{doc_id}/content_list.json"
                if settings.STORAGE_IMPL.obj_exist(kb_id, target_file):
                    file_location = target_file
            elif file_type == "markdown":
                for key in keys:
                    if key.lower().endswith(".md"):
                        file_location = key
                        break
            elif file_type == "pdf":
                for key in keys:
                    if key.lower().endswith(".pdf"):
                        file_location = key
                        break

        if not file_location:
            return get_json_result(
                data=False,
                message=f"未找到该文档的 {file_type} 文件",
                code=RetCode.NOT_FOUND
            )

        file_content = await asyncio.to_thread(settings.STORAGE_IMPL.get, kb_id, file_location)
        if file_content is None or len(file_content) == 0:
            return get_json_result(
                data=False,
                message="文件读取失败或文件为空",
                code=RetCode.SERVER_ERROR
            )

        download_filename = Path(file_location).name
        if not download_filename:
            download_filename = {"json": "content_list.json", "markdown": "document.md", "pdf": "document.pdf"}.get(file_type, "download")

        ext_for_type = {"json": "json", "markdown": "markdown", "pdf": "pdf"}
        ext = ext_for_type.get(file_type, file_type)
        content_type = CONTENT_TYPE_MAP.get(ext, f"application/{ext}")

        response = await make_response(file_content)
        response.headers.set("Content-Type", content_type)
        response.headers.set(
            "Content-Disposition",
            f"attachment; filename*=UTF-8''{quote(download_filename)}"
        )
        return response

    except Exception as e:
        return server_error_response(e)


@manager.route("/mineru_section/update", methods=["POST"])  # noqa: F821
@login_required
@validate_request("chunk_id", "type", "text")
async def update_mineru_section():
    try:
        req = await get_request_json()
        chunk_id = (req.get("chunk_id") or "").strip()
        req_type = (req.get("type") or "").strip().lower()
        text = req.get("text")
        valid_types = ("text", "table_caption", "table_footnote", "table_body")
        if req_type not in valid_types:
            return get_json_result(
                data=False,
                message="type 仅支持 text、table_caption、table_footnote、table_body",
                code=RetCode.ARGUMENT_ERROR,
            )

        section = DocumentService.get_mineru_section_by_chunk_id(chunk_id)
        if not section:
            return get_json_result(
                data=False,
                message="未找到对应 chunk_id 的 mineru_section 记录",
                code=RetCode.NOT_FOUND,
            )

        e, kb = KnowledgebaseService.get_by_id(section.kb_id)
        if not e:
            return get_json_result(
                data=False,
                message="知识库不存在",
                code=RetCode.NOT_FOUND,
            )
        check_kb_team_permission(kb, current_user.id)

        ok, msg, data = DocumentService.update_mineru_section_content_by_chunk_id(
            chunk_id,
            req_type,
            text,
        )
        if not ok:
            return get_json_result(
                data=False,
                message=msg or "更新 mineru_section 失败",
                code=RetCode.SERVER_ERROR,
            )
        return get_json_result(data=data)
    except Exception as e:
        return server_error_response(e)


def _mineru_json_list_or_empty(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, list) else [parsed]
        except Exception:
            return [text]
    return [value]


def _convert_mineru_row_to_content_item(row):
    row_type = str(row.get("type") or "").strip() or "unknown"
    row_type_norm = row_type.lower()
    item = {
        "type": row_type,
        "chunk_id": str(row.get("chunk_id") or "").strip(),
        "bbox": row.get("bbox"),
        "page_idx": row.get("page_idx"),
    }

    if row_type_norm == "text":
        if row.get("text") is not None:
            item["text"] = row.get("text")
        if row.get("text_level") is not None:
            item["text_level"] = row.get("text_level")
        if row.get("img_path"):
            item["img_path"] = row.get("img_path")
        return item

    if row_type_norm == "image":
        if row.get("img_path"):
            item["img_path"] = row.get("img_path")
        item["image_caption"] = _mineru_json_list_or_empty(None)
        item["image_footnote"] = _mineru_json_list_or_empty(None)
        if row.get("text"):
            item["text"] = row.get("text")
        return item

    if row_type_norm == "table":
        if row.get("img_path"):
            item["img_path"] = row.get("img_path")
        item["table_caption"] = _mineru_json_list_or_empty(row.get("table_caption"))
        item["table_footnote"] = _mineru_json_list_or_empty(row.get("table_footnote"))
        if row.get("table_body") is not None:
            item["table_body"] = row.get("table_body")
        return item

    if row_type_norm == "table_caption":
        table_caption = row.get("table_caption")
        if table_caption is None and row.get("text"):
            table_caption = row.get("text")
        item["table_caption"] = _mineru_json_list_or_empty(table_caption)
        if row.get("img_path"):
            item["img_path"] = row.get("img_path")
        return item

    if row_type_norm == "table_footnote":
        table_footnote = row.get("table_footnote")
        if table_footnote is None and row.get("text"):
            table_footnote = row.get("text")
        item["table_footnote"] = _mineru_json_list_or_empty(table_footnote)
        if row.get("img_path"):
            item["img_path"] = row.get("img_path")
        return item

    if row_type_norm == "table_body":
        table_body_text = row.get("table_body")
        if table_body_text is None:
            table_body_text = row.get("text")
        if table_body_text is not None:
            item["text"] = table_body_text
        if row.get("img_path"):
            item["img_path"] = row.get("img_path")
        return item

    if row_type_norm in ("equation", "header", "page_number", "discarded"):
        if row.get("text") is not None:
            item["text"] = row.get("text")
        if row.get("img_path"):
            item["img_path"] = row.get("img_path")
        return item

    if row_type_norm == "code":
        if row.get("text") is not None:
            item["code_body"] = row.get("text")
        if row.get("img_path"):
            item["img_path"] = row.get("img_path")
        return item

    if row_type_norm == "list":
        item["list_items"] = _mineru_json_list_or_empty(row.get("list_items"))
        if row.get("text"):
            item["text"] = row.get("text")
        if row.get("img_path"):
            item["img_path"] = row.get("img_path")
        return item

    if row.get("text") is not None:
        item["text"] = row.get("text")
    if row.get("img_path"):
        item["img_path"] = row.get("img_path")
    if row.get("sub_type"):
        item["sub_type"] = row.get("sub_type")
    if row.get("list_items") is not None:
        item["list_items"] = _mineru_json_list_or_empty(row.get("list_items"))
    return item


@manager.route("/mineru_section/submit", methods=["POST"])  # noqa: F821
@login_required
@validate_request("kb_id", "doc_id")
async def submit_mineru_section():
    temp_file_path = None
    temp_file = None
    try:
        req = await get_request_json()
        kb_id = (req.get("kb_id") or "").strip()
        doc_id = (req.get("doc_id") or "").strip()
        if not kb_id or not doc_id:
            return get_json_result(data=False, message="kb_id 或 doc_id 不能为空", code=RetCode.ARGUMENT_ERROR)

        try:
            batch_size = int(req.get("batch_size") or 500)
        except Exception:
            return get_json_result(data=False, message="batch_size 必须为整数", code=RetCode.ARGUMENT_ERROR)
        if batch_size <= 0 or batch_size > 5000:
            return get_json_result(data=False, message="batch_size 取值范围应为 1-5000", code=RetCode.ARGUMENT_ERROR)

        e, kb = KnowledgebaseService.get_by_id(kb_id)
        if not e:
            return get_json_result(data=False, message="知识库不存在", code=RetCode.NOT_FOUND)
        if not check_kb_team_permission(kb, current_user.id):
            return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)

        e, doc = DocumentService.get_by_id(doc_id)
        if not e:
            return get_json_result(data=False, message="文档不存在", code=RetCode.NOT_FOUND)
        if str(doc.kb_id) != kb_id:
            return get_json_result(data=False, message="doc_id 不属于当前知识库", code=RetCode.ARGUMENT_ERROR)

        first_page = DocumentService.list_mineru_sections_page(kb_id=kb_id, doc_id=doc_id, offset=0, limit=batch_size)
        if not first_page:
            return get_json_result(data=False, message="未找到可提交的 mineru_section 数据", code=RetCode.NOT_FOUND)

        target_key = f"{doc_id}/content_list.json"
        temp_file = tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".json")
        temp_file_path = temp_file.name
        temp_file.write(b"[")

        offset = 0
        record_count = 0
        is_first = True
        while True:
            rows = first_page if offset == 0 else DocumentService.list_mineru_sections_page(
                kb_id=kb_id,
                doc_id=doc_id,
                offset=offset,
                limit=batch_size,
            )
            if not rows:
                break
            for row in rows:
                item = _convert_mineru_row_to_content_item(row)
                if is_first:
                    temp_file.write(json.dumps(item, ensure_ascii=False).encode("utf-8"))
                    is_first = False
                else:
                    temp_file.write(b",")
                    temp_file.write(json.dumps(item, ensure_ascii=False).encode("utf-8"))
                record_count += 1
            offset += len(rows)
            if len(rows) < batch_size:
                break

        temp_file.write(b"]")
        temp_file.flush()
        temp_file.close()
        temp_file = None

        with open(temp_file_path, "rb") as f:
            payload = f.read()
        settings.STORAGE_IMPL.put(kb_id, target_key, payload)

        return get_json_result(data={
            "kb_id": kb_id,
            "doc_id": doc_id,
            "target_path": target_key,
            "record_count": record_count,
            "batch_size": batch_size,
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
                logging.warning("[MinerU] 清理临时 content_list 文件失败: %s", temp_file_path)



# 新增凭证列表
@manager.route("/identity_list", methods=["POST"]) 
@login_required
async def identity_list_docs():
    kb_id = request.args.get("kb_id")
    if not kb_id:
        return get_json_result(data=False, message='Lack of "KB ID"', code=RetCode.ARGUMENT_ERROR)
    tenants = UserTenantService.query(user_id=current_user.id)
    for tenant in tenants:
        if KnowledgebaseService.query(tenant_id=tenant.tenant_id, id=kb_id):
            break
    else:
        return get_json_result(data=False, message="Only owner of dataset authorized for this operation.", code=RetCode.OPERATING_ERROR)
    keywords = request.args.get("keywords", "")

    page_number = int(request.args.get("page", 0))
    items_per_page = int(request.args.get("page_size", 0))
    orderby = request.args.get("orderby", "create_time")
    if request.args.get("desc", "true").lower() == "false":
        desc = False
    else:
        desc = True
    create_time_from = int(request.args.get("create_time_from", 0))
    create_time_to = int(request.args.get("create_time_to", 0))

    req = await get_request_json()

    return_empty_metadata = req.get("return_empty_metadata", False)
    if isinstance(return_empty_metadata, str):
        return_empty_metadata = return_empty_metadata.lower() == "true"

    run_status = req.get("run_status", [])
    if run_status:
        invalid_status = {s for s in run_status if s not in VALID_TASK_STATUS}
        if invalid_status:
            return get_data_error_result(message=f"Invalid filter run status conditions: {', '.join(invalid_status)}")

    types = req.get("types", [])
    if types:
        invalid_types = {t for t in types if t not in VALID_FILE_TYPES}
        if invalid_types:
            return get_data_error_result(message=f"Invalid filter conditions: {', '.join(invalid_types)} type{'s' if len(invalid_types) > 1 else ''}")

    suffix = req.get("suffix", [])
    metadata_condition = req.get("metadata_condition", {}) or {}
    metadata = req.get("metadata", {}) or {}
    if isinstance(metadata, dict) and metadata.get("empty_metadata"):
        return_empty_metadata = True
        metadata = {k: v for k, v in metadata.items() if k != "empty_metadata"}
    if return_empty_metadata:
        metadata_condition = {}
        metadata = {}
    else:
        if metadata_condition and not isinstance(metadata_condition, dict):
            return get_data_error_result(message="metadata_condition must be an object.")
        if metadata and not isinstance(metadata, dict):
            return get_data_error_result(message="metadata must be an object.")

    doc_ids_filter = None
    metas = None
    if metadata_condition or metadata:
        metas = DocumentService.get_flatted_meta_by_kbs([kb_id])

    if metadata_condition:
        doc_ids_filter = set(meta_filter(metas, convert_conditions(metadata_condition), metadata_condition.get("logic", "and")))
        if metadata_condition.get("conditions") and not doc_ids_filter:
            return get_json_result(data={"total": 0, "docs": []})

    if metadata:
        metadata_doc_ids = None
        for key, values in metadata.items():
            if not values:
                continue
            if not isinstance(values, list):
                values = [values]
            values = [str(v) for v in values if v is not None and str(v).strip()]
            if not values:
                continue
            key_doc_ids = set()
            for value in values:
                key_doc_ids.update(metas.get(key, {}).get(value, []))
            if metadata_doc_ids is None:
                metadata_doc_ids = key_doc_ids
            else:
                metadata_doc_ids &= key_doc_ids
            if not metadata_doc_ids:
                return get_json_result(data={"total": 0, "docs": []})
        if metadata_doc_ids is not None:
            if doc_ids_filter is None:
                doc_ids_filter = metadata_doc_ids
            else:
                doc_ids_filter &= metadata_doc_ids
            if not doc_ids_filter:
                return get_json_result(data={"total": 0, "docs": []})

    if doc_ids_filter is not None:
        doc_ids_filter = list(doc_ids_filter)

    try:
        docs, tol = DocumentService.get_by_kb_id(
            kb_id,
            page_number,
            items_per_page,
            orderby,
            desc,
            keywords,
            run_status,
            types,
            suffix,
            doc_ids_filter,
            return_empty_metadata=return_empty_metadata,
        )

        if create_time_from or create_time_to:
            filtered_docs = []
            for doc in docs:
                doc_create_time = doc.get("create_time", 0)
                if (create_time_from == 0 or doc_create_time >= create_time_from) and (create_time_to == 0 or doc_create_time <= create_time_to):
                    filtered_docs.append(doc)
            docs = filtered_docs

        for doc_item in docs:
            if doc_item["thumbnail"] and not doc_item["thumbnail"].startswith(IMG_BASE64_PREFIX):
                doc_item["thumbnail"] = f"/v1/document/image/{kb_id}-{doc_item['thumbnail']}"
            if doc_item.get("source_type"):
                doc_item["source_type"] = doc_item["source_type"].split("/")[0]

        return get_json_result(data={"total": tol, "docs": docs})
    except Exception as e:
        return server_error_response(e)

