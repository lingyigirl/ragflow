import json

DEFAULT_TABLE_TITLES = [
    "合并资产负债表",
    "合并利润表",
    "合并现金流量表",
    "资产负债表",
    "利润表",
    "现金流量表",
    "合并所有者权益变动表",
    "所有者权益变动表",
]
DEFAULT_NOTE_TITLES = [
    "合并财务报表项目注释",
    "财务报表项目注释",
    "财务报表附注",
]
MAX_SIBLING_TITLES = 5


def parse_parent_chain(val):
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()]
        except Exception:
            pass
    return []


def chain_has_title(chain, title):
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


def _toc_paths(toc_index):
    paths = []
    stack = []
    for node in toc_index or []:
        if not isinstance(node, dict):
            continue
        title = (node.get("title") or "").strip()
        if not title:
            continue
        depth = max(1, int(node.get("depth") or 1))
        while len(stack) >= depth:
            stack.pop()
        stack.append(title)
        paths.append((depth, title, list(stack)))
    return paths


def _match_toc_path_index(paths, chain):
    if not paths or not chain:
        return -1
    match_idx = -1
    for i, (_, title, path) in enumerate(paths):
        if chain_has_title(chain, title):
            match_idx = i
    if match_idx >= 0:
        return match_idx
    for i, (_, title, path) in enumerate(paths):
        if chain_has_title(path, chain[-1]):
            return i
    return -1


def _sibling_titles(paths, match_idx, max_siblings=MAX_SIBLING_TITLES):
    if match_idx < 0 or match_idx >= len(paths):
        return []
    depth, title, path = paths[match_idx]
    parent_prefix = tuple(path[:-1])
    siblings = []
    for d, t, p in paths:
        if d != depth or not t:
            continue
        if tuple(p[:-1]) != parent_prefix:
            continue
        if t not in siblings:
            siblings.append(t)
    if title in siblings:
        siblings = [title] + [t for t in siblings if t != title]
    else:
        siblings = [title] + siblings
    return siblings[:max_siblings]


def format_chunk_navigation(parent_chain, toc_index=None, max_siblings=MAX_SIBLING_TITLES):
    chain = parent_chain if isinstance(parent_chain, list) else parse_parent_chain(parent_chain)
    lines = []
    if chain:
        lines.append("Path: " + " > ".join(chain))
    toc_index = toc_index or []
    if toc_index and chain:
        paths = _toc_paths(toc_index)
        match_idx = _match_toc_path_index(paths, chain)
        if match_idx >= 0:
            _, current_title, full_path = paths[match_idx]
            if full_path:
                lines[0] = "Path: " + " > ".join(full_path)
            siblings = _sibling_titles(paths, match_idx, max_siblings=max_siblings)
            if siblings:
                lines.append("Related: " + "、".join(siblings))
    if not lines:
        return ""
    return "\n" + "\n".join("├── " + line for line in lines)


def detect_note_table_intent(chunk, cross_ref=None):
    note_titles = list((cross_ref or {}).get("note_to_table_mapping", {}).keys()) or DEFAULT_NOTE_TITLES
    table_titles = [
        t.get("title", "")
        for t in ((cross_ref or {}).get("main_tables") or [])
        if isinstance(t, dict) and t.get("title")
    ] or DEFAULT_TABLE_TITLES
    chain = parse_parent_chain(chunk.get("parent_chain"))
    content = chunk.get("content_with_weight", "") or chunk.get("content", "") or ""
    has_note = any(chain_has_title(chain, nt) for nt in note_titles) or any(kw in content for kw in note_titles)
    has_table = any(chain_has_title(chain, tt) for tt in table_titles) or any(tt in content for tt in table_titles)
    return has_note or has_table


def format_cross_ref_line(cross_ref):
    if not cross_ref or not isinstance(cross_ref, dict):
        return ""
    note_titles = list((cross_ref.get("note_to_table_mapping") or {}).keys())
    table_titles = [
        t.get("title", "")
        for t in (cross_ref.get("main_tables") or [])
        if isinstance(t, dict) and t.get("title")
    ]
    if not note_titles or not table_titles:
        return ""
    if len(note_titles) == 1:
        note_label = note_titles[0]
    else:
        note_label = "、".join(note_titles[:2])
        if len(note_titles) > 2:
            note_label += "等"
    table_label = "、".join(table_titles[:6])
    if len(table_titles) > 6:
        table_label += "等"
    return f"附注「{note_label}」↔ 主表[{table_label}]"
