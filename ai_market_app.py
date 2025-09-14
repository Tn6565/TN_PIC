import streamlit as st
import json
from loguru import logger
import os
from dotenv import load_dotenv
import replicate
from datetime import date
import requests
from PIL import Image
import imagehash
from io import BytesIO
import matplotlib.pyplot as plt

# =======================
# 環境変数
# =======================
load_dotenv()  # ローカルでは .env を読み込む
REPLICATE_API_TOKEN = os.getenv("EXTNREPLICATE")
PIXABAY_API_KEY = os.getenv("TNPIXABAY")

if not REPLICATE_API_TOKEN or not PIXABAY_API_KEY:
    st.error("EXTNREPLICATE または TNPIXABAY が設定されていません")
    st.stop()

st.write("✅ APIトークン読み込み成功")

# =======================
# 1日10枚まで制限
# =======================
DAILY_DATA_FILE = "daily_usage.json"

def load_daily_data():
    if os.path.exists(DAILY_DATA_FILE):
        with open(DAILY_DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_daily_data(data):
    with open(DAILY_DATA_FILE, "w") as f:
        json.dump(data, f)

# =======================
# 市場分析（Pixabay）
# =======================
def analyze_market(keyword: str):
    logger.info("市場を分析中: {}", keyword)
    url = f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&q={keyword}&image_type=photo&per_page=5"
    try:
        res = requests.get(url)
        data = res.json()
        total_hits = data.get("totalHits", 0)
        hits_sample = [{"id": img["id"], "tags": img["tags"], "previewURL": img["previewURL"]} for img in data.get("hits", [])]
        trend = "上昇中" if total_hits > 500 else "安定" if total_hits > 100 else "低下中"
        return {
            "keyword": keyword,
            "trend": trend,
            "total_results": total_hits,
            "sample_images": hits_sample
        }
    except Exception as e:
        logger.error(f"Pixabay APIエラー: {e}")
        return {"keyword": keyword, "trend": "不明", "total_results": 0, "sample_images": []}

# =======================
# 画像生成（Stable Diffusion 2.1）
# =======================
MODEL_VERSION = "stability-ai/stable-diffusion:ac732df83cea7fff18b8472768c88ad041fa750ff7682a21affe81863cbe77e4"
client = replicate.Client(api_token=REPLICATE_API_TOKEN)

def generate_image(prompt: str, width: int = 512, height: int = 512, steps: int = 20, num_outputs: int = 1):
    try:
        outputs = client.run(
            MODEL_VERSION,
            input={
                "prompt": prompt,
                "width": width,
                "height": height,
                "num_inference_steps": steps,
                "num_outputs": num_outputs,
            },
        )
        urls = [f.url if hasattr(f, "url") else f for f in outputs]
        return urls
    except replicate.exceptions.ReplicateError as e:
        st.error(f"画像生成失敗: {e}")
        return []

# =======================
# 購買分析
# =======================
def analyze_buyers(data: str):
    logger.info("購買データを解析中")
    buyers = json.loads(data)
    reasons = {}
    for entry in buyers:
        reason = entry.get("reason", "不明")
        reasons[reason] = reasons.get(reason, 0) + 1
    return {
        "total_buyers": len(buyers),
        "reason_summary": reasons,
        "example": buyers[:2]
    }

# =======================
# 盗作チェック
# =======================
def check_image_similarity(generated_url, reference_urls, threshold=5):
    gen_img = Image.open(BytesIO(requests.get(generated_url).content))
    gen_hash = imagehash.phash(gen_img)
    warnings = []
    for ref_url in reference_urls:
        ref_img = Image.open(BytesIO(requests.get(ref_url).content))
        ref_hash = imagehash.phash(ref_img)
        distance = gen_hash - ref_hash
        if distance <= threshold:
            warnings.append({"ref_url": ref_url, "distance": distance})
    return warnings

# =======================
# Streamlit UI
# =======================
st.set_page_config(layout="wide")
tabs = st.tabs(["市場分析", "画像生成", "購買分析"])

# ===== 市場分析 =====
with tabs[0]:
    st.header("市場分析（Pixabayベース）")
    keyword = st.text_input("分析キーワード", "猫")
    if st.button("市場を分析"):
        with st.spinner("市場データを収集中..."):
            market_result = analyze_market(keyword)
            st.json(market_result)
            if market_result.get("sample_images"):
                st.subheader("サンプル画像")
                for img in market_result["sample_images"]:
                    st.image(img["previewURL"], width=150, caption=img["tags"])
            plt.bar([keyword], [market_result["total_results"]])
            st.pyplot(plt.gcf())
            plt.clf()

# ===== 画像生成 =====
with tabs[1]:
    st.header("画像生成（1日10枚まで）")
    width = st.number_input("幅(px)", 128, 1024, 512, 64)
    height = st.number_input("高さ(px)", 128, 1024, 512, 64)
    steps = st.slider("ステップ数", 10, 50, 20)
    num_outputs = st.slider("生成枚数", 1, 4, 1)
    prompt = st.text_area("画像生成プロンプト", "かわいい猫、リアル、自然光、白背景", max_chars=150)

    COST_PER_IMAGE = 0.02
    daily_data = load_daily_data()
    today_str = str(date.today())
    if today_str not in daily_data:
        daily_data[today_str] = {"count": 0, "cost": 0.0}

    remaining = max(0, 10 - daily_data[today_str]["count"])
    st.info(f"本日残り生成可能枚数: {remaining} / 10")
    st.info(f"本日合計コスト: ${daily_data[today_str]['cost']:.2f}")

    if remaining <= 0:
        st.warning("本日の生成上限に達しました")
    else:
        if st.button("画像を生成"):
            actual_generate = min(num_outputs, remaining)
            with st.spinner("画像生成中..."):
                urls = generate_image(prompt, width=int(width), height=int(height), steps=steps, num_outputs=actual_generate)
                st.success(f"{len(urls)}枚生成完了")
                for i, url in enumerate(urls):
                    st.image(url, width=512)
                    st.markdown(f"[ダウンロード]({url})")

                    # 盗作チェック
                    if 'market_result' in locals():
                        reference_urls = [img["previewURL"] for img in market_result.get("sample_images", [])]
                        warnings = check_image_similarity(url, reference_urls)
                        if warnings:
                            st.warning(f"画像_{i+1} は既存画像と類似の可能性があります")
                            for w in warnings:
                                st.image(w["ref_url"], width=150, caption=f"類似度 {w['distance']}")

                daily_data[today_str]["count"] += len(urls)
                daily_data[today_str]["cost"] += len(urls) * COST_PER_IMAGE
                save_daily_data(daily_data)

                remaining = max(0, 10 - daily_data[today_str]["count"])
                st.info(f"本日残り生成可能枚数: {remaining} / 10")
                st.info(f"本日合計コスト: ${daily_data[today_str]['cost']:.2f}")

# ===== 購買分析 =====
with tabs[2]:
    st.header("購買分析")
    sample_data = st.text_area("購買データ（JSON形式）", '[{"user":"A","item":"art1","reason":"色が良い"}]')
    if st.button("購買分析を実行"):
        try:
            analysis = analyze_buyers(sample_data)
            st.json(analysis)
            labels = list(analysis["reason_summary"].keys())
            sizes = list(analysis["reason_summary"].values())
            plt.pie(sizes, labels=labels, autopct="%1.1f%%")
            st.pyplot(plt.gcf())
            plt.clf()
        except Exception as e:
            st.error(f"分析失敗: {e}")


