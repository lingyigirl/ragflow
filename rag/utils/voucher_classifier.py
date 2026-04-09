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
    "土地证",
    "股金证",
    "担保证明",
    "股权质押证明",
    "其他",
    "营业执照",
    "征信报告",
    "合同",
    "财务报表",
    "完税凭证",
    "公司章程",
    "审计报告",
    "交易流水",
    "借款明细",
    "简历",
    "学位证书",
    "学历证书",
]


def get_failed_voucher_payload():
    return {
        "voucher_type": None,
        "voucher_type_confidence": None,
        "llm_classify_success": False,
        "voucher_type_source": None,
    }


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


def build_voucher_classify_content_from_content_list(content_list, max_chars=6000):
    text_fields = ("text", "table_body", "content", "title", "table_caption")
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
                value = json.dumps(value, ensure_ascii=False)
            value = str(value).strip()
            if value:
                merged.append(value)
        if merged:
            chunks.append({"content_with_weight": "\n".join(merged)})
    return build_voucher_classify_content(chunks, max_chars=max_chars)


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


def build_voucher_classify_prompt(content: str):
    label_options = "、".join(VOUCHER_TYPE_OPTIONS)
    system_prompt = (
        "你是文档凭证分类助手。"
        "请严格根据用户提供的文档正文内容进行分类，禁止依据文件名、后缀、路径、上传名猜测。"
        f"可选标签仅有：{label_options}。"
        "请只输出 JSON，格式为：{\"label\":\"<标签>\",\"confidence\":<0到1之间数字>}。"
    )
    user_prompt = f"请基于以下文档正文进行单标签分类：\n{content}"
    return system_prompt, user_prompt


def normalize_voucher_result_to_payload(parsed):
    if parsed.get("llm_classify_success"):
        return {
            "voucher_type": parsed.get("voucher_type"),
            "voucher_type_confidence": parsed.get("voucher_type_confidence"),
            "llm_classify_success": True,
            "voucher_type_source": "llm",
        }
    return get_failed_voucher_payload()


OPEN_VOUCHER_TYPE_HINTS = [
    ("授权委托书", "授权委托书"),
    ("委托书", "委托书"),
    ("收据", "收据"),
    ("报价单", "报价单"),
    ("对账单", "对账单"),
    ("验资报告", "验资报告"),
    ("资产评估报告", "资产评估报告"),
    ("尽调报告", "尽职调查报告"),
    ("尽职调查", "尽职调查报告"),
    ("承诺函", "承诺函"),
    ("说明函", "说明函"),
    ("通知书", "通知书"),
    ("结清证明", "结清证明"),
    ("还款计划", "还款计划书"),
    ("保单", "保险保单"),
]


def _guess_open_voucher_type(content: str):
    normalized = str(content or "").strip()
    if not normalized:
        return None, 0.0
    for keyword, voucher_type in OPEN_VOUCHER_TYPE_HINTS:
        if keyword in normalized:
            return voucher_type, 0.82
    lines = [line.strip() for line in normalized.splitlines() if line.strip()]
    first_lines = lines[:20]
    type_pattern = re.compile(r"([\u4e00-\u9fa5A-Za-z0-9]{2,20}(?:证明|证书|报告|合同|发票|凭证|执照|章程|明细|流水|清单|函|单))")
    for line in first_lines:
        matched = type_pattern.search(line)
        if matched:
            return matched.group(1), 0.72
    all_matches = type_pattern.findall(normalized[:4000])
    if all_matches:
        counter = {}
        for item in all_matches:
            counter[item] = counter.get(item, 0) + 1
        best = max(counter, key=counter.get)
        return best, min(0.75, 0.58 + 0.03 * counter[best])
    return "未识别凭证", 0.51


async def classify_voucher_content(chat_mdl, content: str, timeout=45):
    import asyncio

    if not content:
        return get_failed_voucher_payload()
    system_prompt, user_prompt = build_voucher_classify_prompt(content)
    raw_response = await asyncio.wait_for(
        chat_mdl.async_chat(
            system_prompt,
            [{"role": "user", "content": user_prompt}],
            {"temperature": 0.01, "max_tokens": 256},
        ),
        timeout=timeout,
    )
    parsed = parse_voucher_classify_result(raw_response)
    if parsed.get("llm_classify_success") and parsed.get("voucher_type") == "其他":
        inferred_type, inferred_confidence = _guess_open_voucher_type(content)
        if inferred_type:
            return {
                "voucher_type": inferred_type,
                "voucher_type_confidence": max(parsed.get("voucher_type_confidence") or 0.0, inferred_confidence),
                "llm_classify_success": True,
                "voucher_type_source": "rule_generated_from_other",
            }
    return normalize_voucher_result_to_payload(parsed)


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
    if confidence is None:
        confidence = 0.0
    return {
        "voucher_type": label,
        "voucher_type_confidence": confidence,
        "llm_classify_success": True,
    }
