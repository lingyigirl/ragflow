"""
MinerU V2 数据库服务。

提供 MineruSectionV2 的 CRUD 操作。
"""

import json
import logging
from typing import Any, Optional

from api.db.db_models import MineruSectionV2

logger = logging.getLogger(__name__)


class MineruV2Service:
    """MineruSectionV2 表 CRUD 服务。"""

    @classmethod
    def get_chunk_ids_by_doc_id(cls, doc_id: str) -> list[dict]:
        """按 doc_id 获取所有 V2 块。"""
        if not doc_id:
            return []
        try:
            if not MineruSectionV2.table_exists():
                return []
            rows = (
                MineruSectionV2
                .select()
                .where(MineruSectionV2.doc_id == str(doc_id).strip())
                .order_by(MineruSectionV2.page_idx.asc(), MineruSectionV2.id.asc())
            )
            return list(rows.dicts())
        except Exception:
            logger.exception("[custom.mineru_v2] get_chunk_ids_by_doc_id 失败")
            return []

    @classmethod
    def get_by_chunk_id(cls, chunk_id: str) -> Optional[MineruSectionV2]:
        """按 chunk_id 获取单条记录。"""
        if not chunk_id:
            return None
        try:
            if not MineruSectionV2.table_exists():
                return None
            return MineruSectionV2.select().where(
                MineruSectionV2.chunk_id == str(chunk_id).strip()
            ).first()
        except Exception:
            logger.exception("[custom.mineru_v2] get_by_chunk_id 失败")
            return None

    @classmethod
    def delete_by_doc_id(cls, doc_id: str) -> int:
        """删除文档的所有 V2 记录，返回删除数。"""
        if not doc_id:
            return 0
        try:
            if not MineruSectionV2.table_exists():
                return 0
            return (
                MineruSectionV2.delete()
                .where(MineruSectionV2.doc_id == str(doc_id).strip())
                .execute()
            )
        except Exception:
            logger.exception("[custom.mineru_v2] delete_by_doc_id 失败")
            return 0

    @classmethod
    def save_blocks(cls, blocks: list[dict], kb_id: str, doc_id: str) -> int:
        """
        批量保存 V2 blocks 到 mineru_section_v2 表。

        使用逐条 insert 避免批量依赖问题。

        Returns:
            成功插入的记录数
        """
        if not blocks or not kb_id or not doc_id:
            return 0

        try:
            if not MineruSectionV2.table_exists():
                logger.error("[custom.mineru_v2] mineru_section_v2 表不存在")
                return 0

            # 先删除旧数据
            cls.delete_by_doc_id(doc_id)

            count = 0
            for idx, row in enumerate(blocks):
                try:
                    # 自动生成 chunk_id
                    if not row.get("chunk_id"):
                        row["chunk_id"] = f"{doc_id}_v2_{idx:04d}"

                    # JSON 字段序列化
                    for json_field in ("bbox", "image_caption", "image_footnote",
                                       "table_caption", "table_footnote",
                                       "list_items", "inline_formula", "span_json"):
                        val = row.get(json_field)
                        if isinstance(val, (dict, list)):
                            row[json_field] = json.dumps(val, ensure_ascii=False)
                        elif val is None:
                            row[json_field] = None

                    MineruSectionV2.create(**row)
                    count += 1
                except Exception as e:
                    logger.error("[custom.mineru_v2] 保存 block[%d] 失败: %s", idx, e)

            logger.info("[custom.mineru_v2] 保存完成: %d/%d", count, len(blocks))
            return count
        except Exception:
            logger.exception("[custom.mineru_v2] save_blocks 失败")
            return 0
