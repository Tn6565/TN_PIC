import os
import requests
import streamlit as st
import pandas as pd
import json
from loguru import logger
import os
from dotenv import load_dotenv
import replicate
import tempfile
import urllib.request

# 環境変数ロード
load_dotenv()
PIXABAY_API_KEY = os.getenv("TNPIXABAY")
REPLICATE_API_TOKEN = os.getenv("EXTNREPLICATE")

# ---------------- 市場分析 ----------------
def analyze_market(keyword: str):
    """
    Pixabay の写真（photo）限定で市場分析を行う
    """
    logger.info(f"市場を分析中: {keyword}")

    url = f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&q={keyword}&image_type=photo&per_page=5"
    response = requests.get(url)

    if response.status_code != 200:
        logger.error(f"Pixabay API エラー: {response.status_code}")
        return {"error": "Pixabay API にアクセスできませんでした。"}

    data = response.json()

    if "hits" not in data or len(data["hits"]) == 0:
        return {"検索キーワード": keyword, "市場傾向": "データ不足", "ヒット件数": 0, "サンプル画像": []}

    # サンプル画像を整形
    samples = []
    for i, hit in enumerate(data["hits"][:5]):
        samples.append({
            "番号": i + 1,
            "ID": hit["id"],
            "タグ": ", ".join(hit["tags"].split(",")[:5]),
            "プレビュー": hit["previewURL"]
        })

    total_results = data.get("totalHits", 0)
    if total_results > 1000:
        trend = "人気が高い"
    elif total_results > 200:
        trend = "安定"
    else:
        trend = "ニッチ"

    return {
        "検索キーワード": keyword,
        "市場傾向": trend,
        "ヒット件数": total_results,
        "サンプル画像": samples
    }

# ---------------- 画像生成 ----------------
def generate_image(prompt: str, num_outputs: int = 1, width: int = 512, height: int = 512):
    """stability-ai/stable-diffusion:ac732df83cea7fff18b8472768c88ad041fa750ff7682a21affe81863cbe77e4"""
    try:
        model_id = "stability-ai/stable-diffusion:ac732df83cea7fff18b8472768c88ad041fa750ff7682a21affe81863cbe77e4"
        output = replicate.run(
            model_id,
            input={
                "prompt": prompt,
                "num_outputs": num_outputs,
                "image_dimensions": f"{width}x{height}"
            }
        )
        return output
    except Exception as e:
        logger.error(f"画像生成失敗: {e}")
        return None

# ---------------- 画像保存用 ----------------
def download_image(url, filename):
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    urllib.request.urlretrieve(url, tmp_file.name)
    return tmp_file.name

# ---------------- Streamlit UI ----------------
st.title("📊 市場分析 + 🎨 画像生成")

keyword = st.text_input("検索キーワードを入力してください（例: 猫、犬、風景、花など）", "猫")

if st.button("市場分析開始"):
    result = analyze_market(keyword)

    if "error" in result:
        st.error(result["error"])
    else:
        # 結果表示
        st.subheader(f"🔍 キーワード: {result['検索キーワード']}")
        st.write(f"📈 市場傾向: **{result['市場傾向']}**")
        st.write(f"📊 ヒット件数: {result['ヒット件数']} 件")

        st.subheader("🖼 サンプル画像（5件）")
        cols = st.columns(5)
        for i, sample in enumerate(result["サンプル画像"]):
            with cols[i % 5]:
                st.image(sample["プレビュー"], caption=f"タグ: {sample['タグ']}", use_column_width=True)

        # ---------------- 保存機能 ----------------
        st.subheader("💾 データ保存")

        # JSON保存
        json_data = json.dumps(result, ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 JSON で保存",
            data=json_data,
            file_name=f"market_analysis_{keyword}.json",
            mime="application/json"
        )

        # CSV保存
        df = pd.DataFrame(result["サンプル画像"])
        df.insert(0, "検索キーワード", result["検索キーワード"])
        df.insert(1, "市場傾向", result["市場傾向"])
        df.insert(2, "ヒット件数", result["ヒット件数"])
        csv_data = df.to_csv(index=False)
        st.download_button(
            label="📥 CSV で保存",
            data=csv_data,
            file_name=f"market_analysis_{keyword}.csv",
            mime="text/csv"
        )

        # ---------------- 画像生成連携 ----------------
        st.subheader("🎨 市場分析から画像を生成")

        if st.button("このキーワードで画像生成"):
            with st.spinner("画像生成中..."):
                output_urls = generate_image(keyword, num_outputs=2, width=512, height=512)
                if output_urls:
                    st.success("✅ 画像生成成功")
                    for i, url in enumerate(output_urls):
                        st.image(url, use_column_width=True)
                        # ダウンロードボタンを付与
                        file_path = download_image(url, f"{keyword}_{i+1}.png")
                        with open(file_path, "rb") as f:
                            st.download_button(
                                label=f"📥 画像{i+1} を保存",
                                data=f,
                                file_name=f"{keyword}_{i+1}.png",
                                mime="image/png"
                            )
                else:
                    st.error("画像生成に失敗しました。")

