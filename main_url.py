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
    created_finalize_file = False
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

            classification_research = []
            if ignore_already_find:
                print(f"😮 検索で発見していないURLがあります。")
                # 検索で発見していないURLをpage_classifierで分類する
                print(f"一覧ページで発見したURLを分類します...")
                classification_research = page_classifier.classify_urls_from_object(
                    ignore_already_find, prefecture
                )

            print(f"✅ 全てのURLを分類しました。")

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

                # CSVファイルも作成 - page_classifier.pyのカラム順序に合わせる
                csv_data = []
                for result in merged_data:
                    # 補助金制度のタイトルとURLを文字列として結合
                    subsidies = result.get("found_new_housing_subsidies", [])
                    if subsidies:
                        titles = [
                            s.get("title", "") for s in subsidies if s.get("title")
                        ]
                        subsidy_urls = [
                            s.get("url", "") for s in subsidies if s.get("url")
                        ]
                        found_subsidies = " | ".join(titles)
                        subsidy_urls_str = " | ".join(subsidy_urls)
                    else:
                        found_subsidies = ""
                        subsidy_urls_str = ""

                    row = {
                        "URL": result.get("url", ""),
                        "都道府県": result.get("prefecture", ""),
                        "市区町村": result.get("city", ""),
                        "ページタイプ": result.get("page_type", ""),
                        "対象ページ": result.get("is_target_page", ""),
                        "確信度": result.get("confidence", 0.0),
                        "判定理由": result.get("reasoning", ""),
                        "ページタイトル": result.get("page_title", ""),
                        "コンテンツ要約": result.get("main_content_summary", ""),
                        "エラー": result.get("error", ""),
                        "見つかった補助金制度": found_subsidies,
                        "補助金制度URL": subsidy_urls_str,
                    }
                    csv_data.append(row)

                df_merged = pd.DataFrame(csv_data)
                csv_file = f"{prefecture}_all_classification.csv"
                df_merged.to_csv(csv_file, index=False, encoding="utf-8")
                print(f"✅ 統合CSV: {csv_file}")

                created_finalize_file = True
    # 作成されていなかったら、既存のファイルをコピーして作成する
    if not created_finalize_file:
        with open(f"{prefecture}_page_classification.json", "r") as f:
            data = json.load(f)
            # jsonを作る
            with open(f"{prefecture}_all_classification.json", "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"✅ 統合JSON: {prefecture}_all_classification.json")

            # csvを作る - page_classifier.pyのカラム順序に合わせる
            csv_data = []
            for result in data:
                # 補助金制度のタイトルとURLを文字列として結合
                subsidies = result.get("found_new_housing_subsidies", [])
                if subsidies:
                    titles = [s.get("title", "") for s in subsidies if s.get("title")]
                    subsidy_urls = [s.get("url", "") for s in subsidies if s.get("url")]
                    found_subsidies = " | ".join(titles)
                    subsidy_urls_str = " | ".join(subsidy_urls)
                else:
                    found_subsidies = ""
                    subsidy_urls_str = ""

                row = {
                    "URL": result.get("url", ""),
                    "都道府県": result.get("prefecture", ""),
                    "市区町村": result.get("city", ""),
                    "ページタイプ": result.get("page_type", ""),
                    "対象ページ": result.get("is_target_page", ""),
                    "確信度": result.get("confidence", 0.0),
                    "判定理由": result.get("reasoning", ""),
                    "ページタイトル": result.get("page_title", ""),
                    "コンテンツ要約": result.get("main_content_summary", ""),
                    "エラー": result.get("error", ""),
                    "見つかった補助金制度": found_subsidies,
                    "補助金制度URL": subsidy_urls_str,
                }
                csv_data.append(row)

            pd_data = pd.DataFrame(csv_data)
            csv_file = f"{prefecture}_all_classification.csv"
            pd_data.to_csv(csv_file, index=False, encoding="utf-8")
            print(f"✅ 統合CSV: {csv_file}")


if __name__ == "__main__":
    main()
