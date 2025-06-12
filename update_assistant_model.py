from openai import OpenAI
from config import API_KEY, ASSISTANT_ID

client = OpenAI(api_key=API_KEY)
   
# 既存のアシスタントを更新
updated_assistant = client.beta.assistants.update(
    assistant_id=ASSISTANT_ID,
    model="gpt-4o"  # 例: gpt-4o, gpt-4-turbo など
)

print(updated_assistant)