"""
MinerU V2 解析器。

负责：
1. 读取 _content_list_v2.json 文件
2. 将 V2 的 span 级数据结构转换为 block 级统一格式
3. Span 聚合策略：同类型 span 拼接，内联公式提取为 LaTeX

## V1 vs V2 本质区别

V1 和 V2 不是按引擎(pipeline/vlm)划分的，是**同一引擎输出格式的版本迭代**。
无论哪个后端引擎，解析完成后都进入 union_make()，按 MakeMode 参数决定输出格式。

## V2 格式（来自实际 3 份文件分析）

V2 顶层结构是**按页分组**的：
    [[page0_blocks], [page1_blocks], ...]

每个 page 是一个 list[block]，数组下标就是 page_idx：

```json
[
  [  // page 0
    {"type": "paragraph", "content": {"paragraph_content": [...]}, "bbox": [...]},
    {"type": "title", "content": {"title_content": [...], "level": 1}, "bbox": [...]},
  ],
  [  // page 1
    {"type": "table", "content": {"html": "<table>...</table>", "image_source": {...}, ...}, "bbox": [...]},
  ]
]
```

## V2 block 类型一览（从实际数据收集）

| type           | content keys                                      | 说明               |
|---------------|---------------------------------------------------|--------------------|
| paragraph     | paragraph_content: list[span]                     | 普通段落             |
| title         | title_content: list[span], level: int             | 标题               |
| list          | list_items: list, list_type: str                  | 列表               |
| table         | html, image_source, table_caption, table_footnote, table_type, table_nest_level | 表格 |
| image         | image_source, content, image_caption, image_footnote | 图片            |
| page_header   | page_header_content: list[span]                   | 页眉               |
| page_footer   | page_footer_content: list[span]                   | 页脚               |

## Span 类型

V2 的 span 有以下类型（从实际数据看目前全是 text）：
- text: 纯文本
- inline_equation: 内联公式（LaTeX）
- inline_code: 内联代码
- phonetic: 拼音标注
- md: 已有 Markdown 格式的文本
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class V2Block:
    """V2 解析后的统一 block 格式。"""

    chunk_id: str = ""
    type: str = ""                    # paragraph/title/list/table/image/page_header/page_footer
    text: Optional[str] = None        # 纯文本聚合（span 拼接结果）
    content: Optional[str] = None     # 描述性内容（如图片描述）
    bbox: Optional[list] = None       # [x0, y0, x1, y1] 千分比坐标（MinerU 原始输出）
    bbox_rotated: Optional[list] = None  # 旋转修正后的 bbox（仅当 PDF 有 /Rotate 时非空）
    is_rotated: bool = False             # MinerU 是否生成了 _rotated.pdf（内容自动摆正）
    page_idx: Optional[int] = None    # 页码（来自外层数组索引）

    # 标题
    text_level: Optional[int] = None  # 1-6 对应 h1-h6

    # 图片
    img_path: Optional[str] = None
    image_caption: Optional[list] = None
    image_footnote: Optional[list] = None

    # 表格（V2: content.html → 存储为 table_html）
    table_html: Optional[str] = None
    table_caption: Optional[list] = None
    table_footnote: Optional[list] = None

    # 列表
    list_items: Optional[list] = None
    list_type: Optional[str] = None

    # V2 特性
    inline_formula: Optional[list] = None   # 内联公式列表
    span_json: Optional[list] = None        # 原始 span 数组（完整保真）
    sub_type: Optional[str] = None          # 子类型

    def to_db_row(self, kb_id: str, doc_id: str) -> dict[str, Any]:
        """转换为数据库行 dict。

        JSON 字段直接传原生 list/dict，由 JSONField.db_value() 统一序列化，
        避免双重编码导致 API 返回 JSON 字符串而非 JSON 数组。
        """
        return {
            "kb_id": str(kb_id),
            "doc_id": str(doc_id),
            "chunk_id": self.chunk_id or "",
            "type": self.type,
            "text": self.text,
            "content": self.content,
            "bbox": self.bbox,
            "bbox_rotated": self.bbox_rotated,
            "is_rotated": self.is_rotated,
            "page_idx": self.page_idx,
            "text_level": self.text_level,
            "img_path": self.img_path,
            "image_caption": self.image_caption or None,
            "image_footnote": self.image_footnote or None,
            "table_html": self.table_html,
            "table_caption": self.table_caption or None,
            "table_footnote": self.table_footnote or None,
            "list_items": self.list_items or None,
            "list_type": self.list_type,
            "inline_formula": self.inline_formula or None,
            "span_json": self.span_json or None,
            "sub_type": self.sub_type,
        }


class MinerUV2Parser:
    """MinerU V2 content_list 解析器。

    V2 数据格式: [[page0_blocks], [page1_blocks], ...]
    每个 page 是一个 list[block]，数组下标 = page_idx。
    """

    # span → 纯文本的格式化规则
    SPAN_TEXT_FORMATTERS = {
        "text": lambda s: s.get("content", ""),
        "bold": lambda s: f"**{s.get('content', '')}**",
        "inline_equation": lambda s: f"${s.get('content', '')}$",
        "inline_code": lambda s: f"`{s.get('content', '')}`",
        "italic": lambda s: f"*{s.get('content', '')}*",
        "link": lambda s: s.get("content", ""),
        "phonetic": lambda s: s.get("content", ""),
        "md": lambda s: s.get("content", ""),
    }

    # ─── 文件读取 ───

    @classmethod
    def read_v2_file(cls, output_dir: Path, file_stem: str) -> Optional[list]:
        """
        读取 _content_list_v2.json 文件。

        查找顺序：
        1. {file_stem}_content_list_v2.json
        2. {safe_stem}_content_list_v2.json
        3. {safe_stem}/{safe_stem}_content_list_v2.json
        4. 回退 glob: *_content_list_v2.json

        Returns:
            V2 原始数据: [[page0_blocks], [page1_blocks], ...]，文件不存在返回 None。
        """
        def _sanitize(name: str) -> str:
            s = re.sub(r"[/\\]{2,}|[/\\]", "", name)
            s = re.sub(r"[^\w.-]", "_", s, flags=re.UNICODE)
            return s.lstrip(".") or "unnamed"

        safe_stem = _sanitize(file_stem)
        candidates = [
            output_dir / f"{file_stem}_content_list_v2.json",
            output_dir / f"{safe_stem}_content_list_v2.json",
            output_dir / safe_stem / f"{safe_stem}_content_list_v2.json",
        ]

        for path in candidates:
            if path.exists():
                logger.info("[custom.mineru_v2] 找到 v2 文件: %s", path)
                try:
                    return json.loads(path.read_text(encoding="utf-8"))
                except Exception as e:
                    logger.error("[custom.mineru_v2] 解析 v2 文件失败: %s, err=%s", path, e)
                    return None

        # 回退 glob
        try:
            for p in output_dir.rglob("*_content_list_v2.json"):
                if p.is_file():
                    logger.info("[custom.mineru_v2] 回退匹配 v2 文件: %s", p)
                    return json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("[custom.mineru_v2] glob 查找 v2 文件失败: %s", e)

        return None

    # ─── 顶层解析入口 ───

    @classmethod
    def parse_content_list(cls, raw_v2_data: list) -> list[V2Block]:
        """
        解析 V2 原始数据，转换为 V2Block 列表。

        V2 格式: [[page0_blocks], [page1_blocks], ...]
        数组下标即 page_idx。

        Args:
            raw_v2_data: [[{page0 block}, ...], [{page1 block}, ...], ...]

        Returns:
            V2Block 列表（保持页面顺序）
        """
        if not isinstance(raw_v2_data, list):
            logger.warning("[custom.mineru_v2] V2 数据顶层不是 list: %s", type(raw_v2_data))
            return []

        blocks = []
        total_pages = len(raw_v2_data)

        for page_idx, page_blocks in enumerate(raw_v2_data):
            if not isinstance(page_blocks, list):
                logger.warning("[custom.mineru_v2] V2 page[%d] 不是 list: %s", page_idx, type(page_blocks))
                continue

            for idx, raw_block in enumerate(page_blocks):
                if not isinstance(raw_block, dict):
                    continue
                try:
                    block = cls._parse_block(raw_block, idx, page_idx)
                    if block:
                        blocks.append(block)
                except Exception as e:
                    logger.error("[custom.mineru_v2] 解析 V2 page[%d].block[%d] 失败: %s",
                                 page_idx, idx, e, exc_info=True)

        logger.info("[custom.mineru_v2] 解析完成: %d 页, %d 个 block", total_pages, len(blocks))
        return blocks

    # ─── 旋转变换 ───

    @staticmethod
    def rotate_bbox(bbox: list, rotate_deg: int) -> list:
        """对 MinerU 归一化 bbox (0-1000) 做 PDF /Rotate 矩阵变换。

        变换公式与 mineru_parser.py 中 V1 的 bbox 变换一致：
        - 90° CW:  [y0, 1000-x1, y1, 1000-x0]
        - 180°:    [1000-x1, 1000-y1, 1000-x0, 1000-y0]
        - 270° CW: [1000-y1, x0, 1000-y0, x1]

        Args:
            bbox: [x0, y0, x1, y1] 归一化坐标
            rotate_deg: PDF /Rotate 角度 (90/180/270)

        Returns:
            变换后的 [x0, y0, x1, y1]，保留 int 类型
        """
        if rotate_deg not in (90, 180, 270) or not bbox or len(bbox) < 4:
            return list(bbox) if bbox else []
        x0, y0, x1, y1 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
        if rotate_deg == 90:
            return [y0, 1000 - x1, y1, 1000 - x0]
        elif rotate_deg == 180:
            return [1000 - x1, 1000 - y1, 1000 - x0, 1000 - y0]
        else:  # 270
            return [1000 - y1, x0, 1000 - y0, x1]

    @classmethod
    def apply_rotation(cls, blocks: list[V2Block], rotate_deg: int) -> list[V2Block]:
        """对所有 block 应用旋转变换，设置 bbox_rotated 字段。

        bbox 保留原始值，bbox_rotated 存储变换后的坐标。
        当 rotate_deg 为 0 或 360 时，不设置 bbox_rotated（保持 None）。

        Args:
            blocks: V2Block 列表
            rotate_deg: PDF /Rotate 角度

        Returns:
            更新了 bbox_rotated 的同一批 blocks（in-place 修改）
        """
        if rotate_deg in (0, 360):
            return blocks
        for block in blocks:
            if block.bbox and len(block.bbox) >= 4:
                block.bbox_rotated = cls.rotate_bbox(block.bbox, rotate_deg)
        logger.info(
            "[custom.mineru_v2] 已对 %d 个 block 应用 %s° 旋转变换（bbox_rotated）",
            len(blocks), rotate_deg,
        )
        return blocks

    @staticmethod
    def detect_auto_rotation(output_dir: str, rotate_deg: int = 0,
                             orig_pdf_path: str = "") -> int:
        """检测 MinerU 自动摆正的旋转角度（0/90/180/270）。

        判定优先级：
        1. PDF /Rotate 元数据（rotate_deg 参数，已是 90/180/270 则直接返回）
        2. MinerU _rotated.pdf 自动摆正（通过比较原始 PDF 和 _rotated.pdf 的
           页面尺寸及 /Rotate 属性综合判断）

        对于 MinerU 自动摆正，通过 pdfplumber 读取原始 PDF 的页面尺寸和 /Rotate：
        - 宽高互换 → 90° CW（MinerU 行为：将横版内容旋转为竖版阅读方向）
        - 宽高相同但 /Rotate=180 → 返回 180（PDF 标准旋转，极少数情况）

        Args:
            output_dir: MinerU 输出目录（包含 _origin.pdf 和 _rotated.pdf）
            rotate_deg: PDF /Rotate 角度（元数据，0/90/180/270。非 0 时优先返回）
            orig_pdf_path: 原始 PDF 路径（退路，output_dir 内找不到 _origin.pdf 时使用）

        Returns:
            最终旋转角度（0/90/180/270）。
        """
        # ── 优先级 1: PDF /Rotate 元数据 ──
        if rotate_deg in (90, 180, 270):
            return rotate_deg

        try:
            import pdfplumber as _p
            from pathlib import Path as _Path
            _dir = _Path(output_dir)

            # 找 _rotated.pdf
            _rotated = None
            for _f in _dir.rglob("*_rotated.pdf"):
                _rotated = _f
                break
            if _rotated is None:
                return 0

            # 找 _origin.pdf（MinerU 的 return_original_file 产物）
            _origin = None
            for _f in _dir.rglob("*_origin.pdf"):
                if "_rotated" not in _f.name:
                    _origin = _f
                    break
            if _origin is None:
                for _f in _dir.rglob("*.pdf"):
                    if "_rotated" not in _f.name and _f != _rotated:
                        _origin = _f
                        break
            if _origin is None and orig_pdf_path:
                _origin = _Path(orig_pdf_path)

            if _origin is None or not _origin.exists():
                logger.warning(
                    "[custom.mineru_v2] 找到 _rotated.pdf 但无法找到原始 PDF 做尺寸对比"
                )
                return 0

            # ── 读取原始 PDF 和 _rotated.pdf 的尺寸与旋转属性 ──
            with _p.open(str(_origin)) as _opdf:
                _op = _opdf.pages[0]
                _ow, _oh = float(_op.width), float(_op.height)
                _orig_rot = getattr(_op, "rotation", 0) or 0
            with _p.open(str(_rotated)) as _rpdf:
                _rw, _rh = float(_rpdf.pages[0].width), float(_rpdf.pages[0].height)

            # ── 优先级 2: 原始 PDF 自身就有 /Rotate（pdfplumber 可读取） ──
            if _orig_rot in (90, 180, 270):
                logger.info(
                    "[custom.mineru_v2] 从原始 PDF _origin.pdf 读取到 /Rotate=%s°",
                    _orig_rot,
                )
                return int(_orig_rot)

            # ── 优先级 3: MinerU 自动摆正（/Rotate=0 但有 _rotated.pdf） ──
            # 通过宽高比判断 90° CW 旋转（origin.pdf 和 _rotated.pdf 可能 DPI 不同）：
            # origin 宽高比 ≈ _rotated 高宽比 → 90° CW
            _o_aspect = _ow / max(_oh, 1)    # origin 宽高比
            _r_aspect = _rw / max(_rh, 1)    # rotated 宽高比
            _aspect_swapped = (
                # 宽高比互换：origin_w/h ≈ rotated_h/w（即 1/_r_aspect）
                abs(_o_aspect - (1.0 / max(_r_aspect, 0.001))) < 0.05
            ) or (
                # 同 DPI 时的绝对尺寸对比（退化情况，精确度高时走此分支）
                abs(_ow - _rh) / max(_ow, _rh, 1) < 0.05
                and abs(_oh - _rw) / max(_oh, _rw, 1) < 0.05
            )

            if _aspect_swapped:
                logger.info(
                    "[custom.mineru_v2] MinerU 90° CW: "
                    "origin=%.0fx%.0f(%.3f) → rotated=%.0fx%.0f(%.3f)",
                    _ow, _oh, _o_aspect, _rw, _rh, _r_aspect,
                )
                return 90
            else:
                logger.info(
                    "[custom.mineru_v2] _rotated.pdf "
                    "origin=%.0fx%.0f(%.3f) rotated=%.0fx%.0f(%.3f) orig_rot=%s",
                    _ow, _oh, _o_aspect, _rw, _rh, _r_aspect, _orig_rot,
                )
                return 0
        except Exception:
            logger.exception("[custom.mineru_v2] 检测自动旋转角度失败")
            return 0

    # ─── 单块解析 ───

    @classmethod
    def _parse_block(cls, raw: dict, idx: int, page_idx: int) -> Optional[V2Block]:
        """解析单个 V2 block。"""
        block_type = (raw.get("type") or "").strip().lower()
        if not block_type:
            return None

        content = raw.get("content", {})
        if not isinstance(content, dict):
            content = {}

        bbox = raw.get("bbox")
        if isinstance(bbox, list) and len(bbox) == 4:
            bbox = [int(v) if v == int(v) else v for v in bbox]
        else:
            bbox = None

        block = V2Block(
            chunk_id="",
            type=block_type,
            bbox=bbox,
            page_idx=page_idx,        # ← V2 的 page_idx 来自数组下标
        )

        # 按实际 V2 类型分发
        _dispatch = {
            "title": cls._parse_title,
            "paragraph": cls._parse_paragraph,
            "list": cls._parse_list,
            "table": cls._parse_table,
            "image": cls._parse_image,
            "page_header": cls._parse_page_header,
            "page_footer": cls._parse_page_footer,
        }

        handler = _dispatch.get(block_type)
        if handler:
            handler(block, content)
        else:
            # 未知类型：尝试提取文本
            block.text = cls._extract_text_from_any(content)

        # 兜底：如果 text 仍为空
        if not block.text:
            block.text = cls._extract_text_from_any(content)

        return block

    # ─── 类型解析方法 ───

    @classmethod
    def _parse_title(cls, block: V2Block, content: dict):
        block.text_level = content.get("level", 1)
        spans = content.get("title_content", [])
        block.span_json = spans
        block.text, block.inline_formula = cls._spans_to_text(spans)

    @classmethod
    def _parse_paragraph(cls, block: V2Block, content: dict):
        spans = content.get("paragraph_content", [])
        block.span_json = spans
        block.text, block.inline_formula = cls._spans_to_text(spans)

    @classmethod
    def _parse_page_header(cls, block: V2Block, content: dict):
        """页眉：V2 类型为 page_header，有 page_header_content。"""
        spans = content.get("page_header_content", [])
        block.span_json = spans
        block.text, block.inline_formula = cls._spans_to_text(spans)

    @classmethod
    def _parse_page_footer(cls, block: V2Block, content: dict):
        """页脚：V2 类型为 page_footer，有 page_footer_content。"""
        spans = content.get("page_footer_content", [])
        block.span_json = spans
        block.text, block.inline_formula = cls._spans_to_text(spans)

    @classmethod
    def _parse_list(cls, block: V2Block, content: dict):
        block.list_type = content.get("list_type", "text_list")
        raw_items = content.get("list_items", [])
        block.span_json = raw_items

        items = []
        full_text_parts = []
        for raw_item in raw_items:
            if not isinstance(raw_item, dict):
                continue
            item_type = raw_item.get("item_type", "text")
            item_spans = raw_item.get("item_content", [])
            item_text, _ = cls._spans_to_text(item_spans)
            items.append({
                "item_type": item_type,
                "item_text": item_text,
                "bbox": raw_item.get("bbox"),
            })
            full_text_parts.append(f"- {item_text}")

        block.list_items = items
        block.text = "\n".join(full_text_parts)

    @classmethod
    def _parse_table(cls, block: V2Block, content: dict):
        """
        解析 V2 表格。

        V2 表格 content 是扁平结构（不是嵌套的 table_content dict）：
        {
            "html": "<table>...</table>",
            "image_source": {"path": "images/xxx.jpg"},
            "table_caption": [...],
            "table_footnote": [...],
            "table_type": "complex_table",
            "table_nest_level": 0
        }
        """
        block.table_html = content.get("html")         # ← V2: content.html, 不是 table_content.html_body
        block.table_caption = content.get("table_caption", [])
        block.table_footnote = content.get("table_footnote", [])
        block.sub_type = content.get("table_type")       # simple_table / complex_table

        # 组装可读文本
        text_parts = []
        cap_text, _ = cls._spans_to_text(block.table_caption or [])
        fn_text, _ = cls._spans_to_text(block.table_footnote or [])
        if cap_text:
            text_parts.append(cap_text)
        if fn_text:
            text_parts.append(fn_text)
        block.text = "\n".join(text_parts) if text_parts else None

        # 图片路径（表格截图）
        img_src = content.get("image_source", {})
        if isinstance(img_src, dict):
            block.img_path = img_src.get("path")

        block.span_json = content

    @classmethod
    def _parse_image(cls, block: V2Block, content: dict):
        """解析 V2 图片。"""
        img_src = content.get("image_source", {})
        if isinstance(img_src, dict):
            block.img_path = img_src.get("path")
        block.content = content.get("content")           # 图片描述（VLM 生成）
        block.image_caption = content.get("image_caption", [])
        block.image_footnote = content.get("image_footnote", [])

        text_parts = []
        if block.content:
            text_parts.append(block.content)
        cap_text, _ = cls._spans_to_text(block.image_caption or [])
        fn_text, _ = cls._spans_to_text(block.image_footnote or [])
        if cap_text:
            text_parts.append(cap_text)
        if fn_text:
            text_parts.append(fn_text)
        block.text = "\n".join(text_parts) if text_parts else None

        block.span_json = {
            "image_source": img_src,
            "image_caption": block.image_caption,
            "image_footnote": block.image_footnote,
        }

    # ─── Span 聚合核心方法 ───

    @classmethod
    def _spans_to_text(cls, spans: list) -> tuple[str, list]:
        """
        将 span 数组转换为纯文本 + 提取内联公式。

        V2 span 类型（从实际数据看目前全是 text，但也保留扩展性）：
        - text: 纯文本
        - inline_equation: 内联公式 LaTeX
        - inline_code: 内联代码
        - phonetic: 拼音标注
        - md: Markdown 格式文本

        Args:
            spans: [{"type": "text", "content": "..."}, ...]

        Returns:
            (纯文本字符串, 内联公式列表)
        """
        if not isinstance(spans, list):
            return "", []

        text_parts = []
        inline_formulas = []
        formula_count = 0

        for span in spans:
            if not isinstance(span, dict):
                continue
            span_type = (span.get("type") or "").strip()
            span_content = span.get("content", "") or ""

            if span_type == "inline_equation":
                text_parts.append(f"${span_content}$")
                inline_formulas.append({
                    "latex": span_content,
                    "position": formula_count,
                })
                formula_count += 1
            elif span_type == "inline_code":
                text_parts.append(f"`{span_content}`")
            else:
                formatter = cls.SPAN_TEXT_FORMATTERS.get(span_type)
                if formatter:
                    text_parts.append(formatter(span))
                else:
                    text_parts.append(str(span_content))

        return "".join(text_parts) if text_parts else "", inline_formulas if inline_formulas else []

    @classmethod
    def _extract_text_from_any(cls, content: dict) -> Optional[str]:
        """从任意 content dict 中尽力提取文本（兜底逻辑）。"""
        if not isinstance(content, dict):
            return None
        for key in ("paragraph_content", "title_content", "page_header_content",
                     "page_footer_content"):
            spans = content.get(key)
            if isinstance(spans, list):
                text, _ = cls._spans_to_text(spans)
                if text:
                    return text
        items = content.get("list_items")
        if isinstance(items, list):
            parts = []
            for item in items:
                if isinstance(item, dict):
                    t, _ = cls._spans_to_text(item.get("item_content", []))
                    if t:
                        parts.append(f"- {t}")
            if parts:
                return "\n".join(parts)
        return None
