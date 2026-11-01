"""Shared text normalisation: NFC (macOS/Sheets often emit NFD Vietnamese) + strip zero-width/invisible chars."""
import re
import unicodedata

_INVISIBLE = re.compile(r"[​‌‍⁠﻿­]")


def normalize(text):
    if text is None:
        return ""
    return _INVISIBLE.sub("", unicodedata.normalize("NFC", str(text)))
