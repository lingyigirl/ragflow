from datetime import datetime
from io import BytesIO
import logging
import os
from pathlib import Path

from PIL import Image

_logger = logging.getLogger(__name__)

_PIC_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tif", ".tiff"}


def _should_save_pdf_snapshot() -> bool:
    return str(os.environ.get("PIC2PDF_SAVE_LOCAL_PDF", "1")).strip() != "1"


def _save_pdf_snapshot_if_needed(pdf_bytes: bytes, utils_dir: Path):
    if not _should_save_pdf_snapshot():
        return
    snapshot_path = utils_dir / f"pic2pdf_output_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.pdf"
    snapshot_path.write_bytes(pdf_bytes)


def convert_image_bytes_to_pdf_bytes(image_bytes: bytes, image_suffix: str = ".jpg") -> bytes:
    normalized_suffix = image_suffix.lower()
    if normalized_suffix not in _PIC_SUFFIXES:
        raise ValueError(f"image_suffix 必须是 {'/'.join(sorted(_PIC_SUFFIXES))}")

    utils_dir = Path(__file__).resolve().parent

    try:
        image = Image.open(BytesIO(image_bytes))
    except Exception:
        _logger.exception("无法打开图片文件，请确认已安装 Pillow: pip install Pillow")
        raise ValueError("无法识别的图片格式，请确认文件未损坏且 Pillow 已安装")

    if image.mode in ("RGBA", "PA", "LA"):
        background = Image.new("RGB", image.size, (255, 255, 255))
        if image.mode == "RGBA":
            background.paste(image, mask=image.split()[3])
        elif image.mode == "LA":
            background.paste(image, mask=image.split()[1])
        else:
            background.paste(image)
        image = background
    elif image.mode == "P":
        image = image.convert("RGBA")
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[3])
        image = background
    elif image.mode not in ("RGB", "L", "CMYK", "YCbCr", "LAB", "HSV"):
        image = image.convert("RGB")

    pdf_buffer = BytesIO()
    image.save(pdf_buffer, format="PDF")
    pdf_bytes = pdf_buffer.getvalue()

    _save_pdf_snapshot_if_needed(pdf_bytes, utils_dir)
    return pdf_bytes


def convert_image_to_pdf(
    input_image: str,
    output_pdf: str | None = None,
) -> str:
    input_path = Path(input_image).expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {input_path}")
    if input_path.suffix.lower() not in _PIC_SUFFIXES:
        raise ValueError(f"输入文件必须是 {'/'.join(sorted(_PIC_SUFFIXES))}")
    if output_pdf is None:
        output_path = input_path.with_suffix(".pdf")
    else:
        output_path = Path(output_pdf).expanduser().resolve()
    if output_path.suffix.lower() != ".pdf":
        raise ValueError("输出文件必须是 .pdf")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image_bytes = input_path.read_bytes()
    pdf_bytes = convert_image_bytes_to_pdf_bytes(
        image_bytes=image_bytes,
        image_suffix=input_path.suffix,
    )
    output_path.write_bytes(pdf_bytes)
    return str(output_path)


if __name__ == "__main__":
    current_dir = Path(__file__).resolve().parent
    test_image = current_dir / "测试.jpg"
    test_pdf = current_dir / "test.pdf"
    result_pdf = convert_image_to_pdf(
        input_image=str(test_image),
        output_pdf=str(test_pdf),
    )
    print(f"转换完成: {result_pdf}")
