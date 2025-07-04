import search_subsidy
import page_classifier
import json
import os
import merge_classification_results


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

            # 結果をマージする
            merge_classification_results.main(f"{prefecture}2")

    # 一覧ページから取得したURLを再度page_classifierで分類する
    page_classifier.main(f"{prefecture}2")


if __name__ == "__main__":
    main()
