import csv
import os
import json
from config import CSV_FILE

CSV_HEADERS = ["年度", "都道府県", "市区町村", "制度名", "制度の概要", 
               "受付開始日", "受付終了日", "受付期間の補足", "金額タイプ", 
               "金額", "金額に関する詳細情報", "対象条件", "対象経費", "公式URL"]

# JSONデータをCSVに追加
def save_to_csv(json_file):
    with open(json_file, "r", encoding="utf-8") as file:
        data = json.load(file)

    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=CSV_HEADERS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(data)
    
    print(f"✅ データをCSVに保存: {CSV_FILE}")