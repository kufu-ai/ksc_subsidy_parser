#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
一覧ページからURLを抽出して再分類するツール
"""

import pandas as pd
import json
import os
import time
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from html_fetcher import fetch_html
from page_classifier import classify_page_type
from pathlib import Path

def extract_urls_from_html(html_content, base_url, method="improved"):
    """
    HTMLからURLを抽出する

    Args:
        html_content (str): HTMLコンテンツ
        base_url (str): ベースURL
        method (str): 抽出方法 ("simple", "improved", "openai")

    Returns:
        list: 抽出されたURL一覧
    """
    if method == "openai":
        # OpenAI APIを使用
        try:
            from smart_url_extractor import extract_urls_with_openai
            result = extract_urls_with_openai(html_content, base_url)
            return [url['url'] for url in result['subsidy_related_urls']]
        except ImportError:
            print("⚠️  OpenAI抽出機能が利用できません。improved方式を使用します。")
            method = "improved"

    try:
        soup = BeautifulSoup(html_content, 'html.parser')

        if method == "improved":
            # ナビゲーション要素を除外
            exclude_selectors = [
                'nav', '.nav', '#nav', '.navigation',
                'header', '.header', '#header',
                'footer', '.footer', '#footer',
                '.sidebar', '#sidebar', '.side',
                '.breadcrumb', '.breadcrumbs',
                '.menu', '.global-menu', '.site-menu',
                '[role="navigation"]',
                '.sns', '.social'
            ]

            # 除外要素を削除
            for selector in exclude_selectors:
                for element in soup.select(selector):
                    element.decompose()

            # メインコンテンツエリアを特定
            main_content = None
            for selector in ['main', '[role="main"]', '.main-content', '.content', '#content', '.main']:
                main_element = soup.select_one(selector)
                if main_element:
                    main_content = main_element
                    break

            # メインコンテンツエリアから抽出
            if main_content:
                links = main_content.find_all('a', href=True)
                print(f"    🎯 メインコンテンツから抽出: {len(links)}件")
            else:
                # メインコンテンツが見つからない場合は残りのsoupから
                links = soup.find_all('a', href=True)
                print(f"    📄 全体から抽出: {len(links)}件")
        else:
            # 従来の方式
            links = soup.find_all('a', href=True)

        urls = set()
        for link in links:
            href = link.get('href')
            if href:
                # 相対URLを絶対URLに変換
                absolute_url = urljoin(base_url, href)
                urls.add(absolute_url)

        return list(urls)

    except Exception as e:
        print(f"HTML解析エラー: {str(e)}")
        return []

def filter_subsidy_related_urls(urls, keywords=None):
    """
    補助金関連のURLをフィルタリング

    Args:
        urls (list): URL一覧
        keywords (list): 除外キーワード

    Returns:
        list: フィルタリングされたURL一覧
    """
    if keywords is None:
        # 補助金関連のキーワード
        include_keywords = [
            '補助', '助成', '支援', '交付', '給付', '奨励',
            '制度', '事業', '申請', '募集', '対象', '要件',
            'subsidy', 'grant', 'support', 'aid', 'assistance',
            '住宅', '土地', '建設', '改修', '耐震', 'リフォーム'
        ]

        # 除外キーワード
        exclude_keywords = [
            'javascript:', 'mailto:', 'tel:', '#',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.csv',
            'facebook', 'twitter', 'instagram', 'youtube', 'line',
            'login', 'admin', 'search', 'sitemap',
            'privacy', 'contact', 'about', 'access',
            'rss', 'feed', 'print', 'mobile',
            'cookie', 'policy', 'guide', 'help',
            'inquiry', 'form', 'entry'
        ]
    else:
        include_keywords = keywords
        exclude_keywords = []

    filtered_urls = []
    priority_urls = []  # 優先度の高いURL
    secondary_urls = []  # 二次的なURL

    for url in urls:
        url_lower = url.lower()

        # 除外URLをスキップ
        if any(keyword in url_lower for keyword in exclude_keywords):
            continue

        # 同じページへの重複URLを除外（#付きなど）
        if '#' in url and url.split('#')[0] in [u.split('#')[0] for u in filtered_urls]:
            continue

        # 補助金関連キーワードが含まれるURLを優先
        if any(keyword in url_lower for keyword in include_keywords):
            priority_urls.append(url)
        # 同じドメインのHTMLページも含める（相対URLなど）
        elif url_lower.startswith('http') and not any(ext in url_lower for ext in ['.pdf', '.doc', '.xls', '.zip']):
            secondary_urls.append(url)

    # 優先度順に結合
    filtered_urls = priority_urls + secondary_urls

    # 重複削除（順序を保持）
    seen = set()
    unique_urls = []
    for url in filtered_urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)

    return unique_urls

def extract_and_classify_from_list_pages(classification_results, max_urls_per_page=50, delay=2, extraction_method="improved"):
    """
    一覧ページからURLを抽出して分類する

    Args:
        classification_results (list): 分類結果
        max_urls_per_page (int): 1ページあたりの最大URL数
        delay (int): API呼び出し間の待機時間（秒）
        extraction_method (str): URL抽出方法 ("simple", "improved", "openai")

    Returns:
        dict: 抽出・分類結果
    """
    # 一覧ページを抽出
    list_pages = [r for r in classification_results if r.get('page_type') == '一覧ページ']

    if not list_pages:
        print("❌ 一覧ページが見つかりませんでした")
        return {'extracted_results': [], 'statistics': {}}

    print(f"📋 一覧ページ数: {len(list_pages)}")

    all_extracted_results = []
    total_extracted_urls = 0

    for i, list_page in enumerate(list_pages, 1):
        print(f"\n{'='*60}")
        print(f"📄 一覧ページ {i}/{len(list_pages)}: {list_page.get('url', '')}")
        print(f"🏛️ {list_page.get('prefecture', '')} {list_page.get('city', '')}")
        print(f"{'='*60}")

        try:
            # HTMLを取得
            filename = f"list_page_{int(time.time())}_{i}.html"
            html_path = fetch_html(list_page['url'], filename)

            # HTMLからURLを抽出
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            extracted_urls = extract_urls_from_html(html_content, list_page['url'], extraction_method)
            print(f"🔗 抽出された総URL数: {len(extracted_urls)}")

            # 補助金関連URLをフィルタリング
            filtered_urls = filter_subsidy_related_urls(extracted_urls)
            print(f"✅ 補助金関連URL数: {len(filtered_urls)}")

            # 上限を適用
            if len(filtered_urls) > max_urls_per_page:
                filtered_urls = filtered_urls[:max_urls_per_page]
                print(f"⚠️  上限適用: {max_urls_per_page}件に制限")

            total_extracted_urls += len(filtered_urls)

            # 各URLを分類
            for j, url in enumerate(filtered_urls, 1):
                print(f"  🔍 {j}/{len(filtered_urls)}: {url[:80]}...")

                try:
                    # URL分類
                    classification_result = classify_page_type(url)

                    # 元の一覧ページ情報を追加
                    classification_result.update({
                        'parent_list_page_url': list_page['url'],
                        'parent_prefecture': list_page.get('prefecture', ''),
                        'parent_city': list_page.get('city', ''),
                        'extraction_order': j,
                        'extracted_from_list': True
                    })

                    all_extracted_results.append(classification_result)

                    print(f"    📝 判定: {classification_result.get('page_type', '不明')} (確信度: {classification_result.get('confidence', 0.0):.2f})")

                    # API負荷軽減のため待機
                    time.sleep(delay)

                except Exception as e:
                    print(f"    ❌ 分類エラー: {str(e)}")
                    continue

            # HTMLファイルを削除
            os.remove(html_path)

        except Exception as e:
            print(f"❌ 一覧ページ処理エラー: {str(e)}")
            continue

    # 統計情報を作成
    statistics = create_extraction_statistics(all_extracted_results, list_pages)

    return {
        'extracted_results': all_extracted_results,
        'statistics': statistics,
        'total_list_pages': len(list_pages),
        'total_extracted_urls': total_extracted_urls
    }

def create_extraction_statistics(extracted_results, original_list_pages):
    """
    抽出結果の統計を作成

    Args:
        extracted_results (list): 抽出・分類結果
        original_list_pages (list): 元の一覧ページ

    Returns:
        dict: 統計情報
    """
    stats = {
        'total_extracted': len(extracted_results),
        'by_page_type': {},
        'by_prefecture': {},
        'individual_pages_found': 0,
        'confidence_stats': {}
    }

    # ページタイプ別統計
    for result in extracted_results:
        page_type = result.get('page_type', '不明')
        stats['by_page_type'][page_type] = stats['by_page_type'].get(page_type, 0) + 1

    # 都道府県別統計
    for result in extracted_results:
        pref = result.get('parent_prefecture', '不明')
        stats['by_prefecture'][pref] = stats['by_prefecture'].get(pref, 0) + 1

    # 個別ページ数
    stats['individual_pages_found'] = stats['by_page_type'].get('個別ページ', 0)

    # 確信度統計
    confidences = [r.get('confidence', 0.0) for r in extracted_results if r.get('confidence') is not None]
    if confidences:
        stats['confidence_stats'] = {
            'average': sum(confidences) / len(confidences),
            'max': max(confidences),
            'min': min(confidences)
        }

    return stats

def save_extraction_results(results_data, base_filename):
    """
    抽出結果を保存

    Args:
        results_data (dict): 抽出結果データ
        base_filename (str): ベースファイル名
    """
    try:
        extracted_results = results_data['extracted_results']
        statistics = results_data['statistics']

        # すべての結果を保存
        all_results_file = f"{base_filename}_extracted_all.json"
        with open(all_results_file, 'w', encoding='utf-8') as f:
            json.dump(extracted_results, f, ensure_ascii=False, indent=2)
        print(f"✅ 全抽出結果保存: {all_results_file}")

        # 個別ページのみを抽出
        individual_pages = [r for r in extracted_results if r.get('page_type') == '個別ページ']

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

            # CSV形式でも保存
            df_individual = pd.DataFrame(individual_pages)
            individual_csv_file = f"{base_filename}_extracted_individual.csv"
            df_individual.to_csv(individual_csv_file, index=False, encoding='utf-8')
            print(f"✅ 抽出個別ページCSV: {individual_csv_file}")

        # 統計情報を保存
        stats_file = f"{base_filename}_extraction_stats.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(statistics, f, ensure_ascii=False, indent=2)
        print(f"✅ 統計情報保存: {stats_file}")

        # 統計表示
        print_extraction_statistics(statistics, results_data)

    except Exception as e:
        print(f"❌ 保存エラー: {str(e)}")

def print_extraction_statistics(statistics, results_data):
    """
    統計情報を表示
    """
    print(f"\n{'='*60}")
    print(f"📊 一覧ページURL抽出結果統計")
    print(f"{'='*60}")

    print(f"処理した一覧ページ数: {results_data['total_list_pages']}")
    print(f"抽出・分類したURL総数: {statistics['total_extracted']}")
    print(f"新たに発見した個別ページ数: {statistics['individual_pages_found']}")

    print(f"\n--- ページタイプ別 ---")
    for page_type, count in statistics['by_page_type'].items():
        print(f"{page_type}: {count}件")

    print(f"\n--- 都道府県別 ---")
    sorted_prefs = sorted(statistics['by_prefecture'].items(), key=lambda x: x[1], reverse=True)
    for pref, count in sorted_prefs[:10]:  # 上位10都道府県
        print(f"{pref}: {count}件")

    if statistics['confidence_stats']:
        conf_stats = statistics['confidence_stats']
        print(f"\n--- 確信度統計 ---")
        print(f"平均: {conf_stats['average']:.3f}")
        print(f"最高: {conf_stats['max']:.3f}")
        print(f"最低: {conf_stats['min']:.3f}")

def find_classification_files():
    """
    分類結果ファイルを検索
    """
    classification_files = []

    # 分類結果ファイルを検索
    for pattern in ['*_page_classification.json', '*_page_classification.csv']:
        classification_files.extend(Path('.').glob(pattern))

    return sorted(classification_files)

def load_classification_results(file_path):
    """
    分類結果ファイルを読み込み
    """
    try:
        if file_path.endswith('.json'):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        elif file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
            return df.to_dict('records')
        else:
            raise ValueError("サポートされていないファイル形式です")
    except Exception as e:
        print(f"❌ ファイル読み込みエラー: {str(e)}")
        return []

def main():
    """
    メイン処理
    """
    print("🔗 一覧ページURL抽出・分類ツール")
    print("-" * 50)

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
        choice = int(input("\n処理するファイルの番号を選択してください: ")) - 1
        if not (0 <= choice < len(classification_files)):
            print("❌ 無効な選択です")
            return

        selected_file = classification_files[choice]
        print(f"\n📂 {selected_file.name} を処理中...")

        # 分類結果を読み込み
        classification_results = load_classification_results(str(selected_file))

        if not classification_results:
            print("❌ 分類結果が読み込めませんでした")
            return

        # 抽出方法を選択
        print("\nURL抽出方法を選択してください:")
        print("1. 改良版BeautifulSoup（推奨・デフォルト）")
        print("   - ナビゲーション・サイドバーを除外")
        print("   - メインコンテンツエリアに特化")
        print("2. 従来版BeautifulSoup（シンプル）")
        print("3. OpenAI API（最高精度・コスト高）")

        method_choice = input("選択 (1-3): ").strip() or "1"
        method_map = {"1": "improved", "2": "simple", "3": "openai"}
        extraction_method = method_map.get(method_choice, "improved")

        # 設定
        max_urls = int(input("1つの一覧ページから抽出する最大URL数 (デフォルト: 50): ") or "50")
        delay = int(input("API呼び出し間隔（秒、デフォルト: 2): ") or "2")

        print(f"\n🚀 処理開始...")
        print(f"   - URL抽出方法: {extraction_method}")
        print(f"   - 最大URL数/ページ: {max_urls}")
        print(f"   - API呼び出し間隔: {delay}秒")

        # URL抽出・分類実行
        results_data = extract_and_classify_from_list_pages(
            classification_results,
            max_urls_per_page=max_urls,
            delay=delay,
            extraction_method=extraction_method
        )

        # 結果を保存
        base_filename = selected_file.stem
        save_extraction_results(results_data, base_filename)

        print(f"\n🎉 処理完了！")

    except ValueError:
        print("❌ 無効な入力です")
    except KeyboardInterrupt:
        print("\n⚠️  処理が中断されました")
    except Exception as e:
        print(f"❌ 予期しないエラー: {str(e)}")

if __name__ == '__main__':
    main()
