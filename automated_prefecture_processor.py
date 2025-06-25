#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
都道府県名を入力するだけで全ての処理を自動実行する統合ツール
処理フロー：
1. 補助金URL検索 (search_subsidy.py)
2. ページ分類 (page_classifier.py)
3. 一覧ページからURL抽出 (extract_urls_from_list_pages.py)
4. 結果マージ (merge_classification_results.py)
5. 最終URLリスト生成
"""

import os
import sys
import time
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

# 必要なモジュールをインポート
from search_subsidy import get_cities_by_prefecture, search_subsidy_urls, get_flexible_city_name, get_official_domain
from page_classifier import classify_urls_from_file, save_classification_results, extract_individual_page_urls
from extract_urls_from_list_pages import extract_and_classify_from_list_pages, save_extraction_results, load_classification_results
from merge_classification_results import merge_classification_results, create_comprehensive_summary, save_merged_results

def process_prefecture(prefecture_name, settings=None):
    """
    都道府県全体の処理を自動実行

    Args:
        prefecture_name (str): 都道府県名
        settings (dict): 処理設定

    Returns:
        dict: 処理結果
    """
    # デフォルト設定
    default_settings = {
        'max_cities': None,  # None = 全市区町村
        'max_urls_per_city': 20,
        'max_urls_per_list_page': 50,
        'classification_delay': 5,
        'extraction_delay': 5,  # デフォルトを5秒に変更
        'use_openai_for_extraction': True,
        'save_intermediate_files': True
    }

    if settings:
        default_settings.update(settings)

    settings = default_settings

    print(f"🚀 {prefecture_name} の自動処理を開始します")
    print("=" * 60)

    # タイムスタンプ付きのベースファイル名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_filename = f"{prefecture_name}_{timestamp}"

    results = {
        'prefecture': prefecture_name,
        'timestamp': timestamp,
        'settings': settings,
        'step_results': {}
    }

    try:
        # ステップ1: 補助金URL検索
        print(f"\n📋 ステップ1: {prefecture_name} の市区町村別補助金URL検索")
        print("-" * 50)

        search_results = step1_search_subsidy_urls(prefecture_name, settings)
        results['step_results']['search'] = search_results

        if not search_results['success']:
            print(f"❌ URL検索に失敗しました: {search_results['error']}")
            return results

        search_file = search_results['output_file']
        print(f"✅ URL検索完了: {search_file} ({search_results['total_urls']}件のURL)")

        # ステップ2: ページ分類
        print(f"\n🔍 ステップ2: ページタイプ分類")
        print("-" * 50)

        classification_results = step2_classify_pages(search_file, settings)
        results['step_results']['classification'] = classification_results

        if not classification_results['success']:
            print(f"❌ ページ分類に失敗しました: {classification_results['error']}")
            return results

        classification_file = classification_results['output_file']
        print(f"✅ ページ分類完了: {classification_file}")

        # ステップ3: 一覧ページからURL抽出
        print(f"\n🔗 ステップ3: 一覧ページからURL抽出・分類")
        print("-" * 50)

        extraction_results = step3_extract_from_list_pages(classification_file, settings)
        results['step_results']['extraction'] = extraction_results

        if not extraction_results['success']:
            print(f"❌ URL抽出に失敗しました: {extraction_results['error']}")
            return results

        print(f"✅ URL抽出完了: {extraction_results['total_extracted']}件の新規URL")

        # ステップ4: 結果マージ
        print(f"\n🔄 ステップ4: 結果マージ・統合")
        print("-" * 50)

        merge_results = step4_merge_results(classification_file, extraction_results['data'], base_filename, settings)
        results['step_results']['merge'] = merge_results

        if not merge_results['success']:
            print(f"❌ 結果マージに失敗しました: {merge_results['error']}")
            return results

        final_file = merge_results['final_url_file']
        print(f"✅ 結果マージ完了: {final_file} ({merge_results['total_individual_pages']}件の個別ページ)")

        # 最終サマリー表示
        print_final_summary(results)

        results['success'] = True
        results['final_url_file'] = final_file

        return results

    except Exception as e:
        error_msg = f"処理中にエラーが発生しました: {str(e)}"
        print(f"❌ {error_msg}")
        results['success'] = False
        results['error'] = error_msg
        return results

def step1_search_subsidy_urls(prefecture_name, settings):
    """
    ステップ1: 補助金URL検索
    """
    try:
        from search_subsidy import get_cities_by_prefecture, search_subsidy_urls

        # 市区町村リストを取得
        cities = get_cities_by_prefecture(prefecture_name)
        print(f"対象市区町村数: {len(cities)}")

        # 上限設定の適用
        if settings['max_cities'] and len(cities) > settings['max_cities']:
            cities = cities[:settings['max_cities']]
            print(f"⚠️  処理を {settings['max_cities']} 市区町村に制限")

        result_list = []
        total_urls = 0

        for i, city in enumerate(cities, 1):
            print(f"  {i}/{len(cities)}: {city} を検索中...")

            # search_subsidy_urls内で柔軟マッチング処理される
            urls = search_subsidy_urls(city, prefecture_name, max_results=settings['max_urls_per_city'])

            result_list.append({
                "都道府県名": prefecture_name,
                "市区町村名": city,
                "補助金関連URL": urls
            })
            total_urls += len(urls)
            print(f"    📍 {len(urls)}件のURLを取得")

            # API負荷軽減
            time.sleep(1)

            #TODO: kesu 開発中は2件でスキップ
            if i >= 2:
                print(f"    ⚠️  開発モード: {i}件で処理を停止")
                break

        # 結果を保存
        output_json = f"{prefecture_name}_subsidy_urls.json"
        output_csv = f"{prefecture_name}_subsidy_urls.csv"

        df_result = pd.DataFrame(result_list)
        df_result.to_json(output_json, force_ascii=False, orient="records", indent=2)
        df_result.to_csv(output_csv, index=False, encoding='utf-8')

        return {
            'success': True,
            'output_file': output_json,
            'total_cities': len(cities),
            'total_urls': total_urls
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def step2_classify_pages(search_file, settings):
    """
    ステップ2: ページタイプ分類
    """
    try:
        # 分類実行
        classification_results = classify_urls_from_file(search_file)

        if not classification_results:
            return {
                'success': False,
                'error': 'ページ分類結果が空です'
            }

        # 結果を保存
        base_filename = Path(search_file).stem
        output_csv = f"{base_filename}_page_classification.csv"
        save_classification_results(classification_results, output_csv)

        # 個別ページも抽出
        extract_individual_page_urls(classification_results, output_csv)

        output_file = f"{base_filename}_page_classification.json"

        # 統計
        page_types = {}
        for result in classification_results:
            page_type = result.get('page_type', '不明')
            page_types[page_type] = page_types.get(page_type, 0) + 1

        return {
            'success': True,
            'output_file': output_file,
            'total_classified': len(classification_results),
            'page_types': page_types
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def step3_extract_from_list_pages(classification_file, settings):
    """
    ステップ3: 一覧ページからURL抽出
    """
    try:
        # 分類結果を読み込み
        classification_results = load_classification_results(classification_file)

        if not classification_results:
            return {
                'success': False,
                'error': '分類結果の読み込みに失敗'
            }

        # 抽出方法を設定
        extraction_method = "openai" if settings['use_openai_for_extraction'] else "improved"

        # URL抽出・分類実行
        extraction_data = extract_and_classify_from_list_pages(
            classification_results,
            max_urls_per_page=settings['max_urls_per_list_page'],
            delay=settings['extraction_delay'],
            extraction_method=extraction_method
        )

        # 結果を保存
        base_filename = Path(classification_file).stem
        save_extraction_results(extraction_data, base_filename)

        return {
            'success': True,
            'data': extraction_data,
            'total_extracted': extraction_data['total_extracted_urls']
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def step4_merge_results(classification_file, extraction_data, base_filename, settings):
    """
    ステップ4: 結果マージ
    """
    try:
        # 元の分類結果を読み込み
        original_results = load_classification_results(classification_file)
        extracted_results = extraction_data['extracted_results']

        # マージ実行
        merged_data = merge_classification_results(original_results, extracted_results)

        # 包括的サマリー作成
        comprehensive_summary = create_comprehensive_summary(merged_data)

        # 結果を保存
        save_merged_results(merged_data, comprehensive_summary, base_filename)

        final_url_file = f"{base_filename}_merged_individual_urls.txt"

        return {
            'success': True,
            'final_url_file': final_url_file,
            'total_individual_pages': merged_data['statistics']['merged_count'],
            'statistics': merged_data['statistics']
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def print_final_summary(results):
    """
    最終サマリーを表示
    """
    print(f"\n{'='*60}")
    print(f"🎉 {results['prefecture']} の処理が完了しました！")
    print(f"{'='*60}")

    # 各ステップの結果
    steps = ['search', 'classification', 'extraction', 'merge']
    step_names = ['URL検索', 'ページ分類', 'URL抽出', '結果マージ']

    for step, name in zip(steps, step_names):
        step_result = results['step_results'].get(step, {})
        if step_result.get('success'):
            print(f"✅ {name}: 成功")
        else:
            print(f"❌ {name}: 失敗")

    # 最終統計
    if results.get('success'):
        merge_stats = results['step_results']['merge']['statistics']
        print(f"\n📊 最終統計:")
        print(f"  - 初回検索由来の個別ページ: {merge_stats['original_count']}件")
        print(f"  - 一覧ページ抽出由来: {merge_stats['extracted_count']}件")
        print(f"  - 重複除去後の総個別ページ数: {merge_stats['merged_count']}件")
        print(f"  - 新規発見ページ数: {merge_stats['new_from_extraction']}件")

        print(f"\n💾 最終URLリスト: {results['final_url_file']}")

def interactive_prefecture_processor():
    """
    対話的な都道府県処理
    """
    print("🏛️ 都道府県別補助金URL統合処理ツール")
    print("=" * 50)

    # 都道府県名を入力
    prefecture_name = input("処理する都道府県名を入力してください: ").strip()

    if not prefecture_name:
        print("❌ 都道府県名が入力されていません")
        return

    # 設定を確認
    print(f"\n⚙️  処理設定:")
    print(f"1. URL抽出にOpenAI APIを使用（推奨）")
    print(f"2. 処理する市区町村数: 全て")
    print(f"3. API呼び出し間隔: 分類5秒、抽出5秒")

    use_custom = input("\n設定を変更しますか？ (y/N): ").strip().lower()

    settings = {}
    if use_custom == 'y':
        try:
            max_cities = input("処理する最大市区町村数 (空白=全て): ").strip()
            settings['max_cities'] = int(max_cities) if max_cities else None

            use_openai = input("URL抽出にOpenAI APIを使用しますか？ (Y/n): ").strip().lower()
            settings['use_openai_for_extraction'] = use_openai != 'n'

            classification_delay = input("分類API呼び出し間隔（秒、デフォルト5): ").strip()
            settings['classification_delay'] = int(classification_delay) if classification_delay else 5

            extraction_delay = input("抽出API呼び出し間隔（秒、デフォルト5): ").strip()
            settings['extraction_delay'] = int(extraction_delay) if extraction_delay else 5

        except ValueError:
            print("⚠️  無効な入力がありました。デフォルト設定を使用します。")
            settings = {}

    # 確認
    print(f"\n🚀 {prefecture_name} の処理を開始します...")
    confirm = input("よろしいですか？ (Y/n): ").strip().lower()

    if confirm == 'n':
        print("❌ 処理をキャンセルしました")
        return

    # 処理実行
    start_time = time.time()
    results = process_prefecture(prefecture_name, settings)
    end_time = time.time()

    # 処理時間表示
    elapsed_time = end_time - start_time
    print(f"\n⏱️  総処理時間: {elapsed_time/60:.1f}分")

    if results.get('success'):
        print(f"🎉 処理が正常に完了しました！")
        print(f"📁 最終結果: {results['final_url_file']}")
    else:
        print(f"❌ 処理に失敗しました: {results.get('error', '不明なエラー')}")

def main():
    """
    メイン処理
    """
    try:
        if len(sys.argv) > 1:
            # コマンドライン引数から都道府県名を取得
            prefecture_name = sys.argv[1]
            results = process_prefecture(prefecture_name)
        else:
            # 対話的モード
            interactive_prefecture_processor()

    except KeyboardInterrupt:
        print("\n⚠️  処理が中断されました")
    except Exception as e:
        print(f"❌ 予期しないエラー: {str(e)}")

if __name__ == '__main__':
    main()