"""smcc_parser.py — 三井住友カード CSVパーサー"""

import io
import pandas as pd
from datetime import datetime


def parse_smcc(raw: bytes) -> pd.DataFrame:
    """三井住友カード 利用明細CSVをパース"""
    for enc in ("shift_jis", "utf-8-sig", "utf-8"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        return pd.DataFrame()

    rows = []
    for line in text.splitlines():
        cols = [c.strip().strip('"') for c in line.split(",")]
        if not cols or not cols[0]:
            continue

        # 日付行（YY/MM/DD or YYYY/MM/DD）
        date_str = cols[0]
        d = None
        for fmt in ("%Y/%m/%d", "%y/%m/%d"):
            try:
                d = datetime.strptime(date_str, fmt).date()
                break
            except ValueError:
                # 年2桁対応
                if len(date_str.split("/")[0]) == 2:
                    try:
                        d = datetime.strptime("20" + date_str, "%Y/%m/%d").date()
                        break
                    except ValueError:
                        pass
        if d is None:
            continue

        if len(cols) < 6:
            continue

        name = cols[1].strip() if len(cols) > 1 else ""

        # お支払い金額（6列目）を優先
        amount_str = cols[5].replace(",", "").strip() if len(cols) > 5 else ""
        if not amount_str:
            amount_str = cols[2].replace(",", "").strip() if len(cols) > 2 else ""

        try:
            amount_val = int(float(amount_str))
        except ValueError:
            continue

        # 返品はマイナスCSVのままなのでそのまま、通常支出は負に
        if amount_val > 0:
            amount_val = -amount_val

        rows.append({
            "日付":     pd.Timestamp(d),
            "source":   "smcc",
            "摘要":     name,
            "金額":     amount_val,
            "大項目":   "未分類",
            "カテゴリ": "未分類",
        })

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)
