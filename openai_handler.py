import openai
import json
import time
import os
from config import API_KEY, JSON_DIR
from utils import load_prompt, log_error

client = openai.OpenAI(api_key=API_KEY)


def get_subsidy_extraction_schema():
    """
    補助金情報抽出用の構造化出力スキーマを定義する
    """
    return {
        "type": "object",
        "properties": {
            "年度": {
                "type": "string",
                "description": "元号表記を西暦に変換し、4/1を設定（ex.令和6年度 → 2024-04-01）",
            },
            "都道府県": {"type": "string", "description": "都道府県名"},
            "市区町村": {"type": "string", "description": "市区町村名"},
            "制度名": {"type": "string", "description": "年度を含めず、制度名のみ抽出"},
            "制度の概要": {"type": "string", "description": "制度の概要説明"},
            "受付開始日": {
                "type": "string",
                "description": "受付開始日（YYYY-MM-DD形式、ない場合は空文字）",
            },
            "受付終了日": {
                "type": "string",
                "description": "受付終了日（YYYY-MM-DD形式、ない場合は空文字）",
            },
            "受付期間の補足": {
                "type": "string",
                "description": "条件による違いや補足などを記載",
            },
            "金額タイプ": {
                "type": "integer",
                "enum": [0, 1, 2, 3],
                "description": "一律:0, 条件による変動:1, 設備ごと:2, 条件変動・上限なし:3",
            },
            "金額": {
                "type": "integer",
                "description": "金額（数値のみ、万は数値に変換）",
            },
            "金額に関する詳細情報": {
                "type": "string",
                "description": "条件による加算や設備による違いの詳細情報",
            },
            "対象条件": {
                "type": "string",
                "description": "対象条件（改行は\\nで表現）",
            },
            "対象経費": {
                "type": "string",
                "description": "対象経費（改行は\\nで表現）",
            },
            "公式URL": {"type": "string", "description": "公式URL"},
            "抽出結果": {
                "type": "string",
                "description": "エラーや問題がある場合のメッセージ（正常時は空文字）",
            },
        },
        "required": [
            "年度",
            "都道府県",
            "市区町村",
            "制度名",
            "制度の概要",
            "受付開始日",
            "受付終了日",
            "受付期間の補足",
            "金額タイプ",
            "金額",
            "金額に関する詳細情報",
            "対象条件",
            "対象経費",
            "公式URL",
            "抽出結果",
        ],
        "additionalProperties": False,
    }


# OpenAI APIを使ってHTML解析し、JSONを取得
def process_with_openai(html_content, url):
    """
    構造化出力を使ってHTML解析し、補助金情報を抽出する

    Args:
        html_content (str): 解析対象のHTMLコンテンツ
        url (str): 対象URL

    Returns:
        str: 保存されたJSONファイルのパス、エラー時はNone
    """
    try:
        prompt_template = load_prompt()
        prompt = prompt_template.replace("{URL}", url)

        # HTMLコンテンツが長すぎる場合は制限する
        if len(html_content) > 100000:  # 約100KB以上の場合
            html_content = html_content[:100000] + "..."

        # OpenAI APIで構造化出力を使用してHTML解析
        response = client.responses.create(
            model="gpt-4o-mini",
            input=f"システム指示: {prompt}\n\nURL: {url}\n\n以下のHTMLコンテンツを分析してください：\n\n{html_content}",
            text={
                "format": {
                    "type": "json_schema",
                    "name": "subsidy_extraction",
                    "strict": True,
                    "schema": get_subsidy_extraction_schema(),
                }
            },
            temperature=0.1,
        )

        # 構造化出力からJSONを取得
        response_content = response.output[0].content[0].text

        if response_content:
            json_data = json.loads(response_content)
        else:
            raise ValueError("レスポンスが空です")

        print(f"✅ 構造化出力による解析完了: {url}")
        print(f"制度名: {json_data.get('制度名', 'N/A')}")

        # **❗ "抽出結果" がある場合はスキップ**
        if "抽出結果" in json_data and json_data["抽出結果"].strip():
            log_error(url, json_data["抽出結果"])
            return None

        # 抽出結果キーを削除（空でも）
        if "抽出結果" in json_data:
            del json_data["抽出結果"]

        # JSON保存
        os.makedirs(JSON_DIR, exist_ok=True)
        # ファイル名をより識別しやすくする
        timestamp = str(int(time.time()))
        json_path = f"{JSON_DIR}/subsidy_{timestamp}.json"

        with open(json_path, "w", encoding="utf-8") as file:
            json.dump(json_data, file, ensure_ascii=False, indent=2)

        print(f"💾 JSON保存完了: {json_path}")
        return json_path

    except Exception as e:
        error_message = f"構造化出力による解析エラー: {str(e)}"
        print(f"❌ {error_message}")
        log_error(url, error_message)
        return None


# 従来のupload_file関数は不要になったため削除
# HTMLファイルから直接コンテンツを読み込む関数を追加
def process_html_file_with_openai(html_file_path, url):
    """
    HTMLファイルを読み込んで構造化出力で解析する

    Args:
        html_file_path (str): HTMLファイルのパス
        url (str): 対象URL

    Returns:
        str: 保存されたJSONファイルのパス、エラー時はNone
    """
    try:
        with open(html_file_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        return process_with_openai(html_content, url)

    except Exception as e:
        error_message = f"HTMLファイル読み込みエラー: {str(e)}"
        print(f"❌ {error_message}")
        log_error(url, error_message)
        return None
