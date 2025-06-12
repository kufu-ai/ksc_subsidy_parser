import openai
import json
import time
import os
from config import API_KEY, JSON_DIR, ASSISTANT_ID
from utils import load_prompt, log_error

client = openai.OpenAI(api_key=API_KEY)

# HTMLファイルをOpenAIにアップロード
def upload_file(filepath):
    """ HTMLファイルをOpenAIにアップロード """
    file_obj = client.files.create(
        file=open(filepath, "rb"),
        purpose="assistants"
    )
    return file_obj.id

# OpenAI APIを使ってHTML解析し、JSONを取得
def process_with_openai(file_id, url):
    prompt_template = load_prompt()
    prompt = prompt_template.replace("{URL}", url)

    # スレッド作成
    thread = client.beta.threads.create()
    thread_id = thread.id

    # 解析リクエスト
    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=[{
            "type": "text",
            "text": prompt
        }],
        attachments=[{
            "file_id": file_id,
            "tools": [{"type": "file_search"}]
        }]
    )

    # 解析実行
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=ASSISTANT_ID
    )

    # ステータス確認
    while True:
        run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        if run_status.status == "completed":
            break
        time.sleep(5)

    # 結果取得
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    
    # デバッグ: メッセージ全体を表示
    print("\n===== メッセージ情報 =====")
    print(f"メッセージ数: {len(messages.data)}")
    
    # 最新のメッセージの内容を取得（アシスタントからの応答）
    assistant_messages = [msg for msg in messages.data if msg.role == "assistant"]
    if not assistant_messages:
        print("アシスタントからの応答がありません")
        json_data = {}
    else:
        message_content = assistant_messages[0].content
        
        # デバッグ: メッセージ内容の詳細を表示
        print("\n===== メッセージ内容 =====")
        print(f"内容タイプ: {type(message_content)}")
        print(f"内容: {message_content}")
        
        # テキスト内容を抽出
        response_text = ""
        for i, content_item in enumerate(message_content):
            print(f"\n--- 内容アイテム {i+1} ---")
            print(f"タイプ: {content_item.type}")
            print(f"属性: {dir(content_item)}")
            
            if content_item.type == "text":
                try:
                    # 直接JSONとして解析を試みる
                    text_value = content_item.text.value
                    print(f"テキスト値: {text_value[:100]}...")  # 最初の100文字だけ表示
                    
                    # JSONの開始と終了を探す
                    json_start = text_value.find('{')
                    json_end = text_value.rfind('}') + 1
                    
                    if json_start >= 0 and json_end > json_start:
                        response_text = text_value[json_start:json_end]
                        print(f"抽出されたJSON: {response_text[:100]}...")
                    else:
                        response_text = text_value
                except AttributeError as e:
                    print(f"属性エラー: {e}")
                    print(f"text属性の詳細: {dir(content_item.text)}")
        
        print("\n===== 抽出されたテキスト =====")
        print(f"長さ: {len(response_text)}")
        print(f"内容: {response_text[:200]}...")  # 最初の200文字だけ表示
        
        try:
            json_data = json.loads(response_text)
            print("\n===== パースされたJSON =====")
            print(f"キー: {list(json_data.keys())}")
        except json.JSONDecodeError as e:
            print(f"\n===== JSONパースエラー =====")
            print(f"エラー: {e}")
            # JSONパースに失敗した場合、手動でJSONを構築
            try:
                # キーと値のペアを抽出する簡易的な方法
                lines = response_text.split('\n')
                json_data = {}
                for line in lines:
                    if ':' in line:
                        parts = line.split(':', 1)
                        key = parts[0].strip().strip('"')
                        value = parts[1].strip().strip(',').strip('"')
                        if key and value:
                            json_data[key] = value
                print(f"手動抽出したJSON: {json_data}")
            except Exception as e:
                print(f"手動JSON抽出エラー: {e}")
                json_data = {}

    json_data["公式URL"] = url  # URLを追加

    # **❗ "抽出結果" がある場合はスキップ**
    if "抽出結果" in json_data and json_data["抽出結果"].strip():
        log_error(url, json_data["抽出結果"])
        return None
    
    # 抽出結果キーを削除（空でも）
    if "抽出結果" in json_data:
        del json_data["抽出結果"]

    # JSON保存
    os.makedirs(JSON_DIR, exist_ok=True)
    json_path = f"{JSON_DIR}/{file_id}.json"
    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(json_data, file, ensure_ascii=False, indent=2)

    return json_path
