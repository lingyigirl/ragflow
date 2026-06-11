#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
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


import os
import re  # split_text_preserving_tables 中解析 HTML 表格块需要正则
import tiktoken
import numpy as np

from common.file_utils import get_project_base_directory

tiktoken_cache_dir = get_project_base_directory()
os.environ["TIKTOKEN_CACHE_DIR"] = tiktoken_cache_dir
# encoder = tiktoken.encoding_for_model("gpt-3.5-turbo")
encoder = tiktoken.get_encoding("cl100k_base")


def num_tokens_from_string(string: str) -> int:
    """Returns the number of tokens in a text string."""
    try:
        code_list = encoder.encode(string)
        return len(code_list)
    except Exception:
        return 0

def total_token_count_from_response(resp):
    """
    Extract token count from LLM response in various formats.

    Handles None responses and different response structures from various LLM providers.
    Returns 0 if token count cannot be determined.
    """
    if resp is None:
        return 0

    try:
        if hasattr(resp, "usage") and hasattr(resp.usage, "total_tokens"):
            return resp.usage.total_tokens
    except Exception:
        pass

    try:
        if hasattr(resp, "usage_metadata") and hasattr(resp.usage_metadata, "total_tokens"):
            return resp.usage_metadata.total_tokens
    except Exception:
        pass

    try:
        if hasattr(resp, "meta") and hasattr(resp.meta, "billed_units") and hasattr(resp.meta.billed_units, "input_tokens"):
            return resp.meta.billed_units.input_tokens
    except Exception:
        pass

    if isinstance(resp, dict) and 'usage' in resp and 'total_tokens' in resp['usage']:
        try:
            return resp["usage"]["total_tokens"]
        except Exception:
            pass

    if isinstance(resp, dict) and 'usage' in resp and 'input_tokens' in resp['usage'] and 'output_tokens' in resp['usage']:
        try:
            return resp["usage"]["input_tokens"] + resp["usage"]["output_tokens"]
        except Exception:
            pass

    if isinstance(resp, dict) and 'meta' in resp and 'tokens' in resp['meta'] and 'input_tokens' in resp['meta']['tokens'] and 'output_tokens' in resp['meta']['tokens']:
        try:
            return resp["meta"]["tokens"]["input_tokens"] + resp["meta"]["tokens"]["output_tokens"]
        except Exception:
            pass
    return 0


def truncate(string: str, max_len: int) -> str:
    """Returns truncated text if the length of text exceed max_len."""
    return encoder.decode(encoder.encode(string)[:max_len])


def split_text_by_token_budget(string: str, max_tokens: int) -> list[str]:
    """按 token 预算切分文本，供超长 chunk 分批 embedding 使用。"""
    if not string:
        return [""]
    if max_tokens <= 0:
        return [string]
    tokens = encoder.encode(string)
    if len(tokens) <= max_tokens:
        return [string]
    parts = []
    for start in range(0, len(tokens), max_tokens):
        parts.append(encoder.decode(tokens[start:start + max_tokens]))
    return parts


def embedding_token_budget(max_length: int, margin: int = 10) -> int:
    """计算单段 embedding 输入允许的最大 token 数。"""
    return max(1, int(max_length) - margin)


def split_text_preserving_tables(string: str, max_tokens: int) -> list[str]:
    """按 token 预算切分文本，HTML 表格块保持完整。"""
    if not string:
        return [""]
    if max_tokens <= 0:
        return [string]
    if num_tokens_from_string(string) <= max_tokens:
        return [string]
    parts = []
    pattern = re.compile(r"(<table[\s\S]*?</table>)", re.IGNORECASE)
    pos = 0
    buffer = ""
    for match in pattern.finditer(string):
        before = string[pos:match.start()]
        if before:
            buffer += before
            buffer = _flush_text_buffer(buffer, max_tokens, parts)
        table_block = match.group(1)
        if num_tokens_from_string(table_block) > max_tokens:
            if buffer.strip():
                parts.extend(split_text_by_token_budget(buffer, max_tokens))
                buffer = ""
            parts.append(table_block)
        else:
            trial = (buffer + table_block) if buffer else table_block
            if num_tokens_from_string(trial) <= max_tokens:
                buffer = trial
            else:
                if buffer.strip():
                    parts.extend(split_text_by_token_budget(buffer, max_tokens))
                buffer = table_block
        pos = match.end()
    tail = string[pos:]
    if tail:
        buffer += tail
    if buffer:
        parts.extend(split_text_by_token_budget(buffer, max_tokens))
    return [p for p in parts if p]


def _flush_text_buffer(buffer: str, max_tokens: int, parts: list[str]) -> str:
    """将缓冲区按 token 预算写入 parts 并清空。"""
    if not buffer:
        return ""
    if num_tokens_from_string(buffer) <= max_tokens:
        parts.append(buffer)
        return ""
    parts.extend(split_text_by_token_budget(buffer, max_tokens))
    return ""


def encode_texts_respecting_length(mdl, texts: list[str], margin: int = 10):
    """逐条 embedding：未超长整段编码，超长则分段（表格完整）后取均值。"""
    budget = embedding_token_budget(getattr(mdl, "max_length", 8192), margin)
    vectors = []
    token_count = 0
    for text in texts:
        if is_html_table_text(text):
            segments = [text]
        else:
            segments = split_text_preserving_tables(text, budget)
        seg_vecs, c = mdl.encode(segments)
        token_count += c
        if len(seg_vecs) == 1:
            vectors.append(seg_vecs[0])
        else:
            vectors.append(np.mean(seg_vecs, axis=0))
    return np.array(vectors), token_count


def is_html_table_text(text: str) -> bool:
    """判断文本是否为 HTML 表格块。"""
    if not text:
        return False
    s = str(text).strip().lower()
    return s.startswith("<table") and "</table>" in s
