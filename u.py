import os
from openai import OpenAI
from dotenv import load_dotenv

# .env 読み込み
load_dotenv()

# 確認（デバッグ用）
print("DEBUG:", os.getenv("TNSYSTEM1"))

# クライアント生成
client = OpenAI(api_key=os.getenv("TNSYSTEM1"))

# テスト実行
try:
    result = client.images.generate(
        model="gpt-image-1",
        prompt="A cute cat sitting on a sofa",
        size="512x512"
    )
    print("✅ 生成成功:", result.data[0].url)
except Exception as e:
    print("❌ 生成失敗:", e)
