import asyncio
import copy
import re
import os
import json
import logging
from dotenv import load_dotenv
from rag.nlp import rag_tokenizer, tokenize_table, tokenize_chunks, add_positions

from deepdoc.parser.figure_parser import vision_figure_parser_pdf_wrapper
from deepdoc.parser.mineru_parser import MinerUParser, resolve_mineru_api_from_env

load_dotenv()

TITLE_NUM_RE = re.compile(r'^(\d+(?:\.\d+)*)')

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


def get_section_title_level(text: str) -> int:
    if not isinstance(text, str) or not text.strip():
        return 0
    text_stripped = normalize_text_for_title(text)
    if not text_stripped:
        return 0

    if re.match(r'^#*\s*第[一二三四五六七八九十百千\d]+[节章条]', text_stripped):
        return 1

    m = re.match(r'^#*\s*(\d+\.\d+(?:\.\d+)*)', text_stripped)
    if m:
        return m.group(1).count('.') + 1

    m = re.match(r'^#*\s*(\d+)(?![\d.])', text_stripped)
    if m:
        return 2

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


def label_to_depth(label, prev_depth):
    if label is None:
        return prev_depth + 1
    if re.match(r'^第[一二三四五六七八九十百千\d]+[节章条]', label):
        return 1
    if re.match(r'^#*\d+$', label):
        return 1
    if re.match(r'^#*\d+\.\d+$', label):
        return 2
    if re.match(r'^#*\d+\.\d+\.\d+$', label):
        return 3
    if re.match(r'^[一二三四五六七八九十]+$', label):
        return 2
    if re.match(r'^[（(][一二三四五六七八九十]+[）)]$', label):
        return 3
    if re.match(r'^\d+\.$', label):
        return 4
    if re.match(r'^[（(]\d+[）)]$', label):
        return 5
    return prev_depth + 1


def estimate_tokens(text):
    from common.token_utils import num_tokens_from_string
    return num_tokens_from_string(text)


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


def build_tree_from_triples(items):
    root = TocNode(title="root", depth=0)
    stack = [root]
    last_non_null_depth = 0

    for item in items:
        label = item.get("label")
        if label is None:
            depth = last_non_null_depth + 1
        else:
            depth = label_to_depth(label, stack[-1].depth)
            last_non_null_depth = depth

        node = TocNode(
            title=item.get("title", ""),
            label=label,
            depth=depth,
            page_start=0,
            contains_table=item.get("contains_table", False)
        )
        while stack and stack[-1].depth >= node.depth:
            stack.pop()
        stack[-1].children.append(node)
        node.parent = stack[-1]
        stack.append(node)

    return root


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

        node_level = get_section_title_level(node.title)

        headings = []

        for i in range(node.mineru_index_start + 1, scan_end):
            item = mineru_sections[i]
            text = item[0] if len(item) >= 1 else ""
            lvl = item[2] if len(item) >= 3 else get_section_title_level(text)

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


def _tree_to_text(node, depth=1):
    lines = []
    indent = "    " * (depth - 1)
    if node.title != "root":
        suffix = " [表格]" if node.contains_table else ""
        lines.append(f"{indent}{node.title}{suffix}")
    for child in node.children:
        lines.extend(_tree_to_text(child, depth + 1))
    return lines


def _parse_toc_text_with_llm(toc_text, llm_bundle):
    prompt = f"""Extract the table of contents as a flat JSON array of (label, title) pairs.
Each item: {{"label": "section_number_or_null", "title": "section_title"}}
label is the numbering prefix like "第一节", "一", "（一）", "1.", or null for unnumbered items like table names.
Mark financial statement tables with "contains_table": true.

TOC text:
{toc_text}

Output ONLY the JSON array, no other text:"""

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        answer, _ = loop.run_until_complete(
            llm_bundle.async_chat("", [{"role": "user", "content": prompt}], {"temperature": 0.0}))
    finally:
        loop.close()
    try:
        answer = answer.strip()
        if answer.startswith("```"):
            answer = re.sub(r'^```\w*\n?', '', answer)
            answer = re.sub(r'\n?```$', '', answer)
        items = json.loads(answer)
        return items
    except Exception:
        logging.warning("Failed to parse TOC LLM response as JSON, attempting to extract...")
        match = re.search(r'\[.*\]', answer, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
        return None


def _generate_cross_ref_with_llm(toc_items, llm_bundle):
    prompt = f"""Analyze this financial report table of contents. Identify:
1. main_tables: nodes that are the three main financial statements (balance sheet, income statement, cash flow statement)
2. note_to_table_mapping: for each notes parent node, which main tables does it correspond to

TOC items:
{json.dumps(toc_items, ensure_ascii=False)}

Output ONLY valid JSON:
{{
  "main_tables": [{{"title": "...", "index": N}}],
  "note_to_table_mapping": {{"notes_node_title": ["table_title_1", "table_title_2"]}}
}}"""

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        answer, _ = loop.run_until_complete(
            llm_bundle.async_chat("", [{"role": "user", "content": prompt}], {"temperature": 0.0}))
    finally:
        loop.close()
    try:
        answer = answer.strip()
        if answer.startswith("```"):
            answer = re.sub(r'^```\w*\n?', '', answer)
            answer = re.sub(r'\n?```$', '', answer)
        return json.loads(answer)
    except Exception:
        logging.warning("Failed to parse cross_ref LLM response as JSON")
        return {"main_tables": [], "note_to_table_mapping": {}}


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


def _walk_node_for_chunk(node, mineru_sections, chain, threshold):
    chain = list(chain)

    if node.mineru_index_start < 0:
        if node.children:
            child_chain = chain + [node.title] if node.title and node.title != "body" else chain
            results = []
            for child in node.children:
                results.extend(_walk_node_for_chunk(child, mineru_sections, child_chain, threshold))
            return results
        return []

    span_end = node.mineru_index_end
    if span_end < 0:
        if node.children:
            for child in reversed(node.children):
                if child.mineru_index_end >= 0:
                    span_end = child.mineru_index_end
                    break
        if span_end < 0:
            span_end = len(mineru_sections)

    if span_end < node.mineru_index_start:
        if node.children:
            child_chain = chain + [node.title] if node.title and node.title != "body" else chain
            results = []
            for child in node.children:
                results.extend(_walk_node_for_chunk(child, mineru_sections, child_chain, threshold))
            return results
        return []

    sections = mineru_sections[node.mineru_index_start:span_end]
    if not sections:
        if node.children:
            child_chain = chain + [node.title] if node.title and node.title != "body" else chain
            results = []
            for child in node.children:
                results.extend(_walk_node_for_chunk(child, mineru_sections, child_chain, threshold))
            return results
        return []

    if node.has_embedded_parent_title and chain:
        parent_title = chain[-1]
        norm_parent = normalize_text_for_title(parent_title)
        for si in range(len(sections)):
            stext = sections[si][0] if len(sections[si]) >= 1 else ""
            if not stext.strip():
                continue
            norm_stext = normalize_text_for_title(stext)
            if norm_stext.startswith(norm_parent) and norm_stext != norm_parent:
                n_chars = 0
                cut = 0
                for ci, ch in enumerate(stext):
                    if not ch.isspace():
                        n_chars += 1
                    if n_chars >= len(norm_parent):
                        cut = ci + 1
                        break
                sec_list = list(sections[si])
                sec_list[0] = stext[cut:].lstrip()
                sections[si] = tuple(sec_list)
            break

    content = '\n'.join([
        item[0] if len(item) >= 1 else str(item)
        for item in sections
        if not _is_noise_section(item[0] if len(item) >= 1 else str(item))
    ])

    has_table = node.contains_table or any(
        is_html_table(item[0] if len(item) >= 1 else str(item))
        for item in sections
    )
    span = (node.mineru_index_start, span_end)

    if has_table:
        merged = _merge_table_with_adjacent(sections)
        return [{"content": merged, "parent_chain": chain + [node.title], "mineru_range": span}]

    if not content.strip():
        if node.children:
            child_chain = chain + [node.title] if node.title and node.title != "body" else chain
            results = []
            for child in node.children:
                results.extend(_walk_node_for_chunk(child, mineru_sections, child_chain, threshold))
            return results
        return []

    if estimate_tokens(content) < threshold:
        return [{"content": content, "parent_chain": chain + [node.title], "mineru_range": span}]

    if node.children:
        child_chain = chain + [node.title]
        results = []
        for child in node.children:
            results.extend(_walk_node_for_chunk(child, mineru_sections, child_chain, threshold))
        return results

    return [{"content": content, "parent_chain": chain + [node.title], "mineru_range": span}]


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

    token_threshold = 8192
    if tenant_id:
        try:
            from api.db.services.llm_service import LLMBundle
            from common.constants import LLMType
            embd_bundle = LLMBundle(tenant_id, LLMType.EMBEDDING)
            token_threshold = embd_bundle.max_length
        except Exception:
            pass

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
        if len(item) >= 4:
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
# 返回mineru的section内容：            
    mineru_sections = mineru_sections_with_level
    for idx, sec in enumerate(mineru_sections):
        preview = (sec[0] if len(sec) >= 1 else "")[:150]
        lvl = sec[2] if len(sec) >= 3 else 0
        logging.info("解析返回的块信息：mineru_sections[%s] level=%s text=%s", idx, lvl, preview)
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
        if re.search(r'目\s*录|目次|CONTENTS', text.strip()):
            toc_start_idx = i
            break
    if toc_start_idx >= 0:
        toc_lines = []
        MAX_TOC = 300  # generous ceiling for long annual reports
        NON_TOC_STREAK = 8  # consecutive non-TOC lines to trigger early stop
        non_toc_run = 0

        for i in range(toc_start_idx, min(toc_start_idx + MAX_TOC, len(mineru_sections))):
            text = mineru_sections[i][0] if len(mineru_sections[i]) >= 1 else ""
            stripped = text.strip()

            has_section = bool(re.search(r'第[一二三四五六七八九十百千\d]+[节章]', stripped))
            has_page_end = bool(re.search(r'\d{1,4}\s*$', stripped))

            # Primary: body section title without trailing page number → TOC ended
            if len(toc_lines) > 5 and has_section and not has_page_end:
                break

            toc_lines.append(stripped)

            # Secondary: after enough entries, detect drift into non-TOC content
            if len(toc_lines) > 20:
                looks_toc = (
                    has_section
                    or has_page_end
                    or bool(re.search(r'[\.．]{3,}', stripped))       # dot leaders
                    or bool(re.search(r'^\s*[（(]?\d+[）).、]', stripped))  # numbered entry
                    or bool(re.search(r'^[（(][一二三四五六七八九十]+[）)]', stripped))
                )
                if looks_toc:
                    non_toc_run = 0
                else:
                    non_toc_run += 1
                    if non_toc_run >= NON_TOC_STREAK:
                        toc_lines = toc_lines[:-NON_TOC_STREAK]
                        break

        toc_text = '\n'.join(toc_lines)
    if toc_start_idx < 0:
        for i, section_item in enumerate(mineru_sections):
            text = section_item[0] if len(section_item) >= 1 else ""
            if re.search(r'第[一二三四五六七八九十百千\d]+[节章]', text.strip()):
                body_start_idx = i
                break

    pre_toc_boundary = toc_start_idx if toc_start_idx >= 0 else 0
    for i in range(toc_start_idx - 1, -1, -1) if toc_start_idx > 0 else range(0):
        text = mineru_sections[i][0] if len(mineru_sections[i]) >= 1 else ""
        stripped = text.strip()
        if re.search(r'第[一二三四五六七八九十百千\d]+[节章]', stripped) and not re.search(r'\d{1,4}\s*$', stripped):
            pre_toc_boundary = i
            break

# 打印输入给LLM的目录信息
    if toc_text:
        # logging.info("[Financial] toc_start_idx=%s, toc_text[]: %s", toc_start_idx, toc_text[:])
        lines = toc_text.splitlines()
        logging.info("打印输入给LLM的目录信息:")
        logging.info("mineru_sections:")
        for idx, line in enumerate(lines):
            logging.info("  [%d] %s", idx, line)
        logging.info("toc_start_idx = %s", toc_start_idx)
    else:
        logging.info("[Financial] toc_start_idx=%s, toc_text=\"no TOC found\"", toc_start_idx)
#
    toc_items = None
    if toc_text:
        try:
            from api.db.services.llm_service import LLMBundle
            from common.constants import LLMType
            if tenant_id:
                chat_bundle = LLMBundle(tenant_id, LLMType.CHAT)
                toc_items = _parse_toc_text_with_llm(toc_text, chat_bundle)
        except Exception:
            logging.exception("Failed to parse TOC with LLM (Financial).")

    if toc_items is None:
        toc_items = []
        for i, section_item in enumerate(mineru_sections):
            text = section_item[0] if len(section_item) >= 1 else ""
            stripped = text.strip()
            if not stripped:
                continue
            level = section_item[2] if len(section_item) >= 3 else get_section_title_level(stripped)
            if level > 0:
                raw_label = stripped.split()[0] if stripped.split() else ""
                if raw_label.startswith("#"):
                    parts = stripped.split(None, 1)
                    raw_label = parts[1].split()[0] if len(parts) > 1 else raw_label.lstrip("#")
                label = re.sub(r'[、，：:\.]$', '', raw_label)
                toc_items.append({"label": label, "title": stripped})

# 打印LLM返回的目录结构
    source = "llm" if toc_text else "inline"
    # logging.info("[Financial] toc_items source=%s count=%s first5=%s", source, len(toc_items), toc_items[:5])
    toc_root = build_tree_from_triples(toc_items)

    if toc_start_idx >= 0:
        toc_root.mineru_index_start = 0
    else:
        toc_root.mineru_index_start = 0

    _fix_toc_with_inline_titles(toc_root, mineru_sections)

    if toc_start_idx >= 0:
        body_start_idx = len(mineru_sections)
        for child in toc_root.children:
            if child.mineru_index_start >= 0:
                body_start_idx = min(body_start_idx, child.mineru_index_start)
        if body_start_idx >= len(mineru_sections):
            body_start_idx = 0
    else:
        toc_start_idx = 0

    cross_ref = None
    if toc_items and tenant_id:
        try:
            from api.db.services.llm_service import LLMBundle
            from common.constants import LLMType
            chat_bundle = LLMBundle(tenant_id, LLMType.CHAT)
            cross_ref = _generate_cross_ref_with_llm(toc_items, chat_bundle)
        except Exception:
            logging.exception("Failed to generate cross_ref (Financial).")

    toc_text_output = '\n'.join(_tree_to_text(toc_root))
    tree_data = {
        "source": "toc_with_inline_fix" if toc_text else "inline_only",
        "toc": toc_text_output,
    }
    if cross_ref:
        tree_data["cross_ref"] = cross_ref
# 入库存储的目录结构树内容
    toc_preview = toc_text_output[:] if toc_text_output else "(empty)"
    logging.info("入库存储的目录结构树内容：\n[Financial] tree_data source=%s toc_len=%s cross_ref=%s toc_preview=%s",
                 tree_data["source"], len(toc_text_output), bool(cross_ref), toc_preview)
#    
    if doc_id and tenant_id:
        try:
            from api.db.services.document_service import DocumentService
            DocumentService.update_by_id(doc_id, {"tree": tree_data})
        except Exception:
            logging.exception("Failed to save tree to document (Financial).")

    if callback:
        callback(0.3, "Building chunk tree (Financial)...")

    chunks_raw = []

    if pre_toc_boundary > 0:
        pre_toc_text = '\n'.join([
            item[0] if len(item) >= 1 else str(item)
            for item in mineru_sections[:pre_toc_boundary]
            if not _is_noise_section(item[0] if len(item) >= 1 else str(item))
        ])
        if pre_toc_text.strip():
            chunks_raw.append({"content": pre_toc_text, "parent_chain": [], "mineru_range": (0, pre_toc_boundary)})

    if pre_toc_boundary < toc_start_idx:
        pre_body_text = '\n'.join([
            item[0] if len(item) >= 1 else str(item)
            for item in mineru_sections[pre_toc_boundary:toc_start_idx]
            if not _is_noise_section(item[0] if len(item) >= 1 else str(item))
        ])
        if pre_body_text.strip():
            chunks_raw.append({"content": pre_body_text, "parent_chain": [], "mineru_range": (pre_toc_boundary, toc_start_idx)})

    body_root_children = []
    for child in toc_root.children:
        if child.mineru_index_start >= body_start_idx or child.mineru_index_start < 0:
            body_root_children.append(child)

    body_root = TocNode(title="body", depth=0)
    body_root.children = body_root_children
    body_root.mineru_index_start = body_start_idx
    body_root.mineru_index_end = len(mineru_sections)

    for child in body_root.children:
        chunks_raw.extend(_walk_node_for_chunk(child, mineru_sections, [], token_threshold))

    chunks_raw = [cr for cr in chunks_raw if str(cr.get("content", "")).strip()]
    has_body_chunk = any(cr.get("mineru_range", (0, 0))[0] >= body_start_idx for cr in chunks_raw)
    if not has_body_chunk:
        return _fallback_general_docs(filename, binary, lang, callback, kwargs, "Financial tree produced no body chunks.")

    if callback:
        callback(0.5, "Building chunks (Financial)...")

    chunks = []
    chunk_positions = []
    chunk_chains = []
    chunk_mineru_indices = []

    for chunk_raw in chunks_raw:
        ck_content = chunk_raw["content"]
        ck_chain = chunk_raw.get("parent_chain", [])
        mineru_start, mineru_end = chunk_raw.get("mineru_range", (0, 0))

        mineru_indices_in_chunk = set()
        poss_list = []
        for line_idx in range(mineru_start, mineru_end):
            if 0 <= line_idx < len(sections):
                section_item = sections[line_idx]
                if len(section_item) > 1:
                    mineru_indices_in_chunk.add(section_item[1])
                if len(section_item) > 2 and section_item[2]:
                    poss_list.extend(section_item[2])

        if mineru_indices_in_chunk:
            chunk_mineru_indices.append({
                'min': min(mineru_indices_in_chunk),
                'max': max(mineru_indices_in_chunk)
            })
        else:
            chunk_mineru_indices.append({'min': mineru_start, 'max': mineru_end})

        chunks.append(ck_content)
        chunk_positions.append(poss_list)
        chunk_chains.append(ck_chain)

    if doc_id and tenant_id and chunk_chains and sections:
        try:
            from api.db.db_models import MineruSection, DB
            if MineruSection.table_exists():
                with DB.connection_context():
                    total_sec_updated = 0
                    total_chain_count = len(chunk_chains)
                    logging.info("输出chunk块对应的父子连关系：")
                    for ci in range(len(chunk_chains)):
                        pchain = chunk_chains[ci] if ci < len(chunk_chains) else []
                        if not pchain:
                            logging.info("[Financial] mineru_parent_chain chunk=%s/%s chain=[] skipped", ci + 1, total_chain_count)
                            continue
                        ms, me = chunks_raw[ci].get("mineru_range", (0, 0)) if ci < len(chunks_raw) else (0, 0)
                        sec_ids = [sections[li][3] for li in range(ms, me) if 0 <= li < len(sections) and len(sections[li]) > 3 and sections[li][3]]
                        if sec_ids:
                            MineruSection.update(parent_chain=pchain).where(MineruSection.chunk_id.in_(sec_ids)).execute()
                            updated_count = len(sec_ids)
                            total_sec_updated += updated_count
                            logging.info("[Financial] mineru_parent_chain chunk=%s/%s chain=%s sec_count=%s updated=%s", ci + 1, total_chain_count, pchain, updated_count, updated_count)
                    logging.info("[Financial] mineru_parent_chain done total_chunks=%s total_sections_updated=%s", total_chain_count, total_sec_updated)
        except Exception:
            logging.exception("Failed to update mineru_section parent_chain (Financial).")

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

    chunks_len = len(chunk_docs)
    positions_len = len(chunk_positions)
    indices_len = len(chunk_mineru_indices)
    chains_len = len(chunk_chains)
    if chunks_len != positions_len or chunks_len != indices_len or chunks_len != chains_len:
        while len(chunk_positions) < chunks_len:
            chunk_positions.append([])
        while len(chunk_mineru_indices) < chunks_len:
            chunk_mineru_indices.append({'min': -1, 'max': -1})
        while len(chunk_chains) < chunks_len:
            chunk_chains.append([])
        chunk_positions = chunk_positions[:chunks_len]
        chunk_mineru_indices = chunk_mineru_indices[:chunks_len]
        chunk_chains = chunk_chains[:chunks_len]

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

    if toc_text and toc_text.strip():
        toc_docs = tokenize_chunks([toc_text], doc, eng)
        toc_docs[0]["parent_chain"] = []
        toc_docs[0]["position_int"] = []
        toc_docs[0]["page_num_int"] = []
        toc_docs[0]["top_int"] = []
        res.insert(0, toc_docs[0])

    if callback:
        callback(1.0, "Financial chunking done.")

    return res
