import requests
import os
from config import HTML_DIR

# 指定URLのHTMLを取得し、ファイルとして保存
def fetch_html(url, filename):
    os.makedirs(HTML_DIR, exist_ok=True)
    filepath = os.path.join(HTML_DIR, filename)

    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    response.encoding = response.apparent_encoding
    
    with open(filepath, "w", encoding="utf-8") as file:
        file.write(response.text)
    
    print(f"✅ HTMLを保存: {filepath}")
    return filepath
