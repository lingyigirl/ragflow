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
import json
import logging
import random
import re
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime
from io import BytesIO

import xxhash
from peewee import fn, Case, JOIN

from api.constants import IMG_BASE64_PREFIX, FILE_NAME_LEN_LIMIT
from api.db import PIPELINE_SPECIAL_PROGRESS_FREEZE_TASK_TYPES, FileType, UserTenantRole, CanvasCategory
from api.db.db_models import DB, Document, Knowledgebase, Task, Tenant, UserTenant, File2Document, File, UserCanvas, \
    User
from api.db.db_utils import bulk_insert_into_db
from api.db.services.common_service import CommonService
from api.db.services.knowledgebase_service import KnowledgebaseService
from common.metadata_utils import dedupe_list
from common.misc_utils import get_uuid
from common.time_utils import current_timestamp, get_format_time
from common.constants import LLMType, ParserType, StatusEnum, TaskStatus, SVR_CONSUMER_GROUP_NAME
from rag.nlp import rag_tokenizer, search
from rag.utils.redis_conn import REDIS_CONN
from common.doc_store.doc_store_base import OrderByExpr
from common import settings


class DocumentService(CommonService):
    model = Document

    @classmethod
    def get_cls_model_fields(cls):
        return [
            cls.model.id,
            cls.model.thumbnail,
            cls.model.kb_id,
            cls.model.parser_id,
            cls.model.pipeline_id,
            cls.model.parser_config,
            cls.model.source_type,
            cls.model.type,
            cls.model.created_by,
            cls.model.name,
            cls.model.location,
            cls.model.size,
            cls.model.token_num,
            cls.model.chunk_num,
            cls.model.progress,
            cls.model.progress_msg,
            cls.model.process_begin_at,
            cls.model.process_duration,
            cls.model.meta_fields,
            cls.model.suffix,
            cls.model.run,
            cls.model.status,
            cls.model.voucher_type,
            cls.model.llm_classify_success,
            cls.model.voucher_type_confidence,
            cls.model.voucher_type_source,
            cls.model.llm_name, 
            cls.model.llm_content,
            cls.model.create_time,
            cls.model.create_date,
            cls.model.update_time,
            cls.model.update_date,
        ]

    @classmethod
    @DB.connection_context()
    def get_list(cls, kb_id, page_number, items_per_page,
                 orderby, desc, keywords, id, name, suffix=None, run = None, doc_ids=None):
        fields = cls.get_cls_model_fields()
        docs = cls.model.select(*[*fields, UserCanvas.title]).join(File2Document, on = (File2Document.document_id == cls.model.id))\
            .join(File, on = (File.id == File2Document.file_id))\
            .join(UserCanvas, on = ((cls.model.pipeline_id == UserCanvas.id) & (UserCanvas.canvas_category == CanvasCategory.DataFlow.value)), join_type=JOIN.LEFT_OUTER)\
            .where(cls.model.kb_id == kb_id)
        if id:
            docs = docs.where(
                cls.model.id == id)
        if name:
            docs = docs.where(
                cls.model.name == name
            )
        if keywords:
            docs = docs.where(
                fn.LOWER(cls.model.name).contains(keywords.lower())
            )
        if doc_ids:
            docs = docs.where(cls.model.id.in_(doc_ids))
        if suffix:
            docs = docs.where(cls.model.suffix.in_(suffix))
        if run:
            docs = docs.where(cls.model.run.in_(run))
        if desc:
            docs = docs.order_by(cls.model.getter_by(orderby).desc())
        else:
            docs = docs.order_by(cls.model.getter_by(orderby).asc())

        count = docs.count()
        docs = docs.paginate(page_number, items_per_page)
        return list(docs.dicts()), count

    @classmethod
    @DB.connection_context()
    def check_doc_health(cls, tenant_id: str, filename):
        import os
        MAX_FILE_NUM_PER_USER = int(os.environ.get("MAX_FILE_NUM_PER_USER", 0))
        if 0 < MAX_FILE_NUM_PER_USER <= DocumentService.get_doc_count(tenant_id):
            raise RuntimeError("Exceed the maximum file number of a free user!")
        if len(filename.encode("utf-8")) > FILE_NAME_LEN_LIMIT:
            raise RuntimeError("Exceed the maximum length of file name!")
        return True

    @classmethod
    @DB.connection_context()
    def get_by_kb_id(cls, kb_id, page_number, items_per_page, orderby, desc, keywords, run_status, types, suffix, doc_ids=None, return_empty_metadata=False):
        fields = cls.get_cls_model_fields()
        if keywords:
            docs = (
                cls.model.select(*[*fields, UserCanvas.title.alias("pipeline_name"), User.nickname])
                .join(File2Document, on=(File2Document.document_id == cls.model.id))
                .join(File, on=(File.id == File2Document.file_id))
                .join(UserCanvas, on=(cls.model.pipeline_id == UserCanvas.id), join_type=JOIN.LEFT_OUTER)
                .join(User, on=(cls.model.created_by == User.id), join_type=JOIN.LEFT_OUTER)
                .where((cls.model.kb_id == kb_id), (fn.LOWER(cls.model.name).contains(keywords.lower())))
            )
        else:
            docs = (
                cls.model.select(*[*fields, UserCanvas.title.alias("pipeline_name"), User.nickname])
                .join(File2Document, on=(File2Document.document_id == cls.model.id))
                .join(UserCanvas, on=(cls.model.pipeline_id == UserCanvas.id), join_type=JOIN.LEFT_OUTER)
                .join(File, on=(File.id == File2Document.file_id))
                .join(User, on=(cls.model.created_by == User.id), join_type=JOIN.LEFT_OUTER)
                .where(cls.model.kb_id == kb_id)
            )

        if doc_ids:
            docs = docs.where(cls.model.id.in_(doc_ids))
        if run_status:
            docs = docs.where(cls.model.run.in_(run_status))
        if types:
            docs = docs.where(cls.model.type.in_(types))
        if suffix:
            docs = docs.where(cls.model.suffix.in_(suffix))
        if return_empty_metadata:
            docs = docs.where(fn.COALESCE(fn.JSON_LENGTH(cls.model.meta_fields), 0) == 0)

        count = docs.count()
        if desc:
            docs = docs.order_by(cls.model.getter_by(orderby).desc())
        else:
            docs = docs.order_by(cls.model.getter_by(orderby).asc())

        if page_number and items_per_page:
            docs = docs.paginate(page_number, items_per_page)

        return list(docs.dicts()), count

    @classmethod
    @DB.connection_context()
    def get_filter_by_kb_id(cls, kb_id, keywords, run_status, types, suffix):
        """
        returns:
        {
            "suffix": {
                "ppt": 1,
                "doxc": 2
            },
            "run_status": {
             "1": 2,
             "2": 2
            }
            "metadata": {
                "key1": {
                 "key1_value1": 1,
                 "key1_value2": 2,
                },
                "key2": {
                 "key2_value1": 2,
                 "key2_value2": 1,
                },
            }
        }, total
        where "1" => RUNNING, "2" => CANCEL
        """
        fields = cls.get_cls_model_fields()
        if keywords:
            query = cls.model.select(*fields).join(File2Document, on=(File2Document.document_id == cls.model.id)).join(File, on=(File.id == File2Document.file_id)).where(
                (cls.model.kb_id == kb_id),
                (fn.LOWER(cls.model.name).contains(keywords.lower()))
            )
        else:
            query  = cls.model.select(*fields).join(File2Document, on=(File2Document.document_id == cls.model.id)).join(File, on=(File.id == File2Document.file_id)).where(cls.model.kb_id == kb_id)


        if run_status:
            query = query.where(cls.model.run.in_(run_status))
        if types:
            query = query.where(cls.model.type.in_(types))
        if suffix:
            query = query.where(cls.model.suffix.in_(suffix))

        rows = query.select(cls.model.run, cls.model.suffix, cls.model.meta_fields)
        total = rows.count()

        suffix_counter = {}
        run_status_counter = {}
        metadata_counter = {}
        empty_metadata_count = 0

        for row in rows:
            suffix_counter[row.suffix] = suffix_counter.get(row.suffix, 0) + 1
            run_status_counter[str(row.run)] = run_status_counter.get(str(row.run), 0) + 1
            meta_fields = row.meta_fields or {}
            if not meta_fields:
                empty_metadata_count += 1
                continue
            has_valid_meta = False
            for key, value in meta_fields.items():
                values = value if isinstance(value, list) else [value]
                for vv in values:
                    if vv is None:
                        continue
                    if isinstance(vv, str) and not vv.strip():
                        continue
                    sv = str(vv)
                    if key not in metadata_counter:
                        metadata_counter[key] = {}
                    metadata_counter[key][sv] = metadata_counter[key].get(sv, 0) + 1
                    has_valid_meta = True
            if not has_valid_meta:
                empty_metadata_count += 1

        metadata_counter["empty_metadata"] = {"true": empty_metadata_count}
        return {
            "suffix": suffix_counter,
            "run_status": run_status_counter,
            "metadata": metadata_counter,
        }, total

    @classmethod
    @DB.connection_context()
    def count_by_kb_id(cls, kb_id, keywords, run_status, types):
        if keywords:
            docs = cls.model.select().where(
                (cls.model.kb_id == kb_id),
                (fn.LOWER(cls.model.name).contains(keywords.lower()))
            )
        else:
            docs = cls.model.select().where(cls.model.kb_id == kb_id)

        if run_status:
            docs = docs.where(cls.model.run.in_(run_status))
        if types:
            docs = docs.where(cls.model.type.in_(types))

        count = docs.count()

        return count

    @classmethod
    @DB.connection_context()
    def get_total_size_by_kb_id(cls, kb_id, keywords="", run_status=[], types=[]):
        query = cls.model.select(fn.COALESCE(fn.SUM(cls.model.size), 0)).where(
            cls.model.kb_id == kb_id
        )

        if keywords:
            query = query.where(fn.LOWER(cls.model.name).contains(keywords.lower()))
        if run_status:
            query = query.where(cls.model.run.in_(run_status))
        if types:
            query = query.where(cls.model.type.in_(types))

        return int(query.scalar()) or 0

    @classmethod
    @DB.connection_context()
    def get_all_doc_ids_by_kb_ids(cls, kb_ids):
        fields = [cls.model.id]
        docs = cls.model.select(*fields).where(cls.model.kb_id.in_(kb_ids))
        docs.order_by(cls.model.create_time.asc())
        # maybe cause slow query by deep paginate, optimize later
        offset, limit = 0, 100
        res = []
        while True:
            doc_batch = docs.offset(offset).limit(limit)
            _temp = list(doc_batch.dicts())
            if not _temp:
                break
            res.extend(_temp)
            offset += limit
        return res

    @classmethod
    @DB.connection_context()
    def get_all_docs_by_creator_id(cls, creator_id):
        fields = [
            cls.model.id, cls.model.kb_id, cls.model.token_num, cls.model.chunk_num, Knowledgebase.tenant_id
        ]
        docs = cls.model.select(*fields).join(Knowledgebase, on=(Knowledgebase.id == cls.model.kb_id)).where(
            cls.model.created_by == creator_id
        )
        docs.order_by(cls.model.create_time.asc())
        # maybe cause slow query by deep paginate, optimize later
        offset, limit = 0, 100
        res = []
        while True:
            doc_batch = docs.offset(offset).limit(limit)
            _temp = list(doc_batch.dicts())
            if not _temp:
                break
            res.extend(_temp)
            offset += limit
        return res

    @classmethod
    @DB.connection_context()
    def insert(cls, doc):
        if not cls.save(**doc):
            raise RuntimeError("Database error (Document)!")
        if not KnowledgebaseService.atomic_increase_doc_num_by_id(doc["kb_id"]):
            raise RuntimeError("Database error (Knowledgebase)!")
        return Document(**doc)

    @classmethod
    @DB.connection_context()
    def remove_document(cls, doc, tenant_id):
        from api.db.services.task_service import TaskService
        cls.clear_chunk_num(doc.id)
        try:
            TaskService.filter_delete([Task.doc_id == doc.id])
            cls.delete_chunk_images(doc, tenant_id)
            if doc.thumbnail and not doc.thumbnail.startswith(IMG_BASE64_PREFIX):
                if settings.STORAGE_IMPL.obj_exist(doc.kb_id, doc.thumbnail):
                    settings.STORAGE_IMPL.rm(doc.kb_id, doc.thumbnail)
            settings.docStoreConn.delete({"doc_id": doc.id}, search.index_name(tenant_id), doc.kb_id)

            graph_source = settings.docStoreConn.get_fields(
                settings.docStoreConn.search(["source_id"], [], {"kb_id": doc.kb_id, "knowledge_graph_kwd": ["graph"]}, [], OrderByExpr(), 0, 1, search.index_name(tenant_id), [doc.kb_id]), ["source_id"]
            )
            if len(graph_source) > 0 and doc.id in list(graph_source.values())[0]["source_id"]:
                settings.docStoreConn.update({"kb_id": doc.kb_id, "knowledge_graph_kwd": ["entity", "relation", "graph", "subgraph", "community_report"], "source_id": doc.id},
                                             {"remove": {"source_id": doc.id}},
                                             search.index_name(tenant_id), doc.kb_id)
                settings.docStoreConn.update({"kb_id": doc.kb_id, "knowledge_graph_kwd": ["graph"]},
                                             {"removed_kwd": "Y"},
                                             search.index_name(tenant_id), doc.kb_id)
                settings.docStoreConn.delete({"kb_id": doc.kb_id, "knowledge_graph_kwd": ["entity", "relation", "graph", "subgraph", "community_report"], "must_not": {"exists": "source_id"}},
                                             search.index_name(tenant_id), doc.kb_id)
        except Exception:
            pass
        cls.delete_mineru_sections(doc_id=doc.id, kb_id=doc.kb_id)
        return cls.delete_by_id(doc.id)

    @classmethod
    @DB.connection_context()
    def delete_mineru_sections(cls, doc_id=None, kb_id=None):
        if not doc_id and not kb_id:
            return 0
        try:
            from api.db.db_models import MineruSection
            if not MineruSection.table_exists():
                return 0
            where_conds = []
            if kb_id:
                where_conds.append(MineruSection.kb_id == kb_id)
            if doc_id:
                where_conds.append(MineruSection.doc_id == doc_id)
            query = MineruSection.delete()
            for cond in where_conds:
                query = query.where(cond)
            return query.execute()
        except Exception as e:
            logging.warning(
                "[MinerU] delete mineru_section failed: kb_id=%s, doc_id=%s, err=%s",
                kb_id,
                doc_id,
                e,
            )
            return 0

    @classmethod
    @DB.connection_context()
    def get_mineru_section_by_chunk_id(cls, chunk_id):
        if not chunk_id:
            return None
        try:
            from api.db.db_models import MineruSection
            return MineruSection.get_or_none(MineruSection.chunk_id == str(chunk_id).strip())
        except Exception:
            return None

    @classmethod
    @DB.connection_context()
    def apply_mineru_section_es_id_mappings(cls, doc_id, mappings):
        if not doc_id or not mappings:
            return 0
        try:
            from api.db.db_models import MineruSection
            if not MineruSection.table_exists():
                return 0
            doc_id = str(doc_id).strip()
            total = 0
            for item in mappings:
                es_id = str(item.get("es_id") or "").strip()
                mineru_chunk_ids = item.get("mineru_chunk_ids") or []
                if not es_id or not mineru_chunk_ids:
                    continue
                ids = [str(x).strip() for x in mineru_chunk_ids if x and str(x).strip()]
                if not ids:
                    continue
                update_data = {"es_id": es_id}
                parent_chain = item.get("parent_chain")
                if parent_chain:
                    from api.utils.json_encode import normalize_parent_chain_for_storage
                    parent_chain = normalize_parent_chain_for_storage(parent_chain)
                    if parent_chain:
                        update_data["parent_chain"] = parent_chain
                total += MineruSection.update(**update_data).where(
                    (MineruSection.doc_id == doc_id) & (MineruSection.chunk_id.in_(ids))
                ).execute()
            return total
        except Exception:
            logging.exception("apply_mineru_section_es_id_mappings failed doc_id=%s", doc_id)
            return 0

    @classmethod
    @DB.connection_context()
    def enrich_tree_cross_ref_es_ids(cls, doc_id):
        if not doc_id:
            return False
        try:
            from api.db.db_models import Document, MineruSection

            doc = Document.get_or_none(Document.id == str(doc_id).strip())
            if not doc or not doc.tree_cross_ref:
                return False
            if not MineruSection.table_exists():
                return False
            cross_ref = doc.tree_cross_ref
            if isinstance(cross_ref, str):
                cross_ref = json.loads(cross_ref)
            rows = list(
                MineruSection.select(
                    MineruSection.es_id,
                    MineruSection.parent_chain,
                ).where(MineruSection.doc_id == str(doc_id).strip())
            )
            es_id_chains = {}
            for row in rows:
                es_id = str(row.es_id or "").strip()
                if not es_id:
                    continue
                chain = row.parent_chain or []
                if isinstance(chain, str):
                    try:
                        chain = json.loads(chain)
                    except Exception:
                        chain = []
                if not isinstance(chain, list):
                    chain = []
                if es_id not in es_id_chains or len(chain) > len(es_id_chains[es_id]):
                    es_id_chains[es_id] = chain

            def _chain_has_title(chain, title):
                if not chain or not title:
                    return False
                title = str(title).strip()
                for seg in chain:
                    seg = str(seg).strip()
                    if not seg:
                        continue
                    if title in seg or seg in title:
                        return True
                return False

            table_title_to_es_id = {}
            main_tables = cross_ref.get("main_tables") or []
            for item in main_tables:
                if not isinstance(item, dict):
                    continue
                title = (item.get("title") or "").strip()
                if not title:
                    continue
                for es_id, chain in es_id_chains.items():
                    if _chain_has_title(chain, title):
                        table_title_to_es_id[title] = es_id
                        item["es_id"] = es_id
                        break

            note_to_es_id = {}
            for note_title in (cross_ref.get("note_to_table_mapping") or {}).keys():
                ids = []
                for es_id, chain in es_id_chains.items():
                    if _chain_has_title(chain, note_title):
                        ids.append(es_id)
                if ids:
                    note_to_es_id[note_title] = list(dict.fromkeys(ids))

            note_to_table_es_id = {}
            for note_title, table_names in (cross_ref.get("note_to_table_mapping") or {}).items():
                es_ids = [
                    table_title_to_es_id[t]
                    for t in table_names
                    if t in table_title_to_es_id
                ]
                if es_ids:
                    note_to_table_es_id[note_title] = list(dict.fromkeys(es_ids))

            cross_ref["table_title_to_es_id"] = table_title_to_es_id
            cross_ref["note_to_es_id"] = note_to_es_id
            cross_ref["note_to_table_es_id"] = note_to_table_es_id
            Document.update(tree_cross_ref=cross_ref).where(Document.id == str(doc_id).strip()).execute()
            return True
        except Exception:
            logging.exception("enrich_tree_cross_ref_es_ids failed doc_id=%s", doc_id)
            return False

    @classmethod
    @DB.connection_context()
    def list_mineru_sections_page(cls, kb_id, doc_id, offset=0, limit=500):
        if not kb_id or not doc_id:
            return []
        try:
            from api.db.db_models import MineruSection
            if not MineruSection.table_exists():
                return []
            rows = (
                MineruSection
                .select(
                    MineruSection.id,
                    MineruSection.chunk_id,
                    MineruSection.type,
                    MineruSection.text,
                    MineruSection.bbox,
                    MineruSection.page_idx,
                    MineruSection.text_level,
                    MineruSection.img_path,
                    MineruSection.table_caption,
                    MineruSection.table_footnote,
                    MineruSection.table_body,
                    MineruSection.sub_type,
                    MineruSection.list_items,
                )
                .where(
                    (MineruSection.kb_id == str(kb_id)) &
                    (MineruSection.doc_id == str(doc_id))
                )
                .order_by(MineruSection.page_idx.asc(), MineruSection.id.asc())
                .offset(max(int(offset), 0))
                .limit(max(int(limit), 1))
            )
            return list(rows.dicts())
        except Exception as e:
            logging.warning(
                "[MinerU] list_mineru_sections_page failed: kb_id=%s, doc_id=%s, offset=%s, limit=%s, err=%s",
                kb_id,
                doc_id,
                offset,
                limit,
                e,
            )
            return []

    @classmethod
    @DB.connection_context()
    def update_mineru_section_content_by_chunk_id(
        cls,
        chunk_id,
        req_type,
        text,
    ):
        if not chunk_id:
            return False, "chunk_id is required", {}
        req_type = str(req_type or "").strip().lower()
        type_to_field = {
            "text": "text",
            "table_caption": "table_caption",
            "table_footnote": "table_footnote",
            "table_body": "table_body",
        }
        if req_type not in type_to_field:
            return False, "type must be one of text, table_caption, table_footnote, table_body", {}
        if text is None:
            return False, "text is required", {}
        try:
            from api.db.db_models import MineruSection
        except Exception:
            return False, "mineru_section model import failed", {}
        section = cls.get_mineru_section_by_chunk_id(chunk_id)
        if not section:
            return False, "mineru_section not found by chunk_id", {}
        target_field = type_to_field[req_type]
        col = getattr(MineruSection, target_field)
        update_kwargs = {col: text}
        if req_type == "table_body" and text and isinstance(text, str) and ("<table" in text.lower()) and ("<tr" in text.lower() or "<td" in text.lower()):
            try:
                from rag.utils.html_table_parser import convert_html_table
                es_text, llm_text = convert_html_table(text)
                if es_text:
                    update_kwargs[MineruSection.es_tab2text] = es_text
                if llm_text:
                    update_kwargs[MineruSection.llm_tab2text] = llm_text
            except Exception:
                pass
        updated = MineruSection.update(update_kwargs).where(MineruSection.id == section.id).execute()
        if not updated:
            return False, "update failed", {}
        return True, "", {
            "updated_field": target_field,
            "kb_id": section.kb_id,
            "doc_id": section.doc_id,
            "chunk_id": section.chunk_id,
        }

    @classmethod
    @DB.connection_context()
    def re_vectorize_mineru_section_by_chunk_id(cls, mineru_section_chunk_id):
        if not mineru_section_chunk_id:
            return False, "mineru_section_chunk_id is required", {}

        section = cls.get_mineru_section_by_chunk_id(mineru_section_chunk_id)
        if not section:
            return False, "mineru_section not found by chunk_id", {}

        kb_id = getattr(section, "kb_id", None)
        doc_id = getattr(section, "doc_id", None)
        if not kb_id or not doc_id:
            return False, "kb_id or doc_id is missing", {}

        def _unescape_db_text(val):
            if val is None:
                return ""
            if isinstance(val, str):
                try:
                    parsed = json.loads(val)
                    if isinstance(parsed, list):
                        return "\n".join(str(v) for v in parsed)
                    return str(parsed)
                except (json.JSONDecodeError, TypeError):
                    return val
            if isinstance(val, (list, tuple)):
                return "\n".join(str(v) for v in val)
            return str(val)

        def _build_section_text(msec):
            if not msec:
                return ""
            mtype = (getattr(msec, "type", None) or "").strip().lower()
            if mtype == "table":
                es_txt = str(getattr(msec, "es_tab2text", None) or "").strip()
                if es_txt:
                    t = es_txt
                else:
                    t = (
                        str(getattr(msec, "table_body", None) or "")
                        + "\n"
                        + _unescape_db_text(getattr(msec, "table_caption", None))
                        + "\n"
                        + _unescape_db_text(getattr(msec, "table_footnote", None))
                    ).strip()
            elif mtype == "table_caption":
                t = _unescape_db_text(getattr(msec, "table_caption", None))
            elif mtype == "table_footnote":
                t = _unescape_db_text(getattr(msec, "table_footnote", None))
            elif mtype == "table_body":
                es_txt = str(getattr(msec, "es_tab2text", None) or "").strip()
                if es_txt:
                    t = es_txt
                else:
                    t = str(getattr(msec, "table_body", None) or "")
            else:
                t = str(getattr(msec, "text", None) or "")
            return t if t else ""

        tenant_id = cls.get_tenant_id(doc_id)
        if not tenant_id:
            return False, "tenant not found", {}
        embd_id = cls.get_embd_id(doc_id)

        from api.db.services.llm_service import LLMBundle

        embd_mdl = LLMBundle(tenant_id, LLMType.EMBEDDING, embd_id)

        idxnm = search.index_name(tenant_id)
        if not settings.docStoreConn.index_exist(idxnm, kb_id):
            return False, "index does not exist", {}

        found_chunks = settings.docStoreConn.search(
            [],
            [],
            {"doc_id": str(doc_id)},
            [],
            OrderByExpr(),
            0, 10000,
            idxnm,
            [kb_id],
        )

        updated_count = 0
        if not found_chunks:
            return False, "no vector chunks found for this document", {}

        chunk_docs = settings.docStoreConn.get_doc_ids(found_chunks)
        for vchunk_id in chunk_docs:
            vchunk = settings.docStoreConn.get(vchunk_id, idxnm, [kb_id])
            if not vchunk:
                continue
            mineru_ids = vchunk.get("mineru_section_chunk_ids")
            if not mineru_ids or mineru_section_chunk_id not in mineru_ids:
                continue

            all_section_texts = []
            for mid in mineru_ids:
                if not mid:
                    continue
                msec = cls.get_mineru_section_by_chunk_id(mid)
                all_section_texts.append(_build_section_text(msec))

            new_full_content = "\n".join(t for t in all_section_texts if t)
            if not new_full_content:
                continue

            content_ltks = rag_tokenizer.tokenize(
                re.sub(r"</?(table|td|caption|tr|th)( [^<>]{0,12})?>", " ", new_full_content)
            )
            update_d = {
                "content_with_weight": new_full_content,
                "content_ltks": content_ltks,
                "content_sm_ltks": rag_tokenizer.fine_grained_tokenize(content_ltks),
            }

            vts, _ = embd_mdl.encode([new_full_content])
            v = vts[0]
            update_d["q_%d_vec" % len(v)] = v.tolist()

            settings.docStoreConn.update(
                {"id": vchunk_id},
                update_d,
                idxnm,
                kb_id,
            )
            updated_count += 1

        if updated_count == 0:
            return False, "no matching vector chunks found (mineru_section_chunk_ids not matched)", {}

        return True, "", {
            "updated_chunks": updated_count,
            "kb_id": kb_id,
            "doc_id": doc_id,
            "mineru_section_chunk_id": mineru_section_chunk_id,
        }

    @classmethod
    @DB.connection_context()
    def get_chunk_ids_by_doc_id(cls, doc_id):
        if not doc_id:
            return []
        try:
            from api.db.db_models import MineruSection

            if not MineruSection.table_exists():
                return []
            rows = (
                MineruSection
                .select(
                    MineruSection.chunk_id,
                    MineruSection.type,
                    MineruSection.text,
                    MineruSection.table_caption,
                    MineruSection.table_footnote,
                    MineruSection.table_body,
                    MineruSection.bbox,
                    MineruSection.page_idx,
                    MineruSection.img_path,
                    MineruSection.text_level,
                )
                .where(MineruSection.doc_id == str(doc_id).strip())
                .order_by(MineruSection.page_idx.asc(), MineruSection.id.asc())
            )
            return list(rows.dicts())
        except Exception:
            return []

    @classmethod
    @DB.connection_context()
    def delete_chunk_images(cls, doc, tenant_id):
        page = 0
        page_size = 1000
        while True:
            chunks = settings.docStoreConn.search(["img_id"], [], {"doc_id": doc.id}, [], OrderByExpr(),
                                                  page * page_size, page_size, search.index_name(tenant_id),
                                                  [doc.kb_id])
            chunk_ids = settings.docStoreConn.get_doc_ids(chunks)
            if not chunk_ids:
                break
            for cid in chunk_ids:
                if settings.STORAGE_IMPL.obj_exist(doc.kb_id, cid):
                    settings.STORAGE_IMPL.rm(doc.kb_id, cid)
            page += 1

    @classmethod
    @DB.connection_context()
    def get_newly_uploaded(cls):
        fields = [
            cls.model.id,
            cls.model.kb_id,
            cls.model.parser_id,
            cls.model.parser_config,
            cls.model.name,
            cls.model.type,
            cls.model.location,
            cls.model.size,
            Knowledgebase.tenant_id,
            Tenant.embd_id,
            Tenant.img2txt_id,
            Tenant.asr_id,
            cls.model.update_time]
        docs = cls.model.select(*fields) \
            .join(Knowledgebase, on=(cls.model.kb_id == Knowledgebase.id)) \
            .join(Tenant, on=(Knowledgebase.tenant_id == Tenant.id)) \
            .where(
            cls.model.status == StatusEnum.VALID.value,
            ~(cls.model.type == FileType.VIRTUAL.value),
            cls.model.progress == 0,
            cls.model.update_time >= current_timestamp() - 1000 * 600,
            cls.model.run == TaskStatus.RUNNING.value) \
            .order_by(cls.model.update_time.asc())
        return list(docs.dicts())

    @classmethod
    @DB.connection_context()
    def get_unfinished_docs(cls):
        fields = [cls.model.id, cls.model.process_begin_at, cls.model.parser_config, cls.model.progress_msg,
                  cls.model.run, cls.model.parser_id]
        unfinished_task_query = Task.select(Task.doc_id).where(
            (Task.progress >= 0) & (Task.progress < 1)
        )

        docs = cls.model.select(*fields) \
            .where(
            cls.model.status == StatusEnum.VALID.value,
            ~(cls.model.type == FileType.VIRTUAL.value),
            (((cls.model.progress < 1) & (cls.model.progress > 0)) |
             (cls.model.id.in_(unfinished_task_query)))) # including unfinished tasks like GraphRAG, RAPTOR and Mindmap
        return list(docs.dicts())

    @classmethod
    @DB.connection_context()
    def increment_chunk_num(cls, doc_id, kb_id, token_num, chunk_num, duration):
        num = cls.model.update(token_num=cls.model.token_num + token_num,
                               chunk_num=cls.model.chunk_num + chunk_num,
                               process_duration=cls.model.process_duration + duration).where(
            cls.model.id == doc_id).execute()
        if num == 0:
            logging.warning("Document not found which is supposed to be there")
        num = Knowledgebase.update(
            token_num=Knowledgebase.token_num +
                      token_num,
            chunk_num=Knowledgebase.chunk_num +
                      chunk_num).where(
            Knowledgebase.id == kb_id).execute()
        return num

    @classmethod
    @DB.connection_context()
    def decrement_chunk_num(cls, doc_id, kb_id, token_num, chunk_num, duration):
        num = cls.model.update(token_num=cls.model.token_num - token_num,
                               chunk_num=cls.model.chunk_num - chunk_num,
                               process_duration=cls.model.process_duration + duration).where(
            cls.model.id == doc_id).execute()
        if num == 0:
            raise LookupError(
                "Document not found which is supposed to be there")
        num = Knowledgebase.update(
            token_num=Knowledgebase.token_num -
                      token_num,
            chunk_num=Knowledgebase.chunk_num -
                      chunk_num
        ).where(
            Knowledgebase.id == kb_id).execute()
        return num

    @classmethod
    @DB.connection_context()
    def clear_chunk_num(cls, doc_id):
        doc = cls.model.get_by_id(doc_id)
        assert doc, "Can't fine document in database."

        num = Knowledgebase.update(
            token_num=Knowledgebase.token_num -
                      doc.token_num,
            chunk_num=Knowledgebase.chunk_num -
                      doc.chunk_num,
            doc_num=Knowledgebase.doc_num - 1
        ).where(
            Knowledgebase.id == doc.kb_id).execute()
        return num


    @classmethod
    @DB.connection_context()
    def clear_chunk_num_when_rerun(cls, doc_id):
        doc = cls.model.get_by_id(doc_id)
        assert doc, "Can't fine document in database."

        num = (
            Knowledgebase.update(
                token_num=Knowledgebase.token_num - doc.token_num,
                chunk_num=Knowledgebase.chunk_num - doc.chunk_num,
            )
            .where(Knowledgebase.id == doc.kb_id)
            .execute()
        )
        return num


    @classmethod
    @DB.connection_context()
    def get_tenant_id(cls, doc_id):
        docs = cls.model.select(
            Knowledgebase.tenant_id).join(
            Knowledgebase, on=(
                    Knowledgebase.id == cls.model.kb_id)).where(
            cls.model.id == doc_id, Knowledgebase.status == StatusEnum.VALID.value)
        docs = docs.dicts()
        if not docs:
            return None
        return docs[0]["tenant_id"]

    @classmethod
    @DB.connection_context()
    def get_knowledgebase_id(cls, doc_id):
        docs = cls.model.select(cls.model.kb_id).where(cls.model.id == doc_id)
        docs = docs.dicts()
        if not docs:
            return None
        return docs[0]["kb_id"]

    @classmethod
    @DB.connection_context()
    def get_tenant_id_by_name(cls, name):
        docs = cls.model.select(
            Knowledgebase.tenant_id).join(
            Knowledgebase, on=(
                    Knowledgebase.id == cls.model.kb_id)).where(
            cls.model.name == name, Knowledgebase.status == StatusEnum.VALID.value)
        docs = docs.dicts()
        if not docs:
            return None
        return docs[0]["tenant_id"]

    @classmethod
    @DB.connection_context()
    def accessible(cls, doc_id, user_id):
        docs = cls.model.select(
            cls.model.id).join(
            Knowledgebase, on=(
                    Knowledgebase.id == cls.model.kb_id)
        ).join(UserTenant, on=(UserTenant.tenant_id == Knowledgebase.tenant_id)
               ).where(cls.model.id == doc_id, UserTenant.user_id == user_id).paginate(0, 1)
        docs = docs.dicts()
        if not docs:
            return False
        return True

    @classmethod
    @DB.connection_context()
    def accessible4deletion(cls, doc_id, user_id):
        docs = cls.model.select(cls.model.id
                                ).join(
            Knowledgebase, on=(
                    Knowledgebase.id == cls.model.kb_id)
        ).join(
            UserTenant, on=(
                    (UserTenant.tenant_id == Knowledgebase.created_by) & (UserTenant.user_id == user_id))
        ).where(
            cls.model.id == doc_id,
            UserTenant.status == StatusEnum.VALID.value,
            ((UserTenant.role == UserTenantRole.NORMAL) | (UserTenant.role == UserTenantRole.OWNER))
        ).paginate(0, 1)
        docs = docs.dicts()
        if not docs:
            return False
        return True

    @classmethod
    @DB.connection_context()
    def get_embd_id(cls, doc_id):
        docs = cls.model.select(
            Knowledgebase.embd_id).join(
            Knowledgebase, on=(
                    Knowledgebase.id == cls.model.kb_id)).where(
            cls.model.id == doc_id, Knowledgebase.status == StatusEnum.VALID.value)
        docs = docs.dicts()
        if not docs:
            return None
        return docs[0]["embd_id"]

    @classmethod
    @DB.connection_context()
    def get_chunking_config(cls, doc_id):
        configs = (
            cls.model.select(
                cls.model.id,
                cls.model.kb_id,
                cls.model.parser_id,
                cls.model.parser_config,
                Knowledgebase.language,
                Knowledgebase.embd_id,
                Tenant.id.alias("tenant_id"),
                Tenant.img2txt_id,
                Tenant.asr_id,
                Tenant.llm_id,
            )
            .join(Knowledgebase, on=(cls.model.kb_id == Knowledgebase.id))
            .join(Tenant, on=(Knowledgebase.tenant_id == Tenant.id))
            .where(cls.model.id == doc_id)
        )
        configs = configs.dicts()
        if not configs:
            return None
        return configs[0]

    @classmethod
    @DB.connection_context()
    def get_doc_id_by_doc_name(cls, doc_name):
        fields = [cls.model.id]
        doc_id = cls.model.select(*fields) \
            .where(cls.model.name == doc_name)
        doc_id = doc_id.dicts()
        if not doc_id:
            return None
        return doc_id[0]["id"]

    @classmethod
    @DB.connection_context()
    def get_doc_ids_by_doc_names(cls, doc_names):
        if not doc_names:
            return []

        query = cls.model.select(cls.model.id).where(cls.model.name.in_(doc_names))
        return list(query.scalars().iterator())

    @classmethod
    @DB.connection_context()
    def get_thumbnails(cls, docids):
        fields = [cls.model.id, cls.model.kb_id, cls.model.thumbnail]
        return list(cls.model.select(
            *fields).where(cls.model.id.in_(docids)).dicts())

    @classmethod
    @DB.connection_context()
    def update_parser_config(cls, id, config):
        if not config:
            return
        e, d = cls.get_by_id(id)
        if not e:
            raise LookupError(f"Document({id}) not found.")

        def dfs_update(old, new):
            for k, v in new.items():
                if k not in old:
                    old[k] = v
                    continue
                if isinstance(v, dict):
                    assert isinstance(old[k], dict)
                    dfs_update(old[k], v)
                else:
                    old[k] = v

        dfs_update(d.parser_config, config)
        if not config.get("raptor") and d.parser_config.get("raptor"):
            del d.parser_config["raptor"]
        cls.update_by_id(id, {"parser_config": d.parser_config})

    @classmethod
    @DB.connection_context()
    def get_doc_count(cls, tenant_id):
        docs = cls.model.select(cls.model.id).join(Knowledgebase,
                                                   on=(Knowledgebase.id == cls.model.kb_id)).where(
            Knowledgebase.tenant_id == tenant_id)
        return len(docs)

    @classmethod
    @DB.connection_context()
    def begin2parse(cls, doc_id, keep_progress=False):
        info = {
            "progress_msg": "Task is queued...",
            "process_begin_at": get_format_time(),
        }
        if not keep_progress:
            info["progress"] = random.random() * 1 / 100.
            info["run"] = TaskStatus.RUNNING.value
            # keep the doc in DONE state when keep_progress=True for GraphRAG, RAPTOR and Mindmap tasks

        cls.update_by_id(doc_id, info)

    @classmethod
    @DB.connection_context()
    def update_meta_fields(cls, doc_id, meta_fields):
        return cls.update_by_id(doc_id, {"meta_fields": meta_fields})

    @classmethod
    @DB.connection_context()
    def query_by_sha256_hash(cls, sha256_hash, kb_id=None):
        if not sha256_hash:
            return []
        query = cls.model.select().where(cls.model.sha256_hash == sha256_hash)
        if kb_id:
            query = query.where(cls.model.kb_id == kb_id)
        return list(query.dicts())

    @classmethod
    @DB.connection_context()
    def get_meta_by_kbs(cls, kb_ids):
        """
        Legacy metadata aggregator (backward-compatible).
        - Does NOT expand list values and a list is kept as one string key.
          Example: {"tags": ["foo","bar"]} -> meta["tags"]["['foo', 'bar']"] = [doc_id]
        - Expects meta_fields is a dict.
        Use when existing callers rely on the old list-as-string semantics.
        """
        fields = [
            cls.model.id,
            cls.model.meta_fields,
        ]
        meta = {}
        for r in cls.model.select(*fields).where(cls.model.kb_id.in_(kb_ids)):
            doc_id = r.id
            for k,v in r.meta_fields.items():
                if k not in meta:
                    meta[k] = {}
                if not isinstance(v, list):
                    v = [v]
                for vv in v:
                    if vv not in meta[k]:
                        if isinstance(vv, list) or isinstance(vv, dict):
                            continue
                        meta[k][vv] = []
                    meta[k][vv].append(doc_id)
        return meta

    @classmethod
    @DB.connection_context()
    def get_flatted_meta_by_kbs(cls, kb_ids):
        """
        - Parses stringified JSON meta_fields when possible and skips non-dict or unparsable values.
        - Expands list values into individual entries.
          Example: {"tags": ["foo","bar"], "author": "alice"} ->
            meta["tags"]["foo"] = [doc_id], meta["tags"]["bar"] = [doc_id], meta["author"]["alice"] = [doc_id]
        Prefer for metadata_condition filtering and scenarios that must respect list semantics.
        """
        fields = [
            cls.model.id,
            cls.model.meta_fields,
        ]
        meta = {}
        for r in cls.model.select(*fields).where(cls.model.kb_id.in_(kb_ids)):
            doc_id = r.id
            meta_fields = r.meta_fields or {}
            if isinstance(meta_fields, str):
                try:
                    meta_fields = json.loads(meta_fields)
                except Exception:
                    continue
            if not isinstance(meta_fields, dict):
                continue
            for k, v in meta_fields.items():
                if k not in meta:
                    meta[k] = {}
                values = v if isinstance(v, list) else [v]
                for vv in values:
                    if vv is None:
                        continue
                    sv = str(vv)
                    if sv not in meta[k]:
                        meta[k][sv] = []
                    meta[k][sv].append(doc_id)
        return meta

    @classmethod
    @DB.connection_context()
    def get_metadata_summary(cls, kb_id):
        fields = [cls.model.id, cls.model.meta_fields]
        summary = {}
        for r in cls.model.select(*fields).where(cls.model.kb_id == kb_id):
            meta_fields = r.meta_fields or {}
            if isinstance(meta_fields, str):
                try:
                    meta_fields = json.loads(meta_fields)
                except Exception:
                    continue
            if not isinstance(meta_fields, dict):
                continue
            for k, v in meta_fields.items():
                values = v if isinstance(v, list) else [v]
                for vv in values:
                    if not vv:
                        continue
                    sv = str(vv)
                    if k not in summary:
                        summary[k] = {}
                    summary[k][sv] = summary[k].get(sv, 0) + 1
        return {k: sorted([(val, cnt) for val, cnt in v.items()], key=lambda x: x[1], reverse=True) for k, v in summary.items()}

    @classmethod
    @DB.connection_context()
    def batch_update_metadata(cls, kb_id, doc_ids, updates=None, deletes=None):
        updates = updates or []
        deletes = deletes or []
        if not doc_ids:
            return 0

        def _normalize_meta(meta):
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except Exception:
                    return {}
            if not isinstance(meta, dict):
                return {}
            return deepcopy(meta)

        def _str_equal(a, b):
            return str(a) == str(b)

        def _apply_updates(meta):
            changed = False
            for upd in updates:
                key = upd.get("key")
                if not key or key not in meta:
                    continue

                new_value = upd.get("value")
                match_provided = "match" in upd
                if isinstance(meta[key], list):
                    if not match_provided:
                        if isinstance(new_value, list):
                            meta[key] = dedupe_list(new_value)
                        else:
                            meta[key] = new_value
                        changed = True
                    else:
                        match_value = upd.get("match")
                        replaced = False
                        new_list = []
                        for item in meta[key]:
                            if _str_equal(item, match_value):
                                new_list.append(new_value)
                                replaced = True
                            else:
                                new_list.append(item)
                        if replaced:
                            meta[key] = dedupe_list(new_list)
                            changed = True
                else:
                    if not match_provided:
                        meta[key] = new_value
                        changed = True
                    else:
                        match_value = upd.get("match")
                        if _str_equal(meta[key], match_value):
                            meta[key] = new_value
                            changed = True
            return changed

        def _apply_deletes(meta):
            changed = False
            for d in deletes:
                key = d.get("key")
                if not key or key not in meta:
                    continue
                value = d.get("value", None)
                if isinstance(meta[key], list):
                    if value is None:
                        del meta[key]
                        changed = True
                        continue
                    new_list = [item for item in meta[key] if not _str_equal(item, value)]
                    if len(new_list) != len(meta[key]):
                        if new_list:
                            meta[key] = new_list
                        else:
                            del meta[key]
                        changed = True
                else:
                    if value is None or _str_equal(meta[key], value):
                        del meta[key]
                        changed = True
            return changed

        updated_docs = 0
        with DB.atomic():
            rows = cls.model.select(cls.model.id, cls.model.meta_fields).where(
                (cls.model.id.in_(doc_ids)) & (cls.model.kb_id == kb_id)
            )
            for r in rows:
                meta = _normalize_meta(r.meta_fields or {})
                original_meta = deepcopy(meta)
                changed = _apply_updates(meta)
                changed = _apply_deletes(meta) or changed
                if changed and meta != original_meta:
                    cls.model.update(
                        meta_fields=meta,
                        update_time=current_timestamp(),
                        update_date=get_format_time()
                    ).where(cls.model.id == r.id).execute()
                    updated_docs += 1
        return updated_docs

    @classmethod
    @DB.connection_context()
    def update_progress(cls):
        docs = cls.get_unfinished_docs()

        cls._sync_progress(docs)


    @classmethod
    @DB.connection_context()
    def update_progress_immediately(cls, docs:list[dict]):
        if not docs:
            return

        cls._sync_progress(docs)


    @classmethod
    @DB.connection_context()
    def _sync_progress(cls, docs:list[dict]):
        from api.db.services.task_service import TaskService

        for d in docs:
            try:
                tsks = TaskService.query(doc_id=d["id"], order_by=Task.create_time)
                if not tsks:
                    continue
                msg = []
                prg = 0
                finished = True
                bad = 0
                e, doc = DocumentService.get_by_id(d["id"])
                status = doc.run  # TaskStatus.RUNNING.value
                doc_progress = doc.progress if doc and doc.progress else 0.0
                special_task_running = False
                priority = 0
                for t in tsks:
                    task_type = (t.task_type or "").lower()
                    if task_type in PIPELINE_SPECIAL_PROGRESS_FREEZE_TASK_TYPES:
                        special_task_running = True
                    if 0 <= t.progress < 1:
                        finished = False
                    if t.progress == -1:
                        bad += 1
                    prg += t.progress if t.progress >= 0 else 0
                    if t.progress_msg.strip():
                        msg.append(t.progress_msg)
                    priority = max(priority, t.priority)
                prg /= len(tsks)
                if finished and bad:
                    prg = -1
                    status = TaskStatus.FAIL.value
                elif finished:
                    prg = 1
                    status = TaskStatus.DONE.value

                # only for special task and parsed docs and unfinished
                freeze_progress = special_task_running and doc_progress >= 1 and not finished
                msg = "\n".join(sorted(msg))
                begin_at = d.get("process_begin_at")
                if not begin_at:
                    begin_at = datetime.now()
                    # fallback
                    cls.update_by_id(d["id"], {"process_begin_at": begin_at})

                info = {
                    "process_duration": max(datetime.timestamp(datetime.now()) - begin_at.timestamp(), 0),
                    "run": status}
                if prg != 0 and not freeze_progress:
                    info["progress"] = prg
                if msg:
                    info["progress_msg"] = msg
                    if msg.endswith("created task graphrag") or msg.endswith("created task raptor") or msg.endswith("created task mindmap"):
                        info["progress_msg"] += "\n%d tasks are ahead in the queue..."%get_queue_length(priority)
                else:
                    info["progress_msg"] = "%d tasks are ahead in the queue..."%get_queue_length(priority)
                cls.update_by_id(d["id"], info)
            except Exception as e:
                if str(e).find("'0'") < 0:
                    logging.exception("fetch task exception")

    @classmethod
    @DB.connection_context()
    def get_kb_doc_count(cls, kb_id):
        return cls.model.select().where(cls.model.kb_id == kb_id).count()

    @classmethod
    @DB.connection_context()
    def get_all_kb_doc_count(cls):
        result = {}
        rows = cls.model.select(cls.model.kb_id, fn.COUNT(cls.model.id).alias('count')).group_by(cls.model.kb_id)
        for row in rows:
            result[row.kb_id] = row.count
        return result

    @classmethod
    @DB.connection_context()
    def do_cancel(cls, doc_id):
        try:
            _, doc = DocumentService.get_by_id(doc_id)
            return doc.run == TaskStatus.CANCEL.value or doc.progress < 0
        except Exception:
            pass
        return False


    @classmethod
    @DB.connection_context()
    def knowledgebase_basic_info(cls, kb_id: str) -> dict[str, int]:
        # cancelled: run == "2" but progress can vary
        cancelled = (
            cls.model.select(fn.COUNT(1))
            .where((cls.model.kb_id == kb_id) & (cls.model.run == TaskStatus.CANCEL))
            .scalar()
        )
        downloaded = (
            cls.model.select(fn.COUNT(1))
            .where(
                cls.model.kb_id == kb_id,
                cls.model.source_type != "local"
            )
            .scalar()
        )

        row = (
            cls.model.select(
                # finished: progress == 1
                fn.COALESCE(fn.SUM(Case(None, [(cls.model.progress == 1, 1)], 0)), 0).alias("finished"),

                # failed: progress == -1
                fn.COALESCE(fn.SUM(Case(None, [(cls.model.progress == -1, 1)], 0)), 0).alias("failed"),

                # processing: 0 <= progress < 1
                fn.COALESCE(
                    fn.SUM(
                        Case(
                            None,
                            [
                                (((cls.model.progress == 0) | ((cls.model.progress > 0) & (cls.model.progress < 1))), 1),
                            ],
                            0,
                        )
                    ),
                    0,
                ).alias("processing"),
            )
            .where(
                (cls.model.kb_id == kb_id)
                & ((cls.model.run.is_null(True)) | (cls.model.run != TaskStatus.CANCEL))
            )
            .dicts()
            .get()
        )

        return {
            "processing": int(row["processing"]),
            "finished": int(row["finished"]),
            "failed": int(row["failed"]),
            "cancelled": int(cancelled),
            "downloaded": int(downloaded)
        }

    @classmethod
    def run(cls, tenant_id:str, doc:dict, kb_table_num_map:dict):
        from api.db.services.task_service import queue_dataflow, queue_tasks
        from api.db.services.file2document_service import File2DocumentService

        doc["tenant_id"] = tenant_id
        doc_parser = doc.get("parser_id", ParserType.NAIVE)
        if doc_parser == ParserType.TABLE:
            kb_id = doc.get("kb_id")
            if not kb_id:
                return
            if kb_id not in kb_table_num_map:
                count = DocumentService.count_by_kb_id(kb_id=kb_id, keywords="", run_status=[TaskStatus.DONE], types=[])
                kb_table_num_map[kb_id] = count
                if kb_table_num_map[kb_id] <= 0:
                    KnowledgebaseService.delete_field_map(kb_id)
        if doc.get("pipeline_id", ""):
            _chunk_flow_parser = str(doc_parser).strip().lower() if doc_parser is not None else "naive"
            logging.info(
                "[ChunkFlow|DocumentService.run|branch=dataflow|parser=%s|doc_id=%s]",
                _chunk_flow_parser,
                doc.get("id"),
            )
            queue_dataflow(tenant_id, flow_id=doc["pipeline_id"], task_id=get_uuid(), doc_id=doc["id"])
        else:
            logging.info(
                "[ChunkFlow|DocumentService.run|branch=queue_tasks|parser=%s|doc_id=%s]",
                str(doc_parser).strip().lower() if doc_parser is not None else "naive",
                doc.get("id"),
            )
            bucket, name = File2DocumentService.get_storage_address(doc_id=doc["id"])
            queue_tasks(doc, bucket, name, 0)


def queue_raptor_o_graphrag_tasks(sample_doc_id, ty, priority, fake_doc_id="", doc_ids=[]):
    """
    You can provide a fake_doc_id to bypass the restriction of tasks at the knowledgebase level.
    Optionally, specify a list of doc_ids to determine which documents participate in the task.
    """
    assert ty in ["graphrag", "raptor", "mindmap"], "type should be graphrag, raptor or mindmap"

    chunking_config = DocumentService.get_chunking_config(sample_doc_id["id"])
    hasher = xxhash.xxh64()
    for field in sorted(chunking_config.keys()):
        hasher.update(str(chunking_config[field]).encode("utf-8"))

    def new_task():
        nonlocal sample_doc_id
        return {
            "id": get_uuid(),
            "doc_id": sample_doc_id["id"],
            "from_page": 100000000,
            "to_page": 100000000,
            "task_type": ty,
            "progress_msg":  datetime.now().strftime("%H:%M:%S") + " created task " + ty,
            "begin_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    task = new_task()
    for field in ["doc_id", "from_page", "to_page"]:
        hasher.update(str(task.get(field, "")).encode("utf-8"))
    hasher.update(ty.encode("utf-8"))
    task["digest"] = hasher.hexdigest()
    bulk_insert_into_db(Task, [task], True)

    task["doc_id"] = fake_doc_id
    task["doc_ids"] = doc_ids
    DocumentService.begin2parse(sample_doc_id["id"], keep_progress=True)
    assert REDIS_CONN.queue_product(settings.get_svr_queue_name(priority), message=task), "Can't access Redis. Please check the Redis' status."
    return task["id"]


def get_queue_length(priority):
    group_info = REDIS_CONN.queue_info(settings.get_svr_queue_name(priority), SVR_CONSUMER_GROUP_NAME)
    if not group_info:
        return 0
    return int(group_info.get("lag", 0) or 0)


def doc_upload_and_parse(conversation_id, file_objs, user_id):
    from api.db.services.api_service import API4ConversationService
    from api.db.services.conversation_service import ConversationService
    from api.db.services.dialog_service import DialogService
    from api.db.services.file_service import FileService
    from api.db.services.llm_service import LLMBundle
    from api.db.services.user_service import TenantService
    from rag.app import audio, email, naive, picture, presentation

    e, conv = ConversationService.get_by_id(conversation_id)
    if not e:
        e, conv = API4ConversationService.get_by_id(conversation_id)
    assert e, "Conversation not found!"

    e, dia = DialogService.get_by_id(conv.dialog_id)
    if not dia.kb_ids:
        raise LookupError("No dataset associated with this conversation. "
                          "Please add a dataset before uploading documents")
    kb_id = dia.kb_ids[0]
    e, kb = KnowledgebaseService.get_by_id(kb_id)
    if not e:
        raise LookupError("Can't find this dataset!")

    embd_mdl = LLMBundle(kb.tenant_id, LLMType.EMBEDDING, llm_name=kb.embd_id, lang=kb.language)

    err, files = FileService.upload_document(kb, file_objs, user_id)
    assert not err, "\n".join(err)

    def dummy(prog=None, msg=""):
        pass

    FACTORY = {
        ParserType.PRESENTATION.value: presentation,
        ParserType.PICTURE.value: picture,
        ParserType.AUDIO.value: audio,
        ParserType.EMAIL.value: email
    }
    parser_config = {"chunk_token_num": 4096, "delimiter": "\n!?;。；！？", "layout_recognize": "Plain Text", "table_context_size": 0, "image_context_size": 0}
    exe = ThreadPoolExecutor(max_workers=12)
    threads = []
    doc_nm = {}
    for d, blob in files:
        doc_nm[d["id"]] = d["name"]
    for d, blob in files:
        kwargs = {
            "callback": dummy, 
            "parser_config": parser_config, 
            "from_page": 0, 
            "to_page": 100000, 
            "tenant_id": kb.tenant_id, 
            "lang": kb.language, 
            "kb_id": kb.id,  
            "doc_id": d["id"], 
        }
        threads.append( 
            exe.submit(FACTORY.get(d["parser_id"], naive).chunk, d["name"], blob, **kwargs)
        )

    for (docinfo, _), th in zip(files, threads):
        docs = []
        doc = {
            "doc_id": docinfo["id"],
            "kb_id": [kb.id]
        }
        for ck in th.result():
            d = deepcopy(doc)
            d.update(ck)
            d["id"] = xxhash.xxh64((ck["content_with_weight"] + str(d["doc_id"])).encode("utf-8")).hexdigest()
            d["create_time"] = str(datetime.now()).replace("T", " ")[:19]
            d["create_timestamp_flt"] = datetime.now().timestamp()
            if not d.get("image"):
                docs.append(d)
                continue

            output_buffer = BytesIO()
            if isinstance(d["image"], bytes):
                output_buffer = BytesIO(d["image"])
            else:
                d["image"].save(output_buffer, format='JPEG')

            settings.STORAGE_IMPL.put(kb.id, d["id"], output_buffer.getvalue())
            d["img_id"] = "{}-{}".format(kb.id, d["id"])
            d.pop("image", None)
            docs.append(d)

    parser_ids = {d["id"]: d["parser_id"] for d, _ in files}
    docids = [d["id"] for d, _ in files]
    chunk_counts = {id: 0 for id in docids}
    token_counts = {id: 0 for id in docids}
    es_bulk_size = 64

    def embedding(doc_id, cnts, batch_size=16):
        nonlocal embd_mdl, chunk_counts, token_counts
        vectors = []
        for i in range(0, len(cnts), batch_size):
            vts, c = embd_mdl.encode(cnts[i: i + batch_size])
            vectors.extend(vts.tolist())
            chunk_counts[doc_id] += len(cnts[i:i + batch_size])
            token_counts[doc_id] += c
        return vectors

    idxnm = search.index_name(kb.tenant_id)
    try_create_idx = True

    _, tenant = TenantService.get_by_id(kb.tenant_id)
    llm_bdl = LLMBundle(kb.tenant_id, LLMType.CHAT, tenant.llm_id)
    for doc_id in docids:
        cks = [c for c in docs if c["doc_id"] == doc_id]

        if parser_ids[doc_id] != ParserType.PICTURE.value:
            from graphrag.general.mind_map_extractor import MindMapExtractor
            mindmap = MindMapExtractor(llm_bdl)
            try:
                mind_map = asyncio.run(mindmap([c["content_with_weight"] for c in docs if c["doc_id"] == doc_id]))
                mind_map = json.dumps(mind_map.output, ensure_ascii=False, indent=2)
                if len(mind_map) < 32:
                    raise Exception("Few content: " + mind_map)
                cks.append({
                    "id": get_uuid(),
                    "doc_id": doc_id,
                    "kb_id": [kb.id],
                    "docnm_kwd": doc_nm[doc_id],
                    "title_tks": rag_tokenizer.tokenize(re.sub(r"\.[a-zA-Z]+$", "", doc_nm[doc_id])),
                    "content_ltks": rag_tokenizer.tokenize("summary summarize 总结 概况 file 文件 概括"),
                    "content_with_weight": mind_map,
                    "knowledge_graph_kwd": "mind_map"
                })
            except Exception:
                logging.exception("Mind map generation error")

        vectors = embedding(doc_id, [c["content_with_weight"] for c in cks])
        assert len(cks) == len(vectors)
        for i, d in enumerate(cks):
            v = vectors[i]
            d["q_%d_vec" % len(v)] = v
        for b in range(0, len(cks), es_bulk_size):
            if try_create_idx:
                if not settings.docStoreConn.index_exist(idxnm, kb_id):
                    settings.docStoreConn.create_idx(idxnm, kb_id, len(vectors[0]))
                try_create_idx = False
            settings.docStoreConn.insert(cks[b:b + es_bulk_size], idxnm, kb_id)

        DocumentService.increment_chunk_num(
            doc_id, kb.id, token_counts[doc_id], chunk_counts[doc_id], 0)

    return [d["id"] for d, _ in files]
