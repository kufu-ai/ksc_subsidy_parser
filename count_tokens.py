import openai
import tiktoken

# 指定したテキストファイルのトークン数を計測
def count_tokens_from_file(file_path, model="gpt-4"):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            text = file.read()
        
        encoding = tiktoken.encoding_for_model(model)
        tokens = encoding.encode(text)
        
        print(f"✅ モデル: {model}")
        print(f"📊 トークン数: {len(tokens)}")
    
    except FileNotFoundError:
        print(f"❌ エラー: ファイル {file_path} が見つかりません。")

if __name__ == "__main__":
    count_tokens_from_file("prompts/prompt.txt", model="gpt-4")
