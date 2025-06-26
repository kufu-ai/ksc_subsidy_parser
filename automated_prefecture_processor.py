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
from page_classifier import classify_urls_from_file, save_classification_results
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
        'max_urls_per_city': 10,
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
            if city == "千葉市" or city == "銚子市":
                print(f"  {i}/{len(cities)}: {city} を検索中...")

                # search_subsidy_urls内で柔軟マッチング処理される
                urls = search_subsidy_urls(city, prefecture_name, max_results=settings['max_urls_per_city'])

                result_list.append({
                    "都道府県名": prefecture_name,
                    "city_name": city,
                    "補助金関連URL": urls
                })
                total_urls += len(urls)
                print(f"    📍 {len(urls)}件のURLを取得")

                # API負荷軽減
                time.sleep(1)

                #TODO: kesu 開発中は2件でスキップ
                # if i >= 2:
                #     print(f"    ⚠️  開発モード: {i}件で処理を停止")
                #     break

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
        output_file = f"{base_filename}_page_classification.json"
        save_classification_results(classification_results, output_file)

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
    found_new_housing_subsidiesを使用
    さらにリンク先が一覧ページの場合は無視する。
    """
    try:
        # 分類結果を読み込み
        classification_results = load_classification_results(classification_file)

        if not classification_results:
            return {
                'success': False,
                'error': '分類結果の読み込みに失敗'
            }

        # 一覧ページかつfound_new_housing_subsidiesが存在するページを抽出
        list_pages_with_subsidies = []
        for result in classification_results:
            if (result.get('page_type') == '新築住宅関連一覧ページ' and
                result.get('found_new_housing_subsidies') and
                len(result.get('found_new_housing_subsidies', [])) > 0):
                list_pages_with_subsidies.append(result)

        if not list_pages_with_subsidies:
            print("⚠️ 補助金が見つかった一覧ページがありませんでした")
            all_extracted_results = []
            statistics = create_extraction_statistics_from_found_subsidies(all_extracted_results, [])
            base_filename = Path(classification_file).stem
            save_extraction_results_from_found_subsidies(all_extracted_results, statistics, base_filename)
            return {
                'success': True,
                'data': {
                    'extracted_results': all_extracted_results,
                    'statistics': statistics,
                    'total_list_pages': 0,
                    'total_extracted_urls': 0
                },
                'total_extracted': 0
            }

        print(f"📋 補助金発見済み一覧ページ数: {len(list_pages_with_subsidies)}")

        all_extracted_results = []
        total_extracted_urls = 0

        for i, list_page in enumerate(list_pages_with_subsidies, 1):
            print(f"\n{'='*60}")
            print(f"📄 一覧ページ {i}/{len(list_pages_with_subsidies)}: {list_page.get('url', '')}")
            print(f"🏛️ {list_page.get('prefecture', '')} {list_page.get('city', '')}")

            found_subsidies = list_page.get('found_new_housing_subsidies', [])
            print(f"🔗 発見済み補助金数: {len(found_subsidies)}")
            print(f"{'='*60}")

            # found_new_housing_subsidiesから各URLを分類
            for j, subsidy_info in enumerate(found_subsidies, 1):
                url = subsidy_info.get('url', '')
                title = subsidy_info.get('title', '')

                if not url:
                    print(f"  ⚠️  {j}/{len(found_subsidies)}: URLが空のためスキップ - {title}")
                    continue

                print(f"  🔍 {j}/{len(found_subsidies)}: {title}")
                print(f"      URL: {url[:80]}...")

                try:
                    # URLを分類（page_classifier.pyのclassify_page_typeを使用）
                    from page_classifier import classify_page_type
                    classification_result = classify_page_type(url)

                    # 元の一覧ページ情報を追加
                    classification_result.update({
                        'parent_list_page_url': list_page['url'],
                        'parent_prefecture': list_page.get('prefecture', ''),
                        'parent_city': list_page.get('city', ''),
                        'subsidy_title_from_list': title,
                        'extraction_order': j,
                        'extracted_from_list': True
                    })

                    all_extracted_results.append(classification_result)
                    total_extracted_urls += 1

                    print(f"    📝 判定: {classification_result.get('page_type', '不明')} (確信度: {classification_result.get('confidence', 0.0):.2f})")

                    # API負荷軽減のため待機
                    time.sleep(settings['extraction_delay'])

                except Exception as e:
                    print(f"    ❌ 分類エラー: {str(e)}")
                    continue

        # 統計情報を作成
        statistics = create_extraction_statistics_from_found_subsidies(all_extracted_results, list_pages_with_subsidies)

        # 結果を保存
        base_filename = Path(classification_file).stem
        save_extraction_results_from_found_subsidies(all_extracted_results, statistics, base_filename)

        return {
            'success': True,
            'data': {
                'extracted_results': all_extracted_results,
                'statistics': statistics,
                'total_list_pages': len(list_pages_with_subsidies),
                'total_extracted_urls': total_extracted_urls
            },
            'total_extracted': total_extracted_urls
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def create_extraction_statistics_from_found_subsidies(extracted_results, original_list_pages):
    """
    found_new_housing_subsidiesからの抽出結果統計を作成
    """
    stats = {
        'total_extracted': len(extracted_results),
        'by_page_type': {},
        'by_prefecture': {},
        'individual_pages_found': 0,
        'confidence_stats': {},
        'original_list_pages': len(original_list_pages)
    }

    # ページタイプ別統計
    for result in extracted_results:
        page_type = result.get('page_type', '不明')
        stats['by_page_type'][page_type] = stats['by_page_type'].get(page_type, 0) + 1

    # 都道府県別統計
    for result in extracted_results:
        pref = result.get('parent_prefecture', '不明')
        stats['by_prefecture'][pref] = stats['by_prefecture'].get(pref, 0) + 1

    # 個別ページ数（新築住宅関連個別ページ）
    stats['individual_pages_found'] = stats['by_page_type'].get('新築住宅関連個別ページ', 0)

    # 確信度統計
    confidences = [r.get('confidence', 0.0) for r in extracted_results if r.get('confidence') is not None]
    if confidences:
        stats['confidence_stats'] = {
            'average': sum(confidences) / len(confidences),
            'max': max(confidences),
            'min': min(confidences)
        }

    return stats

def save_extraction_results_from_found_subsidies(extracted_results, statistics, base_filename):
    """
    found_new_housing_subsidiesからの抽出結果を保存
    """
    try:
        # すべての結果を保存
        all_results_file = f"{base_filename}_extracted_all.json"
        with open(all_results_file, 'w', encoding='utf-8') as f:
            json.dump(extracted_results, f, ensure_ascii=False, indent=2)
        print(f"✅ 全抽出結果保存: {all_results_file}")

        # 個別ページのみを抽出
        individual_pages = [r for r in extracted_results if r.get('page_type') == '新築住宅関連個別ページ']

        if individual_pages:
            # 個別ページURLリスト
            individual_urls_file = f"{base_filename}_extracted_individual_urls.txt"
            with open(individual_urls_file, 'w', encoding='utf-8') as f:
                for page in individual_pages:
                    f.write(f"{page.get('url', '')}\n")
            print(f"✅ 抽出個別ページURLリスト: {individual_urls_file} ({len(individual_pages)}件)")

            # 個別ページ詳細
            individual_detailed_file = f"{base_filename}_extracted_individual_detailed.json"
            with open(individual_detailed_file, 'w', encoding='utf-8') as f:
                json.dump(individual_pages, f, ensure_ascii=False, indent=2)
            print(f"✅ 抽出個別ページ詳細: {individual_detailed_file}")

        # 統計情報を保存
        stats_file = f"{base_filename}_extraction_stats.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(statistics, f, ensure_ascii=False, indent=2)
        print(f"✅ 統計情報保存: {stats_file}")

        # 統計表示
        print(f"\n📊 抽出統計:")
        print(f"  - 処理対象一覧ページ数: {statistics['original_list_pages']}")
        print(f"  - 総抽出URL数: {statistics['total_extracted']}")
        print(f"  - 新築住宅関連個別ページ数: {statistics['individual_pages_found']}")

        if statistics.get('confidence_stats'):
            conf_stats = statistics['confidence_stats']
            print(f"  - 平均確信度: {conf_stats['average']:.2f}")

        print(f"\n📄 ページタイプ別:")
        for page_type, count in statistics['by_page_type'].items():
            print(f"  - {page_type}: {count}件")

    except Exception as e:
        print(f"❌ 保存エラー: {str(e)}")

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