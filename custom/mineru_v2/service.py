"""
MinerU V2 数据库服务。

提供 MineruSectionV2 的 CRUD 操作。
"""

import json
import logging
from typing import Any, Optional

from custom.mineru_v2.models import MineruSectionV2

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
    def get_sections_for_hichunk(cls, doc_id: str) -> list:
        """
        [自定义] 将 mineru_section_v2 表数据转换为 hichunk 兼容的 section 格式。

        转换格式: (text, pos_tag, title_level, chunk_id)
        - text: V2 block 的纯文本内容
        - pos_tag: 与 V1 _line_tag() 同格式的 "@@页码\\tbbox坐标##" 字符串，
                   供 extract_positions() 解析后存入 ES positions 字段
        - title_level: 标题层级（title 类型专用，0 表示非标题）
        - chunk_id: V2 block 的 ID

        用于在 hichunk.chunk() 中将 V2 数据与 V1 数据合并，统一进入智能分块和 ES 索引流程。

        Returns:
            list of (text, pos_tag, title_level, chunk_id) 元组
        """
        rows = cls.get_chunk_ids_by_doc_id(doc_id)
        if not rows:
            return []
        sections = []
        for row in rows:
            row_type = str(row.get("type") or "").strip().lower()
            # 提取文本：按类型选择合适的字段
            if row_type == "image":
                # 图片：使用内容描述，也可支持纯图片块
                text = (row.get("content") or row.get("text") or "").strip()
            elif row_type == "table":
                # 表格：使用 table_html（hichunk 中 is_html_table() 会识别并特殊处理）
                text = (row.get("table_html") or row.get("text") or "").strip()
            elif row_type == "list":
                text = (row.get("text") or "").strip()
            else:
                # title / paragraph / page_header / page_footer / equation / code 等
                text = (row.get("text") or row.get("content") or "").strip()
            if not text:
                continue
            # 生成 pos_tag: @@{页码}\t{x0}\t{x1}\t{y0}\t{y1}##（格式与 V1 _line_tag 一致）
            bbox_val = row.get("bbox")
            if isinstance(bbox_val, str):
                try:
                    bbox_val = json.loads(bbox_val)
                except (json.JSONDecodeError, TypeError):
                    bbox_val = None
            page_num = int(row.get("page_idx") or 0) + 1  # V1 _line_tag 使用 1-based 页码
            if isinstance(bbox_val, list) and len(bbox_val) >= 4:
                x0, y0, x1, y1 = float(bbox_val[0]), float(bbox_val[1]), float(bbox_val[2]), float(bbox_val[3])
            else:
                x0 = y0 = x1 = y1 = 0.0
            pos_tag = f"@@{page_num}\t{x0:.1f}\t{x1:.1f}\t{y0:.1f}\t{y1:.1f}##"
            title_level = row.get("text_level") or 0
            chunk_id = str(row.get("chunk_id") or "").strip()
            sections.append((text, pos_tag, title_level, chunk_id))
        logger.info(
            "[custom.mineru_v2] get_sections_for_hichunk: doc_id=%s 转换 %d 条 section 供 hichunk 使用",
            doc_id, len(sections),
        )
        return sections

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
