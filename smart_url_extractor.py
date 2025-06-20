#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OpenAI APIを使用した高精度URL抽出ツール
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
from openai_handler import client
from pathlib import Path

# OpenAI APIを使ったURL抽出プロンプト
URL_EXTRACTION_PROMPT = """
あなたは自治体の補助金情報サイトの専門家です。

以下のHTMLコンテンツを分析し、補助金制度に関連するリンクのみを抽出してください。

**抽出対象のリンク：**
- 具体的な補助金制度の詳細ページへのリンク
- 補助金の申請ページへのリンク
- 補助金制度の一覧ページへのリンク
- 各種支援制度の説明ページへのリンク

**除外すべきリンク：**
- ナビゲーションバーのリンク（「ホーム」「お知らせ」「組織案内」など）
- サイドバーの一般的なリンク
- フッターのリンク（「プライバシーポリシー」「サイトマップ」など）
- 外部サイトへのリンク（SNS、他自治体など）
- ファイルダウンロードリンク（PDF、Word等）
- 一般的な行政サービスのリンク（戸籍、税務など）

**出力形式：**
以下のJSON形式で回答してください：
{
  "subsidy_related_urls": [
    {
      "url": "抽出したURL",
      "link_text": "リンクのテキスト",
      "relevance_score": 0.0-1.0の関連度スコア,
      "reasoning": "抽出理由（日本語50文字以内）"
    }
  ],
  "page_analysis": {
    "total_links_found": 全リンク数,
    "subsidy_links_extracted": 抽出したリンク数,
    "main_content_area_identified": "メインコンテンツエリアを特定できたかどうか"
  }
}

関連性スコアは以下の基準で設定してください：
- 0.9-1.0: 明確に特定の補助金制度への直接リンク
- 0.7-0.8: 補助金一覧や支援制度のカテゴリページ
- 0.5-0.6: 関連する可能性のあるページ（要確認）
- 0.0-0.4: 関連性が低い（通常は除外）

0.5以上のスコアのリンクのみを抽出してください。
"""

def extract_urls_with_openai(html_content, base_url, max_content_length=40000):
    """
    OpenAI APIを使ってURLを抽出

    Args:
        html_content (str): HTMLコンテンツ
        base_url (str): ベースURL
        max_content_length (int): 最大コンテンツ長

    Returns:
        dict: 抽出結果
    """
    try:
        # HTMLが長すぎる場合は制限
        if len(html_content) > max_content_length:
            # メインコンテンツを優先的に取得
            soup = BeautifulSoup(html_content, 'html.parser')

            # メインコンテンツエリアを特定
            main_content = None
            for selector in ['main', '[role="main"]', '.main-content', '.content', '#content', '.main']:
                main_element = soup.select_one(selector)
                if main_element:
                    main_content = str(main_element)
                    break

            if main_content:
                html_content = main_content[:max_content_length]
            else:
                html_content = html_content[:max_content_length]

            html_content += "\n...(コンテンツが長いため省略されました)"

        # OpenAI APIでURL抽出
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": URL_EXTRACTION_PROMPT
                },
                {
                    "role": "user",
                    "content": f"ベースURL: {base_url}\n\n以下のHTMLコンテンツから補助金関連URLを抽出してください：\n\n{html_content}"
                }
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "url_extraction",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "subsidy_related_urls": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "url": {"type": "string"},
                                        "link_text": {"type": "string"},
                                        "relevance_score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                                        "reasoning": {"type": "string"}
                                    },
                                    "required": ["url", "link_text", "relevance_score", "reasoning"],
                                    "additionalProperties": False
                                }
                            },
                            "page_analysis": {
                                "type": "object",
                                "properties": {
                                    "total_links_found": {"type": "integer"},
                                    "subsidy_links_extracted": {"type": "integer"},
                                    "main_content_area_identified": {"type": "string"}
                                },
                                "required": ["total_links_found", "subsidy_links_extracted", "main_content_area_identified"],
                                "additionalProperties": False
                            }
                        },
                        "required": ["subsidy_related_urls", "page_analysis"],
                        "additionalProperties": False
                    }
                }
            },
            max_tokens=2000,
            temperature=0.1
        )

        # レスポンスをパース
        response_content = response.choices[0].message.content
        result = json.loads(response_content)

        # URLを絶対URLに変換
        processed_urls = []
        for url_info in result['subsidy_related_urls']:
            original_url = url_info['url']
            absolute_url = urljoin(base_url, original_url)

            url_info['url'] = absolute_url
            url_info['original_url'] = original_url
            processed_urls.append(url_info)

        result['subsidy_related_urls'] = processed_urls
        return result

    except Exception as e:
        print(f"OpenAI URL抽出エラー: {str(e)}")
        return {
            'subsidy_related_urls': [],
            'page_analysis': {
                'total_links_found': 0,
                'subsidy_links_extracted': 0,
                'main_content_area_identified': 'エラーが発生しました'
            },
            'error': str(e)
        }

def extract_urls_with_beautifulsoup_improved(html_content, base_url):
    """
    改良されたBeautifulSoupによるURL抽出（比較用）

    Args:
        html_content (str): HTMLコンテンツ
        base_url (str): ベースURL

    Returns:
        dict: 抽出結果
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')

        # 除外すべき要素を特定
        exclude_selectors = [
            'nav', '.nav', '#nav', '.navigation',
            'header', '.header', '#header',
            'footer', '.footer', '#footer',
            '.sidebar', '#sidebar', '.side',
            '.breadcrumb', '.breadcrumbs',
            '.menu', '.global-menu',
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

        # メインコンテンツエリアが見つからない場合はbody全体を使用
        if main_content is None:
            main_content = soup.find('body') or soup

        # リンクを抽出
        links = main_content.find_all('a', href=True)

        # 補助金関連キーワード
        include_keywords = [
            '補助', '助成', '支援', '交付', '給付', '奨励',
            '制度', '事業', '申請', '募集', '対象',
            'subsidy', 'grant', 'support', 'aid'
        ]

        exclude_keywords = [
            'javascript:', 'mailto:', 'tel:', '#',
            '.pdf', '.doc', '.xls', '.zip', '.csv',
            'facebook', 'twitter', 'instagram', 'youtube',
            'login', 'admin', 'search', 'sitemap',
            'privacy', 'contact', 'about', 'access'
        ]

        extracted_urls = []

        for link in links:
            href = link.get('href', '')
            text = link.get_text(strip=True)

            # 除外キーワードチェック
            if any(keyword in href.lower() for keyword in exclude_keywords):
                continue

            # 空のリンクやアンカーのみは除外
            if not href or href == '#':
                continue

            # 絶対URLに変換
            absolute_url = urljoin(base_url, href)

            # 関連性スコアを計算
            relevance_score = 0.0
            reasoning = ""

            # テキストとURLで関連性を判定
            combined_text = (text + " " + href).lower()
            matching_keywords = [kw for kw in include_keywords if kw in combined_text]

            if matching_keywords:
                relevance_score = min(0.7, 0.4 + len(matching_keywords) * 0.1)
                reasoning = f"キーワード一致: {', '.join(matching_keywords[:2])}"
            elif any(word in combined_text for word in ['制度', '事業', '申請', '募集']):
                relevance_score = 0.5
                reasoning = "関連する可能性あり"

            if relevance_score >= 0.5:
                extracted_urls.append({
                    'url': absolute_url,
                    'link_text': text,
                    'relevance_score': relevance_score,
                    'reasoning': reasoning
                })

        return {
            'subsidy_related_urls': extracted_urls,
            'page_analysis': {
                'total_links_found': len(links),
                'subsidy_links_extracted': len(extracted_urls),
                'main_content_area_identified': 'BeautifulSoup改良版で処理'
            }
        }

    except Exception as e:
        print(f"BeautifulSoup改良版エラー: {str(e)}")
        return {
            'subsidy_related_urls': [],
            'page_analysis': {
                'total_links_found': 0,
                'subsidy_links_extracted': 0,
                'main_content_area_identified': 'エラーが発生しました'
            },
            'error': str(e)
        }

def compare_extraction_methods(html_content, base_url):
    """
    OpenAIとBeautifulSoupの抽出結果を比較

    Args:
        html_content (str): HTMLコンテンツ
        base_url (str): ベースURL

    Returns:
        dict: 比較結果
    """
    print("  🤖 OpenAI APIで抽出中...")
    openai_result = extract_urls_with_openai(html_content, base_url)

    print("  🔍 BeautifulSoup改良版で抽出中...")
    bs_result = extract_urls_with_beautifulsoup_improved(html_content, base_url)

    # 結果を比較
    openai_urls = set(url['url'] for url in openai_result['subsidy_related_urls'])
    bs_urls = set(url['url'] for url in bs_result['subsidy_related_urls'])

    comparison = {
        'openai_count': len(openai_urls),
        'beautifulsoup_count': len(bs_urls),
        'common_urls': list(openai_urls & bs_urls),
        'openai_only': list(openai_urls - bs_urls),
        'beautifulsoup_only': list(bs_urls - openai_urls),
        'openai_result': openai_result,
        'beautifulsoup_result': bs_result
    }

    return comparison

def smart_extract_and_classify_from_list_pages(classification_results, extraction_method="openai", max_urls_per_page=30, delay=3):
    """
    高精度抽出を使って一覧ページからURLを抽出・分類

    Args:
        classification_results (list): 分類結果
        extraction_method (str): "openai", "beautifulsoup", "compare"
        max_urls_per_page (int): 1ページあたりの最大URL数
        delay (int): API呼び出し間の待機時間（秒）

    Returns:
        dict: 抽出・分類結果
    """
    # 一覧ページを抽出
    list_pages = [r for r in classification_results if r.get('page_type') == '一覧ページ']

    if not list_pages:
        print("❌ 一覧ページが見つかりませんでした")
        return {'extracted_results': [], 'statistics': {}}

    print(f"📋 一覧ページ数: {len(list_pages)}")
    print(f"🔧 抽出方法: {extraction_method}")

    all_extracted_results = []
    extraction_details = []
    total_extracted_urls = 0

    for i, list_page in enumerate(list_pages, 1):
        print(f"\n{'='*60}")
        print(f"📄 一覧ページ {i}/{len(list_pages)}: {list_page.get('url', '')}")
        print(f"🏛️ {list_page.get('prefecture', '')} {list_page.get('city', '')}")
        print(f"{'='*60}")

        try:
            # HTMLを取得
            filename = f"smart_list_page_{int(time.time())}_{i}.html"
            html_path = fetch_html(list_page['url'], filename)

            # HTMLを読み込み
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            # 抽出方法に応じて処理
            if extraction_method == "openai":
                extraction_result = extract_urls_with_openai(html_content, list_page['url'])
                filtered_urls = [url['url'] for url in extraction_result['subsidy_related_urls']]
            elif extraction_method == "beautifulsoup":
                extraction_result = extract_urls_with_beautifulsoup_improved(html_content, list_page['url'])
                filtered_urls = [url['url'] for url in extraction_result['subsidy_related_urls']]
            elif extraction_method == "compare":
                comparison = compare_extraction_methods(html_content, list_page['url'])
                extraction_result = comparison
                # OpenAI結果を優先使用
                filtered_urls = [url['url'] for url in comparison['openai_result']['subsidy_related_urls']]

            print(f"✅ 抽出されたURL数: {len(filtered_urls)}")

            # 上限を適用
            if len(filtered_urls) > max_urls_per_page:
                filtered_urls = filtered_urls[:max_urls_per_page]
                print(f"⚠️  上限適用: {max_urls_per_page}件に制限")

            total_extracted_urls += len(filtered_urls)

            # 抽出詳細を保存
            extraction_details.append({
                'list_page_url': list_page['url'],
                'extraction_method': extraction_method,
                'extraction_result': extraction_result
            })

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
                        'extracted_from_list': True,
                        'extraction_method': extraction_method
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
    statistics = create_smart_extraction_statistics(all_extracted_results, list_pages, extraction_details)

    return {
        'extracted_results': all_extracted_results,
        'extraction_details': extraction_details,
        'statistics': statistics,
        'total_list_pages': len(list_pages),
        'total_extracted_urls': total_extracted_urls
    }

def create_smart_extraction_statistics(extracted_results, original_list_pages, extraction_details):
    """
    高精度抽出の統計を作成
    """
    stats = {
        'total_extracted': len(extracted_results),
        'by_page_type': {},
        'by_prefecture': {},
        'individual_pages_found': 0,
        'confidence_stats': {},
        'extraction_method_stats': {}
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

    # 抽出方法別統計
    for detail in extraction_details:
        result = detail['extraction_result']
        if 'page_analysis' in result:
            analysis = result['page_analysis']
            stats['extraction_method_stats'][detail['list_page_url']] = {
                'total_links': analysis.get('total_links_found', 0),
                'extracted_links': analysis.get('subsidy_links_extracted', 0),
                'extraction_rate': analysis.get('subsidy_links_extracted', 0) / max(analysis.get('total_links_found', 1), 1)
            }

    return stats

def save_smart_extraction_results(results_data, base_filename):
    """
    高精度抽出結果を保存
    """
    try:
        extracted_results = results_data['extracted_results']
        statistics = results_data['statistics']
        extraction_details = results_data['extraction_details']

        # すべての結果を保存
        all_results_file = f"{base_filename}_smart_extracted_all.json"
        with open(all_results_file, 'w', encoding='utf-8') as f:
            json.dump(extracted_results, f, ensure_ascii=False, indent=2)
        print(f"✅ 全抽出結果保存: {all_results_file}")

        # 個別ページのみを抽出
        individual_pages = [r for r in extracted_results if r.get('page_type') == '個別ページ']

        if individual_pages:
            # 個別ページURLリスト
            individual_urls_file = f"{base_filename}_smart_individual_urls.txt"
            with open(individual_urls_file, 'w', encoding='utf-8') as f:
                for page in individual_pages:
                    f.write(f"{page.get('url', '')}\n")
            print(f"✅ 高精度個別ページURLリスト: {individual_urls_file} ({len(individual_pages)}件)")

            # 個別ページ詳細
            individual_detailed_file = f"{base_filename}_smart_individual_detailed.json"
            with open(individual_detailed_file, 'w', encoding='utf-8') as f:
                json.dump(individual_pages, f, ensure_ascii=False, indent=2)
            print(f"✅ 高精度個別ページ詳細: {individual_detailed_file}")

        # 抽出詳細情報
        extraction_details_file = f"{base_filename}_smart_extraction_details.json"
        with open(extraction_details_file, 'w', encoding='utf-8') as f:
            json.dump(extraction_details, f, ensure_ascii=False, indent=2)
        print(f"✅ 抽出詳細情報: {extraction_details_file}")

        # 統計情報を保存
        stats_file = f"{base_filename}_smart_extraction_stats.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(statistics, f, ensure_ascii=False, indent=2)
        print(f"✅ 統計情報保存: {stats_file}")

        # 統計表示
        print_smart_extraction_statistics(statistics, results_data)

    except Exception as e:
        print(f"❌ 保存エラー: {str(e)}")

def print_smart_extraction_statistics(statistics, results_data):
    """
    高精度抽出統計情報を表示
    """
    print(f"\n{'='*60}")
    print(f"📊 高精度URL抽出結果統計")
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

    # 抽出効率統計
    extraction_stats = statistics['extraction_method_stats']
    if extraction_stats:
        total_links = sum(stat['total_links'] for stat in extraction_stats.values())
        total_extracted = sum(stat['extracted_links'] for stat in extraction_stats.values())
        avg_extraction_rate = sum(stat['extraction_rate'] for stat in extraction_stats.values()) / len(extraction_stats)

        print(f"\n--- 抽出効率統計 ---")
        print(f"総リンク数: {total_links}")
        print(f"抽出リンク数: {total_extracted}")
        print(f"平均抽出率: {avg_extraction_rate:.3f}")

def main():
    """
    メイン処理
    """
    print("🧠 高精度URL抽出・分類ツール")
    print("-" * 50)

    # 分類結果ファイルを検索
    classification_files = []
    for pattern in ['*_page_classification.json', '*_page_classification.csv']:
        classification_files.extend(Path('.').glob(pattern))

    if not classification_files:
        print("❌ 分類結果ファイルが見つかりません")
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

        # 分類結果を読み込み
        if selected_file.suffix == '.json':
            with open(selected_file, 'r', encoding='utf-8') as f:
                classification_results = json.load(f)
        else:
            df = pd.read_csv(selected_file)
            classification_results = df.to_dict('records')

        if not classification_results:
            print("❌ 分類結果が読み込めませんでした")
            return

        # 抽出方法を選択
        print("\n抽出方法を選択してください:")
        print("1. OpenAI API（高精度・推奨）")
        print("2. BeautifulSoup改良版（高速・無料）")
        print("3. 比較モード（両方実行して比較）")

        method_choice = input("選択 (1-3): ").strip()
        method_map = {"1": "openai", "2": "beautifulsoup", "3": "compare"}
        extraction_method = method_map.get(method_choice, "openai")

        # 設定
        max_urls = int(input("1つの一覧ページから抽出する最大URL数 (デフォルト: 30): ") or "30")
        delay = int(input("API呼び出し間隔（秒、デフォルト: 3): ") or "3")

        print(f"\n🚀 処理開始...")
        print(f"   - 抽出方法: {extraction_method}")
        print(f"   - 最大URL数/ページ: {max_urls}")
        print(f"   - API呼び出し間隔: {delay}秒")

        # 高精度抽出・分類実行
        results_data = smart_extract_and_classify_from_list_pages(
            classification_results,
            extraction_method=extraction_method,
            max_urls_per_page=max_urls,
            delay=delay
        )

        # 結果を保存
        base_filename = f"{selected_file.stem}_{extraction_method}"
        save_smart_extraction_results(results_data, base_filename)

        print(f"\n🎉 処理完了！")

    except ValueError:
        print("❌ 無効な入力です")
    except KeyboardInterrupt:
        print("\n⚠️  処理が中断されました")
    except Exception as e:
        print(f"❌ 予期しないエラー: {str(e)}")

if __name__ == '__main__':
    main()
