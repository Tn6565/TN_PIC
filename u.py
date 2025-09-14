import os
from dotenv import load_dotenv
import replicate
import streamlit as st

# ----------------------
# 環境変数読み込み
# ----------------------
load_dotenv()  # ローカル用
REPLICATE_API_TOKEN = os.getenv("EXTNREPLICATE")

if not REPLICATE_API_TOKEN:
    st.error("EXTNREPLICATE が設定されていません")
    st.stop()

# ----------------------
# Replicateクライアント初期化
# ----------------------
client = replicate.Client(api_token=REPLICATE_API_TOKEN)

# ----------------------
# Streamlit UI
# ----------------------
st.title("Stable Diffusion 1.5 画像生成")

prompt = st.text_area("生成プロンプト", "かわいい猫、自然光、白背景", max_chars=150)
width = st.number_input("幅 (px)", 128, 1024, 512, 64)
height = st.number_input("高さ (px)", 128, 1024, 512, 64)
steps = st.slider("ステップ数", 10, 50, 20)

if st.button("画像を生成"):
    with st.spinner("画像生成中..."):
        try:
            # モデルID指定
            model_version = "stability-ai/stable-diffusion:b3d14e1cd1f9470bbb0bb68cac48e5f483e5be309551992cc33dc30654a82bb7"

            output = client.run(
                model_version,
                input={
                    "prompt": prompt,
                    "width": width,
                    "height": height,
                    "num_inference_steps": steps,
                },
            )

            # FileOutput → URL に変換
            if isinstance(output, list):
                urls = [str(o) for o in output]
                st.success(f"{len(urls)} 枚の画像を生成しました")
                for i, url in enumerate(urls):
                    st.image(url, caption=f"{prompt} (画像{i+1})", use_column_width=True)
                    st.markdown(f"[画像{i+1}_ダウンロード]({url})")

        except Exception as e:
            st.error(f"画像生成失敗: {e}")
