import pandas as pd
import os
from dotenv import load_dotenv
from langchain_tavily import TavilySearch
import time

# .envからAPIキーを読み込む
load_dotenv()

CITY_CSV_PATH = 'data/address/city.csv'
TAVILY_API_KEY = os.getenv('TAVILY_API_KEY')

# 用途ワードと支援ワード
PURPOSE_WORDS = ["住宅", "土地"]
SUPPORT_WORDS = ["補助金"]


def get_cities_by_prefecture(prefecture_name: str, city_csv_path: str = CITY_CSV_PATH):
    """
    指定した都道府県名に属する市区町村名リストを返す
    """
    df = pd.read_csv(city_csv_path)
    # 都道府県名のカラム名はcsvの内容に合わせて修正してください
    # 例: '都道府県名', '市区町村名'
    if '都道府県名' not in df.columns or '市区町村名' not in df.columns:
        raise ValueError('city.csvのカラム名が想定と異なります')
    cities = df[df['都道府県名'] == prefecture_name]['市区町村名'].unique().tolist()
    return cities


def search_subsidy_urls(city: str, prefecture: str, max_results=3):
    """
    市区町村名・都道府県名・用途ワード・支援ワードの組み合わせでTavily検索し、URLリストを返す
    """
    tavily = TavilySearch(api_key=TAVILY_API_KEY)
    urls = set()
    for purpose in PURPOSE_WORDS:
        for support in SUPPORT_WORDS:
            query = f"{prefecture} {city} {purpose} {support}"
            try:
                results = tavily.invoke({"query": query, "max_results": max_results})
                for r in results.get('results', []):
                    urls.add(r.get('url'))
                time.sleep(1.0)  # API負荷軽減のため
            except Exception as e:
                print(f"検索失敗: {query} ({e})")
    return list(urls)


def main():
    prefecture = input('都道府県名を入力してください: ')
    cities = get_cities_by_prefecture(prefecture)
    print(f"{prefecture}の市区町村数: {len(cities)}")
    result_list = []
    for city in cities:
        urls = search_subsidy_urls(city, prefecture)
        result_list.append({"都道府県名": prefecture, "市区町村名": city, "補助金関連URL": urls})
        print(f"{city}: {len(urls)}件のURLを取得")
        break
    # 結果をCSV/JSONで保存
    df_result = pd.DataFrame(result_list)
    df_result.to_json(f"{prefecture}_subsidy_urls.json", force_ascii=False, orient="records", indent=2)
    df_result.to_csv(f"{prefecture}_subsidy_urls.csv", index=False)
    print(f"保存完了: {prefecture}_subsidy_urls.json, {prefecture}_subsidy_urls.csv")

if __name__ == '__main__':
    main()
