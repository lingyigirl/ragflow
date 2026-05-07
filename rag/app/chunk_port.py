from typing import Any, Callable

from rag.app import hichunk as hichunk_app
from rag.app import one as one_app


def _safe_callback(callback: Callable | None, progress: float, message: str) -> None:
    if callback is not None:
        callback(progress, message)


def chunk_hichunk_port(
    filename: str,
    binary: bytes | None = None,
    lang: str = "Chinese",
    callback: Callable | None = None,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    _safe_callback(callback, 0.05, "hichunk bridge start")
    docs = hichunk_app.chunk(filename, binary=binary, lang=lang, callback=callback, **kwargs)
    _safe_callback(callback, 0.95, "hichunk bridge done")
    return docs or []


def chunk_one_port(
    filename: str,
    binary: bytes | None = None,
    lang: str = "Chinese",
    callback: Callable | None = None,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    _safe_callback(callback, 0.05, "one bridge start")
    docs = one_app.chunk(filename, binary=binary, lang=lang, callback=callback, **kwargs)
    _safe_callback(callback, 0.95, "one bridge done")
    return docs or []


def chunk_dispatch_port(
    method: str,
    filename: str,
    binary: bytes | None = None,
    lang: str = "Chinese",
    callback: Callable | None = None,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    method_lc = (method or "").strip().lower()
    if method_lc == "hichunk":
        return chunk_hichunk_port(filename, binary=binary, lang=lang, callback=callback, **kwargs)
    if method_lc == "one":
        return chunk_one_port(filename, binary=binary, lang=lang, callback=callback, **kwargs)
    raise ValueError(f"Unsupported chunk method: {method}")
