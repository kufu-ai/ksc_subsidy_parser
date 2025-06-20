import pandas as pd
import json
import os
import time
from html_fetcher import fetch_html
from openai_handler import client
from config import API_KEY, JSON_DIR
from utils import log_error

# ページ種類を判定するプロンプト
PAGE_CLASSIFICATION_PROMPT = """
あなたは自治体の補助金情報ページを分析する専門家です。

以下のHTMLコンテンツを分析し、このページが以下のどちらに該当するかを判定してください：

1. **一覧ページ**: 複数の補助金制度が掲載されているページ
   - 複数の補助金制度のタイトルやリンクが含まれている
   - 制度の一覧、目次、索引のような構造を持つ
   - 「補助金一覧」「制度一覧」「支援制度」などの見出しがある

2. **個別ページ**: 特定の補助金制度について詳細が書かれているページ
   - 1つの具体的な補助金制度について詳しく説明している
   - 以下のいずれかの詳細情報が含まれている
     - 申請方法
     - 対象
     - 要件
     - 条件
     - 金額
     - 補助率
     - 期間
     - 受給義務
   - 特定の制度名がページタイトルや見出しに使われている

3. **関連なし**: 補助金に関連しないページ

構造化出力形式で回答してください。判定の確信度は0.0から1.0の範囲で設定し、見つかった補助金制度のタイトルを抽出してください。
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
                                "enum": ["一覧ページ", "個別ページ", "関連なし"],
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
                            "found_subsidy_titles": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                                "description": "見つかった補助金制度のタイトル一覧（最大5個）"
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
                        "required": ["page_type", "confidence", "reasoning", "found_subsidy_titles", "page_title", "main_content_summary"],
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
            "found_subsidy_titles": [],
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
            city = item.get("市区町村名", "")
            urls = item.get("補助金関連URL", [])

            print(f"\n{prefecture} {city} の分析開始...")

            for i, url in enumerate(urls, 1):
                print(f"  {i}/{len(urls)}: {url}")

                result = classify_page_type(url)
                result["prefecture"] = prefecture
                result["city"] = city

                results.append(result)

                # API負荷軽減のため待機
                time.sleep(2)

                # 3つまでテスト（デバッグ用）
                if i >= 3:
                    break

            # 1つの市区町村だけテスト（デバッグ用）
            break

        return results

    except Exception as e:
        print(f"ファイル処理エラー: {str(e)}")
        return []

def save_classification_results(results, output_file):
    """
    分類結果を保存する

    Args:
        results (list): 分類結果のリスト
        output_file (str): 出力ファイル名
    """
    try:
        # JSONで保存
        json_output = output_file.replace('.csv', '.json')
        with open(json_output, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"JSON保存完了: {json_output}")

        # CSVで保存
        df = pd.DataFrame(results)
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"CSV保存完了: {output_file}")

        # 個別ページのURLを抽出
        extract_individual_page_urls(results, output_file)

        # 分類結果の統計を表示
        if results:
            page_types = [r.get('page_type', 'エラー') for r in results]
            type_counts = pd.Series(page_types).value_counts()
            print("\n=== 分類結果統計 ===")
            for page_type, count in type_counts.items():
                print(f"{page_type}: {count}件")

    except Exception as e:
        print(f"保存エラー: {str(e)}")

def extract_individual_page_urls(results, base_output_file):
    """
    個別ページのURLを抽出して別ファイルに保存する

    Args:
        results (list): 分類結果のリスト
        base_output_file (str): ベースとなる出力ファイル名
    """
    try:
        # 個別ページのみをフィルタリング
        individual_pages = [r for r in results if r.get('page_type') == '個別ページ']

        if not individual_pages:
            print("個別ページが見つかりませんでした")
            return

        # 個別ページ用のファイル名を生成
        individual_csv = base_output_file.replace('.csv', '_individual_pages.csv')
        individual_json = base_output_file.replace('.csv', '_individual_pages.json')
        individual_urls_txt = base_output_file.replace('.csv', '_individual_urls.txt')

        # 詳細情報付きで保存（JSON）
        with open(individual_json, 'w', encoding='utf-8') as f:
            json.dump(individual_pages, f, ensure_ascii=False, indent=2)
        print(f"個別ページ詳細保存完了: {individual_json}")

        # 詳細情報付きで保存（CSV）
        df_individual = pd.DataFrame(individual_pages)
        df_individual.to_csv(individual_csv, index=False, encoding='utf-8')
        print(f"個別ページ詳細保存完了: {individual_csv}")

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
            output_file = selected_file.replace('_subsidy_urls.json', '_page_classification.csv')
            save_classification_results(results, output_file)
        else:
            print("分類結果が得られませんでした")

    except ValueError:
        print("無効な入力です")
    except KeyboardInterrupt:
        print("\n処理が中断されました")

if __name__ == '__main__':
    main()
