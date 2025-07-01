## URL一覧のアウトプット
どのくらい網羅できたのかがわかるようにしたい

PDFの置き場はあるけど。。みたいな付随情報を持ってくるとかs

## Google Custom Search API設定

### 必要な環境変数
.envファイルに以下を追加してください：

```
GOOGLE_API_KEY=あなたのGoogle APIキー
GOOGLE_CSE_ID=あなたのCustom Search Engine ID
```

### 設定手順
1. [Google Cloud Console](https://console.cloud.google.com/)でプロジェクトを作成
2. Custom Search APIを有効化
3. APIキーを作成
4. [Programmable Search Engine](https://programmablesearchengine.google.com/)でカスタム検索エンジンを作成
5. 「ウェブ全体を検索」を有効にする
6. Search Engine IDを取得