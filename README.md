補助金情報を収集するツール

## セットアップ

```sh
pip install -r requirements.txt
```

環境変数を設定するために、`.env`ファイルを作成してください：

```sh
# OpenAI API設定
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_ASSISTANT_ID=your_assistant_id_here

# Tavily Search API設定
TAVILY_API_KEY=your_tavily_api_key_here
```

## 使用方法

### 1. 補助金URLの検索
```sh
python search_subsidy.py
```

### 2. ページの種類判定（新機能）
補助金関連URLが一覧ページか個別ページかを判定します：

```sh
python test_classifier.py
```

#### 機能説明
- **一覧ページ**: 複数の補助金制度が掲載されているページ
- **個別ページ**: 特定の補助金制度の詳細ページ
- **関連なし**: 補助金に関連しないページ

結果はCSVとJSONで保存され、以下の情報が含まれます：
- ページタイプの判定結果
- 判定の確信度（0.0-1.0）
- 判定理由
- 見つかった補助金制度のタイトル
- ページタイトル
- 主要コンテンツの要約

#### 自動生成される個別ページファイル
分類処理実行時に自動的に以下のファイルが生成されます：
- `*_individual_pages.csv` - 個別ページの詳細情報（CSV形式）
- `*_individual_pages.json` - 個別ページの詳細情報（JSON形式）
- `*_individual_urls.txt` - 個別ページのURLリスト（テキスト形式）
- `*_individual_summary.csv` - 自治体別サマリー

### 3. 一覧ページからの追加URL抽出
一覧ページと判定されたページから補助金関連URLを抽出して再分類します：

```sh
python extract_urls_from_list_pages.py
```

#### URL抽出方法
実行時に以下の抽出方法から選択できます：

1. **BeautifulSoup（推奨・デフォルト）**
   - ナビゲーション・サイドバーを自動除外
   - メインコンテンツエリアに特化した抽出
   - 無料で高精度

2. **従来版BeautifulSoup（シンプル）**
   - すべてのリンクを抽出する従来方式
   - ノイズが多いが高速

3. **OpenAI API（最高精度・コスト高）**
   - AIがコンテンツを解析して関連リンクを判定
   - 関連度スコア付きで最高精度
   - API利用料が発生

#### 機能説明
- 一覧ページのHTMLから補助金関連のURLを抽出
- 抽出したURLを自動的に分類（個別ページ・一覧ページ・関連なし）
- 階層的な検索により、より多くの個別ページを発見
- **精度問題を解決**: ナビゲーションバー・サイドバーのノイズを大幅削減

#### 生成されるファイル
- `*_extracted_all.json` - 抽出・分類結果（全件）
- `*_extracted_individual_urls.txt` - 新たに発見した個別ページURLリスト
- `*_extracted_individual_detailed.json` - 個別ページの詳細情報
- `*_extraction_stats.json` - 抽出統計情報

### 3-2. 高精度URL抽出ツール（上級者向け）
OpenAI APIを使った最高精度のURL抽出専用ツール：

```sh
python smart_url_extractor.py
```

#### 抽出方法
- **OpenAI API抽出**: HTMLコンテンツを解析して関連リンクのみを精密抽出
- **BeautifulSoup改良版**: 無料で高精度な抽出
- **比較モード**: 両方実行して抽出結果を比較

#### 生成されるファイル
- `*_smart_extracted_all.json` - 全抽出結果
- `*_smart_individual_urls.txt` - 高精度個別ページURLリスト
- `*_smart_extraction_details.json` - 抽出詳細情報（関連度スコア等）

### 3-3. 抽出精度テストツール
実際のページで抽出精度を比較できるテストツール：

```sh
python test_smart_extractor.py
```

テスト対象のURL（一覧ページ）を入力すると、OpenAI APIとBeautifulSoup改良版の抽出結果を比較表示します。

### 4. 個別ページURL抽出（専用ツール）
既存の分類結果から個別ページのURLを抽出します：

```sh
python extract_individual_urls.py
```

#### 生成されるファイル
- `*_individual_urls.txt` - 個別ページのURLリスト（シンプルなテキスト形式）
- `*_individual_detailed.json` - 個別ページの詳細情報
- `*_individual_summary.csv` - 自治体別サマリー（統計情報付き）

### 5. 分類結果の統合（推奨）
初回検索結果と一覧ページ抽出結果を統合して、重複を除去した最終的な個別ページリストを作成：

```sh
python merge_classification_results.py
```

#### 機能説明
- 初回検索結果と一覧ページ抽出結果をマージ
- URL重複の自動除去
- ソース別統計（初回検索 vs 一覧ページ抽出）
- 包括的な都道府県・市区町村別サマリー

#### 生成されるファイル
- `*_merged_individual_urls.txt` - **最終的な個別ページURLリスト**
- `*_merged_individual_detailed.json` - 統合詳細情報
- `*_merged_summary.csv` - 自治体別統合サマリー
- `*_merged_stats.json` - 統合統計情報

## 推奨ワークフロー

### 基本的な流れ
```sh
# 1. 補助金URLの検索
python search_subsidy.py

# 2. ページ分類実行
python test_classifier.py

# 3. 一覧ページからの追加抽出（改良版使用）
python extract_urls_from_list_pages.py
# -> 実行時に「1. 改良版BeautifulSoup」を選択（推奨）

# 4. 結果統合して最終URLリスト作成
python merge_classification_results.py

# 最終結果: *_merged_individual_urls.txt
```

### 高精度が必要な場合
```sh
# 1-2は同じ

# 3. 高精度抽出ツールを使用
python smart_url_extractor.py
# -> 実行時に「OpenAI API」を選択

# または、精度をテストしてから判断
python test_smart_extractor.py

# 4. 結果統合
python merge_classification_results.py
```

### URL抽出精度に関する注意点

#### 改良版BeautifulSoup（推奨）
- ✅ **無料で高精度**: ナビゲーション・サイドバーを自動除外
- ✅ **処理速度が速い**: API呼び出し不要
- ⚠️ **完璧ではない**: 複雑なサイト構造では一部ノイズが残る可能性

#### OpenAI API
- ✅ **最高精度**: AIがコンテンツを理解して関連リンクを判定
- ✅ **関連度スコア**: 各リンクの信頼度を数値化
- ❌ **コスト**: API利用料が発生
- ❌ **速度**: APIへのリクエスト分だけ時間がかかる

#### 使い分けの目安
- **大量処理・コスト重視**: 改良版BeautifulSoup
- **精度重視・重要なデータ**: OpenAI API
- **初回テスト**: テストツールで比較してから決定

### 6. 個別ページの詳細解析
```sh
python main.py
```
