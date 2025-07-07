補助金情報を収集するツール

## セットアップ

```sh
pip install -r requirements.txt
```

環境変数を設定するために、`.env`ファイルを作成してください：

```sh
# OpenAI API設定
OPENAI_API_KEY=your_openai_api_key_here
# 不明
OPENAI_ASSISTANT_ID=your_assistant_id_here

# Tavily Search API設定
TAVILY_API_KEY=your_tavily_api_key_here
```

SPAでできているサイトからHTMLを取得するために`playwright`のインストールが必要です。
```sh
# pip install -r requirements.txt の中で
# pip install playwright が済んでいるはずなので以下が実行できるはず
playwright install

```

## 使用方法

### 補助金に関するURLの一覧を取得・分類
```sh
python main_url.py
```

#### 処理フロー
1. **補助金検索**: 指定した都道府県の各市区町村で補助金に関するURLを検索
2. **ページ分類**: 検索で見つかったURLを3つのカテゴリに自動分類
3. **個別URL抽出**: 補助金一覧ページから個別の補助金制度のURLを抽出
4. **重複チェック**: 既に検索済みのURLと重複しないよう確認
5. **追加分類**: 新しく見つかった個別URLを再度分類
6. **結果統合**: 全ての分類結果を統合して最終ファイルを生成

#### ページ分類カテゴリ
- **補助金一覧ページ**: 複数の補助金制度が掲載されているページ
- **住宅関連個別ページ**: 特定の補助金制度の詳細ページ
- **その他**: 補助金に関連しないページ

#### 生成される主要ファイル
- `{都道府県名}_all_classification.json`: 全ての分類結果（JSON形式）
- `{都道府県名}_all_classification.csv`: 全ての分類結果（CSV形式）
- `{都道府県名}_page_classification.json`: 初回検索結果の分類
- `{都道府県名}2_subsidy_urls_detailed.json`: 一覧ページから抽出したURLの分類結果

**注意**: すべての出力ファイルは `data/output/` ディレクトリに保存されます。

#### 出力される情報
- ページタイプの判定結果
- 判定の確信度（0.0-1.0）
- 判定理由
- 見つかった補助金制度のタイトルとURL
- ページタイトル
- 主要コンテンツの要約

### 個別ページの詳細解析
```sh
python main.py
```

以下の選択肢が出る。
```text
🚀 補助金情報解析システム
==================================================
1. 既存URLリスト（urls.txt）の処理
2. 分類済み住宅関連個別ページの処理
3. 個別URL要約処理
==================================================
処理を選択してください (1, 2, または 3):
```

** 1 **
urls.txtの内容を全て要約します。

** 2 **
main_url.pyで実行した
`{都道府県名}_all_classification.json`
の個別ページでかつ対象のURLのみをまとめて実施します。

** 3 **
ターミナル上で入力したURLの要約を実施します。

要約されたデータは`data/subsidy_data.csv`に出力されます。