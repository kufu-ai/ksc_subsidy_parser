#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
分類結果から個別ページのURLを抽出する専用ツール
"""

import pandas as pd
import json
import os
from pathlib import Path

def extract_individual_urls_from_classification(classification_file):
    """
    分類結果ファイルから個別ページのURLを抽出

    Args:
        classification_file (str): 分類結果ファイルのパス
    """
    try:
        # ファイル形式を判定して読み込み
        if classification_file.endswith('.json'):
            with open(classification_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
        elif classification_file.endswith('.csv'):
            df = pd.read_csv(classification_file)
            results = df.to_dict('records')
        else:
            raise ValueError("サポートされていないファイル形式です（.json または .csv のみ）")

        # 個別ページのみをフィルタリング
        individual_pages = [r for r in results if r.get('page_type') == '個別ページ']

        if not individual_pages:
            print("❌ 個別ページが見つかりませんでした")
            return

        # 出力ファイル名を生成
        base_name = Path(classification_file).stem
        output_dir = Path(classification_file).parent

        individual_urls_file = output_dir / f"{base_name}_individual_urls.txt"
        individual_summary_file = output_dir / f"{base_name}_individual_summary.csv"
        individual_detailed_file = output_dir / f"{base_name}_individual_detailed.json"

        # 1. URLリストのみを保存
        with open(individual_urls_file, 'w', encoding='utf-8') as f:
            for page in individual_pages:
                url = page.get('url', '')
                if url:
                    f.write(f"{url}\n")

        print(f"✅ URLリスト保存: {individual_urls_file} ({len(individual_pages)}件)")

        # 2. 詳細情報付きJSON保存
        with open(individual_detailed_file, 'w', encoding='utf-8') as f:
            json.dump(individual_pages, f, ensure_ascii=False, indent=2)

        print(f"✅ 詳細情報保存: {individual_detailed_file}")

        # 3. 自治体別サマリーを作成
        create_summary_by_prefecture(individual_pages, individual_summary_file)

        # 4. 統計情報を表示
        display_statistics(individual_pages)

    except Exception as e:
        print(f"❌ エラー: {str(e)}")

def create_summary_by_prefecture(individual_pages, summary_file):
    """
    都道府県・市区町村別のサマリーを作成
    """
    try:
        # 都道府県・市区町村でグループ化
        grouped = {}
        for page in individual_pages:
            pref = page.get('prefecture', '不明')
            city = page.get('city', '不明')
            key = (pref, city)

            if key not in grouped:
                grouped[key] = {
                    'urls': [],
                    'titles': [],
                    'confidences': [],
                    'pages': []
                }

            grouped[key]['urls'].append(page.get('url', ''))
            grouped[key]['titles'].extend(page.get('found_subsidy_titles', []))
            grouped[key]['confidences'].append(page.get('confidence', 0.0))
            grouped[key]['pages'].append(page)

        # サマリーデータを作成
        summary_data = []
        for (pref, city), data in grouped.items():
            unique_titles = list(set(data['titles']))  # 重複除去
            avg_confidence = sum(data['confidences']) / len(data['confidences']) if data['confidences'] else 0.0

            summary_data.append({
                '都道府県名': pref,
                '市区町村名': city,
                '個別ページ数': len(data['urls']),
                '平均確信度': round(avg_confidence, 3),
                '見つかった補助金制度数': len(unique_titles),
                '補助金制度例': ', '.join(unique_titles[:5]),  # 最初の5つ
                'URL例': data['urls'][0] if data['urls'] else '',
                'URL一覧': '|'.join(data['urls'])  # パイプ区切りで全URL
            })

        # CSVで保存
        df_summary = pd.DataFrame(summary_data)
        df_summary = df_summary.sort_values(['都道府県名', '市区町村名'])
        df_summary.to_csv(summary_file, index=False, encoding='utf-8')

        print(f"✅ サマリー保存: {summary_file}")

    except Exception as e:
        print(f"❌ サマリー作成エラー: {str(e)}")

def display_statistics(individual_pages):
    """
    統計情報を表示
    """
    print(f"\n{'='*50}")
    print(f"📊 個別ページ抽出結果統計")
    print(f"{'='*50}")

    # 基本統計
    print(f"総個別ページ数: {len(individual_pages)}")

    # 都道府県別統計
    pref_counts = {}
    city_counts = {}

    for page in individual_pages:
        pref = page.get('prefecture', '不明')
        city = page.get('city', '不明')

        pref_counts[pref] = pref_counts.get(pref, 0) + 1
        city_key = f"{pref} {city}"
        city_counts[city_key] = city_counts.get(city_key, 0) + 1

    print(f"対象都道府県数: {len(pref_counts)}")
    print(f"対象市区町村数: {len(city_counts)}")

    # 確信度統計
    confidences = [p.get('confidence', 0.0) for p in individual_pages]
    if confidences:
        avg_confidence = sum(confidences) / len(confidences)
        print(f"平均確信度: {avg_confidence:.3f}")
        print(f"最高確信度: {max(confidences):.3f}")
        print(f"最低確信度: {min(confidences):.3f}")

    # 上位都道府県
    print(f"\n--- 個別ページ数上位5都道府県 ---")
    top_prefs = sorted(pref_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    for pref, count in top_prefs:
        print(f"{pref}: {count}件")

    # 上位市区町村
    print(f"\n--- 個別ページ数上位5市区町村 ---")
    top_cities = sorted(city_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    for city, count in top_cities:
        print(f"{city}: {count}件")

def find_classification_files():
    """
    分類結果ファイルを検索
    """
    classification_files = []

    # 現在のディレクトリから分類結果ファイルを検索
    for pattern in ['*_page_classification.json', '*_page_classification.csv']:
        classification_files.extend(Path('.').glob(pattern))

    return sorted(classification_files)

def main():
    """
    メイン処理
    """
    print("🔍 個別ページURL抽出ツール")
    print("-" * 40)

    # 分類結果ファイルを検索
    classification_files = find_classification_files()

    if not classification_files:
        print("❌ 分類結果ファイルが見つかりません")
        print("   (*_page_classification.json または *_page_classification.csv)")
        return

    print("利用可能な分類結果ファイル:")
    for i, file in enumerate(classification_files, 1):
        print(f"{i}. {file.name}")

    try:
        choice = int(input("\n抽出するファイルの番号を選択してください: ")) - 1
        if 0 <= choice < len(classification_files):
            selected_file = classification_files[choice]
            print(f"\n📂 {selected_file.name} から個別ページを抽出中...")
            extract_individual_urls_from_classification(str(selected_file))
        else:
            print("❌ 無効な選択です")

    except ValueError:
        print("❌ 無効な入力です")
    except KeyboardInterrupt:
        print("\n⚠️  処理が中断されました")

if __name__ == '__main__':
    main()
