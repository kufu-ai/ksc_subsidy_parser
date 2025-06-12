import openai
from config import API_KEY

client = openai.OpenAI(api_key=API_KEY)

# 新しいアシスタントを作成
def create_assistant():
    assistant = client.beta.assistants.create(
        name="補助金情報解析アシスタント",
        instructions="このアシスタントは、提供されたHTMLデータから補助金情報を抽出し、JSON形式で整理する役割を担います。",
        model="gpt-4o",
        tools=[{"type": "file_search"}]  # HTMLファイルを解析するためのツールを有効化
    )
    
    print(f"✅ アシスタント作成成功！\n名前: {assistant.name}\nID: {assistant.id}")

if __name__ == "__main__":
    create_assistant()
