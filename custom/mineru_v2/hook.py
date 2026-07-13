"""
MinerU V2 Hook — 注入 mineru_parser 流程。

此 Hook 以最小侵入方式（try/except import）在 MinerU 解析流程中
同时处理 V2 content_list 数据。

使用方式：
    在 mineru_parser.py 的 parse_pdf() 方法中，
    在 _read_output（V1）读取完成后添加 Hook 调用：

    # [自定义] MinerU V2 并行解析
    try:
        from custom.mineru_v2.hook import mineru_v2_hook
        mineru_v2_hook(final_out_dir, pdf.stem, kb_id, doc_id)
    except Exception:
        pass
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def mineru_v2_hook(
    output_dir: Path,
    file_stem: str,
    kb_id: Optional[str] = None,
    doc_id: Optional[str] = None,
) -> bool:
    """
    MinerU V2 并行解析 Hook。

    在 V1 主流程中调用，尝试读取并存储 V2 content_list 数据。
    完全独立于 V1 链路，失败不影响 V1。

    Args:
        output_dir: MinerU 输出目录（包含 content_list_v2.json）
        file_stem: PDF 文件名（不含扩展名）
        kb_id: 知识库 ID
        doc_id: 文档 ID

    Returns:
        是否成功处理 V2 数据
    """
    if not kb_id or not doc_id:
        logger.info("[custom.mineru_v2] 缺少 kb_id/doc_id，跳过 V2 处理")
        return False

    try:
        from custom.mineru_v2.parser import MinerUV2Parser
        from custom.mineru_v2.service import MineruV2Service
    except ImportError as e:
        logger.warning("[custom.mineru_v2] 导入失败，跳过: %s", e)
        return False

    # 1. 读取 V2 文件
    raw_data = MinerUV2Parser.read_v2_file(Path(output_dir), file_stem)
    if raw_data is None:
        logger.info("[custom.mineru_v2] 未找到 content_list_v2.json，跳过")
        return False

    logger.info("[custom.mineru_v2] 找到 V2 数据，开始解析...")

    # 2. 解析为 V2Block 列表
    blocks = MinerUV2Parser.parse_content_list(raw_data)
    if not blocks:
        logger.warning("[custom.mineru_v2] V2 解析结果为空")
        return False

    # 3. 转换为 DB 行格式
    rows = [b.to_db_row(kb_id, doc_id) for b in blocks]

    # 4. 存入 mineru_section_v2 表
    count = MineruV2Service.save_blocks(rows, kb_id, doc_id)
    if count > 0:
        logger.info("[custom.mineru_v2] V2 数据入库成功: %d 条", count)

    return count > 0
