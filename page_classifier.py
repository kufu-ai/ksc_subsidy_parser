import pandas as pd
import json
import os
import time
from html_fetcher import fetch_html
from openai_handler import client
from config import API_KEY, JSON_DIR
from utils import log_error
from datetime import date


# 新築住宅建築に特化したページ分類プロンプト
def get_page_classification_prompt():
    return f"""
あなたは住宅建築に関する自治体の補助金情報ページを分析する専門家です。

以下のHTMLコンテンツを分析し、ページが注文住宅の購入を検討している人が活用できる補助金情報かの判定をしてください。
住宅の取得・建築や、それに付随する設備・用地・材料費などに対する補助金、または住宅取得・建築を条件とした移住、三世代同居・近居、結婚、若者、子育て世帯などに関する補助金情報が該当します。

## 対象となる住宅建築関連補助金について
- 補助金の申請手続きを目的とした、具体的な情報の提供をしているページを対象とします。
- 「住宅を新しく建てたい人が探している一般的な補助金」補助金を対象とします。
- 既存の危険性からの「移転」や「除却」を主目的とした補助金は対象外とします。
- 住宅の取得・建築や、それに付随する設備・用地・材料費などに対する補助金、または住宅取得・建築を条件とした移住、三世代同居・近居、結婚、若者、子育て世帯などを対象とした補助金を含みます。
- 補助対象に住宅が含まれていれば対象としてください。
  - 例えば、「住宅における太陽光発電システムや蓄電池等の設備導入補助金」などで、明確に新築としていされていなくても該当市区町村の住宅が対象の場合は既存の住宅も新築の住宅も対象となります。
  - 対象が市民の場合は市民の新築住宅も対象となります。
  - 戸建てに関する補助金も新築住宅も戸建てなので対象となります。
- 「市内の住宅」「住宅全般」「戸建て住宅」など、新築・既存の区別なく住宅全体が補助対象とされている場合は、新築住宅も含まれるものとして対象としてください。
- 「既存住宅のみ」「中古住宅のみ」など、既存住宅に限定されている場合のみ除外してください。
- 既存住宅**のみ**が補助対象の場合や、中古・賃貸・マンション専用の場合は除外してください。
- **ページ内に「新築住宅は対象外」「新築住宅の購入は補助対象外」など、新築住宅が補助対象外であることが明記されている場合は、必ず"関連なし"と判定してください。**

【判定ルールの明示】
- ページ内に「市内の住宅」「住宅全般」「戸建て住宅」などの表現がある場合は、必ず新築住宅も補助対象に含まれるものとして判定してください。
- 「新築」「既存」などの記載がなくても、「住宅」とだけ書かれていれば新築も含むものとします。
- 「既存住宅のみ」「中古住宅のみ」など、既存住宅に限定されている場合のみ新築住宅を除外してください。
- ページ内に「新築住宅は対象外」「新築住宅の購入は補助対象外」など、新築住宅が補助対象外であることが明記されている場合は、必ず"関連なし"と判定してください。
- 現在の日付{date.today()}よりも過去に建設された住宅が補助対象の場合は、必ず"関連なし"と判定してください。

【判定フロー例】
1. 「既存住宅のみ」「中古住宅のみ」などの記載がある場合 → "関連なし"
2. 「新築住宅は対象外」などの記載がある場合 → "関連なし"
3. 「市内の住宅」「住宅全般」「戸建て住宅」などの記載がある場合 → "住宅関連個別ページ"または"補助金情報一覧ページ"
4. 「住宅」とだけ書かれている場合 → "住宅関連個別ページ"または"補助金情報一覧ページ"


## 分類基準：

1. **補助金情報一覧ページ**: 複数の新築住宅建築関連補助金制度が掲載されているページ
   - 複数の新築住宅関連補助金制度のタイトルやリンクが含まれている
   - 新築住宅関連制度の一覧、目次、索引のような構造を持つ
   - 「新築住宅補助金一覧」「住宅建築支援制度」「新築関連制度」などの見出しがある

2. **住宅関連個別ページ**: 特定の新築住宅建築関連補助金制度について詳細が書かれているページ
   - 上記のいずれかの新築住宅関連補助金制度について詳しく説明している
   - 以下の詳細情報が含まれている：
     - 補助対象
     - 補助額・補助率
     - 申請条件・要件（例：新築住宅の取得・建築、移住、三世代同居・近居、結婚、新婚世帯、若者、子育て世帯、地域材利用など）
     - 申請方法・手続き
     - 申請期間・期限
     - 対象者（世帯条件、所得制限等）
   - **重要**: 既存住宅の改修・リフォーム専用の補助金は除外

3. **関連なし**:
   - 既存住宅のリフォーム・改修・修繕専用の補助金ページ
   - 中古住宅、マンション、団地、賃貸住宅専用の補助金ページ
   - 補助金に関連しないページ

構造化出力形式で回答してください。判定の確信度は0.0から1.0の範囲で設定し、見つかった住宅建築関連補助金制度のタイトルと対応するURLのセットを抽出してください。

**抽出指示**:
- 住宅建築関連補助金制度の名称・タイトルを正確に抽出
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
        # PDFファイルの場合は処理をスキップ
        # 非ウェブページファイルの拡張子を除外
        non_web_extensions = [
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".ppt",
            ".pptx",
            ".zip",
            ".rar",
            ".7z",
            ".tar",
            ".gz",
            ".exe",
            ".msi",
            ".dmg",
            ".pkg",
            ".deb",
            ".rpm",
            ".mp3",
            ".mp4",
            ".avi",
            ".mov",
            ".wmv",
            ".flv",
            ".mkv",
            ".wav",
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".bmp",
            ".svg",
            ".tiff",
            ".ico",
            ".rtf",
        ]

        if any(url.lower().endswith(ext) for ext in non_web_extensions):
            print(
                f"⚠️ 非対応のファイル(PDF, PPTX, DOCX, XLSX, etc.)のためスキップします: {url}"
            )
            return {
                "page_type": "その他",
                "is_target_page": "対象外",
                "confidence": 0.0,
                "reasoning": "PDFファイルのため分析対象外",
                "found_new_housing_subsidies": [],
                "url": url,
            }

        html_path = fetch_html(url, filename)

        # HTMLファイルの内容を読み込む
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        # HTMLが長すぎる場合は最初の部分だけを使用（OpenAIのトークン制限対策）
        if len(html_content) > 50000:  # 約50KB以上の場合
            html_content = html_content[:50000] + "..."

        # OpenAI APIでページを分析（構造化出力を使用）
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=f"システム指示: {get_page_classification_prompt()}\n\nURL: {url}\n\n以下のHTMLコンテンツを分析してください：\n\n{html_content}",
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
                                "enum": [
                                    "補助金情報一覧ページ",
                                    "住宅関連個別ページ",
                                    "その他",
                                ],
                                "description": "ページの種類",
                            },
                            "is_target_page": {
                                "type": "string",
                                "enum": [
                                    "対象",
                                    "対象外",
                                ],
                                "description": "ページが対象かどうか",
                            },
                            "confidence": {
                                "type": "number",
                                "minimum": 0.0,
                                "maximum": 1.0,
                                "description": "判定の確信度",
                            },
                            "reasoning": {
                                "type": "string",
                                "description": "判定理由を日本語で200文字以内で説明",
                            },
                            "found_new_housing_subsidies": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "title": {
                                            "type": "string",
                                            "description": "補助金制度のタイトル・名称",
                                        },
                                        "url": {
                                            "type": "string",
                                            "description": "補助金制度の詳細ページURL（見つからない場合は空文字）",
                                        },
                                    },
                                    "required": ["title", "url"],
                                    "additionalProperties": False,
                                },
                                "description": "見つかった新築住宅建築関連補助金制度のタイトルとURL一覧（最大10個）",
                            },
                            "page_title": {
                                "type": "string",
                                "description": "ページのタイトル",
                            },
                            "main_content_summary": {
                                "type": "string",
                                "description": "ページの主要コンテンツの要約（100文字以内）",
                            },
                        },
                        "required": [
                            "page_type",
                            "is_target_page",
                            "confidence",
                            "reasoning",
                            "found_new_housing_subsidies",
                            "page_title",
                            "main_content_summary",
                        ],
                        "additionalProperties": False,
                    },
                }
            },
            temperature=0.1,
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
            "page_title": "",
            "main_content_summary": "",
            "error": str(e),
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
        with open(json_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        results = []

        # ファイル名から都道府県名を推測
        prefecture = ""
        if "_" in json_file_path:
            prefecture = json_file_path.split("_")[0]

        # 新しいJSON形式に対応: {市区町村名: [検索結果の配列]}
        for city_name, search_results_list in data.items():
            print(f"\n{prefecture} {city_name} の分析開始...")

            # 各市区町村の検索結果リストを処理
            for search_result in search_results_list:
                if isinstance(search_result, dict) and "URL" in search_result:
                    urls = search_result.get("URL", [])

                    for i, url in enumerate(urls, 1):
                        print(f"  {i}/{len(urls)}: {url}")

                        result = classify_page_type(url)
                        result["prefecture"] = prefecture
                        result["city"] = city_name

                        results.append(result)

                        # API負荷軽減のため待機
                        time.sleep(5)

                        # TODO: 必要なくなったら消す。3つまでテスト（デバッグ用）
                        # if i >= 3:
                        #     break

            # TODO: 必要なくなったら消す。1つの市区町村だけテスト（デバッグ用）
            break

        return results

    except Exception as e:
        print(f"ファイル処理エラー: {str(e)}")
        return []


def save_classification_results(results, output_json_file):
    """
    分類結果をJSONファイルとCSVファイルに保存する

    Args:
        results (list): 分類結果のリスト
        output_json_file (str): 出力JSONファイル名
    """
    try:
        # 分類した結果を全てJSONで保存
        with open(output_json_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"JSON保存完了: {output_json_file}")

        # CSVファイルも作成
        output_csv_file = output_json_file.replace(".json", ".csv")
        save_results_as_csv(results, output_csv_file)
        print(f"CSV保存完了: {output_csv_file}")

        # 個別ページのURLのみを抽出
        extract_individual_page_urls(results, output_json_file)

        # 分類結果の統計を表示
        if results:
            page_types = [r.get("page_type", "エラー") for r in results]
            type_counts = pd.Series(page_types).value_counts()
            print("\n=== 分類結果統計 ===")
            for page_type, count in type_counts.items():
                print(f"{page_type}: {count}件")

    except Exception as e:
        print(f"保存エラー: {str(e)}")


def save_results_as_csv(results, output_csv_file):
    """
    分類結果をCSVファイルに保存する

    Args:
        results (list): 分類結果のリスト
        output_csv_file (str): 出力CSVファイル名
    """
    try:
        # CSVに変換するためのデータを準備
        csv_data = []
        for result in results:
            # 基本情報を抽出
            row = {
                "URL": result.get("url", ""),
                "都道府県": result.get("prefecture", ""),
                "市区町村": result.get("city", ""),
                "ページタイプ": result.get("page_type", ""),
                "対象ページ": result.get("is_target_page", ""),
                "確信度": result.get("confidence", 0.0),
                "判定理由": result.get("reasoning", ""),
                "ページタイトル": result.get("page_title", ""),
                "コンテンツ要約": result.get("main_content_summary", ""),
                "エラー": result.get("error", ""),
            }

            # 補助金制度のタイトルとURLを文字列として結合
            subsidies = result.get("found_new_housing_subsidies", [])
            if subsidies:
                titles = [s.get("title", "") for s in subsidies if s.get("title")]
                subsidy_urls = [s.get("url", "") for s in subsidies if s.get("url")]
                row["見つかった補助金制度"] = " | ".join(titles)
                row["補助金制度URL"] = " | ".join(subsidy_urls)
            else:
                row["見つかった補助金制度"] = ""
                row["補助金制度URL"] = ""

            csv_data.append(row)

        # DataFrameを作成してCSVに保存
        df = pd.DataFrame(csv_data)
        df.to_csv(output_csv_file, index=False, encoding="utf-8-sig")

    except Exception as e:
        print(f"CSV保存エラー: {str(e)}")


def extract_individual_page_urls(results, base_json_file):
    """
    個別ページのみのURLを抽出して別ファイルに保存する

    Args:
        results (list): 分類結果のリスト
        base_json_file (str): ベースとなるJSONファイル名
    """
    try:
        # 住宅関連個別ページのみをフィルタリング
        individual_pages = [
            r for r in results if r.get("page_type") == "住宅関連個別ページ"
        ]

        if not individual_pages:
            print("新築住宅関連の個別ページが見つかりませんでした")
            return

        # 個別ページ用のファイル名を生成
        individual_json = base_json_file.replace(".json", "_individual_pages.json")
        individual_urls_txt = base_json_file.replace(".json", "_individual_urls.txt")

        # 詳細情報付きで保存（JSON）
        with open(individual_json, "w", encoding="utf-8") as f:
            json.dump(individual_pages, f, ensure_ascii=False, indent=2)
        print(f"個別ページ詳細保存完了: {individual_json}")

        # URLリストのみを保存（テキストファイル）
        with open(individual_urls_txt, "w", encoding="utf-8") as f:
            for page in individual_pages:
                f.write(f"{page.get('url', '')}\n")
        print(f"個別ページURLリスト保存完了: {individual_urls_txt}")

        print(f"\n✅ 個別ページ抽出完了: {len(individual_pages)}件")

    except Exception as e:
        print(f"個別ページ抽出エラー: {str(e)}")


def main(file_name=None):
    """メイン処理"""
    print("補助金ページ分類します。")

    # 入力ファイルを選択
    json_files = [
        f for f in os.listdir(".") if f.endswith("_subsidy_urls_detailed.json")
    ]

    if not json_files:
        print("*_subsidy_urls_detailed.jsonファイルが見つかりません")
        return

    print("\n利用可能なファイル:")
    for i, file in enumerate(json_files, 1):
        print(f"{i}. {file}")

    try:
        selected_file = None
        if file_name:
            selected_file = f"{file_name}_subsidy_urls_detailed.json"
        else:
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
            # 元のファイル名から新しいファイル名を生成
            base_name = selected_file.replace("_subsidy_urls_detailed.json", "")
            output_file = f"{base_name}_page_classification.json"
            save_classification_results(results, output_file)
        else:
            print("分類結果が得られませんでした")

    except ValueError:
        print("無効な入力です")
    except KeyboardInterrupt:
        print("\n処理が中断されました")


if __name__ == "__main__":
    main()
