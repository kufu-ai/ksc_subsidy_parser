#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
高精度URL抽出機能のテスト用スクリプト
"""

import json
from smart_url_extractor import extract_urls_with_openai, extract_urls_with_beautifulsoup_improved, compare_extraction_methods
from html_fetcher import fetch_html

def test_extraction_methods():
    """
    抽出方法のテスト
    """
    print("🧪 URL抽出精度テスト")
    print("-" * 50)

    # テスト用URL（手動で入力）
    test_url = input("テスト対象のURL（一覧ページ）を入力してください: ").strip()

    if not test_url:
        print("❌ URLが入力されませんでした")
        return

    try:
        # HTMLを取得
        print(f"📥 HTMLを取得中: {test_url}")
        html_path = fetch_html(test_url, "test_extraction.html")

        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # 両方の方法で抽出・比較
        print("\n🔍 抽出方法を比較中...")
        comparison = compare_extraction_methods(html_content, test_url)

        # 結果を表示
        print(f"\n{'='*60}")
        print(f"📊 抽出結果比較")
        print(f"{'='*60}")

        print(f"🤖 OpenAI API: {comparison['openai_count']}件")
        print(f"🔍 BeautifulSoup改良版: {comparison['beautifulsoup_count']}件")
        print(f"🤝 共通: {len(comparison['common_urls'])}件")
        print(f"🆕 OpenAI独自: {len(comparison['openai_only'])}件")
        print(f"🆕 BeautifulSoup独自: {len(comparison['beautifulsoup_only'])}件")

        # 詳細結果を表示
        print(f"\n--- OpenAI結果の詳細 ---")
        for i, url_info in enumerate(comparison['openai_result']['subsidy_related_urls'][:5], 1):
            print(f"{i}. {url_info['link_text'][:30]} (スコア: {url_info['relevance_score']:.2f})")
            print(f"   URL: {url_info['url'][:80]}...")
            print(f"   理由: {url_info['reasoning']}")

        if len(comparison['openai_result']['subsidy_related_urls']) > 5:
            print(f"   ... 他{len(comparison['openai_result']['subsidy_related_urls']) - 5}件")

        print(f"\n--- BeautifulSoup改良版の詳細 ---")
        for i, url_info in enumerate(comparison['beautifulsoup_result']['subsidy_related_urls'][:5], 1):
            print(f"{i}. {url_info['link_text'][:30]} (スコア: {url_info['relevance_score']:.2f})")
            print(f"   URL: {url_info['url'][:80]}...")
            print(f"   理由: {url_info['reasoning']}")

        if len(comparison['beautifulsoup_result']['subsidy_related_urls']) > 5:
            print(f"   ... 他{len(comparison['beautifulsoup_result']['subsidy_related_urls']) - 5}件")

        # 結果をファイルに保存
        with open('extraction_comparison_test.json', 'w', encoding='utf-8') as f:
            json.dump(comparison, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 詳細な比較結果を保存: extraction_comparison_test.json")

    except Exception as e:
        print(f"❌ テストエラー: {str(e)}")

def main():
    """
    メイン処理
    """
    print("高精度URL抽出機能テスト")
    print("このツールは抽出精度の違いを確認するためのものです。")
    print("実際の一覧ページURLを入力して、抽出結果を比較できます。")
    print()

    test_extraction_methods()

if __name__ == '__main__':
    main()
