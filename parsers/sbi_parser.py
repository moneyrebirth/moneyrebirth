"""sbi_parser.py — SBI証券 保有証券一覧CSVパーサー"""

import io
import re
import pandas as pd
from datetime import date


SECTION_PATTERNS = {
    "stock": re.compile(r"^株式"),
    "fund":  re.compile(r"^投資信託"),
    "bond":  re.compile(r"^国内債券|^外国債券"),
}

SKIP_PATTERNS = re.compile(r"合計$|^評価額合計|^保有証券一覧$")


def to_num(val: str):
    v = str(val).strip().replace(",", "").replace("+", "").replace("口", "")
    if v in ("", "--", "-", "nan"):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def parse_sbi(raw: bytes) -> pd.DataFrame:
    """SBI証券 保有証券一覧CSVをパースしてポートフォリオDataFrameを返す"""
    for enc in ("shift_jis", "utf-8-sig", "utf-8"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        return pd.DataFrame()

    rows = []
    current_section = ""
    current_atype   = "other"
    in_data         = False
    snapshot_date   = date.today()

    for line in text.splitlines():
        cols  = [c.strip().strip('"') for c in line.split(",")]
        first = cols[0].strip()

        if not any(c for c in cols):
            continue

        if SKIP_PATTERNS.search(first):
            in_data = False
            continue

        if any(pat.search(first) for pat in SECTION_PATTERNS.values()):
            current_section = first
            for atype, pat in SECTION_PATTERNS.items():
                if pat.search(first):
                    current_atype = atype
                    break
            in_data = False
            continue

        if first in ("銘柄コード", "ファンド名", "銘柄"):
            in_data = True
            continue

        if not in_data or current_atype == "other":
            continue

        try:
            if current_atype == "stock":
                name         = cols[1] if len(cols) > 1 else ""
                market_value = to_num(cols[7]) if len(cols) > 7 else None
                gain_loss    = to_num(cols[8]) if len(cols) > 8 else None
            elif current_atype == "fund":
                name         = cols[0]
                market_value = to_num(cols[6]) if len(cols) > 6 else None
                gain_loss    = to_num(cols[7]) if len(cols) > 7 else None
            elif current_atype == "bond":
                name         = cols[0]
                market_value = to_num(cols[8]) if len(cols) > 8 else None
                gain_loss    = None
            else:
                continue

            if not name:
                continue

            rows.append({
                "snapshot_date": snapshot_date,
                "section":       current_section,
                "asset_type":    current_atype,
                "name":          name,
                "market_value":  market_value,
                "gain_loss":     gain_loss,
            })
        except IndexError:
            continue

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)
