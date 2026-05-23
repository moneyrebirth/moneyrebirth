"""mf_parser.py — MoneyForward CSVパーサー"""

import io
import pandas as pd


def parse_mf(raw: bytes) -> pd.DataFrame:
    """
    MoneyForward CSVをパースしてDataFrameを返す。
    振替（計算対象=0）は除外。
    """
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

    required = ["日付", "内容", "金額（円）", "大項目", "中項目"]
    for col in required:
        if col not in df.columns:
            return pd.DataFrame()

    # 振替除外
    if "計算対象" in df.columns:
        df = df[df["計算対象"].str.strip() == "1"]

    df["日付"] = pd.to_datetime(df["日付"], errors="coerce")
    df["金額"] = df["金額（円）"].str.replace(",", "").str.strip()
    df["金額"] = pd.to_numeric(df["金額"], errors="coerce")
    df = df.dropna(subset=["日付", "金額"])
    df["金額"] = df["金額"].astype(int)

    df["カテゴリ"] = df.apply(
        lambda r: f"{r['大項目']}/{r['中項目']}"
        if str(r["中項目"]).strip() and str(r["中項目"]).strip() != str(r["大項目"]).strip()
        else str(r["大項目"]),
        axis=1
    )
    df["大項目"] = df["大項目"].str.strip()
    df["source"] = "moneyforward"
    df["摘要"] = df["内容"].str.strip()

    return df[["日付", "source", "摘要", "金額", "大項目", "カテゴリ"]].copy()
