#!/bin/bash
# MoneyRebirth - 一括インポートスクリプト
# 各ディレクトリのCSV/PDFを全て取り込む
# 使い方: bash import_all.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
IMPORTERS="$SCRIPT_DIR/importers"

echo "🚀 MoneyRebirth インポート開始"
echo "================================"

# MoneyForward
if ls "$SCRIPT_DIR"/csv/moneyforward/*.csv 2>/dev/null | head -1 > /dev/null; then
    echo "📊 MoneyForward..."
    for f in "$SCRIPT_DIR"/csv/moneyforward/*.csv; do
        python3 "$IMPORTERS/mf_importer.py" "$f"
    done
fi

# 三菱UFJ 入出金
if ls "$SCRIPT_DIR"/csv/mufg/*.csv 2>/dev/null | head -1 > /dev/null; then
    echo "🏦 三菱UFJ（入出金）..."
    for f in "$SCRIPT_DIR"/csv/mufg/*.csv; do
        python3 "$IMPORTERS/mufg_importer.py" "$f"
    done
fi

# 三菱UFJ 残高
if ls "$SCRIPT_DIR"/csv/mufg_balance/*.csv 2>/dev/null | head -1 > /dev/null; then
    echo "🏦 三菱UFJ（残高）..."
    for f in "$SCRIPT_DIR"/csv/mufg_balance/*.csv; do
        python3 "$IMPORTERS/mufg_balance_importer.py" "$f"
    done
fi

# 三井住友カード
if ls "$SCRIPT_DIR"/csv/smcc/*.csv 2>/dev/null | head -1 > /dev/null; then
    echo "💳 三井住友カード..."
    for f in "$SCRIPT_DIR"/csv/smcc/*.csv; do
        python3 "$IMPORTERS/smcc_importer.py" "$f"
    done
fi

# SBI証券
if ls "$SCRIPT_DIR"/csv/sbi/*.csv 2>/dev/null | head -1 > /dev/null; then
    echo "📈 SBI証券..."
    for f in "$SCRIPT_DIR"/csv/sbi/*.csv; do
        python3 "$IMPORTERS/sbi_portfolio_importer.py" "$f"
    done
fi

# Suica PDF
if ls "$SCRIPT_DIR"/pdf/suica/*.pdf 2>/dev/null | head -1 > /dev/null; then
    echo "🚃 Suica..."
    for f in "$SCRIPT_DIR"/pdf/suica/*.pdf; do
        python3 "$IMPORTERS/suica_importer.py" "$f"
    done
fi

echo "================================"
echo "✅ インポート完了!"
