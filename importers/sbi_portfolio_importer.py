"""
SBI証券 保有証券一覧CSVインポーター
household.db は1つ上のディレクトリに置く想定
"""

import csv
import json
import re
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "household.db"

SECTION_PATTERNS = {
    "stock": re.compile(r"^株式"),
    "fund":  re.compile(r"^投資信託"),
    "bond":  re.compile(r"^国内債券|^外国債券"),
}

SKIP_PATTERNS = re.compile(r"合計$|^評価額合計|^保有証券一覧$")


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


def to_num(val: str) -> float | None:
    if val is None:
        return None
    v = str(val).strip().replace(",", "").replace("+", "").replace("口", "")
    if v in ("", "--", "-"):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def detect_asset_type(section: str) -> str:
    for atype, pat in SECTION_PATTERNS.items():
        if pat.search(section):
            return atype
    return "other"


def is_nisa(section: str) -> int:
    return 1 if "NISA" in section or "旧NISA" in section else 0


def parse_stock_row(row, section):
    return dict(code=row[0].strip() or None, name=row[1].strip(),
                quantity=to_num(row[2]), unit_price=to_num(row[4]),
                current_price=to_num(row[5]), cost=to_num(row[6]),
                market_value=to_num(row[7]), gain_loss=to_num(row[8]), extra=None)

def parse_fund_row(row, section):
    extra = {}
    if len(row) >= 9:
        extra["分配金受取方法"] = row[8].strip()
    return dict(code=None, name=row[0].strip(),
                quantity=to_num(row[1]), unit_price=to_num(row[3]),
                current_price=to_num(row[4]), cost=to_num(row[5]),
                market_value=to_num(row[6]), gain_loss=to_num(row[7]),
                extra=json.dumps(extra, ensure_ascii=False) if extra else None)

def parse_bond_row(row, section):
    extra = {"利率": row[1].strip(), "償還日": row[2].strip(), "利払日": row[3].strip()}
    return dict(code=None, name=row[0].strip(),
                quantity=to_num(row[4]), unit_price=to_num(row[5]),
                current_price=None, cost=None, market_value=to_num(row[8]),
                gain_loss=None, extra=json.dumps(extra, ensure_ascii=False))

PARSERS = {"stock": parse_stock_row, "fund": parse_fund_row, "bond": parse_bond_row}


def import_sbi_portfolio(csv_path: str, snapshot_date: date | None = None) -> tuple[int, int]:
    path = Path(csv_path)
    if snapshot_date is None:
        snapshot_date = date.fromtimestamp(path.stat().st_mtime)

    inserted = skipped = 0
    current_section = ""
    current_atype   = "other"
    current_nisa    = 0
    in_data         = False

    with sqlite3.connect(DB_PATH) as conn:
        init_db(conn)
        with open(path, encoding="shift_jis", errors="replace") as f:
            reader = csv.reader(f)
            for raw_row in reader:
                if not any(c.strip() for c in raw_row):
                    continue
                first = raw_row[0].strip()

                if SKIP_PATTERNS.search(first):
                    in_data = False
                    continue

                if any(pat.search(first) for pat in SECTION_PATTERNS.values()):
                    current_section = first
                    current_atype   = detect_asset_type(first)
                    current_nisa    = is_nisa(first)
                    in_data         = False
                    continue

                if first in ("銘柄コード", "ファンド名", "銘柄"):
                    in_data = True
                    continue

                if not in_data or current_atype == "other":
                    continue

                parser = PARSERS.get(current_atype)
                if parser is None:
                    continue

                try:
                    fields = parser(raw_row, current_section)
                except IndexError:
                    continue

                if not fields["name"]:
                    continue

                try:
                    conn.execute("""
                        INSERT INTO portfolios
                            (snapshot_date, section, asset_type, nisa,
                             code, name, quantity, unit_price, current_price,
                             cost, market_value, gain_loss, extra, raw_data)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """, (snapshot_date.isoformat(), current_section, current_atype, current_nisa,
                          fields["code"], fields["name"], fields["quantity"], fields["unit_price"],
                          fields["current_price"], fields["cost"], fields["market_value"],
                          fields["gain_loss"], fields["extra"],
                          json.dumps(raw_row, ensure_ascii=False)))
                    inserted += 1
                except sqlite3.IntegrityError:
                    skipped += 1
        conn.commit()

    return inserted, skipped


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 sbi_portfolio_importer.py <csvファイル> [YYYY-MM-DD]")
        sys.exit(1)

    snap = None
    if len(sys.argv) >= 3:
        snap = date.fromisoformat(sys.argv[2])

    ins, skip = import_sbi_portfolio(sys.argv[1], snap)
    print(f"✅ SBI証券ポートフォリオ: {ins}件インポート, {skip}件スキップ（重複）")
