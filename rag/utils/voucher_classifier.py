import json
import re

import json_repair


VOUCHER_TYPE_OPTIONS = [
    "身份证",
    "户口簿",
    "临时身份证",
    "出生证明",
    "普通存单",
    "大额特种存单",
    "个人大额存单",
    "凭证式国债",
    "转账支票",
    "进账单",
    "特种转账借方凭证",
    "特种转账贷方凭证",
    "结婚证",
    "房产证",
    "机动车驾驶证",
    "机动车行驶证",
    "电子发票",
    "其他",
]


def build_voucher_classify_content(chunks, max_chars=6000):
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


def _normalize_confidence(raw_confidence):
    try:
        conf = float(raw_confidence)
    except Exception:
        return None
    if conf < 0:
        return 0.0
    if conf > 1:
        return 1.0
    return conf


def parse_voucher_classify_result(raw_response):
    failed = {
        "voucher_type": None,
        "voucher_type_confidence": None,
        "llm_classify_success": False,
    }
    if not raw_response:
        return failed

    cleaned = re.sub(r"^.*</think>", "", str(raw_response), flags=re.DOTALL)
    cleaned = re.sub(r"^```json\s*|```$", "", cleaned.strip(), flags=re.DOTALL)
    try:
        obj = json_repair.loads(cleaned)
    except json_repair.JSONDecodeError:
        try:
            obj = json.loads(cleaned)
        except Exception:
            return failed
    except Exception:
        return failed

    if not isinstance(obj, dict):
        return failed

    label = str(obj.get("label", "")).strip()
    if label not in VOUCHER_TYPE_OPTIONS:
        return failed

    confidence = _normalize_confidence(obj.get("confidence"))
    return {
        "voucher_type": label,
        "voucher_type_confidence": confidence,
        "llm_classify_success": True,
    }
