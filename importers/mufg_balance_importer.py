"""
三菱UFJ お預かり残高CSVインポーター
household.db は1つ上のディレクトリに置く想定
"""

import csv
import json
import re
import sqlite3
import sys
from datetime import date
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "household.db"


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS portfolios (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_date DATE    NOT NULL,
            section       TEXT    NOT NULL,
            asset_type    TEXT    NOT NULL,
            nisa          INTEGER NOT NULL DEFAULT 0,
            code          TEXT,
            name          TEXT    NOT NULL,
            quantity      REAL,
            unit_price    REAL,
            current_price REAL,
            cost          REAL,
            market_value  REAL,
            gain_loss     REAL,
            extra         TEXT,
            raw_data      TEXT,
            imported_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_portfolio_unique
        ON portfolios(snapshot_date, section, COALESCE(code,''), name)
    """)
    conn.commit()


def parse_year_month(val: str) -> date | None:
    val = val.strip()
    m = re.match(r"(\d{4})年(\d{1,2})月", val)
    if m:
        return date(int(m.group(1)), int(m.group(2)), 1)
    return None


def to_int(val: str) -> int | None:
    v = val.strip().replace(",", "").replace("+", "").replace("△", "-")
    if not v:
        return None
    try:
        return int(float(v))
    except ValueError:
        return None


def import_mufg_balance(csv_path: str) -> tuple[int, int]:
    path = Path(csv_path)
    inserted = skipped = 0

    with open(path, encoding="shift_jis", errors="replace") as f:
        reader = csv.reader(f)
        rows = list(reader)

    month_row_idx = None
    months = []
    for i, row in enumerate(rows):
        if len(row) > 4 and re.match(r"\d{4}年\d{1,2}月", row[4].strip()):
            month_row_idx = i
            months = [parse_year_month(c) for c in row[4:] if parse_year_month(c)]
            break

    if not months:
        print("❌ 月ヘッダー行が見つかりません")
        sys.exit(1)

    valid_months = months[:-1]
    print(f"📅 対象月: {valid_months[0]} 〜 {valid_months[-1]}")

    last_product = last_currency = last_type = last_currency2 = ""
    records = []

    for row in rows[month_row_idx + 1:]:
        if not row or not any(c.strip() for c in row):
            continue
        if row[0].strip().startswith("お預かり残高"):
            break

        col0 = row[0].strip().strip('"') if len(row) > 0 else ""
        col1 = row[1].strip().strip('"') if len(row) > 1 else ""
        col2 = row[2].strip().strip('"') if len(row) > 2 else ""
        col3 = row[3].strip().strip('"') if len(row) > 3 else ""

        if col0: last_product   = col0
        if col1: last_currency  = col1
        if col2: last_type      = col2
        if col3: last_currency2 = col3

        amounts = row[4:4 + len(valid_months)]
        if not amounts:
            continue

        parts = [p for p in [last_product, last_currency, last_type, last_currency2] if p]
        name    = " / ".join(parts)
        section = f"三菱UFJ / {last_product}{last_currency}"

        for i, month_date in enumerate(valid_months):
            if i >= len(amounts):
                break
            val = to_int(amounts[i])
            if val is None:
                continue
            records.append({"snapshot_date": month_date, "section": section, "name": name, "market_value": val})

    with sqlite3.connect(DB_PATH) as conn:
        init_db(conn)
        for r in records:
            try:
                conn.execute("""
                    INSERT INTO portfolios
                        (snapshot_date, section, asset_type, nisa, name, market_value, raw_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (r["snapshot_date"].isoformat(), r["section"], "bank", 0, r["name"],
                      r["market_value"], json.dumps(r, ensure_ascii=False, default=str)))
                inserted += 1
            except sqlite3.IntegrityError:
                skipped += 1
        conn.commit()

    return inserted, skipped


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 mufg_balance_importer.py <csvファイル>")
        sys.exit(1)
    ins, skip = import_mufg_balance(sys.argv[1])
    print(f"✅ 三菱UFJ残高: {ins}件インポート, {skip}件スキップ（重複）")
