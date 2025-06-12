from dotenv import load_dotenv
import os

# .env ファイルを読み込む
load_dotenv()

# OpenAI API設定
API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID")

# ディレクトリ設定
HTML_DIR = "data/html/"
JSON_DIR = "data/json/"
OUTPUT_DIR = "data/output/"
CSV_FILE = "data/subsidy_data.csv"

# ログファイル
LOG_DIR = "logs/"
ERROR_LOG_FILE = f"{LOG_DIR}/error.log"