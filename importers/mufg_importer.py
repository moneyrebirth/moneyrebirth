"""
三菱UFJ銀行 入出金明細CSVインポーター
household.db は1つ上のディレクトリに置く想定
"""

import csv
import sqlite3
import json
import re
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "household.db"

def init_db(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            source      TEXT NOT NULL,
            date        DATE NOT NULL,
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

def parse_amount(val: str) -> int | None:
    val = val.strip()
    if not val:
        return None
    return int(val.replace(",", ""))

def import_mufg(csv_path: str) -> tuple[int, int]:
    path = Path(csv_path)
    inserted = skipped = 0

    with sqlite3.connect(DB_PATH) as conn:
        init_db(conn)
        with open(path, encoding="shift_jis", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                date_str = row.get("日付", "").strip().strip('"')
                if not date_str:
                    continue
                try:
                    date = datetime.strptime(date_str, "%Y/%m/%d").date()
                except ValueError:
                    continue

                pay  = parse_amount(row.get("支払い金額", ""))
                recv = parse_amount(row.get("預かり金額", ""))
                bal  = parse_amount(row.get("差引残高", ""))
                desc = row.get("摘要", "").strip()
                detail = row.get("摘要内容", "").strip()
                memo = row.get("メモ", "").strip()

                if pay is not None:
                    amount = -pay
                elif recv is not None:
                    amount = recv
                else:
                    continue

                try:
                    conn.execute("""
                        INSERT INTO transactions
                            (source, date, description, detail, amount, balance, memo, raw_data)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, ("mufg", date.isoformat(), desc, detail, amount, bal, memo,
                          json.dumps(dict(row), ensure_ascii=False)))
                    inserted += 1
                except sqlite3.IntegrityError:
                    skipped += 1
        conn.commit()

    return inserted, skipped

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 mufg_importer.py <csvファイル>")
        sys.exit(1)
    ins, skip = import_mufg(sys.argv[1])
    print(f"✅ 三菱UFJ: {ins}件インポート, {skip}件スキップ（重複）")
