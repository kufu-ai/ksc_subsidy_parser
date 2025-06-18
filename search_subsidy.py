import pandas as pd
import os
from dotenv import load_dotenv
from langchain_tavily import TavilySearch
import time

# .envからAPIキーを読み込む
load_dotenv()

CITY_CSV_PATH = 'data/address/city.csv'
SITE_CSV_PATH = 'data/address/site.csv'
TAVILY_API_KEY = os.getenv('TAVILY_API_KEY')

# 用途ワードと支援ワード
PURPOSE_WORDS = ["住宅", "土地"]
SUPPORT_WORDS = ["補助金"]

# 市区町村ごとの公式ドメインを辞書化
def load_city_domains(site_csv_path=SITE_CSV_PATH):
    df = pd.read_csv(site_csv_path)
    # キー: (都道府県名, 市区町村名) → 公式ドメイン
    city_domain_dict = {}
    for _, row in df.iterrows():
        pref = row['pref']
        city = row['city']
        url = row['url']
        if pd.notnull(url):
            # ドメイン部分だけ抽出
            domain = url.replace('https://', '').replace('http://', '').split('/')[0]
            city_domain_dict[(pref, city)] = domain
    return city_domain_dict

CITY_DOMAIN_DICT = load_city_domains()

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


def search_subsidy_urls(city: str, prefecture: str, max_results=20):
    """
    市区町村名・都道府県名・用途ワード・支援ワードの組み合わせでTavily検索し、URLリストを返す
    公式ドメインがあればsite:で絞り込む
    """
    tavily = TavilySearch(api_key=TAVILY_API_KEY)
    urls = set()
    domain = CITY_DOMAIN_DICT.get((prefecture, city))
    for purpose in PURPOSE_WORDS:
        for support in SUPPORT_WORDS:
            if domain:
                print("公式ドメインを使用します", domain)
                query = f"{prefecture} {city} {purpose} {support} site:{domain}"
            else:
                query = f"{prefecture} {city} {purpose} {support} 公式"
            try:
                results = tavily.invoke({"query": query, "max_results": max_results})
                for r in results.get('results', []):
                    # 公式ドメインのみ抽出
                    url = r.get('url')
                    if domain:
                        if domain in url:
                            urls.add(url)
                    else:
                        urls.add(url)
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
