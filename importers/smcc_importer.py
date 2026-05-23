"""
三井住友カード 利用明細CSVインポーター
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
        CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_tx
        ON transactions(source, date, description, amount)
    """)
    conn.commit()


def to_int(val: str) -> int | None:
    v = val.strip().replace(",", "").replace("　", "").replace(" ", "")
    if not v:
        return None
    try:
        return int(float(v))
    except ValueError:
        return None


def import_smcc(csv_path: str) -> tuple[int, int]:
    path = Path(csv_path)
    inserted = skipped = 0

    with sqlite3.connect(DB_PATH) as conn:
        init_db(conn)
        with open(path, encoding="shift_jis", errors="replace") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or not row[0].strip():
                    continue
                first = row[0].strip()

                d = None
                for fmt in ("%Y/%m/%d", "%y/%m/%d"):
                    try:
                        d = datetime.strptime(first, fmt).date()
                        break
                    except ValueError:
                        if len(first.split("/")[0]) == 2:
                            try:
                                d = datetime.strptime("20" + first, "%Y/%m/%d").date()
                                break
                            except ValueError:
                                pass
                if d is None:
                    continue

                if len(row) < 6:
                    continue

                name   = row[1].strip() if len(row) > 1 else ""
                amount = to_int(row[5]) if len(row) > 5 else None
                note   = row[10].strip() if len(row) > 10 else ""

                if amount is None:
                    amount = to_int(row[2]) if len(row) > 2 else None
                if amount is None:
                    continue

                if amount > 0:
                    amount = -amount

                foreign_info = None
                if len(row) > 6 and row[6].strip():
                    foreign_info = json.dumps({
                        "現地通貨額": row[6].strip(),
                        "略称":      row[7].strip() if len(row) > 7 else "",
                        "換算レート": row[8].strip() if len(row) > 8 else "",
                        "換算日":    row[9].strip() if len(row) > 9 else "",
                    }, ensure_ascii=False)

                try:
                    conn.execute("""
                        INSERT INTO transactions
                            (source, date, description, amount, memo, detail, raw_data)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, ("smcc", d.isoformat(), name, amount, note, foreign_info,
                          json.dumps(row, ensure_ascii=False)))
                    inserted += 1
                except sqlite3.IntegrityError:
                    skipped += 1
        conn.commit()

    return inserted, skipped


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 smcc_importer.py <csvファイル>")
        sys.exit(1)
    ins, skip = import_smcc(sys.argv[1])
    print(f"✅ 三井住友カード: {ins}件インポート, {skip}件スキップ（重複）")
