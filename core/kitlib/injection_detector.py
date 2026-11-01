"""Untrusted-instruction (prompt injection) detector — spec §7, E08.

Content from sources is data. This module flags instruction-like phrases so the agent
records a warning and does NOT act. Warnings carry pattern id + position only.
Run it on RAW text (before redaction) so a sensitive sentence can't hide an instruction.
"""
import re

from .text_normalize import normalize

_NAME = r"(anh |chị |sếp |mr\.? |ms\.? )?(tom|pm|owner|manager|lead|sếp|quản lý)"

PATTERNS = [
    ("override_instructions", re.compile(
        r"(?i)\b(ignore|disregard|forget)\b.{0,20}\b(previous|prior|above|all|your)\b.{0,20}\b(instructions?|rules?|policy|policies)\b"
        r"|bỏ qua (mọi |tất cả |các )?(hướng dẫn|chỉ dẫn|quy tắc|rule|luật)")),
    ("skip_gate_or_approval", re.compile(
        r"(?i)\b(skip|bypass|remove|disable|ignore)\b.{0,15}\b(gates?|approvals?|reviews?|safety|human)\b"
        r"|bỏ (qua )?(bước |khâu )?(gate|duyệt|phê duyệt|review)|không cần " + _NAME + r"? ?(phải )?(duyệt|review|phê duyệt|gate)|khỏi cần duyệt")),
    ("demand_external_write", re.compile(
        r"(?i)\b(create|open|make|file|add)\b.{0,15}\b(tasks?|tickets?|issues?)\b.{0,25}\b(now|immediately|right away|in asana|in jira)\b"
        r"|(hãy |vui lòng |cứ )?(tạo|mở|cập nhật) (task|ticket|việc|trạng thái)( này| mới)?( trong asana| trên asana)?( ngay| luôn| lập tức)?"
        r"(?=.*(asana|ngay|luôn|lập tức|jira))")),
    ("demand_exfiltration", re.compile(
        r"(?i)\b(send|post|forward|share|email|dm)\b.{0,15}\b(all|entire|whole|every|this|the)\b.{0,25}\b(data|feedback|files?|records?|lists?|sheet)\b"
        r"|gửi (toàn bộ|tất cả|hết|cả|cho tôi)\b|chia sẻ (toàn bộ|tất cả)|forward (toàn bộ|tất cả)")),
    ("role_hijack", re.compile(
        r"(?i)\byou are now\b|\bact as (the |an? )?(admin|system|developer|owner)\b|\bsystem prompt\b|\bnew instructions?:|\bai agent:")),
    ("fake_approval_claim", re.compile(
        r"(?i)\b" + _NAME + r"\b.{0,20}\b(already\s+)?approved\b|\bapproved by " + _NAME
        + r"|đã (được )?" + _NAME + r"? ?(duyệt|phê duyệt|approve)( rồi)?"
        + r"|mark(ed)? (it |this )?as approved|approved_by\s*[:=]")),
]


def detect(text, part_id="?"):
    """Return list of warnings [{pattern_id, part_id, position}] — no quoted text."""
    text = normalize(text)
    warnings = []
    for pattern_id, rx in PATTERNS:
        for m in rx.finditer(text):
            warnings.append({"pattern_id": pattern_id, "part_id": part_id, "position": m.start()})
    return warnings
