"""
mufg_balance_parser.py — 三菱UFJ お預かり残高CSVパーサー

フォーマット:
  - 横持ち（月が列）→ 縦持ちに変換
  - 円貨・外貨（円換算済）両対応
  - 合計行は自動除外
"""

import io
import re
import pandas as pd
from datetime import date


def parse_year_month(val: str) -> date | None:
    """'2025年3月' → date(2025, 3, 1)"""
    val = val.strip()
    m = re.match(r"(\d{4})年(\d{1,2})月", val)
    if m:
        return date(int(m.group(1)), int(m.group(2)), 1)
    return None


def to_int(val: str) -> int | None:
    v = str(val).strip().replace(",", "").replace("+", "").replace("△", "-")
    if not v or v in ("--", "-", "nan"):
        return None
    try:
        return int(float(v))
    except ValueError:
        return None


def parse_mufg_balance(raw: bytes) -> pd.DataFrame:
    """
    三菱UFJ残高CSVをパースして月次残高DataFrameを返す。

    返り値カラム:
      snapshot_date, section, asset_type, name, market_value
    """
    for enc in ("shift_jis", "utf-8-sig", "utf-8"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        return pd.DataFrame()

    lines = text.splitlines()

    # ── 月ヘッダー行を探す ──
    months = []
    month_row_idx = None
    for i, line in enumerate(lines):
        cols = [c.strip().strip('"') for c in line.split(",")]
        # 年月パターンが4列目以降に出てくる行
        parsed = [parse_year_month(c) for c in cols[4:] if parse_year_month(c)]
        if len(parsed) >= 3:
            month_row_idx = i
            months = [parse_year_month(c) for c in cols[4:] if parse_year_month(c)]
            break

    if not months:
        return pd.DataFrame()

    # 前月比列を除外（最後の月）
    valid_months = months[:-1]

    # ── データ行を処理 ──
    last_product  = ""
    last_currency = ""
    last_type     = ""
    last_currency2= ""

    rows = []

    for line in lines[month_row_idx + 1:]:
        cols  = [c.strip().strip('"') for c in line.split(",")]
        first = cols[0].strip()

        # 終了判定
        if first.startswith("お預かり残高"):
            break

        # 空行スキップ
        if not any(c for c in cols):
            continue

        # 合計行スキップ
        if "合計" in first:
            continue

        # 各列を引き継ぎ
        if cols[0].strip(): last_product   = cols[0].strip()
        if len(cols) > 1 and cols[1].strip(): last_currency  = cols[1].strip()
        if len(cols) > 2 and cols[2].strip(): last_type      = cols[2].strip()
        if len(cols) > 3 and cols[3].strip(): last_currency2 = cols[3].strip()

        # 金額列
        amounts = cols[4:4 + len(valid_months)]
        if not amounts:
            continue

        # 名称
        parts = [p for p in [last_product, last_currency, last_type, last_currency2] if p]
        name  = " / ".join(parts)
        section = f"三菱UFJ / {last_product}{last_currency}"

        for i, month_date in enumerate(valid_months):
            if i >= len(amounts):
                break
            val = to_int(amounts[i])
            if val is None or val == 0:
                continue

            rows.append({
                "snapshot_date": pd.Timestamp(month_date),
                "section":       section,
                "asset_type":    "bank",
                "name":          name,
                "market_value":  float(val),
                "gain_loss":     None,
            })

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)
