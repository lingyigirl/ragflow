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
#  limitations under the License.
#
import asyncio
import datetime
import hashlib
import json
import logging
import pathlib
import re
import unicodedata
from copy import deepcopy
from io import BytesIO

import xxhash
from quart import request, send_file, jsonify
from peewee import OperationalError
from pydantic import BaseModel, Field, validator

from api.constants import FILE_NAME_LEN_LIMIT
from api.db import FileType
from api.db.db_models import File, Task
from api.db.services.document_service import DocumentService
from api.db.services.file2document_service import File2DocumentService
from api.db.services.file_service import FileService
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.llm_service import LLMBundle
from api.db.services.tenant_llm_service import TenantLLMService
from api.db.services.task_service import TaskService, queue_tasks, cancel_all_task_of
from common.metadata_utils import meta_filter, convert_conditions
from api.utils.api_utils import check_duplicate_ids, construct_json_result, get_error_data_result, get_parser_config, get_result, server_error_response, token_required, \
    get_request_json
from api.utils.file_utils import filename_type
from rag.app.qa import beAdoc, rmPrefix
from rag.app.tag import label_question
from rag.nlp import rag_tokenizer, search
from rag.prompts.generator import cross_languages, keyword_extraction
from common.string_utils import remove_redundant_spaces
from common.token_utils import num_tokens_from_string
from common.constants import RetCode, LLMType, ParserType, TaskStatus, FileSource
from common import settings

MAXIMUM_OF_UPLOADING_FILES = 256

_INVISIBLE_RE = re.compile(r"[​-‏⁠﻿ ]")

VALID_CHUNK_METHODS = {
    "naive",
    "manual",
    "qa",
    "table",
    "paper",
    "book",
    "laws",
    "presentation",
    "picture",
    "one",
    "knowledge_graph",
    "email",
    "tag",
    "hichunk",
}

BASIC_PDF_PARSERS = {"DeepDOC", "Plain Text"}
EXTENDED_PDF_PARSERS = {"MinerU", "Docling", "TCADP Parser"}

PDF_PARSER_CANONICAL_MAP = {
    "deepdoc": "DeepDOC",
    "plain text": "Plain Text",
    "plaintext": "Plain Text",
    "plain_text": "Plain Text",
    "mineru": "MinerU",
    "docling": "Docling",
    "tcadp parser": "TCADP Parser",
    "tcadp": "TCADP Parser",
}

DOC_TYPE_MAP = [
    ("financing_loan_details", "融资借款明细"),
    ("company_charter", "公司章程"),
    ("contract", "合同"),
    ("tax_payment_certificate", "完税凭证"),
    ("hydroelectricity_invoice", "水电发票"),
    ("executive_resume", "高管简历"),
    ("audit_report", "审计报告"),
    ("footnote", "附注"),
    ("financial_statements", "财务报表"),
    ("guarantor_enterprise_note", "担保企业附注"),
    ("bank_transaction_history", "银行交易流水"),
    ("credit_investigation_of_loan_applicant", "借款申请人征信"),
    ("credit_investigation_of_legal_representative", "法人代表征信"),
    ("credit_investigation_of_major_shareholders", "主要股东征信"),
    ("other", "其他"),
]


def compute_sha256_stream(file_obj):
    sha256_hash = hashlib.sha256()
    while chunk := file_obj.read(4096):
        sha256_hash.update(chunk)
    file_obj.seek(0)
    return sha256_hash.hexdigest()


async def _classify_document(chat_mdl, content_sample, filename):
    types_text = "\n".join([f"- {cn} - {en}" for en, cn in DOC_TYPE_MAP])
    system = "你是一个专业的文档分类助手，只返回JSON格式的结果，不要有任何其他内容。"
    prompt_template = f"""你是一个文档分类专家。请根据以下文档内容，判断文档类型，从以下类型列表中选择最匹配的一项：

类型列表(中文 - 英文):
{types_text}

请只返回一个JSON对象，格式如下：
{{"cn": "中文类型", "en": "english_type"}}

文档名称：{filename}
文档内容预览：
"""
    prompt_overhead = num_tokens_from_string(system) + num_tokens_from_string(prompt_template) + 500
    max_content_tokens = max(chat_mdl.max_length - prompt_overhead, 500)
    content_tokens = num_tokens_from_string(content_sample)
    if content_tokens > max_content_tokens:
        content_sample = content_sample[:int(max_content_tokens * 4)]
    prompt = prompt_template + content_sample
    history = [{"role": "user", "content": prompt}]
    response = await asyncio.wait_for(chat_mdl.async_chat(system, history), timeout=30)
    try:
        json_match = re.search(r'\{[^{}]*\}', response)
        if json_match:
            result = json.loads(json_match.group())
            return result.get("en", "other"), result.get("cn", "其他")
    except (json.JSONDecodeError, AttributeError):
        pass
    return "other", "其他"


def _normalize_chunk_method(value):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("`chunk_method` must be a string value.")
    method = _INVISIBLE_RE.sub("", value.strip())
    method = unicodedata.normalize("NFKC", method).strip().lower()
    if not method:
        raise ValueError("`chunk_method` must be a non-empty string.")
    if method not in VALID_CHUNK_METHODS:
        raise ValueError(f"`chunk_method` {value} doesn't exist")
    return method


def _coerce_chunk_method_for_validation(value):
    if value is None:
        return "naive"
    method_raw = str(value).strip()
    if len(method_raw) >= 2 and method_raw[0] == method_raw[-1] and method_raw[0] in {"'", '"', "`"}:
        method_raw = method_raw[1:-1].strip()
    method_raw = unicodedata.normalize("NFKC", _INVISIBLE_RE.sub("", method_raw)).strip()
    if not method_raw:
        return "naive"
    try:
        return _normalize_chunk_method(method_raw)
    except ValueError:
        return method_raw.lower()


def _normalize_pdf_parser(value):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("`pdf_parser` must be a string value.")
    normalized = value.strip()
    if len(normalized) >= 2 and normalized[0] == normalized[-1] and normalized[0] in {"'", '"', "`"}:
        normalized = normalized[1:-1].strip()
    normalized = re.sub(r"[​-‏⁠﻿ ]", "", normalized)
    normalized = normalized.rstrip(".。")
    normalized = unicodedata.normalize("NFKC", normalized)
    if not normalized:
        raise ValueError("`pdf_parser` must be a non-empty string.")
    lower_key = normalized.lower()
    if lower_key in PDF_PARSER_CANONICAL_MAP:
        return PDF_PARSER_CANONICAL_MAP[lower_key]
    slug = re.sub(r"[^a-z0-9]+", "", lower_key)
    slug_aliases = {
        "mineru": "MinerU",
        "deepdoc": "DeepDOC",
        "plaintext": "Plain Text",
        "docling": "Docling",
        "tcadpparser": "TCADP Parser",
        "tcadp": "TCADP Parser",
    }
    if slug in slug_aliases:
        return slug_aliases[slug]
    return normalized


def _validate_chunk_method_for_file(method, filename):
    if not method:
        return
    suffix = pathlib.Path(filename).suffix.lower().lstrip(".")
    file_type = filename_type(filename)
    if method in {"manual", "paper"}:
        if file_type != FileType.PDF.value:
            raise ValueError(f"`chunk_method` {method} supports only PDF files.")
    elif method == "qa":
        allowed_suffixes = {"pdf", "docx", "csv", "xls", "xlsx", "txt", "md", "markdown"}
        if file_type == FileType.PDF.value:
            return
        if suffix not in allowed_suffixes - {"pdf"}:
            raise ValueError("`chunk_method` qa supports PDF, DOCX, Markdown, TXT, CSV or Excel files.")
    elif method == "table":
        if suffix not in {"xls", "xlsx", "csv"}:
            raise ValueError("`chunk_method` table supports only Excel or CSV files.")
    elif method == "book":
        if file_type not in {FileType.PDF.value, FileType.DOC.value}:
            raise ValueError("`chunk_method` book supports PDF or document files.")
    elif method == "laws":
        if file_type not in {FileType.PDF.value, FileType.DOC.value}:
            raise ValueError("`chunk_method` laws supports PDF or document files.")
    elif method == "presentation":
        if file_type == FileType.PDF.value:
            return
        if suffix not in {"ppt", "pptx"}:
            raise ValueError("`chunk_method` presentation supports PDF or PPT/PPTX files.")
    elif method == "picture":
        if file_type != FileType.VISUAL.value:
            raise ValueError("`chunk_method` picture supports only image files.")
    elif method == "one":
        if file_type not in {FileType.PDF.value, FileType.DOC.value, FileType.VISUAL.value} and suffix not in {"xls", "xlsx", "csv"}:
            raise ValueError("`chunk_method` one supports PDF, document, image or Excel files.")
    elif method == "knowledge_graph":
        if file_type not in {FileType.PDF.value, FileType.DOC.value}:
            raise ValueError("`chunk_method` knowledge_graph supports PDF or document files.")
    elif method == "email":
        if suffix not in {"eml", "msg"}:
            raise ValueError("`chunk_method` email supports only EML or MSG files.")
    elif method == "tag":
        if suffix not in {"xls", "xlsx", "csv", "txt"}:
            raise ValueError("`chunk_method` tag supports CSV, TXT or Excel files.")


def _validate_pdf_parser_choice(pdf_parser, effective_chunk_method, file_type, filename):
    if not pdf_parser:
        return None
    canonical = _normalize_pdf_parser(pdf_parser)
    if file_type != FileType.PDF.value:
        suffix = pathlib.Path(filename).suffix.lower().lstrip(".")
        if suffix in {"xls", "xlsx", "csv", "doc", "docx"}:
            return canonical
        raise ValueError("`pdf_parser` can only be applied to PDF/Excel/CSV/Word files.")
    method = _coerce_chunk_method_for_validation(effective_chunk_method)
    _eff_raw = unicodedata.normalize("NFKC", _INVISIBLE_RE.sub("", str(effective_chunk_method or "").strip())).lower()
    _eff_slug = re.sub(r"[^a-z]+", "", _eff_raw)
    if (
        method in {"hichunk", "one"}
        or _eff_raw in {"hichunk", "one"}
        or _eff_slug in {"hichunk", "one"}
    ):
        return canonical
    if method == "qa":
        if canonical != "DeepDOC":
            raise ValueError("`pdf_parser` DeepDOC is required when `chunk_method` is `qa`.")
    elif method in {"manual", "paper", "book", "laws", "knowledge_graph"}:
        if canonical not in BASIC_PDF_PARSERS:
            raise ValueError(f"`pdf_parser` {canonical} is not supported with `chunk_method` {method}.")
    elif method == "presentation":
        if canonical in EXTENDED_PDF_PARSERS:
            raise ValueError(f"`pdf_parser` {canonical} is not supported with `chunk_method` {method}.")
    elif method == "naive":
        pass
    else:
        if canonical not in BASIC_PDF_PARSERS:
            raise ValueError(f"`pdf_parser` {canonical} is not supported with `chunk_method` {method}.")
    return canonical


def _resolve_word_chunk_method(method, filename, file_type):
    if not method:
        return method
    suffix = pathlib.Path(filename).suffix.lower().lstrip(".")
    if file_type == FileType.DOC.value and suffix in {"doc", "docx"}:
        return "naive"
    return method


class Chunk(BaseModel):
    id: str = ""
    content: str = ""
    document_id: str = ""
    docnm_kwd: str = ""
    important_keywords: list = Field(default_factory=list)
    questions: list = Field(default_factory=list)
    question_tks: str = ""
    image_id: str = ""
    available: bool = True
    positions: list[list[int]] = Field(default_factory=list)

    @validator("positions")
    def validate_positions(cls, value):
        for sublist in value:
            if len(sublist) != 5:
                raise ValueError("Each sublist in positions must have a length of 5")
        return value


@manager.route("/datasets/<dataset_id>/documents", methods=["POST"])  # noqa: F821
@token_required
async def upload(dataset_id, tenant_id):
    """
    Upload documents to a dataset and optionally enqueue parsing tasks.
    ---
    tags:
      - Documents
    security:
      - ApiKeyAuth: []
    parameters:
      - in: path
        name: dataset_id
        type: string
        required: true
        description: ID of the dataset.
      - in: header
        name: Authorization
        type: string
        required: true
        description: Bearer token for authentication.
      - in: formData
        name: file
        type: file
        required: true
        description: Document files to upload.
      - in: formData
        name: parent_path
        type: string
        description: Optional nested path under the parent folder. Uses '/' separators.
      - in: formData
        name: metadata
        type: string
        required: false
        description: JSON object mapping filenames or `__default__` to metadata dicts.
      - in: formData
        name: tags
        type: string
        required: false
        description: JSON object mapping filenames or `__default__` to tag lists.
      - in: formData
        name: chunk_method
        type: string
        required: false
        description: JSON object mapping filenames or `__default__` to chunk methods.
      - in: formData
        name: pdf_parser
        type: string
        required: false
        description: JSON object mapping filenames or `__default__` to PDF parser choices.
      - in: formData
        name: llm_analyse
        type: string
        required: false
        description: Whether to use LLM to auto-classify document types ("true"/"false"). Defaults to "false".
      - in: formData
        name: parse
        type: string
        required: false
        description: Whether to immediately enqueue parsing ("true"/"false"). Defaults to "true".
    responses:
      200:
        description: Successfully uploaded documents.
        schema:
          type: object
          properties:
            data:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: string
                    description: Document ID.
                  name:
                    type: string
                    description: Document name.
                  chunk_count:
                    type: integer
                    description: Number of chunks.
                  token_count:
                    type: integer
                    description: Number of tokens.
                  dataset_id:
                    type: string
                    description: ID of the dataset.
                  chunk_method:
                    type: string
                    description: Chunking method used.
                  run:
                    type: string
                    description: Processing status.
    """
    form = await request.form
    files = await request.files
    if "file" not in files:
        return get_error_data_result(message="No file part!", code=RetCode.ARGUMENT_ERROR)
    file_objs = files.getlist("file")
    for file_obj in file_objs:
        if file_obj.filename == "":
            return get_result(message="No file selected!", code=RetCode.ARGUMENT_ERROR)
        if len(file_obj.filename.encode("utf-8")) > FILE_NAME_LEN_LIMIT:
            return get_result(message=f"File name must be {FILE_NAME_LEN_LIMIT} bytes or less.", code=RetCode.ARGUMENT_ERROR)

    parent_path = form.get("parent_path")
    metadata_payload = form.get("metadata")
    tag_payload = form.get("tags")
    chunk_method_payload = form.get("chunk_method")
    pdf_parser_payload = form.get("pdf_parser")
    llm_analyse_raw = form.get("llm_analyse", "false")
    llm_analyse = llm_analyse_raw.lower() in ("true", "1", "yes")
    parse_raw = form.get("parse", "true")
    parse = parse_raw.lower() in ("true", "1", "yes")

    e, kb = KnowledgebaseService.get_by_id(dataset_id)
    if not e:
        raise LookupError(f"Can't find the dataset with ID {dataset_id}!")

    def _load_mapping(raw_payload, mapping_name):
        if not raw_payload:
            return {}
        try:
            parsed = json.loads(raw_payload)
        except json.JSONDecodeError:
            raise ValueError(f"`{mapping_name}` must be a valid JSON object")
        if not isinstance(parsed, dict):
            raise ValueError(f"`{mapping_name}` must be a JSON object keyed by file names")
        return parsed

    def _lookup_per_file(mapping, filename):
        if not mapping:
            return None
        if filename in mapping:
            return mapping[filename]
        stemmed = pathlib.Path(filename).name
        if stemmed in mapping:
            return mapping[stemmed]
        return mapping.get("__default__")

    try:
        metadata_mapping = _load_mapping(metadata_payload, "metadata")
    except ValueError as exc:
        return get_error_data_result(message=str(exc), code=RetCode.ARGUMENT_ERROR)
    try:
        tags_mapping = _load_mapping(tag_payload, "tags")
    except ValueError as exc:
        return get_error_data_result(message=str(exc), code=RetCode.ARGUMENT_ERROR)
    try:
        raw_chunk_mapping = _load_mapping(chunk_method_payload, "chunk_method")
    except ValueError as exc:
        return get_error_data_result(message=str(exc), code=RetCode.ARGUMENT_ERROR)
    try:
        pdf_parser_mapping = _load_mapping(pdf_parser_payload, "pdf_parser")
    except ValueError as exc:
        return get_error_data_result(message=str(exc), code=RetCode.ARGUMENT_ERROR)

    for key, value in metadata_mapping.items():
        if key == "__default__" and value is None:
            continue
        if value is not None and not isinstance(value, dict):
            return get_error_data_result(
                message="Each metadata entry must be a JSON object (or null for unset).",
                code=RetCode.ARGUMENT_ERROR,
            )

    def _validate_tags(tag_value):
        if tag_value is None:
            return None
        if not isinstance(tag_value, list) or not all(isinstance(tag, str) for tag in tag_value):
            raise ValueError("Each tags entry must be a list of strings")
        return tag_value

    try:
        chunk_mapping = {k: _normalize_chunk_method(v) if v is not None else None for k, v in raw_chunk_mapping.items()}
    except ValueError as exc:
        return get_error_data_result(message=str(exc), code=RetCode.ARGUMENT_ERROR)
    for key, value in pdf_parser_mapping.items():
        if value is None:
            continue
        if not isinstance(value, str):
            return get_error_data_result(message="Each pdf_parser entry must be a string (or null for unset).", code=RetCode.ARGUMENT_ERROR)

    try:
        tags_mapping = {k: _validate_tags(v) for k, v in tags_mapping.items()}
    except ValueError as exc:
        return get_error_data_result(message=str(exc), code=RetCode.ARGUMENT_ERROR)

    dataset_default_chunk = (kb.parser_id or "naive").lower()
    if dataset_default_chunk not in VALID_CHUNK_METHODS:
        dataset_default_chunk = "naive"

    upload_context = []
    renamed_doc_list = []
    duplicate_failures = []
    parse_failures = []
    key_mapping = {
        "chunk_num": "chunk_count",
        "kb_id": "dataset_id",
        "token_num": "token_count",
        "parser_id": "chunk_method",
    }
    non_duplicate_file_objs = []
    for file_obj in file_objs:
        sha256_hash = compute_sha256_stream(file_obj)

        chunk_override = _lookup_per_file(chunk_mapping, file_obj.filename)
        pdf_parser_choice = _lookup_per_file(pdf_parser_mapping, file_obj.filename)
        meta_fields = deepcopy(_lookup_per_file(metadata_mapping, file_obj.filename))
        tags = deepcopy(_lookup_per_file(tags_mapping, file_obj.filename))
        file_type = filename_type(file_obj.filename)
        effective_chunk_method = chunk_override or dataset_default_chunk
        effective_chunk_method = _resolve_word_chunk_method(effective_chunk_method, file_obj.filename, file_type)
        chunk_override = _resolve_word_chunk_method(chunk_override, file_obj.filename, file_type)
        try:
            _validate_chunk_method_for_file(chunk_override, file_obj.filename)
        except ValueError as exc:
            return get_error_data_result(message=str(exc), code=RetCode.ARGUMENT_ERROR)
        try:
            _validate_chunk_method_for_file(effective_chunk_method, file_obj.filename)
        except ValueError as exc:
            return get_error_data_result(message=str(exc), code=RetCode.ARGUMENT_ERROR)
        try:
            canonical_pdf_parser = _validate_pdf_parser_choice(pdf_parser_choice, effective_chunk_method, file_type, file_obj.filename)
        except ValueError as exc:
            return get_error_data_result(message=str(exc), code=RetCode.ARGUMENT_ERROR)
        force_reparse = False

        existing_docs = DocumentService.query_by_sha256_hash(sha256_hash, kb.id)

        if existing_docs:
            _, existing_doc = DocumentService.get_by_id(existing_docs[0]["id"])
            existing_doc_dict = existing_doc.to_dict() if existing_doc else {}

            if not chunk_override:
                doc_type_en = existing_doc_dict.get("doc_type_en")
                if doc_type_en:
                    if doc_type_en in ("credit_investigation_of_loan_applicant", "credit_investigation_of_legal_representative", "credit_investigation_of_major_shareholders"):
                        effective_chunk_method = "one"
                    else:
                        effective_chunk_method = "hichunk"
                    if canonical_pdf_parser is None:
                        canonical_pdf_parser = "MinerU"

            old_chunk_method = existing_doc_dict.get("parser_id")
            old_pdf_parser = (existing_doc_dict.get("parser_config") or {}).get("layout_recognize")
            if (effective_chunk_method != old_chunk_method) or (canonical_pdf_parser and canonical_pdf_parser != old_pdf_parser):
                force_reparse = True
                logging.info(f"Detected config change for {file_obj.filename}, forcing re-parse.")

            if not force_reparse:
                meta_fields = meta_fields or {}
                tags = tags or []
                existing_meta = existing_doc_dict.get("meta_fields", {})
                meta_fields = {**existing_meta, **meta_fields}
                if tags:
                    meta_fields["tags"] = list(set(existing_meta.get("tags", []) + tags))

                DocumentService.update_meta_fields(existing_doc_dict["id"], meta_fields)

                renamed_doc = {
                    "id": existing_doc_dict["id"],
                    "name": existing_doc_dict["name"],
                    "chunk_count": existing_doc_dict["chunk_num"],
                    "token_count": existing_doc_dict["token_num"],
                    "dataset_id": existing_doc_dict["kb_id"],
                    "chunk_method": existing_doc_dict["parser_id"],
                    "run": existing_doc_dict["run"],
                    "original_name": existing_doc_dict.get("name", file_obj.filename),
                    "parser_config": existing_doc_dict.get("parser_config", {}),
                    "pipeline_id": existing_doc_dict.get("pipeline_id", ""),
                    "location": existing_doc_dict.get("location", ""),
                    "size": existing_doc_dict.get("size", 0),
                    "suffix": existing_doc_dict.get("suffix", ""),
                    "thumbnail": existing_doc_dict.get("thumbnail", ""),
                    "type": existing_doc_dict.get("type", "doc"),
                    "meta_fields": meta_fields,
                    "created_by": existing_doc_dict.get("created_by", tenant_id)
                }
                renamed_doc_list.append(renamed_doc)
                duplicate_failures.append(f"Duplicate file {file_obj.filename} based on hash {sha256_hash}")
                continue

            if force_reparse:
                logging.info(
                    f"File {file_obj.filename} (Hash: {sha256_hash}) already exists, "
                    f"but config changed (Parser: {old_chunk_method} -> {effective_chunk_method}). "
                    f"but config changed (Parser: {old_pdf_parser} -> {canonical_pdf_parser}). "
                    f"Re-parsing triggered in-place."
                )
                existing_meta = existing_doc_dict.get("meta_fields", {}) or {}
                meta_fields = meta_fields or {}
                tags = tags or []
                merged_meta_fields = {**existing_meta, **meta_fields}
                if tags:
                    merged_meta_fields["tags"] = list(dict.fromkeys(list(existing_meta.get("tags", [])) + tags))
                elif "tags" in merged_meta_fields and not merged_meta_fields["tags"]:
                    del merged_meta_fields["tags"]
                merged_meta_fields.setdefault("doc_id", existing_doc_dict["id"])
                DocumentService.update_meta_fields(existing_doc_dict["id"], merged_meta_fields)

                doc_type_en = None
                cn_type = None
                if llm_analyse:
                    try:
                        bucket, name = File2DocumentService.get_storage_address(doc_id=existing_doc_dict["id"])
                        file_bin = settings.STORAGE_IMPL.get(bucket, name)
                        content_sample = ""
                        if file_bin:
                            try:
                                content_sample = file_bin.decode("utf-8")
                            except (UnicodeDecodeError, AttributeError):
                                raw_text = bytes(b for b in file_bin[:200000] if 32 <= b <= 126 or b in (9, 10, 13)).decode("ascii", errors="ignore")
                                content_sample = raw_text if len(raw_text) >= 50 else file_obj.filename
                        chat_mdl = LLMBundle(kb.tenant_id, LLMType.CHAT)
                        en_type, cn_type = await _classify_document(chat_mdl, content_sample, file_obj.filename)
                        doc_type_en = en_type
                        DocumentService.update_by_id(existing_doc_dict["id"], {"doc_type_en": en_type, "doc_type_cn": cn_type})
                    except Exception as exc:
                        logging.exception("Failed to classify document %s", existing_doc_dict["id"])

                if not chunk_override and doc_type_en:
                    if doc_type_en in ("credit_investigation_of_loan_applicant", "credit_investigation_of_legal_representative", "credit_investigation_of_major_shareholders"):
                        effective_chunk_method = "one"
                    else:
                        effective_chunk_method = "hichunk"

                parser_config_source = deepcopy(existing_doc_dict.get("parser_config")) if isinstance(existing_doc_dict.get("parser_config"), dict) else {}
                parser_config = get_parser_config(effective_chunk_method, deepcopy(parser_config_source) or None)
                if parser_config is None:
                    parser_config = {}
                if canonical_pdf_parser:
                    parser_config["layout_recognize"] = canonical_pdf_parser
                elif doc_type_en:
                    parser_config["layout_recognize"] = "MinerU"

                doc_updates = {
                    "parser_id": effective_chunk_method,
                    "parser_config": parser_config,
                    "run": TaskStatus.RUNNING.value if parse else TaskStatus.UNSTART.value,
                    "progress": 0,
                    "progress_msg": "",
                    "chunk_num": 0,
                    "token_num": 0,
                    "sha256_hash": sha256_hash
                }
                DocumentService.update_by_id(existing_doc_dict["id"], doc_updates)

                renamed_doc = {}
                for key, value in existing_doc_dict.items():
                    new_key = key_mapping.get(key, key)
                    renamed_doc[new_key] = value
                renamed_doc["meta_fields"] = merged_meta_fields
                renamed_doc["original_name"] = file_obj.filename
                renamed_doc["chunk_method"] = effective_chunk_method
                renamed_doc["parser_config"] = parser_config
                if canonical_pdf_parser:
                    renamed_doc["pdf_parser"] = canonical_pdf_parser
                elif doc_type_en:
                    renamed_doc["pdf_parser"] = "MinerU"
                if doc_type_en:
                    renamed_doc["doc_type_en"] = doc_type_en
                    renamed_doc["doc_type_cn"] = cn_type

                current_run_label = TaskStatus.RUNNING.name if parse else TaskStatus.UNSTART.name
                if parse:
                    try:
                        TaskService.filter_delete([Task.doc_id == existing_doc_dict["id"]])
                        settings.docStoreConn.delete({"doc_id": existing_doc_dict["id"]}, search.index_name(kb.tenant_id), kb.id)
                        e_refresh, refreshed_doc = DocumentService.get_by_id(existing_doc_dict["id"])
                        if not e_refresh:
                            raise LookupError(f"Document({existing_doc_dict['id']}) not found after update.")
                        refreshed_doc_dict = refreshed_doc.to_dict()
                        refreshed_doc_dict["tenant_id"] = tenant_id
                        if refreshed_doc_dict.get("parser_config") is None:
                            refreshed_doc_dict["parser_config"] = {}
                        bucket, name = File2DocumentService.get_storage_address(doc_id=existing_doc_dict["id"])
                        queue_tasks(refreshed_doc_dict, bucket, name, 0)
                    except Exception as exc:
                        logging.exception("Failed to queue in-place parsing task for document %s", existing_doc_dict["id"])
                        parse_failures.append(f"{existing_doc_dict.get('name', file_obj.filename)}: {exc}")
                        DocumentService.update_by_id(existing_doc_dict["id"], {"run": TaskStatus.UNSTART.value})
                        current_run_label = TaskStatus.UNSTART.name

                renamed_doc["run"] = current_run_label
                renamed_doc_list.append(renamed_doc)
                continue

        non_duplicate_file_objs.append(file_obj)

        upload_context.append(
            {
                "original_name": file_obj.filename,
                "meta_fields": meta_fields,
                "tags": tags,
                "chunk_method": chunk_override,
                "pdf_parser": canonical_pdf_parser,
                "sha256_hash": sha256_hash
            }
        )

    err, files_result = FileService.upload_document(kb, non_duplicate_file_objs, tenant_id, parent_path=parent_path)
    if err:
        return get_result(message="\n".join(err), code=RetCode.SERVER_ERROR)
    for index, file in enumerate(files_result):
        doc = file[0]
        renamed_doc = {}
        for key, value in doc.items():
            new_key = key_mapping.get(key, key)
            renamed_doc[new_key] = value
        context = upload_context[index] if index < len(upload_context) else {}
        meta_fields = context.get("meta_fields") if context else None
        tags = context.get("tags") if context else None
        chunk_override = context.get("chunk_method")
        pdf_parser_choice = context.get("pdf_parser")
        sha256_hash = context.get("sha256_hash")

        tags_from_request = tags or []
        existing_tags = list((meta_fields or {}).get("tags", []))
        merged = existing_tags or []
        merged.extend(tags_from_request)
        meta_fields = meta_fields or {}
        if merged:
            meta_fields["tags"] = list(dict.fromkeys(merged))
        elif "tags" in meta_fields:
            del meta_fields["tags"]
        meta_fields.setdefault("doc_id", doc["id"])

        if meta_fields:
            DocumentService.update_meta_fields(doc["id"], meta_fields)
            renamed_doc["meta_fields"] = meta_fields
        renamed_doc["original_name"] = context.get("original_name") if context else doc.get("name")

        doc_type_en = None
        if llm_analyse:
            try:
                bucket, name = File2DocumentService.get_storage_address(doc_id=doc["id"])
                file_bin = settings.STORAGE_IMPL.get(bucket, name)
                content_sample = ""
                if file_bin:
                    try:
                        content_sample = file_bin.decode("utf-8")
                    except (UnicodeDecodeError, AttributeError):
                        raw_text = bytes(b for b in file_bin[:200000] if 32 <= b <= 126 or b in (9, 10, 13)).decode("ascii", errors="ignore")
                        content_sample = raw_text if len(raw_text) >= 50 else renamed_doc.get("name", "")
                chat_mdl = LLMBundle(kb.tenant_id, LLMType.CHAT)
                en_type, cn_type = await _classify_document(chat_mdl, content_sample, renamed_doc.get("name", ""))
                doc_type_en = en_type
                DocumentService.update_by_id(doc["id"], {"doc_type_en": en_type, "doc_type_cn": cn_type})
                renamed_doc["doc_type_en"] = en_type
                renamed_doc["doc_type_cn"] = cn_type
            except Exception as exc:
                logging.exception("Failed to classify document %s", doc["id"])

        doc_default_chunk = (doc.get("parser_id") or "naive").lower()
        target_chunk_method = chunk_override or doc_default_chunk
        if not chunk_override and doc_type_en:
            if doc_type_en in ("credit_investigation_of_loan_applicant", "credit_investigation_of_legal_representative", "credit_investigation_of_major_shareholders"):
                target_chunk_method = "one"
            else:
                target_chunk_method = "hichunk"
        target_chunk_method = _resolve_word_chunk_method(target_chunk_method, renamed_doc.get("name", ""), renamed_doc.get("type"))

        parser_config_source = deepcopy(doc.get("parser_config")) if isinstance(doc.get("parser_config"), dict) else {}
        parser_config = get_parser_config(target_chunk_method, deepcopy(parser_config_source) or None)
        if parser_config is None:
            parser_config = {}
        if pdf_parser_choice:
            parser_config["layout_recognize"] = pdf_parser_choice
        elif doc_type_en:
            parser_config["layout_recognize"] = "MinerU"

        doc_updates = {
            "parser_id": target_chunk_method,
            "parser_config": parser_config,
            "run": TaskStatus.RUNNING.value if parse else TaskStatus.UNSTART.value,
            "progress": 0,
            "progress_msg": "",
            "chunk_num": 0,
            "token_num": 0,
            "sha256_hash": sha256_hash
        }
        DocumentService.update_by_id(doc["id"], doc_updates)

        current_run_label = TaskStatus.RUNNING.name if parse else TaskStatus.UNSTART.name
        if parse:
            try:
                TaskService.filter_delete([Task.doc_id == doc["id"]])
                settings.docStoreConn.delete({"doc_id": doc["id"]}, search.index_name(kb.tenant_id), kb.id)
                e_refresh, refreshed_doc = DocumentService.get_by_id(doc["id"])
                if not e_refresh:
                    raise LookupError(f"Document({doc['id']}) not found after update.")
                refreshed_doc_dict = refreshed_doc.to_dict()
                refreshed_doc_dict["tenant_id"] = tenant_id
                if refreshed_doc_dict.get("parser_config") is None:
                    refreshed_doc_dict["parser_config"] = {}
                bucket, name = File2DocumentService.get_storage_address(doc_id=doc["id"])
                queue_tasks(refreshed_doc_dict, bucket, name, 0)
            except Exception as exc:
                logging.exception("Failed to queue parsing task for document %s", doc["id"])
                parse_failures.append(f"{doc.get('name')}: {exc}")
                DocumentService.update_by_id(doc["id"], {"run": TaskStatus.UNSTART.value})
                current_run_label = TaskStatus.UNSTART.name

        renamed_doc["chunk_method"] = target_chunk_method
        renamed_doc["parser_config"] = parser_config
        if pdf_parser_choice:
            renamed_doc["pdf_parser"] = pdf_parser_choice
        elif doc_type_en:
            renamed_doc["pdf_parser"] = "MinerU"
        renamed_doc["run"] = current_run_label
        renamed_doc_list.append(renamed_doc)

    if parse_failures:
        return get_result(message="\n".join(parse_failures), code=RetCode.SERVER_ERROR)
    return get_result(data=renamed_doc_list)


@manager.route("/datasets/<dataset_id>/documents/<document_id>", methods=["PUT"])  # noqa: F821
@token_required
async def update_doc(tenant_id, dataset_id, document_id):
    """
    Update a document within a dataset.
    ---
    tags:
      - Documents
    security:
      - ApiKeyAuth: []
    parameters:
      - in: path
        name: dataset_id
        type: string
        required: true
        description: ID of the dataset.
      - in: path
        name: document_id
        type: string
        required: true
        description: ID of the document to update.
      - in: header
        name: Authorization
        type: string
        required: true
        description: Bearer token for authentication.
      - in: body
        name: body
        description: Document update parameters.
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
              description: New name of the document.
            parser_config:
              type: object
              description: Parser configuration.
            chunk_method:
              type: string
              description: Chunking method.
            enabled:
              type: boolean
              description: Document status.
    responses:
      200:
        description: Document updated successfully.
        schema:
          type: object
    """
    req = await get_request_json()
    if not KnowledgebaseService.query(id=dataset_id, tenant_id=tenant_id):
        return get_error_data_result(message="You don't own the dataset.")
    e, kb = KnowledgebaseService.get_by_id(dataset_id)
    if not e:
        return get_error_data_result(message="Can't find this dataset!")
    doc = DocumentService.query(kb_id=dataset_id, id=document_id)
    if not doc:
        return get_error_data_result(message="The dataset doesn't own the document.")
    doc = doc[0]
    if "chunk_count" in req:
        if req["chunk_count"] != doc.chunk_num:
            return get_error_data_result(message="Can't change `chunk_count`.")
    if "token_count" in req:
        if req["token_count"] != doc.token_num:
            return get_error_data_result(message="Can't change `token_count`.")
    if "progress" in req:
        if req["progress"] != doc.progress:
            return get_error_data_result(message="Can't change `progress`.")

    if "meta_fields" in req:
        if not isinstance(req["meta_fields"], dict):
            return get_error_data_result(message="meta_fields must be a dictionary")
        DocumentService.update_meta_fields(document_id, req["meta_fields"])

    if "name" in req and req["name"] != doc.name:
        if len(req["name"].encode("utf-8")) > FILE_NAME_LEN_LIMIT:
            return get_result(
                message=f"File name must be {FILE_NAME_LEN_LIMIT} bytes or less.",
                code=RetCode.ARGUMENT_ERROR,
            )
        if pathlib.Path(req["name"].lower()).suffix != pathlib.Path(doc.name.lower()).suffix:
            return get_result(
                message="The extension of file can't be changed",
                code=RetCode.ARGUMENT_ERROR,
            )
        for d in DocumentService.query(name=req["name"], kb_id=doc.kb_id):
            if d.name == req["name"]:
                return get_error_data_result(message="Duplicated document name in the same dataset.")
        if not DocumentService.update_by_id(document_id, {"name": req["name"]}):
            return get_error_data_result(message="Database error (Document rename)!")

        informs = File2DocumentService.get_by_document_id(document_id)
        if informs:
            e, file = FileService.get_by_id(informs[0].file_id)
            FileService.update_by_id(file.id, {"name": req["name"]})

    if "parser_config" in req:
        DocumentService.update_parser_config(doc.id, req["parser_config"])
    if "chunk_method" in req:
        valid_chunk_method = {"naive", "manual", "qa", "table", "paper", "book", "laws", "presentation", "picture", "one", "hichunk", "financial", "knowledge_graph", "email", "tag"}
        if req.get("chunk_method") not in valid_chunk_method:
            return get_error_data_result(f"`chunk_method` {req['chunk_method']} doesn't exist")

        if (doc.type == FileType.VISUAL and req.get("chunk_method") not in ("picture", "one", "hichunk", "financial")) or \
           (re.search(r"\.(ppt|pptx|pages)$", doc.name) and req.get("chunk_method") != "presentation"):
            return get_error_data_result(message="Not supported yet!")

        if doc.parser_id.lower() != req["chunk_method"].lower():
            e = DocumentService.update_by_id(
                doc.id,
                {
                    "parser_id": req["chunk_method"],
                    "progress": 0,
                    "progress_msg": "",
                    "run": TaskStatus.UNSTART.value,
                },
            )
            if not e:
                return get_error_data_result(message="Document not found!")
        if not req.get("parser_config"):
            req["parser_config"] = get_parser_config(req["chunk_method"], req.get("parser_config"))
            DocumentService.update_parser_config(doc.id, req["parser_config"])
        if doc.token_num > 0:
            e = DocumentService.increment_chunk_num(
                doc.id,
                doc.kb_id,
                doc.token_num * -1,
                doc.chunk_num * -1,
                doc.process_duration * -1,
            )
            if not e:
                return get_error_data_result(message="Document not found!")
            settings.docStoreConn.delete({"doc_id": doc.id}, search.index_name(tenant_id), dataset_id)

    if "enabled" in req:
        status = int(req["enabled"])
        if doc.status != req["enabled"]:
            try:
                if not DocumentService.update_by_id(doc.id, {"status": str(status)}):
                    return get_error_data_result(message="Database error (Document update)!")
                settings.docStoreConn.update({"doc_id": doc.id}, {"available_int": status}, search.index_name(kb.tenant_id), doc.kb_id)
            except Exception as e:
                return server_error_response(e)

    try:
        ok, doc = DocumentService.get_by_id(doc.id)
        if not ok:
            return get_error_data_result(message="Dataset created failed")
    except OperationalError as e:
        logging.exception(e)
        return get_error_data_result(message="Database operation failed")

    key_mapping = {
        "chunk_num": "chunk_count",
        "kb_id": "dataset_id",
        "token_num": "token_count",
        "parser_id": "chunk_method",
    }
    run_mapping = {
        "0": "UNSTART",
        "1": "RUNNING",
        "2": "CANCEL",
        "3": "DONE",
        "4": "FAIL",
    }
    renamed_doc = {}
    for key, value in doc.to_dict().items():
        new_key = key_mapping.get(key, key)
        renamed_doc[new_key] = value
        if key == "run":
            renamed_doc["run"] = run_mapping.get(str(value))

    return get_result(data=renamed_doc)


@manager.route("/datasets/<dataset_id>/documents/<document_id>", methods=["GET"])  # noqa: F821
@token_required
async def download(tenant_id, dataset_id, document_id):
    """
    Download a document from a dataset.
    ---
    tags:
      - Documents
    security:
      - ApiKeyAuth: []
    produces:
      - application/octet-stream
    parameters:
      - in: path
        name: dataset_id
        type: string
        required: true
        description: ID of the dataset.
      - in: path
        name: document_id
        type: string
        required: true
        description: ID of the document to download.
      - in: header
        name: Authorization
        type: string
        required: true
        description: Bearer token for authentication.
    responses:
      200:
        description: Document file stream.
        schema:
          type: file
      400:
        description: Error message.
        schema:
          type: object
    """
    if not document_id:
        return get_error_data_result(message="Specify document_id please.")
    if not KnowledgebaseService.query(id=dataset_id, tenant_id=tenant_id):
        return get_error_data_result(message=f"You do not own the dataset {dataset_id}.")
    doc = DocumentService.query(kb_id=dataset_id, id=document_id)
    if not doc:
        return get_error_data_result(message=f"The dataset not own the document {document_id}.")
    # The process of downloading
    doc_id, doc_location = File2DocumentService.get_storage_address(doc_id=document_id)  # minio address
    file_stream = settings.STORAGE_IMPL.get(doc_id, doc_location)
    if not file_stream:
        return construct_json_result(message="This file is empty.", code=RetCode.DATA_ERROR)
    file = BytesIO(file_stream)
    # Use send_file with a proper filename and MIME type
    return await send_file(
        file,
        as_attachment=True,
        attachment_filename=doc[0].name,
        mimetype="application/octet-stream",  # Set a default MIME type
    )


@manager.route("/datasets/<dataset_id>/documents", methods=["GET"])  # noqa: F821
@token_required
def list_docs(dataset_id, tenant_id):
    """
    List documents in a dataset.
    ---
    tags:
      - Documents
    security:
      - ApiKeyAuth: []
    parameters:
      - in: path
        name: dataset_id
        type: string
        required: true
        description: ID of the dataset.
      - in: query
        name: id
        type: string
        required: false
        description: Filter by document ID.
      - in: query
        name: page
        type: integer
        required: false
        default: 1
        description: Page number.
      - in: query
        name: page_size
        type: integer
        required: false
        default: 30
        description: Number of items per page.
      - in: query
        name: orderby
        type: string
        required: false
        default: "create_time"
        description: Field to order by.
      - in: query
        name: desc
        type: boolean
        required: false
        default: true
        description: Order in descending.
      - in: query
        name: create_time_from
        type: integer
        required: false
        default: 0
        description: Unix timestamp for filtering documents created after this time. 0 means no filter.
      - in: query
        name: create_time_to
        type: integer
        required: false
        default: 0
        description: Unix timestamp for filtering documents created before this time. 0 means no filter.
      - in: query
        name: suffix
        type: array
        items:
          type: string
        required: false
        description: Filter by file suffix (e.g., ["pdf", "txt", "docx"]).
      - in: query
        name: run
        type: array
        items:
          type: string
        required: false
        description: Filter by document run status. Supports both numeric ("0", "1", "2", "3", "4") and text formats ("UNSTART", "RUNNING", "CANCEL", "DONE", "FAIL").
      - in: header
        name: Authorization
        type: string
        required: true
        description: Bearer token for authentication.
    responses:
      200:
        description: List of documents.
        schema:
          type: object
          properties:
            total:
              type: integer
              description: Total number of documents.
            docs:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: string
                    description: Document ID.
                  name:
                    type: string
                    description: Document name.
                  chunk_count:
                    type: integer
                    description: Number of chunks.
                  token_count:
                    type: integer
                    description: Number of tokens.
                  dataset_id:
                    type: string
                    description: ID of the dataset.
                  chunk_method:
                    type: string
                    description: Chunking method used.
                  run:
                    type: string
                    description: Processing status.
    """
    if not KnowledgebaseService.accessible(kb_id=dataset_id, user_id=tenant_id):
      return get_error_data_result(message=f"You don't own the dataset {dataset_id}. ")

    q = request.args
    document_id = q.get("id")
    name        = q.get("name")

    if document_id and not DocumentService.query(id=document_id, kb_id=dataset_id):
        return get_error_data_result(message=f"You don't own the document {document_id}.")
    if name and not DocumentService.query(name=name, kb_id=dataset_id):
        return get_error_data_result(message=f"You don't own the document {name}.")

    page        = int(q.get("page", 1))
    page_size   = int(q.get("page_size", 30))
    orderby     = q.get("orderby", "create_time")
    desc        = str(q.get("desc", "true")).strip().lower() != "false"
    keywords    = q.get("keywords", "")

    # filters - align with OpenAPI parameter names
    suffix               = q.getlist("suffix")
    run_status           = q.getlist("run")
    create_time_from     = int(q.get("create_time_from", 0))
    create_time_to       = int(q.get("create_time_to", 0))
    metadata_condition_raw = q.get("metadata_condition")
    metadata_condition = {}
    if metadata_condition_raw:
        try:
            metadata_condition = json.loads(metadata_condition_raw)
        except Exception:
            return get_error_data_result(message="metadata_condition must be valid JSON.")
    if metadata_condition and not isinstance(metadata_condition, dict):
        return get_error_data_result(message="metadata_condition must be an object.")

    # map run status (text or numeric) - align with API parameter
    run_status_text_to_numeric = {"UNSTART": "0", "RUNNING": "1", "CANCEL": "2", "DONE": "3", "FAIL": "4"}
    run_status_converted = [run_status_text_to_numeric.get(v, v) for v in run_status]

    doc_ids_filter = None
    if metadata_condition:
        metas = DocumentService.get_flatted_meta_by_kbs([dataset_id])
        doc_ids_filter = meta_filter(metas, convert_conditions(metadata_condition), metadata_condition.get("logic", "and"))
        if metadata_condition.get("conditions") and not doc_ids_filter:
            return get_result(data={"total": 0, "docs": []})

    docs, total = DocumentService.get_list(
        dataset_id, page, page_size, orderby, desc, keywords, document_id, name, suffix, run_status_converted, doc_ids_filter
    )

    # time range filter (0 means no bound)
    if create_time_from or create_time_to:
        docs = [
            d for d in docs
            if (create_time_from == 0 or d.get("create_time", 0) >= create_time_from)
            and (create_time_to == 0 or d.get("create_time", 0) <= create_time_to)
        ]

    # rename keys + map run status back to text for output
    key_mapping = {
        "chunk_num": "chunk_count",
        "kb_id": "dataset_id",
        "token_num": "token_count",
        "parser_id": "chunk_method",
    }
    run_status_numeric_to_text = {"0": "UNSTART", "1": "RUNNING", "2": "CANCEL", "3": "DONE", "4": "FAIL"}

    output_docs = []
    for d in docs:
        renamed_doc = {key_mapping.get(k, k): v for k, v in d.items()}
        if "run" in d:
            renamed_doc["run"] = run_status_numeric_to_text.get(str(d["run"]), d["run"])
        output_docs.append(renamed_doc)

    return get_result(data={"total": total, "docs": output_docs})


@manager.route("/datasets/<dataset_id>/metadata/summary", methods=["GET"])  # noqa: F821
@token_required
def metadata_summary(dataset_id, tenant_id):
    if not KnowledgebaseService.accessible(kb_id=dataset_id, user_id=tenant_id):
        return get_error_data_result(message=f"You don't own the dataset {dataset_id}. ")

    try:
        summary = DocumentService.get_metadata_summary(dataset_id)
        return get_result(data={"summary": summary})
    except Exception as e:
        return server_error_response(e)


@manager.route("/datasets/<dataset_id>/metadata/update", methods=["POST"])  # noqa: F821
@token_required
async def metadata_batch_update(dataset_id, tenant_id):
    if not KnowledgebaseService.accessible(kb_id=dataset_id, user_id=tenant_id):
        return get_error_data_result(message=f"You don't own the dataset {dataset_id}. ")

    req = await get_request_json()
    selector = req.get("selector", {}) or {}
    updates = req.get("updates", []) or []
    deletes = req.get("deletes", []) or []

    if not isinstance(selector, dict):
        return get_error_data_result(message="selector must be an object.")
    if not isinstance(updates, list) or not isinstance(deletes, list):
        return get_error_data_result(message="updates and deletes must be lists.")

    metadata_condition = selector.get("metadata_condition", {}) or {}
    if metadata_condition and not isinstance(metadata_condition, dict):
        return get_error_data_result(message="metadata_condition must be an object.")

    document_ids = selector.get("document_ids", []) or []
    if document_ids and not isinstance(document_ids, list):
        return get_error_data_result(message="document_ids must be a list.")

    for upd in updates:
        if not isinstance(upd, dict) or not upd.get("key") or "value" not in upd:
            return get_error_data_result(message="Each update requires key and value.")
    for d in deletes:
        if not isinstance(d, dict) or not d.get("key"):
            return get_error_data_result(message="Each delete requires key.")

    kb_doc_ids = KnowledgebaseService.list_documents_by_ids([dataset_id])
    target_doc_ids = set(kb_doc_ids)
    if document_ids:
        invalid_ids = set(document_ids) - set(kb_doc_ids)
        if invalid_ids:
            return get_error_data_result(message=f"These documents do not belong to dataset {dataset_id}: {', '.join(invalid_ids)}")
        target_doc_ids = set(document_ids)

    if metadata_condition:
        metas = DocumentService.get_flatted_meta_by_kbs([dataset_id])
        filtered_ids = set(meta_filter(metas, convert_conditions(metadata_condition), metadata_condition.get("logic", "and")))
        target_doc_ids = target_doc_ids & filtered_ids
        if metadata_condition.get("conditions") and not target_doc_ids:
            return get_result(data={"updated": 0, "matched_docs": 0})

    target_doc_ids = list(target_doc_ids)
    updated = DocumentService.batch_update_metadata(dataset_id, target_doc_ids, updates, deletes)
    return get_result(data={"updated": updated, "matched_docs": len(target_doc_ids)})

@manager.route("/datasets/<dataset_id>/documents", methods=["DELETE"])  # noqa: F821
@token_required
async def delete(tenant_id, dataset_id):
    """
    Delete documents from a dataset.
    ---
    tags:
      - Documents
    security:
      - ApiKeyAuth: []
    parameters:
      - in: path
        name: dataset_id
        type: string
        required: true
        description: ID of the dataset.
      - in: body
        name: body
        description: Document deletion parameters.
        required: true
        schema:
          type: object
          properties:
            ids:
              type: array
              items:
                type: string
              description: List of document IDs to delete.
      - in: header
        name: Authorization
        type: string
        required: true
        description: Bearer token for authentication.
    responses:
      200:
        description: Documents deleted successfully.
        schema:
          type: object
    """
    if not KnowledgebaseService.accessible(kb_id=dataset_id, user_id=tenant_id):
        return get_error_data_result(message=f"You don't own the dataset {dataset_id}. ")
    req = await get_request_json()
    if not req:
        doc_ids = None
    else:
        doc_ids = req.get("ids")
    if not doc_ids:
        doc_list = []
        docs = DocumentService.query(kb_id=dataset_id)
        for doc in docs:
            doc_list.append(doc.id)
    else:
        doc_list = doc_ids

    unique_doc_ids, duplicate_messages = check_duplicate_ids(doc_list, "document")
    doc_list = unique_doc_ids

    root_folder = FileService.get_root_folder(tenant_id)
    pf_id = root_folder["id"]
    FileService.init_knowledgebase_docs(pf_id, tenant_id)
    errors = ""
    not_found = []
    success_count = 0
    for doc_id in doc_list:
        try:
            e, doc = DocumentService.get_by_id(doc_id)
            if not e:
                not_found.append(doc_id)
                continue
            tenant_id = DocumentService.get_tenant_id(doc_id)
            if not tenant_id:
                return get_error_data_result(message="Tenant not found!")

            b, n = File2DocumentService.get_storage_address(doc_id=doc_id)

            if not DocumentService.remove_document(doc, tenant_id):
                return get_error_data_result(message="Database error (Document removal)!")

            f2d = File2DocumentService.get_by_document_id(doc_id)
            FileService.filter_delete(
                [
                    File.source_type == FileSource.KNOWLEDGEBASE,
                    File.id == f2d[0].file_id,
                ]
            )
            File2DocumentService.delete_by_document_id(doc_id)

            settings.STORAGE_IMPL.rm(b, n)
            success_count += 1
        except Exception as e:
            errors += str(e)

    if not_found:
        return get_result(message=f"Documents not found: {not_found}", code=RetCode.DATA_ERROR)

    if errors:
        return get_result(message=errors, code=RetCode.SERVER_ERROR)

    if duplicate_messages:
        if success_count > 0:
            return get_result(
                message=f"Partially deleted {success_count} datasets with {len(duplicate_messages)} errors",
                data={"success_count": success_count, "errors": duplicate_messages},
            )
        else:
            return get_error_data_result(message=";".join(duplicate_messages))

    return get_result()


@manager.route("/datasets/<dataset_id>/chunks", methods=["POST"])  # noqa: F821
@token_required
async def parse(tenant_id, dataset_id):
    """
    Start parsing documents into chunks.
    ---
    tags:
      - Chunks
    security:
      - ApiKeyAuth: []
    parameters:
      - in: path
        name: dataset_id
        type: string
        required: true
        description: ID of the dataset.
      - in: body
        name: body
        description: Parsing parameters.
        required: true
        schema:
          type: object
          properties:
            document_ids:
              type: array
              items:
                type: string
              description: List of document IDs to parse.
      - in: header
        name: Authorization
        type: string
        required: true
        description: Bearer token for authentication.
    responses:
      200:
        description: Parsing started successfully.
        schema:
          type: object
    """
    if not KnowledgebaseService.accessible(kb_id=dataset_id, user_id=tenant_id):
        return get_error_data_result(message=f"You don't own the dataset {dataset_id}.")
    req = await get_request_json()
    if not req.get("document_ids"):
        return get_error_data_result("`document_ids` is required")
    doc_list = req.get("document_ids")
    unique_doc_ids, duplicate_messages = check_duplicate_ids(doc_list, "document")
    doc_list = unique_doc_ids

    not_found = []
    success_count = 0
    for id in doc_list:
        doc = DocumentService.query(id=id, kb_id=dataset_id)
        if not doc:
            not_found.append(id)
            continue
        if not doc:
            return get_error_data_result(message=f"You don't own the document {id}.")
        if 0.0 < doc[0].progress < 1.0:
            return get_error_data_result("Can't parse document that is currently being processed")
        info = {"run": "1", "progress": 0, "progress_msg": "", "chunk_num": 0, "token_num": 0}
        DocumentService.update_by_id(id, info)
        settings.docStoreConn.delete({"doc_id": id}, search.index_name(tenant_id), dataset_id)
        TaskService.filter_delete([Task.doc_id == id])
        e, doc = DocumentService.get_by_id(id)
        doc = doc.to_dict()
        doc["tenant_id"] = tenant_id
        bucket, name = File2DocumentService.get_storage_address(doc_id=doc["id"])
        queue_tasks(doc, bucket, name, 0)
        success_count += 1
    if not_found:
        return get_result(message=f"Documents not found: {not_found}", code=RetCode.DATA_ERROR)
    if duplicate_messages:
        if success_count > 0:
            return get_result(
                message=f"Partially parsed {success_count} documents with {len(duplicate_messages)} errors",
                data={"success_count": success_count, "errors": duplicate_messages},
            )
        else:
            return get_error_data_result(message=";".join(duplicate_messages))

    return get_result()


@manager.route("/datasets/<dataset_id>/chunks", methods=["DELETE"])  # noqa: F821
@token_required
async def stop_parsing(tenant_id, dataset_id):
    """
    Stop parsing documents into chunks.
    ---
    tags:
      - Chunks
    security:
      - ApiKeyAuth: []
    parameters:
      - in: path
        name: dataset_id
        type: string
        required: true
        description: ID of the dataset.
      - in: body
        name: body
        description: Stop parsing parameters.
        required: true
        schema:
          type: object
          properties:
            document_ids:
              type: array
              items:
                type: string
              description: List of document IDs to stop parsing.
      - in: header
        name: Authorization
        type: string
        required: true
        description: Bearer token for authentication.
    responses:
      200:
        description: Parsing stopped successfully.
        schema:
          type: object
    """
    if not KnowledgebaseService.accessible(kb_id=dataset_id, user_id=tenant_id):
        return get_error_data_result(message=f"You don't own the dataset {dataset_id}.")
    req = await get_request_json()

    if not req.get("document_ids"):
        return get_error_data_result("`document_ids` is required")
    doc_list = req.get("document_ids")
    unique_doc_ids, duplicate_messages = check_duplicate_ids(doc_list, "document")
    doc_list = unique_doc_ids

    success_count = 0
    for id in doc_list:
        doc = DocumentService.query(id=id, kb_id=dataset_id)
        if not doc:
            return get_error_data_result(message=f"You don't own the document {id}.")
        if int(doc[0].progress) == 1 or doc[0].progress == 0:
            return get_error_data_result("Can't stop parsing document with progress at 0 or 1")
        # Send cancellation signal via Redis to stop background task
        cancel_all_task_of(id)
        info = {"run": "2", "progress": 0, "chunk_num": 0}
        DocumentService.update_by_id(id, info)
        settings.docStoreConn.delete({"doc_id": doc[0].id}, search.index_name(tenant_id), dataset_id)
        success_count += 1
    if duplicate_messages:
        if success_count > 0:
            return get_result(
                message=f"Partially stopped {success_count} documents with {len(duplicate_messages)} errors",
                data={"success_count": success_count, "errors": duplicate_messages},
            )
        else:
            return get_error_data_result(message=";".join(duplicate_messages))
    return get_result()


@manager.route("/datasets/<dataset_id>/documents/<document_id>/chunks", methods=["GET"])  # noqa: F821
@token_required
def list_chunks(tenant_id, dataset_id, document_id):
    """
    List chunks of a document.
    ---
    tags:
      - Chunks
    security:
      - ApiKeyAuth: []
    parameters:
      - in: path
        name: dataset_id
        type: string
        required: true
        description: ID of the dataset.
      - in: path
        name: document_id
        type: string
        required: true
        description: ID of the document.
      - in: query
        name: page
        type: integer
        required: false
        default: 1
        description: Page number.
      - in: query
        name: page_size
        type: integer
        required: false
        default: 30
        description: Number of items per page.
      - in: query
        name: id
        type: string
        required: false
        default: ""
        description: Chunk id.
      - in: header
        name: Authorization
        type: string
        required: true
        description: Bearer token for authentication.
    responses:
      200:
        description: List of chunks.
        schema:
          type: object
          properties:
            total:
              type: integer
              description: Total number of chunks.
            chunks:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: string
                    description: Chunk ID.
                  content:
                    type: string
                    description: Chunk content.
                  document_id:
                    type: string
                    description: ID of the document.
                  important_keywords:
                    type: array
                    items:
                      type: string
                    description: Important keywords.
                  image_id:
                    type: string
                    description: Image ID associated with the chunk.
            doc:
              type: object
              description: Document details.
    """
    if not KnowledgebaseService.accessible(kb_id=dataset_id, user_id=tenant_id):
        return get_error_data_result(message=f"You don't own the dataset {dataset_id}.")
    doc = DocumentService.query(id=document_id, kb_id=dataset_id)
    if not doc:
        return get_error_data_result(message=f"You don't own the document {document_id}.")
    doc = doc[0]
    req = request.args
    doc_id = document_id
    page = int(req.get("page", 1))
    size = int(req.get("page_size", 30))
    question = req.get("keywords", "")
    query = {
        "doc_ids": [doc_id],
        "page": page,
        "size": size,
        "question": question,
        "sort": True,
    }
    key_mapping = {
        "chunk_num": "chunk_count",
        "kb_id": "dataset_id",
        "token_num": "token_count",
        "parser_id": "chunk_method",
    }
    run_mapping = {
        "0": "UNSTART",
        "1": "RUNNING",
        "2": "CANCEL",
        "3": "DONE",
        "4": "FAIL",
    }
    doc = doc.to_dict()
    renamed_doc = {}
    for key, value in doc.items():
        new_key = key_mapping.get(key, key)
        renamed_doc[new_key] = value
        if key == "run":
            renamed_doc["run"] = run_mapping.get(str(value))

    res = {"total": 0, "chunks": [], "doc": renamed_doc}
    if req.get("id"):
        chunk = settings.docStoreConn.get(req.get("id"), search.index_name(tenant_id), [dataset_id])
        if not chunk:
            return get_result(message=f"Chunk not found: {dataset_id}/{req.get('id')}", code=RetCode.NOT_FOUND)
        k = []
        for n in chunk.keys():
            if re.search(r"(_vec$|_sm_|_tks|_ltks)", n):
                k.append(n)
        for n in k:
            del chunk[n]
        if not chunk:
            return get_error_data_result(f"Chunk `{req.get('id')}` not found.")
        res["total"] = 1
        final_chunk = {
            "id": chunk.get("id", chunk.get("chunk_id")),
            "content": chunk["content_with_weight"],
            "document_id": chunk.get("doc_id", chunk.get("document_id")),
            "docnm_kwd": chunk["docnm_kwd"],
            "important_keywords": chunk.get("important_kwd", []),
            "questions": chunk.get("question_kwd", []),
            "dataset_id": chunk.get("kb_id", chunk.get("dataset_id")),
            "image_id": chunk.get("img_id", ""),
            "available": bool(chunk.get("available_int", 1)),
            "positions": chunk.get("position_int", []),
        }
        res["chunks"].append(final_chunk)
        _ = Chunk(**final_chunk)

    elif settings.docStoreConn.index_exist(search.index_name(tenant_id), dataset_id):
        sres = settings.retriever.search(query, search.index_name(tenant_id), [dataset_id], emb_mdl=None, highlight=True)
        res["total"] = sres.total
        for id in sres.ids:
            d = {
                "id": id,
                "content": (remove_redundant_spaces(sres.highlight[id]) if question and id in sres.highlight else sres.field[id].get("content_with_weight", "")),
                "document_id": sres.field[id]["doc_id"],
                "docnm_kwd": sres.field[id]["docnm_kwd"],
                "important_keywords": sres.field[id].get("important_kwd", []),
                "questions": sres.field[id].get("question_kwd", []),
                "dataset_id": sres.field[id].get("kb_id", sres.field[id].get("dataset_id")),
                "image_id": sres.field[id].get("img_id", ""),
                "available": bool(int(sres.field[id].get("available_int", "1"))),
                "positions": sres.field[id].get("position_int", []),
            }
            res["chunks"].append(d)
            _ = Chunk(**d)  # validate the chunk
    return get_result(data=res)


@manager.route(  # noqa: F821
    "/datasets/<dataset_id>/documents/<document_id>/chunks", methods=["POST"]
)
@token_required
async def add_chunk(tenant_id, dataset_id, document_id):
    """
    Add a chunk to a document.
    ---
    tags:
      - Chunks
    security:
      - ApiKeyAuth: []
    parameters:
      - in: path
        name: dataset_id
        type: string
        required: true
        description: ID of the dataset.
      - in: path
        name: document_id
        type: string
        required: true
        description: ID of the document.
      - in: body
        name: body
        description: Chunk data.
        required: true
        schema:
          type: object
          properties:
            content:
              type: string
              required: true
              description: Content of the chunk.
            important_keywords:
              type: array
              items:
                type: string
              description: Important keywords.
      - in: header
        name: Authorization
        type: string
        required: true
        description: Bearer token for authentication.
    responses:
      200:
        description: Chunk added successfully.
        schema:
          type: object
          properties:
            chunk:
              type: object
              properties:
                id:
                  type: string
                  description: Chunk ID.
                content:
                  type: string
                  description: Chunk content.
                document_id:
                  type: string
                  description: ID of the document.
                important_keywords:
                  type: array
                  items:
                    type: string
                  description: Important keywords.
    """
    if not KnowledgebaseService.accessible(kb_id=dataset_id, user_id=tenant_id):
        return get_error_data_result(message=f"You don't own the dataset {dataset_id}.")
    doc = DocumentService.query(id=document_id, kb_id=dataset_id)
    if not doc:
        return get_error_data_result(message=f"You don't own the document {document_id}.")
    doc = doc[0]
    req = await get_request_json()
    if not str(req.get("content", "")).strip():
        return get_error_data_result(message="`content` is required")
    if "important_keywords" in req:
        if not isinstance(req["important_keywords"], list):
            return get_error_data_result("`important_keywords` is required to be a list")
    if "questions" in req:
        if not isinstance(req["questions"], list):
            return get_error_data_result("`questions` is required to be a list")
    chunk_id = xxhash.xxh64((req["content"] + document_id).encode("utf-8")).hexdigest()
    d = {
        "id": chunk_id,
        "content_ltks": rag_tokenizer.tokenize(req["content"]),
        "content_with_weight": req["content"],
    }
    d["content_sm_ltks"] = rag_tokenizer.fine_grained_tokenize(d["content_ltks"])
    d["important_kwd"] = req.get("important_keywords", [])
    d["important_tks"] = rag_tokenizer.tokenize(" ".join(req.get("important_keywords", [])))
    d["question_kwd"] = [str(q).strip() for q in req.get("questions", []) if str(q).strip()]
    d["question_tks"] = rag_tokenizer.tokenize("\n".join(req.get("questions", [])))
    d["create_time"] = str(datetime.datetime.now()).replace("T", " ")[:19]
    d["create_timestamp_flt"] = datetime.datetime.now().timestamp()
    d["kb_id"] = dataset_id
    d["docnm_kwd"] = doc.name
    d["doc_id"] = document_id
    embd_id = DocumentService.get_embd_id(document_id)
    embd_mdl = TenantLLMService.model_instance(tenant_id, LLMType.EMBEDDING.value, embd_id)
    v, c = embd_mdl.encode([doc.name, req["content"] if not d["question_kwd"] else "\n".join(d["question_kwd"])])
    v = 0.1 * v[0] + 0.9 * v[1]
    d["q_%d_vec" % len(v)] = v.tolist()
    settings.docStoreConn.insert([d], search.index_name(tenant_id), dataset_id)

    DocumentService.increment_chunk_num(doc.id, doc.kb_id, c, 1, 0)
    # rename keys
    key_mapping = {
        "id": "id",
        "content_with_weight": "content",
        "doc_id": "document_id",
        "important_kwd": "important_keywords",
        "question_kwd": "questions",
        "kb_id": "dataset_id",
        "create_timestamp_flt": "create_timestamp",
        "create_time": "create_time",
        "document_keyword": "document",
    }
    renamed_chunk = {}
    for key, value in d.items():
        if key in key_mapping:
            new_key = key_mapping.get(key, key)
            renamed_chunk[new_key] = value
    _ = Chunk(**renamed_chunk)  # validate the chunk
    return get_result(data={"chunk": renamed_chunk})
    # return get_result(data={"chunk_id": chunk_id})


@manager.route(  # noqa: F821
    "datasets/<dataset_id>/documents/<document_id>/chunks", methods=["DELETE"]
)
@token_required
async def rm_chunk(tenant_id, dataset_id, document_id):
    """
    Remove chunks from a document.
    ---
    tags:
      - Chunks
    security:
      - ApiKeyAuth: []
    parameters:
      - in: path
        name: dataset_id
        type: string
        required: true
        description: ID of the dataset.
      - in: path
        name: document_id
        type: string
        required: true
        description: ID of the document.
      - in: body
        name: body
        description: Chunk removal parameters.
        required: true
        schema:
          type: object
          properties:
            chunk_ids:
              type: array
              items:
                type: string
              description: List of chunk IDs to remove.
      - in: header
        name: Authorization
        type: string
        required: true
        description: Bearer token for authentication.
    responses:
      200:
        description: Chunks removed successfully.
        schema:
          type: object
    """
    if not KnowledgebaseService.accessible(kb_id=dataset_id, user_id=tenant_id):
        return get_error_data_result(message=f"You don't own the dataset {dataset_id}.")
    docs = DocumentService.get_by_ids([document_id])
    if not docs:
        raise LookupError(f"Can't find the document with ID {document_id}!")
    req = await get_request_json()
    condition = {"doc_id": document_id}
    if "chunk_ids" in req:
        unique_chunk_ids, duplicate_messages = check_duplicate_ids(req["chunk_ids"], "chunk")
        condition["id"] = unique_chunk_ids
    else:
        unique_chunk_ids = []
        duplicate_messages = []
    chunk_number = settings.docStoreConn.delete(condition, search.index_name(tenant_id), dataset_id)
    if chunk_number != 0:
        DocumentService.decrement_chunk_num(document_id, dataset_id, 1, chunk_number, 0)
    if "chunk_ids" in req and chunk_number != len(unique_chunk_ids):
        if len(unique_chunk_ids) == 0:
            return get_result(message=f"deleted {chunk_number} chunks")
        return get_error_data_result(message=f"rm_chunk deleted chunks {chunk_number}, expect {len(unique_chunk_ids)}")
    if duplicate_messages:
        return get_result(
            message=f"Partially deleted {chunk_number} chunks with {len(duplicate_messages)} errors",
            data={"success_count": chunk_number, "errors": duplicate_messages},
        )
    return get_result(message=f"deleted {chunk_number} chunks")


@manager.route(  # noqa: F821
    "/datasets/<dataset_id>/documents/<document_id>/chunks/<chunk_id>", methods=["PUT"]
)
@token_required
async def update_chunk(tenant_id, dataset_id, document_id, chunk_id):
    """
    Update a chunk within a document.
    ---
    tags:
      - Chunks
    security:
      - ApiKeyAuth: []
    parameters:
      - in: path
        name: dataset_id
        type: string
        required: true
        description: ID of the dataset.
      - in: path
        name: document_id
        type: string
        required: true
        description: ID of the document.
      - in: path
        name: chunk_id
        type: string
        required: true
        description: ID of the chunk to update.
      - in: body
        name: body
        description: Chunk update parameters.
        required: true
        schema:
          type: object
          properties:
            content:
              type: string
              description: Updated content of the chunk.
            important_keywords:
              type: array
              items:
                type: string
              description: Updated important keywords.
            available:
              type: boolean
              description: Availability status of the chunk.
      - in: header
        name: Authorization
        type: string
        required: true
        description: Bearer token for authentication.
    responses:
      200:
        description: Chunk updated successfully.
        schema:
          type: object
    """
    chunk = settings.docStoreConn.get(chunk_id, search.index_name(tenant_id), [dataset_id])
    if chunk is None:
        return get_error_data_result(f"Can't find this chunk {chunk_id}")
    if not KnowledgebaseService.accessible(kb_id=dataset_id, user_id=tenant_id):
        return get_error_data_result(message=f"You don't own the dataset {dataset_id}.")
    doc = DocumentService.query(id=document_id, kb_id=dataset_id)
    if not doc:
        return get_error_data_result(message=f"You don't own the document {document_id}.")
    doc = doc[0]
    req = await get_request_json()
    if "content" in req and req["content"] is not None:
        content = req["content"]
    else:
        content = chunk.get("content_with_weight", "")
    d = {"id": chunk_id, "content_with_weight": content}
    d["content_ltks"] = rag_tokenizer.tokenize(d["content_with_weight"])
    d["content_sm_ltks"] = rag_tokenizer.fine_grained_tokenize(d["content_ltks"])
    if "important_keywords" in req:
        if not isinstance(req["important_keywords"], list):
            return get_error_data_result("`important_keywords` should be a list")
        d["important_kwd"] = req.get("important_keywords", [])
        d["important_tks"] = rag_tokenizer.tokenize(" ".join(req["important_keywords"]))
    if "questions" in req:
        if not isinstance(req["questions"], list):
            return get_error_data_result("`questions` should be a list")
        d["question_kwd"] = [str(q).strip() for q in req.get("questions", []) if str(q).strip()]
        d["question_tks"] = rag_tokenizer.tokenize("\n".join(req["questions"]))
    if "available" in req:
        d["available_int"] = int(req["available"])
    if "positions" in req:
        if not isinstance(req["positions"], list):
            return get_error_data_result("`positions` should be a list")
        d["position_int"] = req["positions"]
    embd_id = DocumentService.get_embd_id(document_id)
    embd_mdl = TenantLLMService.model_instance(tenant_id, LLMType.EMBEDDING.value, embd_id)
    if doc.parser_id == ParserType.QA:
        arr = [t for t in re.split(r"[\n\t]", d["content_with_weight"]) if len(t) > 1]
        if len(arr) != 2:
            return get_error_data_result(message="Q&A must be separated by TAB/ENTER key.")
        q, a = rmPrefix(arr[0]), rmPrefix(arr[1])
        d = beAdoc(d, arr[0], arr[1], not any([rag_tokenizer.is_chinese(t) for t in q + a]))

    v, c = embd_mdl.encode([doc.name, d["content_with_weight"] if not d.get("question_kwd") else "\n".join(d["question_kwd"])])
    v = 0.1 * v[0] + 0.9 * v[1] if doc.parser_id != ParserType.QA else v[1]
    d["q_%d_vec" % len(v)] = v.tolist()
    settings.docStoreConn.update({"id": chunk_id}, d, search.index_name(tenant_id), dataset_id)
    return get_result()


@manager.route("/retrieval", methods=["POST"])  # noqa: F821
@token_required
async def retrieval_test(tenant_id):
    """
    Retrieve chunks based on a query.
    ---
    tags:
      - Retrieval
    security:
      - ApiKeyAuth: []
    parameters:
      - in: body
        name: body
        description: Retrieval parameters.
        required: true
        schema:
          type: object
          properties:
            dataset_ids:
              type: array
              items:
                type: string
              required: true
              description: List of dataset IDs to search in.
            question:
              type: string
              required: true
              description: Query string.
            document_ids:
              type: array
              items:
                type: string
              description: List of document IDs to filter.
            similarity_threshold:
              type: number
              format: float
              description: Similarity threshold.
            vector_similarity_weight:
              type: number
              format: float
              description: Vector similarity weight.
            top_k:
              type: integer
              description: Maximum number of chunks to return.
            highlight:
              type: boolean
              description: Whether to highlight matched content.
            metadata_condition:
              type: object
              description: metadata filter condition.
      - in: header
        name: Authorization
        type: string
        required: true
        description: Bearer token for authentication.
    responses:
      200:
        description: Retrieval results.
        schema:
          type: object
          properties:
            chunks:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: string
                    description: Chunk ID.
                  content:
                    type: string
                    description: Chunk content.
                  document_id:
                    type: string
                    description: ID of the document.
                  dataset_id:
                    type: string
                    description: ID of the dataset.
                  similarity:
                    type: number
                    format: float
                    description: Similarity score.
    """
    req = await get_request_json()
    if not req.get("dataset_ids"):
        return get_error_data_result("`dataset_ids` is required.")
    kb_ids = req["dataset_ids"]
    if not isinstance(kb_ids, list):
        return get_error_data_result("`dataset_ids` should be a list")
    for id in kb_ids:
        if not KnowledgebaseService.accessible(kb_id=id, user_id=tenant_id):
            return get_error_data_result(f"You don't own the dataset {id}.")
    kbs = KnowledgebaseService.get_by_ids(kb_ids)
    embd_nms = list(set([TenantLLMService.split_model_name_and_factory(kb.embd_id)[0] for kb in kbs]))  # remove vendor suffix for comparison
    if len(embd_nms) != 1:
        return get_result(
            message='Datasets use different embedding models."',
            code=RetCode.DATA_ERROR,
        )
    if "question" not in req:
        return get_error_data_result("`question` is required.")
    page = int(req.get("page", 1))
    size = int(req.get("page_size", 30))
    question = req["question"]
    doc_ids = req.get("document_ids", [])
    use_kg = req.get("use_kg", False)
    toc_enhance = req.get("toc_enhance", False)
    langs = req.get("cross_languages", [])
    if not isinstance(doc_ids, list):
        return get_error_data_result("`documents` should be a list")
    doc_ids_list = KnowledgebaseService.list_documents_by_ids(kb_ids)
    for doc_id in doc_ids:
        if doc_id not in doc_ids_list:
            return get_error_data_result(f"The datasets don't own the document {doc_id}")
    if not doc_ids:
        metadata_condition = req.get("metadata_condition", {}) or {}
        metas = DocumentService.get_meta_by_kbs(kb_ids)
        doc_ids = meta_filter(metas, convert_conditions(metadata_condition), metadata_condition.get("logic", "and"))
        # If metadata_condition has conditions but no docs match, return empty result
        if not doc_ids and metadata_condition.get("conditions"):
            return get_result(data={"total": 0, "chunks": [], "doc_aggs": {}})
        if metadata_condition and not doc_ids:
            doc_ids = ["-999"]
    similarity_threshold = float(req.get("similarity_threshold", 0.2))
    vector_similarity_weight = float(req.get("vector_similarity_weight", 0.3))
    top = int(req.get("top_k", 1024))
    if req.get("highlight") == "False" or req.get("highlight") == "false":
        highlight = False
    else:
        highlight = True
    try:
        tenant_ids = list(set([kb.tenant_id for kb in kbs]))
        e, kb = KnowledgebaseService.get_by_id(kb_ids[0])
        if not e:
            return get_error_data_result(message="Dataset not found!")
        embd_mdl = LLMBundle(kb.tenant_id, LLMType.EMBEDDING, llm_name=kb.embd_id)

        rerank_mdl = None
        if req.get("rerank_id"):
            rerank_mdl = LLMBundle(kb.tenant_id, LLMType.RERANK, llm_name=req["rerank_id"])

        if langs:
            question = await cross_languages(kb.tenant_id, None, question, langs)

        if req.get("keyword", False):
            chat_mdl = LLMBundle(kb.tenant_id, LLMType.CHAT)
            question += await keyword_extraction(chat_mdl, question)

        ranks = settings.retriever.retrieval(
            question,
            embd_mdl,
            tenant_ids,
            kb_ids,
            page,
            size,
            similarity_threshold,
            vector_similarity_weight,
            top,
            doc_ids,
            rerank_mdl=rerank_mdl,
            highlight=highlight,
            rank_feature=label_question(question, kbs),
        )
        if toc_enhance:
            chat_mdl = LLMBundle(kb.tenant_id, LLMType.CHAT)
            cks = settings.retriever.retrieval_by_toc(question, ranks["chunks"], tenant_ids, chat_mdl, size)
            if cks:
                ranks["chunks"] = cks
        if use_kg:
            ck = await settings.kg_retriever.retrieval(question, [k.tenant_id for k in kbs], kb_ids, embd_mdl, LLMBundle(kb.tenant_id, LLMType.CHAT))
            if ck["content_with_weight"]:
                ranks["chunks"].insert(0, ck)

        for c in ranks["chunks"]:
            c.pop("vector", None)

        ##rename keys
        renamed_chunks = []
        for chunk in ranks["chunks"]:
            key_mapping = {
                "chunk_id": "id",
                "content_with_weight": "content",
                "doc_id": "document_id",
                "important_kwd": "important_keywords",
                "question_kwd": "questions",
                "docnm_kwd": "document_keyword",
                "kb_id": "dataset_id",
            }
            rename_chunk = {}
            for key, value in chunk.items():
                new_key = key_mapping.get(key, key)
                rename_chunk[new_key] = value
            renamed_chunks.append(rename_chunk)
        ranks["chunks"] = renamed_chunks
        return get_result(data=ranks)
    except Exception as e:
        if str(e).find("not_found") > 0:
            return get_result(
                message="No chunk found! Check the chunk status please!",
                code=RetCode.DATA_ERROR,
            )
        return server_error_response(e)

@manager.route("/datasets/<dataset_id>/documents/<document_id>/status", methods=["PUT"])  # noqa: F821
@token_required
def change_document_status_sdk(tenant_id, dataset_id, document_id):
    """
    Changes the status (enable/disable) of a specific document within a dataset via SDK.
    ---
    tags:
      - Documents
    security:
      - ApiKeyAuth: []
    parameters:
      - in: path
        name: dataset_id
        type: string
        required: true
        description: ID of the dataset.
      - in: path
        name: document_id
        type: string
        required: true
        description: ID of the document.
      - in: body
        name: body
        description: Status update parameters.
        required: true
        schema:
          type: object
          properties:
            status:
              type: integer
              enum: [0, 1]
              required: true
              description: New status (0 for disabled, 1 for enabled).
      - in: header
        name: Authorization
        type: string
        required: true
        description: Bearer token for authentication.
    responses:
      200:
        description: Document status updated successfully.
        schema:
          type: object
          properties:
            data:
              type: boolean
              description: True if successful.
      400:
        description: Invalid arguments.
      401:
        description: Unauthorized.
      404:
        description: Document or Dataset not found.
      500:
        description: Internal server error.
    """
    req = request.json
    status = req.get("status")

    # 1. Input Validation
    if status is None:
        return get_error_data_result(message="`status` is required.")
    if not isinstance(status, int) or status not in [0, 1]:
        return get_error_data_result(message="`status` must be 0 or 1.")

    # 2. Authorization Check (Check if the tenant associated with the token has access to the dataset)
    # This aligns with the pattern in other SDK doc functions checking dataset access using tenant_id.
    if not KnowledgebaseService.accessible(kb_id=dataset_id, user_id=tenant_id):
        return get_error_data_result(message=f"You don't own the dataset {dataset_id}.")

    try:
        # 3. Check if document exists and belongs to the dataset
        e_doc, doc = DocumentService.get_by_id(document_id)
        if not e_doc:
            return get_error_data_result(message=f"Document with ID {document_id} not found.")

        if doc.kb_id != dataset_id:
            # Ensure the document is actually in the specified dataset
            return get_error_data_result(message=f"Document with ID {document_id} does not belong to dataset with ID {dataset_id}.")

        # 4. Update database status
        updated_db = DocumentService.update_by_id(document_id, {"status": str(status)})
        if not updated_db:
            # Database update failed
            return get_error_data_result(message="Failed to update document status in database.")

        # 5. Update search index availability
        index_name = search.index_name(tenant_id)

        # Check if index exists before attempting update
        # This prevents errors if the KB index hasn't been created yet (e.g., empty KB)
        if settings.docStoreConn.indexExist(index_name, doc.kb_id):
            settings.docStoreConn.update({"doc_id": document_id}, {"available_int": status}, index_name, doc.kb_id)
        else:
            pass  # Continue as database update was successful

        # 6. Return success result
        return get_result(data=True)

    except Exception as e:
        # Catch any unexpected exceptions during the process
        return server_error_response(e)


@manager.route("/datasets/<dataset_id>/documents/<document_id>/set_meta", methods=["PUT"])  # noqa: F821
@token_required
def set_document_meta(tenant_id: str, dataset_id: str, document_id: str):
    """
    Sets or updates the metadata for a specific document within a dataset.
    ---
    tags:
      - Documents
    security:
      - ApiKeyAuth: []
    parameters:
      - in: path
        name: dataset_id
        type: string
        required: true
        description: ID of the dataset.
      - in: path
        name: document_id
        type: string
        required: true
        description: ID of the document.
      - in: body
        name: body
        description: Metadata update parameters.
        required: true
        schema:
          type: object
          properties:
            meta:
              type: object
              additionalProperties: true
              description: 'Meta data in JSON map format, like {"key": "value"}'
              example: {"source": "external_api", "processed_by": "script_v2"}
          required:
            - meta
      - in: header
        name: Authorization
        type: string
        required: true
        description: Bearer token for authentication.
    responses:
      200:
        description: Document metadata updated successfully.
        schema:
          type: object
          properties:
            code:
              type: integer
              description: The status code of the response.
            message:
              type: string
              description: The message of the response.
            data:
              type: boolean
              description: True if successful.
      400:
        description: Invalid arguments (e.g., meta not a dict, missing meta, document not in dataset).
      401:
        description: Unauthorized (e.g., invalid token, insufficient permissions).
      404:
        description: Document or Dataset not found.
      500:
        description: Internal server error.
    """
    req_data = request.json
    if not req_data or "meta" not in req_data:
        return get_result(data=False, message="'meta' field is required in the JSON body.", code=settings.RetCode.ARGUMENT_ERROR)

    meta_payload = req_data["meta"]
    if not isinstance(meta_payload, dict):
        return get_result(data=False, message="Meta data should be in Json map format, like {'key': 'value'}.", code=settings.RetCode.ARGUMENT_ERROR)

    try:
        # Check if document exists and belongs to the dataset
        e_doc, doc = DocumentService.get_by_id(document_id)
        if not e_doc:
            return get_error_data_result(message=f"Document with ID {document_id} not found.")

        if doc.kb_id != dataset_id:
            return get_error_data_result(message=f"Document with ID {document_id} does not belong to dataset with ID {dataset_id}.")

        # Update document metadata
        # Check if meta_fields already exists
        if "meta_fields" in doc.meta_fields:
            # Merge existing meta_fields with new payload
            existing_meta = doc.meta_fields["meta_fields"]
            merged_meta = {**existing_meta, **meta_payload}
            meta_payload = merged_meta

        if not DocumentService.update_by_id(document_id, {"meta_fields": meta_payload}):
            return get_error_data_result(message="Failed to update document metadata in database.")

        return get_result(data=True)

    except Exception as e:
        return server_error_response(e)


@manager.route("/datasets/Appd_AbListDocs", methods=["POST"])
@token_required
async def Appd_AbListDocs(tenant_id):
    data = await get_request_json()
    dataset_id = data.get("dataset_id")
    doc_id_list = data.get("doc_id_list", [])

    if not dataset_id or not isinstance(doc_id_list, list):
        return get_error_data_result(message="Missing or invalid parameters: dataset_id, doc_id_list")

    if not KnowledgebaseService.accessible(kb_id=dataset_id, user_id=tenant_id):
        return get_error_data_result(message=f"You don't own the dataset {dataset_id}.")

    docs, _ = DocumentService.get_list(kb_id=dataset_id, page_number=1, items_per_page=99999, orderby="create_time", \
                                       desc=True, keywords="", id=None, name=None)
    docs = [d for d in docs if d.get("id") in doc_id_list]

    total_docs = len(docs)
    done_docs = sum(1 for d in docs if str(d.get("run")) == "3")
    percentage = int(done_docs / total_docs * 100) if total_docs else 100

    result = {
        "percentage": percentage
    }
    return jsonify(result)