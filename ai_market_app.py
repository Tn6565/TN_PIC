import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from pytrends.request import TrendReq

# ==========================
# ページ設定（タイトルとアイコン）
# ==========================
st.set_page_config(
    page_title="画像市場調査アプリ",
    page_icon="icon.ico",  # Windowsアイコンをここに設定
    layout="centered"
)

# ==========================
# 複数サイズファビコンを HTML で設定
# ==========================
st.markdown("""
<link rel="icon" type="image/png" sizes="32x32" href="static/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="128x128" href="static/favicon-128x128.png">
""", unsafe_allow_html=True)

# ==========================
# APIキーの読み込み
# ==========================
PIXABAY_API_KEY = os.getenv("TNPIXABAY")
UNSPLASH_ACCESS_KEY = os.getenv("TNUNSPLASH")

# ==========================
# Pixabay からデータ取得
# ==========================
def fetch_pixabay_data(query, per_page=50):
    url = f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&q={query}&per_page={per_page}"
    res = requests.get(url)
    if res.status_code == 200:
        hits = res.json().get("hits", [])
        return [
            {
                "source": "Pixabay",
                "likes": h.get("likes", 0),
                "downloads": h.get("downloads", 0),
                "tags": h.get("tags", ""),
            }
            for h in hits
        ]
    return []

# ==========================
# Unsplash からデータ取得
# ==========================
def fetch_unsplash_data(query, per_page=30):
    url = f"https://api.unsplash.com/search/photos?query={query}&per_page={per_page}&client_id={UNSPLASH_ACCESS_KEY}"
    res = requests.get(url)
    if res.status_code == 200:
        results = res.json().get("results", [])
        return [
            {
                "source": "Unsplash",
                "likes": r.get("likes", 0),
                "downloads": r.get("downloads", 0),  # Unsplash APIはDL数未提供
                "tags": ", ".join([t["title"] for t in r.get("tags", [])]),
            }
            for r in results
        ]
    return []

# ==========================
# Google Trends データ取得
# ==========================
def fetch_trends_data(query):
    pytrends = TrendReq(hl="en-US", tz=360)
    pytrends.build_payload([query], cat=0, timeframe="today 12-m", geo="", gprop="")
    interest = pytrends.interest_over_time()
    if not interest.empty:
        return int(interest[query].mean())
    return 0

# ==========================
# データ分析とスコア算出
# ==========================
def analyze_data(query):
    data = []
    data.extend(fetch_pixabay_data(query))
    data.extend(fetch_unsplash_data(query))
    trends_score = fetch_trends_data(query)

    df = pd.DataFrame(data)
    if df.empty:
        return None

    # 各評価指標（最大値で正規化）
    df["likes_norm"] = df["likes"] / (df["likes"].max() + 1)
    df["downloads_norm"] = df["downloads"] / (df["downloads"].max() + 1)

    # スコア設計（例: DL40%, いいね30%, Trends30%）
    df["score"] = (
        df["downloads_norm"] * 0.4
        + df["likes_norm"] * 0.3
        + (trends_score / 100) * 0.3
    )

    return df, trends_score

# ==========================
# レーダーチャート描画
# ==========================
def plot_radar_chart(scores, query):
    categories = list(scores.keys())
    values = list(scores.values())
    values += values[:1]
    angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.plot(angles, values, "o-", linewidth=2)
    ax.fill(angles, values, alpha=0.25)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories)
    ax.set_title(f"Analysis Radar Chart: {query}")
    return fig

# ==========================
# Streamlit アプリ本体
# ==========================
def main():
    st.title("📊 画像市場調査アプリ")
    query = st.text_input("検索キーワードを入力してください（例: cat, business, nature）")

    if st.button("分析開始"):
        if not query:
            st.warning("⚠️ キーワードを入力してください。")
            return

        with st.spinner("データ収集中..."):
            result = analyze_data(query)

        if result is None:
            st.error("❌ データを取得できませんでした。")
        else:
            df, trends_score = result
            st.success("✅ データ取得完了！")

            st.dataframe(df[["source", "likes", "downloads", "tags", "score"]])

            avg_likes = df["likes"].mean()
            avg_downloads = df["downloads"].mean()
            avg_score = df["score"].mean()

            scores = {
                "Likes": avg_likes / (df["likes"].max() + 1),
                "Downloads": avg_downloads / (df["downloads"].max() + 1),
                "GoogleTrends": trends_score / 100,
            }

            fig = plot_radar_chart(scores, query)
            st.pyplot(fig)

if __name__ == "__main__":
    main()
