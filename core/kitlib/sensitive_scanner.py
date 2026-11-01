"""Sensitive-zone scanner and redactor (spec §3 privacy.never_persist, §7, E07).

- PATTERN rules: the match itself is replaced by [REDACTED:<category>].
- ZONE rules: a keyword hit redacts the whole sentence with the core redacted note.
Findings never include the matched text, only category + count. Input is NFC-normalised first.
"""
import json
import re

from .text_normalize import normalize

REDACTED_NOTE = "Có nội dung nhạy cảm, không transcribe chi tiết."
_NB = r"(?<![A-Za-z0-9])"  # non-alnum boundary (\b fails after '_', e.g. DB_PASSWORD)
_WB = r"(?<![A-Za-z0-9_])"  # word boundary incl. underscore, so redaction markers like salary_and_bonus never re-match

PATTERN_RULES = [
    ("credentials_tokens_api_keys", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?(-----END [A-Z ]*PRIVATE KEY-----|$)")),
    ("credentials_tokens_api_keys", re.compile(r"https?://hooks\.slack\.com/services/\S+")),
    ("credentials_tokens_api_keys", re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}(\.[A-Za-z0-9_-]{5,})?")),
    ("credentials_tokens_api_keys", re.compile(
        _NB + r"(sk[-_](live|test)?[-_]?[A-Za-z0-9_-]{8,}|gh[pousr]_[A-Za-z0-9]{20,}|xox[abpe]-[A-Za-z0-9-]{10,}"
        r"|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{30,}|glpat-[A-Za-z0-9_-]{20,})")),
    ("credentials_tokens_api_keys", re.compile(r"(?i)" + _NB + r"bearer\s+[A-Za-z0-9._-]{16,}")),
    ("credentials_tokens_api_keys", re.compile(
        r"(?i)" + _NB + r"[A-Za-z0-9_-]*(api[_ -]?key|access[_ -]?token|secret|password|passwd|mật khẩu|private[_ -]?key|token)"
        r"[A-Za-z0-9_-]*\s*[:=]\s*[\"']?\S{4,}")),
    ("employee_personal_data", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("employee_personal_data", re.compile(r"(?<!\d)(?:\+?84|\(\+84\)\s?|0)(?:[\s.-]?\d){9,10}(?!\d)")),
    ("employee_personal_data", re.compile(r"(?i)" + _NB + r"(CCCD|CMND|căn cước|passport|hộ chiếu)\b\s*[:#]?\s*\d{6,}")),
]

ZONE_RULES = [
    ("salary_and_bonus", re.compile(
        r"(?i)" + _WB + r"(lương|salary|bonus|thưởng|payroll|thu nhập|compensation|phụ cấp)(?![A-Za-z0-9_])")),
    ("employee_assessments", re.compile(
        r"(?i)(đánh giá nhân sự|đánh giá hiệu suất|đánh giá năng lực|performance review|xếp loại|"
        r"rating nhân viên|kỷ luật|sa thải|cho nghỉ việc|EKS của|điểm EKS|review nhân sự)")),
    ("unauthorized_bod_content", re.compile(r"(?i)" + _WB + r"(BOD|hội đồng quản trị|board of directors)(?![A-Za-z0-9_])")),
]

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?\n])\s+")


def scan(text):
    """Return (redacted_text, findings:list[{category,count}], detected:bool)."""
    text = normalize(text)
    counts = {}
    redacted = text
    for category, rx in PATTERN_RULES:
        redacted, n = rx.subn(f"[REDACTED:{category}]", redacted)
        if n:
            counts[category] = counts.get(category, 0) + n

    out = []
    for sentence in _SENTENCE_SPLIT.split(redacted):
        hit = next((cat for cat, rx in ZONE_RULES if rx.search(sentence)), None)
        if hit:
            counts[hit] = counts.get(hit, 0) + 1
            out.append(f"[REDACTED:{hit}] {REDACTED_NOTE}")
        else:
            out.append(sentence)
    redacted = " ".join(out).strip()

    findings = [{"category": c, "count": n} for c, n in sorted(counts.items())]
    return redacted, findings, bool(findings)


def scan_json_blob(obj):
    """Scan a serialised JSON object; returns (findings, detected) — used as the persist gate."""
    _, findings, detected = scan(json.dumps(obj, ensure_ascii=False))
    return findings, detected
