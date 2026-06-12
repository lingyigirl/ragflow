import json
import logging
from collections import defaultdict

from rag.nlp.search import index_name

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


def _parse_chain(val):
    if isinstance(val, list):
        return [str(x) for x in val]
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            if isinstance(parsed, list):
                return [str(x) for x in parsed]
        except Exception:
            pass
    return []


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


def _load_doc_cross_ref(doc_id):
    try:
        from api.db.services.document_service import DocumentService
        from api.utils.json_encode import unicode_unescape_text_fields

        docs = DocumentService.query(id=doc_id)
        if not docs:
            return None, []
        doc_row = docs[0]
        cross_ref = None
        if getattr(doc_row, "tree_cross_ref", None):
            cross_ref = unicode_unescape_text_fields(doc_row.tree_cross_ref)
        elif doc_row.tree and isinstance(doc_row.tree, dict):
            cross_ref = unicode_unescape_text_fields(doc_row.tree.get("cross_ref"))
        toc_index = []
        tree = doc_row.tree or {}
        if isinstance(tree, dict):
            toc_index = tree.get("toc_index") or []
        return cross_ref, toc_index
    except Exception:
        logging.exception("load doc cross_ref failed doc_id=%s", doc_id)
        return None, []


def _load_doc_es_index(doc_id):
    es_id_to_chain = {}
    chain_prefix_to_es_ids = defaultdict(set)
    es_id_pages = defaultdict(list)
    try:
        from api.db.db_models import MineruSection

        if not MineruSection.table_exists():
            return es_id_to_chain, chain_prefix_to_es_ids, []
        rows = MineruSection.select(
            MineruSection.es_id,
            MineruSection.parent_chain,
            MineruSection.page_idx,
        ).where(MineruSection.doc_id == str(doc_id).strip())
        for row in rows:
            es_id = str(row.es_id or "").strip()
            if not es_id:
                continue
            chain = _parse_chain(row.parent_chain)
            if chain and (es_id not in es_id_to_chain or len(chain) > len(es_id_to_chain[es_id])):
                es_id_to_chain[es_id] = chain
            es_id_pages[es_id].append(int(row.page_idx or 0))
            for depth in range(1, len(chain) + 1):
                chain_prefix_to_es_ids[tuple(chain[:depth])].add(es_id)
        ordered = sorted(es_id_pages.keys(), key=lambda eid: min(es_id_pages[eid]))
        return es_id_to_chain, chain_prefix_to_es_ids, ordered
    except Exception:
        logging.exception("load doc es index failed doc_id=%s", doc_id)
        return es_id_to_chain, chain_prefix_to_es_ids, []


def _detect_intent(doc_chunks, cross_ref):
    note_titles = list((cross_ref or {}).get("note_to_table_mapping", {}).keys()) or DEFAULT_NOTE_TITLES
    table_titles = [
        t.get("title", "")
        for t in ((cross_ref or {}).get("main_tables") or [])
        if isinstance(t, dict) and t.get("title")
    ] or DEFAULT_TABLE_TITLES
    has_note = False
    has_table = False
    hit_chains = []
    for ck in doc_chunks:
        chain = _parse_chain(ck.get("parent_chain"))
        if chain:
            hit_chains.append(chain)
        content = ck.get("content_with_weight", "") or ""
        if any(_chain_has_title(chain, nt) for nt in note_titles):
            has_note = True
        if any(kw in content for kw in note_titles):
            has_note = True
        if any(_chain_has_title(chain, tt) for tt in table_titles):
            has_table = True
        if any(tt in content for tt in table_titles):
            has_table = True
    return has_note, has_table, note_titles, table_titles, hit_chains


def _cross_ref_target_es_ids(has_note, has_table, cross_ref, note_titles, table_titles):
    targets = set()
    cref = cross_ref or {}
    table_map = cref.get("table_title_to_es_id") or {}
    note_table_map = cref.get("note_to_table_es_id") or {}
    note_map = cref.get("note_to_es_id") or {}
    if has_note:
        for note in note_titles:
            if note in note_table_map:
                targets.update(note_table_map[note])
            for table_name in (cref.get("note_to_table_mapping") or {}).get(note, []):
                es_id = table_map.get(table_name)
                if es_id:
                    targets.add(es_id)
            if note in note_map:
                targets.update(note_map[note])
        for item in cref.get("main_tables") or []:
            if isinstance(item, dict) and item.get("es_id"):
                targets.add(item["es_id"])
    if has_table:
        for item in cref.get("main_tables") or []:
            if isinstance(item, dict) and item.get("es_id"):
                targets.add(item["es_id"])
            elif isinstance(item, dict):
                es_id = table_map.get(item.get("title", ""))
                if es_id:
                    targets.add(es_id)
        for note, es_ids in note_map.items():
            if es_ids:
                targets.update(es_ids)
    return targets


def _parent_chain_target_es_ids(hit_chains, chain_prefix_to_es_ids):
    targets = set()
    for chain in hit_chains:
        if not chain:
            continue
        for depth in range(max(1, len(chain) - 1), len(chain) + 1):
            targets.update(chain_prefix_to_es_ids.get(tuple(chain[:depth]), set()))
    return targets


def _toc_target_es_ids(question, toc_index, es_id_to_chain, chain_prefix_to_es_ids):
    targets = set()
    if not question or not toc_index:
        return targets
    q = str(question).strip()
    if not q:
        return targets
    for node in toc_index:
        title = (node.get("title") or "").strip()
        if not title or len(title) < 2:
            continue
        if title not in q:
            matched = False
            for seg in title.replace("、", " ").replace("，", " ").split():
                seg = seg.strip()
                if len(seg) >= 2 and seg in q:
                    matched = True
                    break
            if not matched:
                continue
        depth = max(1, int(node.get("depth") or 1))
        for es_id, chain in es_id_to_chain.items():
            if _chain_has_title(chain, title):
                targets.add(es_id)
                pref = tuple(chain[:depth]) if len(chain) >= depth else tuple(chain)
                targets.update(chain_prefix_to_es_ids.get(pref, set()))
    return targets


def _adjacent_es_ids(es_ids, ordered_es_ids):
    if not ordered_es_ids:
        return set()
    pos = {eid: idx for idx, eid in enumerate(ordered_es_ids)}
    out = set()
    for es_id in es_ids:
        idx = pos.get(es_id)
        if idx is None:
            continue
        if idx > 0:
            out.add(ordered_es_ids[idx - 1])
        if idx + 1 < len(ordered_es_ids):
            out.add(ordered_es_ids[idx + 1])
    return out


def _fetch_and_append_chunks(dealer, chunks, doc_id, kb_id, tenant_ids, target_es_ids, doc_chunks):
    if not target_es_ids:
        return chunks
    existing_ids = {ck.get("chunk_id") for ck in chunks}
    idx_nms = [index_name(tid) for tid in tenant_ids]
    kb_ids = [kb_id] if isinstance(kb_id, str) else list(kb_id)
    field_list = [
        "content_with_weight",
        "doc_type_kwd",
        "docnm_kwd",
        "important_kwd",
        "img_id",
        "position_int",
        "parent_chain",
    ]
    base_sim = min([ck.get("similarity", 0.3) for ck in doc_chunks]) if doc_chunks else 0.3
    vector_size = 1024
    if doc_chunks and doc_chunks[0].get("vector"):
        vector_size = len(doc_chunks[0]["vector"])
    for es_id in target_es_ids:
        if not es_id or es_id in existing_ids:
            continue
        fields = None
        for idx_nm in idx_nms:
            try:
                fields = dealer.dataStore.get(es_id, idx_nm, kb_ids)
            except Exception:
                fields = None
            if fields:
                break
        if not fields:
            continue
        content = fields.get("content_with_weight", "")
        pchain = _parse_chain(fields.get("parent_chain"))
        chunks.append(
            {
                "chunk_id": es_id,
                "content_ltks": content,
                "content_with_weight": content,
                "doc_id": doc_id,
                "docnm_kwd": fields.get("docnm_kwd", ""),
                "kb_id": kb_id,
                "important_kwd": fields.get("important_kwd", []),
                "image_id": fields.get("img_id", ""),
                "similarity": base_sim * 0.5,
                "vector_similarity": 0.0,
                "term_similarity": 0.0,
                "vector": [0.0] * vector_size,
                "positions": fields.get("position_int", []),
                "parent_chain": pchain,
                "doc_type_kwd": fields.get("doc_type_kwd", ""),
            }
        )
        existing_ids.add(es_id)
    return chunks


def expand_financial_chunks_v2(dealer, chunks, tenant_ids, question=None):
    if not chunks:
        return chunks
    doc_ids = list({ck["doc_id"] for ck in chunks if ck.get("doc_id")})
    for doc_id in doc_ids:
        doc_chunks = [ck for ck in chunks if ck.get("doc_id") == doc_id]
        if not doc_chunks:
            continue
        kb_id = doc_chunks[0].get("kb_id")
        cross_ref, toc_index = _load_doc_cross_ref(doc_id)
        es_id_to_chain, chain_prefix_to_es_ids, ordered_es_ids = _load_doc_es_index(doc_id)
        has_note, has_table, note_titles, table_titles, hit_chains = _detect_intent(doc_chunks, cross_ref)
        targets = set()
        if has_note or has_table:
            targets.update(_cross_ref_target_es_ids(has_note, has_table, cross_ref, note_titles, table_titles))
            targets.update(_parent_chain_target_es_ids(hit_chains, chain_prefix_to_es_ids))
        targets.update(_toc_target_es_ids(question, toc_index, es_id_to_chain, chain_prefix_to_es_ids))
        if not targets:
            continue
        targets.update(_adjacent_es_ids(targets, ordered_es_ids))
        for ck in doc_chunks:
            cid = ck.get("chunk_id")
            if cid:
                targets.add(cid)
        chunks = _fetch_and_append_chunks(dealer, chunks, doc_id, kb_id, tenant_ids, targets, doc_chunks)
    return chunks
