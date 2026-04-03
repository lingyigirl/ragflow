import pytest


def test_parse_voucher_result_success_and_clamp_confidence():
    from rag.utils.voucher_classifier import parse_voucher_classify_result

    raw = '{"label":"身份证","confidence":1.8}'
    res = parse_voucher_classify_result(raw)
    assert res["llm_classify_success"] is True
    assert res["voucher_type"] == "身份证"
    assert res["voucher_type_confidence"] == 1.0


def test_parse_voucher_result_invalid_label_returns_null():
    from rag.utils.voucher_classifier import parse_voucher_classify_result

    raw = '{"label":"未知证件","confidence":0.9}'
    res = parse_voucher_classify_result(raw)
    assert res["llm_classify_success"] is False
    assert res["voucher_type"] is None
    assert res["voucher_type_confidence"] is None


def test_build_voucher_content_only_uses_chunk_text():
    from rag.utils.voucher_classifier import build_voucher_classify_content

    chunks = [
        {"content_with_weight": "姓名：张三\n公民身份号码：110101199001010011"},
        {"content_with_weight": "签发机关：北京市公安局"},
    ]
    text = build_voucher_classify_content(chunks, max_chars=50)
    assert "公民身份号码" in text
    assert len(text) <= 50
