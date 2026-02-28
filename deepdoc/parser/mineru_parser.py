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
import base64
import json
import logging
import os
import re
import sys
import tempfile
import threading
import zipfile
from dataclasses import dataclass
from io import BytesIO
from os import PathLike
from pathlib import Path
from typing import Any, Callable, Optional

import numpy as np
import pdfplumber
import requests
from PIL import Image
from strenum import StrEnum

from deepdoc.parser.pdf_parser import RAGFlowPdfParser
from common import settings

# 图片下载链接统一使用无鉴权接口，写入 JSON 时只使用该前缀，避免出现 /v1/document/download/
DOCUMENT_PUBLIC_DOWNLOAD_PREFIX = "/v1/document/public_download"

LOCK_KEY_pdfplumber = "global_shared_lock_pdfplumber"
if LOCK_KEY_pdfplumber not in sys.modules:
    sys.modules[LOCK_KEY_pdfplumber] = threading.Lock()


class MinerUContentType(StrEnum):
    IMAGE = "image"
    TABLE = "table"
    TEXT = "text"
    EQUATION = "equation"
    CODE = "code"
    LIST = "list"
    DISCARDED = "discarded"


# Mapping from language names to MinerU language codes
LANGUAGE_TO_MINERU_MAP = {
    'English': 'en',
    'Chinese': 'ch',
    'Traditional Chinese': 'chinese_cht',
    'Russian': 'east_slavic',
    'Ukrainian': 'east_slavic',
    'Indonesian': 'latin',
    'Spanish': 'latin',
    'Vietnamese': 'latin',
    'Japanese': 'japan',
    'Korean': 'korean',
    'Portuguese BR': 'latin',
    'German': 'latin',
    'French': 'latin',
    'Italian': 'latin',
    'Tamil': 'ta',
    'Telugu': 'te',
    'Kannada': 'ka',
    'Thai': 'th',
    'Greek': 'el',
    'Hindi': 'devanagari',
}


class MinerUBackend(StrEnum):
    """MinerU processing backend options."""

    PIPELINE = "pipeline"  # Traditional multimodel pipeline (default)
    VLM_TRANSFORMERS = "vlm-transformers"  # Vision-language model using HuggingFace Transformers
    VLM_MLX_ENGINE = "vlm-mlx-engine"  # Faster, requires Apple Silicon and macOS 13.5+
    VLM_VLLM_ENGINE = "vlm-vllm-engine"  # Local vLLM engine, requires local GPU
    VLM_VLLM_ASYNC_ENGINE = "vlm-vllm-async-engine"  # Asynchronous vLLM engine, new in MinerU API
    VLM_LMDEPLOY_ENGINE = "vlm-lmdeploy-engine"  # LMDeploy engine
    VLM_HTTP_CLIENT = "vlm-http-client"  # HTTP client for remote vLLM server (CPU only)


class MinerULanguage(StrEnum):
    """MinerU supported languages for OCR (pipeline backend only)."""

    CH = "ch"  # Chinese
    CH_SERVER = "ch_server"  # Chinese (server)
    CH_LITE = "ch_lite"  # Chinese (lite)
    EN = "en"  # English
    KOREAN = "korean"  # Korean
    JAPAN = "japan"  # Japanese
    CHINESE_CHT = "chinese_cht"  # Chinese Traditional
    TA = "ta"  # Tamil
    TE = "te"  # Telugu
    KA = "ka"  # Kannada
    TH = "th"  # Thai
    EL = "el"  # Greek
    LATIN = "latin"  # Latin
    ARABIC = "arabic"  # Arabic
    EAST_SLAVIC = "east_slavic"  # East Slavic
    CYRILLIC = "cyrillic"  # Cyrillic
    DEVANAGARI = "devanagari"  # Devanagari


class MinerUParseMethod(StrEnum):
    """MinerU PDF parsing methods (pipeline backend only)."""

    AUTO = "auto"  # Automatically determine the method based on the file type
    TXT = "txt"  # Use text extraction method
    OCR = "ocr"  # Use OCR method for image-based PDFs


@dataclass
class MinerUParseOptions:
    """Options for MinerU PDF parsing."""

    backend: MinerUBackend = MinerUBackend.PIPELINE
    lang: Optional[MinerULanguage] = None  # language for OCR (pipeline backend only)
    method: MinerUParseMethod = MinerUParseMethod.AUTO
    server_url: Optional[str] = None
    delete_output: bool = True
    parse_method: str = "raw"
    formula_enable: bool = True
    table_enable: bool = True


class MinerUParser(RAGFlowPdfParser):
    def __init__(self, mineru_path: str = "mineru", mineru_api: str = "", mineru_server_url: str = ""):
        self.mineru_api = mineru_api.rstrip("/")
        self.mineru_server_url = mineru_server_url.rstrip("/")
        self.outlines = []
        self.logger = logging.getLogger(self.__class__.__name__)

    def _extract_zip_no_root(self, zip_path, extract_to, root_dir):
        self.logger.info(f"[MinerU] Extract zip: zip_path={zip_path}, extract_to={extract_to}, root_hint={root_dir}")
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            if not root_dir:
                files = zip_ref.namelist()
                if files and files[0].endswith("/"):
                    root_dir = files[0]
                else:
                    root_dir = None

            if not root_dir or not root_dir.endswith("/"):
                self.logger.info(f"[MinerU] No root directory found, extracting all (root_hint={root_dir})")
                zip_ref.extractall(extract_to)
                return

            root_len = len(root_dir)
            for member in zip_ref.infolist():
                filename = member.filename
                if filename == root_dir:
                    self.logger.info("[MinerU] Ignore root folder...")
                    continue

                path = filename
                if path.startswith(root_dir):
                    path = path[root_len:]

                full_path = os.path.join(extract_to, path)
                if member.is_dir():
                    os.makedirs(full_path, exist_ok=True)
                else:
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    with open(full_path, "wb") as f:
                        f.write(zip_ref.read(filename))

    @staticmethod
    def _is_http_endpoint_valid(url, timeout=5):
        try:
            response = requests.head(url, timeout=timeout, allow_redirects=True)
            return response.status_code in [200, 301, 302, 307, 308]
        except Exception:
            return False

    def check_installation(self, backend: str = "pipeline", server_url: Optional[str] = None) -> tuple[bool, str]:
        reason = ""

        valid_backends = ["pipeline", "vlm-http-client", "vlm-transformers", "vlm-vllm-engine", "vlm-mlx-engine", "vlm-vllm-async-engine", "vlm-lmdeploy-engine"]
        if backend not in valid_backends:
            reason = f"[MinerU] Invalid backend '{backend}'. Valid backends are: {valid_backends}"
            self.logger.warning(reason)
            return False, reason

        if not self.mineru_api:
            reason = "[MinerU] MINERU_APISERVER not configured."
            self.logger.warning(reason)
            return False, reason

        api_openapi = f"{self.mineru_api}/openapi.json"
        try:
            api_ok = self._is_http_endpoint_valid(api_openapi)
            self.logger.info(f"[MinerU] API openapi.json reachable={api_ok} url={api_openapi}")
            if not api_ok:
                reason = f"[MinerU] MinerU API not accessible: {api_openapi}"
                return False, reason
        except Exception as exc:
            reason = f"[MinerU] MinerU API check failed: {exc}"
            self.logger.warning(reason)
            return False, reason

        if backend == "vlm-http-client":
            resolved_server = server_url or self.mineru_server_url
            if not resolved_server:
                reason = "[MinerU] MINERU_SERVER_URL required for vlm-http-client backend."
                self.logger.warning(reason)
                return False, reason
            try:
                server_ok = self._is_http_endpoint_valid(resolved_server)
                self.logger.info(f"[MinerU] vlm-http-client server check reachable={server_ok} url={resolved_server}")
            except Exception as exc:
                self.logger.warning(f"[MinerU] vlm-http-client server probe failed: {resolved_server}: {exc}")

        return True, reason

    def _run_mineru(
        self, input_path: Path, output_dir: Path, options: MinerUParseOptions, callback: Optional[Callable] = None
    ) -> Path:
        return self._run_mineru_api(input_path, output_dir, options, callback)

    def _run_mineru_api(
        self, input_path: Path, output_dir: Path, options: MinerUParseOptions, callback: Optional[Callable] = None
    ) -> Path:
        pdf_file_path = str(input_path)

        if not os.path.exists(pdf_file_path):
            raise RuntimeError(f"[MinerU] PDF file not exists: {pdf_file_path}")

        pdf_file_name = Path(pdf_file_path).stem.strip()
        output_path = tempfile.mkdtemp(prefix=f"{pdf_file_name}_{options.method}_", dir=str(output_dir))
        output_zip_path = os.path.join(str(output_dir), f"{Path(output_path).name}.zip")

        files = {"files": (pdf_file_name + ".pdf", open(pdf_file_path, "rb"), "application/pdf")}

        data = {
            "output_dir": "./output",
            "lang_list": options.lang,
            "backend": options.backend,
            "parse_method": options.method,
            "formula_enable": options.formula_enable,
            "table_enable": options.table_enable,
            "server_url": None,
            "return_md": True,
            "return_middle_json": True,
            "return_model_output": True,
            "return_content_list": True,
            "return_images": True,
            "response_format_zip": True,
            "start_page_id": 0,
            "end_page_id": 99999,
        }

        if options.server_url:
            data["server_url"] = options.server_url
        elif self.mineru_server_url:
            data["server_url"] = self.mineru_server_url

        self.logger.info(f"[MinerU] request {data=}")
        self.logger.info(f"[MinerU] request {options=}")

        headers = {"Accept": "application/json"}
        try:
            self.logger.info(f"[MinerU] invoke api: {self.mineru_api}/file_parse backend={options.backend} server_url={data.get('server_url')}")
            if callback:
                callback(0.20, f"[MinerU] invoke api: {self.mineru_api}/file_parse")
            response = requests.post(url=f"{self.mineru_api}/file_parse", files=files, data=data, headers=headers,
                                     timeout=1800)

            response.raise_for_status()
            if response.headers.get("Content-Type") == "application/zip":
                self.logger.info(f"[MinerU] zip file returned, saving to {output_zip_path}...")

                if callback:
                    callback(0.30, f"[MinerU] zip file returned, saving to {output_zip_path}...")

                with open(output_zip_path, "wb") as f:
                    f.write(response.content)

                self.logger.info(f"[MinerU] Unzip to {output_path}...")
                self._extract_zip_no_root(output_zip_path, output_path, pdf_file_name + "/")

                if callback:
                    callback(0.40, f"[MinerU] Unzip to {output_path}...")
            else:
                self.logger.warning(f"[MinerU] not zip returned from api: {response.headers.get('Content-Type')}")
        except Exception as e:
            raise RuntimeError(f"[MinerU] api failed with exception {e}")
        self.logger.info("[MinerU] Api completed successfully.")
        return Path(output_path)

    def __images__(self, fnm, zoomin: int = 1, page_from=0, page_to=600, callback=None):
        self.page_from = page_from
        self.page_to = page_to
        try:
            with pdfplumber.open(fnm) if isinstance(fnm, (str, PathLike)) else pdfplumber.open(BytesIO(fnm)) as pdf:
                self.pdf = pdf
                self.page_images = [p.to_image(resolution=72 * zoomin, antialias=True).original for _, p in
                                    enumerate(self.pdf.pages[page_from:page_to])]
        except Exception as e:
            self.page_images = None
            self.total_page = 0
            self.logger.exception(e)

    def _line_tag(self, bx):
        pn = [bx["page_idx"] + 1]
        positions = bx.get("bbox", (0, 0, 0, 0))
        x0, top, x1, bott = positions

        if hasattr(self, "page_images") and self.page_images and len(self.page_images) > bx["page_idx"]:
            page_width, page_height = self.page_images[bx["page_idx"]].size
            x0 = (x0 / 1000.0) * page_width
            x1 = (x1 / 1000.0) * page_width
            top = (top / 1000.0) * page_height
            bott = (bott / 1000.0) * page_height

        return "@@{}\t{:.1f}\t{:.1f}\t{:.1f}\t{:.1f}##".format("-".join([str(p) for p in pn]), x0, x1, top, bott)

    def crop(self, text, ZM=1, need_position=False):
        imgs = []
        poss = self.extract_positions(text)
        if not poss:
            if need_position:
                return None, None
            return

        if not getattr(self, "page_images", None):
            self.logger.warning("[MinerU] crop called without page images; skipping image generation.")
            if need_position:
                return None, None
            return

        page_count = len(self.page_images)

        filtered_poss = []
        for pns, left, right, top, bottom in poss:
            if not pns:
                self.logger.warning("[MinerU] Empty page index list in crop; skipping this position.")
                continue
            valid_pns = [p for p in pns if 0 <= p < page_count]
            if not valid_pns:
                self.logger.warning(f"[MinerU] All page indices {pns} out of range for {page_count} pages; skipping.")
                continue
            filtered_poss.append((valid_pns, left, right, top, bottom))

        poss = filtered_poss
        if not poss:
            self.logger.warning("[MinerU] No valid positions after filtering; skip cropping.")
            if need_position:
                return None, None
            return

        max_width = max(np.max([right - left for (_, left, right, _, _) in poss]), 6)
        GAP = 6
        pos = poss[0]
        first_page_idx = pos[0][0]
        poss.insert(0, ([first_page_idx], pos[1], pos[2], max(0, pos[3] - 120), max(pos[3] - GAP, 0)))
        pos = poss[-1]
        last_page_idx = pos[0][-1]
        if not (0 <= last_page_idx < page_count):
            self.logger.warning(
                f"[MinerU] Last page index {last_page_idx} out of range for {page_count} pages; skipping crop.")
            if need_position:
                return None, None
            return
        last_page_height = self.page_images[last_page_idx].size[1]
        poss.append(
            (
                [last_page_idx],
                pos[1],
                pos[2],
                min(last_page_height, pos[4] + GAP),
                min(last_page_height, pos[4] + 120),
            )
        )

        positions = []
        for ii, (pns, left, right, top, bottom) in enumerate(poss):
            right = left + max_width

            if bottom <= top:
                bottom = top + 2

            for pn in pns[1:]:
                if 0 <= pn - 1 < page_count:
                    bottom += self.page_images[pn - 1].size[1]
                else:
                    self.logger.warning(
                        f"[MinerU] Page index {pn}-1 out of range for {page_count} pages during crop; skipping height accumulation.")

            if not (0 <= pns[0] < page_count):
                self.logger.warning(
                    f"[MinerU] Base page index {pns[0]} out of range for {page_count} pages during crop; skipping this segment.")
                continue

            img0 = self.page_images[pns[0]]
            x0, y0, x1, y1 = int(left), int(top), int(right), int(min(bottom, img0.size[1]))
            crop0 = img0.crop((x0, y0, x1, y1))
            imgs.append(crop0)
            if 0 < ii < len(poss) - 1:
                positions.append((pns[0] + self.page_from, x0, x1, y0, y1))

            bottom -= img0.size[1]
            for pn in pns[1:]:
                if not (0 <= pn < page_count):
                    self.logger.warning(
                        f"[MinerU] Page index {pn} out of range for {page_count} pages during crop; skipping this page.")
                    continue
                page = self.page_images[pn]
                x0, y0, x1, y1 = int(left), 0, int(right), int(min(bottom, page.size[1]))
                cimgp = page.crop((x0, y0, x1, y1))
                imgs.append(cimgp)
                if 0 < ii < len(poss) - 1:
                    positions.append((pn + self.page_from, x0, x1, y0, y1))
                bottom -= page.size[1]

        if not imgs:
            if need_position:
                return None, None
            return

        height = 0
        for img in imgs:
            height += img.size[1] + GAP
        height = int(height)
        width = int(np.max([i.size[0] for i in imgs]))
        pic = Image.new("RGB", (width, height), (245, 245, 245))
        height = 0
        for ii, img in enumerate(imgs):
            if ii == 0 or ii + 1 == len(imgs):
                img = img.convert("RGBA")
                overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
                overlay.putalpha(128)
                img = Image.alpha_composite(img, overlay).convert("RGB")
            pic.paste(img, (0, int(height)))
            height += img.size[1] + GAP

        if need_position:
            return pic, positions
        return pic

    @staticmethod
    def extract_positions(txt: str):
        poss = []
        for tag in re.findall(r"@@[0-9-]+\t[0-9.\t]+##", txt):
            pn, left, right, top, bottom = tag.strip("#").strip("@").split("\t")
            left, right, top, bottom = float(left), float(right), float(top), float(bottom)
            poss.append(([int(p) - 1 for p in pn.split("-")], left, right, top, bottom))
        return poss

    def _read_output(self, output_dir: Path, file_stem: str, method: str = "auto", backend: str = "pipeline") -> list[
        dict[str, Any]]:
        json_file = None
        subdir = None
        attempted = []

        # mirror MinerU's sanitize_filename to align ZIP naming
        def _sanitize_filename(name: str) -> str:
            sanitized = re.sub(r"[/\\\.]{2,}|[/\\]", "", name)
            sanitized = re.sub(r"[^\w.-]", "_", sanitized, flags=re.UNICODE)
            if sanitized.startswith("."):
                sanitized = "_" + sanitized[1:]
            return sanitized or "unnamed"

        safe_stem = _sanitize_filename(file_stem)
        allowed_names = {f"{file_stem}_content_list.json", f"{safe_stem}_content_list.json"}
        self.logger.info(f"[MinerU] Expected output files: {', '.join(sorted(allowed_names))}")
        self.logger.info(f"[MinerU] Searching output in: {output_dir}")

        jf = output_dir / f"{file_stem}_content_list.json"
        self.logger.info(f"[MinerU] Trying original path: {jf}")
        attempted.append(jf)
        if jf.exists():
            subdir = output_dir
            json_file = jf
        else:
            alt = output_dir / f"{safe_stem}_content_list.json"
            self.logger.info(f"[MinerU] Trying sanitized filename: {alt}")
            attempted.append(alt)
            if alt.exists():
                subdir = output_dir
                json_file = alt
            else:
                nested_alt = output_dir / safe_stem / f"{safe_stem}_content_list.json"
                self.logger.info(f"[MinerU] Trying sanitized nested path: {nested_alt}")
                attempted.append(nested_alt)
                if nested_alt.exists():
                    subdir = nested_alt.parent
                    json_file = nested_alt

        if not json_file:
            raise FileNotFoundError(f"[MinerU] Missing output file, tried: {', '.join(str(p) for p in attempted)}")

        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data:
            for key in ("img_path", "table_img_path", "equation_img_path"):
                if key in item and item[key]:
                    item[key] = str((subdir / item[key]).resolve())
        return data

    def _transfer_to_sections(self, outputs: list[dict[str, Any]], parse_method: str = None):
        sections = []
        for output in outputs:
            match output["type"]:
                case MinerUContentType.TEXT:
                    section = output.get("text", "")
                case MinerUContentType.TABLE:
                    section = output.get("table_body", "") + "\n".join(output.get("table_caption", [])) + "\n".join(
                        output.get("table_footnote", []))
                    if not section.strip():
                        section = "FAILED TO PARSE TABLE"
                case MinerUContentType.IMAGE:
                    section = "".join(output.get("image_caption", [])) + "\n" + "".join(
                        output.get("image_footnote", []))
                case MinerUContentType.EQUATION:
                    section = output.get("text", "")
                case MinerUContentType.CODE:
                    section = output.get("code_body", "") + "\n".join(output.get("code_caption", []))
                case MinerUContentType.LIST:
                    section = "\n".join(output.get("list_items", []))
                case MinerUContentType.DISCARDED:
                    continue  # Skip discarded blocks entirely

            if section and parse_method == "manual":
                sections.append((section, output["type"], self._line_tag(output)))
            elif section and parse_method == "paper":
                sections.append((section + self._line_tag(output), output["type"]))
            else:
                sections.append((section, self._line_tag(output)))
        return sections

    def _transfer_to_tables(self, outputs: list[dict[str, Any]]):
        return []

    def _convert_content_list_to_markdown(self, content_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
        new_content_list: list[dict[str, Any]] = []
        for item in content_list:
            new_item = dict(item)
            item_type = new_item.get("type")
            if item_type == MinerUContentType.TEXT or item_type == MinerUContentType.TEXT.value:
                text = new_item.get("text")
                if isinstance(text, str) and text.strip():
                    text_level = new_item.get("text_level")
                    level_int = 0
                    if isinstance(text_level, int):
                        level_int = text_level
                    elif isinstance(text_level, str):
                        try:
                            level_int = int(text_level)
                        except ValueError:
                            level_int = 0
                    if level_int > 0:
                        level_int = max(1, min(6, level_int))
                        if not text.lstrip().startswith("#"):
                            new_item["text"] = f"{'#' * level_int} {text}"
            new_content_list.append(new_item)
        return new_content_list

    def _upload_mineru_outputs_to_minio(
        self,
        output_dir: Path,
        kb_id: str,
        doc_id: str,
        content_list: list[dict[str, Any]],
        callback: Optional[Callable] = None,
    ) -> bool:
        try:
            if not output_dir or not output_dir.exists():
                self.logger.error(f"[MinerU] 上传MinIO失败: output_dir 不存在或无效: {output_dir}")
                if callback:
                    callback(-1, f"[MinerU] 解析输出目录无效: {output_dir}")
                return False
            if not output_dir.is_dir():
                self.logger.error(f"[MinerU] 上传MinIO失败: output_dir 不是目录: {output_dir}")
                if callback:
                    callback(-1, f"[MinerU] 解析输出路径不是目录: {output_dir}")
                return False

            base_prefix = f"{doc_id}"
            self.logger.info(f"[MinerU] 开始上传解析产物到MinIO: bucket={kb_id}, prefix={base_prefix}")

            _IMG_KEYS_NORM = ("img_path", "table_img_path", "equation_img_path")

            def _normalize_download_to_public(obj: Any) -> None:
                if isinstance(obj, dict):
                    for k in list(obj.keys()):
                        if k in _IMG_KEYS_NORM and obj[k] and isinstance(obj[k], str) and "/v1/document/download/" in obj[k]:
                            obj[k] = obj[k].replace("/v1/document/download/", f"{DOCUMENT_PUBLIC_DOWNLOAD_PREFIX}/", 1)
                        else:
                            _normalize_download_to_public(obj[k])
                elif isinstance(obj, list):
                    for v in obj:
                        _normalize_download_to_public(v)

            for item in content_list:
                _normalize_download_to_public(item)

            if callback:
                callback(0.76, f"[MinerU] 开始上传解析产物到MinIO...")

            image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
            processed_image_paths: set[str] = set()
            image_files_to_upload: list[dict] = []
            img_path_to_minio_url: dict[str, str] = {}
            _IMG_KEYS = ("img_path", "table_img_path", "equation_img_path")

            def _collect_img_paths(obj: Any):
                if isinstance(obj, dict):
                    for k in list(obj.keys()):
                        if k in _IMG_KEYS and obj[k] and isinstance(obj[k], str):
                            yield obj[k]
                        else:
                            yield from _collect_img_paths(obj[k])
                elif isinstance(obj, list):
                    for v in obj:
                        yield from _collect_img_paths(v)

            for item in content_list:
                for img_path_str in _collect_img_paths(item):
                    raw_str = str(img_path_str).strip()
                    if not raw_str:
                        continue
                    img_path = (output_dir / raw_str) if not os.path.isabs(raw_str) else Path(raw_str)
                    if not img_path.exists():
                        img_filename = Path(raw_str).name
                        found_img = None
                        for possible_img in output_dir.rglob(img_filename):
                            found_img = possible_img
                            break
                        if found_img:
                            img_path = found_img
                    if img_path.exists() and img_path.is_file() and img_path.suffix.lower() in image_extensions:
                        try:
                            img_relative_path = str(img_path.relative_to(output_dir))
                            if img_relative_path not in processed_image_paths:
                                processed_image_paths.add(img_relative_path)
                                image_files_to_upload.append({"path": img_path, "relative_path": img_relative_path})
                            filename = img_path.name
                            minio_key = f"{base_prefix}/images/{filename}"
                            ext = img_path.suffix.lstrip(".") or "jpg"
                            key_b64 = base64.urlsafe_b64encode(minio_key.encode("utf-8")).decode("utf-8").rstrip("=")
                            download_url = f"{DOCUMENT_PUBLIC_DOWNLOAD_PREFIX}/{key_b64}?ext={ext}&bucket={kb_id}"
                            img_path_to_minio_url[raw_str] = download_url
                            img_path_to_minio_url[raw_str.replace("\\", "/")] = download_url
                            img_path_to_minio_url[img_relative_path] = download_url
                            img_path_to_minio_url[filename] = download_url
                        except ValueError:
                            self.logger.warning(f"[MinerU] 图片路径不在输出目录内，跳过: {img_path}")

            for img_file in output_dir.rglob("*"):
                if img_file.is_file() and img_file.suffix.lower() in image_extensions:
                    img_relative_path = str(img_file.relative_to(output_dir))
                    if img_relative_path not in processed_image_paths:
                        processed_image_paths.add(img_relative_path)
                        image_files_to_upload.append({"path": img_file, "relative_path": img_relative_path})
                        filename = img_file.name
                        minio_key = f"{base_prefix}/images/{filename}"
                        ext = img_file.suffix.lstrip(".") or "jpg"
                        key_b64 = base64.urlsafe_b64encode(minio_key.encode("utf-8")).decode("utf-8").rstrip("=")
                        download_url = f"{DOCUMENT_PUBLIC_DOWNLOAD_PREFIX}/{key_b64}?ext={ext}&bucket={kb_id}"
                        img_path_to_minio_url[img_relative_path] = download_url
                        img_path_to_minio_url[filename] = download_url

            IMG_KEYS = ("img_path", "table_img_path", "equation_img_path")
            _IMG_KEY_SET = {k.lower() for k in IMG_KEYS}

            def _is_local_img_path(s: str) -> bool:
                s = (s or "").strip()
                if not s or s.startswith("/v1/document/"):
                    return False
                return "/" in s or "\\" in s or s.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"))

            def _replace_img_paths_in_obj(obj: Any, path: str = "") -> None:
                if isinstance(obj, dict):
                    for k in list(obj.keys()):
                        if (k in IMG_KEYS or k.lower() in _IMG_KEY_SET) and obj[k] and isinstance(obj[k], str):
                            raw = str(obj[k]).strip()
                            cands = [raw, raw.replace("\\", "/"), Path(raw).name]
                            try:
                                cands.append(str(Path(raw).resolve()))
                                cands.append(str(Path(raw).relative_to(output_dir)))
                            except (ValueError, OSError):
                                pass
                            replaced = False
                            for cand in cands:
                                if cand and cand in img_path_to_minio_url:
                                    obj[k] = img_path_to_minio_url[cand]
                                    replaced = True
                                    break
                            if not replaced:
                                for part in raw.replace("\\", "/").split("/"):
                                    if part and any(part.lower().endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")):
                                        if part in img_path_to_minio_url:
                                            obj[k] = img_path_to_minio_url[part]
                                            replaced = True
                                        break
                            if not replaced and _is_local_img_path(raw):
                                self.logger.warning(f"[MinerU] ⚠ 未匹配到下载链接: path={path}, key={k}, value={raw}")
                        else:
                            _replace_img_paths_in_obj(obj[k], f"{path}.{k}" if path else k)
                elif isinstance(obj, list):
                    for i, v in enumerate(obj):
                        _replace_img_paths_in_obj(v, f"{path}[{i}]" if path else f"[{i}]")

            for idx, item in enumerate(content_list):
                _replace_img_paths_in_obj(item, f"item[{idx}]")

            def _normalize_to_public_download(obj: Any) -> None:
                if isinstance(obj, dict):
                    for k in list(obj.keys()):
                        if k in IMG_KEYS and obj[k] and isinstance(obj[k], str) and "/v1/document/download/" in obj[k]:
                            obj[k] = obj[k].replace("/v1/document/download/", f"{DOCUMENT_PUBLIC_DOWNLOAD_PREFIX}/", 1)
                        else:
                            _normalize_to_public_download(obj[k])
                elif isinstance(obj, list):
                    for v in obj:
                        _normalize_to_public_download(v)

            for item in content_list:
                _normalize_to_public_download(item)

            json_uploaded = False
            try:
                content_list_location = f"{base_prefix}/content_list.json"
                content_list_json_str = json.dumps(content_list, ensure_ascii=False, indent=2)
                settings.STORAGE_IMPL.put(kb_id, content_list_location, content_list_json_str.encode("utf-8"))
                self.logger.info(f"[MinerU] 已上传content_list.json: bucket={kb_id}, location={content_list_location}")
                json_uploaded = True
                if callback:
                    callback(0.78, f"[MinerU] 已上传content_list.json")
            except Exception as e:
                self.logger.error(f"[MinerU] 上传 content_list.json 失败: {e}", exc_info=True)
                if callback:
                    callback(-1, f"[MinerU] 上传 content_list.json 失败: {e}")
                return False

            markdown_uploaded = False
            try:
                markdown_files = list(output_dir.rglob("*.md"))
                if markdown_files:
                    md_file = markdown_files[0]
                    with open(md_file, "r", encoding="utf-8") as f:
                        markdown_content = f.read()
                    markdown_location = f"{base_prefix}/{md_file.name}"
                    settings.STORAGE_IMPL.put(kb_id, markdown_location, markdown_content.encode("utf-8"))
                    self.logger.info(f"[MinerU] 已上传Markdown文件: bucket={kb_id}, location={markdown_location}")
                    markdown_uploaded = True
                    if callback:
                        callback(0.80, f"[MinerU] 已上传Markdown文件")
                else:
                    self.logger.info(f"[MinerU] 未找到Markdown文件，跳过上传")
            except Exception as e:
                self.logger.warning(f"[MinerU] 上传Markdown文件失败: {e}")

            uploaded_image_count = 0
            for img_info in image_files_to_upload:
                img_path = img_info["path"]
                img_filename = img_path.name
                try:
                    with open(img_path, "rb") as img_file:
                        img_data = img_file.read()
                    img_location = f"{base_prefix}/images/{img_filename}"
                    settings.STORAGE_IMPL.put(kb_id, img_location, img_data)
                    uploaded_image_count += 1
                    self.logger.debug(f"[MinerU] 已上传图片: bucket={kb_id}, location={img_location}")
                except Exception as e:
                    self.logger.warning(f"[MinerU] 上传图片失败 {img_filename}: {e}")

            if uploaded_image_count > 0:
                self.logger.info(f"[MinerU] 已上传 {uploaded_image_count} 张图片到MinIO (bucket: {kb_id}, prefix: {base_prefix})")
                if callback:
                    callback(0.85, f"[MinerU] 已上传 {uploaded_image_count} 张图片")
            else:
                self.logger.info(f"[MinerU] 未找到图片文件，跳过上传")

            self.logger.info(
                f"[MinerU] 解析产物上传完成: bucket={kb_id}, prefix={base_prefix}, "
                f"json={'已上传' if json_uploaded else '失败'}, markdown={'已上传' if markdown_uploaded else '未找到'}, 图片={uploaded_image_count}张"
            )
            if callback:
                callback(0.90, f"[MinerU] 解析产物上传完成")
            return True

        except Exception as e:
            self.logger.error(f"[MinerU] 上传解析产物到MinIO失败: {e}", exc_info=True)
            if callback:
                callback(-1, f"[MinerU] 上传解析产物到MinIO失败: {e}")
            return False

    def parse_pdf(
            self,
            filepath: str | PathLike[str],
            binary: BytesIO | bytes,
            callback: Optional[Callable] = None,
            *,
            output_dir: Optional[str] = None,
            backend: str = "pipeline",
            server_url: Optional[str] = None,
            delete_output: bool = True,
            parse_method: str = "raw",
            **kwargs,
    ) -> tuple:
        import shutil

        temp_pdf = None
        created_tmp_dir = False

        parser_cfg = kwargs.get('parser_config', {})
        lang = parser_cfg.get('mineru_lang') or kwargs.get('lang', 'English')
        mineru_lang_code = LANGUAGE_TO_MINERU_MAP.get(lang, 'ch')  # Defaults to Chinese if not matched
        mineru_method_raw_str = parser_cfg.get('mineru_parse_method', 'auto')
        enable_formula = parser_cfg.get('mineru_formula_enable', True)
        enable_table = parser_cfg.get('mineru_table_enable', True)

        # remove spaces, or mineru crash, and _read_output fail too
        file_path = Path(filepath)
        pdf_file_name = file_path.stem.replace(" ", "") + ".pdf"
        pdf_file_path_valid = os.path.join(file_path.parent, pdf_file_name)

        if binary:
            temp_dir = Path(tempfile.mkdtemp(prefix="mineru_bin_pdf_"))
            temp_pdf = temp_dir / pdf_file_name
            with open(temp_pdf, "wb") as f:
                f.write(binary)
            pdf = temp_pdf
            self.logger.info(f"[MinerU] Received binary PDF -> {temp_pdf}")
            if callback:
                callback(0.15, f"[MinerU] Received binary PDF -> {temp_pdf}")
        else:
            if pdf_file_path_valid != filepath:
                self.logger.info(f"[MinerU] Remove all space in file name: {pdf_file_path_valid}")
                shutil.move(filepath, pdf_file_path_valid)
            pdf = Path(pdf_file_path_valid)
            if not pdf.exists():
                if callback:
                    callback(-1, f"[MinerU] PDF not found: {pdf}")
                raise FileNotFoundError(f"[MinerU] PDF not found: {pdf}")

        if output_dir:
            out_dir = Path(output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
        else:
            out_dir = Path(tempfile.mkdtemp(prefix="mineru_pdf_"))
            created_tmp_dir = True

        self.logger.info(f"[MinerU] Output directory: {out_dir} backend={backend} api={self.mineru_api} server_url={server_url or self.mineru_server_url}")
        if callback:
            callback(0.15, f"[MinerU] Output directory: {out_dir}")

        self.__images__(pdf, zoomin=1)

        try:
            options = MinerUParseOptions(
                backend=MinerUBackend(backend),
                lang=MinerULanguage(mineru_lang_code),
                method=MinerUParseMethod(mineru_method_raw_str),
                server_url=server_url,
                delete_output=delete_output,
                parse_method=parse_method,
                formula_enable=enable_formula,
                table_enable=enable_table,
            )
            final_out_dir = self._run_mineru(pdf, out_dir, options, callback=callback)
            outputs = self._read_output(final_out_dir, pdf.stem, method=mineru_method_raw_str, backend=backend)
            self.logger.info(f"[MinerU] Parsed {len(outputs)} blocks from PDF.")
            if callback:
                callback(0.75, f"[MinerU] Parsed {len(outputs)} blocks from PDF.")

            kb_id = kwargs.get('kb_id')
            doc_id = kwargs.get('doc_id')
            self.logger.info(f"[MinerU] 解析完成，MinIO 上传参数: kb_id={kb_id}, doc_id={doc_id}")

            if not kb_id or not doc_id:
                self.logger.warning(
                    "[MinerU] 未传入 kb_id 或 doc_id，跳过解析产物上传 MinIO（知识库/文档链路应传入二者）；"
                    "若批量解析时经常缺失，请检查任务执行器传入的 task['kb_id']/task['doc_id']"
                )
            else:
                try:
                    content_list_for_minio = self._convert_content_list_to_markdown(outputs)
                    ok = self._upload_mineru_outputs_to_minio(
                        output_dir=final_out_dir,
                        kb_id=kb_id,
                        doc_id=doc_id,
                        content_list=content_list_for_minio,
                        callback=callback,
                    )
                    if not ok:
                        self.logger.warning(
                            "[MinerU] 解析产物上传 MinIO 返回失败（见上文日志），doc_id=%s, kb_id=%s",
                            doc_id, kb_id,
                        )
                except Exception as e:
                    self.logger.warning(
                        "[MinerU] 上传解析产物到MinIO异常: %s (doc_id=%s, kb_id=%s)",
                        e, doc_id, kb_id, exc_info=True,
                    )

            return self._transfer_to_sections(outputs, parse_method), self._transfer_to_tables(outputs)
        finally:
            if temp_pdf and temp_pdf.exists():
                try:
                    temp_pdf.unlink()
                    temp_pdf.parent.rmdir()
                except Exception:
                    pass
            if delete_output and created_tmp_dir and out_dir.exists():
                try:
                    shutil.rmtree(out_dir)
                except Exception:
                    pass


if __name__ == "__main__":
    parser = MinerUParser("mineru")
    ok, reason = parser.check_installation()
    print("MinerU available:", ok)

    filepath = ""
    with open(filepath, "rb") as file:
        outputs = parser.parse_pdf(filepath=filepath, binary=file.read())
        for output in outputs:
            print(output)
