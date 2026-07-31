"""Dev tool: download flag PNGs from flagcdn.com into assets/flags/.

Usage: python tools/fetch_flags.py
"""

import sys
from pathlib import Path
from urllib.request import urlopen

_SRC = "https://flagcdn.com/w40/{code}.png"
_OUT = Path(__file__).resolve().parent.parent / "assets" / "flags"

_RESERVED = {"AA"} | {f"Q{c}" for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"} \
    | {f"X{c}" for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"} | {"ZZ"}


def main():
    _OUT.mkdir(parents=True, exist_ok=True)
    codes = [
        f"{a}{b}".lower()
        for a in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for b in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        if f"{a}{b}" not in _RESERVED
    ]
    ok = 0
    missing = []
    for code in codes:
        dest = _OUT / f"{code}.png"
        if dest.exists():
            ok += 1
            continue
        try:
            with urlopen(_SRC.format(code=code), timeout=20) as r:
                data = r.read()
            if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) > 40:
                dest.write_bytes(data)
                ok += 1
            else:
                missing.append(code)
        except Exception:
            missing.append(code)
    print(f"done: {ok} flags saved, missing: {missing}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
