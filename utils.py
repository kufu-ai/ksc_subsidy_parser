import os
import datetime

LOG_DIR = "logs/"
ERROR_LOG_FILE = os.path.join(LOG_DIR, "error.log")
OUTPUT_DIR = "data/output/"

# ディレクトリを作成
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


def ensure_output_dir():
    """出力ディレクトリが存在することを確認し、なければ作成"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    return OUTPUT_DIR


def get_output_path(filename):
    """出力ファイルの完全パスを生成"""
    ensure_output_dir()
    return os.path.join(OUTPUT_DIR, filename)


def log_error(url, message):
    """エラーログを記録"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] URL: {url} - {message}\n"

    with open(ERROR_LOG_FILE, "a", encoding="utf-8") as file:
        file.write(log_entry)

    print(f"⚠️ エラー記録: {message}")


def load_prompt():
    """プロンプトをファイルから読み込む"""
    with open("prompts/prompt.txt", "r", encoding="utf-8") as file:
        return file.read()


def load_urls():
    """URLリストをファイルから読み込む"""
    with open("urls.txt", "r", encoding="utf-8") as file:
        return [line.strip() for line in file if line.strip()]
