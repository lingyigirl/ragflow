import asyncio
import logging
import re

from common.constants import LLMType
from api.db.services.document_service import DocumentService
from api.db.services.llm_service import LLMBundle
from graphrag.utils import chat_limiter


def build_auto_filename_content_from_chunks(chunks, max_chars=12000):
    content_parts = []
    for chunk in chunks or []:
        text = str(chunk.get("content_with_weight", "") or "").strip()
        if not text:
            continue
        content_parts.append(text)
        if sum(len(part) for part in content_parts) >= max_chars:
            break
    merged = "\n\n".join(content_parts)
    return merged[:max_chars]


def build_auto_filename_content_from_content_list(content_list, max_chars=12000):
    text_fields = ("text", "table_body", "content", "title", "table_caption", "table_footnote")
    chunks = []
    for item in content_list or []:
        if not isinstance(item, dict):
            continue
        merged = []
        for key in text_fields:
            value = item.get(key)
            if value is None:
                continue
            if isinstance(value, (list, dict)):
                value = str(value)
            value = str(value).strip()
            if value:
                merged.append(value)
        if merged:
            chunks.append({"content_with_weight": "\n".join(merged)})
    return build_auto_filename_content_from_chunks(chunks, max_chars=max_chars)


def build_auto_filename_content_from_mineru_sections(rows, max_chars=12000):
    chunks = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        merged = []
        for key in ("text", "table_body", "table_caption", "table_footnote"):
            value = row.get(key)
            if value is None:
                continue
            if isinstance(value, (list, dict)):
                value = str(value)
            value = str(value).strip()
            if value:
                merged.append(value)
        if merged:
            chunks.append({"content_with_weight": "\n".join(merged)})
    return build_auto_filename_content_from_chunks(chunks, max_chars=max_chars)


def normalize_filename_from_llm(raw_name: str, max_len: int = 80):
    name = str(raw_name or "").strip()
    name = re.sub(r"^```[a-zA-Z]*\s*|```$", "", name, flags=re.DOTALL).strip()
    name = re.sub(r"[\r\n\t]+", " ", name).strip()
    name = name.strip("\"'`")
    name = re.sub(r"[\\/:*?\"<>|]+", "-", name).strip()
    name = re.sub(r"\s*-\s*", "-", name).strip("- ").strip()
    if "." in name:
        name = re.sub(r"\.[A-Za-z0-9]{1,8}$", "", name).strip() or name
    if not name:
        name = "未知主体-文档材料-未知年份"
    if len(name) > max_len:
        name = name[:max_len].rstrip("- ").strip() or "未知主体-文档材料-未知年份"
    return name


async def generate_standard_filename_by_llm(chat_mdl, content: str, timeout: int = 45):
    system_prompt = (
        "你是文档命名助手。"
        "请根据给定文档内容生成一个标准化中文文件名。"
        "输出格式优先为“主体名称-文档类型-年份”。"
        "只输出文件名字符串，不要解释，不要输出引号，不要输出扩展名。"
    )
    user_prompt = f"请根据以下文档内容生成标准化文件名：\n{content}"
    raw = await asyncio.wait_for(
        chat_mdl.async_chat(
            system_prompt,
            [{"role": "user", "content": user_prompt}],
            {"temperature": 0.01, "max_tokens": 128},
        ),
        timeout=timeout,
    )
    return normalize_filename_from_llm(raw)


async def auto_standard_filename_async(task: dict, chunks: list[dict]):
    doc_id = task.get("doc_id")
    if not doc_id:
        return
    tenant_id = task.get("tenant_id")
    if not tenant_id:
        logging.warning("[auto_standard_filename] 缺少 tenant_id doc_id=%s", doc_id)
        return
    content = build_auto_filename_content_from_chunks(chunks)
    if not content:
        logging.info("[auto_standard_filename] 无可用命名内容 doc_id=%s", doc_id)
        return
    chat_mdl = LLMBundle(tenant_id, LLMType.CHAT, llm_name=None, lang=task.get("language") or "Chinese")
    try:
        logging.info("[auto_standard_filename] 开始 LLM 命名 doc_id=%s", doc_id)
        async with chat_limiter:
            standard_name = await generate_standard_filename_by_llm(chat_mdl, content, timeout=45)
        ok = DocumentService.update_by_id(doc_id, {"llm_name": standard_name})
        if ok:
            logging.info("[auto_standard_filename] 写入成功 doc_id=%s result=%s", doc_id, standard_name)
        else:
            logging.warning("[auto_standard_filename] 数据库更新失败 doc_id=%s", doc_id)
    except Exception as ex:
        logging.warning("[auto_standard_filename] 失败 doc_id=%s err=%s", doc_id, ex)
