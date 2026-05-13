# -*- coding: utf-8 -*-

import copy
import re
import os
import time
import asyncio
import aiohttp
import itertools
from dotenv import load_dotenv 
from rag.nlp import rag_tokenizer, tokenize_table, tokenize_chunks, add_positions

from deepdoc.parser.figure_parser import vision_figure_parser_pdf_wrapper
from deepdoc.parser.mineru_parser import MinerUParser, resolve_mineru_api_from_env
import logging

load_dotenv()

TITLE_NUM_RE = re.compile(r'^(\d+(?:\.\d+)*)')


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
        # r'^第[一二三四五六七八九十百千\d]+章',
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
    
    return 0


def strip_position_stamp(text):
    return re.sub(r'@@\d+(?:\s+[+-]?\d+(?:\.\d+)?){4}##', '', text)

def count_length(text):
    return len(text)


def index_format(idx, line, title_level=None):
    if title_level is not None:
        return f'{idx} @ [level={title_level}] {line}'
    return f'{idx} @ {line}'

def parse_answer_chunking_point(answer_string):
    points = []
    for line in answer_string.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(',')]
        if len(parts) < 2:
            continue
        try:
            point = int(parts[0])
            level = int(parts[1])
            if level == 1:
                points.append(point)
        except:
            continue
    return sorted(set(points))

def build_splits(origin_lines, points):
    if not origin_lines:
        return []

    sorted_points = sorted(
        p for p in points
        if isinstance(p, int) and 0 <= p < len(origin_lines)
    )

    splits = []
    prev = 0
    for p in sorted_points:
        if p > prev:
            splits.append((prev, p))
            prev = p
    if prev < len(origin_lines):
        splits.append((prev, len(origin_lines)))

    return splits


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

class InfModel:
    def __init__(self, model_path, max_new_token, window_size, model_deploy='ip:port', 
                 api_url=None, api_key=None, temperature=0.0, max_retries=20):
        self.model_path = model_path
        self.max_new_token = max_new_token
        self.window_size = window_size
        self.model_deploy = model_deploy
        self.api_url = api_url
        self.api_key = api_key
        self.temperature = temperature
        self.max_retries = max_retries
        self.inf_func = self.inf_api

    def apply_chat_template(self, question, known_answer_str=''):
        prefix_ans = known_answer_str
        return f"""<|im_start|>user\n{question}<|im_end|>\n<|im_start|>assistant\n<think>\n</think>\n\n{prefix_ans}"""

    async def inf_api(self, question, request_id, known_answer_str=''):
        text = self.apply_chat_template(question, known_answer_str)
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        post_data = {
            "model": self.model_path,
            "messages": [{"role": "user", "content": text}],
            "temperature": self.temperature,
            "max_tokens": self.max_new_token,
        }

        api_endpoint = self.api_url or "http://172.19.0.3:8080/v1/chat/completions"
        if "/chat/completions" not in api_endpoint:
            api_endpoint = api_endpoint.rstrip("/") + "/chat/completions"

        async with aiohttp.ClientSession() as session:
            for attempt in range(self.max_retries):
                try:
                    async with session.post(api_endpoint, json=post_data, headers=headers, timeout=aiohttp.ClientTimeout(total=300)) as resp:
                        if resp.status != 200:
                            error_text = await resp.text()
                            raise RuntimeError(f"HTTP {resp.status}: {error_text}")
                        pred = await resp.json()
                        if 'error' in pred:
                            raise RuntimeError(pred['error'].get('message', str(pred['error'])))
                        choices = pred.get('choices', [])
                        if not choices:
                            raise RuntimeError(f"Empty choices: {pred}")
                        pred_text = choices[0].get('message', {}).get('content', "")
                        return pred_text, text
                except Exception as e:
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(min(5*(attempt+1), 30))
                    else:
                        raise RuntimeError(f"Max retries reached: {e}")

def build_chunk_points_by_title_level(lines_with_level):
    if not lines_with_level:
        return [0]

    levels = [
        item[1] if isinstance(item, (list, tuple)) and len(item) >= 2 else 0
        for item in lines_with_level
    ]
    n = len(levels)

    level_to_indices = {}
    for i, lvl in enumerate(levels):
        if lvl > 0:
            level_to_indices.setdefault(lvl, []).append(i)

    chunk_starts = [0]
    for i, lvl in enumerate(levels):
        if lvl > 0 and len(level_to_indices.get(lvl, [])) > 1:
            if i not in chunk_starts:
                chunk_starts.append(i)

    if n not in chunk_starts:
        chunk_starts.append(n)

    return sorted(set(chunk_starts))


class InferenceEngine:
    def __init__(self, model_path, window_size, model_deploy, max_new_token=4096, 
                 api_url=None, api_key=None, temperature=0.0, max_retries=20):
        self.window_size = window_size
        self.model = InfModel(model_path, max_new_token, window_size, model_deploy,
                              api_url=api_url, api_key=api_key, temperature=temperature, max_retries=max_retries)
        self.request_ids = ("".join(x) for x in itertools.product("0123456789", repeat=9))

    async def iterative_inf(self, document, limit=-1, lines_with_level=None):
        original_lines_with_level = lines_with_level
        enable_llm_merging = False
        level1_chunk_points = None
        if original_lines_with_level is not None and len(original_lines_with_level) > 0:
            level1_indices = set()
            for idx, item in enumerate(original_lines_with_level):
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    text_content = item[0]
                else:
                    text_content = str(item)
                computed_level = get_section_title_level(strip_position_stamp(text_content))
                if computed_level == 1:
                    level1_indices.add(idx)
            level1_chunk_points = sorted(set([0] + list(level1_indices)))
        blocks = []
        block_to_original_mapping = []
        input_count = len(original_lines_with_level) if original_lines_with_level else 0

        if lines_with_level is not None and len(lines_with_level) > 0:
            base_points = build_chunk_points_by_title_level(lines_with_level)
            
            if base_points:
                for block_idx, (s, e) in enumerate(zip(base_points, base_points[1:] + [len(lines_with_level)])):
                    if s < len(lines_with_level) and e <= len(lines_with_level) and s < e:
                        chunk_lines = lines_with_level[s:e]
                        if chunk_lines:
                            texts = []
                            max_level = 0
                            for idx_in_chunk, x in enumerate(chunk_lines):
                                if isinstance(x, (list, tuple)) and len(x) >= 2:
                                    text_content = x[0]
                                    text_level = x[1]
                                    texts.append(text_content)
                                    max_level = max(max_level, text_level)
                                else:
                                    text_content = str(x)
                                    texts.append(text_content)
                            
                            block_text = '\n'.join(texts)
                            blocks.append((block_text, max_level))
                            block_to_original_mapping.append((s, e))
            
            if blocks:
                lines_with_level = blocks
        else:
            if lines_with_level is None:
                lines_with_level = []
            if not blocks:
                block_to_original_mapping = []

        if lines_with_level is not None and len(lines_with_level) > 0:
            lines = []
            origin_lines = []
            for item in lines_with_level:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    line_text, title_level = item[0], item[1]
                else:
                    line_text = str(item)
                    title_level = 0
                lines.append(line_text)
                origin_lines.append(strip_position_stamp(line_text))
        else:
            lines = list(filter(lambda l: l.strip(), map(str.strip, document.split('\n'))))
            origin_lines = [strip_position_stamp(l) for l in lines]
            lines_with_level = [(l, 0) for l in lines]

        global_chunk_points = [[]]
        raw_qa = []
        error_count = 0
        
        if enable_llm_merging and blocks and block_to_original_mapping:
            current_blocks = blocks[:]
            current_mapping = block_to_original_mapping[:]

            for target_level in [4, 3, 2, 1]:
                same_level_ranges = []
                current_start = None

                for block_idx, block_item in enumerate(current_blocks):
                    if isinstance(block_item, (list, tuple)) and len(block_item) >= 2:
                        block_level = block_item[1]
                    else:
                        block_level = 0
                    
                    if block_level == target_level:
                        if current_start is None:
                            current_start = block_idx
                    else:
                        if current_start is not None:
                            same_level_ranges.append((current_start, block_idx, target_level))
                            current_start = None
                
                if current_start is not None:
                    same_level_ranges.append((current_start, len(current_blocks), target_level))

                level_merge_points = set()
                level_merge_points.add(0)
                
                for range_idx, (range_start, range_end, range_level) in enumerate(same_level_ranges):
                    if range_end - range_start <= 1:
                        level_merge_points.add(range_start)
                        if range_end < len(current_blocks):
                            level_merge_points.add(range_end)
                        continue
                    
                    range_blocks = current_blocks[range_start:range_end]
                    range_blocks_for_input = [(block_item[0] if isinstance(block_item, (list, tuple)) else str(block_item), 
                                              block_item[1] if isinstance(block_item, (list, tuple)) and len(block_item) >= 2 else 0)
                                             for block_item in range_blocks]
                    
                    range_prompt = (
                        "You are a senior financial analyst and document understanding expert. "
                        "The following semantic blocks are from the SAME title level (level=" + str(range_level) + ") "
                        "and are ADJACENT in the PDF document. "
                        "Your task is to determine if these blocks are semantically continuous and can be merged.\n\n"
                        "CRITICAL RULES:\n"
                        "1. You can ONLY merge adjacent blocks within this range.\n"
                        "2. You CANNOT skip any block, CANNOT split blocks, CANNOT create new boundaries.\n"
                        "3. You can merge some blocks, all blocks, or keep all blocks separate.\n"
                        "4. Output ONLY the starting block indices (0-based within this range) where a new chunk should start.\n"
                        "5. Format: '{block_index}, 1, yes' for each chunk start.\n"
                        "6. The first block (index 0) is always a chunk start.\n\n"
                        ">>> Input blocks (same level, adjacent):\n"
                    )
                    
                    range_question = range_prompt
                    for local_idx, (block_text, block_level) in enumerate(range_blocks_for_input):
                        range_question += index_format(local_idx, block_text, block_level)
                    
                    start_time = time.time()
                    try:
                        answer, revised_question = await self.model.inf_func(
                            range_question, next(self.request_ids)
                        )
                        end_time = time.time()
                        
                        tmp = {
                            'level': target_level,
                            'range_idx': range_idx,
                            'range_start': range_start,
                            'range_end': range_end,
                            'range_level': range_level,
                            'question': revised_question,
                            'answer': answer,
                            'time': end_time - start_time,
                            'question_token_num': count_length(range_question),
                            'answer_token_num': count_length(answer)
                        }
                        
                        points = parse_answer_chunking_point(answer)
                        
                        if points:
                            global_points = [range_start + p for p in points if 0 <= p < (range_end - range_start)]
                            global_points = sorted(set(global_points))
                            
                            if global_points and global_points[0] == range_start:
                                validated_points = [p for p in global_points if range_start <= p <= range_end]
                                if validated_points and validated_points[-1] <= range_end:
                                    for p in validated_points:
                                        level_merge_points.add(p)
                                    level_merge_points.add(range_end)
                                    tmp['status'] = 'check ok'
                                    tmp['validated_points'] = validated_points
                                else:
                                    tmp['status'] = 'invalid points'
                                    error_count += 1
                                    level_merge_points.add(range_start)
                                    level_merge_points.add(range_end)
                            else:
                                tmp['status'] = 'first point error'
                                error_count += 1
                                level_merge_points.add(range_start)
                                level_merge_points.add(range_end)
                        else:
                            tmp['status'] = 'empty points'
                            error_count += 1
                            level_merge_points.add(range_start)
                            level_merge_points.add(range_end)
                        
                        raw_qa.append(tmp)
                        
                    except Exception as e:
                        error_count += 1
                        level_merge_points.add(range_start)
                        level_merge_points.add(range_end)
                
                level_merge_points.add(len(current_blocks))
                
                for block_idx, block_item in enumerate(current_blocks):
                    if isinstance(block_item, (list, tuple)) and len(block_item) >= 2:
                        block_level = block_item[1]
                    else:
                        block_level = 0
                    if block_level != target_level:
                        level_merge_points.add(block_idx)
                        if block_idx + 1 < len(current_blocks):
                            level_merge_points.add(block_idx + 1)
                
                merge_points = sorted(list(level_merge_points))
                
                new_blocks = []
                new_mapping = []
                
                for i in range(len(merge_points) - 1):
                    chunk_start = merge_points[i]
                    chunk_end = merge_points[i + 1]
                    
                    merged_texts = []
                    merged_max_level = 0
                    merged_orig_start = None
                    merged_orig_end = None
                    
                    for block_idx in range(chunk_start, chunk_end):
                        if block_idx < len(current_blocks):
                            block_item = current_blocks[block_idx]
                            if isinstance(block_item, (list, tuple)) and len(block_item) >= 2:
                                block_text = block_item[0]
                                block_level = block_item[1]
                            else:
                                block_text = str(block_item)
                                block_level = 0
                            
                            merged_texts.append(block_text)
                            merged_max_level = max(merged_max_level, block_level)
                            
                            if block_idx < len(current_mapping):
                                orig_start, orig_end = current_mapping[block_idx]
                                if merged_orig_start is None:
                                    merged_orig_start = orig_start
                                merged_orig_end = orig_end
                    
                    if merged_texts:
                        merged_text = '\n'.join(merged_texts)
                        new_blocks.append((merged_text, merged_max_level))
                        if merged_orig_start is not None and merged_orig_end is not None:
                            new_mapping.append((merged_orig_start, merged_orig_end))
                
                current_blocks = new_blocks
                current_mapping = new_mapping

            validated_block_points = list(range(len(current_blocks) + 1))
            
            final_points = [0]
            for i in range(len(validated_block_points) - 1):
                chunk_block_start = validated_block_points[i]
                chunk_block_end = validated_block_points[i + 1] - 1

                if 0 <= chunk_block_end < len(current_mapping):
                    _, end_orig = current_mapping[chunk_block_end]
                    if end_orig not in final_points and end_orig <= len(original_lines_with_level):
                        final_points.append(end_orig)
            
            if original_lines_with_level and len(original_lines_with_level) not in final_points:
                final_points.append(len(original_lines_with_level))
            
            final_points = sorted(set(final_points))
            global_chunk_points[0] = sorted(set(final_points))
        else:
            if level1_chunk_points is not None:
                final_points = level1_chunk_points
            else:
                level1_indices = set()
                if lines_with_level is not None and len(lines_with_level) > 0:
                    for idx, item in enumerate(lines_with_level):
                        if isinstance(item, (list, tuple)) and len(item) >= 2:
                            text_content = item[0]
                        else:
                            text_content = str(item)
                        computed_level = get_section_title_level(strip_position_stamp(text_content))
                        if computed_level == 1:
                            level1_indices.add(idx)
                final_points = sorted(set([0] + list(level1_indices)))
            
            if 0 not in final_points:
                final_points.insert(0, 0)
            
            global_chunk_points[0] = sorted(set(final_points))

        if global_chunk_points and global_chunk_points[0]:
            chunk_points = global_chunk_points[0]
            chunk_points = sorted(set(chunk_points))
            if 0 not in chunk_points:
                chunk_points.insert(0, 0)
            if original_lines_with_level:
                max_idx = len(original_lines_with_level)
                chunk_points = [p for p in chunk_points if 0 <= p <= max_idx]
                if max_idx not in chunk_points:
                    chunk_points.append(max_idx)
            global_chunk_points[0] = sorted(set(chunk_points))
        
        if original_lines_with_level and len(original_lines_with_level) > 0:
            original_lines_text = [item[0] if isinstance(item, (list, tuple)) else str(item) for item in original_lines_with_level]
            original_lines_stripped = [strip_position_stamp(l) for l in original_lines_text]
            splits = build_splits(original_lines_stripped, global_chunk_points[0] if global_chunk_points and global_chunk_points[0] else [])
        else:
            splits = build_splits(origin_lines, global_chunk_points[0] if global_chunk_points and global_chunk_points[0] else [])

        if splits:
            seen_ranges = set()
            validated_splits = []
            prev_end = 0
            
            for start_idx, end_idx in splits:
                if start_idx >= end_idx:
                    continue
                
                if start_idx < prev_end:
                    start_idx = prev_end
                    if start_idx >= end_idx:
                        continue
                
                split_key = (start_idx, end_idx)
                if split_key not in seen_ranges:
                    seen_ranges.add(split_key)
                    validated_splits.append(split_key)
                    prev_end = end_idx
            
            validated_splits = sorted(validated_splits, key=lambda x: x[0])
            splits = validated_splits

        num_points = len(global_chunk_points[0]) if global_chunk_points and global_chunk_points[0] else 0

        result = {
            'multi_level_seg_points': global_chunk_points,
            'raw_qa': raw_qa,
            'error_count': error_count,
            'splits': splits
        }
        return result


def chunk(filename, binary=None, lang="Chinese", callback=None, **kwargs):
    llm_config = {
        "model_path": kwargs.get("model_path", os.environ.get("HICHUNK_MODEL_PATH", "qwen3-30b-a3b-instruct-2507-fp8")),
        "window_size": kwargs.get("window_size", int(os.environ.get("HICHUNK_WINDOW_SIZE", "16384"))),
        "model_deploy": kwargs.get("model_deploy", "ip:port"),
        "max_new_token": kwargs.get("max_new_token", int(os.environ.get("HICHUNK_MAX_TOKEN", "8192"))),
        "api_url": kwargs.get("api_url", os.environ.get("HICHUNK_API_URL", "http://172.19.0.3:8080/v1/chat/completions")), 
        "api_key": kwargs.get("api_key", os.environ.get("HICHUNK_API_KEY", "gpustack_293c70e664a90d95_b9d12e775692d8770d509f842e0ee81f")),         
        "temperature": kwargs.get("temperature", 0.0),
        "max_retries": kwargs.get("max_retries", 20)
    }

    parser_config = kwargs.get("parser_config", {"chunk_token_num": 512, "delimiter": "\n!?。！？；，、"})
    parser_config = copy.deepcopy(parser_config)
    limit = kwargs.get("limit", int(os.environ.get("HICHUNK_LIMIT", "100")))

    # Excel 走 MinerU 时将文档名归一为 .pdf，确保与手动“先转 PDF 再解析”元数据一致
    normalized_doc_name = re.sub(r"\.(xlsx?|xlsm)$", ".pdf", filename, flags=re.IGNORECASE)
    doc = {"docnm_kwd": normalized_doc_name}
    doc["title_tks"] = rag_tokenizer.tokenize(re.sub(r"\.[a-zA-Z]+$", "", doc["docnm_kwd"]))
    doc["title_sm_tks"] = rag_tokenizer.fine_grained_tokenize(doc["title_tks"])
    eng = lang.lower() == "english"

    sections, tbls = [], []
    table_indices_in_mineru = []  

    is_mineru_doc = re.search(r"\.(pdf|xlsx?|xlsm)$", filename, re.IGNORECASE)
    is_mineru_img = re.search(r"\.(jpe?g|png)$", filename, re.IGNORECASE)
    if is_mineru_doc or is_mineru_img:
        is_excel_mineru_path = bool(re.search(r"\.(xlsx?|xlsm)$", filename, re.IGNORECASE))
        if callback:
            callback(0.1, "Start MinerU parsing (PDF or image).")

        mineru_executable = os.environ.get("MINERU_EXECUTABLE", "mineru")
        _mineru_api_cfg = parser_config.get("mineru_api_base")
        mineru_api = _mineru_api_cfg.strip().rstrip("/") if isinstance(_mineru_api_cfg, str) else ""
        if not mineru_api:
            mineru_api = resolve_mineru_api_from_env()
        mineru_parser = MinerUParser(mineru_path=mineru_executable, mineru_api=mineru_api)

        backend = (parser_config.get("mineru_backend") or os.environ.get("MINERU_BACKEND", "hybrid-auto-engine")).strip() or "hybrid-auto-engine"

        mineru_ok, _mineru_install_reason = mineru_parser.check_installation(backend)
        if not mineru_ok:
            if is_excel_mineru_path:
                logging.error(
                    "[MinerU][Excel] MinerU 不可用，已禁用 naive 回退: file=%s backend=%s parser_config=%s",
                    filename,
                    backend,
                    parser_config,
                )
                if callback:
                    callback(-1, "Excel+MinerU：MinerU 不可用，已禁用 naive 回退，请检查 MINERU_EXECUTABLE / mineru_api_base。")
                raise RuntimeError("Excel+MinerU: MinerU unavailable, naive fallback disabled for spreadsheet.")
            return _fallback_general_docs(filename, binary, lang, callback, kwargs, "MinerU is unavailable.")

        logging.info("[MinerU] Start parse: file=%s, backend=%s, parser_config=%s", filename, backend, parser_config)
        try:
            mineru_sections, mineru_tables = mineru_parser.parse_document(
                filepath=filename,
                binary=binary,
                callback=callback,
                output_dir=os.environ.get("MINERU_OUTPUT_DIR", ""),
                backend=backend,
                delete_output=bool(int(os.environ.get("MINERU_DELETE_OUTPUT", 1))),
            )
        except KeyError as exc:
            if str(exc).strip("'\"") == "type":
                if is_excel_mineru_path:
                    logging.exception(
                        "[MinerU][Excel] 输出缺少 type，已禁用 naive 回退: file=%s backend=%s parser_config=%s",
                        filename,
                        backend,
                        parser_config,
                    )
                    if callback:
                        callback(
                            -1,
                            f"Excel+MinerU：MinerU 输出缺少 type，已禁用 naive 回退。file={filename} backend={backend}",
                        )
                    raise RuntimeError("Excel+MinerU: MinerU output missing 'type', naive fallback disabled.") from exc
                logging.exception("MinerU parser output misses 'type'; file=%s, backend=%s, parser_config=%s", filename, backend, parser_config)
                return _fallback_general_docs(filename, binary, lang, callback, kwargs, "MinerU output missing 'type'.")
            else:
                raise
        except Exception as exc:
            if is_excel_mineru_path:
                logging.exception(
                    "[MinerU][Excel] 解析失败，已禁用 naive 回退: file=%s backend=%s parser_config=%s exc_type=%s exc_repr=%r",
                    filename,
                    backend,
                    parser_config,
                    type(exc).__name__,
                    exc,
                )
                if callback:
                    callback(
                        -1,
                        f"Excel+MinerU 解析失败（已禁用 naive 回退）: {type(exc).__name__}: {exc!s}. file={filename} backend={backend}",
                    )
                raise RuntimeError(f"Excel+MinerU parse failed, naive fallback disabled: {exc!s}") from exc
            logging.exception("MinerU parser failed; file=%s, backend=%s, parser_config=%s", filename, backend, parser_config)
            return _fallback_general_docs(filename, binary, lang, callback, kwargs, f"MinerU parse failed: {exc}")

        logging.info("[MinerU] Raw output count: sections=%s, tables=%s", len(mineru_sections), len(mineru_tables)) 
        for idx, item in enumerate(mineru_sections):
            text = (item[0] if len(item) >= 1 else "").strip()
            preview = (text[:])
            preview = preview.replace("\n", " ").replace("\r", " ")
            raw_pos = item[1] if len(item) > 1 else None
            logging.info("[MinerU][RawOutput][%d] pos=%s text=%s", idx + 1, raw_pos, preview) 

        count_before_dedup = len(mineru_sections)
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
            else:
                pass  
        mineru_sections = unique_sections

        logging.info("[第二步 PDF解析] 去重后解析文本结果（每行一个段落）:")
        for idx, item in enumerate(mineru_sections):
            text = (item[0] if len(item) >= 1 else "").strip()
            preview = text.replace("\n", " ").replace("\r", " ") if text else ""
            logging.info("  [%d] %s", idx + 1, preview)

        mineru_sections_with_level = []
        for item in mineru_sections:
            if len(item) == 2:
                text, pos_tag = item
                text = " ".join((text or "").strip().split())
                title_level = 0 if is_html_table(text) else get_section_title_level(text)
                mineru_sections_with_level.append((text, pos_tag, title_level))
            elif len(item) == 3:
                text = " ".join((item[0] or "").strip().split())
                title_level = 0 if is_html_table(text) else get_section_title_level(text)
                mineru_sections_with_level.append((text, item[1], title_level))
            else:
                text = item[0] if len(item) > 0 else ""
                pos_tag = item[1] if len(item) > 1 else None
                text = " ".join((text or "").strip().split())
                title_level = 0 if (not text or is_html_table(text)) else get_section_title_level(text)
                mineru_sections_with_level.append((text, pos_tag, title_level))

        mineru_sections = mineru_sections_with_level
        levels_display = []
        for item in mineru_sections:
            text = item[0] if len(item) >= 1 else ""
            lv = item[2] if len(item) >= 3 else 0
            levels_display.append("tab" if is_html_table(text) else lv)
        lines_with_level_for_chunk = [
            (item[0], item[2]) if len(item) >= 3 else (item[0] if len(item) >= 1 else "", 0)
            for item in mineru_sections
        ]
        base_points = build_chunk_points_by_title_level(lines_with_level_for_chunk)
        chunks_levels = [
            levels_display[s:e]
            for s, e in zip(base_points, base_points[1:] + [len(levels_display)])
            if s < e
        ]
        # logging.info(
        #     "[第二步 标题层级] 划分列表（0=原文 1=一级 2=二级 3=三级 4=四级标题 tab=表格）: %s",
        #     chunks_levels,
        # )

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
            else:
                text = section_item[0] if len(section_item) > 0 else ""
                pos_tag = None
                title_level = 0
            
            poss = _normalize_pos_list(mineru_parser.extract_positions(pos_tag)) if pos_tag else []
            if is_html_table(text):
                tbls.append(((None, text), poss if poss else []))
                table_indices_in_mineru.append(idx)
                sections.append((text, idx, poss, 0))
            else:
                sections.append((text, idx, poss, title_level))
            section_preview = (text or "").replace("\n", " ").replace("\r", " ").strip()
            logging.info("[MinerU][Section][%d] title_level=%s poss=%s text=%s", idx + 1, title_level, poss, section_preview[:500])  # 记录 section 归一化后位置和文本
        
                        
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

        if not hasattr(mineru_parser, 'outlines'):
            mineru_parser.outlines = []

        if callback:
            callback(0.3, "Finish MinerU parsing.")

    lines = []
    section_idx_mapping = []
    for i, section_item in enumerate(sections):
        if len(section_item) >= 3:
            txt, sec_id, poss = section_item[0], section_item[1], section_item[2]
            title_level = section_item[3] if len(section_item) >= 4 else 0
        else:
            txt = section_item[0] if len(section_item) > 0 else ""
            sec_id = section_item[1] if len(section_item) > 1 else i
            poss = section_item[2] if len(section_item) > 2 else []
            title_level = 0
        
        if txt and txt.strip():
            lines.append((txt, title_level))
            section_idx_mapping.append(i) 
  
    inf_engine = InferenceEngine(
        model_path=llm_config["model_path"],
        window_size=llm_config["window_size"],
        model_deploy=llm_config["model_deploy"],
        max_new_token=llm_config["max_new_token"],
        api_url=llm_config["api_url"],
        api_key=llm_config["api_key"],
        temperature=llm_config["temperature"],
        max_retries=llm_config["max_retries"]
    )
    lines_text_only = [item[0] if isinstance(item, (list, tuple)) else str(item) for item in lines]
    lines_with_level_for_inf = [(item[0] if isinstance(item, (list, tuple)) else str(item), 
                                  item[1] if isinstance(item, (list, tuple)) and len(item) >= 2 else 0) 
                                 for item in lines]
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            inf_engine.iterative_inf('\n'.join(lines_text_only), limit,
                                     lines_with_level=lines_with_level_for_inf)
        )
    except Exception:
        logging.exception("HiChunk inference failed for %s, degrading to a single text chunk.", filename)
        if callback:
            callback(0.6, "HiChunk inference failed, degrade to rule-based single chunk output.")
        result = {"splits": [(0, len(lines))] if lines else []}
    finally:
        loop.close()

    # splits_from_inf = result.get('splits', [])
    # logging.info("[第三步 智能分块] 输出 | 得到 splits 数: %d", len(splits_from_inf))

    if len(lines) != len(section_idx_mapping):
        if len(section_idx_mapping) < len(lines):
            last_idx = section_idx_mapping[-1] if section_idx_mapping else 0
            section_idx_mapping.extend([last_idx] * (len(lines) - len(section_idx_mapping)))
        else:
            section_idx_mapping = section_idx_mapping[:len(lines)]

    chunks = [] 
    chunk_positions = [] 
    chunk_mineru_indices = []

    splits = result.get('splits', [])
    
    if not splits:
        if lines and len(lines) > 0:
            splits = [(0, len(lines))]
        else:
            return _fallback_general_docs(filename, binary, lang, callback, kwargs, "No text extracted from MinerU path.")
    
    if not lines or len(lines) == 0:
        return _fallback_general_docs(filename, binary, lang, callback, kwargs, "No lines available for HiChunk.")
    
    if splits:
        splits = sorted(splits, key=lambda x: x[0])
        validated_splits = []
        seen_ranges = set()
        prev_end = 0
        
        for start_idx, end_idx in splits:
            if start_idx >= end_idx:
                continue
            
            if start_idx < prev_end:
                start_idx = prev_end
                if start_idx >= end_idx:
                    continue
            
            split_key = (start_idx, end_idx)
            if split_key not in seen_ranges:
                seen_ranges.add(split_key)
                validated_splits.append((start_idx, end_idx))
                prev_end = end_idx
        
        splits = validated_splits

    if not splits and lines and len(lines) > 0:
        splits = [(0, len(lines))]

    boundaries = set()
    boundaries.add(0)
    boundaries.add(len(lines))
    for start_idx, end_idx in splits:
        boundaries.add(start_idx)
        boundaries.add(end_idx)
    sorted_b = sorted(boundaries)
    splits = [
        (sorted_b[j], sorted_b[j + 1])
        for j in range(len(sorted_b) - 1)
        if sorted_b[j] < sorted_b[j + 1]
    ]

    last_title_idx_before = [{} for _ in range(len(lines) + 1)]
    last_at = {}
    for i in range(len(lines)):
        last_title_idx_before[i] = dict(last_at)
        item = lines[i] if i < len(lines) else ((), 0)
        lv = item[1] if isinstance(item, (list, tuple)) and len(item) >= 2 else 0
        if lv > 0:
            last_at[lv] = i
    last_title_idx_before[len(lines)] = dict(last_at)

    for split_idx, (start_idx, end_idx) in enumerate(splits):
        start_idx = max(0, min(start_idx, len(lines) - 1))
        end_idx = min(end_idx, len(lines))
        end_idx = min(end_idx, len(section_idx_mapping))

        if start_idx >= end_idx:
            continue

        chunk_lines_items = lines[start_idx:end_idx]
        
        if not chunk_lines_items:
            continue
        
        chunk_lines = []
        for item in chunk_lines_items:
            if isinstance(item, (list, tuple)) and len(item) >= 1:
                line_text = item[0]
            else:
                line_text = str(item) if item else ""
            
            if line_text and str(line_text).strip():
                chunk_lines.append(str(line_text))
        
        if not chunk_lines:
            continue

        ancestor_indices = []
        clean_chunk_text = '\n'.join(chunk_lines)
        chunks.append(clean_chunk_text)

        poss_list = []
        mineru_indices_in_chunk = set()
        for idx in ancestor_indices:
            if 0 <= idx < len(section_idx_mapping):
                sec_idx = section_idx_mapping[idx]
                if 0 <= sec_idx < len(sections):
                    section_item = sections[sec_idx]
                    if len(section_item) > 1:
                        mineru_indices_in_chunk.add(section_item[1])
                    if len(section_item) > 2 and section_item[2]:
                        poss_list.extend(section_item[2])
        for line_idx in range(start_idx, end_idx):
            if 0 <= line_idx < len(section_idx_mapping):
                sec_idx = section_idx_mapping[line_idx]
                if 0 <= sec_idx < len(sections):
                    section_item = sections[sec_idx]
                    if len(section_item) > 1:
                        mineru_idx = section_item[1]
                        mineru_indices_in_chunk.add(mineru_idx)
                    if len(section_item) > 2:
                        section_poss = section_item[2]
                        if section_poss:
                            poss_list.extend(section_poss)

        chunk_positions.append(poss_list)
        if mineru_indices_in_chunk:
            chunk_mineru_indices.append({
                'min': min(mineru_indices_in_chunk),
                'max': max(mineru_indices_in_chunk)
            })
        else:
            chunk_mineru_indices.append({'min': -1, 'max': -1})

    if not chunks or len(chunks) == 0:

        if lines and len(lines) > 0:
            all_chunk_lines = []
            for item in lines:
                if isinstance(item, (list, tuple)) and len(item) >= 1:
                    line_text = item[0]
                else:
                    line_text = str(item) if item else ""
                if line_text and str(line_text).strip():
                    all_chunk_lines.append(str(line_text))
            if all_chunk_lines:
                fallback_chunk = '\n'.join(all_chunk_lines)
                chunks = [fallback_chunk]
                chunk_positions = [[]]
                chunk_mineru_indices = [{'min': -1, 'max': -1}]

    levels_display_step3 = []
    for item in lines:
        txt = item[0] if isinstance(item, (list, tuple)) and len(item) >= 1 else ""
        lv = item[1] if isinstance(item, (list, tuple)) and len(item) >= 2 else 0
        levels_display_step3.append("tab" if is_html_table(txt) else lv)
    chunks_levels_step3 = [
        levels_display_step3[s:e]
        for (s, e) in splits
        if s < e and 0 <= s <= len(levels_display_step3) and 0 <= e <= len(levels_display_step3)
    ]
    # logging.info(
    #     "[第三步 智能分块] 最终输出（0=原文 1=一级 2=二级 3=三级 4=四级标题 tab=表格）: %s",
    #     chunks_levels_step3,
    # )

    chunks_len = len(chunks)
    positions_len = len(chunk_positions)
    indices_len = len(chunk_mineru_indices)
    
    if chunks_len != positions_len or chunks_len != indices_len:
        while len(chunk_positions) < chunks_len:
            chunk_positions.append([])
        while len(chunk_mineru_indices) < chunks_len:
            chunk_mineru_indices.append({'min': -1, 'max': -1})
        chunk_positions = chunk_positions[:chunks_len]
        chunk_mineru_indices = chunk_mineru_indices[:chunks_len]
    
    valid_chunks = []
    valid_positions = []
    valid_indices = []
    for i, chunk_text in enumerate(chunks):
        if chunk_text and str(chunk_text).strip():
            valid_chunks.append(chunk_text)
            valid_positions.append(chunk_positions[i] if i < len(chunk_positions) else [])
            valid_indices.append(chunk_mineru_indices[i] if i < len(chunk_mineru_indices) else {'min': -1, 'max': -1})
    
    if len(valid_chunks) != len(chunks):
        chunks = valid_chunks
        chunk_positions = valid_positions
        chunk_mineru_indices = valid_indices

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
        sanitized_tbls.append(((None, table_text), table_pos if table_pos else []))
    table_docs = tokenize_table(sanitized_tbls, doc, eng)
    chunk_docs = tokenize_chunks(chunks, doc, eng)

    for i, chunk_doc in enumerate(chunk_docs):
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
    
    if is_mineru_doc or is_mineru_img:
        for i, table_doc in enumerate(table_docs):
            all_elements.append({
                'type': 'table',
                'doc': table_doc,
                'mineru_index': 999999, 
                'mineru_range': {'min': 999999, 'max': 999999}
            })
    else:
        for table_doc in table_docs:
            all_elements.append({
                'type': 'table',
                'doc': table_doc,
                'mineru_index': 999999,
                'mineru_range': {'min': 999999, 'max': 999999}
            })
    
    all_elements.sort(key=lambda x: x['mineru_index'])
    res = [elem['doc'] for elem in all_elements]
    # logging.info(f"Chunking completed: {len([e for e in all_elements if e['type'] == 'chunk'])} chunks + {len([e for e in all_elements if e['type'] == 'table'])} tables")

    if callback:
        callback(1.0, "Finish chunking.")

    return res
