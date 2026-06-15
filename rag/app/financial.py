import copy
import re
import os
import json
import logging
from dotenv import load_dotenv
from rag.nlp import rag_tokenizer, tokenize_table, tokenize_chunks, add_positions

from deepdoc.parser.figure_parser import vision_figure_parser_pdf_wrapper
from deepdoc.parser.mineru_parser import MinerUParser, resolve_mineru_api_from_env, normalize_mineru_checkbox_latex
from rag.utils.html_table_parser import convert_html_table

load_dotenv()

TITLE_NUM_RE = re.compile(r'^(\d+(?:\.\d+)*)')

TOC_SECTION_LEVEL = -1

# Common accounting subject names found in Chinese financial report notes.
# These appear as unnumbered sub-headings under "财务报表项目注释" and would
# otherwise be missed by get_section_title_level (no numbering prefix).
_FINANCIAL_NOTE_TITLES = {
    # 资产类
    '货币资金', '应收账款', '应收票据', '预付款项', '其他应收款',
    '存货', '固定资产', '在建工程', '无形资产', '长期待摊费用',
    '递延所得税资产', '商誉', '投资性房地产', '长期股权投资',
    '交易性金融资产', '债权投资', '其他债权投资', '其他权益工具投资',
    '持有待售资产', '使用权资产', '开发支出', '油气资产',
    '应收款项融资', '合同资产', '发出商品', '委托加工物资',
    # 负债类
    '短期借款', '应付账款', '应付票据', '预收款项', '其他应付款',
    '应付职工薪酬', '应交税费', '长期借款', '应付债券',
    '长期应付款', '预计负债', '递延收益', '递延所得税负债',
    '合同负债', '租赁负债', '交易性金融负债',
    # 权益类
    '实收资本', '资本公积', '盈余公积', '未分配利润',
    '其他综合收益', '少数股东权益', '归属于母公司所有者权益',
    '库存股', '专项储备', '一般风险准备',
    # 损益类
    '营业收入', '营业成本', '税金及附加', '销售费用', '管理费用',
    '研发费用', '财务费用', '投资收益', '信用减值损失',
    '资产减值损失', '资产处置收益', '营业外收入', '营业外支出',
    '所得税费用', '其他收益', '公允价值变动收益', '汇兑收益',
    '利息收入', '利息支出', '手续费及佣金收入', '手续费及佣金支出',
    # 现金流量表附注
    '经营活动产生的现金流量', '投资活动产生的现金流量',
    '筹资活动产生的现金流量', '现金及现金等价物',
    # 常见补充
    '关联方关系及其交易', '或有事项', '承诺事项',
    '资产负债表日后事项', '分部报告', '金融工具及其风险',
    '所有者权益变动表', '合并范围的变更', '外币折算',
    '会计政策变更', '会计估计变更', '前期差错更正',
    '其他流动资产', '其他非流动资产', '其他流动负债', '其他非流动负债',
}

# Financial bigrams — if a short text contains one of these, it is likely a
# note heading even if not in _FINANCIAL_NOTE_TITLES.
_FINANCIAL_BIGRAMS = {
    '账款', '票据', '付款', '收款', '借款', '存款', '债券',
    '股权', '公积', '损益', '折旧', '摊销', '减值', '准备',
    '税金', '薪酬', '担保', '承诺', '租赁', '商誉', '专利',
    '商标', '特许', '矿权', '林权', '养殖', '捕捞', '生物',
    '永续', '可转债', '优先股', '期货', '期权', '套期',
}


def _looks_like_financial_note_heading(text):
    """Check if text looks like an unnumbered financial note sub-heading."""
    if not text:
        return False
    stripped = text.strip()
    if not stripped:
        return False
    # Must be short enough to be a heading (not a paragraph)
    if len(stripped) > 20:
        return False
    # Must not look like a regular sentence (no sentence-ending punctuation)
    if re.search(r'[。！？;；]', stripped):
        return False

    # Phase 1: exact match in known titles
    if stripped in _FINANCIAL_NOTE_TITLES:
        return True

    # Phase 2: contains financial bigram (catch titles not in the set)
    for bg in _FINANCIAL_BIGRAMS:
        if bg in stripped:
            return True

    return False


def is_html_table(txt) -> bool:
    if not isinstance(txt, str):
        return False
    lower = txt.lower()
    return ("<table" in lower) and ("<tr" in lower or "<td" in lower)


def normalize_text_for_title(text: str) -> str:
    if not isinstance(text, str):
        return ""
    s = text.strip()
    return re.sub(r"\s+", "", s)


def _looks_like_cover_metadata(text_stripped):
    if re.match(r'^#*\s*\d{4}年', text_stripped):
        return True
    if re.match(r'^#*\s*\d{4}-\d+', text_stripped):
        return True
    return False


def get_section_title_level(text: str) -> int:
    if not isinstance(text, str) or not text.strip():
        return 0
    text_stripped = normalize_text_for_title(text)
    if not text_stripped:
        return 0

    if _looks_like_cover_metadata(text_stripped):
        return 0

    if re.match(r'^#*\s*第[一二三四五六七八九十百千\d]+[节章条]', text_stripped):
        return 1

    m = re.match(r'^#*\s*(\d+\.\d+(?:\.\d+)*)', text_stripped)
    if m:
        return m.group(1).count('.') + 1

    level2_patterns = [
        r'^\d+[\.、](?!\d)',
        r'^[（(][一二三四五六七八九十]+[）)](?!\d)',
        r'^第[一二三四五六七八九十百千\d]+条',
    ]

    level3_patterns = [
        r'^\d+\.\d(?!\d)',
        r'^（\d+）',
        r'^\d+）',
    ]

    level4_patterns = [
        r'^\d+\.\d+\.\d+',
    ]

    level1_patterns = [
        r'^[一二三四五六七八九十]',
    ]

    for pattern in level4_patterns:
        if re.match(pattern, text_stripped):
            return 4

    for pattern in level3_patterns:
        if re.match(pattern, text_stripped):
            return 3

    for pattern in level2_patterns:
        if re.match(pattern, text_stripped):
            return 2

    for pattern in level1_patterns:
        if re.match(pattern, text_stripped):
            return 1

    m = TITLE_NUM_RE.match(text_stripped)
    if m:
        dot_count = m.group(1).count('.')
        if dot_count >= 3:
            return dot_count + 1

    if _looks_like_financial_note_heading(text_stripped):
        return 2

    return 0


def strip_position_stamp(text):
    return re.sub(r'@@\d+(?:\s+[+-]?\d+(?:\.\d+)?){4}##', '', text)


def _docs_have_content(docs):
    for item in docs or []:
        text = item.get("content_with_weight") if isinstance(item, dict) else None
        if isinstance(text, str) and text.strip():
            return True
    return False


def _fallback_general_docs(filename, binary, lang, callback, kwargs, reason):
    from rag.app import naive as naive_app
    from rag.app import picture as picture_app

    parser_config = copy.deepcopy(kwargs.get("parser_config") or {})
    last_exc = None

    if callback:
        callback(0.2, f"{reason} Falling back to stable parser.")

    if re.search(r"\.pdf$", filename, re.IGNORECASE):
        layouts = []
        preferred = str(parser_config.get("layout_recognize", "")).strip()
        for layout in [preferred, "DeepDOC", "Plain Text"]:
            if layout and layout != "MinerU" and layout not in layouts:
                layouts.append(layout)

        for layout in layouts:
            fallback_kwargs = dict(kwargs)
            fallback_conf = copy.deepcopy(parser_config)
            fallback_conf["layout_recognize"] = layout
            fallback_kwargs["parser_config"] = fallback_conf
            try:
                docs = naive_app.chunk(
                    filename,
                    binary=binary,
                    lang=lang,
                    callback=callback,
                    **fallback_kwargs,
                ) or []
                if _docs_have_content(docs):
                    logging.info("Fallback parser succeeded for %s with layout_recognize=%s", filename, layout)
                    return docs
            except Exception as exc:
                last_exc = exc
                logging.exception("Fallback parser failed for %s with layout_recognize=%s", filename, layout)

    elif re.search(r"\.(jpe?g|png)$", filename, re.IGNORECASE):
        tenant_id = kwargs.get("tenant_id")
        if tenant_id is not None:
            fallback_kwargs = dict(kwargs)
            fallback_conf = copy.deepcopy(parser_config)
            fallback_conf["layout_recognize"] = "OCR"
            fallback_kwargs["parser_config"] = fallback_conf
            try:
                docs = picture_app.chunk(
                    filename,
                    binary=binary,
                    tenant_id=tenant_id,
                    lang=lang,
                    callback=callback,
                    **fallback_kwargs,
                ) or []
                if _docs_have_content(docs):
                    logging.info("Fallback picture parser succeeded for %s", filename)
                    return docs
            except Exception as exc:
                last_exc = exc
                logging.exception("Fallback picture parser failed for %s", filename)
    else:
        fallback_kwargs = dict(kwargs)
        fallback_conf = copy.deepcopy(parser_config)
        fallback_conf["layout_recognize"] = "DeepDOC"
        fallback_kwargs["parser_config"] = fallback_conf
        try:
            docs = naive_app.chunk(
                filename,
                binary=binary,
                lang=lang,
                callback=callback,
                **fallback_kwargs,
            ) or []
            if _docs_have_content(docs):
                logging.info("Fallback generic parser succeeded for %s", filename)
                return docs
        except Exception as exc:
            last_exc = exc
            logging.exception("Fallback generic parser failed for %s", filename)

    if last_exc:
        logging.warning("Fallback parser produced no content for %s after error: %s", filename, last_exc)
    return []


def _collect_positions_from_docs(docs):
    poss = []
    for item in docs or []:
        if not isinstance(item, dict):
            continue
        for pos in item.get("position_int") or []:
            if isinstance(pos, (list, tuple)) and len(pos) >= 5:
                poss.append(tuple(pos[:5]))
    return poss


def _collapse_to_single_chunk(docs, doc, eng):
    merged = []
    for item in docs or []:
        if not isinstance(item, dict):
            continue
        text = item.get("content_with_weight")
        if isinstance(text, str) and text.strip():
            merged.append(text.strip())

    if not merged:
        return []

    chunk_docs = tokenize_chunks(["\n".join(merged)], doc, eng)
    poss = _collect_positions_from_docs(docs)
    if poss:
        add_positions(chunk_docs[0], poss)
    else:
        chunk_docs[0]["position_int"] = []
        chunk_docs[0]["page_num_int"] = []
        chunk_docs[0]["top_int"] = []
    return chunk_docs


def _detect_title_kind(text_stripped):
    if not text_stripped:
        return None
    if _looks_like_cover_metadata(text_stripped):
        return None
    if re.match(r'^#*\s*第[一二三四五六七八九十百千\d]+[节章条]', text_stripped):
        return "section"
    if re.match(r'^#*\s*[一二三四五六七八九十]+[、．.]', text_stripped):
        return "cn_num"
    if re.match(r'^#*\s*[（(][一二三四五六七八九十]+[）)]', text_stripped):
        return "cn_paren"
    m = re.match(r'^#*\s*(\d+(?:\.\d+)+)', text_stripped)
    if m:
        seg_count = m.group(1).count('.') + 1
        return f"digit_x{seg_count}"
    if re.match(r'^#*\s*\d+[、．.]', text_stripped):
        return "digit_dot"
    if _looks_like_financial_note_heading(text_stripped):
        return "note"
    if get_section_title_level(text_stripped) > 0:
        return "other"
    return None


def _induce_dynamic_level_map(mineru_sections, scan_start, scan_end):
    kind_depth = {}
    stack = []
    level_map = {}
    for i in range(scan_start, scan_end):
        if i < 0 or i >= len(mineru_sections):
            continue
        item = mineru_sections[i]
        text = _section_text(item)
        if not text.strip() or is_html_table(text):
            continue
        text_stripped = normalize_text_for_title(text)
        kind = _detect_title_kind(text_stripped)
        if kind is None:
            continue
        if kind in kind_depth:
            depth = kind_depth[kind]
        else:
            if not stack:
                depth = 1
            else:
                depth = stack[-1][2] + 1
            kind_depth[kind] = depth
        while stack and stack[-1][2] >= depth:
            stack.pop()
        stack.append((i, text_stripped, depth, kind))
        level_map[i] = depth
    return level_map


def _extract_label_for_toc_item(stripped):
    if not stripped:
        return None
    text_stripped = normalize_text_for_title(stripped)
    m = re.match(r'^#*\s*(第[一二三四五六七八九十百千\d]+[节章条])', text_stripped)
    if m:
        return m.group(1)
    m = re.match(r'^#*\s*(\d+\.\d+(?:\.\d+)*)', text_stripped)
    if m:
        return m.group(1)
    m = re.match(r'^#*\s*([一二三四五六七八九十]+)[、．.]', text_stripped)
    if m:
        return m.group(1)
    m = re.match(r'^#*\s*[（(]([一二三四五六七八九十]+)[）)]', text_stripped)
    if m:
        return '（' + m.group(1) + '）'
    m = re.match(r'^#*\s*(\d+)[、．.]', text_stripped)
    if m:
        return m.group(1) + '.'
    parts = stripped.split()
    if parts:
        raw_label = parts[0]
        if raw_label.startswith("#"):
            sub = stripped.split(None, 1)
            raw_label = sub[1].split()[0] if len(sub) > 1 else raw_label.lstrip("#")
        return re.sub(r'[、，：:\.]$', '', raw_label)
    return None


def _toc_items_from_induced_outline(mineru_sections, level_map, scan_start, scan_end):
    items = []
    for i in range(scan_start, scan_end):
        if i not in level_map:
            continue
        text = _section_text(mineru_sections[i]).strip()
        if not text:
            continue
        items.append({
            "label": _extract_label_for_toc_item(text),
            "title": text,
            "induced_depth": level_map[i],
        })
    return items


def build_tree_from_induced_items(items):
    root = TocNode(title="root", depth=0)
    stack = [root]
    for item in items:
        depth = item.get("induced_depth") or 1
        node = TocNode(
            title=item.get("title", ""),
            label=item.get("label"),
            depth=depth,
            page_start=0,
            contains_table=item.get("contains_table", False),
        )
        while stack and stack[-1].depth >= node.depth:
            stack.pop()
        stack[-1].children.append(node)
        node.parent = stack[-1]
        stack.append(node)
    return root


def _induction_scan_start(toc_start_idx, body_start_idx):
    if toc_start_idx >= 0:
        return max(body_start_idx, 0)
    return 0


def _in_toc_range(idx, toc_start_idx, body_start_idx):
    return toc_start_idx >= 0 and toc_start_idx <= idx < body_start_idx


def _repack_section_item(item, new_level):
    text = item[0] if len(item) >= 1 else ""
    chunk_id = item[3] if len(item) >= 4 else ""
    pos_tag = item[1] if len(item) >= 2 else None
    return (text, pos_tag, new_level, chunk_id)


def _apply_induced_dynamic_levels(mineru_sections, toc_start_idx, body_start_idx):
    scan_start = _induction_scan_start(toc_start_idx, body_start_idx)
    scan_end = len(mineru_sections)
    level_map = _induce_dynamic_level_map(mineru_sections, scan_start, scan_end)
    if not level_map:
        return mineru_sections, level_map, False

    updated = []
    for i, item in enumerate(mineru_sections):
        text = _section_text(item)
        if _in_toc_range(i, toc_start_idx, body_start_idx):
            if not text.strip():
                updated.append(item)
            else:
                updated.append(_repack_section_item(item, TOC_SECTION_LEVEL))
            continue
        if not text.strip() or is_html_table(text):
            updated.append(item)
            continue
        if i in level_map:
            new_level = level_map[i]
        elif toc_start_idx >= 0 and i < toc_start_idx:
            new_level = get_section_title_level(text)
            if _looks_like_cover_metadata(normalize_text_for_title(text)):
                new_level = 0
        else:
            new_level = get_section_title_level(text)
        updated.append(_repack_section_item(item, new_level))
    return updated, level_map, True


def _tree_display_title(node):
    title = (node.title or "").strip()
    if title and title not in ("root", "__leaf_root__"):
        return title
    label = node.label
    if label:
        return str(label).strip()
    return ""


def _tree_outline_lines(node, outline_depth=0):
    lines = []
    display = _tree_display_title(node)
    if node.title != "root" and display:
        suffix = " [表格]" if node.contains_table else ""
        if outline_depth == 0:
            lines.append(f"{display}{suffix}")
        else:
            indent = "    " * outline_depth
            lines.append(f"{indent}{display}{suffix}")
    is_chapter = node.title != "root" and outline_depth == 0
    for child in node.children:
        lines.extend(_tree_outline_lines(child, outline_depth + 1))
    if is_chapter and node.children:
        lines.append("")
    return lines


def _tree_to_outline_text(toc_root):
    lines = []
    for child in toc_root.children:
        lines.extend(_tree_outline_lines(child, 0))
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def _tree_nodes_for_level_map(toc_root):
    nodes = []

    def walk(node):
        if node.title != "root":
            nodes.append({
                "depth": node.depth,
                "mineru_index": node.mineru_index_start,
            })
        for child in node.children:
            walk(child)

    walk(toc_root)
    return nodes


def _tree_level_by_index_from_nodes(tree_nodes):
    level_by_index = {}
    if not tree_nodes:
        return level_by_index
    for node in tree_nodes:
        idx = node.get("mineru_index")
        if idx is None or idx < 0:
            continue
        level_by_index[idx] = node.get("depth") or 1
    return level_by_index


def _apply_tree_levels_to_sections(mineru_sections, tree_level_by_index, level_map, toc_start_idx, body_start_idx):
    updated = []
    for i, item in enumerate(mineru_sections):
        text = _section_text(item)
        if _in_toc_range(i, toc_start_idx, body_start_idx):
            if not text.strip():
                updated.append(item)
            else:
                updated.append(_repack_section_item(item, TOC_SECTION_LEVEL))
            continue
        if not text.strip() or is_html_table(text):
            updated.append(item)
            continue
        if i in tree_level_by_index:
            new_level = tree_level_by_index[i]
        elif i in level_map:
            new_level = level_map[i]
        elif toc_start_idx >= 0 and i < toc_start_idx:
            new_level = get_section_title_level(text)
            if _looks_like_cover_metadata(normalize_text_for_title(text)):
                new_level = 0
        else:
            new_level = 0
        updated.append(_repack_section_item(item, new_level))
    return updated


def _sync_sections_title_levels(sections, mineru_sections):
    synced = []
    for idx, sec in enumerate(sections):
        lvl = sec[3] if len(sec) >= 4 else 0
        if idx < len(mineru_sections) and len(mineru_sections[idx]) >= 3:
            lvl = mineru_sections[idx][2]
        if len(sec) >= 5:
            synced.append((sec[0], sec[1], sec[2], lvl, sec[4]))
        elif len(sec) >= 4:
            synced.append((sec[0], sec[1], sec[2], lvl))
        else:
            synced.append(sec)
    return synced


class TocNode:
    def __init__(self, title, label=None, depth=0, page_start=0, contains_table=False):
        self.title = title
        self.label = label
        self.depth = depth
        self.page_start = page_start
        self.page_end = 0
        self.children = []
        self.parent = None
        self.mineru_index_start = -1
        self.mineru_index_end = -1
        self.contains_table = contains_table
        self.has_embedded_parent_title = False


def normalize_heading(s):
    """Strip numbering/prefix patterns from a heading, leaving only the semantic title."""
    if not s:
        return ""
    s = s.strip()
    # 第X节/章/条
    s = re.sub(r'^第[一二三四五六七八九十百千\d]+[节章条]\s*', '', s)
    # （一）/ (一) / （1）/ (1)
    s = re.sub(r'^[（(][一二三四五六七八九十\d]+[）)]\s*', '', s)
    # 1. / 1.1 / 1.1.1 / 1、
    s = re.sub(r'^\d+(?:\.\d+)*[\.、]\s*', '', s)
    # 一、/ 二、
    s = re.sub(r'^[一二三四五六七八九十]+[、，]\s*', '', s)
    # # headers
    s = re.sub(r'^#+\s*', '', s)
    return s.strip()


def _fuzzy_match_title(toc_title, text):
    if not toc_title or not text:
        return False

    def _normalize(s):
        s = re.sub(r'[\.、．\s]', '', s)
        s = re.sub(r'[（(]', '(', s)
        s = re.sub(r'[）)]', ')', s)
        return s

    # Phase 1: strict startswith (handles page-number rejection in TOC lines)
    nt = _normalize(text)
    ntt = _normalize(toc_title)
    if nt.startswith(ntt):
        remaining = nt[len(ntt):]
        if not re.match(r'^[\s.]*\d{1,4}[\s.]*$', remaining):
            return True

    # Phase 2: strip numbering prefixes, compare semantic titles
    # Handles cases like:
    #   TOC: "一、货币资金"  vs  body: "（一）货币资金"
    #   TOC: "货币资金"      vs  body: "五、货币资金"
    norm_toc = normalize_heading(toc_title)
    norm_text = normalize_heading(text)
    if norm_toc and norm_text and norm_toc in norm_text:
        idx = norm_text.index(norm_toc)
        remaining = norm_text[idx + len(norm_toc):]
        # Reject TOC lines that end with page numbers
        # e.g. TOC title "货币资金" vs text "第一节 货币资金 15" → remaining = " 15"
        if re.match(r'^\s*\.{0,3}\s*\d{1,4}\s*$', remaining):
            return False
        return True

    return False


def _find_title_in_sections(title, sections, start_idx=0):
    for i in range(start_idx, len(sections)):
        item = sections[i]
        text = (item[0] if len(item) >= 1 else "").strip()
        if _fuzzy_match_title(title, text):
            return i
    return -1


def _fix_toc_with_inline_titles(toc_root, mineru_sections):
    def _walk_start(node, start_search_idx):
        if node.title != "root":
            idx = _find_title_in_sections(node.title, mineru_sections, start_search_idx)
            if idx >= 0:
                node.mineru_index_start = idx
            # else: leave as -1 — a fake start is more dangerous than a missing one

        next_start = node.mineru_index_start if node.mineru_index_start >= 0 else start_search_idx
        for child in node.children:
            _walk_start(child, next_start)
            if child.mineru_index_start >= 0:
                next_start = child.mineru_index_start

    _walk_start(toc_root, 0)

    def _fill_inline_children(node):
        if node.children:
            for child in node.children:
                _fill_inline_children(child)

        if node.children or node.mineru_index_start < 0:
            return

        scan_end = len(mineru_sections)

        if node.parent and node.parent.children:
            siblings = node.parent.children
            for si, sib in enumerate(siblings):
                if sib is node and si + 1 < len(siblings):
                    nxt = siblings[si + 1].mineru_index_start
                    if nxt >= 0:
                        scan_end = nxt
                    break

        if node.mineru_index_start >= 0:
            node_level = _section_title_level(mineru_sections[node.mineru_index_start])
        else:
            node_level = get_section_title_level(node.title)

        headings = []

        for i in range(node.mineru_index_start + 1, scan_end):
            item = mineru_sections[i]
            text = item[0] if len(item) >= 1 else ""
            lvl = _section_title_level(item)

            if lvl <= 0:
                continue

            if node_level > 0 and lvl <= node_level:
                break

            headings.append((i, text.strip(), lvl))

        if not headings:
            return

        stack = [TocNode(title="__leaf_root__", depth=0)]
        child_nodes = []

        for idx, h_text, h_lvl in headings:
            child = TocNode(
                title=h_text,
                depth=h_lvl,
                page_start=0
            )

            child.mineru_index_start = idx

            if node.title and node.title != "__leaf_root__":
                section_text = mineru_sections[idx][0] if idx < len(mineru_sections) and len(mineru_sections[idx]) >= 1 else ""
                if section_text:
                    norm_section = normalize_text_for_title(section_text)
                    norm_parent = normalize_text_for_title(node.title)
                    if norm_section.startswith(norm_parent) and norm_section != norm_parent:
                        child.has_embedded_parent_title = True

            while stack and stack[-1].depth >= h_lvl:
                stack.pop()

            stack[-1].children.append(child)
            child.parent = stack[-1]

            stack.append(child)
            child_nodes.append(child)

        node.children = child_nodes

        for child in node.children:
            _fill_inline_children(child)

    _fill_inline_children(toc_root)

    def _walk_end(node):
        for i, child in enumerate(node.children):

            if i + 1 < len(node.children):
                nxt_start = node.children[i + 1].mineru_index_start
                if nxt_start >= 0 and nxt_start > child.mineru_index_start:
                    child.mineru_index_end = nxt_start
                # else: next sibling shares same start or is invalid —
                # leave child's end unset, _finalize_node_ends will fill it

            elif node.mineru_index_end >= 0:
                child.mineru_index_end = node.mineru_index_end

            else:
                child.mineru_index_end = len(mineru_sections)

            _walk_end(child)

    toc_root.mineru_index_start = 0
    toc_root.mineru_index_end = len(mineru_sections)
    _walk_end(toc_root)

    def _finalize_node_ends(node, fallback_end):
        for child in node.children:
            _finalize_node_ends(child, fallback_end)

        if not node.children:
            if node.mineru_index_end < 0:
                node.mineru_index_end = fallback_end
            return

        child_end = max(
            (
                c.mineru_index_end
                for c in node.children
                if c.mineru_index_end >= 0
            ),
            default=fallback_end
        )

        if node.mineru_index_end < 0:
            node.mineru_index_end = child_end
        elif node.mineru_index_end <= node.mineru_index_start and child_end > node.mineru_index_end:
            # end was poisoned by sibling start collision; override with children's extent
            node.mineru_index_end = child_end
        else:
            node.mineru_index_end = min(
                node.mineru_index_end,
                child_end
            )

    _finalize_node_ends(toc_root, len(mineru_sections))

    def _is_ancestor(a, b):
        cur = b.parent
        while cur:
            if cur is a:
                return True
            cur = cur.parent
        return False

    def _collect_nodes(node, result):
        if node is not toc_root:
            result.append(node)
        for child in node.children:
            _collect_nodes(child, result)

    all_nodes = []
    _collect_nodes(toc_root, all_nodes)
    all_nodes.sort(
        key=lambda n: (
            n.mineru_index_start,
            n.depth
        )
    )

    for i in range(len(all_nodes) - 1):

        cur = all_nodes[i]

        if cur.mineru_index_start < 0:
            continue

        for j in range(i + 1, len(all_nodes)):

            nxt = all_nodes[j]

            if nxt.mineru_index_start < 0:
                continue

            if _is_ancestor(cur, nxt):
                continue

            if nxt.mineru_index_start <= cur.mineru_index_start:
                continue

            if (
                cur.mineru_index_end < 0
                or cur.mineru_index_end > nxt.mineru_index_start
            ):
                cur.mineru_index_end = nxt.mineru_index_start

            break

    for node in all_nodes:

        if node.mineru_index_start < 0:
            continue

        if node.mineru_index_end <= node.mineru_index_start:

            node.mineru_index_end = min(
                node.mineru_index_start + 1,
                len(mineru_sections)
            )

    return toc_root


_MAIN_TABLE_TITLE_RULES = (
    ("合并资产负债表", "合并资产负债表"),
    ("合并利润表", "合并利润表"),
    ("合并现金流量表", "合并现金流量表"),
    ("资产负债表", "资产负债表"),
    ("利润表", "利润表"),
    ("现金流量表", "现金流量表"),
)
_NOTE_TITLE_KEYWORDS = ("附注", "注释")


def _build_cross_ref_from_toc_items(toc_items):
    if not toc_items:
        return None
    main_tables = []
    note_titles = []
    seen_tables = set()
    for i, item in enumerate(toc_items):
        title = (item.get("title") or "").strip()
        if not title:
            continue
        if any(kw in title for kw in _NOTE_TITLE_KEYWORDS):
            note_titles.append(title)
            continue
        for pattern, canonical in _MAIN_TABLE_TITLE_RULES:
            if pattern in title and canonical not in seen_tables:
                seen_tables.add(canonical)
                main_tables.append({"title": canonical, "index": i})
                break
    if not main_tables and not note_titles:
        return None
    table_names = [t["title"] for t in main_tables]
    note_to_table_mapping = {note: list(table_names) for note in note_titles} if table_names else {}
    return {"main_tables": main_tables, "note_to_table_mapping": note_to_table_mapping}


def _is_noise_section(text):
    if not text or not str(text).strip():
        return True
    return False


def _merge_table_with_adjacent(content_sections):
    merged = []
    for item in content_sections:
        text = item[0] if len(item) >= 1 else str(item)
        merged.append(text)
    return '\n'.join(merged)


def _section_text(item):
    raw = item[0] if len(item) >= 1 else str(item)
    return normalize_mineru_checkbox_latex(raw)


def _section_title_level(item):
    text = _section_text(item)
    if len(item) >= 3:
        return item[2]
    return get_section_title_level(text)


def _display_depth_tag(item):
    """日志用：展示块在目录树/诱导后的结构 depth（非静态标题 level）。"""
    text = _section_text(item)
    if not text or not str(text).strip():
        return "空"
    if len(item) >= 3 and item[2] == TOC_SECTION_LEVEL:
        return "toc"
    if is_html_table(text):
        return "tab"
    return _section_title_level(item)


def _display_title_level_tag(item):
    """日志用：展示 get_section_title_level 的静态标题层级（0~4）。"""
    text = _section_text(item)
    if not text or not str(text).strip():
        return "空"
    if is_html_table(text):
        return "tab"
    return get_section_title_level(text)


def _depths_display_for_range(mineru_sections, start, end):
    tags = []
    for i in range(start, end):
        if 0 <= i < len(mineru_sections):
            tags.append(_display_depth_tag(mineru_sections[i]))
    return tags


def _section_page(item):
    pos_tag = item[1] if len(item) >= 2 else None
    if not pos_tag:
        return None
    for tag in re.findall(r"@@([0-9-]+)\t[0-9.\t]+##", str(pos_tag)):
        try:
            return int(tag.split("-")[0]) - 1
        except (TypeError, ValueError):
            continue
    return None


def _is_level0_or_table_section(item):
    text = _section_text(item)
    if is_html_table(text):
        return True
    if _is_noise_section(text):
        return True
    return _section_title_level(item) <= 0


def _scan_inline_enum_patterns(mineru_sections, range_start, range_end):
    patterns = []
    i = range_start
    while i < range_end:
        item = mineru_sections[i]
        text = _section_text(item)
        if _is_noise_section(text):
            i += 1
            continue
        if is_html_table(text):
            i += 1
            continue
        run_level = _section_title_level(item)
        if run_level <= 0:
            i += 1
            continue
        run_start = i
        j = i + 1
        while j < range_end:
            cur = mineru_sections[j]
            cur_text = _section_text(cur)
            if _is_noise_section(cur_text):
                j += 1
                continue
            if is_html_table(cur_text):
                break
            if _section_title_level(cur) == run_level:
                j += 1
            else:
                break
        if j - run_start < 2:
            i += 1
            continue
        block_start = run_start
        k = run_start - 1
        while k >= range_start and _is_level0_or_table_section(mineru_sections[k]):
            block_start = k
            k -= 1
        last_title_idx = j - 1
        body2_start = j
        if body2_start >= range_end:
            i = j
            continue
        while body2_start < range_end and _is_noise_section(_section_text(mineru_sections[body2_start])):
            body2_start += 1
        if body2_start >= range_end:
            i = j
            continue
        body2_item = mineru_sections[body2_start]
        if is_html_table(_section_text(body2_item)):
            i = j
            continue
        if _section_title_level(body2_item) == run_level:
            i = j
            continue
        last_title_page = _section_page(mineru_sections[last_title_idx])
        body2_page = _section_page(body2_item)
        if last_title_page is None or body2_page is None or last_title_page != body2_page:
            i = j
            continue
        block_end = body2_start + 1
        t = body2_start + 1
        while t < range_end:
            tail = mineru_sections[t]
            if not _is_level0_or_table_section(tail):
                break
            tail_page = _section_page(tail)
            if tail_page is None or tail_page != body2_page:
                break
            block_end = t + 1
            t += 1
        patterns.append({
            "block_start": block_start,
            "block_end": block_end,
            "run_start": run_start,
            "run_end": j,
        })
        i = block_end
    return patterns


def _demote_inline_enum_titles_for_tree(mineru_sections, level_map, patterns):
    if not patterns or not level_map:
        return mineru_sections, level_map
    demote = set()
    for pattern in patterns:
        for idx in range(pattern["run_start"], pattern["run_end"]):
            if idx in level_map:
                demote.add(idx)
    if not demote:
        return mineru_sections, level_map
    new_map = {idx: lvl for idx, lvl in level_map.items() if idx not in demote}
    updated = []
    for i, item in enumerate(mineru_sections):
        if i in demote:
            updated.append(_repack_section_item(item, 0))
        else:
            updated.append(item)
    return updated, new_map


def _join_sections_range(mineru_sections, start, end):
    parts = []
    for item in mineru_sections[start:end]:
        text = _section_text(item)
        if not _is_noise_section(text):
            parts.append(text)
    return "\n".join(parts)


def _titles_in_index_range(mineru_sections, start, end):
    stack = []
    for idx in range(start, end):
        if idx < 0 or idx >= len(mineru_sections):
            continue
        item = mineru_sections[idx]
        text = _section_text(item)
        if _is_noise_section(text):
            continue
        level = _section_title_level(item)
        if level <= 0:
            continue
        stripped = text.strip()
        if not stripped:
            continue
        while stack and stack[-1][1] >= level:
            stack.pop()
        stack.append((stripped, level))
    return [t[0] for t in stack]


def _collect_logical_units(
    mineru_sections, range_start, range_end, unit_stop_depth=1, use_toc_unit_stop=False, toc_kind_depth=None,
):
    units = []
    i = range_start
    seen_d1 = False
    last_d1_idx = None

    def _advance_noise(idx):
        while idx < range_end and _is_noise_section(_section_text(mineru_sections[idx])):
            idx += 1
        return idx

    def _extend_until_tree_stop(start, stop_depth):
        j = start + 1
        while j < range_end:
            if _is_noise_section(_section_text(mineru_sections[j])):
                j += 1
                continue
            d = _section_title_level(mineru_sections[j])
            if d == TOC_SECTION_LEVEL or d == stop_depth:
                break
            j += 1
        return j

    def _extend_until_toc_stop(start, stop_depth, kind_depth):
        j = start + 1
        while j < range_end:
            if _is_noise_section(_section_text(mineru_sections[j])):
                j += 1
                continue
            d = _section_title_level(mineru_sections[j])
            if d == TOC_SECTION_LEVEL:
                break
            toc_d = _toc_depth_for_text(_section_text(mineru_sections[j]), kind_depth)
            if toc_d == stop_depth:
                break
            j += 1
        return j

    while i < range_end:
        i = _advance_noise(i)
        if i >= range_end:
            break

        depth = _section_title_level(mineru_sections[i])

        if depth == TOC_SECTION_LEVEL:
            s = i
            i += 1
            while i < range_end:
                if _is_noise_section(_section_text(mineru_sections[i])):
                    i += 1
                    continue
                if _section_title_level(mineru_sections[i]) != TOC_SECTION_LEVEL:
                    break
                i += 1
            units.append({"type": "toc", "start": s, "end": i})
            continue

        if not seen_d1 and depth <= 0:
            s = i
            i += 1
            while i < range_end:
                if _is_noise_section(_section_text(mineru_sections[i])):
                    i += 1
                    continue
                d = _section_title_level(mineru_sections[i])
                if d == TOC_SECTION_LEVEL:
                    break
                if d > 0:
                    break
                i += 1
            units.append({"type": "leading_zero", "start": s, "end": i})
            continue

        if use_toc_unit_stop and toc_kind_depth:
            toc_d = _toc_depth_for_text(_section_text(mineru_sections[i]), toc_kind_depth)
            if toc_d > 0:
                s = i
                i = _extend_until_toc_stop(s, unit_stop_depth, toc_kind_depth)
                units.append({"type": "orphan", "start": s, "end": i})
                continue

        if not seen_d1 and depth > 0 and depth != 1:
            s = i
            i = _extend_until_tree_stop(s, unit_stop_depth)
            units.append({"type": "orphan", "start": s, "end": i})
            continue

        if depth == 1:
            seen_d1 = True
            last_d1_idx = i
            s = i
            i += 1
            while i < range_end:
                if _is_noise_section(_section_text(mineru_sections[i])):
                    i += 1
                    continue
                d = _section_title_level(mineru_sections[i])
                if d == TOC_SECTION_LEVEL:
                    break
                if d == 1:
                    break
                i += 1
            units.append({"type": "d1_unit", "start": s, "end": i, "anchor": s})
            continue

        if seen_d1 and depth <= 0:
            s = i
            i += 1
            while i < range_end:
                if _is_noise_section(_section_text(mineru_sections[i])):
                    i += 1
                    continue
                d = _section_title_level(mineru_sections[i])
                if d == TOC_SECTION_LEVEL or d == 1:
                    break
                i += 1
            units.append({
                "type": "d1_continuation",
                "start": s,
                "end": i,
                "anchor": last_d1_idx if last_d1_idx is not None else s,
            })
            continue

        if seen_d1 and depth > 1:
            s = i
            i = _extend_until_tree_stop(s, unit_stop_depth)
            units.append({"type": "orphan", "start": s, "end": i})
            continue

        if not seen_d1:
            s = i
            i += 1
            while i < range_end:
                if _is_noise_section(_section_text(mineru_sections[i])):
                    i += 1
                    continue
                if _section_title_level(mineru_sections[i]) == TOC_SECTION_LEVEL:
                    break
                i += 1
            units.append({"type": "no_d1_body", "start": s, "end": i})
            continue

        i += 1

    return units


def _unit_parent_chain(mineru_sections, unit_start, chunk_end_exclusive, chain_start=None):
    if chunk_end_exclusive <= unit_start:
        return []
    start = chain_start if chain_start is not None else unit_start
    return _titles_in_index_range(mineru_sections, start, chunk_end_exclusive)


def _split_logical_unit_into_chunks(mineru_sections, unit_start, unit_end, token_budget, unit_type, chain_start=None, tab_text_map=None):
    from common.token_utils import num_tokens_from_string, split_text_by_token_budget

    if unit_start >= unit_end:
        return []

    _tab_map = tab_text_map or {}
    pieces = []
    for idx in range(unit_start, unit_end):
        item = mineru_sections[idx]
        text = _section_text(item)
        if _is_noise_section(text):
            continue
        body = text.strip()
        if not body:
            continue
        if is_html_table(body):
            es_text, llm_text = _tab_map.get(idx, (body, body))
            pieces.append({"indices": [idx], "text": es_text, "tokens": num_tokens_from_string(es_text), "atomic": True, "llm_text": llm_text})
            continue
        tokens = num_tokens_from_string(body)
        if tokens <= token_budget:
            pieces.append({"indices": [idx], "text": body, "tokens": tokens, "atomic": False})
        else:
            for part in split_text_by_token_budget(body, token_budget):
                if part.strip():
                    pieces.append({
                        "indices": [idx],
                        "text": part,
                        "tokens": num_tokens_from_string(part),
                        "atomic": False,
                    })

    if not pieces:
        return []

    chunks = []
    buf_texts = []
    buf_llm_texts = []
    buf_indices = set()
    buf_tokens = 0
    buf_has_table = False

    def _flush_buffer():
        nonlocal buf_texts, buf_llm_texts, buf_indices, buf_tokens, buf_has_table
        if not buf_texts:
            return
        chunk_start = min(buf_indices)
        chunk_end = max(buf_indices) + 1
        chain = [] if unit_type == "toc" else _unit_parent_chain(
            mineru_sections, unit_start, chunk_end, chain_start=chain_start,
        )
        table_prefix = ""
        if buf_has_table and chain and unit_type != "toc":
            leaf_title = chain[-1] if chain else ""
            if leaf_title:
                table_prefix = f"[{leaf_title}]\n"
        chunks.append({
            "content": table_prefix + "\n".join(buf_texts),
            "parent_chain": chain,
            "mineru_range": (chunk_start, chunk_end),
            "llm_content": "\n".join(buf_llm_texts) if buf_llm_texts else "",
        })
        buf_texts = []
        buf_llm_texts = []
        buf_indices = set()
        buf_tokens = 0
        buf_has_table = False

    for piece in pieces:
        piece_tokens = piece["tokens"]
        join_cost = 1 if buf_texts else 0
        if piece.get("atomic") and buf_texts and buf_tokens + join_cost + piece_tokens > token_budget:
            _flush_buffer()
        elif not piece.get("atomic") and buf_texts and buf_tokens + join_cost + piece_tokens > token_budget:
            _flush_buffer()

        if not buf_texts and piece_tokens > token_budget:
            buf_texts.append(piece["text"])
            buf_indices.update(piece["indices"])
            if piece.get("llm_text"):
                buf_llm_texts.append(piece["llm_text"])
                buf_has_table = True
            else:
                buf_llm_texts.append(piece["text"])
            _flush_buffer()
            continue

        buf_texts.append(piece["text"])
        buf_indices.update(piece["indices"])
        if piece.get("llm_text"):
            buf_llm_texts.append(piece["llm_text"])
            buf_has_table = True
        else:
            buf_llm_texts.append(piece["text"])
        buf_tokens += piece_tokens + join_cost

    _flush_buffer()
    return chunks


def _scan_merge_range(
    mineru_sections, range_start, range_end, token_budget,
    unit_stop_depth=1, use_toc_unit_stop=False, toc_kind_depth=None, tab_text_map=None,
):
    chunks = []
    units = _collect_logical_units(
        mineru_sections, range_start, range_end, unit_stop_depth, use_toc_unit_stop, toc_kind_depth,
    )
    for unit in units:
        chain_start = unit.get("anchor", unit["start"])
        chunks.extend(_split_logical_unit_into_chunks(
            mineru_sections,
            unit["start"],
            unit["end"],
            token_budget,
            unit["type"],
            chain_start=chain_start,
            tab_text_map=tab_text_map,
        ))
    return chunks


def _build_chunks_from_labeled_sections(
    mineru_sections, toc_start_idx, body_start_idx, token_budget,
    unit_stop_depth=1, use_toc_unit_stop=False, toc_kind_depth=None, tab_text_map=None,
):
    n = len(mineru_sections)
    chunks = []

    if toc_start_idx >= 0:
        toc_end = min(max(body_start_idx, toc_start_idx + 1), n)
        if toc_start_idx > 0:
            chunks.extend(_scan_merge_range(mineru_sections, 0, toc_start_idx, token_budget))
        if toc_start_idx < toc_end:
            chunks.extend(_scan_merge_range(mineru_sections, toc_start_idx, toc_end, token_budget))
        if toc_end < n:
            chunks.extend(_scan_merge_range(
                mineru_sections, toc_end, n, token_budget, unit_stop_depth, use_toc_unit_stop, toc_kind_depth, tab_text_map=tab_text_map,
            ))
    else:
        chunks.extend(_scan_merge_range(
            mineru_sections, 0, n, token_budget, unit_stop_depth, False, None, tab_text_map=tab_text_map,
        ))

    chunks.sort(key=lambda cr: cr.get("mineru_range", (0, 0))[0])
    return chunks


def _parse_toc_kind_depths(toc_lines):
    kind_depth = {}
    stack = []
    depths = []
    for raw in toc_lines:
        stripped = raw.strip()
        if not stripped:
            continue
        if re.match(r'^\s*(?:目\s*录|目\s*次|CONTENTS|Table\s*of\s*Contents)\s*$', stripped, re.IGNORECASE):
            continue
        text_stripped = normalize_text_for_title(stripped)
        kind = _detect_title_kind(text_stripped)
        if kind is None:
            if not _looks_like_toc_entry(stripped):
                continue
            lvl = get_section_title_level(stripped)
            if lvl <= 0:
                continue
            kind = "toc_other"
        if kind in kind_depth:
            depth = kind_depth[kind]
        else:
            depth = stack[-1][2] + 1 if stack else 1
            kind_depth[kind] = depth
        while stack and stack[-1][2] >= depth:
            stack.pop()
        stack.append((0, "", depth, kind))
        depths.append(depth)
    if not depths:
        return {}, 0, 0
    return kind_depth, min(depths), max(depths)


def _toc_depth_bounds(toc_lines):
    _, toc_min_d, toc_max_d = _parse_toc_kind_depths(toc_lines)
    return toc_min_d, toc_max_d


def _toc_depth_for_text(text, kind_depth):
    if not kind_depth or not text:
        return 0
    stripped = text.strip() if isinstance(text, str) else ""
    if not stripped:
        return 0
    text_stripped = normalize_text_for_title(stripped)
    if not text_stripped:
        return 0
    kind = _detect_title_kind(text_stripped)
    if kind is None:
        return 0
    return kind_depth.get(kind, 0)


def _resolve_unit_stop_depth(toc_lines, toc_start_idx):
    if toc_start_idx < 0 or len(toc_lines) < 3:
        return 1, False, {}
    kind_depth, _, toc_max_d = _parse_toc_kind_depths(toc_lines)
    if toc_max_d <= 0 or not kind_depth:
        return 1, False, {}
    return toc_max_d, True, kind_depth


def _looks_like_toc_entry(stripped):
    if not stripped:
        return False
    if re.match(r'^\s*(?:目\s*录|目\s*次|CONTENTS|Table\s*of\s*Contents)\s*$', stripped, re.IGNORECASE):
        return True
    has_section = bool(re.search(r'第[一二三四五六七八九十百千\d]+[节章]', stripped))
    has_page_end = bool(re.search(r'\d{1,4}\s*$', stripped))
    if has_section and has_page_end:
        return True
    if re.search(r'[\.．]{3,}', stripped):
        return True
    if re.search(r'^\s*[（(]?\d+[）).、]', stripped):
        return True
    if re.search(r'^[（(][一二三四五六七八九十]+[）)]', stripped):
        return True
    return False


def _collect_covered_indices(chunks_raw):
    covered = set()
    for chunk_raw in chunks_raw:
        start, end = chunk_raw.get("mineru_range", (0, 0))
        for idx in range(start, end):
            covered.add(idx)
    return covered


def _assert_text_coverage(mineru_sections, chunks_raw):
    covered = _collect_covered_indices(chunks_raw)
    for idx, item in enumerate(mineru_sections):
        if _is_noise_section(_section_text(item)):
            continue
        if idx not in covered:
            return False
    return True


def _fallback_full_single_chunk(mineru_sections):
    n = len(mineru_sections)
    if n <= 0:
        return []
    return [{
        "content": _join_sections_range(mineru_sections, 0, n),
        "parent_chain": [],
        "mineru_range": (0, n),
    }]


def chunk(filename, binary=None, lang="Chinese", callback=None, **kwargs):
    parser_config = kwargs.get("parser_config", {"chunk_token_num": 512, "delimiter": "\n!?。！？；，、"})
    parser_config = copy.deepcopy(parser_config)

    normalized_doc_name = re.sub(r"\.(xlsx?|xlsm)$", ".pdf", filename, flags=re.IGNORECASE)
    doc = {"docnm_kwd": normalized_doc_name}
    doc["title_tks"] = rag_tokenizer.tokenize(re.sub(r"\.[a-zA-Z]+$", "", doc["docnm_kwd"]))
    doc["title_sm_tks"] = rag_tokenizer.fine_grained_tokenize(doc["title_tks"])
    eng = lang.lower() == "english"

    tenant_id = kwargs.get("tenant_id")
    kb_id = kwargs.get("kb_id")
    doc_id = kwargs.get("doc_id")

    sections, tbls = [], []
    table_indices_in_mineru = []

    is_mineru_doc = re.search(r"\.(pdf|xlsx?|xlsm|docx?|docm|dotx?|dotm)$", filename, re.IGNORECASE)
    is_mineru_img = re.search(r"\.(jpe?g|png|gif|bmp|webp|tiff?)$", filename, re.IGNORECASE)

    if not (is_mineru_doc or is_mineru_img):
        return _fallback_general_docs(filename, binary, lang, callback, kwargs, "Financial parser requires PDF/image/docx.") or []

    is_excel_mineru_path = bool(re.search(r"\.(xlsx?|xlsm)$", filename, re.IGNORECASE))

    if callback:
        callback(0.05, "Start MinerU parsing (Financial).")

    mineru_executable = os.environ.get("MINERU_EXECUTABLE", "mineru")
    mineru_api = parser_config.get("mineru_api_base") or resolve_mineru_api_from_env()
    mineru_parser = MinerUParser(mineru_path=mineru_executable, mineru_api=mineru_api)

    backend = (parser_config.get("mineru_backend") or os.environ.get("MINERU_BACKEND", "hybrid-auto-engine")).strip() or "hybrid-auto-engine"

    mineru_ok, _mineru_install_reason = mineru_parser.check_installation(backend)
    if not mineru_ok:
        if is_excel_mineru_path:
            if callback:
                callback(-1, "Excel+Financial：MinerU 不可用。")
            raise RuntimeError("Excel+Financial: MinerU unavailable.")
        return _collapse_to_single_chunk(
            _fallback_general_docs(filename, binary, lang, callback, kwargs, "MinerU is unavailable."),
            doc, eng,
        )

    try:
        mineru_sections, mineru_tables = mineru_parser.parse_document(
            filepath=filename,
            binary=binary,
            callback=callback,
            output_dir=os.environ.get("MINERU_OUTPUT_DIR", ""),
            backend=backend,
            delete_output=bool(int(os.environ.get("MINERU_DELETE_OUTPUT", 1))),
            kb_id=kb_id,
            doc_id=doc_id,
            parser_config=kwargs.get("parser_config", {}),
        )
    except KeyError as exc:
        _missing_key = exc.args[0] if exc.args else None
        if _missing_key == "type":
            if is_excel_mineru_path:
                raise RuntimeError("Excel+Financial: MinerU output missing 'type'.") from exc
            return _collapse_to_single_chunk(
                _fallback_general_docs(filename, binary, lang, callback, kwargs, "MinerU output missing 'type'."),
                doc, eng,
            )
        if _missing_key == "hichunk":
            if is_excel_mineru_path:
                raise RuntimeError("Excel+Financial: MinerU KeyError('hichunk').") from exc
            return _collapse_to_single_chunk(
                _fallback_general_docs(filename, binary, lang, callback, kwargs, "MinerU KeyError('hichunk')."),
                doc, eng,
            )
        raise
    except Exception as exc:
        if is_excel_mineru_path:
            raise RuntimeError(f"Excel+Financial parse failed: {exc!s}") from exc
        return _collapse_to_single_chunk(
            _fallback_general_docs(filename, binary, lang, callback, kwargs, f"MinerU parse failed: {exc}"),
            doc, eng,
        )

    if callback:
        callback(0.15, "MinerU parsing done (Financial).")

    unique_sections = []
    seen_key = set()
    for item in mineru_sections:
        text = (item[0] if len(item) >= 1 else "").strip()
        pos = item[1] if len(item) > 1 else None
        if not text:
            unique_sections.append(item)
            continue
        if is_html_table(text):
            key = ("tab", hash(text))
        else:
            pos_hash = hash(str(pos)) if pos is not None else None
            key = ("sec", hash(text), pos_hash)
        if key not in seen_key:
            unique_sections.append(item)
            seen_key.add(key)
    mineru_sections = unique_sections

    mineru_sections_with_level = []
    for item in mineru_sections:
        chunk_id = ""
        # MinerU 默认三元组 (text, pos, chunk_id)，manual 模式为四元组，chunk_id 均在末尾
        if len(item) >= 3:
            _raw = str(item[-1] or "").strip()
            if len(_raw) <= 64:
                chunk_id = _raw
        if len(item) == 2:
            text, pos_tag = item
            text = " ".join((text or "").strip().split())
            title_level = 0 if is_html_table(text) else get_section_title_level(text)
            mineru_sections_with_level.append((text, pos_tag, title_level, chunk_id))
        elif len(item) == 3:
            text = " ".join((item[0] or "").strip().split())
            title_level = 0 if is_html_table(text) else get_section_title_level(text)
            mineru_sections_with_level.append((text, item[1], title_level, chunk_id))
        else:
            text = item[0] if len(item) > 0 else ""
            pos_tag = item[1] if len(item) > 1 else None
            text = " ".join((text or "").strip().split())
            title_level = 0 if (not text or is_html_table(text)) else get_section_title_level(text)
            mineru_sections_with_level.append((text, pos_tag, title_level, chunk_id))
    mineru_sections = mineru_sections_with_level
    title_levels_display = [_display_title_level_tag(item) for item in mineru_sections]
    logging.info(
        "[Financial][静态标题] 标题层级序列（0=正文 1~4=标题 tab=表格 空=空行，非分块 depth）: %s",
        title_levels_display,
    )
#
    def _normalize_pos_list(poss):
        norm = []
        if not poss:
            return norm
        for p in poss:
            try:
                if not isinstance(p, (list, tuple)) or len(p) < 5:
                    continue
                pn = p[0][0] if isinstance(p[0], list) else p[0]
                norm.append((pn, p[1], p[2], p[3], p[4]))
            except Exception:
                continue
        return norm

    for idx, section_item in enumerate(mineru_sections):
        if len(section_item) >= 2:
            text, pos_tag = section_item[0], section_item[1]
            title_level = section_item[2] if len(section_item) >= 3 else 0
            sec_chunk_id = section_item[3] if len(section_item) >= 4 else ""
        else:
            text = section_item[0] if len(section_item) > 0 else ""
            pos_tag = None
            title_level = 0
            sec_chunk_id = ""

        poss = _normalize_pos_list(mineru_parser.extract_positions(pos_tag)) if pos_tag else []
        if is_html_table(text):
            tbls.append(((None, text), poss if poss else []))
            table_indices_in_mineru.append(idx)
            sections.append((text, idx, poss, 0, sec_chunk_id))
        else:
            sections.append((text, idx, poss, title_level, sec_chunk_id))

    if mineru_tables:
        for table_item in mineru_tables:
            if isinstance(table_item, tuple) and len(table_item) == 2:
                table_text, table_pos = table_item
                if table_text is None:
                    continue
                table_text = str(table_text).strip()
                if not table_text:
                    continue
                poss = _normalize_pos_list(mineru_parser.extract_positions(table_pos)) if table_pos else []
                tbls.append(((None, table_text), poss))
            else:
                if table_item is None:
                    continue
                fallback_text = str(table_item).strip()
                if not fallback_text:
                    continue
                tbls.append(((None, fallback_text), []))

    if callback:
        callback(0.2, "Extracting TOC (Financial)...")

    toc_text = ""
    toc_start_idx = -1
    body_start_idx = 0
    for i, section_item in enumerate(mineru_sections):
        text = section_item[0] if len(section_item) >= 1 else ""
        if re.match(r'^\s*(?:目\s*录|目\s*次|CONTENTS|Table\s*of\s*Contents)\s*$', text, re.IGNORECASE):
            toc_start_idx = i
            break
    toc_lines = []
    if toc_start_idx >= 0:
        MAX_TOC = 300
        body_start_idx = len(mineru_sections)

        for i in range(toc_start_idx, min(toc_start_idx + MAX_TOC, len(mineru_sections))):
            text = mineru_sections[i][0] if len(mineru_sections[i]) >= 1 else ""
            stripped = text.strip()

            has_section = bool(re.search(r'第[一二三四五六七八九十百千\d]+[节章]', stripped))
            has_page_end = bool(re.search(r'\d{1,4}\s*$', stripped))

            if i > toc_start_idx and len(toc_lines) >= 3 and not _looks_like_toc_entry(stripped):
                body_start_idx = i
                break

            if len(toc_lines) > 5 and has_section and not has_page_end:
                body_start_idx = i
                break

            toc_lines.append(stripped)
        else:
            body_start_idx = toc_start_idx + len(toc_lines)
            if body_start_idx > len(mineru_sections):
                body_start_idx = len(mineru_sections)

        toc_text = '\n'.join(toc_lines)
    if toc_text:
        lines = toc_text.splitlines()
        logging.info("[Financial] 目录页文本 toc_start_idx=%s lines=%s", toc_start_idx, len(lines))
        for idx, line in enumerate(lines):
            logging.info("  [%d] %s", idx, line)
    else:
        logging.info("[Financial] toc_start_idx=%s, toc_text=\"no TOC found\"", toc_start_idx)

    scan_start = _induction_scan_start(toc_start_idx, body_start_idx)
    mineru_sections, level_map, induced = _apply_induced_dynamic_levels(
        mineru_sections, toc_start_idx, body_start_idx,
    )
    sections = _sync_sections_title_levels(sections, mineru_sections)
    if induced:
        depths_induced = [_display_depth_tag(item) for item in mineru_sections]
        logging.info(
            "[Financial][诱导depth] 按出现顺序诱导后: %s",
            depths_induced,
        )

    inline_patterns = _scan_inline_enum_patterns(mineru_sections, scan_start, len(mineru_sections))
    mineru_sections, level_map = _demote_inline_enum_titles_for_tree(
        mineru_sections, level_map, inline_patterns,
    )
    sections = _sync_sections_title_levels(sections, mineru_sections)

    toc_items = _toc_items_from_induced_outline(
        mineru_sections, level_map, scan_start, len(mineru_sections),
    )
    if not toc_items:
        toc_items = []
        for i, section_item in enumerate(mineru_sections):
            text = section_item[0] if len(section_item) >= 1 else ""
            stripped = text.strip()
            if not stripped:
                continue
            level = section_item[2] if len(section_item) >= 3 else get_section_title_level(stripped)
            if level > 0:
                toc_items.append({
                    "label": _extract_label_for_toc_item(stripped),
                    "title": stripped,
                    "induced_depth": level,
                })
    toc_root = build_tree_from_induced_items(toc_items)
    toc_root.mineru_index_start = 0

    _fix_toc_with_inline_titles(toc_root, mineru_sections)

    tree_level_nodes = _tree_nodes_for_level_map(toc_root)
    tree_level_by_index = _tree_level_by_index_from_nodes(tree_level_nodes)
    mineru_sections = _apply_tree_levels_to_sections(
        mineru_sections, tree_level_by_index, level_map, toc_start_idx, body_start_idx,
    )
    sections = _sync_sections_title_levels(sections, mineru_sections)
    depths_display = [_display_depth_tag(item) for item in mineru_sections]
    logging.info(
        "[Financial][树depth] 块合并采用的目录树 depth（-1=目录 0=正文 1~=标题深度）: %s",
        depths_display,
    )
    for idx, sec in enumerate(mineru_sections):
        preview = (_section_text(sec) or "").replace("\n", " ").replace("\r", " ")[:150]
        logging.info(
            "[Financial][打标] [%d] depth=%s text=%s",
            idx,
            depths_display[idx] if idx < len(depths_display) else "?",
            preview,
        )

    cross_ref = _build_cross_ref_from_toc_items(toc_items)

    toc_text_output = '\n'.join(_tree_to_outline_text(toc_root))
    toc_index = [
        {"title": (item.get("title") or "").strip(), "depth": int(item.get("induced_depth") or 1)}
        for item in toc_items
        if (item.get("title") or "").strip()
    ]
    tree_data = {"toc": toc_text_output, "toc_index": toc_index}
    toc_preview = toc_text_output[:] if toc_text_output else "(empty)"
    logging.info(
        "[Financial] tree toc_len=%s cross_ref=%s toc_preview=%s",
        len(toc_text_output),
        bool(cross_ref),
        toc_preview,
    )
    if doc_id and tenant_id:
        try:
            from api.db.services.document_service import DocumentService
            DocumentService.update_by_id(doc_id, {"tree": tree_data, "tree_cross_ref": cross_ref})
        except Exception:
            logging.exception("Failed to save tree to document (Financial).")

    if callback:
        callback(0.3, "Building chunks (Financial)...")

    tab_text_map = {}
    for idx, item in enumerate(mineru_sections):
        text = _section_text(item)
        if is_html_table(text):
            es_text, llm_text = convert_html_table(text)
            if es_text or llm_text:
                tab_text_map[idx] = (es_text, llm_text)

    from common.token_utils import embedding_token_budget
    token_budget = embedding_token_budget(8192)
    if tenant_id:
        try:
            from api.db.services.llm_service import LLMBundle
            from common.constants import LLMType
            embd_bundle = LLMBundle(tenant_id, LLMType.EMBEDDING)
            token_budget = embedding_token_budget(embd_bundle.max_length)
        except Exception:
            pass

    unit_stop_depth, use_toc_unit_stop, toc_kind_depth = _resolve_unit_stop_depth(
        toc_lines, toc_start_idx,
    )
    chunks_raw = _build_chunks_from_labeled_sections(
        mineru_sections, toc_start_idx, body_start_idx, token_budget,
        unit_stop_depth, use_toc_unit_stop, toc_kind_depth, tab_text_map=tab_text_map,
    )
    if not _assert_text_coverage(mineru_sections, chunks_raw):
        logging.warning("Financial chunk coverage assertion failed, fallback to single chunk.")
        chunks_raw = _fallback_full_single_chunk(mineru_sections)

    chunks_raw = [cr for cr in chunks_raw if cr.get("mineru_range", (0, 0))[1] > cr.get("mineru_range", (0, 0))[0]]
    if not chunks_raw:
        return _fallback_general_docs(filename, binary, lang, callback, kwargs, "Financial merge produced no chunks.")

    for ci, chunk_raw in enumerate(chunks_raw):
        ms, me = chunk_raw.get("mineru_range", (0, 0))
        depth_seq = _depths_display_for_range(mineru_sections, ms, me)
        content_preview = (chunk_raw.get("content") or "").replace("\n", " ")[:100]
        logging.info(
            "[Financial][分块] chunk=%d/%d range=[%d,%d) depths=%s parent_chain=%s preview=%s",
            ci + 1,
            len(chunks_raw),
            ms,
            me,
            depth_seq,
            chunk_raw.get("parent_chain", []),
            content_preview,
        )

    if callback:
        callback(0.5, "Building chunks (Financial)...")

    chunks = []
    chunk_positions = []
    chunk_chains = []
    chunk_mineru_indices = []
    chunk_mineru_chunk_ids = []
    llm_chunks = []

    for chunk_raw in chunks_raw:
        ck_content = chunk_raw["content"]
        ck_chain = chunk_raw.get("parent_chain", [])
        ck_llm = chunk_raw.get("llm_content", "")
        mineru_start, mineru_end = chunk_raw.get("mineru_range", (0, 0))

        mineru_indices_in_chunk = set()
        poss_list = []
        sec_ids = []
        for line_idx in range(mineru_start, mineru_end):
            if 0 <= line_idx < len(sections):
                section_item = sections[line_idx]
                if len(section_item) > 1:
                    mineru_indices_in_chunk.add(section_item[1])
                if len(section_item) > 2 and section_item[2]:
                    poss_list.extend(section_item[2])
                if len(section_item) > 4 and section_item[4]:
                    sec_ids.append(section_item[4])

        if mineru_indices_in_chunk:
            chunk_mineru_indices.append({
                'min': min(mineru_indices_in_chunk),
                'max': max(mineru_indices_in_chunk)
            })
        else:
            chunk_mineru_indices.append({'min': mineru_start, 'max': mineru_end})

        chunks.append(ck_content)
        llm_chunks.append(ck_llm if ck_llm else ck_content)
        chunk_positions.append(poss_list)
        chunk_chains.append(ck_chain)
        chunk_mineru_chunk_ids.append(sec_ids)

    from api.utils.json_encode import normalize_parent_chain_for_storage
    chunk_chains = [normalize_parent_chain_for_storage(c) for c in chunk_chains]

    if doc_id and tenant_id and chunk_chains and sections:
        try:
            from api.db.db_models import MineruSection, DB
            from peewee import Case
            if MineruSection.table_exists():
                with DB.connection_context():
                    accumulated = {}
                    for ci in range(len(chunk_chains)):
                        pchain = chunk_chains[ci] if ci < len(chunk_chains) else []
                        if not pchain:
                            continue
                        ms, me = chunks_raw[ci].get("mineru_range", (0, 0)) if ci < len(chunks_raw) else (0, 0)
                        sec_ids = [
                            sections[li][4]
                            for li in range(ms, me)
                            if 0 <= li < len(sections) and len(sections[li]) > 4 and sections[li][4]
                        ]
                        for sid in sec_ids:
                            if sid:
                                accumulated[sid] = pchain
                    if accumulated:
                        chunk_ids = list(accumulated.keys())
                        case_expr = Case(
                            None,
                            [(MineruSection.chunk_id == cid, accumulated[cid]) for cid in chunk_ids],
                        )
                        MineruSection.update(parent_chain=case_expr).where(
                            MineruSection.chunk_id.in_(chunk_ids)
                        ).execute()
                    logging.info("[Financial] mineru_parent_chain done total_chunks=%s total_sections_updated=%s", len(chunk_chains), len(accumulated))
        except Exception:
            logging.exception("Failed to update mineru_section parent_chain (Financial).")

    if doc_id and tenant_id and tab_text_map:
        try:
            from api.db.db_models import MineruSection as _MS, DB as _DB
            if _MS.table_exists():
                chunk_id_to_es = {}
                chunk_id_to_llm = {}
                for idx, (es_text, llm_text) in tab_text_map.items():
                    if idx < len(mineru_sections) and len(mineru_sections[idx]) >= 4:
                        cid = mineru_sections[idx][3]
                        if cid:
                            chunk_id_to_es[cid] = es_text
                            chunk_id_to_llm[cid] = llm_text
                if chunk_id_to_es:
                    with _DB.connection_context():
                        for cid, es_text in chunk_id_to_es.items():
                            llm_text = chunk_id_to_llm.get(cid, "")
                            _MS.update(
                                es_tab2text=es_text,
                                llm_tab2text=llm_text,
                            ).where(_MS.chunk_id == cid).execute()
                    logging.info("[Financial] mineru_tab2text done total_sections_updated=%s", len(chunk_id_to_es))
        except Exception:
            logging.exception("Failed to update mineru_section es_tab2text/llm_tab2text (Financial).")

    if not chunks:
        return _fallback_general_docs(filename, binary, lang, callback, kwargs, "Financial chunking produced empty result.")

    html_table_count = len(table_indices_in_mineru)
    mineru_only_tbls = tbls[html_table_count:] if html_table_count < len(tbls) else []

    try:
        tbls = vision_figure_parser_pdf_wrapper(tbls=mineru_only_tbls, callback=callback, **kwargs)
    except KeyError as exc:
        if str(exc).strip("'\"") == "type":
            logging.exception("Skip vision figure enhancement due to missing 'type' field in parser output.")
            tbls = mineru_only_tbls
        else:
            raise

    sanitized_tbls = []
    table_doc_orders = []
    for table_item in tbls:
        if not isinstance(table_item, (list, tuple)) or len(table_item) < 1:
            continue
        table_payload = table_item[0]
        table_pos = table_item[1] if len(table_item) > 1 else []
        table_text = None
        if isinstance(table_payload, (list, tuple)) and len(table_payload) >= 2:
            table_text = table_payload[1]
        elif isinstance(table_payload, str):
            table_text = table_payload
        if table_text is None:
            continue
        table_text = str(table_text).strip()
        if not table_text:
            continue
        table_sort_idx = 999999
        if table_pos:
            try:
                p0 = table_pos[0]
                table_sort_idx = p0[0][0] if isinstance(p0[0], list) else p0[0]
            except Exception:
                pass
        sanitized_tbls.append(((None, table_text), table_pos if table_pos else []))
        table_doc_orders.append(table_sort_idx)

    table_docs = tokenize_table(sanitized_tbls, doc, eng)
    chunk_docs = tokenize_chunks(chunks, doc, eng)

    for i, chunk_doc in enumerate(chunk_docs):
        if i < len(chunk_chains):
            chunk_doc["parent_chain"] = chunk_chains[i]
        if i < len(llm_chunks) and llm_chunks[i]:
            if i >= len(chunks) or llm_chunks[i] != chunks[i]:
                chunk_doc["content_llm"] = llm_chunks[i]
        if i < len(chunk_positions):
            if chunk_positions[i]:
                add_positions(chunk_doc, chunk_positions[i])
            else:
                chunk_doc["position_int"] = []
                chunk_doc["page_num_int"] = []
                chunk_doc["top_int"] = []
        else:
            chunk_doc["position_int"] = []
            chunk_doc["page_num_int"] = []
            chunk_doc["top_int"] = []

        if "position_int" in chunk_doc and chunk_doc["position_int"]:
            chunk_doc["position_int"] = [
                list(pos) if isinstance(pos, tuple) else pos
                for pos in chunk_doc["position_int"]
            ]
        if i < len(chunk_mineru_chunk_ids) and chunk_mineru_chunk_ids[i]:
            chunk_doc["mineru_section_chunk_ids"] = chunk_mineru_chunk_ids[i]

    chunks_len = len(chunk_docs)
    positions_len = len(chunk_positions)
    indices_len = len(chunk_mineru_indices)
    chains_len = len(chunk_chains)
    chunk_ids_len = len(chunk_mineru_chunk_ids)
    llm_len = len(llm_chunks)
    if chunks_len != positions_len or chunks_len != indices_len or chunks_len != chains_len or chunks_len != chunk_ids_len or chunks_len != llm_len:
        while len(chunk_positions) < chunks_len:
            chunk_positions.append([])
        while len(chunk_mineru_indices) < chunks_len:
            chunk_mineru_indices.append({'min': -1, 'max': -1})
        while len(chunk_chains) < chunks_len:
            chunk_chains.append([])
        while len(chunk_mineru_chunk_ids) < chunks_len:
            chunk_mineru_chunk_ids.append([])
        while len(llm_chunks) < chunks_len:
            llm_chunks.append("")
        chunk_positions = chunk_positions[:chunks_len]
        chunk_mineru_indices = chunk_mineru_indices[:chunks_len]
        chunk_chains = chunk_chains[:chunks_len]
        chunk_mineru_chunk_ids = chunk_mineru_chunk_ids[:chunks_len]
        llm_chunks = llm_chunks[:chunks_len]

    all_elements = []
    for i, chunk_doc in enumerate(chunk_docs):
        if i < len(chunk_mineru_indices):
            mineru_range = chunk_mineru_indices[i]
            all_elements.append({
                'type': 'chunk',
                'doc': chunk_doc,
                'mineru_index': mineru_range['min'],
                'mineru_range': mineru_range
            })

    for ti, table_doc in enumerate(table_docs):
        table_sort_idx = table_doc_orders[ti] if ti < len(table_doc_orders) else 999999
        all_elements.append({
            'type': 'table',
            'doc': table_doc,
            'mineru_index': table_sort_idx,
            'mineru_range': {'min': table_sort_idx, 'max': table_sort_idx}
        })

    all_elements.sort(key=lambda x: x['mineru_index'])
    res = [elem['doc'] for elem in all_elements]

    if callback:
        callback(1.0, "Financial chunking done.")

    return res
