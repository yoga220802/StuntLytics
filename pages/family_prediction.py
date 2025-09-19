import streamlit as st
import pandas as pd
import os
import json
import requests
from src import prediction_service  # Menggunakan service pipeline yang baru


# ==============================================================================
# LOGIKA UNTUK FITUR INSIGHTNOW (AI RECOMMENDATION)
# Tetap sama, tidak ada perubahan di sini
# ==============================================================================
def _get_openrouter_api_key():
    env_key = os.getenv("OPENROUTER_API_KEY", "")
    if env_key:
        return env_key
    try:
        return st.secrets.get("OPENROUTER_API_KEY", "")
    except Exception:
        return ""


def generate_recommendation(
    user_data: dict, prediction_proba: float, prediction_result: str
) -> str:
    api_key = _get_openrouter_api_key()
    if not api_key:
        return (
            "**Rekomendasi AI tidak tersedia.**\n\n"
            "API Key untuk LLM (OpenRouter) belum di-set."
        )

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    prompt = f"""
    Anda adalah seorang ahli gizi dan kesehatan kandungan di Indonesia. Berikan rekomendasi yang personal, singkat, dan actionable (maksimal 3 poin dalam format bullet points) untuk seorang **ibu hamil** berdasarkan data berikut:

    **Data Ibu & Keluarga:**
    - Tinggi Badan Ibu: {user_data.get("tinggi_badan_ibu_cm", "N/A")} cm
    - LiLA saat Hamil: {user_data.get("lila_saat_hamil_cm", "N/A")} cm
    - Kepatuhan Konsumsi TTD: {user_data.get("kepatuhan_ttd", "N/A")}
    - Pendidikan Terakhir Ibu: {user_data.get("pendidikan_ibu", "N/A")}

    **Hasil Prediksi Model Machine Learning:**
    - Prediksi Risiko Stunting pada Anak (Nantinya): {prediction_result}
    - Tingkat Probabilitas Risiko: {prediction_proba:.2f}%

    **Tugas Anda:**
    Fokus pada 3 rekomendasi praktis yang paling relevan untuk membantu ibu hamil ini **selama masa kehamilannya** untuk mengurangi risiko stunting pada anak yang akan dilahirkannya. Gunakan bahasa yang mudah dipahami.
    """

    data = {
        "model": "qwen/qwen-2.5-7b-instruct",
        "messages": [{"role": "user", "content": prompt}],
    }

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            data=json.dumps(data),
            timeout=45,
        )
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Gagal menghubungi server AI. Mohon coba lagi nanti. Error: {e}"


# --- BAGIAN UTAMA APLIKASI STREAMLIT ---

# Muat SATU pipeline saja
pipeline = prediction_service.load_pipeline()

st.set_page_config(page_title="Prediksi Risiko Stunting", layout="wide")
st.title("Prediksi Risiko Stunting Selama Kehamilan")
st.markdown(
    "Isi form data ibu hamil untuk memprediksi risiko stunting pada anak yang akan lahir."
)

if pipeline:
    with st.form(key="prediction_form"):
        st.subheader("1. Data Ibu & Kehamilan")
        col1, col2, col3 = st.columns(3)
        with col1:
            tinggi_badan_ibu_cm = st.number_input(
                "Tinggi Badan Ibu (cm)", min_value=130, max_value=200, value=155
            )
            lila_saat_hamil_cm = st.number_input(
                "LiLA saat Hamil (cm)",
                min_value=15.0,
                max_value=40.0,
                value=25.0,
                step=0.1,
            )
            bmi_pra_hamil = st.number_input(
                "BMI Pra-Hamil", min_value=10.0, max_value=40.0, value=22.0, step=0.1
            )
        with col2:
            usia_ibu_saat_hamil_tahun = st.number_input(
                "Usia Ibu saat Hamil (tahun)", min_value=15, max_value=50, value=28
            )
            kenaikan_bb_hamil_kg = st.number_input(
                "Kenaikan BB saat Hamil (kg)", min_value=0, max_value=30, value=12
            )
            jarak_kehamilan_sebelumnya_bulan = st.number_input(
                "Jarak Kehamilan Sebelumnya (bulan)",
                min_value=0,
                max_value=120,
                value=24,
            )
        with col3:
            hb_g_dl = st.number_input(
                "Kadar Hb (g/dL)", min_value=5.0, max_value=20.0, value=11.0, step=0.1
            )
            kunjungan_anc_x = st.number_input(
                "Jumlah Kunjungan ANC", min_value=0, max_value=20, value=4
            )
            kepatuhan_ttd = st.selectbox(
                "Kepatuhan Konsumsi TTD", ["Rutin", "Tidak Rutin"]
            )

        st.subheader("2. Kondisi Keluarga & Lainnya")
        col1, col2, col3 = st.columns(3)
        with col1:
            # Pastikan pilihan ini sama persis dengan yang ada di dataset asli
            pendidikan_ibu = st.selectbox(
                "Pendidikan Terakhir Ibu",
                ["SD", "SMP", "SMA", "Diploma", "S1", "S2/S3", "Tidak Sekolah"],
            )
            jenis_pekerjaan_orang_tua = st.selectbox(
                "Pekerjaan Orang Tua",
                [
                    "Buruh",
                    "Lainnya",
                    "Nelayan",
                    "PNS/TNI/Polri",
                    "Petani/Buruh Tani",
                    "TKI/TKW",
                    "Wiraswasta",
                ],
            )
            status_pernikahan = st.selectbox(
                "Status Pernikahan", ["Menikah", "Cerai"]
            )
        with col2:
            jumlah_anak = st.number_input(
                "Total Jumlah Anak Sebelumnya", min_value=0, max_value=15, value=1
            )
            kepesertaan_program_bantuan = st.radio(
                "Menerima Program Bantuan?", ["Ya", "Tidak"]
            )
            paparan_asap_rokok = st.radio(
                "Paparan Asap Rokok di Rumah?", ["Ya", "Tidak"]
            )
        with col3:
            akses_air_bersih = st.radio("Akses Air Bersih Layak?", ["Ya", "Tidak"])
            hipertensi_ibu = (
                1
                if st.radio("Riwayat Hipertensi Ibu?", ["Ya", "Tidak"], index=1) == "Ya"
                else 0
            )
            diabetes_ibu = (
                1
                if st.radio("Riwayat Diabetes Ibu?", ["Ya", "Tidak"], index=1) == "Ya"
                else 0
            )

        submit_button = st.form_submit_button(
            label="🔬 Prediksi & Dapatkan Rekomendasi"
        )

    if submit_button:
        # Kumpulkan semua data mentah ke dalam dictionary
        # Nama key HARUS sama dengan nama kolom di DataFrame awal
        input_data = {
            "tinggi_badan_ibu_cm": tinggi_badan_ibu_cm,
            "lila_saat_hamil_cm": lila_saat_hamil_cm,
            "bmi_pra_hamil": bmi_pra_hamil,
            "hb_g_dl": hb_g_dl,
            "kenaikan_bb_hamil_kg": kenaikan_bb_hamil_kg,
            "usia_ibu_saat_hamil_tahun": usia_ibu_saat_hamil_tahun,
            "jarak_kehamilan_sebelumnya_bulan": jarak_kehamilan_sebelumnya_bulan,
            "kunjungan_anc_x": kunjungan_anc_x,
            "jumlah_anak": jumlah_anak,
            "kepatuhan_ttd": kepatuhan_ttd,
            "pendidikan_ibu": pendidikan_ibu,
            "jenis_pekerjaan_orang_tua": jenis_pekerjaan_orang_tua,
            "status_pernikahan": status_pernikahan,
            "kepesertaan_program_bantuan": kepesertaan_program_bantuan,
            "akses_air_bersih": akses_air_bersih,
            "paparan_asap_rokok": paparan_asap_rokok,
            "hipertensi_ibu": hipertensi_ibu,
            "diabetes_ibu": diabetes_ibu,
        }

        # Panggil prediction service dengan pipeline dan data mentah
        prediction_result = prediction_service.run_prediction(pipeline, input_data)

        st.subheader("Hasil Analisis")
        if prediction_result["error"]:
            st.error(f"Gagal melakukan prediksi: {prediction_result['error']}")
        else:
            col1, col2 = st.columns(2)
            with col1:
                st.metric(
                    label="Probabilitas Risiko Stunting",
                    value=f"{prediction_result['probability']:.2f}%",
                )
                st.write(f"Kategori: **{prediction_result['result']}**")

            with col2:
                st.subheader("💡 Rekomendasi InsightNow")
                with st.spinner("AI sedang menganalisis dan membuat rekomendasi..."):
                    recommendation = generate_recommendation(
                        input_data,
                        prediction_result["probability"],
                        prediction_result["result"],
                    )
                    st.markdown(recommendation)
else:
    st.error(
        "Gagal memuat pipeline prediksi. Mohon periksa file 'models/stunting_pipeline.joblib'."
    )
