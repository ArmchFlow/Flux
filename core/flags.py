"""Country-flag extraction for server names.

Flags arrive in subscription data either as emoji (regional indicator
pairs, e.g. "Poland \U0001F1F5\U0001F1F1") or as textual country codes
(e.g. "[HK] 01", "(JP) 02", "US Los Angeles"). The Qt item-view text
path does not perform font fallback for emoji, so the UI renders flags
in a dedicated label column instead. This module locates the flag and
splits it off the name.
"""

import re
from typing import Tuple

_FLAG_BASE = 0x1F1E6  # regional indicator A

_RI_PAIR_RE = re.compile("[\U0001F1E6-\U0001F1FF]{2}")
_START_CODE_RE = re.compile(
    r"^(?:\[([A-Za-z]{2})\]|\(([A-Za-z]{2})\)|([A-Za-z]{2})\s+)")
_END_CODE_RE = re.compile(r"\s*(?:\[([A-Za-z]{2})\]$|\(([A-Za-z]{2})\)$)")

# Codes that never map to real countries (ISO 3166-1 reserved/user-assigned).
_RESERVED_CODES = {"AA"} | {f"Q{c}" for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"} \
    | {f"X{c}" for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"} | {"ZZ"}


def _code_to_flag(code: str) -> str:
    code = code.strip().upper()
    if len(code) != 2 or not code.isascii() or not code.isalpha():
        return ""
    if code in _RESERVED_CODES:
        return ""
    return chr(_FLAG_BASE + ord(code[0]) - ord("A")) + chr(
        _FLAG_BASE + ord(code[1]) - ord("A"))


def emoji_to_code(flag_emoji: str) -> str:
    """Convert an emoji flag (regional indicator pair) to its 2-letter code."""
    if len(flag_emoji) != 2:
        return ""
    a = ord(flag_emoji[0]) - _FLAG_BASE
    b = ord(flag_emoji[1]) - _FLAG_BASE
    if not (0 <= a < 26 and 0 <= b < 26):
        return ""
    return chr(ord("A") + a) + chr(ord("A") + b)


def extract_flag(name: str) -> Tuple[str, str]:
    """Return (flag_emoji, cleaned_name).

    Recognizes an emoji flag pair anywhere in the name, and textual
    country codes in brackets or at the start/end ("[HK]", "(JP)",
    "US Name"). Returns ("", name) when nothing is found.
    """
    if not name:
        return "", name

    m = _RI_PAIR_RE.search(name)
    if m:
        flag = m.group(0)
        cleaned = (name[:m.start()] + name[m.end():]).strip()
        return flag, cleaned or name

    m = _START_CODE_RE.match(name)
    if m:
        code = next((g for g in m.groups() if g), "")
        flag = _code_to_flag(code)
        if flag:
            cleaned = name[m.end():].strip()
            return flag, cleaned or name

    m = _END_CODE_RE.search(name)
    if m:
        code = next((g for g in m.groups() if g), "")
        flag = _code_to_flag(code)
        if flag:
            cleaned = (name[:m.start()] + name[m.end():]).strip()
            return flag, cleaned or name

    return "", name
