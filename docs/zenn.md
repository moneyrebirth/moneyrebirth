# 【Python×Claude】金融データは自分で管理。3日で家計簿アプリ「MoneyRebirth」を作った話

## はじめに
MoneyForwardのデータをバックアップとして保存していましたが、そのCSVファイルをローカル環境でわかりやすく、できればグラフ化して可視化できる個人用のツールがほしいと考えていました。

ちょうど話題のClaudeの勉強もかねて、最初に作成したのが「MoneyReverse」です。
名前の由来は、MoneyForwardのデータをCSVでダウンロードし、それを逆向き（Reverse）にSQLiteのデータベースへ戻して、Streamlitで簡単に表示することを目的としたことから名付けました。

驚くことに、初めて本格的に利用したClaudeの力を借りることで、わずか1〜2時間の短時間で完成させることができました。

この成功で勢いに乗り、「自分がメインで使っている金融機関（三菱UFJ銀行、三井住友カード、SBI証券）のCSVや、SuicaのPDFファイルも自分で管理できないか？」と始めたプロジェクトが、MoneyReverseの後継となる「MoneyRebirth」です。

> 「自分のデータ、特に金融データは自分で管理したい！」
> 「可能ならAIの力を借りて、分析や改善をしたい。でも、作るのは大変そう……」

そんな思いから始まったプロジェクトの、開発の裏側や苦労を本記事にまとめました。

---

## Claudeと作ったら3日で完成した
結論から書くと、開発にかかった時間はおよそ3日間。仕事後に1.5〜2時間ずつ作業したため、合計で5〜6時間といったところです。
飽きっぽい性格で、仕事後の限られた時間。まずは「動くこと（ランニングコード）」を最優先の目標としました。

### 短時間で完成までのサイクル
個人開発で挫折しないために大切なのは、以下のサイクルを高速で回すことでした。

■ 開発の高速サイクル
「アイデア（自分で決める）」 -> 「Claudeとコード化」 -> 「動かす（デバッグ・気付き）」 -> 「修正・リリース」

今回のアイデアは「自分のためのシンプルな家計簿」です。
昨今の金融機関のAPI厳格化や、各社バラバラのインターフェースに対応するため、自動でのデータ取得はあえて諦め、各サービスのWeb画面から手動でダウンロードする方針にしました。その代わり、PDFやCSV、文字コード（UTF-8やShift-JIS）の違いを自動で吸収する仕組みを目指します。

### 「理解してから委譲する」スタイル
AIに丸投げするのではなく、「アイデア、コード、テスト、気付き、修正」のプロセスを自分が主導し、理解した上で実装をClaudeに委譲するスタイルが、結果として開発スピードを爆発的に上げました。

・Chat（通常のClaude）とClaude Codeの使い分け：
全体の設計やエラーのディスカッションにはチャットを使い、実際のファイルの自動生成やリファクタリングにはターミナル連携ツール（Claude Codeなど）を使うことで、思考を妨げずに実装の進め方を習得する予定でした。
コード全体を理解したい、アイデアのやりとりが主体ということもあり、開発のほとんどは Claude Chat で実現しています。

---

## MoneyRebirthとは
「MoneyRebirth」は、ローカル環境で安全に動作する個人向けの金融データ可視化ダッシュボードです。

### 対応金融機関・サービス
MoneyForwardからエクスポートしたCSVだけでなく、以下の複数ソースに標準で対応しています。
・三菱UFJ銀行（CSV）
・三井住友カード（CSV）
・SBI証券（CSV）
・Suica（PDF形式しかサポートしていないため、PDF解析に対応）
・MoneyForward（CSVバックアップ）

### ローカル版とクラウド版
基本はローカルのSQLiteで安全にデータを保持しますが、Streamlit Community Cloud等を利用して自分専用のプライベートなクラウド環境にデプロイすることも可能です。

以下はクラウド上に公開されている、Cloud 用デモ版です。  
読み取ったデータをデータベースに保存しない、サポートされない機能があなど、機能も制限されています。

Cloud 版の詳細はコード (https://github.com/moneyrebirth/moneyrebirth/blob/main/moneyrebirth_cloud.py) を参照ください。

MoneyRebirth Cloud on Streamlit Cloud Community(https://moneyrebirth.streamlit.app)

---

## 技術スタック
コアとなる技術は非常にシンプルかつ強力なPythonエコシステムです。

・フロントエンド/UI: Streamlit （爆速でUIが作れるため採用）
・データ処理: Python + pandas （文字コードや複数フォーマットの変換に使用）
・データベース: SQLite （手軽にローカルに保存できる軽量DB）

### 拡張性の高いアーキテクチャ
parsers/ というディレクトリ配下に、金融機関ごとの解析ロジックを独立して配置しています。これにより、新しい金融機関のフォーマットを追加したい時も、既存のコードを汚さずに新しいパーサーを追加するだけで対応できる設計にしました。

---

## 使い方

使い方は非常にシンプルです。

### 1. インストール手順
リポジトリをクローンし、必要なライブラリをインストールして起動するだけです。

(コマンド一例)
git clone https://github.com/moneyrebirth/moneyrebirth.git
cd moneyrebirth
pip install -r requirements.txt
streamlit run moneyrebirth_dashboard.py

### 2. データのインポート
ブラウザでStreamlitの画面が開いたら、各金融機関からダウンロードしてきたCSVやPDFファイルを「画面にドラッグ＆ドロップするだけ」。
システムが自動でファイル形式を判定し、SQLiteへ流し込み、即座にグラフへ反映されます。


![demo](https://github.com/moneyrebirth/moneyrebirth/raw/refs/heads/main/docs/demo.gif)


---


## 番外編: SuicaはPDFしか対応していない問題

対応サービスを増やす中で、最も苦労したのがSuicaでした。

モバイルSuicaはCSVダウンロードに**非対応**で、提供されるのはPDF形式のみ。しかも半角カタカナ混じりの独特なフォーマットです。

```
11 10 ｵｰﾄ  東京          \9,389  +5,000
11 11 物販                \8,707  -682
11 19 定    浦和 出 池袋  \7,127  -274
```



一見シンプルに見えますが、裏では以下のような課題が山積みでした。

- **PDF → テキスト抽出**の処理
- **半角カタカナの種別判定**（`ｵｰﾄ` = チャージ、`物販` = 支出）
- **駅名の有無で列がずれる**問題への対応
- **年の情報がない**という根本的な問題

### pdfplumberが救世主

`pdfplumber` を使えばPDFのテキスト抽出は数行で済みます。

```python
with pdfplumber.open(pdf_path) as pdf:
    text = "\n".join(page.extract_text() for page in pdf.pages)
```

裏では複雑なPDF解析が走っていますが、使う側はこれだけ。OSSの力を実感した瞬間でした。

### 年の推定ロジック

PDFには月・日しか記載されていません。発行日から年を推定します。

```python
def infer_year(month, issue_year, issue_month):
    # 取引月 > 発行月 なら前年と判断
    # 例: 発行2026/5、取引月=11 → 2025年11月
    return issue_year - 1 if month > issue_month else issue_year
```

たった3行で1年分のデータを正しく振り分けられます。複雑な問題をシンプルに解決できた、開発の中で一番気持ちよかった瞬間でした。




## Claude, ChatGPT, Gemini の比較（開発の所感）
今回の開発では主にClaudeを使用しましたが、他のLLMツールとの使い分けについての所感です。

・Claude (Claude 4.6 Sonnet / Claude Code):  
コードの文脈を理解する能力が圧倒的。特に今回のような「複数ファイルのフォーマットを統一する」といった構造の理解やリファクタリングにおいて、最もバグの少ないコードを出力してくれました。

・ChatGPT:
 ![icon](https://avatars.githubusercontent.com/u/284693651?s=400&u=4ab7186d96c58a0d4c3cbd2b60b1ca7fd2e1bc7a&v=4)
MoneyReverse のアイコンは ChatGPT と一緒に M、R をデザインとした家計簿サービスをテーマに3、4分で作成しました。  
実は Claude と同様の作業をしたのですが、センスがイマイチだった :<  
よくみると、翼は MoneyRebirth の M と R です。右下の三本線は右肩上がりの資産グラフ!


・Gemini:  
仕事も含めて利用機会が最も多く、Gemini の実力・可能性については Claude, ChatGPT より理解しているつもりです。
よって、今回のプロジェクトではできるだけ Gemini に頼らず完成させることも目標としました。

---

## おわりに
自分で使うために作ったツールですが、同じように「金融データを他社に預けっぱなしにしたくない」「自分で自由に分析したい」という方のために、OSS（オープンソース）としてGitHubに公開しました。

### v2の予定、ロードマップ
今後は以下のアップデートを予定しています(飽きなければ &#x1f923;)。

- [x] MoneyForward CSVインポート
- [x] 三菱UFJ・三井住友カード・SBI証券・Suica対応
- [x] ブラウザからCSV/PDFアップロード（フォーマット自動判定）
- [x] 資産推移・ポートフォリオグラフ
- [x] 月次レビュー・年次サマリー
- [x] 手入力（現金支出の記録・編集・削除）
- [x] **V1.1** Streamlit Cloudクラウド版
- [ ] **v2**: 財布機能・手入力との残高連携
- [ ] **v2**: レシート撮影による自動入力（Claude Vision API活用）
- [ ] **v2**: カテゴリ自動分類（AI活用）
- [ ] **v2**: 楽天銀行・イオン銀行など対応金融機関追加



ソースコードは以下で公開しています。スターやフィードバック、プルリクエストなどをいただけると励みになります！

- GitHubリポジトリ、他:   
  - Github (https://github.com/moneyrebirth/moneyrebirth)
  - X / Twitter (https://x.com/moneyrebirth)  
- 関連リンク:   
  - Streamlit公式 (https://streamlit.io/)  
  - Streamlit Cloud Community (https://streamlit.io/cloud)
  - MoneyRebirth Cloud on Streamlit Cloud Community(https://moneyrebirth.streamlit.app)
---
Built with Claude — because your financial data should be yours.
