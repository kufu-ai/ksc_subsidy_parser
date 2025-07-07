import json
import glob
import os
from html_fetcher import fetch_html
from openai_handler import process_html_file_with_openai
from csv_handler import save_to_csv
from utils import load_urls, get_output_path


def process_existing_urls():
    """既存のURLリストを処理"""
    urls = load_urls()
    print(f"📋 既存のURLリスト（{len(urls)}件）の処理を開始...")

    for idx, url in enumerate(urls):
        print(f"\n🚀 {idx+1}/{len(urls)}: {url} の解析を開始")

        html_path = fetch_html(url, f"page_{idx+1}.html")
        json_path = process_html_file_with_openai(html_path, url)

        # **❗ JSONデータがない場合はスキップ**
        if json_path is None:
            print(f"⚠️ {url} のデータが取得できなかったため、スキップします。")
            continue

        save_to_csv(json_path)
        print(f"✅ {url} の解析が完了しました！\n")


def get_available_prefectures():
    """利用可能な都道府県リストを取得"""
    output_dir = get_output_path("")
    classification_files = glob.glob(
        os.path.join(output_dir, "*_all_classification.json")
    )

    prefectures = []
    for file_path in classification_files:
        filename = os.path.basename(file_path)
        # ファイル名から都道府県名を抽出（例：長野県_all_classification.json → 長野県）
        prefecture = filename.replace("_all_classification.json", "")
        prefectures.append(prefecture)

    return sorted(prefectures)


def select_prefecture():
    """都道府県を選択"""
    prefectures = get_available_prefectures()

    if not prefectures:
        print("⚠️ *_all_classification.jsonファイルが見つかりませんでした。")
        return None

    print(f"\n📁 {len(prefectures)}個の都道府県のファイルが見つかりました")
    print("=" * 50)

    for i, prefecture in enumerate(prefectures, 1):
        print(f"{i}. {prefecture}")

    print("=" * 50)

    while True:
        try:
            choice = input(
                f"処理したい都道府県の番号を入力してください (1-{len(prefectures)}): "
            ).strip()
            choice_num = int(choice)

            if 1 <= choice_num <= len(prefectures):
                selected_prefecture = prefectures[choice_num - 1]
                print(f"✅ {selected_prefecture} を選択しました")
                return selected_prefecture
            else:
                print(f"⚠️ 1から{len(prefectures)}の範囲で入力してください。")
        except ValueError:
            print("⚠️ 数字を入力してください。")


def process_classification_pages():
    """*_all_classification.jsonファイルから住宅関連個別ページのURLを抽出・処理"""
    # 都道府県を選択
    selected_prefecture = select_prefecture()
    if not selected_prefecture:
        return

    print(f"\n📋 {selected_prefecture}の住宅関連個別ページのURLを抽出・処理を開始...")

    # 選択された都道府県のファイルを読み込み
    output_dir = get_output_path("")
    file_path = os.path.join(
        output_dir, f"{selected_prefecture}_all_classification.json"
    )

    if not os.path.exists(file_path):
        print(
            f"⚠️ {selected_prefecture}_all_classification.jsonファイルが見つかりませんでした。"
        )
        return

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"⚠️ {file_path} の読み込みでエラーが発生しました: {e}")
        return

    # 住宅関連個別ページのURLを抽出
    target_urls = []
    for item in data:
        if (
            item.get("page_type") == "住宅関連個別ページ"
            and item.get("is_target_page") == "対象"
        ):
            target_urls.append(item.get("url"))

    if not target_urls:
        print(
            f"⚠️ {selected_prefecture}で対象となる住宅関連個別ページが見つかりませんでした。"
        )
        return

    print(
        f"🎯 {selected_prefecture}で{len(target_urls)}個の住宅関連個別ページを発見しました"
    )

    # 各URLを処理
    for idx, url in enumerate(target_urls):
        print(f"\n🏠 {idx+1}/{len(target_urls)}: {url} の解析を開始")

        html_path = fetch_html(
            url, f"{selected_prefecture}_classification_page_{idx+1}.html"
        )
        json_path = process_html_file_with_openai(html_path, url)

        # **❗ JSONデータがない場合はスキップ**
        if json_path is None:
            print(f"⚠️ {url} のデータが取得できなかったため、スキップします。")
            continue

        save_to_csv(json_path)
        print(f"✅ {url} の解析が完了しました！\n")


def main():
    """メイン処理"""
    print("🚀 補助金情報解析システム")
    print("=" * 50)
    print("1. 既存URLリスト（urls.txt）の処理")
    print("2. 分類済み住宅関連個別ページの処理")
    print("=" * 50)

    while True:
        choice = input("処理を選択してください (1 または 2): ").strip()

        if choice == "1":
            process_existing_urls()
            break
        elif choice == "2":
            process_classification_pages()
            break
        else:
            print("⚠️ 1 または 2 を入力してください。")

    print("\n🎉 処理が完了しました！")


if __name__ == "__main__":
    main()
