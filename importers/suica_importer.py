"""
モバイルSuica 残高ご利用明細PDFインポーター
household.db は1つ上のディレクトリに置く想定
"""

import json
import re
import sqlite3
import sys
from datetime import date
from pathlib import Path

import pdfplumber

DB_PATH = Path(__file__).parent.parent / "household.db"

TYPE_MAP = {
    "繰":    {"skip": True},
    "ｵｰﾄ":  {"category": "現金・カード/電子マネー", "desc": "Suicaチャージ（オート）", "sign": +1},
    "物販":  {"category": "未分類",                  "desc": "Suica物販",              "sign": -1},
    "定":    {"category": "交通費/電車",              "desc": "Suica定期外乗車",        "sign": -1},
    "入":    {"category": "交通費/電車",              "desc": "Suica乗車",              "sign": -1},
    "ﾊﾞｽ等": {"category": "交通費/バス",             "desc": "Suicaバス",              "sign": -1},
}


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            source      TEXT    NOT NULL,
            date        DATE    NOT NULL,
            description TEXT,
            detail      TEXT,
            amount      INTEGER NOT NULL,
            balance     INTEGER,
            category    TEXT,
            memo        TEXT,
            raw_data    TEXT,
            imported_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_tx
        ON transactions(source, date, description, amount, balance)
    """)
    conn.commit()


def infer_year(month: int, issue_year: int, issue_month: int) -> int:
    return issue_year - 1 if month > issue_month else issue_year


def extract_issue_date(pdf_path: Path) -> tuple[int, int]:
    with pdfplumber.open(pdf_path) as pdf:
        text = pdf.pages[0].extract_text() or ""
    m = re.search(r"(\d{4})/(\d{1,2})/\d{1,2}", text)
    if m:
        return int(m.group(1)), int(m.group(2))
    today = date.today()
    return today.year, today.month


def parse_line(line: str) -> dict | None:
    m = re.match(r"^(\d{1,2})\s+(\d{1,2})\s+(.+)$", line.strip())
    if not m:
        return None
    mon_str, day_str, rest = m.group(1), m.group(2), m.group(3)
    amount_m   = re.search(r"([+-]\d[\d,]+)\s*$", rest)
    amount_raw = amount_m.group(1) if amount_m else None
    rest2      = rest[:amount_m.start()].strip() if amount_m else rest
    balance_m  = re.search(r"\\([\d,]+)\s*$", rest2)
    if not balance_m:
        return None
    rest3  = rest2[:balance_m.start()].strip()
    type_m = re.match(r"^(繰|ｵｰﾄ|物販|定|入|ﾊﾞｽ等)\s*(.*)?$", rest3)
    if not type_m:
        return None
    return {
        "month":      int(mon_str),
        "day":        int(day_str),
        "type":       type_m.group(1),
        "station":    type_m.group(2).strip() if type_m.group(2) else "",
        "amount_raw": amount_raw,
    }


def import_suica(pdf_path: str) -> tuple[int, int, int]:
    path = Path(pdf_path)
    issue_year, issue_month = extract_issue_date(path)
    print(f"📅 発行年月: {issue_year}/{issue_month:02d}")

    inserted = skipped_dup = skipped_skip = 0

    with pdfplumber.open(path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    with sqlite3.connect(DB_PATH) as conn:
        init_db(conn)
        for line in text.splitlines():
            parsed    = parse_line(line)
            if not parsed:
                continue
            type_info = TYPE_MAP.get(parsed["type"])
            if not type_info:
                continue
            if type_info.get("skip"):
                skipped_skip += 1
                continue

            year = infer_year(parsed["month"], issue_year, issue_month)
            try:
                d = date(year, parsed["month"], parsed["day"])
            except ValueError:
                continue

            if not parsed["amount_raw"]:
                continue

            amount_val = int(parsed["amount_raw"].replace(",", ""))
            amount     = amount_val
            desc = type_info["desc"]
            if parsed["station"]:
                desc = f"{desc}（{parsed['station']}）"

            try:
                conn.execute("""
                    INSERT INTO transactions
                        (source, date, description, amount, category, raw_data)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, ("suica", d.isoformat(), desc, amount, type_info["category"],
                      json.dumps(parsed, ensure_ascii=False)))
                inserted += 1
            except sqlite3.IntegrityError:
                skipped_dup += 1
        conn.commit()

    return inserted, skipped_dup, skipped_skip


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 suica_importer.py <PDFファイル>")
        sys.exit(1)
    ins, dup, skip = import_suica(sys.argv[1])
    print(f"✅ Suica: {ins}件インポート, {dup}件スキップ（重複）, {skip}件スキップ（繰越）")
