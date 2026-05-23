"""
MoneyRebirth Dashboard - ローカル版
使い方: streamlit run moneyrebirth_dashboard.py
"""

import sqlite3
from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px
from moneyrebirth_categories import load_categories

DB_PATH = Path(__file__).parent / "household.db"

st.set_page_config(
    page_title="MoneyRebirth",
    page_icon="💰",
    layout="wide",
)

# ─── データ取得 ────────────────────────────────────────────────────────────────

@st.cache_data
def load_transactions() -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='transactions'"
        ).fetchone()
        if not tables:
            return pd.DataFrame(columns=["source","date","description","amount","category","memo","detail"])
        df = pd.read_sql("""
            SELECT source, date, description, amount, category, memo, detail
            FROM transactions ORDER BY date DESC
        """, conn, parse_dates=["date"])
    return df

@st.cache_data
def load_portfolios() -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='portfolios'"
        ).fetchone()
        if not tables:
            return pd.DataFrame(columns=[
                "snapshot_date","section","asset_type","nisa","code","name","market_value","gain_loss","cost"
            ])
        df = pd.read_sql("""
            SELECT snapshot_date, section, asset_type, nisa,
                   code, name, market_value, gain_loss, cost
            FROM portfolios ORDER BY snapshot_date, market_value DESC
        """, conn, parse_dates=["snapshot_date"])
    return df

def reload():
    load_transactions.clear()
    load_portfolios.clear()

# ─── サイドバー ────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("💰 MoneyRebirth")
    if st.button("🔄 データ再読み込み"):
        reload()
        st.rerun()
    st.divider()
    page = st.radio("ページ", [
        "📊 サマリー", "📈 資産推移", "💳 取引履歴",
        "🏦 ポートフォリオ", "📅 年次サマリー", "🗓️ 月次レビュー", "✏️ 手入力", "📥 インポート"
    ])
    st.divider()
    st.caption("⚙️ 設定")
    # 月次レビューのデータソース
    # MoneyForward解約後は「SMCC・UFJ・手入力」に切り替え
    REVIEW_SOURCE = st.radio(
        "月次レビュー データソース",
        ["moneyforward", "other"],
        format_func=lambda x: "💚 MoneyForward" if x == "moneyforward" else "🏦 SMCC・UFJ・手入力",
        index=0,
    )

tx = load_transactions()
pf = load_portfolios()

SOURCE_LABELS = {
    "mufg": "三菱UFJ", "smcc": "三井住友カード",
    "amazon": "Amazon", "suica": "Suica",
    "moneyforward": "MoneyForward", "manual": "手入力"
}

# REVIEW_SOURCE はサイドバーで設定

# ─── データなし時のガード ──────────────────────────────────────────────────────

def no_data_message():
    st.info("📌 データがありません。📥 インポートページからCSVを取り込んでください。")

# ─── サマリー ──────────────────────────────────────────────────────────────────

if page == "📊 サマリー":
    st.title("📊 サマリー")

    sbi_pf   = pf[pf["asset_type"] != "bank"]
    bank_pf  = pf[pf["asset_type"] == "bank"]
    latest_sbi_date  = sbi_pf["snapshot_date"].max() if not sbi_pf.empty else None
    latest_bank_date = bank_pf["snapshot_date"].max() if not bank_pf.empty else None

    latest_pf  = sbi_pf[sbi_pf["snapshot_date"] == latest_sbi_date] if latest_sbi_date else pd.DataFrame()
    sbi_value  = latest_pf["market_value"].sum() if not latest_pf.empty else 0
    total_gain = latest_pf["gain_loss"].sum() if not latest_pf.empty else 0
    total_cost = latest_pf["cost"].sum() if not latest_pf.empty else 0

    bank_value = 0.0
    if latest_bank_date is not None:
        latest_bank = bank_pf[bank_pf["snapshot_date"] == latest_bank_date]
        bank_value  = latest_bank["market_value"].sum()

    total_value = sbi_value + bank_value

    today = pd.Timestamp.today()
    if not tx.empty:
        this_month = tx[(tx["date"].dt.year == today.year) & (tx["date"].dt.month == today.month)]
        expense    = this_month[this_month["amount"] < 0]["amount"].sum()
        income     = this_month[this_month["amount"] > 0]["amount"].sum()
    else:
        this_month = pd.DataFrame()
        expense = income = 0

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("総資産",      f"¥{total_value:,.0f}")
    col2.metric("うちSBI証券", f"¥{sbi_value:,.0f}")
    col3.metric("うち銀行預金",f"¥{bank_value:,.0f}")
    col4.metric("今月支出",    f"¥{abs(expense):,.0f}")
    col5.metric("評価損益",    f"¥{total_gain:+,.0f}")

    st.divider()
    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("資産クラス別内訳")
        type_labels = {"stock": "株式", "fund": "投資信託", "bond": "債券", "bank": "銀行預金"}
        if not latest_pf.empty:
            sbi_by_type = latest_pf.groupby("asset_type")["market_value"].sum()
            bank_series = pd.Series({"bank": bank_value}) if bank_value > 0 else pd.Series(dtype=float)
            combined    = pd.concat([sbi_by_type, bank_series]).reset_index()
            combined.columns = ["asset_type", "market_value"]
            combined["label"] = combined["asset_type"].map(type_labels).fillna(combined["asset_type"])
            fig = px.pie(combined, values="market_value", names="label", hole=0.5)
            fig.update_traces(textposition="inside", textinfo="percent")
            fig.update_layout(showlegend=True, margin=dict(t=20, b=20, l=20, r=100))
            st.plotly_chart(fig, use_container_width=True, key="summary_asset_pie")
        else:
            st.info("SBI証券のデータがありません")

    with col_r:
        st.subheader("今月の支出内訳（口座別）")
        if this_month.empty or "amount" not in this_month.columns:
            st.info("今月の支出データがありません")
        else:
            exp_by_src = this_month[this_month["amount"] < 0].copy()
            if not exp_by_src.empty:
                exp_by_src["source_label"] = exp_by_src["source"].map(SOURCE_LABELS).fillna(exp_by_src["source"])
                grp = exp_by_src.groupby("source_label")["amount"].sum().abs().reset_index()
                fig2 = px.pie(grp, values="amount", names="source_label", hole=0.5)
                fig2.update_traces(textposition="inside", textinfo="percent")
                fig2.update_layout(showlegend=True, margin=dict(t=20, b=20, l=20, r=100))
                st.plotly_chart(fig2, use_container_width=True, key="summary_expense_pie")
            else:
                st.info("今月の支出データがありません")

    if not latest_pf.empty:
        st.subheader("評価額 TOP10")
        top10 = latest_pf.nlargest(10, "market_value")[["name","market_value","gain_loss","section"]].copy()
        top10.columns = ["銘柄","評価額","評価損益","セクション"]
        top10["評価額"]   = top10["評価額"].map(lambda x: f"¥{x:,.0f}")
        top10["評価損益"] = top10["評価損益"].map(lambda x: f"¥{x:+,.0f}" if pd.notna(x) else "—")
        st.dataframe(top10, use_container_width=True, hide_index=True)

# ─── 資産推移 ──────────────────────────────────────────────────────────────────

elif page == "📈 資産推移":
    st.title("📈 資産推移")

    if pf.empty or pf["snapshot_date"].nunique() < 2:
        st.info("📌 スナップショットが1件しかありません。月1回CSVをインポートすると推移グラフが表示されます。")
        if not pf.empty:
            latest_date = pf["snapshot_date"].max()
            latest_pf   = pf[pf["snapshot_date"] == latest_date]
            type_labels = {"stock": "株式", "fund": "投資信託", "bond": "債券", "bank": "銀行預金"}
            summary = latest_pf.groupby("asset_type").agg(
                評価額=("market_value","sum"), 評価損益=("gain_loss","sum")
            ).reset_index()
            summary["asset_type"] = summary["asset_type"].map(type_labels)
            summary.columns = ["種別","評価額","評価損益"]
            summary["評価額"]   = summary["評価額"].map(lambda x: f"¥{x:,.0f}")
            summary["評価損益"] = summary["評価損益"].map(lambda x: f"¥{x:+,.0f}")
            st.dataframe(summary, use_container_width=True, hide_index=True)
    else:
        type_labels = {"stock": "株式", "fund": "投資信託", "bond": "債券", "bank": "銀行預金"}
        pf2 = pf.copy()
        pf2["asset_label"] = pf2["asset_type"].map(type_labels)
        monthly = pf2.groupby(["snapshot_date","asset_label"])["market_value"].sum().reset_index()
        fig = px.bar(monthly, x="snapshot_date", y="market_value", color="asset_label",
                     barmode="stack", labels={"market_value":"評価額","snapshot_date":"日付","asset_label":"種別"})
        fig.update_layout(legend_title="種別")
        st.plotly_chart(fig, use_container_width=True, key="asset_trend")

    st.divider()
    st.subheader("UFJ口座 残高推移")
    mufg = tx[tx["source"] == "mufg"].copy()
    if not mufg.empty:
        mufg_sorted = mufg.sort_values("date")
        mufg_daily  = mufg_sorted.groupby("date")["amount"].sum().cumsum().reset_index()
        mufg_daily.columns = ["date","残高推移（累積）"]
        fig3 = px.line(mufg_daily, x="date", y="残高推移（累積）")
        st.plotly_chart(fig3, use_container_width=True, key="mufg_trend")

# ─── 取引履歴 ──────────────────────────────────────────────────────────────────

elif page == "💳 取引履歴":
    st.title("💳 取引履歴")
    if tx.empty:
        no_data_message()
        st.stop()

    col1, col2, col3 = st.columns(3)
    with col1:
        sources   = ["全て"] + list(tx["source"].unique())
        sel_src   = st.selectbox("口座", sources)
    with col2:
        months    = sorted(tx["date"].dt.to_period("M").unique(), reverse=True)
        sel_month = st.selectbox("月", ["全て"] + [str(m) for m in months])
    with col3:
        keyword = st.text_input("キーワード検索")

    filtered = tx.copy()
    if sel_src   != "全て": filtered = filtered[filtered["source"] == sel_src]
    if sel_month != "全て": filtered = filtered[filtered["date"].dt.to_period("M").astype(str) == sel_month]
    if keyword:              filtered = filtered[filtered["description"].str.contains(keyword, na=False)]

    filtered = filtered.sort_values("date", ascending=False).copy()
    filtered["source"] = filtered["source"].map(SOURCE_LABELS).fillna(filtered["source"])
    filtered["金額"]   = filtered["amount"].map(lambda x: f"¥{x:+,.0f}")
    filtered["日付"]   = filtered["date"].dt.strftime("%Y/%m/%d")

    st.dataframe(
        filtered[["日付","source","description","金額","memo"]].rename(columns={
            "source":"口座","description":"摘要","memo":"メモ"
        }),
        use_container_width=True, hide_index=True,
    )
    st.caption(f"{len(filtered)}件")

# ─── ポートフォリオ ────────────────────────────────────────────────────────────

elif page == "🏦 ポートフォリオ":
    st.title("🏦 ポートフォリオ")

    if pf.empty:
        st.info("SBI証券のCSVをインポートしてください")
    else:
        latest_date = pf["snapshot_date"].max()
        st.caption(f"最終更新: {latest_date.date()}")
        latest_pf = pf[pf["snapshot_date"] == latest_date].copy()

        sections = ["全て"] + sorted(latest_pf["section"].unique())
        sel_sec  = st.selectbox("セクション", sections)
        view     = latest_pf if sel_sec == "全て" else latest_pf[latest_pf["section"] == sel_sec]
        view     = view.sort_values("market_value", ascending=False).copy()
        view["損益率"]   = (view["gain_loss"] / view["cost"] * 100).map(
            lambda x: f"{x:+.1f}%" if pd.notna(x) else "—"
        )
        view["評価額"]   = view["market_value"].map(lambda x: f"¥{x:,.0f}")
        view["評価損益"] = view["gain_loss"].map(lambda x: f"¥{x:+,.0f}" if pd.notna(x) else "—")
        st.dataframe(
            view[["section","name","評価額","評価損益","損益率"]].rename(columns={
                "section":"セクション","name":"銘柄"
            }),
            use_container_width=True, hide_index=True,
        )

        st.divider()
        st.subheader("NISA vs 一般預り")
        nisa_grp = latest_pf.groupby("nisa")["market_value"].sum().reset_index()
        nisa_grp["nisa"] = nisa_grp["nisa"].map({0:"一般預り",1:"NISA"})
        fig4 = px.pie(nisa_grp, values="market_value", names="nisa", hole=0.5)
        fig4.update_traces(textposition="inside", textinfo="percent")
        fig4.update_layout(showlegend=True, margin=dict(t=20, b=20))
        st.plotly_chart(fig4, use_container_width=True, key="nisa_pie")

# ─── 年次サマリー ──────────────────────────────────────────────────────────────

elif page == "📅 年次サマリー":
    st.title("📅 年次サマリー")
    st.caption("2014年からの支出・収入推移")
    if tx.empty:
        no_data_message()
        st.stop()

    @st.cache_data
    def load_tx_with_category() -> pd.DataFrame:
        with sqlite3.connect(DB_PATH) as conn:
            df = pd.read_sql("""
                SELECT source, date, description, amount, category, detail
                FROM transactions ORDER BY date
            """, conn, parse_dates=["date"])
        return df

    txc = load_tx_with_category()
    txc["year"] = txc["date"].dt.year
    txc["ym"]   = txc["date"].dt.to_period("M").astype(str)

    expense_df = txc[txc["amount"] < 0].copy()
    expense_df["abs_amount"] = expense_df["amount"].abs()
    income_df  = txc[txc["amount"] > 0].copy()

    st.subheader("年別支出合計")
    yearly = expense_df.groupby("year")["abs_amount"].sum().reset_index()
    yearly.columns = ["年","支出合計"]
    fig_y = px.bar(yearly, x="年", y="支出合計", labels={"支出合計":"支出（円）","年":"年"})
    fig_y.update_traces(texttemplate="¥%{y:,.0f}", textposition="outside")
    fig_y.update_layout(yaxis_tickformat=",.0f", showlegend=False)
    st.plotly_chart(fig_y, use_container_width=True, key="yearly_bar")

    st.subheader("月別支出推移（全期間）")
    monthly = expense_df.groupby("ym")["abs_amount"].sum().reset_index()
    monthly.columns = ["月","支出"]
    fig_m = px.line(monthly, x="月", y="支出", labels={"支出":"支出（円）","月":""})
    fig_m.update_layout(yaxis_tickformat=",.0f")
    st.plotly_chart(fig_m, use_container_width=True, key="monthly_line")

    st.subheader("カテゴリ別支出（年次）")
    cat_df = expense_df[expense_df["category"].notna() & (expense_df["category"] != "未分類")].copy()
    if cat_df.empty:
        st.info("MoneyForwardのカテゴリデータがあると表示されます")
    else:
        cat_df["大項目"] = cat_df["category"].str.split("/").str[0]
        top_cats = cat_df.groupby("大項目")["abs_amount"].sum().nlargest(8).index.tolist()
        cat_yearly = cat_df[cat_df["大項目"].isin(top_cats)].groupby(
            ["year","大項目"]
        )["abs_amount"].sum().reset_index()
        cat_yearly.columns = ["年","カテゴリ","支出"]
        fig_c = px.bar(cat_yearly, x="年", y="支出", color="カテゴリ", barmode="stack",
                       labels={"支出":"支出（円）","年":"年"})
        fig_c.update_layout(yaxis_tickformat=",.0f", legend_title="カテゴリ")
        st.plotly_chart(fig_c, use_container_width=True, key="cat_yearly")

    st.subheader("年別サマリー")
    yr_exp     = expense_df.groupby("year")["abs_amount"].sum()
    yr_inc     = income_df.groupby("year")["amount"].sum()
    yr_summary = pd.DataFrame({"支出":yr_exp,"収入":yr_inc}).fillna(0).astype(int)
    yr_summary["収支"]    = yr_summary["収入"] - yr_summary["支出"]
    yr_summary.index.name = "年"
    yr_summary = yr_summary.sort_index(ascending=False)
    yr_summary["支出"] = yr_summary["支出"].map(lambda x: f"¥{x:,.0f}")
    yr_summary["収入"] = yr_summary["収入"].map(lambda x: f"¥{x:,.0f}")
    yr_summary["収支"] = yr_summary["収支"].map(lambda x: f"¥{x:+,.0f}")
    st.dataframe(yr_summary, use_container_width=True)

# ─── 月次レビュー ──────────────────────────────────────────────────────────────

elif page == "🗓️ 月次レビュー":
    st.title("🗓️ 月次レビュー")
    if tx.empty:
        no_data_message()
        st.stop()

    today = pd.Timestamp.today()
    if "review_year"  not in st.session_state: st.session_state.review_year  = today.year
    if "review_month" not in st.session_state: st.session_state.review_month = today.month

    col_prev, col_title, col_next = st.columns([1,3,1])
    with col_prev:
        if st.button("◀ 前月"):
            if st.session_state.review_month == 1:
                st.session_state.review_month = 12
                st.session_state.review_year -= 1
            else:
                st.session_state.review_month -= 1
            st.rerun()
    with col_title:
        st.markdown(
            f"<h3 style='text-align:center'>{st.session_state.review_year}/{st.session_state.review_month:02d}</h3>",
            unsafe_allow_html=True
        )
    with col_next:
        if st.button("次月 ▶"):
            if st.session_state.review_month == 12:
                st.session_state.review_month = 1
                st.session_state.review_year += 1
            else:
                st.session_state.review_month += 1
            st.rerun()

    yr  = st.session_state.review_year
    mon = st.session_state.review_month

    if REVIEW_SOURCE == 'moneyforward':
        source_filter = "AND source = 'moneyforward'"
        st.caption("📌 データソース: MoneyForward")
    else:
        source_filter = "AND source IN ('smcc','mufg','manual')"
        st.caption("📌 データソース: SMCC・UFJ・手入力")

    with sqlite3.connect(DB_PATH) as conn:
        # テーブルが存在しない場合は空のDataFrameを返す
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='transactions'"
        ).fetchone()
        if not tables:
            st.info("📌 データがありません。📥 インポートページからCSVを取り込んでください。")
            st.stop()
        month_cat = pd.read_sql(f"""
            SELECT date, source, description, amount, category, memo, detail
            FROM transactions
            WHERE strftime('%Y', date) = '{yr:04d}'
              AND strftime('%m', date) = '{mon:02d}'
              {source_filter}
            ORDER BY date DESC
        """, conn, parse_dates=["date"])

    income  = month_cat[month_cat["amount"] > 0]["amount"].sum()
    expense = month_cat[month_cat["amount"] < 0]["amount"].sum()
    balance = income + expense

    col1, col2, col3 = st.columns(3)
    col1.metric("当月収入", f"¥{income:,.0f}")
    col2.metric("当月支出", f"¥{abs(expense):,.0f}")
    col3.metric("当月収支", f"¥{balance:+,.0f}")

    st.divider()

    exp_df = month_cat[month_cat["amount"] < 0].copy()
    exp_df["abs_amount"] = exp_df["amount"].abs()
    exp_df["大項目"] = exp_df["category"].fillna("未分類").str.split("/").str[0]
    exp_df["中項目"] = exp_df["category"].fillna("").apply(
        lambda x: x.split("/")[1] if "/" in str(x) else ""
    )

    if exp_df.empty:
        st.info("この月の支出データがありません")
    else:
        total_exp = exp_df["abs_amount"].sum()
        col_l, col_r = st.columns([3,2])

        with col_l:
            st.subheader("カテゴリ別支出")
            major_grp = exp_df.groupby("大項目")["abs_amount"].sum().sort_values(ascending=False)
            for major, major_total in major_grp.items():
                pct = major_total / total_exp * 100
                with st.expander(f"**{major}**　¥{major_total:,.0f}　({pct:.1f}%)"):
                    minor_grp = exp_df[exp_df["大項目"] == major].groupby(
                        exp_df["中項目"].replace("","（なし）")
                    )["abs_amount"].sum().sort_values(ascending=False)
                    for minor, minor_total in minor_grp.items():
                        st.markdown(f"　{minor}　¥{minor_total:,.0f}")
                    detail = exp_df[exp_df["大項目"] == major][["date","description","abs_amount","source"]].copy()
                    detail["date"]   = detail["date"].dt.strftime("%m/%d")
                    detail["source"] = detail["source"].map(SOURCE_LABELS).fillna(detail["source"])
                    detail.columns   = ["日付","摘要","金額","口座"]
                    detail["金額"]   = detail["金額"].map(lambda x: f"¥{x:,.0f}")
                    st.dataframe(detail, use_container_width=True, hide_index=True)

        with col_r:
            st.subheader("支出内訳")
            fig = px.pie(major_grp.reset_index(), values="abs_amount", names="大項目", hole=0.4)
            fig.update_traces(textposition="inside", textinfo="percent")
            fig.update_layout(showlegend=True, legend=dict(orientation="v", x=1.05, y=0.5),
                              margin=dict(t=20, b=20, l=20, r=120))
            st.plotly_chart(fig, use_container_width=True, key="monthly_pie")
            st.metric("支出合計", f"¥{total_exp:,.0f}")

# ─── 手入力 ────────────────────────────────────────────────────────────────────

elif page == "✏️ 手入力":
    st.title("✏️ 手入力")
    st.caption("財布・現金の支出を入力")

    # カテゴリをcategories.txtから読み込む
    CATEGORIES = load_categories()

    if not CATEGORIES:
        st.warning("⚠️ categories.txt が見つかりません。以下を実行してください：")
        st.code("python3 moneyrebirth-pickupcategories.py")
        st.stop()

    SOURCES = ["財布","三菱UFJ","三井住友カード","Suica","PayPay","その他"]

    col_pre1, col_pre2 = st.columns(2)
    with col_pre1:
        major = st.selectbox("大項目", list(CATEGORIES.keys()))
    with col_pre2:
        subs  = CATEGORIES.get(major, [])
        minor = st.selectbox("中項目", ["（なし）"] + subs)

    with st.form("manual_entry", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            entry_date = st.date_input("日付", value=pd.Timestamp.today().date())
            content    = st.text_input("内容（店名など）")
            amount_raw = st.number_input("金額（円）", min_value=-1000000, max_value=1000000, value=0, step=100)
            st.caption("支出はマイナス（例：-1500）、収入はプラス")
        with col2:
            source = st.selectbox("支出元", SOURCES)
            memo   = st.text_input("メモ")

        submitted = st.form_submit_button("💾 保存", use_container_width=True)
        if submitted:
            category = major
            if minor and minor != "（なし）":
                category = f"{major}/{minor}"
            import json as _json
            with sqlite3.connect(DB_PATH) as conn:
                # テーブルがなければ作成
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS transactions (
                        id          INTEGER PRIMARY KEY AUTOINCREMENT,
                        source      TEXT    NOT NULL,
                        date        DATE    NOT NULL,
                        description TEXT,
                        detail      TEXT,
                        amount      INTEGER NOT NULL,
                        balance     INTEGER,
                        category    TEXT,
                        memo        TEXT,
                        raw_data    TEXT,
                        imported_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("""
                    INSERT INTO transactions
                        (source, date, description, amount, category, memo, detail, raw_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    "manual", entry_date.isoformat(), content, amount_raw,
                    category, memo, source,
                    _json.dumps({"content":content,"amount":amount_raw,"source":source,"category":category,"memo":memo}, ensure_ascii=False),
                ))
                conn.commit()
            reload()
            st.success(f"✅ 保存しました：{content} ¥{amount_raw:,}")

    st.divider()
    st.subheader("手入力履歴（編集・削除）")

    with sqlite3.connect(DB_PATH) as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='transactions'"
        ).fetchone()
        if not tables:
            st.caption("まだ手入力データがありません")
            st.stop()
        manual_df = pd.read_sql("""
            SELECT id, date, description, amount, category, memo, detail
            FROM transactions WHERE source='manual'
            ORDER BY date DESC, id DESC LIMIT 50
        """, conn, parse_dates=["date"])

    if manual_df.empty:
        st.caption("まだ手入力データがありません")
    else:
        disp = manual_df.copy()
        disp["日付"] = disp["date"].dt.strftime("%Y/%m/%d")
        disp["表示"] = disp["日付"] + " | " + disp["description"].fillna("") + " | ¥" + disp["amount"].astype(str)

        sel_label = st.selectbox("編集・削除する行を選択", ["（選択してください）"] + disp["表示"].tolist())

        if sel_label != "（選択してください）":
            sel_idx = disp[disp["表示"] == sel_label].index[0]
            sel_row = manual_df.loc[sel_idx]
            sel_id  = int(sel_row["id"])

            st.divider()
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                e_date    = st.date_input("日付", value=sel_row["date"].date(), key="e_date")
                e_content = st.text_input("内容", value=sel_row["description"] or "", key="e_content")
                e_amount  = st.number_input("金額", value=int(sel_row["amount"]), step=100, key="e_amount")
            with col_e2:
                e_category = st.text_input("カテゴリ", value=sel_row["category"] or "", key="e_category")
                e_memo     = st.text_input("メモ", value=sel_row["memo"] or "", key="e_memo")
                e_source   = st.text_input("支出元", value=sel_row["detail"] or "", key="e_source")

            col_s, col_d = st.columns(2)
            with col_s:
                if st.button("💾 保存", use_container_width=True):
                    with sqlite3.connect(DB_PATH) as conn:
                        conn.execute("""
                            UPDATE transactions
                            SET date=?, description=?, amount=?, category=?, memo=?, detail=?
                            WHERE id=?
                        """, (e_date.isoformat(), e_content, e_amount, e_category, e_memo, e_source, sel_id))
                        conn.commit()
                    reload()
                    st.success("✅ 保存しました")
                    st.rerun()
            with col_d:
                if st.button("🗑️ 削除", use_container_width=True, type="primary"):
                    with sqlite3.connect(DB_PATH) as conn:
                        conn.execute("DELETE FROM transactions WHERE id=?", (sel_id,))
                        conn.commit()
                    reload()
                    st.success("✅ 削除しました")
                    st.rerun()

        st.divider()
        st.dataframe(
            disp[["日付","description","amount","category","memo"]].rename(columns={
                "description":"内容","amount":"金額","category":"カテゴリ","memo":"メモ"
            }),
            use_container_width=True, hide_index=True,
        )

# ─── インポート ────────────────────────────────────────────────────────────────

elif page == "📥 インポート":
    st.title("📥 インポート")
    st.caption("CSV/PDFをアップロードしてデータベースに取り込む")

    from parsers.detector import detect_format, FORMAT_LABELS
    from parsers.mf_parser import parse_mf
    from parsers.mufg_parser import parse_mufg
    from parsers.mufg_balance_parser import parse_mufg_balance
    from parsers.smcc_parser import parse_smcc
    from parsers.sbi_parser import parse_sbi
    from parsers.suica_parser import parse_suica

    uploaded_files = st.file_uploader(
        "CSV / PDF をアップロード（複数可）",
        type=["csv", "pdf"],
        accept_multiple_files=True,
        help="MoneyForward・三菱UFJ・三井住友カード・SBI証券・モバイルSuicaに対応",
    )

    if not uploaded_files:
        st.markdown("""
| サービス | 種別 | 取得方法 |
|---------|------|---------|
| MoneyForward ME | CSV | 家計簿 → 収支内訳 → CSVダウンロード |
| 三菱UFJ銀行（入出金） | CSV | 入出金明細 → ダウンロード |
| 三菱UFJ銀行（残高） | CSV | お預かり残高 → ダウンロード |
| 三井住友カード | CSV | Vpass → WEB明細 → CSV |
| SBI証券 | CSV | 口座管理 → 保有証券一覧 → CSV |
| モバイルSuica | PDF | 残高ご利用明細 → PDF |
        """)
        st.stop()

    if st.button("💾 取り込み開始", type="primary", use_container_width=True):
        results = []

        for f in uploaded_files:
            raw = f.read()
            fmt = detect_format(f.name, raw)
            label = FORMAT_LABELS.get(fmt, "❓ 不明")

            if fmt == "unknown":
                results.append(f"❓ {f.name} → フォーマット不明、スキップ")
                continue

            try:
                # ── 取引系 ──
                if fmt == "mf":
                    df = parse_mf(raw)
                    if df.empty:
                        results.append(f"⚠️ {f.name} → 読み込み失敗")
                        continue
                    from importers.mf_importer import import_moneyforward
                    import tempfile, os
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                        tmp.write(raw)
                        tmp_path = tmp.name
                    ins, dup, transfer = import_moneyforward(tmp_path)
                    os.unlink(tmp_path)
                    results.append(f"✅ {f.name} → {label}: {ins}件追加, {dup}件重複スキップ")

                elif fmt == "mufg":
                    from importers.mufg_importer import import_mufg
                    import tempfile, os
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                        tmp.write(raw)
                        tmp_path = tmp.name
                    ins, dup = import_mufg(tmp_path)
                    os.unlink(tmp_path)
                    results.append(f"✅ {f.name} → {label}: {ins}件追加, {dup}件重複スキップ")

                elif fmt == "mufg_balance":
                    from importers.mufg_balance_importer import import_mufg_balance
                    import tempfile, os
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                        tmp.write(raw)
                        tmp_path = tmp.name
                    ins, dup = import_mufg_balance(tmp_path)
                    os.unlink(tmp_path)
                    results.append(f"✅ {f.name} → {label}: {ins}件追加, {dup}件重複スキップ")

                elif fmt == "smcc":
                    from importers.smcc_importer import import_smcc
                    import tempfile, os
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                        tmp.write(raw)
                        tmp_path = tmp.name
                    ins, dup = import_smcc(tmp_path)
                    os.unlink(tmp_path)
                    results.append(f"✅ {f.name} → {label}: {ins}件追加, {dup}件重複スキップ")

                elif fmt == "sbi":
                    from importers.sbi_portfolio_importer import import_sbi_portfolio
                    import tempfile, os
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                        tmp.write(raw)
                        tmp_path = tmp.name
                    ins, dup = import_sbi_portfolio(tmp_path)
                    os.unlink(tmp_path)
                    results.append(f"✅ {f.name} → {label}: {ins}件追加, {dup}件重複スキップ")

                elif fmt == "suica":
                    from importers.suica_importer import import_suica
                    import tempfile, os
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(raw)
                        tmp_path = tmp.name
                    ins, dup, skip = import_suica(tmp_path)
                    os.unlink(tmp_path)
                    results.append(f"✅ {f.name} → {label}: {ins}件追加, {dup}件重複スキップ")

            except Exception as e:
                results.append(f"❌ {f.name} → エラー: {str(e)}")

        # 結果表示
        st.divider()
        for r in results:
            st.write(r)

        reload()
        st.success("✅ 取り込み完了！データを再読み込みしました。")
