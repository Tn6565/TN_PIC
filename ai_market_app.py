import os
import requests
import streamlit as st
from dotenv import load_dotenv
from pytrends.request import TrendReq
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from datetime import datetime
from requests.utils import quote

# =============================
# .env から APIキーを読み込み
# =============================
load_dotenv()
PIXABAY_API_KEY = os.getenv("TNPIXABAY")
UNSPLASH_API_KEY = os.getenv("TNUNSPLASH")

# =============================
# ジャンルマッピング辞書
# =============================
GENRE_MAP = {
    "Wellness & Fitness": ["yoga", "fitness", "meditation", "exercise", "wellness", "health"],
    "Eco & Nature": ["nature", "forest", "eco", "sustainable", "environment", "green"],
    "Travel & Tourism": ["travel", "beach", "city", "mountain", "landscape", "tourism"],
    "Tech & Business": ["computer", "ai", "office", "technology", "startup", "innovation"],
    "Diversity & People": ["family", "community", "school", "diversity", "education", "friends"],
    "Food & Drink": ["food", "coffee", "restaurant", "meal", "drink", "dessert"],
    "Fashion & Beauty": ["fashion", "makeup", "clothes", "style", "beauty", "model"],
    "Pets & Animals": ["dog", "cat", "bird", "animal", "pet", "wildlife"],
    "Art & Design": ["art", "architecture", "abstract", "design", "creative", "illustration"],
    "Lifestyle & Home": ["home", "interior", "daily", "lifestyle", "house", "furniture"],
    "Education & Learning": ["study", "book", "school", "university", "teacher", "learning"],
    "Sports & Outdoor": ["soccer", "basketball", "running", "hiking", "outdoor", "fitness"],
    "Entertainment & Media": ["music", "movie", "tv", "game", "entertainment", "media"],
    "Science & Innovation": ["lab", "research", "science", "experiment", "future", "space"],
    "Finance & Money": ["money", "investment", "stock", "finance", "bank", "crypto"],
    "Automotive & Transport": ["car", "bike", "bus", "train", "transport", "automotive"],
    "Real Estate & Architecture": ["real estate", "building", "architecture", "house", "property"],
    "Medical & Healthcare": ["doctor", "hospital", "medicine", "healthcare", "nurse", "treatment"],
    "Religion & Spirituality": ["religion", "church", "temple", "spiritual", "faith"],
    "Events & Holidays": ["christmas", "halloween", "festival", "party", "event", "holiday"]
}

def classify_genre(keyword: str) -> str:
    keyword = keyword.lower()
    for genre, keywords in GENRE_MAP.items():
        if any(k in keyword for k in keywords):
            return genre
    return "Other"

# =============================
# APIからデータ取得
# =============================
def get_pixabay_count(keyword: str) -> int:
    if not PIXABAY_API_KEY:
        st.error("Pixabay APIキーが設定されていません (.env を確認してください)")
        return 0
    url = f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&q={quote(keyword)}&image_type=photo"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            return res.json().get("totalHits", 0)
        else:
            st.warning(f"Pixabay Error {res.status_code}: {res.text[:200]}")
            return 0
    except Exception as e:
        st.warning(f"Pixabay Exception: {e}")
        return 0

def get_unsplash_count(keyword: str) -> int:
    if not UNSPLASH_API_KEY:
        st.error("Unsplash APIキーが設定されていません (.env を確認してください)")
        return 0
    url = f"https://api.unsplash.com/search/photos?query={quote(keyword)}"
    headers = {"Authorization": f"Client-ID {UNSPLASH_API_KEY}"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json().get("total", 0)
        else:
            st.warning(f"Unsplash Error {res.status_code}: {res.text[:200]}")
            return 0
    except Exception as e:
        st.warning(f"Unsplash Exception: {e}")
        return 0

def get_trends_score(keyword: str) -> int:
    try:
        pytrends = TrendReq(hl='en-US', tz=360)
        pytrends.build_payload([keyword], cat=0, timeframe='today 12-m', geo='', gprop='')
        data = pytrends.interest_over_time()
        if not data.empty:
            return int(data[keyword].mean())
    except Exception:
        return 50
    return 50

# =============================
# CSV保存処理
# =============================
def save_to_csv(keyword, genre, pixabay_hits, unsplash_hits, trends_score, competition_score, final_score):
    filename = "analysis_results.csv"
    new_data = pd.DataFrame([{
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "keyword": keyword,
        "genre": genre,
        "pixabay_hits": pixabay_hits,
        "unsplash_hits": unsplash_hits,
        "trends_score": trends_score,
        "competition_score": competition_score,
        "final_score": final_score
    }])

    if os.path.exists(filename):
        old_data = pd.read_csv(filename)
        df = pd.concat([old_data, new_data], ignore_index=True)
    else:
        df = new_data

    df.to_csv(filename, index=False)
    return filename

# =============================
# Streamlit UI
# =============================
st.title("📊 売れやすさ分析アプリ")

keyword = st.text_input("調べたいキーワードを入力してください")

if keyword:
    st.write("⏳ データを取得中...")

    genre = classify_genre(keyword)
    pixabay_hits = get_pixabay_count(keyword)
    unsplash_hits = get_unsplash_count(keyword)
    trends_score = get_trends_score(keyword)

    competition_score = min(100, (pixabay_hits + unsplash_hits) // 1000)
    final_score = max(0, min(100, trends_score - competition_score/2))

    # =============================
    # 出力
    # =============================
    st.subheader("分析結果")
    st.write(f"🔹 ジャンル分類 → **{genre}**")
    st.write(f"🔹 Pixabay 件数 → {pixabay_hits}")
    st.write(f"🔹 Unsplash 件数 → {unsplash_hits}")
    st.write(f"🔹 Google Trends 人気度 → {trends_score} / 100")
    st.write(f"🔹 売れやすさ総合スコア → **{int(final_score)} / 100**")

    if final_score > 70:
        st.success("✅ 高スコア！今すぐ狙い目のジャンルです。")
    elif final_score > 50:
        st.warning("⚠️ 競合はやや多いですが需要あり。工夫すれば狙える。")
    else:
        st.error("❌ 需要に対して競合が多い。別の切り口を探すべき。")

    # =============================
    # CSV保存ボタン
    # =============================
    if st.button("💾 分析結果をCSV保存"):
        filename = save_to_csv(keyword, genre, pixabay_hits, unsplash_hits, trends_score, competition_score, final_score)
        st.success(f"分析結果を {filename} に保存しました。")

    # =============================
    # レーダーチャート
    # =============================
    st.subheader("📈 レーダーチャート")

    labels = ["需要度 (Trends)", "競合度", "売れやすさスコア"]
    values = [trends_score, competition_score, final_score]

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    values += values[:1]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.plot(angles, values, "o-", linewidth=2)
    ax.fill(angles, values, alpha=0.25)
    ax.set_thetagrids(np.degrees(angles[:-1]), labels)
    ax.set_ylim(0, 100)

    st.pyplot(fig)
