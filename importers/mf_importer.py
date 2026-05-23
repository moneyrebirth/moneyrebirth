"""
MoneyForward 家計簿エクスポートCSVインポーター
household.db は1つ上のディレクトリに置く想定
"""

import csv
import json
import sqlite3
import sys
from datetime import datetime, date
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "household.db"


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
        CREATE TABLE IF NOT EXISTS mf_ids (
            mf_id TEXT PRIMARY KEY
        )
    """)
    conn.commit()


def to_int(val: str) -> int | None:
    v = val.strip().replace(",", "")
    if not v:
        return None
    try:
        return int(float(v))
    except ValueError:
        return None


def import_moneyforward(csv_path: str, skip_transfer: bool = True) -> tuple[int, int, int]:
    path = Path(csv_path)
    inserted = skipped_dup = skipped_transfer = 0

    # Shift_JIS / UTF-8 自動判定
    for enc in ("shift_jis", "utf-8-sig", "utf-8"):
        try:
            with open(path, encoding=enc) as f:
                f.read()
            encoding = enc
            break
        except UnicodeDecodeError:
            continue
    else:
        encoding = "shift_jis"

    with sqlite3.connect(DB_PATH) as conn:
        init_db(conn)
        with open(path, encoding=encoding, errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                mf_id      = row.get("ID", "").strip()
                is_target  = row.get("計算対象", "1").strip()
                date_str   = row.get("日付", "").strip()
                desc       = row.get("内容", "").strip()
                amount_str = row.get("金額（円）", "").strip()
                institution= row.get("保有金融機関", "").strip()
                cat_major  = row.get("大項目", "").strip()
                cat_minor  = row.get("中項目", "").strip()
                memo       = row.get("メモ", "").strip()
                is_transfer= row.get("振替", "0").strip()

                if skip_transfer and (is_target == "0" or is_transfer == "1"):
                    skipped_transfer += 1
                    continue

                try:
                    d = datetime.strptime(date_str, "%Y/%m/%d").date()
                except ValueError:
                    continue

                amount = to_int(amount_str)
                if amount is None:
                    continue

                category = cat_major
                if cat_minor and cat_minor != cat_major and cat_minor != "未分類":
                    category = f"{cat_major}/{cat_minor}"

                if mf_id:
                    exists = conn.execute(
                        "SELECT 1 FROM mf_ids WHERE mf_id = ?", (mf_id,)
                    ).fetchone()
                    if exists:
                        skipped_dup += 1
                        continue

                try:
                    conn.execute("""
                        INSERT INTO transactions
                            (source, date, description, amount, category, memo, detail, raw_data)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, ("moneyforward", d.isoformat(), desc, amount, category, memo, institution,
                          json.dumps(dict(row), ensure_ascii=False)))
                    if mf_id:
                        conn.execute("INSERT INTO mf_ids (mf_id) VALUES (?)", (mf_id,))
                    inserted += 1
                except sqlite3.IntegrityError:
                    skipped_dup += 1
        conn.commit()

    return inserted, skipped_dup, skipped_transfer


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 mf_importer.py <csvファイル> [--include-transfer]")
        sys.exit(1)

    skip = "--include-transfer" not in sys.argv
    ins, dup, transfer = import_moneyforward(sys.argv[1], skip_transfer=skip)
    print(f"✅ MoneyForward: {ins}件インポート, {dup}件スキップ（重複）, {transfer}件スキップ（振替）")
