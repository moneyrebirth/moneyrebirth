"""suica_parser.py — モバイルSuica PDFパーサー"""

import re
import pandas as pd
from datetime import date
from io import BytesIO

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

TYPE_MAP = {
    "繰":    {"skip": True},
    "ｵｰﾄ":  {"category": "現金・カード/電子マネー", "desc": "Suicaチャージ", "sign": +1},
    "物販":  {"category": "未分類",                  "desc": "Suica物販",    "sign": -1},
    "定":    {"category": "交通費/電車",              "desc": "Suica定期外",  "sign": -1},
    "入":    {"category": "交通費/電車",              "desc": "Suica乗車",    "sign": -1},
    "ﾊﾞｽ等": {"category": "交通費/バス",             "desc": "Suicaバス",    "sign": -1},
}


def infer_year(month: int, issue_year: int, issue_month: int) -> int:
    return issue_year - 1 if month > issue_month else issue_year


def parse_line(line: str) -> dict | None:
    m = re.match(r"^(\d{1,2})\s+(\d{1,2})\s+(.+)$", line.strip())
    if not m:
        return None

    mon_str, day_str, rest = m.group(1), m.group(2), m.group(3)

    amount_m   = re.search(r"([+-]\d[\d,]+)\s*$", rest)
    amount_raw = amount_m.group(1) if amount_m else None
    rest2      = rest[:amount_m.start()].strip() if amount_m else rest

    balance_m = re.search(r"\\([\d,]+)\s*$", rest2)
    if not balance_m:
        return None

    rest3    = rest2[:balance_m.start()].strip()
    type_m   = re.match(r"^(繰|ｵｰﾄ|物販|定|入|ﾊﾞｽ等)\s*(.*)?$", rest3)
    if not type_m:
        return None

    return {
        "month":      int(mon_str),
        "day":        int(day_str),
        "type":       type_m.group(1),
        "station":    type_m.group(2).strip() if type_m.group(2) else "",
        "amount_raw": amount_raw,
    }


def parse_suica(raw: bytes) -> pd.DataFrame:
    """Suica PDFをパースしてDataFrameを返す"""
    if not PDFPLUMBER_AVAILABLE:
        return pd.DataFrame(columns=["error"])

    try:
        with pdfplumber.open(BytesIO(raw)) as pdf:
            text        = "\n".join(page.extract_text() or "" for page in pdf.pages)
            issue_year  = date.today().year
            issue_month = date.today().month

            # 発行日取得
            m = re.search(r"(\d{4})/(\d{1,2})/\d{1,2}", text)
            if m:
                issue_year  = int(m.group(1))
                issue_month = int(m.group(2))
    except Exception:
        return pd.DataFrame()

    rows = []
    for line in text.splitlines():
        parsed    = parse_line(line)
        if not parsed:
            continue
        type_info = TYPE_MAP.get(parsed["type"])
        if not type_info or type_info.get("skip"):
            continue

        year = infer_year(parsed["month"], issue_year, issue_month)
        try:
            d = date(year, parsed["month"], parsed["day"])
        except ValueError:
            continue

        if not parsed["amount_raw"]:
            continue
        amount_abs = int(parsed["amount_raw"].replace(",", "").replace("+", ""))
        amount     = type_info["sign"] * amount_abs

        desc = type_info["desc"]
        if parsed["station"]:
            desc = f"{desc}（{parsed['station']}）"

        rows.append({
            "日付":     pd.Timestamp(d),
            "source":   "suica",
            "摘要":     desc,
            "金額":     amount,
            "大項目":   type_info["category"].split("/")[0],
            "カテゴリ": type_info["category"],
        })

    return pd.DataFrame(rows) if rows else pd.DataFrame()
