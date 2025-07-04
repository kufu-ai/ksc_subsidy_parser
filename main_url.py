import search_subsidy
import page_classifier
import json
import os
import merge_classification_results
import pandas as pd


def main():
    prefecture = search_subsidy.main()
    page_classifier.main(prefecture)

    # page_classification.jsonの中でpage_typeが補助金情報一覧ページのfound_new_housing_subsidiesを取得する
    with open(f"{prefecture}_page_classification.json", "r") as f:
        research_urls = {}
        data = json.load(f)
        for item in data:
            if item["page_type"] == "補助金情報一覧ページ":
                urls_list = []
                for subsidy in item["found_new_housing_subsidies"]:
                    urls_list.append(subsidy["url"])

                if urls_list:
                    research_urls[item["city"]] = [
                        {
                            "クエリ": "一覧ページから取得",
                            "URL": urls_list,
                            "URL数": len(urls_list),
                            "status": "success",
                        }
                    ]
        if research_urls:
            # {prefecture}2_search_subsidy_urls_detailed.jsonにresearch_urlsを追加する
            with open(f"{prefecture}2_subsidy_urls_detailed.json", "w") as f:
                json.dump(research_urls, f, indent=2, ensure_ascii=False)

            ignore_already_find = research_urls.copy()
            # 一覧ページから取得したURLを再度page_classifierで分類する
            # 検索で発見済みのURLをチェック(*_all_urls.txt)して、同じURLがある場合はignore_already_findから除外する
            with open(f"{prefecture}_all_urls.txt", "r") as f:
                all_urls = [url.strip() for url in f.readlines()]

            # ignore_already_findの各市区町村のURL配列から、all_urlsに含まれるURLを削除する
            for city in ignore_already_find:
                for query_data in ignore_already_find[city]:
                    # URL配列から既存URLを削除
                    original_urls = query_data["URL"]
                    filtered_urls = [
                        url for url in original_urls if url not in all_urls
                    ]
                    query_data["URL"] = filtered_urls
                    query_data["URL数"] = len(filtered_urls)

            # 空のURL配列を持つ市区町村は削除
            ignore_already_find = {
                city: data
                for city, data in ignore_already_find.items()
                if any(query_data["URL"] for query_data in data)
            }

            # 検索で発見していないURLをpage_classifierで分類する
            print(f"一覧ページで発見したURLを分類します...")
            classification_research = page_classifier.classify_urls_from_object(
                ignore_already_find, prefecture
            )
            print(f"全てのURLを分類しました。")

            # 結果をマージする
            if classification_research:
                print(f"分類結果をマージします...")
                merged_data = merge_classification_results.merge_classification_results(
                    data,
                    classification_research,
                )

                # JSONファイルに保存
                with open(f"{prefecture}_all_classification.json", "w") as f:
                    json.dump(merged_data, f, indent=2, ensure_ascii=False)
                print(f"✅ 統合JSON: {prefecture}_all_classification.json")

                # CSVファイルも作成
                df_merged = pd.DataFrame(merged_data)
                csv_file = f"{prefecture}_all_classification.csv"
                df_merged.to_csv(csv_file, index=False, encoding="utf-8")
                print(f"✅ 統合CSV: {csv_file}")


if __name__ == "__main__":
    main()
