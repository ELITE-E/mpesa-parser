import re

def normalize_name(raw_string: str) -> str:
    """Normalizes messy M-Pesa transaction strings into canonical entities."""
    if not raw_string:
        return ""

    normalized = _remove_bracketed_references(raw_string)
    normalized = _reformat_paybill_pattern(normalized)
    normalized = _reformat_till_pattern(normalized)
    normalized = _extract_p2p_customer_name(normalized)
    return _sanitize_delimiters_and_spacing(normalized)

def _remove_bracketed_references(text: str) -> str:
    return re.sub(r"\(Ref:.*?\)", "", text)

def _reformat_paybill_pattern(text: str) -> str:
    paybill_pattern = r"PayBill\s*-\s*(\d+)\s*-\s*(.*)"
    match = re.search(paybill_pattern, text, re.IGNORECASE)
    if match:
        bill_id, name = match.groups()
        return f"{name.strip()} {bill_id.strip()}"
    return text

def _reformat_till_pattern(text: str) -> str:
    till_pattern = r"(?:Till|Buy\s*Goods)\s*-\s*(\d+)\s*-\s*(.*)"
    match = re.search(till_pattern, text, re.IGNORECASE)
    if match:
        till_id, name = match.groups()
        return f"{name.strip()} {till_id.strip()}"
    return text

def _extract_p2p_customer_name(text: str) -> str:
    p2p_pattern = r"(?:Sent\s+to|Received\s+from)\s+(?:\+?254|0)?\d{9}\s*-?\s*(.*)"
    match = re.search(p2p_pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text

def _sanitize_delimiters_and_spacing(text: str) -> str:
    text = text.replace("-", " ")
    return re.sub(r"\s+", " ", text).strip()
