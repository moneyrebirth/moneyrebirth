"""
moneyrebirth-pickupcategories.py

household.db の transactions テーブルから
カテゴリ（大項目/中項目）を抽出して categories.txt を生成する。

使い方:
  python3 moneyrebirth-pickupcategories.py

出力: categories.txt（同じディレクトリ）

categories.txt フォーマット:
  # コメント行（#で始まる行は無視）
  大項目
      中項目1
      中項目2
  別の大項目
      中項目A
"""

import sqlite3
from collections import defaultdict
from pathlib import Path

DB_PATH  = Path(__file__).parent / "household.db"
OUT_PATH = Path(__file__).parent / "categories.txt"


def extract_categories() -> dict[str, list[str]]:
    """
    DBのcategoryカラム（"大項目/中項目" 形式）から
    大項目→中項目リストの辞書を作成。
    """
    categories = defaultdict(set)

    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("""
            SELECT DISTINCT category
            FROM transactions
            WHERE category IS NOT NULL AND category != ''
            ORDER BY category
        """).fetchall()

    for (cat,) in rows:
        cat = cat.strip()
        if "/" in cat:
            major, minor = cat.split("/", 1)
            categories[major.strip()].add(minor.strip())
        else:
            # 中項目なし（大項目のみ）
            categories[cat].add("")

    # setをソート済みリストに変換、空文字を除外
    return {
        major: sorted(m for m in minors if m)
        for major, minors in sorted(categories.items())
    }


def write_categories(categories: dict[str, list[str]]) -> None:
    """categories.txt に書き出す"""
    lines = [
        "# MoneyRebirth カテゴリ設定ファイル",
        "# - '#' で始まる行はコメント",
        "# - 大項目は行頭から記述",
        "# - 中項目はタブまたは4スペースでインデント",
        "# - 手動で追加・編集・削除可能",
        "",
    ]

    for major, minors in categories.items():
        lines.append(major)
        for minor in minors:
            lines.append(f"    {minor}")
        lines.append("")  # 大項目間の空行

    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    print(f"📂 DB: {DB_PATH}")
    cats = extract_categories()

    if not cats:
        print("❌ カテゴリが見つかりません。先にCSVをインポートしてください。")
        exit(1)

    write_categories(cats)

    total_major = len(cats)
    total_minor = sum(len(v) for v in cats.values())
    print(f"✅ {total_major}大項目 / {total_minor}中項目を抽出")
    print(f"📄 出力: {OUT_PATH}")
    print()
    print("--- プレビュー ---")
    for major, minors in cats.items():
        print(f"  {major}: {', '.join(minors) if minors else '（中項目なし）'}")
