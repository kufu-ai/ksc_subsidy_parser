import os
from config import HTML_DIR
from html_content_extractor import extract_clean_content
import requests


def fetch_html(url, filename, use_playwright=True):
    os.makedirs(HTML_DIR, exist_ok=True)
    filepath = os.path.join(HTML_DIR, filename)

    if use_playwright:
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=30000)
                page.wait_for_load_state("networkidle")
                html = page.content()
                with open(filepath, "w", encoding="utf-8") as file:
                    file.write(html)
                browser.close()
            print(f"✅ PlaywrightでHTMLを保存: {filepath}")

            # 軽量コンテンツも生成
            clean_content = extract_clean_content(html)
            content_filepath = filepath.replace(".html", "_content.txt")
            with open(content_filepath, "w", encoding="utf-8") as file:
                file.write(clean_content)
            print(f"📄 軽量コンテンツを保存: {content_filepath}")

            return content_filepath
        except Exception as e:
            print(f"⚠️ Playwrightでの取得に失敗: {e}。requestsで再試行します。")

    # fallback: requests
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    response.encoding = response.apparent_encoding
    html = response.text
    with open(filepath, "w", encoding="utf-8") as file:
        file.write(html)
    print(f"✅ requestsでHTMLを保存: {filepath}")

    # 軽量コンテンツも生成
    clean_content = extract_clean_content(html)
    content_filepath = filepath.replace(".html", "_content.txt")
    with open(content_filepath, "w", encoding="utf-8") as file:
        file.write(clean_content)
    print(f"📄 軽量コンテンツを保存: {content_filepath}")

    return content_filepath
