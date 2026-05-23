"""
MoneyRebirth v2 - Cloud版
複数金融機関のCSV/PDFをアップロードして家計簿＋資産を可視化

⚠️ デモ版: データはセッション終了時に消去されます
"""

import pandas as pd
import streamlit as st
import plotly.express as px

from parsers.detector import detect_format, FORMAT_LABELS
from parsers.mf_parser import parse_mf
from parsers.mufg_parser import parse_mufg
from parsers.mufg_balance_parser import parse_mufg_balance
from parsers.smcc_parser import parse_smcc
from parsers.sbi_parser import parse_sbi
from parsers.suica_parser import parse_suica, PDFPLUMBER_AVAILABLE

st.set_page_config(
    page_title="MoneyRebirth",
    page_icon="💰",
    layout="wide",
)

# ─── デモ版注意書き ───────────────────────────────────────────────────────────

st.info(
    "⚠️ **デモ版** — アップロードされたデータはセッション終了時に消去されます。"
    "大量データの処理は保証されません。本格利用はローカル版を推奨します。"
    " | [GitHub](https://github.com/moneyrebirth/moneyrebirth)"
)

st.title("💰 MoneyRebirth")
st.caption("複数金融機関のCSV/PDFをアップロードして家計簿・資産を可視化")

# ─── ファイルアップロード ──────────────────────────────────────────────────────

st.divider()

accept_types = ["csv"]
if PDFPLUMBER_AVAILABLE:
    accept_types.append("pdf")

uploaded_files = st.file_uploader(
    "CSV / PDF をアップロード（複数可）",
    type=accept_types,
    accept_multiple_files=True,
    help="MoneyForward・三菱UFJ・三井住友カード・SBI証券・モバイルSuicaに対応",
)

if not uploaded_files:
    st.markdown("""
### 対応ファイル

| サービス | 種別 | 取得方法 |
|---------|------|---------|
| MoneyForward ME | CSV | 家計簿 → 収支内訳 → CSVダウンロード |
| 三菱UFJ銀行 | CSV | 入出金明細 → ダウンロード |
| 三井住友カード | CSV | Vpass → WEB明細 → CSV |
| SBI証券 | CSV | 口座管理 → 保有証券一覧 → CSV |
| モバイルSuica | PDF | 残高ご利用明細 → PDF |
    """)

    with st.expander("🔒 プライバシーについて"):
        st.markdown("""
- アップロードされたデータはサーバーに**保存されません**
- セッション終了時にデータは消去されます
- [コードで確認できます](https://github.com/moneyrebirth/moneyrebirth-cloud)
        """)
    st.stop()

# ─── ファイル処理 ─────────────────────────────────────────────────────────────

tx_frames  = []  # 取引データ
pf_frames  = []  # ポートフォリオデータ
file_log   = []  # 処理ログ

PARSERS = {
    "mf":   parse_mf,
    "mufg": parse_mufg,   
    "mufg_balance": parse_mufg_balance,
    "smcc": parse_smcc,
    "suica": parse_suica,
}

for f in uploaded_files:
    raw   = f.read()
    fmt   = detect_format(f.name, raw)
    label = FORMAT_LABELS.get(fmt, "❓ 不明")

    if fmt == "sbi":
        df = parse_sbi(raw)
        if not df.empty:
            pf_frames.append(df)
            file_log.append(f"✅ {f.name} → {label} ({len(df)}銘柄)")
        else:
            file_log.append(f"⚠️ {f.name} → {label} (読み込み失敗)")

    elif fmt == "mufg_balance":
        df = parse_mufg_balance(raw)
        if not df.empty:
            pf_frames.append(df)
            file_log.append(f"✅ {f.name} → {label} ({len(df)}件)")
        else:
            file_log.append(f"⚠️ {f.name} → {label} (読み込み失敗)")

    elif fmt in PARSERS:
        df = PARSERS[fmt](raw)
        if not df.empty:
            tx_frames.append(df)
            file_log.append(f"✅ {f.name} → {label} ({len(df)}件)")
        else:
            file_log.append(f"⚠️ {f.name} → {label} (読み込み失敗)")

    else:
        file_log.append(f"❓ {f.name} → フォーマット不明、スキップ")

# ログ表示
for log in file_log:
    st.write(log)

# 取引データ統合
tx = pd.concat(tx_frames, ignore_index=True) if tx_frames else pd.DataFrame()
pf = pd.concat(pf_frames, ignore_index=True) if pf_frames else pd.DataFrame()

if tx.empty and pf.empty:
    st.error("読み込めたデータがありません。ファイルを確認してください。")
    st.stop()

if not tx.empty:
    tx = tx.sort_values("日付", ascending=False)
    tx["年"]  = tx["日付"].dt.year
    tx["月"]  = tx["日付"].dt.to_period("M").astype(str)
    st.success(f"✅ 取引データ: {len(tx):,}件")

if not pf.empty:
    st.success(f"✅ ポートフォリオ: {len(pf)}銘柄")

# ─── サイドバー ───────────────────────────────────────────────────────────────

pages = []
if not tx.empty:
    pages += ["🗓️ 月次レビュー", "📅 年次サマリー", "💳 取引履歴"]
if not pf.empty:
    pages += ["🏦 ポートフォリオ"]

if not pages:
    st.stop()

with st.sidebar:
    st.title("💰 MoneyRebirth")
    st.caption("v2 Cloud edition")
    st.divider()
    page = st.radio("ページ", pages)
    if not tx.empty:
        st.divider()
        st.caption(f"📊 {len(tx):,}件")
        st.caption(f"📅 {tx['日付'].min().strftime('%Y/%m')} 〜 {tx['日付'].max().strftime('%Y/%m')}")
        sources = tx["source"].value_counts()
        for src, cnt in sources.items():
            label = FORMAT_LABELS.get(src, src)
            st.caption(f"{label}: {cnt}件")

SOURCE_LABELS = {
    "moneyforward": "MoneyForward",
    "mufg":         "三菱UFJ",
    "smcc":         "三井住友",
    "suica":        "Suica",
}

# ─── 月次レビュー ─────────────────────────────────────────────────────────────

if page == "🗓️ 月次レビュー":
    st.title("🗓️ 月次レビュー")

    months = sorted(tx["月"].unique(), reverse=True)
    if "month_idx" not in st.session_state:
        st.session_state.month_idx = 0
    st.session_state.month_idx = max(0, min(st.session_state.month_idx, len(months) - 1))

    col_prev, col_sel, col_next = st.columns([1, 3, 1])
    with col_prev:
        if st.button("◀ 前月", disabled=st.session_state.month_idx >= len(months) - 1):
            st.session_state.month_idx += 1
            st.rerun()
    with col_sel:
        sel = st.selectbox("月", months, index=st.session_state.month_idx, label_visibility="collapsed")
        if sel != months[st.session_state.month_idx]:
            st.session_state.month_idx = months.index(sel)
            st.rerun()
    with col_next:
        if st.button("次月 ▶", disabled=st.session_state.month_idx <= 0):
            st.session_state.month_idx -= 1
            st.rerun()

    sel_month = months[st.session_state.month_idx]
    month_df  = tx[tx["月"] == sel_month]

    m_income  = month_df[month_df["金額"] > 0]["金額"].sum()
    m_expense = month_df[month_df["金額"] < 0]["金額"].sum()
    m_balance = m_income + m_expense

    col1, col2, col3 = st.columns(3)
    col1.metric("当月収入", f"¥{m_income:,.0f}")
    col2.metric("当月支出", f"¥{abs(m_expense):,.0f}")
    col3.metric("当月収支", f"¥{m_balance:+,.0f}")

    st.divider()

    m_exp = month_df[month_df["金額"] < 0].copy()
    m_exp["金額絶対値"] = m_exp["金額"].abs()

    if m_exp.empty:
        st.info("この月の支出データがありません")
    else:
        total_exp = m_exp["金額絶対値"].sum()
        col_l, col_r = st.columns([3, 2])

        with col_l:
            st.subheader("カテゴリ別支出")
            major_grp = m_exp.groupby("大項目")["金額絶対値"].sum().sort_values(ascending=False)
            for major, major_total in major_grp.items():
                pct = major_total / total_exp * 100
                with st.expander(f"**{major}**　¥{major_total:,.0f}　({pct:.1f}%)"):
                    detail = m_exp[m_exp["大項目"] == major][["日付", "摘要", "金額絶対値", "source"]].copy()
                    detail["日付"]   = detail["日付"].dt.strftime("%m/%d")
                    detail["金額"]   = detail["金額絶対値"].map(lambda x: f"¥{x:,.0f}")
                    detail["口座"]   = detail["source"].map(SOURCE_LABELS).fillna(detail["source"])
                    st.dataframe(detail[["日付", "摘要", "金額", "口座"]], use_container_width=True, hide_index=True)

        with col_r:
            st.subheader("支出内訳")
            fig = px.pie(major_grp.reset_index(), values="金額絶対値", names="大項目", hole=0.4)
            fig.update_traces(textposition="inside", textinfo="percent")
            fig.update_layout(showlegend=True, legend=dict(orientation="v", x=1.05, y=0.5),
                              margin=dict(t=20, b=20, l=20, r=120))
            st.plotly_chart(fig, use_container_width=True, key="monthly_pie")
            st.metric("支出合計", f"¥{total_exp:,.0f}")

# ─── 年次サマリー ─────────────────────────────────────────────────────────────

elif page == "📅 年次サマリー":
    st.title("📅 年次サマリー")

    exp_df = tx[tx["金額"] < 0].copy()
    exp_df["金額絶対値"] = exp_df["金額"].abs()
    inc_df = tx[tx["金額"] > 0].copy()

    yearly = exp_df.groupby("年")["金額絶対値"].sum().reset_index()
    yearly.columns = ["年", "支出合計"]
    fig_y = px.bar(yearly, x="年", y="支出合計", labels={"支出合計": "支出（円）"})
    fig_y.update_traces(texttemplate="¥%{y:,.0f}", textposition="outside")
    fig_y.update_layout(yaxis_tickformat=",.0f", showlegend=False)
    st.subheader("年別支出合計")
    st.plotly_chart(fig_y, use_container_width=True, key="yearly_bar")

    monthly = exp_df.groupby("月")["金額絶対値"].sum().reset_index()
    monthly.columns = ["月", "支出"]
    fig_m = px.line(monthly, x="月", y="支出", labels={"支出": "支出（円）"})
    fig_m.update_layout(yaxis_tickformat=",.0f")
    st.subheader("月別支出推移")
    st.plotly_chart(fig_m, use_container_width=True, key="monthly_line")

    cat_df   = exp_df[exp_df["大項目"] != "未分類"].copy()
    if not cat_df.empty:
        top_cats   = cat_df.groupby("大項目")["金額絶対値"].sum().nlargest(8).index.tolist()
        cat_yearly = cat_df[cat_df["大項目"].isin(top_cats)].groupby(["年", "大項目"])["金額絶対値"].sum().reset_index()
        cat_yearly.columns = ["年", "カテゴリ", "支出"]
        fig_c = px.bar(cat_yearly, x="年", y="支出", color="カテゴリ", barmode="stack",
                       labels={"支出": "支出（円）"})
        fig_c.update_layout(yaxis_tickformat=",.0f")
        st.subheader("カテゴリ別支出（年次）")
        st.plotly_chart(fig_c, use_container_width=True, key="cat_yearly")

    st.subheader("年別サマリー")
    yr_exp     = exp_df.groupby("年")["金額絶対値"].sum()
    yr_inc     = inc_df.groupby("年")["金額"].sum()
    yr_summary = pd.DataFrame({"支出": yr_exp, "収入": yr_inc}).fillna(0).astype(int)
    yr_summary["収支"]    = yr_summary["収入"] - yr_summary["支出"]
    yr_summary.index.name = "年"
    yr_summary = yr_summary.sort_index(ascending=False)
    yr_summary["支出"] = yr_summary["支出"].map(lambda x: f"¥{x:,.0f}")
    yr_summary["収入"] = yr_summary["収入"].map(lambda x: f"¥{x:,.0f}")
    yr_summary["収支"] = yr_summary["収支"].map(lambda x: f"¥{x:+,.0f}")
    st.dataframe(yr_summary, use_container_width=True)

# ─── 取引履歴 ─────────────────────────────────────────────────────────────────

elif page == "💳 取引履歴":
    st.title("💳 取引履歴")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        months    = ["全て"] + sorted(tx["月"].unique(), reverse=True)
        sel_month = st.selectbox("月", months)
    with col2:
        sources    = ["全て"] + sorted(tx["source"].unique())
        sel_source = st.selectbox("口座", sources)
    with col3:
        cats    = ["全て"] + sorted(tx["大項目"].dropna().unique())
        sel_cat = st.selectbox("カテゴリ", cats)
    with col4:
        keyword = st.text_input("キーワード")

    filtered = tx.copy()
    if sel_month  != "全て": filtered = filtered[filtered["月"] == sel_month]
    if sel_source != "全て": filtered = filtered[filtered["source"] == sel_source]
    if sel_cat    != "全て": filtered = filtered[filtered["大項目"] == sel_cat]
    if keyword:               filtered = filtered[filtered["摘要"].str.contains(keyword, na=False)]

    filtered["日付表示"] = filtered["日付"].dt.strftime("%Y/%m/%d")
    filtered["金額表示"] = filtered["金額"].map(lambda x: f"¥{x:+,.0f}")
    filtered["口座"]    = filtered["source"].map(SOURCE_LABELS).fillna(filtered["source"])

    st.dataframe(
        filtered[["日付表示", "口座", "摘要", "金額表示", "カテゴリ"]].rename(columns={"日付表示": "日付", "金額表示": "金額"}),
        use_container_width=True, hide_index=True,
    )
    st.caption(f"{len(filtered):,}件")

# ─── ポートフォリオ ───────────────────────────────────────────────────────────

elif page == "🏦 ポートフォリオ":
    st.title("🏦 ポートフォリオ（SBI証券）")
    st.caption(f"取得日: {pf['snapshot_date'].iloc[0]}")

    total_value = pf["market_value"].sum()
    total_gain  = pf["gain_loss"].dropna().sum()
    col1, col2, col3 = st.columns(3)
    col1.metric("総評価額", f"¥{total_value:,.0f}")
    col2.metric("評価損益", f"¥{total_gain:+,.0f}")
    col3.metric("損益率",   f"{total_gain/total_value*100:+.1f}%" if total_value else "—")

    st.divider()
    col_l, col_r = st.columns(2)

    with col_l:
        type_labels = {"stock": "株式", "fund": "投資信託", "bond": "債券"}
        pf_type = pf.groupby("asset_type")["market_value"].sum().reset_index()
        pf_type["label"] = pf_type["asset_type"].map(type_labels).fillna(pf_type["asset_type"])
        fig = px.pie(pf_type, values="market_value", names="label", hole=0.5)
        fig.update_traces(textposition="inside", textinfo="percent")
        fig.update_layout(showlegend=True, margin=dict(t=20, b=20, l=20, r=100))
        st.subheader("資産クラス別")
        st.plotly_chart(fig, use_container_width=True, key="pf_pie")

    with col_r:
        st.subheader("評価額 TOP10")
        top10 = pf.nlargest(10, "market_value")[["name", "market_value", "gain_loss", "section"]].copy()
        top10["評価額"]   = top10["market_value"].map(lambda x: f"¥{x:,.0f}")
        top10["評価損益"] = top10["gain_loss"].map(lambda x: f"¥{x:+,.0f}" if pd.notna(x) else "—")
        st.dataframe(
            top10[["name", "評価額", "評価損益"]].rename(columns={"name": "銘柄"}),
            use_container_width=True, hide_index=True,
        )

    st.divider()
    sections = ["全て"] + sorted(pf["section"].unique())
    sel_sec  = st.selectbox("セクション", sections)
    view     = pf if sel_sec == "全て" else pf[pf["section"] == sel_sec]
    view     = view.sort_values("market_value", ascending=False).copy()
    view["評価額"]   = view["market_value"].map(lambda x: f"¥{x:,.0f}")
    view["評価損益"] = view["gain_loss"].map(lambda x: f"¥{x:+,.0f}" if pd.notna(x) else "—")
    st.dataframe(
        view[["section", "name", "評価額", "評価損益"]].rename(columns={"section": "セクション", "name": "銘柄"}),
        use_container_width=True, hide_index=True,
    )
