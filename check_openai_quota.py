import openai
import requests
from datetime import datetime, timedelta
import os
from config import API_KEY


def check_openai_quota():
    client = openai.OpenAI(api_key=API_KEY)
    
    try:
        # APIキーの最初と最後の数文字を表示（セキュリティのため）
        print(f"APIキー: {API_KEY[:5]}...{API_KEY[-4:] if len(API_KEY) > 8 else ''}")
        
        # 現在の日付を取得
        today = datetime.now()
        # 先月の同日
        start_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        # 今日
        end_date = today.strftime("%Y-%m-%d")
        print(f"期間: {start_date} から {end_date}")
        
        # モデル一覧を取得（APIが動作しているかの確認）
        try:
            print("\nモデル一覧を取得中...")
            models = client.models.list()
            print(f"  📋 利用可能なモデル数: {len(models.data)}")
            print(f"  📋 最初の数モデル: {[model.id for model in models.data[:3]]}")
            print("  ✅ APIキーは有効です")
        except Exception as e:
            print(f"\n❌ モデル一覧の取得に失敗: {str(e)}")
            print("  ⚠️ APIキーが無効か、アクセス権限がない可能性があります")
        
        # 使用状況の確認方法を案内
        print("\n📊 使用状況と残高の確認方法:")
        print("  1. OpenAIのダッシュボードにアクセス: https://platform.openai.com/usage")
        print("  2. ログインして使用状況を確認")
        print("  3. 「Billing」セクションで残高と請求情報を確認")
        
        # 使用状況の確認コマンドを提案
        print("\n💡 コマンドラインで使用状況を確認するには:")
        print("  curl -s -X GET \"https://api.openai.com/v1/dashboard/billing/usage?start_date=2023-01-01&end_date=2023-12-31\" \\")
        print("    -H \"Authorization: Bearer $OPENAI_API_KEY\" \\")
        print("    -H \"Content-Type: application/json\" | jq")
        print("  ※ 上記コマンドは`jq`がインストールされている必要があります")
        
    except Exception as e:
        print(f"\n❌ 全体的な処理に失敗しました: {str(e)}")
        print("  ℹ️ OpenAI APIの仕様変更により、正確な残高情報が取得できない場合があります。")
        print("  ℹ️ 詳細はOpenAIのダッシュボードで確認してください: https://platform.openai.com/usage")

if __name__ == "__main__":
    check_openai_quota()
