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

def get_cities_by_prefecture(prefecture_name: str, city_csv_path: str = CITY_CSV_PATH):
    """
    指定した都道府県名に属する市区町村名リストを返す（正式名称のみ）
    """
    df = pd.read_csv(city_csv_path)
    # 都道府県名のカラム名はcsvの内容に合わせて修正してください
    # 例: '都道府県名', '市区町村名'
    if '都道府県名' not in df.columns or '市区町村名' not in df.columns:
        raise ValueError('city.csvのカラム名が想定と異なります')

    # 正式名称のみを返す（重複除去）
    cities = df[df['都道府県名'] == prefecture_name]['市区町村名'].unique().tolist()
    return cities

def get_flexible_city_name(input_city: str, prefecture_name: str, city_csv_path: str = CITY_CSV_PATH):
    """
    入力された市区町村名に対して、柔軟にマッチする正式名称を返す

    Args:
        input_city (str): 入力された市区町村名
        prefecture_name (str): 都道府県名
        city_csv_path (str): CSVファイルパス

    Returns:
        str: マッチした正式な市区町村名、見つからなければ元の名前
    """
    df = pd.read_csv(city_csv_path)

    # その都道府県の全市区町村を取得
    prefecture_cities = df[df['都道府県名'] == prefecture_name]['市区町村名'].unique()

    # 1. 完全一致を確認
    if input_city in prefecture_cities:
        return input_city

    # 2. 後方一致を確認（「川越町」が「三重郡川越町」にマッチ）
    for city in prefecture_cities:
        if city.endswith(input_city):
            return city

    # 見つからない場合は元の名前を返す
    return input_city

def get_official_domain(city: str, prefecture: str, site_csv_path=SITE_CSV_PATH):
    """
    市区町村名から公式ドメインを取得（柔軟マッチング対応）

    Args:
        city (str): 市区町村名（正式名称、郡名付き可能性あり）
        prefecture (str): 都道府県名
        site_csv_path (str): site.csvのパス

    Returns:
        str: 公式ドメイン（見つからなければNone）
    """
    try:
        df = pd.read_csv(site_csv_path)

        # その都道府県のsite.csvデータを取得
        prefecture_sites = df[df['pref'] == prefecture]

        # 1. 完全一致を確認
        exact_match = prefecture_sites[prefecture_sites['city'] == city]
        if not exact_match.empty and pd.notnull(exact_match.iloc[0]['url']):
            url = exact_match.iloc[0]['url']
            return url.replace('https://', '').replace('http://', '').split('/')[0]

        # 2. 後方一致を確認（「越智郡上島町」が「上島町」にマッチ）
        for _, row in prefecture_sites.iterrows():
            site_city = row['city']
            if pd.notnull(site_city) and city.endswith(site_city) and pd.notnull(row['url']):
                url = row['url']
                return url.replace('https://', '').replace('http://', '').split('/')[0]

        return None

    except Exception as e:
        print(f"ドメイン取得エラー: {str(e)}")
        return None

def search_subsidy_urls(city: str, prefecture: str, max_results=20):
    """
    市区町村名・都道府県名・用途ワード・支援ワードの組み合わせでTavily検索し、URLリストを返す
    公式ドメインがあればsite:で絞り込む（get_flexible_city_nameを使用）
    """
    tavily = TavilySearch(api_key=TAVILY_API_KEY)
    urls = set()

    # 柔軟マッチングで正式名称を取得
    formal_city_name = get_flexible_city_name(city, prefecture)
    if formal_city_name != city:
        print(f"    📝 正式名称: {city} → {formal_city_name}")

    # 正式名称で公式ドメインを取得
    domain = get_official_domain(formal_city_name, prefecture)

    for purpose in PURPOSE_WORDS:
        for support in SUPPORT_WORDS:
            if domain:
                print(f"    🌐 公式ドメインを使用: {domain}")
                query = f"{prefecture} {formal_city_name} {purpose} {support} site:{domain}"
            else:
                print(f"    🔍 公式ドメイン未発見、一般検索を実行")
                query = f"{prefecture} {formal_city_name} {purpose} {support} 公式"
            try:
                results = tavily.invoke({"query": query, "max_results": max_results})
                for r in results.get('results', []):
                    url = r.get('url')
                    if url:
                        urls.add(url)
                time.sleep(1.0)  # API負荷軽減のため
            except Exception as e:
                print(f"    ❌ 検索失敗: {query} ({e})")
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
        # TODO: 最後・通しのチェックの時は消す
        # 2件取得したら終了 リミット来ないように
        # if len(result_list) >= 2:
        #     break
    # 結果をCSV/JSONで保存
    df_result = pd.DataFrame(result_list)
    df_result.to_json(f"{prefecture}_subsidy_urls.json", force_ascii=False, orient="records", indent=2)
    df_result.to_csv(f"{prefecture}_subsidy_urls.csv", index=False)
    print(f"保存完了: {prefecture}_subsidy_urls.json, {prefecture}_subsidy_urls.csv")

if __name__ == '__main__':
    main()
