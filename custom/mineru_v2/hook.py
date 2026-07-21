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
    rotate_deg: int = 0,
    orig_pdf_path: Optional[Path] = None,
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
        rotate_deg: PDF /Rotate 角度（0/90/180/270），用于计算 bbox_rotated

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

    # 3. 检测 MinerU 自动摆正和 PDF /Rotate，确定综合旋转角度
    #    bbox 始终是原始 PDF 的归一化坐标（不因 _rotated.pdf 或 /Rotate 变化）。
    #    bbox_rotated = bbox 经旋转矩阵变换后的坐标，供前端高亮使用。
    #    优先级：PDF /Rotate 元数据 > MinerU 自动摆正（_rotated.pdf 尺寸互换检测）
    _final_rotate_deg = rotate_deg
    has_rotated_pdf = any(
        Path(output_dir).rglob("*_rotated.pdf")
    )
    if has_rotated_pdf:
        for b in blocks:
            b.is_rotated = True
        # 如果 /Rotate=0 但有 _rotated.pdf，检测 MinerU 自动摆正角度
        if rotate_deg in (0, 360):
            _final_rotate_deg = MinerUV2Parser.detect_auto_rotation(
                str(output_dir), rotate_deg,
                orig_pdf_path=str(orig_pdf_path) if orig_pdf_path else "",
            )
        logger.info(
            "[custom.mineru_v2] 检测到 _rotated.pdf，is_rotated=True final_rotate=%s°",
            _final_rotate_deg,
        )

    # 4. 应用旋转变换到 bbox_rotated（bbox 保持不变）
    if _final_rotate_deg not in (0, 360):
        MinerUV2Parser.apply_rotation(blocks, _final_rotate_deg)

    # 5. 转换为 DB 行格式
    rows = [b.to_db_row(kb_id, doc_id) for b in blocks]

    # 6. 存入 mineru_section_v2 表
    count = MineruV2Service.save_blocks(rows, kb_id, doc_id)
    if count > 0:
        logger.info("[custom.mineru_v2] V2 数据入库成功: %d 条", count)

    return count > 0
