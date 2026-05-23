"""
detector.py — アップロードファイルのフォーマット自動判定

対応フォーマット:
  - MoneyForward CSV
  - 三菱UFJ銀行 CSV
  - 三井住友カード CSV
  - SBI証券 CSV
  - モバイルSuica PDF
"""

import io
import re


def detect_format(filename: str, raw: bytes) -> str:
    """
    ファイル名と中身からフォーマットを判定。
    Returns: 'mf' | 'mufg' | 'smcc' | 'sbi' | 'suica' | 'unknown'
    """
    fname = filename.lower()

    # PDF → Suica
    if fname.endswith(".pdf"):
        return "suica"

    # CSV の中身を確認
    for enc in ("shift_jis", "utf-8-sig", "utf-8"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        return "unknown"

    # 先頭数行を確認
    head = text[:500]

    if "計算対象" in head and "大項目" in head:
        return "mf"
    if "お預かり残高" in head or ("表示期間" in head and "お名前" in head):
        return "mufg_balance"
    if "摘要内容" in head and "支払い金額" in head and "預かり金額" in head:
        return "mufg"
    if "お預かり残高" in head or "外貨定期預金" in head:
        return "mufg_balance"
    if "銘柄コード" in head or "保有証券一覧" in head or "投資信託" in head and "口数" in head:
        return "sbi"
    if "ご利用金額" in head and "支払" in head and "今回" in head:
        return "smcc"
    # SMCC: 1行目がカード番号形式（****を含む）で2行目が日付
    if "****" in head and re.search(r'\d{4}/\d{2}/\d{2}', head):
        return "smcc"

    return "unknown"


FORMAT_LABELS = {
    "mf":           "💚 MoneyForward",
    "mufg":         "🏦 三菱UFJ銀行（入出金）",
    "mufg_balance": "🏦 三菱UFJ銀行（残高）",
    "smcc":         "💳 三井住友カード",
    "sbi":          "📈 SBI証券",
    "suica":        "🚃 モバイルSuica",
    "unknown":      "❓ 不明",
}
