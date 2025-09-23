import streamlit as st
import os
import json
import openai  # Mengganti requests dengan library resmi OpenAI
from src import styles, elastic_client as es
from src.components import sidebar


# --- FUNGSI AKSES LLM (DI-UPGRADE KE OPENAI) ---
def _get_openai_api_key():
    # Mencari OPENAI_API_KEY
    env_key = os.getenv("OPENAI_API_KEY", "")
    if env_key:
        return env_key
    try:
        return st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        return ""


def get_ai_insight(filters: dict, user_question: str) -> str:
    """
    Menghasilkan insight dari AI berdasarkan data agregat yang terfilter dan pertanyaan pengguna.
    """
    api_key = _get_openai_api_key()
    if not api_key:
        return "**Insight AI tidak tersedia.** `OPENAI_API_KEY` belum diatur."

    try:
        client = openai.OpenAI(api_key=api_key)
    except Exception as e:
        return f"Gagal menginisialisasi client OpenAI: {e}"

    # 1. Tarik data ringkasan dari Elasticsearch berdasarkan filter
    try:
        with st.spinner("Mengumpulkan data ringkasan dari server..."):
            summary_data = es.get_main_page_summary(filters)
            summary_data.pop(
                "charts", None
            )  # Hapus data yang tidak relevan untuk prompt
            summary_json = json.dumps(summary_data, indent=2, ensure_ascii=False)
    except Exception as e:
        st.error(f"Gagal mengambil data ringkasan dari Elasticsearch: {e}")
        return "Gagal memproses permintaan karena tidak bisa mengambil data."

    # 2. Buat prompt yang kuat, terinspirasi dari beta.py
    prompt = f"""
    Anda adalah seorang analis data kesehatan masyarakat senior yang ahli dalam analisis stunting di Jawa Barat.
    Anda sedang melihat dasbor data yang sudah difilter.

    **Konteks Filter Aktif:**
    {json.dumps(filters, indent=2)}

    **Ringkasan Data (KPI) dari Wilayah Terfilter:**
    ```json
    {summary_json}
    ```

    **Tugas Anda:**
    Berdasarkan **HANYA PADA DATA RINGKASAN DI ATAS**, jawab pertanyaan dari atasan Anda.
    Jawaban harus singkat, padat, berbasis data, dan langsung ke intinya. Gunakan format Markdown untuk poin-poin jika perlu.

    **Pertanyaan Atasan:** "{user_question}"
    """

    # 3. Panggil API OpenAI
    try:
        with st.spinner("AI sedang menganalisis data dan menyusun jawaban..."):
            response = client.chat.completions.create(
                model="gpt-4.1-nano",  # Menggunakan model yang diminta
                messages=[
                    {
                        "role": "system",
                        "content": "Anda adalah seorang analis data kesehatan masyarakat senior di Jawa Barat.",
                    },
                    {"role": "user", "content": prompt},
                ],
                timeout=60,
            )
            return response.choices[0].message.content
    except Exception as e:
        return f"Gagal menghubungi server OpenAI. Mohon coba lagi nanti. Error: {e}"


# --- RENDER HALAMAN ---
def render_page():
    st.subheader("💡 InsightNow - Tanya Jawab dengan Data")
    st.caption(
        "Ajukan pertanyaan tentang data yang sedang ditampilkan. AI akan menganalisisnya untuk Anda."
    )

    main_filters = sidebar.render()

    if "insight_messages" not in st.session_state:
        st.session_state.insight_messages = []

    for message in st.session_state.insight_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input(
        "Contoh: Apa saja faktor risiko paling umum di wilayah ini?"
    ):
        st.session_state.insight_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            response = get_ai_insight(main_filters, prompt)
            st.markdown(response)

        st.session_state.insight_messages.append(
            {"role": "assistant", "content": response}
        )


# --- Main Execution ---
if "page_config_set" not in st.session_state:
    st.set_page_config(layout="wide")
    st.session_state.page_config_set = True
styles.load_css()
render_page()
