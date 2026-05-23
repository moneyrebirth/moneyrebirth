"""mufg_parser.py — 三菱UFJ銀行 CSVパーサー（入出金明細）"""

import io
import pandas as pd


def parse_mufg(raw: bytes) -> pd.DataFrame:
    """三菱UFJ 入出金明細CSVをパース"""
    for enc in ("shift_jis", "utf-8-sig", "utf-8"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        return pd.DataFrame()

    df = pd.read_csv(io.StringIO(text), dtype=str)
    df.columns = df.columns.str.strip()

    if "日付" not in df.columns:
        return pd.DataFrame()

    df["日付"] = pd.to_datetime(df["日付"], errors="coerce")

    def calc_amount(row):
        pay  = str(row.get("支払い金額", "")).replace(",", "").strip()
        recv = str(row.get("預かり金額", "")).replace(",", "").strip()
        if pay and pay != "nan":
            return -int(float(pay))
        if recv and recv != "nan":
            return int(float(recv))
        return None

    df["金額"] = df.apply(calc_amount, axis=1)
    df = df.dropna(subset=["日付", "金額"])
    df["金額"] = df["金額"].astype(int)
    df["摘要"] = df.get("摘要", df.get("内容", pd.Series([""] * len(df)))).fillna("").str.strip()
    df["大項目"] = "未分類"
    df["カテゴリ"] = "未分類"
    df["source"] = "mufg"

    return df[["日付", "source", "摘要", "金額", "大項目", "カテゴリ"]].copy()
