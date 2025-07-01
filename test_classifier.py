#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
補助金ページ分類機能のテストスクリプト
"""

from page_classifier import classify_page_type, classify_urls_from_file, save_classification_results
import sys

def test_single_url():
    """
    単一URLでテストする
    """
    print("=== 単一URL分類テスト ===")

    # テスト用のURL（愛媛県のものから例として）
    test_url = input("テストするURLを入力してください: ").strip()

    if not test_url:
        print("URLが入力されませんでした")
        return

    print(f"分析中: {test_url}")
    result = classify_page_type(test_url)

    print("\n=== 分析結果 ===")
    print(f"ページタイプ: {result.get('page_type', '不明')}")
    print(f"確信度: {result.get('confidence', 0.0)}")
    print(f"判定理由: {result.get('reasoning', '不明')}")
    print(f"ページタイトル: {result.get('page_title', '不明')}")
    print(f"見つかった補助金制度:")
    for title in result.get('found_subsidy_titles', []):
        print(f"  - {title}")
    print(f"主要コンテンツ要約: {result.get('main_content_summary', '不明')}")

    if 'error' in result:
        print(f"エラー: {result['error']}")

def test_batch_classification():
    """
    バッチ処理でテストする
    """
    print("=== バッチ分類テスト ===")

    import os
    json_files = [f for f in os.listdir('.') if f.endswith('_subsidy_urls.json')]

    if not json_files:
        print("*_subsidy_urls.jsonファイルが見つかりません")
        return

    print("\n利用可能なファイル:")
    for i, file in enumerate(json_files, 1):
        print(f"{i}. {file}")

    try:
        choice = int(input("\n分析するファイルの番号を選択してください: ")) - 1
        if choice < 0 or choice >= len(json_files):
            print("無効な選択です")
            return

        selected_file = json_files[choice]
        print(f"\n{selected_file}を分析します...")

        # URLを分類（テスト用に制限）
        results = classify_urls_from_file(selected_file)

        if results:
            # 結果を保存
            output_file = selected_file.replace('_subsidy_urls.json', '_page_classification.csv')
            save_classification_results(results, output_file)
            print(f"\n結果が保存されました: {output_file}")
        else:
            print("分類結果が得られませんでした")

    except ValueError:
        print("無効な入力です")
    except KeyboardInterrupt:
        print("\n処理が中断されました")

def main():
    """
    メイン処理
    """
    print("補助金ページ分類テストツール")
    print("1. 単一URLテスト")
    print("2. バッチ処理テスト")

    try:
        choice = input("\n選択してください (1 or 2): ").strip()

        if choice == '1':
            test_single_url()
        elif choice == '2':
            test_batch_classification()
        else:
            print("無効な選択です")

    except KeyboardInterrupt:
        print("\n処理が中断されました")

if __name__ == '__main__':
    main()
