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
import copy
import hashlib
import json
import logging
import os
import re
import sys
import tempfile
import threading
import time
import zipfile
from dataclasses import dataclass
from io import BytesIO
from os import PathLike
from pathlib import Path
from typing import Any, Callable, Optional, Union 

import numpy as np
import pdfplumber
import requests
from PIL import Image
from strenum import StrEnum

from deepdoc.parser.pdf_parser import RAGFlowPdfParser
from common import settings

DOCUMENT_PUBLIC_DOWNLOAD_PREFIX = "/v1/document/public_download"
MINERU_SECTION_IMG_PATH_MAX_LEN = 2048

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


# MinerU 将财报勾选框误判为空的 \boxed{\begin{array}...\end{array}} 公式
_MINERU_EMPTY_BOXED_ARRAY_RE = re.compile(
    r"\$?\s*\\boxed\s*\{\s*\\begin\{array\}\{[^}]*\}\s*\\end\{array\}\s*\}\s*\$?",
    re.IGNORECASE,
)
# 无 boxed 包裹的空 array 环境（同类误判）
_MINERU_EMPTY_ARRAY_ONLY_RE = re.compile(
    r"\$?\s*\\begin\{array\}\{[^}]*\}\s*\\end\{array\}\s*\$?",
    re.IGNORECASE,
)


def normalize_mineru_checkbox_latex(text: str) -> str:
    """将 MinerU 误判为公式的勾选框 LaTeX 还原为可读符号。"""
    if not text or not isinstance(text, str):
        return text
    # 无 LaTeX 勾选特征则原样返回
    if "\\boxed" not in text and "\\begin{array}" not in text:
        return text
    # 空 boxed array → 已勾选 ☑
    normalized = _MINERU_EMPTY_BOXED_ARRAY_RE.sub("☑", text)
    # 兜底：单独的空 array 环境
    normalized = _MINERU_EMPTY_ARRAY_ONLY_RE.sub("☑", normalized)
    # 合并多余空白，避免替换后留下双空格
    normalized = re.sub(r"[ \t]{2,}", " ", normalized)
    return normalized


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
    HYBRID_AUTO_ENGINE = "hybrid-auto-engine"  # MinerU hybrid auto engine（混合自动引擎）
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

    backend: Union[MinerUBackend, str] = MinerUBackend.PIPELINE  # 允许外部自定义 backend 字符串透传
    lang: Optional[MinerULanguage] = None  # language for OCR (pipeline backend only)
    method: MinerUParseMethod = MinerUParseMethod.AUTO
    server_url: Optional[str] = None
    delete_output: bool = True
    parse_method: str = "raw"
    formula_enable: bool = True
    table_enable: bool = True


def resolve_mineru_api_from_env(fallback: str = "http://host.docker.internal:9987") -> str:
    base = os.environ.get("MINERU_APISERVER")
    if base:
        return base.rstrip("/")

    scheme = os.environ.get("MINERU_API_SCHEME", "http").strip() or "http"
    host = os.environ.get("MINERU_API_HOST", "host.docker.internal").strip()
    port = os.environ.get("MINERU_API_PORT", "").strip()

    if host:
        if port:
            return f"{scheme}://{host}:{port}"
        return f"{scheme}://{host}"

    return fallback.rstrip("/")
class MinerUParser(RAGFlowPdfParser):
    def __init__(
        self,
        mineru_path: str = "mineru",
        mineru_api: str = "",
        mineru_server_url: Optional[str] = None,
    ):
        self.mineru_api = mineru_api.rstrip("/") if mineru_api else ""
        self.mineru_server_url = (mineru_server_url or "").rstrip("/")
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
        for _method in ("head", "get"):
            try:
                if _method == "head":
                    response = requests.head(url, timeout=timeout, allow_redirects=True)
                else:
                    response = requests.get(url, timeout=timeout, allow_redirects=True)
                if response.status_code in [200, 301, 302, 307, 308]:
                    return True
            except Exception:
                continue
        return False

    def check_installation(self, backend: str = "pipeline", server_url: Optional[str] = None) -> tuple[bool, str]:
        reason = ""

        valid_backends = ["pipeline", "vlm-http-client", "vlm-transformers", "vlm-vllm-engine", "vlm-mlx-engine", "vlm-vllm-async-engine", "vlm-lmdeploy-engine"]  # 保留已知 backend 列表用于提示日志
        if backend not in valid_backends: 
            reason = f"[MinerU] Unknown backend '{backend}', skip local validation and delegate to remote MinerU API. Known backends: {valid_backends}"  # 将校验责任下放给外部 API
            self.logger.warning(reason)

        if not self.mineru_api:
            reason = "[MinerU] MINERU_APISERVER not configured."
            self.logger.warning(reason)
            return False, reason

        api_openapi = f"{self.mineru_api}/openapi.json"
        #
        _probe_attempts = int(os.environ.get("MINERU_API_PROBE_ATTEMPTS", "3"))  
        _probe_interval = float(os.environ.get("MINERU_API_PROBE_INTERVAL_SEC", "2"))  
        api_ok = False  
        reason = ""  
        for _attempt in range(1, _probe_attempts + 1):  
            try:
                api_ok = self._is_http_endpoint_valid(api_openapi)  
                self.logger.info(
                    f"[MinerU] API openapi.json reachable={api_ok} url={api_openapi} attempt={_attempt}/{_probe_attempts}"
                )  
                if api_ok:  
                    break  
                reason = f"[MinerU] MinerU API not accessible: {api_openapi}"  
            except Exception as exc:  
                reason = f"[MinerU] MinerU API check failed: {exc}"  
                self.logger.warning(f"{reason} attempt={_attempt}/{_probe_attempts}")  
            if not api_ok and _attempt < _probe_attempts:  
                time.sleep(_probe_interval)  
        if not api_ok:  
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

    def _emit_callback(self, callback: Optional[Callable], prog: float, msg: str) -> None:
        """安全触发进度回调，避免上游回调异常打断主流程。"""
        if not callback:
            return
        try:
            callback(prog, msg)
        except Exception as _cb_err:
            self.logger.warning(
                "[MinerU] callback failed (ignored): %s, prog=%s, msg=%s",
                _cb_err,
                prog,
                msg,
                exc_info=True,
            )

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
            self._emit_callback(callback, 0.20, f"[MinerU] invoke api: {self.mineru_api}/file_parse")
            response = requests.post(url=f"{self.mineru_api}/file_parse", files=files, data=data, headers=headers,
                                     timeout=1800)

            response.raise_for_status()
            if response.headers.get("Content-Type") == "application/zip":
                self.logger.info(f"[MinerU] zip file returned, saving to {output_zip_path}...")

                self._emit_callback(callback, 0.30, f"[MinerU] zip file returned, saving to {output_zip_path}...")

                with open(output_zip_path, "wb") as f:
                    f.write(response.content)

                self.logger.info(f"[MinerU] Unzip to {output_path}...")
                self._extract_zip_no_root(output_zip_path, output_path, pdf_file_name + "/")

                self._emit_callback(callback, 0.40, f"[MinerU] Unzip to {output_path}...")
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

    @staticmethod
    def _join_mineru_lines(val: Any, sep: str = "\n") -> str:
        """将 table_caption / list_items 等安全拼成字符串（兼容 null、纯 str、JSON 列表）。"""  
        if val is None:  
            return ""  
        if isinstance(val, str):  
            return val  
        if isinstance(val, (list, tuple)):  
            return sep.join(str(x) for x in val)  
        return str(val)  

    def _line_tag(self, bx):
        _pi = bx.get("page_idx", 0)  
        if _pi is None:  
            _pi = 0  
        try:
            _pi = int(_pi)  
        except (TypeError, ValueError):  
            self.logger.warning("[MinerU] _line_tag: 无效 page_idx=%r，改用 0", bx.get("page_idx"))  
            _pi = 0  
        pn = [_pi + 1]  

        raw_bbox = bx.get("bbox")  
        if raw_bbox is None:  
            positions = (0.0, 0.0, 0.0, 0.0)  
        elif isinstance(raw_bbox, (list, tuple)) and len(raw_bbox) >= 4:  
            try:
                positions = tuple(float(x) for x in raw_bbox[:4])  
            except (TypeError, ValueError):  
                self.logger.warning("[MinerU] _line_tag: bbox 非数值 %r", raw_bbox)  
                positions = (0.0, 0.0, 0.0, 0.0)  
        else:  
            self.logger.warning("[MinerU] _line_tag: bbox 形状异常 %r", raw_bbox)  
            positions = (0.0, 0.0, 0.0, 0.0)  
        x0, top, x1, bott = positions  

        if hasattr(self, "page_images") and self.page_images and 0 <= _pi < len(self.page_images):  
            page_width, page_height = self.page_images[_pi].size  
            x0 = (x0 / 1000.0) * page_width  
            x1 = (x1 / 1000.0) * page_width  
            top = (top / 1000.0) * page_height  
            bott = (bott / 1000.0) * page_height  

        return "@@{}\t{:.1f}\t{:.1f}\t{:.1f}\t{:.1f}##".format("-".join([str(p) for p in pn]), x0, x1, top, bott)  #

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
            fallback_candidates: list[Path] = [] 
            try:
                for candidate_name in ("content_list.json", "*_content_list.json"): 
                    for p in output_dir.rglob(candidate_name): 
                        if p.is_file():
                            fallback_candidates.append(p)
            except Exception as scan_err:
                self.logger.warning(  
                    "[MinerU] Fallback scan for content_list.json failed: %s", scan_err, exc_info=True
                )

            if fallback_candidates:
                fallback_candidates.sort(
                    key=lambda p: (
                        (file_stem not in str(p).lower() and safe_stem not in str(p).lower()),
                        len(str(p)),
                    )
                )
                json_file = fallback_candidates[0]  
                subdir = json_file.parent  
                self.logger.warning(
                    "[MinerU] Fixed-path lookup failed, fallback matched content list: %s (total candidates=%s)",
                    json_file,
                    len(fallback_candidates),
                )

        if not json_file:
            attempted_str = ", ".join(str(p) for p in attempted) 
            raise FileNotFoundError(f"[MinerU] Missing output file, tried: {attempted_str}")

        try:
            _st = json_file.stat()  
            _abs_json = str(json_file.resolve())  
        except OSError as _e_stat:  
            _st = None  
            _abs_json = str(json_file)  
            self.logger.warning(f"[MinerU][content_list.json] stat 失败: {_e_stat}, path={_abs_json}")  
        _sz = _st.st_size if _st else -1  
        self.logger.warning(
            f"[MinerU][content_list.json] 文件已找到 exists=True path={_abs_json} size_bytes={_sz}"
        )  

        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)  

        if not isinstance(data, list):  
            self.logger.error(
                f"[MinerU][content_list.json] 根节点类型非 list: {type(data)}, path={_abs_json}"
            )  
            raise ValueError(
                f"[MinerU] content_list.json 根节点应为 list，实际 {type(data)}，path={_abs_json}"
            )  
        else:
            _n_blocks = len(data)  
            _n_with_cid = sum(
                1
                for _it in data
                if isinstance(_it, dict)
                and (str(_it.get("chuck_id") or _it.get("chunk_id") or "").strip())
            )  
            _sample_keys = (
                list(data[0].keys())[:16] if data and isinstance(data[0], dict) else []
            )  
            self.logger.warning(
                f"[MinerU][content_list.json] 已加载 blocks={_n_blocks} with_chunk_id={_n_with_cid} "
                f"sample_first_keys={_sample_keys}"
            )  

        for item in data:
            for key in ("img_path", "table_img_path", "equation_img_path"):
                if key in item and item[key]:
                    item[key] = str((subdir / item[key]).resolve())
        return data

    def _transfer_to_sections(self, outputs: list[dict[str, Any]], parse_method: str = None):
        sections = []  
        for idx, output in enumerate(outputs):  
            if "type" not in output or not output.get("type"):  
                continue  
            try:  
                section = None  
                _t = output["type"]  
                match _t:  
                    case MinerUContentType.TEXT | "text":  
                        section = output.get("text", "") or ""  
                    case MinerUContentType.TABLE | "table":  
                        _tb = output.get("table_body") or ""  
                        section = (
                            str(_tb)
                            + self._join_mineru_lines(output.get("table_caption"), "\n")
                            + self._join_mineru_lines(output.get("table_footnote"), "\n")
                        )  
                        if not str(section).strip():  
                            section = "FAILED TO PARSE TABLE"  
                    case MinerUContentType.IMAGE | "image":  
                        section = self._join_mineru_lines(output.get("image_caption"), "") + "\n" + self._join_mineru_lines(
                            output.get("image_footnote"), ""
                        )  
                    case MinerUContentType.EQUATION | "equation":  
                        section = output.get("text", "") or ""  
                    case MinerUContentType.CODE | "code":  
                        section = (output.get("code_body") or "") + self._join_mineru_lines(
                            output.get("code_caption"), "\n"
                        )  
                    case MinerUContentType.LIST | "list":
                        section = self._join_mineru_lines(output.get("list_items"), "\n")
                    case "header":
                        continue
                    case "footer":
                        section = output.get("text", "") or ""
                    case "page_number":
                        continue
                    case MinerUContentType.DISCARDED | "discarded":
                        continue

                if section is None:  
                    _fallback = output.get("text")  
                    if _fallback is not None and str(_fallback).strip():  
                        section = str(_fallback)  
                        self.logger.warning(  
                            "[MinerU] _transfer_to_sections: 未识别 type=%r，已用 text 兜底 idx=%s",
                            _t,
                            idx,
                        )  
                    else:  
                        section = ""  
                        self.logger.warning(
                            "[MinerU] _transfer_to_sections: 未识别 type=%r 且无 text，idx=%s keys=%s",
                            _t,
                            idx,
                            list(output.keys())[:20] if isinstance(output, dict) else None,
                        )  

                _cid = output.get("chunk_id") or output.get("chuck_id") or output.get("id") or output.get("block_id") or ""
                _cid = str(_cid).strip()[:64] if _cid else ""
                if section:
                    section = normalize_mineru_checkbox_latex(str(section))
                if section and parse_method == "manual":
                    sections.append((section, output["type"], self._line_tag(output), _cid))
                elif section and parse_method == "paper":
                    sections.append((section + self._line_tag(output), output["type"], _cid))
                else:
                    sections.append((section, self._line_tag(output), _cid))
            except Exception as _e_block:  
                self.logger.error(  
                    "[MinerU] _transfer_to_sections 单块失败 idx=%s type=%r page_idx=%r bbox=%r keys=%s err=%s",
                    idx,
                    output.get("type"),
                    output.get("page_idx"),
                    output.get("bbox"),
                    list(output.keys())[:28] if isinstance(output, dict) else None,
                    _e_block,
                    exc_info=True,
                )  
                raise  
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

    @staticmethod
    def _mineru_row_type_for_db(raw_type: Any) -> str:  
        s = (raw_type if raw_type is not None else "")  
        s = str(s).strip() or "unknown"  
        return s[:20]  

    @staticmethod
    def _mineru_str_path_for_db(p: Any, max_len: int = 512) -> Optional[str]:  
        if p is None or p == "":  
            return None  
        s = str(p).strip()  
        if len(s) <= max_len:  
            return s
        
        # 如果包含查询参数（?），保护查询参数不被截断
        if "?" in s:
            base_path, query_string = s.split("?", 1)
            # 为查询参数预留空间（加上 "?" 本身）
            query_len = len(query_string) + 1
            available_len = max(max_len - query_len, 50)  # 至少保留50字符的base路径
            if available_len > 0 and len(base_path) > available_len:
                truncated_base = base_path[:available_len - 1] + "…"
                return truncated_base + "?" + query_string
        
        return s[: max_len - 1] + "…"  

    @staticmethod
    def _mineru_public_download_url_for_db(
        raw_img_path: Any,
        kb_id: str,
        doc_id: str,
        *,
        max_len: int = MINERU_SECTION_IMG_PATH_MAX_LEN,
    ) -> Optional[str]:
        """将 img_path 规范为与 content_list.json 一致的完整 public_download URL 后写入 DB。"""
        if raw_img_path is None:
            return None
        raw = str(raw_img_path).strip()
        if not raw:
            return None
        if raw.startswith(f"{DOCUMENT_PUBLIC_DOWNLOAD_PREFIX}/"):
            return MinerUParser._mineru_str_path_for_db(raw, max_len=max_len)
        if raw.startswith("/v1/document/download/"):
            normalized = raw.replace("/v1/document/download/", f"{DOCUMENT_PUBLIC_DOWNLOAD_PREFIX}/", 1)
            return MinerUParser._mineru_str_path_for_db(normalized, max_len=max_len)
        img_path_obj = Path(raw.replace("\\", "/"))
        img_name = img_path_obj.name
        if not img_name:
            return MinerUParser._mineru_str_path_for_db(raw, max_len=max_len)
        ext = img_path_obj.suffix.lstrip(".") or "jpg"
        minio_key = f"{doc_id}/images/{img_name}"
        key_b64 = base64.urlsafe_b64encode(minio_key.encode("utf-8")).decode("utf-8").rstrip("=")
        download_url = f"{DOCUMENT_PUBLIC_DOWNLOAD_PREFIX}/{key_b64}?ext={ext}&bucket={kb_id}"
        return MinerUParser._mineru_str_path_for_db(download_url, max_len=max_len)

    @staticmethod
    def _sync_public_download_img_paths(
        target_list: list[dict[str, Any]],
        source_list: list[dict[str, Any]],
        img_keys: tuple[str, ...] = ("img_path", "table_img_path", "equation_img_path"),
    ) -> None:
        """MinIO 上传后，将 content_list 中已替换的完整图片 URL 同步回 outputs。"""
        if len(target_list) != len(source_list):
            return
        for tgt, src in zip(target_list, source_list):
            if not isinstance(tgt, dict) or not isinstance(src, dict):
                continue
            for key in img_keys:
                val = src.get(key)
                if val and isinstance(val, str) and str(val).strip():
                    tgt[key] = val

    @staticmethod
    def _mineru_json_safe_scalar(x: Any) -> Any:  
        if x is None:  
            return None  
        if hasattr(x, "item") and callable(getattr(x, "item", None)):  
            try:
                return x.item()  
            except Exception:  
                pass  
        if isinstance(x, (int, float, str, bool)):  
            return x  
        try:
            return str(x)
        except Exception:
            return repr(x)

    @staticmethod
    def _mineru_bbox_for_db(bbox: Any) -> Any:  
        if bbox is None:  
            return None  
        if isinstance(bbox, (list, tuple)):  
            return [MinerUParser._mineru_json_safe_scalar(v) for v in bbox[:32]]  
        if isinstance(bbox, dict):  
            return bbox  
        return bbox  

    @staticmethod
    def _mineru_json_safe(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, dict):
            return {
                str(k): MinerUParser._mineru_json_safe(v)
                for k, v in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [MinerUParser._mineru_json_safe(v) for v in value]
        return MinerUParser._mineru_json_safe_scalar(value)

    @staticmethod
    def _mineru_json_field_for_db(value: Any) -> Any:
        if value is None:
            return None
        try:
            # Ensure JSON fields are always serializable and normalized.
            return json.loads(json.dumps(MinerUParser._mineru_json_safe(value), ensure_ascii=False))
        except Exception:
            return None

    @staticmethod
    def _mineru_longtext_for_db(value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, (dict, list, tuple)):
            return json.dumps(MinerUParser._mineru_json_safe(value), ensure_ascii=False)
        return str(MinerUParser._mineru_json_safe_scalar(value))

    @staticmethod
    def _mineru_short_text_for_db(value: Any, max_len: int = 50) -> Optional[str]:
        if value is None:
            return None
        s = value if isinstance(value, str) else MinerUParser._mineru_longtext_for_db(value)
        if s is None:
            return None
        s = str(s).strip()
        if not s:
            return None
        return s[:max_len]

    @staticmethod
    def _build_mineru_section_id(doc_id: str, chunk_id: str, index: int) -> int:
        raw = f"{doc_id}:{chunk_id}:{index}".encode("utf-8", errors="ignore")
        val = int.from_bytes(hashlib.blake2b(raw, digest_size=8).digest(), "big") & 0x7FFFFFFFFFFFFFFF
        return val or (index + 1)

    @staticmethod
    def _resolve_chunk_id_for_mineru_section(item: dict[str, Any], index: int, doc_id: str) -> tuple[str, bool]:
        for _k in ("chunk_id", "chuck_id", "id", "block_id"):
            _v = item.get(_k)
            if _v is not None and str(_v).strip():
                _s = str(_v).strip()
                if len(_s) > 64:
                    _s = _s[:64]
                return _s, False
        return "", True

    @staticmethod
    def _normalize_kb_doc_ctx(v: Any) -> str:
        """将知识库/文档上下文 ID 规范为去空白字符串（兼容 list 包裹或非 str）。"""
        if v is None:
            return ""
        if isinstance(v, (list, tuple)) and len(v) > 0:
            v = v[0]
        return str(v).strip()

    def _save_sections_to_db(
        self,
        outputs: list[dict[str, Any]],
        kb_id: Optional[str],
        doc_id: Optional[str],
        callback: Optional[Callable] = None,
        *,
        progress_after_chunk: bool = False,
    ) -> None:
        kb_id = MinerUParser._normalize_kb_doc_ctx(kb_id)
        doc_id = MinerUParser._normalize_kb_doc_ctx(doc_id)
        _th = threading.current_thread()
        logging.info(
            "[MinerU][mineru_section] _save_sections_to_db 进入: pid=%s thread=%s daemon=%s kb_id=%r doc_id=%r outputs类型=%s len=%s",
            os.getpid(),
            _th.name,
            _th.daemon,
            kb_id,
            doc_id,
            type(outputs).__name__,
            len(outputs) if isinstance(outputs, list) else None,
        )

        def _progress(prog: float, msg: str) -> None:
            if progress_after_chunk:
                _lo, _hi = 0.902, 0.922
                _a, _b = 0.925, 0.943
                _cx = max(_lo, min(_hi, prog))
                prog = _a + (_cx - _lo) * (_b - _a) / (_hi - _lo) if _hi > _lo else _a
            self._emit_callback(callback, prog, msg)

        _start_msg = f"[MinerU] 开始保存 MinerU 输出到 mineru_section 表: kb_id={kb_id}, doc_id={doc_id}"
        self.logger.warning(_start_msg)
        logging.warning(_start_msg)
        if not kb_id or not doc_id:
            _skip_ctx_msg = f"[MinerU] 没有知识库或文档上下文，跳过写入数据库: kb_id={kb_id}, doc_id={doc_id}"
            self.logger.warning(_skip_ctx_msg)
            logging.warning(_skip_ctx_msg)
            _progress(0.91, f"[MinerU] 跳过写入 mineru_section：缺少 kb_id/doc_id (kb_id={kb_id}, doc_id={doc_id})")
            return
        try:
            from api.db.db_models import DB, MineruSection
        except Exception as e:
            logging.error(
                "[MinerU][mineru_section] 导入 MineruSection/DB 失败，跳过写入。请确认任务进程 PYTHONPATH 含项目根且可 import api。err=%s",
                e,
                exc_info=True,
            )
            self.logger.error(
                f"[MinerU][mineru_section] 导入模型失败，跳过写入: {e}",
                exc_info=True,
            )
            return

        _progress(0.902, "[MinerU] mineru_section：检查数据表…")
        try:
            _tbl_ok = MineruSection.table_exists()
            logging.info(
                "[MinerU][mineru_section] 表检查: mineru_section.table_exists()=%s kb_id=%s doc_id=%s",
                _tbl_ok,
                kb_id,
                doc_id,
            )
            if not _tbl_ok:
                _tb_missing_msg = "[MinerU] mineru_section 表不存在，跳过写入（请确认服务启动时已执行 init_database_tables/完成迁移）"
                self.logger.error(_tb_missing_msg)
                logging.error(_tb_missing_msg)
                _progress(0.91, "[MinerU] 跳过写入 mineru_section：表不存在")
                return
        except Exception as e:
            logging.error(
                "[MinerU][mineru_section] table_exists() 异常，仍将尝试 INSERT；若最终无数据请查库连接/权限。err=%s",
                e,
                exc_info=True,
            )
            self.logger.warning(
                f"[MinerU] 检查 mineru_section 表是否存在时异常: {e}",
                exc_info=True,
            )

        _pre_n = len(outputs)
        _nondict = (
            sum(1 for _it in outputs if not isinstance(_it, dict)) if isinstance(outputs, list) else -1
        )
        _pre_cid = sum(
            1
            for _it in outputs
            if isinstance(_it, dict)
            and (str(_it.get("chuck_id") or _it.get("chunk_id") or _it.get("id") or "").strip())
        )
        _pre_stat_msg = (
            f"[MinerU][mineru_section] 入表前统计 outputs_len={_pre_n} mineru原生块id数={_pre_cid} "
            f"（缺 id 时将自动生成合成 chunk_id 以保证可入库）"
        )
        self.logger.warning(_pre_stat_msg)
        logging.warning(_pre_stat_msg)
        if isinstance(outputs, list) and _nondict > 0:
            logging.warning(
                "[MinerU][mineru_section] outputs 中非 dict 元素已跳过: 跳过数=%s（仅 dict 会入表）",
                _nondict,
            )

        _progress(0.904, f"[MinerU] mineru_section：组装行数据（解析块 {_pre_n}，MinerU 自带 id {_pre_cid}）…")

        def _normalize_img_path_for_mineru_section(raw_img_path: Any) -> Optional[str]:
            return self._mineru_public_download_url_for_db(raw_img_path, kb_id, doc_id)

        rows: list[dict[str, Any]] = []
        missing_native_chunk_id = 0
        for idx, item in enumerate(outputs):
            if not isinstance(item, dict):
                continue
            _n_done = idx + 1
            if _pre_n > 0 and _pre_n >= 20 and _n_done % max(1, _pre_n // 8) == 0:
                _p = 0.904 + 0.012 * (_n_done / float(_pre_n))
                _progress(min(0.916, _p), f"[MinerU] mineru_section：组装中 {_n_done}/{_pre_n}…")

            item_type_raw = item.get("type") or "" 
            item_type_db = self._mineru_row_type_for_db(item_type_raw) 

            chunk_id, _missing_chunk_id = self._resolve_chunk_id_for_mineru_section(item, idx, str(doc_id))
            if _missing_chunk_id:
                missing_native_chunk_id += 1

            _pi = item.get("page_idx") 
            try:
                _pi = int(_pi) if _pi is not None and str(_pi).strip() != "" else None  
            except (TypeError, ValueError):
                _pi = None 

            row: dict[str, Any] = {
                "kb_id": str(kb_id),
                "doc_id": str(doc_id),
                "chunk_id": chunk_id or "", 
                "type": item_type_db,
                "bbox": self._mineru_json_field_for_db(self._mineru_bbox_for_db(item.get("bbox"))),
                "page_idx": _pi,
                "text": None,
                "text_level": None,
                "img_path": None,
                "table_caption": None,
                "table_footnote": None,
                "table_body": None,
                "sub_type": None,
                "list_items": None,
            }

            _tl = item.get("text_level")
            try:
                row["text_level"] = int(_tl) if _tl is not None and str(_tl).strip() != "" else None
            except (TypeError, ValueError):
                row["text_level"] = None 

            item_type_db_norm = str(item_type_db).strip().lower()  
            if item_type_db_norm == "text":
                if item.get("text") is not None and str(item.get("text")).strip() != "":
                    _text = normalize_mineru_checkbox_latex(str(item.get("text")))
                    _tl = row.get("text_level")
                    if _tl is not None and isinstance(_tl, int) and _tl > 0:
                        _level = max(1, min(6, _tl))
                        if not _text.lstrip().startswith("#"):
                            _text = f"{'#' * _level} {_text}"
                    row["text"] = self._mineru_longtext_for_db(_text)
            elif item_type_db_norm == "table":
                if item.get("table_caption") is not None: 
                    row["table_caption"] = self._mineru_json_field_for_db(item.get("table_caption")) 
                if item.get("table_footnote") is not None: 
                    row["table_footnote"] = self._mineru_json_field_for_db(item.get("table_footnote")) 
                if item.get("table_body") is not None and str(item.get("table_body")).strip() != "": 
                    row["table_body"] = self._mineru_longtext_for_db(item.get("table_body")) 
            elif item_type_db_norm == "table_caption":
                _table_caption = item.get("table_caption")  
                if (_table_caption is None or str(_table_caption).strip() == "") and item.get("text") is not None and str(item.get("text")).strip() != "":
                    _table_caption = item.get("text")  
                if _table_caption is not None and str(_table_caption).strip() != "":
                    row["table_caption"] = self._mineru_json_field_for_db(_table_caption)
            elif item_type_db_norm == "table_footnote":
                _table_footnote = item.get("table_footnote")  
                if (_table_footnote is None or str(_table_footnote).strip() == "") and item.get("text") is not None and str(item.get("text")).strip() != "":
                    _table_footnote = item.get("text") 
                if _table_footnote is not None and str(_table_footnote).strip() != "":
                    row["table_footnote"] = self._mineru_json_field_for_db(_table_footnote)
            elif item_type_db_norm == "table_body":
                _table_body = item.get("table_body")
                if (_table_body is None or str(_table_body).strip() == "") and item.get("text") is not None and str(item.get("text")).strip() != "":
                    _table_body = item.get("text")
                if _table_body is not None and str(_table_body).strip() != "":
                    row["table_body"] = self._mineru_longtext_for_db(_table_body)
            else:
                if item_type_db_norm == "image":
                    _img_parts = []
                    _img_cap = item.get("image_caption")
                    _img_fn = item.get("image_footnote")
                    if isinstance(_img_cap, list):
                        _img_parts.extend(str(c) for c in _img_cap if str(c).strip())
                    elif isinstance(_img_cap, str) and _img_cap.strip():
                        _img_parts.append(_img_cap.strip())
                    if isinstance(_img_fn, list):
                        _img_parts.extend(str(f) for f in _img_fn if str(f).strip())
                    elif isinstance(_img_fn, str) and _img_fn.strip():
                        _img_parts.append(_img_fn.strip())
                    if _img_parts:
                        row["text"] = self._mineru_longtext_for_db("\n".join(_img_parts))
                elif item.get("text") is not None and str(item.get("text")).strip() != "":
                    row["text"] = self._mineru_longtext_for_db(
                        normalize_mineru_checkbox_latex(str(item.get("text")))
                    )
            if "img_path" in item and item.get("img_path") is not None and str(item.get("img_path")).strip() != "":
                row["img_path"] = _normalize_img_path_for_mineru_section(item.get("img_path")) 
            if "sub_type" in item and item.get("sub_type") is not None and str(item.get("sub_type")).strip() != "":
                row["sub_type"] = self._mineru_short_text_for_db(item.get("sub_type"), max_len=50)
            if "list_items" in item and item.get("list_items") is not None:
                row["list_items"] = self._mineru_json_field_for_db(item.get("list_items"))

            rows.append(row)

        if missing_native_chunk_id:
            self.logger.warning(
                f"[MinerU][mineru_section] 共 {missing_native_chunk_id}/{len(rows)} 条未提供原生 chunk_id，已按空字符串写入（未生成合成值）"
            )

        if not rows:
            logging.warning(
                "[MinerU][mineru_section] 无可写入行: rows=0 outputs_len=%s nondict_skipped=%s kb_id=%s doc_id=%s",
                _pre_n,
                _nondict,
                kb_id,
                doc_id,
            )
            self.logger.info(
                f"[MinerU] mineru_section 本次无可写入记录，doc_id={doc_id}, kb_id={kb_id}, total_blocks={len(outputs)}"
            )
            _progress(0.91, f"[MinerU] mineru_section 无可写入记录：total_blocks={len(outputs)}")
            return

        _sample_keys = list(rows[0].keys()) if rows else []
        logging.info(
            "[MinerU][mineru_section] 即将写入: 行数=%s 首行字段键=%s 首行id=%s chunk_id=%s type=%s",
            len(rows),
            _sample_keys,
            rows[0].get("id") if rows else None,
            rows[0].get("chunk_id") if rows else None,
            rows[0].get("type") if rows else None,
        )

        _progress(0.917, f"[MinerU] mineru_section：删除本文档旧记录并写入 {len(rows)} 条…")

        try:
            with DB.connection_context():
                _progress(0.918, "[MinerU] mineru_section：正在删除旧切片…")
                _del_n = (
                    MineruSection.delete()
                    .where((MineruSection.kb_id == kb_id) & (MineruSection.doc_id == doc_id))
                    .execute()
                )
                logging.info(
                    "[MinerU][mineru_section] DELETE 已执行: 删除行数(返回值)=%s kb_id=%r doc_id=%r",
                    _del_n,
                    kb_id,
                    doc_id,
                )
                _progress(0.919, f"[MinerU] mineru_section：正在批量插入 {len(rows)} 条…")
                try:
                    MineruSection.insert_many(rows).execute()
                    logging.info(
                        "[MinerU][mineru_section] insert_many 成功: 条数=%s kb_id=%s doc_id=%s",
                        len(rows),
                        kb_id,
                        doc_id,
                    )
                    self.logger.warning(
                        "[MinerU][mineru_section] insert_many 成功: 条数=%s kb_id=%s doc_id=%s",
                        len(rows),
                        kb_id,
                        doc_id,
                    )
                except Exception as _bulk_e:
                    logging.error(
                        "[MinerU][mineru_section] insert_many 失败，将逐条重试: type=%s repr=%s kb_id=%s doc_id=%s",
                        type(_bulk_e).__name__,
                        repr(_bulk_e)[:800],
                        kb_id,
                        doc_id,
                        exc_info=True,
                    )
                    self.logger.error(
                        "[MinerU][mineru_section] insert_many 失败，将逐条重试: type=%s repr=%s kb_id=%s doc_id=%s",
                        type(_bulk_e).__name__,
                        repr(_bulk_e)[:800],
                        kb_id,
                        doc_id,
                        exc_info=True,
                    )
                    self.logger.warning(
                        "[MinerU][mineru_section] 批量插入失败，降级逐条插入。doc_id=%s kb_id=%s err=%s",
                        doc_id,
                        kb_id,
                        _bulk_e,
                        exc_info=True,
                    )
                    ok_cnt = 0
                    fail_cnt = 0
                    for _r in rows:
                        try:
                            MineruSection.insert(**_r).execute()
                            ok_cnt += 1
                        except Exception as _row_e:
                            fail_cnt += 1
                            _lvl = logging.error if fail_cnt <= 3 else logging.warning
                            _lvl(
                                "[MinerU][mineru_section] 单条 insert 失败 #%s: chunk_id=%r id=%r err_type=%s err=%s",
                                fail_cnt,
                                _r.get("chunk_id"),
                                _r.get("id"),
                                type(_row_e).__name__,
                                repr(_row_e)[:500],
                                exc_info=(fail_cnt <= 2),
                            )
                            self.logger.warning(
                                "[MinerU][mineru_section] 单条插入失败，已跳过。doc_id=%s kb_id=%s chunk_id=%s err=%s",
                                doc_id,
                                kb_id,
                                _r.get("chunk_id"),
                                _row_e,
                            )
                    self.logger.warning(
                        "[MinerU][mineru_section] 降级插入完成。ok=%s fail=%s total=%s doc_id=%s kb_id=%s",
                        ok_cnt,
                        fail_cnt,
                        len(rows),
                        doc_id,
                        kb_id,
                    )
                    if ok_cnt <= 0:
                        raise RuntimeError(f"mineru_section fallback insert failed: fail={fail_cnt}, total={len(rows)}")
            try:
                _verify_cnt = (
                    MineruSection.select()
                    .where((MineruSection.kb_id == kb_id) & (MineruSection.doc_id == doc_id))
                    .count()
                )
            except Exception as _vc_e:
                _verify_cnt = -1
                logging.warning(
                    "[MinerU][mineru_section] 写入后 COUNT 校验失败（可忽略）kb_id=%s doc_id=%s err=%s",
                    kb_id,
                    doc_id,
                    _vc_e,
                )
            _ok_msg = (
                f"[MinerU] mineru_section 已写入 {len(rows)} 条记录，doc_id={doc_id}, kb_id={kb_id}, "
                f"total_blocks={len(outputs)}, synthetic_chunk_id_count={missing_native_chunk_id}"
            )
            self.logger.info(_ok_msg)
            logging.warning(_ok_msg)
            logging.info(
                "[MinerU][mineru_section] 写入后校验: 本 doc 在表中行数=%s（期望约 %s）",
                _verify_cnt,
                len(rows),
            )
            _progress(0.92, f"[MinerU] mineru_section 已写入 {len(rows)} 条记录")
        except Exception as e:
            self.logger.error(
                f"[MinerU] 写入 mineru_section 表失败，doc_id={doc_id}, kb_id={kb_id}, err={e}",
                exc_info=True,
            )
            logging.error(
                "[MinerU][mineru_section] 写入流程异常(整块): type=%s doc_id=%r kb_id=%r rows计划=%s err=%s",
                type(e).__name__,
                doc_id,
                kb_id,
                len(rows) if isinstance(rows, list) else None,
                repr(e)[:800],
                exc_info=True,
            )
            self.logger.error(
                "[MinerU][mineru_section] 写入流程异常(整块): type=%s doc_id=%r kb_id=%r rows计划=%s err=%s",
                type(e).__name__,
                doc_id,
                kb_id,
                len(rows) if isinstance(rows, list) else None,
                repr(e)[:800],
                exc_info=True,
            )
            logging.warning(
                "[MinerU] 写入 mineru_section 表失败（root摘要）doc_id=%s kb_id=%s err=%s",
                doc_id,
                kb_id,
                e,
            )
            _em = str(e).replace("'", "")[:400]
            _progress(0.922, f"[MinerU][WARN] mineru_section 写入失败（主解析仍继续）: {_em}")

    def _schedule_save_sections_to_db(
        self,
        outputs: list[dict[str, Any]],
        kb_id: Optional[str],
        doc_id: Optional[str],
        callback: Optional[Callable] = None,
        cleanup_dir: Optional[Path] = None,
        cleanup_enabled: bool = False,
    ) -> Optional[threading.Thread]:
        """解析完成后异步写 mineru_section，主链路继续执行。"""
        if not kb_id or not doc_id:
            logging.warning(
                "[MinerU][mineru_section] _schedule_save_sections_to_db 跳过: kb_id/doc_id 为空 kb_id=%r doc_id=%r",
                kb_id,
                doc_id,
            )
            return None
        try:
            snapshot = copy.deepcopy(outputs)
        except Exception as _e_snap:
            logging.warning(
                "[MinerU][mineru_section] deepcopy(outputs) 失败改用原引用: %s",
                _e_snap,
                exc_info=True,
            )
            self.logger.warning(
                "[MinerU][DB_THREAD] deepcopy(outputs) 失败，改用原引用: %s",
                _e_snap,
                exc_info=True,
            )
            snapshot = outputs

        def _worker() -> None:
            try:
                _wth = threading.current_thread()
                logging.info(
                    "[MinerU][mineru_section][ASYNC] 后台线程开始: name=%s ident=%s pid=%s kb_id=%r doc_id=%r blocks=%s",
                    _wth.name,
                    getattr(_wth, "native_id", None),
                    os.getpid(),
                    kb_id,
                    doc_id,
                    len(snapshot) if isinstance(snapshot, list) else None,
                )
                self.logger.warning(
                    "[MinerU][DB_THREAD] 后台入库线程开始: kb_id=%s doc_id=%s blocks=%s",
                    kb_id,
                    doc_id,
                    len(snapshot) if isinstance(snapshot, list) else None,
                )
                self._save_sections_to_db(snapshot, kb_id, doc_id, callback=callback, progress_after_chunk=False)
                logging.info(
                    "[MinerU][mineru_section][ASYNC] 后台线程正常结束: doc_id=%r kb_id=%r",
                    doc_id,
                    kb_id,
                )
                self.logger.warning("[MinerU][DB_THREAD] 后台入库线程结束: doc_id=%s", doc_id)
            except Exception as _e_worker:
                logging.error(
                    "[MinerU][mineru_section][ASYNC] 后台线程异常: type=%s err=%s doc_id=%r kb_id=%r",
                    type(_e_worker).__name__,
                    repr(_e_worker)[:800],
                    doc_id,
                    kb_id,
                    exc_info=True,
                )
                self.logger.error(
                    "[MinerU][DB_THREAD] 后台入库线程异常: %s",
                    _e_worker,
                    exc_info=True,
                )
                _em = str(_e_worker).replace("'", "")[:400]
                self._emit_callback(callback, 0.922, f"[MinerU][WARN] 后台入库线程异常: {_em}")
            finally:
                if cleanup_enabled and cleanup_dir and cleanup_dir.exists():
                    try:
                        import shutil
                        shutil.rmtree(cleanup_dir)
                        logging.info(
                            "[MinerU][mineru_section][ASYNC] 后台任务清理输出目录完成: dir=%s doc_id=%r kb_id=%r",
                            str(cleanup_dir),
                            doc_id,
                            kb_id,
                        )
                    except Exception as _e_cleanup:
                        logging.warning(
                            "[MinerU][mineru_section][ASYNC] 后台任务清理输出目录失败: dir=%s err=%s",
                            str(cleanup_dir),
                            _e_cleanup,
                            exc_info=True,
                        )

        worker = threading.Thread(
            target=_worker,
            name=f"mineru_db_{str(doc_id)[:8]}",
            daemon=False,
        )
        worker.start()
        logging.info(
            "[MinerU][mineru_section] 已启动异步入库线程: thread_name=%s kb_id=%r doc_id=%r MINERU_DB_SAVE_ASYNC=1",
            worker.name,
            kb_id,
            doc_id,
        )
        self.logger.warning(
            "[MinerU][DB_THREAD] 已启动后台入库线程: kb_id=%s doc_id=%s",
            kb_id,
            doc_id,
        )
        return worker

    def _upload_mineru_outputs_to_minio(
        self,
        output_dir: Path,
        kb_id: str,
        doc_id: str,
        content_list: list[dict[str, Any]],
        callback: Optional[Callable] = None,
        pdf_path: Optional[Path] = None,
    ) -> bool:
        try:
            if not output_dir or not output_dir.exists():
                self.logger.error(f"[MinerU] 上传MinIO失败: output_dir 不存在或无效: {output_dir}")
                self._emit_callback(callback, -1, f"[MinerU] 解析输出目录无效: {output_dir}")
                return False
            if not output_dir.is_dir():
                self.logger.error(f"[MinerU] 上传MinIO失败: output_dir 不是目录: {output_dir}")
                self._emit_callback(callback, -1, f"[MinerU] 解析输出路径不是目录: {output_dir}")
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

            self._emit_callback(callback, 0.76, f"[MinerU] 开始上传解析产物到MinIO...")

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
                self._emit_callback(callback, 0.78, f"[MinerU] 已上传content_list.json")
            except Exception as e:
                self.logger.error(f"[MinerU] 上传 content_list.json 失败: {e}", exc_info=True)
                self._emit_callback(callback, -1, f"[MinerU] 上传 content_list.json 失败: {e}")
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
                    self._emit_callback(callback, 0.80, f"[MinerU] 已上传Markdown文件")
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
                self._emit_callback(callback, 0.85, f"[MinerU] 已上传 {uploaded_image_count} 张图片")
            else:
                self.logger.info(f"[MinerU] 未找到图片文件，跳过上传")

            pdf_uploaded = False
            if pdf_path and pdf_path.exists() and pdf_path.is_file():
                try:
                    pdf_location = f"{base_prefix}/{pdf_path.name}"
                    settings.STORAGE_IMPL.put(kb_id, pdf_location, pdf_path.read_bytes())
                    self.logger.info(f"[MinerU] 已上传PDF文件: bucket={kb_id}, location={pdf_location}")
                    pdf_uploaded = True
                    self._emit_callback(callback, 0.87, f"[MinerU] 已上传PDF文件")
                except Exception as e:
                    self.logger.warning(f"[MinerU] 上传PDF文件失败: {e}")

            self.logger.info(
                f"[MinerU] 解析产物上传完成: bucket={kb_id}, prefix={base_prefix}, "
                f"json={'已上传' if json_uploaded else '失败'}, markdown={'已上传' if markdown_uploaded else '未找到'}, 图片={uploaded_image_count}张, "
                f"pdf={'已上传' if pdf_uploaded else '未上传'}"
            )
            self._emit_callback(callback, 0.90, f"[MinerU] 解析产物上传完成")
            return True

        except Exception as e:
            self.logger.error(f"[MinerU] 上传解析产物到MinIO失败: {e}", exc_info=True)
            self._emit_callback(callback, -1, f"[MinerU] 上传解析产物到MinIO失败: {e}")
            return False

    def parse_document(
        self,
        filepath: str | PathLike[str],
        binary: Union[BytesIO, bytes, None] = None,
        callback: Optional[Callable] = None,
        *,
        output_dir: Optional[str] = None,
        backend: str = "pipeline",
        delete_output: bool = True,
        **kwargs,
    ) -> tuple:
        return self.parse_pdf(
            filepath=filepath,
            binary=binary,
            callback=callback,
            output_dir=output_dir,
            backend=backend,
            delete_output=delete_output,
            **kwargs,
        )

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
        cleanup_handed_to_db_task = False

        parser_cfg = kwargs.get('parser_config', {}) or {}
        _kb_mineru_backend = parser_cfg.get("mineru_backend")
        if _kb_mineru_backend not in (None, ""):
            backend = str(_kb_mineru_backend).strip()
        lang = parser_cfg.get('mineru_lang') or kwargs.get('lang', 'English')
        mineru_lang_code = LANGUAGE_TO_MINERU_MAP.get(lang, 'ch') 
        mineru_method_raw_str = parser_cfg.get('mineru_parse_method', 'auto')
        enable_formula = parser_cfg.get('mineru_formula_enable', True)
        enable_table = parser_cfg.get('mineru_table_enable', True)
        use_submitted_content_list = bool(parser_cfg.get("use_submitted_content_list", False))

        _kb_raw = kwargs.get("kb_id")
        _doc_raw = kwargs.get("doc_id")
        kb_id = MinerUParser._normalize_kb_doc_ctx(_kb_raw)
        doc_id = MinerUParser._normalize_kb_doc_ctx(_doc_raw)

        if use_submitted_content_list:
            self.logger.info(
                "[MinerU] use_submitted_content_list=True，直接读取已提交 content_list，跳过 MinerU 重新解析与回写。kb_id=%s doc_id=%s",
                kb_id,
                doc_id,
            )
            if not kb_id or not doc_id:
                self._emit_callback(callback, -1, "[MinerU] use_submitted_content_list 模式缺少 kb_id/doc_id。")
                raise ValueError("use_submitted_content_list requires kb_id and doc_id")
            content_bin = settings.STORAGE_IMPL.get(kb_id, f"{doc_id}/content_list.json")
            if not content_bin:
                self._emit_callback(callback, -1, "[MinerU] 未找到已提交的 content_list.json。")
                raise FileNotFoundError(f"content_list.json not found for doc_id={doc_id}")
            outputs = json.loads(content_bin.decode("utf-8"))
            if not isinstance(outputs, list):
                self._emit_callback(callback, -1, "[MinerU] content_list.json 根节点必须是 list。")
                raise ValueError("content_list.json root must be list")
            self._emit_callback(callback, 0.70, f"[MinerU] 已加载提交产物 blocks={len(outputs)}")
            sections = self._transfer_to_sections(outputs, parse_method)
            tables = self._transfer_to_tables(outputs)
            self._emit_callback(callback, 0.78, "[MinerU] 已基于提交产物完成分块转换")
            try:
                from api.db.services.document_service import DocumentService
                ok, doc = DocumentService.get_by_id(doc_id)
                if ok and isinstance(doc.parser_config, dict):
                    new_cfg = dict(doc.parser_config)
                    for _flag in (
                        "use_submitted_content_list",
                        "skip_mineru_output_upload",
                        "skip_mineru_section_persist",
                    ):
                        if _flag in new_cfg:
                            new_cfg.pop(_flag, None)
                    DocumentService.update_parser_config(doc_id, new_cfg)
            except Exception as _clear_err:
                self.logger.warning("[MinerU] 清理一次性 parser_config 开关失败: %s", _clear_err)
            return sections, tables

        file_path = Path(filepath)
        suffix_lower = file_path.suffix.lower()
        mineru_excel_suffixes = {".xlsx", ".xls", ".xlsm"}
        if suffix_lower in mineru_excel_suffixes:
            from deepdoc.utils.excel2pdf import convert_excel_bytes_to_pdf_bytes

            raw = None
            if binary is not None:
                raw = binary.read() if hasattr(binary, "read") else binary
            if raw is None:
                raw = Path(filepath).read_bytes()
            if not isinstance(raw, bytes):
                raw = bytes(raw)
            try:
                self.logger.info(
                    "[MinerU][Diag] Incoming Excel bytes md5=%s size=%s suffix=%s",
                    hashlib.md5(raw).hexdigest(),
                    len(raw),
                    suffix_lower,
                )
            except Exception:
                pass
            if callback:
                callback(0.12, "[MinerU] Excel detected, converting to PDF...")
            pdf_bytes = convert_excel_bytes_to_pdf_bytes(raw, excel_suffix=suffix_lower)
            try:
                self.logger.info(
                    "[MinerU][Diag] Excel->PDF bytes md5=%s size=%s",
                    hashlib.md5(pdf_bytes).hexdigest(),
                    len(pdf_bytes),
                )
            except Exception:
                pass
            pdf_virtual_path = str(file_path.with_suffix(".pdf"))
            if callback:
                callback(0.14, "[MinerU] Excel converted to PDF, continue parsing...")
            if kb_id and doc_id and not bool(parser_cfg.get("skip_mineru_output_upload", False)):
                try:
                    pdf_filename = Path(pdf_virtual_path).name
                    pdf_location = f"{doc_id}/{pdf_filename}"
                    result = settings.STORAGE_IMPL.put(kb_id, pdf_location, pdf_bytes)
                    if result is None:
                        raise RuntimeError("MinIO put returned None")
                    self.logger.info(f"[MinerU] 已上传Excel转化PDF文件: bucket={kb_id}, location={pdf_location}")
                except Exception as e:
                    self.logger.warning(f"[MinerU] 上传Excel转化PDF文件失败: {e}")
            return self.parse_pdf(
                filepath=pdf_virtual_path,
                binary=pdf_bytes,
                callback=callback,
                output_dir=output_dir,
                backend=backend,
                server_url=server_url,
                delete_output=delete_output,
                parse_method=parse_method,
                **kwargs,
            )

        mineru_word_suffixes = {".doc", ".docx", ".docm", ".dot", ".dotx", ".dotm"}
        if suffix_lower in mineru_word_suffixes:
            from deepdoc.utils.word2pdf import convert_word_bytes_to_pdf_bytes

            raw = None
            if binary is not None:
                raw = binary.read() if hasattr(binary, "read") else binary
            if raw is None:
                raw = Path(filepath).read_bytes()
            if not isinstance(raw, bytes):
                raw = bytes(raw)
            try:
                self.logger.info(
                    "[MinerU][Diag] Incoming Word bytes md5=%s size=%s suffix=%s",
                    hashlib.md5(raw).hexdigest(),
                    len(raw),
                    suffix_lower,
                )
            except Exception:
                pass
            if callback:
                callback(0.12, "[MinerU] Word detected, converting to PDF...")
            pdf_bytes = convert_word_bytes_to_pdf_bytes(raw, word_suffix=suffix_lower)
            try:
                self.logger.info(
                    "[MinerU][Diag] Word->PDF bytes md5=%s size=%s",
                    hashlib.md5(pdf_bytes).hexdigest(),
                    len(pdf_bytes),
                )
            except Exception:
                pass
            pdf_virtual_path = str(file_path.with_suffix(".pdf"))
            if callback:
                callback(0.14, "[MinerU] Word converted to PDF, continue parsing...")
            if kb_id and doc_id and not bool(parser_cfg.get("skip_mineru_output_upload", False)):
                try:
                    pdf_filename = Path(pdf_virtual_path).name
                    pdf_location = f"{doc_id}/{pdf_filename}"
                    result = settings.STORAGE_IMPL.put(kb_id, pdf_location, pdf_bytes)
                    if result is None:
                        raise RuntimeError("MinIO put returned None")
                    self.logger.info(f"[MinerU] 已上传Word转化PDF文件: bucket={kb_id}, location={pdf_location}")
                except Exception as e:
                    self.logger.warning(f"[MinerU] 上传Word转化PDF文件失败: {e}")
            return self.parse_pdf(
                filepath=pdf_virtual_path,
                binary=pdf_bytes,
                callback=callback,
                output_dir=output_dir,
                backend=backend,
                server_url=server_url,
                delete_output=delete_output,
                parse_method=parse_method,
                **kwargs,
            )

        mineru_image_suffixes = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tif", ".tiff"}
        if suffix_lower in mineru_image_suffixes:
            from deepdoc.utils.pic2pdf import convert_image_bytes_to_pdf_bytes

            raw = None
            if binary is not None:
                raw = binary.read() if hasattr(binary, "read") else binary
            if raw is None:
                raw = Path(filepath).read_bytes()
            if not isinstance(raw, bytes):
                raw = bytes(raw)
            try:
                self.logger.info(
                    "[MinerU][Diag] Incoming Image bytes md5=%s size=%s suffix=%s",
                    hashlib.md5(raw).hexdigest(),
                    len(raw),
                    suffix_lower,
                )
            except Exception:
                pass
            if callback:
                callback(0.12, "[MinerU] Image detected, converting to PDF...")
            pdf_bytes = convert_image_bytes_to_pdf_bytes(raw, image_suffix=suffix_lower)
            try:
                self.logger.info(
                    "[MinerU][Diag] Image->PDF bytes md5=%s size=%s",
                    hashlib.md5(pdf_bytes).hexdigest(),
                    len(pdf_bytes),
                )
            except Exception:
                pass
            pdf_virtual_path = str(file_path.with_suffix(".pdf"))
            if callback:
                callback(0.14, "[MinerU] Image converted to PDF, continue parsing...")
            if kb_id and doc_id and not bool(parser_cfg.get("skip_mineru_output_upload", False)):
                try:
                    pdf_filename = Path(pdf_virtual_path).name
                    pdf_location = f"{doc_id}/{pdf_filename}"
                    result = settings.STORAGE_IMPL.put(kb_id, pdf_location, pdf_bytes)
                    if result is None:
                        raise RuntimeError("MinIO put returned None")
                    self.logger.info(f"[MinerU] 已上传图片转化PDF文件: bucket={kb_id}, location={pdf_location}")
                except Exception as e:
                    self.logger.warning(f"[MinerU] 上传图片转化PDF文件失败: {e}")
            return self.parse_pdf(
                filepath=pdf_virtual_path,
                binary=pdf_bytes,
                callback=callback,
                output_dir=output_dir,
                backend=backend,
                server_url=server_url,
                delete_output=delete_output,
                parse_method=parse_method,
                **kwargs,
            )

        pdf_file_name = file_path.stem.replace(" ", "") + ".pdf"
        pdf_file_path_valid = os.path.join(file_path.parent, pdf_file_name)

        if binary:
            temp_dir = Path(tempfile.mkdtemp(prefix="mineru_bin_pdf_"))
            temp_pdf = temp_dir / pdf_file_name
            with open(temp_pdf, "wb") as f:
                f.write(binary)
            pdf = temp_pdf
            self.logger.info(f"[MinerU] Received binary PDF -> {temp_pdf}")
            self._emit_callback(callback, 0.15, f"[MinerU] Received binary PDF -> {temp_pdf}")
        else:
            if pdf_file_path_valid != filepath:
                self.logger.info(f"[MinerU] Remove all space in file name: {pdf_file_path_valid}")
                shutil.move(filepath, pdf_file_path_valid)
            pdf = Path(pdf_file_path_valid)
            if not pdf.exists():
                self._emit_callback(callback, -1, f"[MinerU] PDF not found: {pdf}")
                raise FileNotFoundError(f"[MinerU] PDF not found: {pdf}")

        if output_dir:
            out_dir = Path(output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
        else:
            out_dir = Path(tempfile.mkdtemp(prefix="mineru_pdf_"))
            created_tmp_dir = True

        self.logger.info(f"[MinerU] Output directory: {out_dir} backend={backend} api={self.mineru_api} server_url={server_url or self.mineru_server_url}")
        self._emit_callback(callback, 0.15, f"[MinerU] Output directory: {out_dir}")

        self.__images__(pdf, zoomin=1)

        self._mineru_outputs_for_db = None

        try:
            try:
                resolved_backend = MinerUBackend(backend)  
            except ValueError:
                resolved_backend = backend  
                self.logger.warning( 
                    "[MinerU] Unknown backend '%s', bypass local enum cast and forward as raw string.",
                    backend,
                )
            options = MinerUParseOptions(
                backend=resolved_backend,
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
            self._emit_callback(callback, 0.75, f"[MinerU] Parsed {len(outputs)} blocks from PDF.")

            _db_async_flag = str(os.environ.get("MINERU_DB_SAVE_ASYNC", "0")).strip().lower() not in (
                "0",
                "false",
                "no",
                "off",
            )
            logging.info(
                "[MinerU][mineru_section] 解析完成上下文: kb_id(raw)=%r doc_id(raw)=%r -> kb_id=%r doc_id=%r "
                "outputs=%s MINERU_DB_SAVE_ASYNC=%s",
                _kb_raw,
                _doc_raw,
                kb_id,
                doc_id,
                len(outputs),
                _db_async_flag,
            )
            self.logger.info(f"[MinerU] 解析完成，MinIO/入库上下文: kb_id={kb_id}, doc_id={doc_id}")

            if not kb_id or not doc_id:
                logging.warning(
                    "[MinerU][mineru_section] 缺少有效 kb_id/doc_id，已跳过 MinIO 与 mineru_section。"
                    "raw_kb_id=%r raw_doc_id=%r（请确认 chunk 调用传入 kb_id、doc_id，且 task 联表含 document.kb_id）",
                    _kb_raw,
                    _doc_raw,
                )
                self.logger.warning(
                    "[MinerU] 未传入 kb_id 或 doc_id，跳过解析产物上传 MinIO（知识库/文档链路应传入二者）；"
                    "若批量解析时经常缺失，请检查任务执行器传入的 task['kb_id']/task['doc_id']"
                )
            else:
                try:
                    if bool(parser_cfg.get("skip_mineru_output_upload", False)):
                        self.logger.info(
                            "[MinerU] skip_mineru_output_upload=True，跳过解析产物上传 MinIO。doc_id=%s kb_id=%s",
                            doc_id,
                            kb_id,
                        )
                    else:
                        content_list_for_minio = self._convert_content_list_to_markdown(outputs)
                        ok = self._upload_mineru_outputs_to_minio(
                            output_dir=final_out_dir,
                            kb_id=kb_id,
                            doc_id=doc_id,
                            content_list=content_list_for_minio,
                            callback=callback,
                            pdf_path=pdf,
                        )
                        if ok:
                            self._sync_public_download_img_paths(outputs, content_list_for_minio)
                        else:
                            self.logger.warning(
                                "[MinerU] 解析产物上传 MinIO 返回失败（见上文日志），doc_id=%s, kb_id=%s",
                                doc_id, kb_id,
                            )

                    logging.warning("#########上传解析产物流程结束#########")
                    logging.warning("#########上传解析产物流程结束#########")
                    logging.warning("#########上传解析产物流程结束#########")
                except Exception as e:
                    self.logger.warning(
                        "[MinerU] 上传解析产物到MinIO异常: %s (doc_id=%s, kb_id=%s)",
                        e, doc_id, kb_id, exc_info=True,
                    )

            self.logger.info(
                "[MinerU] 解析与（如有）解析产物 MinIO/入库阶段已完成，开始 _transfer_to_sections / _transfer_to_tables，"
                "blocks=%s parse_method=%s",
                len(outputs),
                parse_method,
            )
            try:
                _sections = self._transfer_to_sections(outputs, parse_method)
                _tables = self._transfer_to_tables(outputs)
            except Exception as _e_transfer:
                self.logger.error(
                    "[MinerU] _transfer_to_sections/_transfer_to_tables 失败: %s",
                    _e_transfer,
                    exc_info=True,
                )
                raise

            self._mineru_outputs_for_db = None
            if kb_id and doc_id:
                logging.info(
                    "[MinerU][mineru_section] 主链路已结束，开始同步入库: blocks=%s kb_id=%s doc_id=%s",
                    len(outputs),
                    kb_id,
                    doc_id,
                )
                if bool(parser_cfg.get("skip_mineru_section_persist", False)):
                    logging.info(
                        "[MinerU][mineru_section] skip_mineru_section_persist=True，跳过写入 mineru_section。kb_id=%s doc_id=%s",
                        kb_id,
                        doc_id,
                    )
                else:
                    self._save_sections_to_db(
                        outputs,
                        kb_id,
                        doc_id,
                        callback=callback,
                        progress_after_chunk=False,
                    )
            else:
                logging.warning(
                    "[MinerU][mineru_section] 未触发入库（kb_id/doc_id 为空）outputs=%s",
                    len(outputs),
                )
            return _sections, _tables
        finally:
            if temp_pdf and temp_pdf.exists():
                try:
                    temp_pdf.unlink()
                    temp_pdf.parent.rmdir()
                except Exception:
                    pass
            if delete_output and created_tmp_dir and out_dir.exists() and not cleanup_handed_to_db_task:
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
