from html_fetcher import fetch_html
from openai_handler import upload_file, process_with_openai
from csv_handler import save_to_csv
from utils import load_urls

# ✅ URLリストを読み込み
urls = load_urls()

# ✅ 処理の実行
for idx, url in enumerate(urls):
    print(f"\n🚀 {idx+1}/{len(urls)}: {url} の解析を開始")

    html_path = fetch_html(url, f"page_{idx+1}.html")
    file_id = upload_file(html_path)
    json_path = process_with_openai(file_id, url)

    # **❗ JSONデータがない場合はスキップ**
    if json_path is None:
        print(f"⚠️ {url} のデータが取得できなかったため、スキップします。")
        continue

    save_to_csv(json_path)
    print(f"✅ {url} の解析が完了しました！\n")