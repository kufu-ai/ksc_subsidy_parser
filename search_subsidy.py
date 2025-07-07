import pandas as pd
import os
import json
from dotenv import load_dotenv
from langchain_tavily import TavilySearch
import time
from utils import get_output_path

# .envからAPIキーを読み込む
load_dotenv()

CITY_CSV_PATH = "data/address/city.csv"
SITE_CSV_PATH = "data/address/site.csv"
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# 用途ワードと支援ワード
PURPOSE_WORDS = ["住宅"]
SUPPORT_WORDS = ["補助金"]

# prefecture_idから都道府県名への対応辞書
PREFECTURE_MAP = {
    1: "北海道",
    2: "青森県",
    3: "岩手県",
    4: "宮城県",
    5: "秋田県",
    6: "山形県",
    7: "福島県",
    8: "茨城県",
    9: "栃木県",
    10: "群馬県",
    11: "埼玉県",
    12: "千葉県",
    13: "東京都",
    14: "神奈川県",
    15: "新潟県",
    16: "富山県",
    17: "石川県",
    18: "福井県",
    19: "山梨県",
    20: "長野県",
    21: "岐阜県",
    22: "静岡県",
    23: "愛知県",
    24: "三重県",
    25: "滋賀県",
    26: "京都府",
    27: "大阪府",
    28: "兵庫県",
    29: "奈良県",
    30: "和歌山県",
    31: "鳥取県",
    32: "島根県",
    33: "岡山県",
    34: "広島県",
    35: "山口県",
    36: "徳島県",
    37: "香川県",
    38: "愛媛県",
    39: "高知県",
    40: "福岡県",
    41: "佐賀県",
    42: "長崎県",
    43: "熊本県",
    44: "大分県",
    45: "宮崎県",
    46: "鹿児島県",
    47: "沖縄県",
}


def get_cities_by_prefecture(prefecture_name: str, city_csv_path: str = CITY_CSV_PATH):
    """
    指定した都道府県名に属する市区町村名リストを返す（正式名称のみ）
    """
    df = pd.read_csv(city_csv_path)

    # prefecture_idを都道府県名から逆引き
    prefecture_id = None
    for pid, pname in PREFECTURE_MAP.items():
        if pname == prefecture_name:
            prefecture_id = pid
            break

    if prefecture_id is None:
        raise ValueError(f'都道府県名 "{prefecture_name}" が見つかりません')

    # 指定した都道府県の市区町村名を取得（重複除去）
    cities = df[df["prefecture_id"] == prefecture_id]["city_name"].unique().tolist()
    return cities


def get_flexible_city_name(
    input_city: str, prefecture_name: str, city_csv_path: str = CITY_CSV_PATH
):
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

    # prefecture_idを都道府県名から逆引き
    prefecture_id = None
    for pid, pname in PREFECTURE_MAP.items():
        if pname == prefecture_name:
            prefecture_id = pid
            break

    if prefecture_id is None:
        return input_city

    # その都道府県の全市区町村を取得
    prefecture_cities = df[df["prefecture_id"] == prefecture_id]["city_name"].unique()

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
        prefecture_sites = df[df["pref"] == prefecture]

        # 1. 完全一致を確認
        exact_match = prefecture_sites[prefecture_sites["city"] == city]
        if not exact_match.empty and pd.notnull(exact_match.iloc[0]["url"]):
            url = exact_match.iloc[0]["url"]
            return url.replace("https://", "").replace("http://", "").split("/")[0]

        # 2. 後方一致を確認（「越智郡上島町」が「上島町」にマッチ）
        for _, row in prefecture_sites.iterrows():
            site_city = row["city"]
            if (
                pd.notnull(site_city)
                and city.endswith(site_city)
                and pd.notnull(row["url"])
            ):
                url = row["url"]
                return url.replace("https://", "").replace("http://", "").split("/")[0]

        return None

    except Exception as e:
        print(f"ドメイン取得エラー: {str(e)}")
        return None


def search_subsidy_urls_detailed(city: str, prefecture: str, max_results=20):
    """
    市区町村名・都道府県名・用途ワード・支援ワードの組み合わせでTavily検索し、
    クエリごとに詳細なデータを返す（重複削除なし）

    Args:
        city (str): 市区町村名
        prefecture (str): 都道府県名
        max_results (int): 検索結果の最大数
        save_txt (bool): URLをtxtファイルに保存するかどうか

    Returns:
        dict: 市区町村名をキーとした辞書
        "市区町村名": [
            {
                "クエリ": "検索クエリ",
                "URL": ["URL1", "URL2", ...],
                "URL数": 取得URL数,
                "status": "success" | "error",
                "error_message": "エラーメッジ（エラー時のみ）"
            },
            ...
        ]...
    """
    # 柔軟マッチングで正式名称を取得
    formal_city_name = get_flexible_city_name(city, prefecture)
    if formal_city_name != city:
        print(f"    📝 正式名称: {city} → {formal_city_name}")

    # 正式名称で公式ドメインを取得
    domain = get_official_domain(formal_city_name, prefecture)
    # 複数指定したいがうまく取得できないので比較的多いpdfのみ除外
    minus_query = "-filetype:pdf"

    # 市区町村名をキーとした辞書を初期化
    city_results = {city: []}

    for purpose in PURPOSE_WORDS:
        for support in SUPPORT_WORDS:
            if domain:
                print(f"    🌐 公式ドメインを使用: {domain}")
                query = f"{formal_city_name} {purpose} {support} {minus_query}"
            else:
                print(f"    🔍 公式ドメイン未発見、一般検索を実行")
                query = f"{prefecture}{formal_city_name} {purpose} {support} 公式 {minus_query}"

            query_result = {"クエリ": query, "URL": [], "URL数": 0, "status": "success"}

            try:
                tavily = TavilySearch(
                    api_key=TAVILY_API_KEY,
                    max_results=max_results,
                    include_domains=[domain],
                )

                print(f"    🔍 query: {query}")
                results = tavily.invoke({"query": query})
                urls = []
                for r in results.get("results", []):
                    url = r.get("url")
                    if url:
                        urls.append(url)

                query_result["URL"] = urls
                query_result["URL数"] = len(urls)
                time.sleep(1.0)  # API負荷軽減のため

            except Exception as e:
                print(f"    ❌ 検索失敗: {query} ({e})")
                query_result["status"] = "error"
                query_result["error_message"] = str(e)

            city_results[city].append(query_result)

    return city_results


def search_subsidy_urls_detailed_prefecture(
    prefecture: str, max_results=20, save_files=True, limit_cities=None
):
    """
    都道府県全体の市区町村で補助金URLを検索し、まとめてファイルに保存

    Args:
        prefecture (str): 都道府県名
        max_results (int): 各検索クエリの最大結果数
        save_files (bool): ファイル保存するかどうか
        limit_cities (int): 処理する市区町村数の上限（テスト用、Noneで全て）

    Returns:
        dict: 全市区町村の検索結果を含む辞書
        {
            "市区町村名1": [
                {
                    "クエリ": "検索クエリ",
                    "URL": ["URL1", "URL2", ...],
                    "URL数": 取得URL数,
                    "status": "success" | "error",
                    "error_message": "エラーメッセージ（エラー時のみ）"
                },
                ...
            ],
            "市区町村名2": [...],
            ...
        }
    """
    print(f"🌐 {prefecture}の補助金URL検索を開始")

    # 都道府県内の全市区町村を取得
    cities = get_cities_by_prefecture(prefecture)
    print(f"📍 対象市区町村数: {len(cities)}件")

    # 処理する市区町村数を制限（テスト用）
    if limit_cities:
        cities = cities[:limit_cities]
        print(f"⚠️  テストモード: {limit_cities}件のみ処理")

    all_results = {}
    all_urls = []

    for i, city in enumerate(cities, 1):
        print(f"\n📍 ({i}/{len(cities)}) {city} を処理中...")

        try:
            # 各市区町村の詳細検索を実行
            city_result = search_subsidy_urls_detailed(city, prefecture, max_results)
            all_results.update(city_result)

            # 成功したURLを収集
            for query_data in city_result[city]:
                if query_data["status"] == "success":
                    all_urls.extend(query_data["URL"])

            print(f"✅ {city}: 完了")
            # break  # TODO 不要になったら消す

        except Exception as e:
            print(f"❌ {city}: エラー - {e}")
            # エラーが発生した市区町村も記録
            all_results[city] = [
                {
                    "クエリ": "",
                    "URL": [],
                    "URL数": 0,
                    "status": "error",
                    "error_message": f"市区町村処理エラー: {str(e)}",
                }
            ]

    print(f"\n📊 検索完了:")
    print(f"  処理市区町村数: {len(all_results)}")
    print(f"  総URL数: {len(all_urls)}")

    # ファイル保存
    if save_files:
        # 安全なファイル名を生成
        safe_prefecture = prefecture.replace("/", "_").replace("\\", "_")

        # 1. 詳細JSONファイル保存
        json_filename = get_output_path(f"{safe_prefecture}_subsidy_urls_detailed.json")
        try:
            with open(json_filename, "w", encoding="utf-8") as f:
                json.dump(all_results, f, ensure_ascii=False, indent=2)
            print(f"💾 詳細データ保存: {json_filename}")
        except Exception as e:
            print(f"❌ JSON保存失敗: {e}")

        # 2. URLリストtxtファイル保存
        txt_filename = get_output_path(f"{safe_prefecture}_all_urls.txt")
        try:
            with open(txt_filename, "w", encoding="utf-8") as f:
                for url in all_urls:
                    f.write(f"{url}\n")
            print(f"💾 URLリスト保存: {txt_filename} ({len(all_urls)}件)")
        except Exception as e:
            print(f"❌ txt保存失敗: {e}")

        # 4. 検索結果詳細CSV保存
        csv_detailed_filename = get_output_path(
            f"{safe_prefecture}_search_results_detailed.csv"
        )
        try:
            csv_data = []

            for city, data in all_results.items():
                for query_info in data:
                    # 各URLを個別の行として記録（URLがある場合のみ）
                    if query_info["URL数"] > 0:
                        for url in query_info["URL"]:
                            csv_data.append(
                                {
                                    "都道府県": prefecture,
                                    "市区町村": city,
                                    "クエリ": query_info["クエリ"],
                                    "URL": url,
                                }
                            )

            df_detailed = pd.DataFrame(csv_data)
            df_detailed.to_csv(csv_detailed_filename, index=False, encoding="utf-8-sig")
            print(
                f"📊 検索結果詳細CSV保存: {csv_detailed_filename} ({len(csv_data)}行)"
            )
        except Exception as e:
            print(f"❌ 詳細CSV保存失敗: {e}")

    return all_results


def main():
    prefecture = input("都道府県名を入力してください: ")
    cities = get_cities_by_prefecture(prefecture)
    print(f"{prefecture}の市区町村数: {len(cities)}")
    search_subsidy_urls_detailed_prefecture(prefecture)
    return prefecture


if __name__ == "__main__":
    main()
