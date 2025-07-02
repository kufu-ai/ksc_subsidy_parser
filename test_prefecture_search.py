from search_subsidy import search_subsidy_urls_detailed_prefecture
import os

def test_prefecture_search():
    """search_subsidy_urls_detailed_prefecture関数のテスト"""

    print("🔍 テスト開始: search_subsidy_urls_detailed_prefecture")

    # テスト対象の都道府県
    prefecture = "千葉県"

    print(f"テスト対象: {prefecture}")
    print("⚠️  テストモード: 最初の2つの市区町村のみ処理")

    # limit_citiesを使ってテスト（APIコストを抑えるため）
    result = search_subsidy_urls_detailed_prefecture(
        prefecture=prefecture,
        max_results=20,  # 各クエリの結果数を制限
        save_files=True,
        limit_cities=None  # 最初の2つの市区町村のみ
    )

    print("\n📊 結果サマリー:")
    print(f"処理市区町村数: {len(result)}")

    total_urls = 0
    cities_with_results = 0

    for city, data in result.items():
        city_url_count = sum(q["URL数"] for q in data if q["status"] == "success")
        total_urls += city_url_count
        if city_url_count > 0:
            cities_with_results += 1

        print(f"  🏘️ {city}: {city_url_count}件のURL")

        # 各クエリの詳細も表示
        for i, query_data in enumerate(data):
            status_icon = "✅" if query_data["status"] == "success" else "❌"
            print(f"    {status_icon} クエリ{i+1}: {query_data['URL数']}件")

    print(f"\n📈 統計:")
    print(f"  総URL数: {total_urls}")
    print(f"  結果があった市区町村: {cities_with_results}/{len(result)}")

    # 生成されたファイルを確認
    expected_files = [
        f"{prefecture}_subsidy_urls_detailed.json",
        f"{prefecture}_all_urls.txt",
        f"{prefecture}_stats.json",
        f"{prefecture}_search_results_detailed.csv"
    ]

    print(f"\n📁 生成ファイル確認:")
    file_descriptions = {
        f"{prefecture}_subsidy_urls_detailed.json": "詳細検索結果（構造化データ）",
        f"{prefecture}_all_urls.txt": "全URL一覧（シンプルリスト）",
        f"{prefecture}_stats.json": "統計情報",
        f"{prefecture}_search_results_detailed.csv": "検索結果詳細CSV（都道府県、市区町村、クエリ、URL）"
    }

    for filename in expected_files:
        if os.path.exists(filename):
            file_size = os.path.getsize(filename)
            description = file_descriptions.get(filename, "")
            print(f"  ✅ {filename} ({file_size} bytes) - {description}")
        else:
            description = file_descriptions.get(filename, "")
            print(f"  ❌ {filename} (見つかりません) - {description}")

    print("\n📊 新機能:")
    print("  ・検索結果詳細CSV: 各クエリで取得したURLをシンプルに一覧表示")
    print("  ・カラム: 都道府県、市区町村、クエリ、URL")
    print("\n✅ テスト完了!")

if __name__ == '__main__':
    test_prefecture_search()