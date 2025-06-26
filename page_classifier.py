import pandas as pd
import json
import os
import time
from html_fetcher import fetch_html
from openai_handler import client
from config import API_KEY, JSON_DIR
from utils import log_error

# 新築住宅建築に特化したページ分類プロンプト
PAGE_CLASSIFICATION_PROMPT = """
あなたは新築住宅建築に関する自治体の補助金情報ページを分析する専門家です。

以下のHTMLコンテンツを分析し、このページが新築住宅建築に関する補助金情報に該当するかを判定してください：

## 対象となる新築住宅建築関連補助金：
- **新築住宅建築補助金**: 新築住宅の建設費用に対する補助
- **新築住宅取得・購入補助金**: 新築住宅購入時の費用補助
- **住宅用地取得補助金**: 新築住宅建築用の土地購入費用補助
- **新築住宅用設備補助金**: 新築時の太陽光発電、蓄電池、エコキュート等の設備設置費用補助
- **新築住宅ローン利子補給**: 新築住宅購入・建築時の住宅ローン利子補助
- **子育て世帯新築住宅支援**: 子育て世帯向けの新築住宅取得・建築支援
- **新婚世帯新築住宅支援**: 新婚世帯向けの新築住宅取得・建築支援
- **移住定住新築住宅支援**: 移住・定住促進のための新築住宅取得・建築支援
- **省エネ新築住宅補助金**: 省エネ性能の高い新築住宅建築に対する補助
- **認定住宅建築補助金**: 長期優良住宅、ZEH等の認定新築住宅建築補助

## 分類基準：

1. **新築住宅関連一覧ページ**: 複数の新築住宅建築関連補助金制度が掲載されているページ
   - 複数の新築住宅関連補助金制度のタイトルやリンクが含まれている
   - 新築住宅関連制度の一覧、目次、索引のような構造を持つ
   - 「新築住宅補助金一覧」「住宅建築支援制度」「新築関連制度」などの見出しがある

2. **新築住宅関連個別ページ**: 特定の新築住宅建築関連補助金制度について詳細が書かれているページ
   - 上記のいずれかの新築住宅関連補助金制度について詳しく説明している
   - 以下の詳細情報が含まれている：
     - 補助対象
     - 補助額・補助率
     - 申請条件・要件
     - 申請方法・手続き
     - 申請期間・期限
     - 対象者（世帯条件、所得制限等）
   - 新築住宅建築に関する具体的な制度名がページタイトルや見出しに使われている
   - **重要**: 既存住宅の改修・リフォーム専用の補助金は除外

3. **関連なし**:
   - 新築住宅建築に関連しない補助金ページ
   - 既存住宅のリフォーム・改修・修繕専用の補助金ページ
   - 農業、商工業、教育、福祉等の他分野の補助金ページ
   - 補助金に関連しないページ

構造化出力形式で回答してください。判定の確信度は0.0から1.0の範囲で設定し、見つかった新築住宅関連補助金制度のタイトルと対応するURLのセットを抽出してください。

**抽出指示**:
- 新築住宅関連補助金制度の名称・タイトルを正確に抽出
- 各制度の詳細ページへのリンクURLを抽出（相対URLの場合は絶対URLに変換）
- 一覧ページの場合は、個別制度への内部リンクを優先的に抽出
- URLが見つからない制度の場合は、URLフィールドを空文字にする
"""

def classify_page_type(url):
    """
    URLのページタイプを判定する

    Args:
        url (str): 分析対象のURL

    Returns:
        dict: 判定結果
    """
    try:
        # HTMLを取得
        filename = f"page_classify_{int(time.time())}.html"
        html_path = fetch_html(url, filename)

        # HTMLファイルの内容を読み込む
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # HTMLが長すぎる場合は最初の部分だけを使用（OpenAIのトークン制限対策）
        if len(html_content) > 50000:  # 約50KB以上の場合
            html_content = html_content[:50000] + "..."

        # OpenAI APIでページを分析（構造化出力を使用）
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=f"システム指示: {PAGE_CLASSIFICATION_PROMPT}\n\nURL: {url}\n\n以下のHTMLコンテンツを分析してください：\n\n{html_content}",
            text={
                "format": {
                    "type": "json_schema",
                    "name": "page_classification",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "page_type": {
                                "type": "string",
                                "enum": ["新築住宅関連一覧ページ", "新築住宅関連個別ページ", "関連なし"],
                                "description": "ページの種類"
                            },
                            "confidence": {
                                "type": "number",
                                "minimum": 0.0,
                                "maximum": 1.0,
                                "description": "判定の確信度"
                            },
                            "reasoning": {
                                "type": "string",
                                "description": "判定理由を日本語で200文字以内で説明"
                            },
                            "found_new_housing_subsidies": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "title": {
                                            "type": "string",
                                            "description": "補助金制度のタイトル・名称"
                                        },
                                        "url": {
                                            "type": "string",
                                            "description": "補助金制度の詳細ページURL（見つからない場合は空文字）"
                                        }
                                    },
                                    "required": ["title", "url"],
                                    "additionalProperties": False
                                },
                                "description": "見つかった新築住宅建築関連補助金制度のタイトルとURL一覧（最大5個）"
                            },
                            "new_housing_subsidy_categories": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "enum": ["新築住宅建築", "新築住宅取得", "新築用土地取得", "新築時住宅設備", "新築住宅ローン利子補給", "子育て世帯新築支援", "新婚世帯新築支援", "移住定住新築支援", "省エネ新築住宅", "認定新築住宅", "その他新築関連"]
                                },
                                "description": "該当する新築住宅関連補助金のカテゴリ一覧"
                            },
                            "page_title": {
                                "type": "string",
                                "description": "ページのタイトル"
                            },
                            "main_content_summary": {
                                "type": "string",
                                "description": "ページの主要コンテンツの要約（100文字以内）"
                            }
                        },
                        "required": ["page_type", "confidence", "reasoning", "found_new_housing_subsidies", "new_housing_subsidy_categories", "page_title", "main_content_summary"],
                        "additionalProperties": False
                    }
                }
            },
            temperature=0.1
        )

        # 構造化出力からJSONを取得
        response_content = response.output[0].content[0].text

        # 構造化出力の場合、直接JSONとしてパース可能
        if response_content:
            result = json.loads(response_content)
        else:
            raise ValueError("レスポンスが空です")

        # URLを結果に追加
        result["url"] = url

        # HTMLファイルを削除
        os.remove(html_path)

        return result

    except Exception as e:
        log_error(url, f"ページ分類エラー: {str(e)}")
        return {
            "url": url,
            "page_type": "エラー",
            "confidence": 0.0,
            "reasoning": f"処理中にエラーが発生しました: {str(e)}",
            "found_new_housing_subsidies": [],
            "new_housing_subsidy_categories": [],
            "page_title": "",
            "main_content_summary": "",
            "error": str(e)
        }

def classify_urls_from_file(json_file_path):
    """
    JSONファイルからURLリストを読み込み、各URLを分類する

    Args:
        json_file_path (str): URLが保存されているJSONファイルのパス

    Returns:
        list: 分類結果のリスト
    """
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        results = []

        for item in data:
            prefecture = item.get("都道府県名", "")
            city = item.get("city_name", "")
            urls = item.get("補助金関連URL", [])

            print(f"\n{prefecture} {city} の分析開始...")

            for i, url in enumerate(urls, 1):
                print(f"  {i}/{len(urls)}: {url}")

                result = classify_page_type(url)
                result["prefecture"] = prefecture
                result["city"] = city

                results.append(result)

                # API負荷軽減のため待機
                time.sleep(5)

                # TODO: 必要なくなったら消す。3つまでテスト（デバッグ用）
                if i >= 3:
                    break

            # TODO: 必要なくなったら消す。1つの市区町村だけテスト（デバッグ用）
            # break

        return results

    except Exception as e:
        print(f"ファイル処理エラー: {str(e)}")
        return []

def save_classification_results(results, output_json_file):
    """
    分類結果をJSONファイルに保存する

    Args:
        results (list): 分類結果のリスト
        output_json_file (str): 出力JSONファイル名
    """
    try:
        # JSONで保存
        with open(output_json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"JSON保存完了: {output_json_file}")

        # 個別ページのURLを抽出
        extract_individual_page_urls(results, output_json_file)

        # 分類結果の統計を表示
        if results:
            page_types = [r.get('page_type', 'エラー') for r in results]
            type_counts = pd.Series(page_types).value_counts()
            print("\n=== 分類結果統計 ===")
            for page_type, count in type_counts.items():
                print(f"{page_type}: {count}件")

    except Exception as e:
        print(f"保存エラー: {str(e)}")

def extract_individual_page_urls(results, base_json_file):
    """
    個別ページのURLを抽出して別ファイルに保存する

    Args:
        results (list): 分類結果のリスト
        base_json_file (str): ベースとなるJSONファイル名
    """
    try:
        # 新築住宅関連個別ページのみをフィルタリング
        individual_pages = [r for r in results if r.get('page_type') == '新築住宅関連個別ページ']

        if not individual_pages:
            print("新築住宅関連の個別ページが見つかりませんでした")
            return

        # 個別ページ用のファイル名を生成
        individual_json = base_json_file.replace('.json', '_individual_pages.json')
        individual_urls_txt = base_json_file.replace('.json', '_individual_urls.txt')

        # 詳細情報付きで保存（JSON）
        with open(individual_json, 'w', encoding='utf-8') as f:
            json.dump(individual_pages, f, ensure_ascii=False, indent=2)
        print(f"個別ページ詳細保存完了: {individual_json}")

        # URLリストのみを保存（テキストファイル）
        with open(individual_urls_txt, 'w', encoding='utf-8') as f:
            for page in individual_pages:
                f.write(f"{page.get('url', '')}\n")
        print(f"個別ページURLリスト保存完了: {individual_urls_txt}")

        print(f"\n✅ 個別ページ抽出完了: {len(individual_pages)}件")

    except Exception as e:
        print(f"個別ページ抽出エラー: {str(e)}")

def main():
    """メイン処理"""
    print("補助金ページ分類ツール")

    # 入力ファイルを選択
    json_files = [f for f in os.listdir('.') if f.endswith('_subsidy_urls.json')]

    if not json_files:
        print("*_subsidy_urls.jsonファイルが見つかりません")
        return

    print("\n利用可能なファイル:")
    for i, file in enumerate(json_files, 1):
        print(f"{i}. {file}")

    try:
        choice = int(input("\n分析するファイルの番号を選択してください: ")) - 1
        if choice < 0 or choice >= len(json_files):
            print("無効な選択です")
            return

        selected_file = json_files[choice]
        print(f"\n{selected_file}を分析します...")

        # URLを分類
        results = classify_urls_from_file(selected_file)

        if results:
            # 結果を保存
            output_file = selected_file.replace('_subsidy_urls.json', '_page_classification.json')
            save_classification_results(results, output_file)
        else:
            print("分類結果が得られませんでした")

    except ValueError:
        print("無効な入力です")
    except KeyboardInterrupt:
        print("\n処理が中断されました")

if __name__ == '__main__':
    main()
