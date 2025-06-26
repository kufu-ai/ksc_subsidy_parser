#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
分類結果をマージして統合的な個別ページリストを作成するツール
"""

import pandas as pd
import json
import os
from pathlib import Path
from datetime import datetime
import re

def merge_classification_results(original_results, extracted_results):
    """
    元の分類結果と抽出結果をマージ

    Args:
        original_results (list): 元の分類結果
        extracted_results (list): 一覧ページから抽出した結果

    Returns:
        dict: マージされた結果
    """
    # 個別ページのみを抽出（新スキーマのみ）
    original_individual = [r for r in original_results if r.get('page_type') == '新築住宅関連個別ページ']
    extracted_individual = [r for r in extracted_results if r.get('page_type') == '新築住宅関連個別ページ']

    # 元の個別ページにソース情報を追加
    for page in original_individual:
        page['source'] = '初回検索'
        page['extracted_from_list'] = False

    # 抽出した個別ページにソース情報を追加
    for page in extracted_individual:
        page['source'] = '一覧ページから抽出'
        # extracted_from_listは既に設定済み

    # URL重複を除去しながらマージ
    seen_urls = set()
    merged_individual = []

    # 元の結果を先に追加（優先度高）
    for page in original_individual:
        url = page.get('url', '')
        if url and url not in seen_urls:
            seen_urls.add(url)
            merged_individual.append(page)

    # 抽出結果を追加（重複チェック）
    new_from_extraction = 0
    for page in extracted_individual:
        url = page.get('url', '')
        if url and url not in seen_urls:
            seen_urls.add(url)
            merged_individual.append(page)
            new_from_extraction += 1

    return {
        'merged_individual_pages': merged_individual,
        'statistics': {
            'original_count': len(original_individual),
            'extracted_count': len(extracted_individual),
            'merged_count': len(merged_individual),
            'new_from_extraction': new_from_extraction,
            'duplicate_removed': len(original_individual) + len(extracted_individual) - len(merged_individual)
        }
    }

def create_comprehensive_summary(merged_data):
    """
    包括的なサマリーを作成

    Args:
        merged_data (dict): マージされたデータ

    Returns:
        dict: サマリーデータ
    """
    individual_pages = merged_data['merged_individual_pages']

    # 都道府県・市区町村別統計
    prefecture_stats = {}
    city_stats = {}
    source_stats = {'初回検索': 0, '一覧ページから抽出': 0}

    for page in individual_pages:
        # 都道府県統計（parent_prefectureも考慮）
        pref = page.get('prefecture') or page.get('parent_prefecture', '不明')
        prefecture_stats[pref] = prefecture_stats.get(pref, 0) + 1

        # 市区町村統計
        city = page.get('city') or page.get('parent_city', '不明')
        city_key = f"{pref} {city}"
        city_stats[city_key] = city_stats.get(city_key, 0) + 1

        # ソース統計
        source = page.get('source', '不明')
        if source in source_stats:
            source_stats[source] += 1

    # 確信度統計
    confidences = [p.get('confidence', 0.0) for p in individual_pages if p.get('confidence') is not None]
    confidence_stats = {}
    if confidences:
        confidence_stats = {
            'average': sum(confidences) / len(confidences),
            'max': max(confidences),
            'min': min(confidences),
            'high_confidence_count': len([c for c in confidences if c >= 0.8])
        }

    # 補助金制度統計
    all_titles = []
    for page in individual_pages:
        titles = page.get('found_subsidy_titles', [])
        all_titles.extend(titles)

    unique_titles = list(set(all_titles))

    return {
        'total_individual_pages': len(individual_pages),
        'prefecture_stats': dict(sorted(prefecture_stats.items(), key=lambda x: x[1], reverse=True)),
        'city_stats': dict(sorted(city_stats.items(), key=lambda x: x[1], reverse=True)[:20]),  # 上位20市区町村
        'source_stats': source_stats,
        'confidence_stats': confidence_stats,
        'subsidy_titles_found': len(unique_titles),
        'sample_titles': unique_titles[:10]  # サンプルタイトル
    }

def save_merged_results(merged_data, comprehensive_summary, base_filename):
    """
    マージ結果を保存

    Args:
        merged_data (dict): マージされたデータ
        comprehensive_summary (dict): 包括的サマリー
        base_filename (str): ベースファイル名
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    individual_pages = merged_data['merged_individual_pages']

    # 1. 統合個別ページURLリスト（テキスト）
    merged_urls_file = f"{base_filename}_merged_individual_urls.txt"
    with open(merged_urls_file, 'w', encoding='utf-8') as f:
        for page in individual_pages:
            f.write(f"{page.get('url', '')}\n")
    print(f"✅ 統合URLリスト: {merged_urls_file} ({len(individual_pages)}件)")

    # 2. 詳細情報付きJSON
    merged_detailed_file = f"{base_filename}_merged_individual_detailed.json"
    with open(merged_detailed_file, 'w', encoding='utf-8') as f:
        json.dump(individual_pages, f, ensure_ascii=False, indent=2)
    print(f"✅ 統合詳細情報: {merged_detailed_file}")

    # 3. CSV形式
    df_merged = pd.DataFrame(individual_pages)
    merged_csv_file = f"{base_filename}_merged_individual.csv"
    df_merged.to_csv(merged_csv_file, index=False, encoding='utf-8')
    print(f"✅ 統合CSV: {merged_csv_file}")

    # 4. 都道府県・市区町村別サマリー
    summary_data = []
    for city_key, count in comprehensive_summary['city_stats'].items():
        try:
            pref, city = city_key.split(' ', 1)
        except ValueError:
            pref, city = city_key, ''

        # その市区町村の個別ページを取得
        city_pages = [p for p in individual_pages
                     if (p.get('prefecture') or p.get('parent_prefecture', '')) == pref
                     and (p.get('city') or p.get('parent_city', '')) == city]

        # 統計計算
        sources = [p.get('source', '不明') for p in city_pages]
        source_counts = {s: sources.count(s) for s in set(sources)}

        confidences = [p.get('confidence', 0.0) for p in city_pages if p.get('confidence') is not None]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        # 補助金制度タイトル
        titles = []
        for p in city_pages:
            titles.extend(p.get('found_subsidy_titles', []))
        unique_titles = list(set(titles))

        summary_data.append({
            '都道府県名': pref,
            '市区町村名': city,
            '個別ページ数': count,
            '初回検索由来': source_counts.get('初回検索', 0),
            '一覧ページ抽出由来': source_counts.get('一覧ページから抽出', 0),
            '平均確信度': round(avg_confidence, 3),
            '見つかった補助金制度数': len(unique_titles),
            '補助金制度例': ', '.join(unique_titles[:3]),
            'URL例': city_pages[0].get('url', '') if city_pages else '',
        })

    summary_csv_file = f"{base_filename}_merged_summary.csv"
    df_summary = pd.DataFrame(summary_data)
    df_summary.to_csv(summary_csv_file, index=False, encoding='utf-8')
    print(f"✅ 統合サマリー: {summary_csv_file}")

    # 5. 統計情報
    stats_data = {
        'merge_timestamp': timestamp,
        'merge_statistics': merged_data['statistics'],
        'comprehensive_summary': comprehensive_summary
    }

    stats_file = f"{base_filename}_merged_stats.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats_data, f, ensure_ascii=False, indent=2)
    print(f"✅ 統計情報: {stats_file}")

    # 都道府県→市区町村→URLリスト（タイトル付き）形式のJSON出力
    # TODO: 内容の要約時に使用するようにする。prefectureとcityが機械的に判断できるようになるのでAIによる間違えが起こらないくなる。
    # individual_pagesを都道府県・市区町村ごとにまとめる
    pref_city_dict = {}
    for page in individual_pages:
        pref = page.get('prefecture') or page.get('parent_prefecture', '不明')
        city = page.get('city') or page.get('parent_city', '不明')
        # URLとタイトルのリストを作成
        urls = []
        # found_new_housing_subsidiesがあればそのtitle/url、なければpage_title
        if page.get('found_new_housing_subsidies'):
            for sub in page['found_new_housing_subsidies']:
                urls.append({
                    'url': sub.get('url', page.get('url', '')),
                    'title': sub.get('title', page.get('page_title', ''))
                })
        else:
            urls.append({
                'url': page.get('url', ''),
                'title': page.get('page_title', '')
            })
        # 既存の市区町村エントリを探す
        if pref not in pref_city_dict:
            pref_city_dict[pref] = []
        # city_nameが既にあればurlsを追加、なければ新規
        found = False
        for city_entry in pref_city_dict[pref]:
            if city_entry['city_name'] == city:
                city_entry['urls'].extend(urls)
                found = True
                break
        if not found:
            pref_city_dict[pref].append({
                'city_name': city,
                'urls': urls
            })
    city_urls_json_file = f"{base_filename}_merged_city_urls.json"
    with open(city_urls_json_file, 'w', encoding='utf-8') as f:
        json.dump(pref_city_dict, f, ensure_ascii=False, indent=2)
    print(f"✅ 都道府県→市区町村→URLリストJSON: {city_urls_json_file}")

def print_merge_statistics(merged_data, comprehensive_summary):
    """
    マージ統計を表示
    """
    merge_stats = merged_data['statistics']

    print(f"\n{'='*60}")
    print(f"📊 分類結果マージ統計")
    print(f"{'='*60}")

    print(f"元の個別ページ数: {merge_stats['original_count']}")
    print(f"一覧ページから抽出した個別ページ数: {merge_stats['extracted_count']}")
    print(f"重複除去後の統合個別ページ数: {merge_stats['merged_count']}")
    print(f"新規発見ページ数: {merge_stats['new_from_extraction']}")
    print(f"除去された重複数: {merge_stats['duplicate_removed']}")

    print(f"\n--- ソース別統計 ---")
    for source, count in comprehensive_summary['source_stats'].items():
        print(f"{source}: {count}件")

    print(f"\n--- 都道府県別上位10 ---")
    for i, (pref, count) in enumerate(list(comprehensive_summary['prefecture_stats'].items())[:10], 1):
        print(f"{i:2d}. {pref}: {count}件")

    if comprehensive_summary['confidence_stats']:
        conf_stats = comprehensive_summary['confidence_stats']
        print(f"\n--- 確信度統計 ---")
        print(f"平均: {conf_stats['average']:.3f}")
        print(f"最高: {conf_stats['max']:.3f}")
        print(f"最低: {conf_stats['min']:.3f}")
        print(f"高確信度(≥0.8): {conf_stats['high_confidence_count']}件")

    print(f"\n--- 補助金制度発見統計 ---")
    print(f"発見された補助金制度数: {comprehensive_summary['subsidy_titles_found']}")
    if comprehensive_summary['sample_titles']:
        print(f"制度例: {', '.join(comprehensive_summary['sample_titles'][:5])}")

def find_result_files():
    """
    結果ファイルを検索
    """
    files = {
        'classification': [],
        'extraction': []
    }

    # 分類結果ファイル
    for pattern in ['*_page_classification.json']:
        files['classification'].extend(Path('.').glob(pattern))

    # 抽出結果ファイル
    for pattern in ['*_extracted_all.json']:
        files['extraction'].extend(Path('.').glob(pattern))

    return files

def load_json_file(file_path):
    """
    JSONファイルを読み込み
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ ファイル読み込みエラー ({file_path}): {str(e)}")
        return []

def main():
    """
    メイン処理
    """
    print("🔗 分類結果マージツール")
    print("-" * 40)

    # 結果ファイルを検索
    result_files = find_result_files()

    if not result_files['classification']:
        print("❌ 分類結果ファイルが見つかりません (*_page_classification.json)")
        return

    print("利用可能な分類結果ファイル:")
    for i, file in enumerate(result_files['classification'], 1):
        print(f"{i}. {file.name}")

    try:
        choice = int(input("\nベースとなる分類結果ファイルを選択してください: ")) - 1
        if not (0 <= choice < len(result_files['classification'])):
            print("❌ 無効な選択です")
            return

        classification_file = result_files['classification'][choice]
        base_name = classification_file.stem.replace('_page_classification', '')

        print(f"\n📂 {classification_file.name} を読み込み中...")
        original_results = load_json_file(str(classification_file))

        if not original_results:
            print("❌ 分類結果が読み込めませんでした")
            return

        # 対応する抽出結果ファイルを検索
        extraction_file = Path(f"{base_name}_extracted_all.json")

        if extraction_file.exists():
            print(f"📂 {extraction_file.name} を読み込み中...")
            extracted_results = load_json_file(str(extraction_file))
        else:
            print("⚠️  対応する抽出結果ファイルが見つかりません。元の結果のみを処理します。")
            extracted_results = []

        print(f"\n🔄 結果をマージ中...")

        # 結果をマージ
        merged_data = merge_classification_results(original_results, extracted_results)

        # 包括的サマリーを作成
        comprehensive_summary = create_comprehensive_summary(merged_data)

        # 結果を保存
        save_merged_results(merged_data, comprehensive_summary, base_name)

        # 統計を表示
        print_merge_statistics(merged_data, comprehensive_summary)

        print(f"\n🎉 マージ完了！")
        print(f"📁 統合個別ページリスト: {base_name}_merged_individual_urls.txt")

    except ValueError:
        print("❌ 無効な入力です")
    except KeyboardInterrupt:
        print("\n⚠️  処理が中断されました")
    except Exception as e:
        print(f"❌ 予期しないエラー: {str(e)}")

if __name__ == '__main__':
    main()
