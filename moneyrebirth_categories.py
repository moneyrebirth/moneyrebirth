"""
moneyrebirth-categories.py

categories.txt を読み込んで辞書として返すユーティリティ。
dashboard.py から import して使う。

使い方:
  from moneyrebirth_categories import load_categories

  CATEGORIES = load_categories()
  # → {"食費": ["外食", "カフェ", ...], "交通費": [...], ...}

categories.txt フォーマット:
  # コメント
  大項目
      中項目1
      中項目2
  別の大項目
      中項目A
"""

from pathlib import Path

CATEGORIES_PATH = Path(__file__).parent / "categories.txt"


def load_categories(path: str | Path | None = None) -> dict[str, list[str]]:
    """
    categories.txt を読み込んで {大項目: [中項目, ...]} の辞書を返す。
    ファイルが存在しない場合は空の辞書を返す。
    """
    fpath = Path(path) if path else CATEGORIES_PATH

    if not fpath.exists():
        print(f"⚠️  {fpath} が見つかりません。")
        print("   python3 moneyrebirth-pickupcategories.py を実行してください。")
        return {}

    categories: dict[str, list[str]] = {}
    current_major: str | None = None

    for line in fpath.read_text(encoding="utf-8").splitlines():
        # コメント・空行スキップ
        if line.startswith("#") or not line.strip():
            continue

        # インデントあり → 中項目
        if line.startswith(("\t", "    ")):
            minor = line.strip()
            if current_major and minor:
                categories[current_major].append(minor)

        # インデントなし → 大項目
        else:
            current_major = line.strip()
            if current_major:
                categories[current_major] = []

    return categories


if __name__ == "__main__":
    cats = load_categories()
    if cats:
        print(f"✅ {len(cats)}大項目 読み込み完了")
        for major, minors in cats.items():
            print(f"  {major} ({len(minors)}件): {', '.join(minors[:3])}{'...' if len(minors) > 3 else ''}")
    else:
        print("❌ カテゴリが読み込めませんでした")
