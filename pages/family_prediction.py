import streamlit as st
import pandas as pd
import joblib
import requests
import json

# Muat model yang telah dilatih
try:
    model = joblib.load("models/stunting_model.joblib")
except FileNotFoundError:
    st.error(
        "File model 'stunting_model.joblib' tidak ditemukan. Pastikan file tersebut ada di dalam folder 'models/'."
    )
    st.stop()


# Fungsi untuk memanggil API OpenRouter dan mendapatkan rekomendasi
def get_llm_recommendation(user_data, prediction_proba, prediction_result):
    # Ganti dengan API Key Anda
    api_key = (
        "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"
    )
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    # Membuat prompt yang informatif untuk LLM
    prompt = f"""
    Anda adalah seorang ahli gizi dan kesehatan anak. Berikan rekomendasi yang personal, singkat, dan actionable (maksimal 3 poin) untuk keluarga di Indonesia berdasarkan data berikut:

    Data Anak dan Keluarga:
    - Usia Anak: {user_data["Usia Anak (bulan)"]} bulan
    - Berat Lahir: {user_data["Berat Lahir (gram)"]} gram
    - Jenis Kelamin: {"Laki-laki" if user_data["Jenis Kelamin"] == 1 else "Perempuan"}
    - ASI Eksklusif: {"Ya" if user_data["ASI Eksklusif"] == 1 else "Tidak"}
    - Status Imunisasi: {"Lengkap" if user_data["Status Imunisasi"] == 1 else "Tidak Lengkap"}
    - Akses Air Bersih: {"Layak" if user_data["Akses Air Bersih"] == 1 else "Tidak Layak"}
    - Paparan Asap Rokok: {"Ya" if user_data["Paparan Asap Rokok"] == 1 else "Tidak"}
    - Pendidikan Terakhir Ibu: {user_data["Pendidikan Terakhir Ibu"]}
    - Pekerjaan Orang Tua: {user_data["Pekerjaan Orang Tua"]}

    Hasil Prediksi Model:
    - Probabilitas Stunting: {prediction_proba:.2f}%
    - Kategori Risiko: {prediction_result}

    Tugas Anda:
    Berikan 3 rekomendasi praktis yang paling relevan untuk membantu keluarga ini mencegah atau mengatasi risiko stunting berdasarkan data yang paling menonjol. Gunakan bahasa yang mudah dipahami oleh orang awam.
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
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()
        recommendation = result["choices"][0]["message"]["content"]
        return recommendation
    except requests.exceptions.RequestException as e:
        return f"Terjadi kesalahan saat menghubungi server AI: {e}"
    except (KeyError, IndexError):
        return "Gagal memproses respons dari AI. Format respons tidak sesuai."


# Fungsi untuk mengirim data ke database
def upload_to_database(data):
    url = "https://your-database-url/stunting-data"
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.put(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        return "Data berhasil diunggah ke database."
    except requests.exceptions.RequestException as e:
        return f"Gagal mengunggah data: {e}"


# Judul halaman
st.set_page_config(page_title="Prediksi Risiko Keluarga", layout="wide")
st.title("Prediksi Risiko Keluarga – Scoring & Rekomendasi")
st.markdown(
    "Isi form berikut untuk memprediksi risiko stunting berdasarkan model Machine Learning."
)

# Membuat form input
with st.form(key="prediction_form"):
    st.subheader("1. Data Anak")
    col1, col2, col3 = st.columns(3)
    with col1:
        usia_anak = st.number_input(
            "Usia Anak (bulan)", min_value=0, max_value=60, value=12
        )
        berat_lahir = st.number_input(
            "Berat Lahir (gram)", min_value=1000, max_value=5000, value=3000
        )
    with col2:
        jenis_kelamin = st.radio("Jenis Kelamin", ["Laki-laki", "Perempuan"])
        asi_eksklusif = st.radio("ASI Eksklusif?", ["Ya", "Tidak"])
    with col3:
        status_imunisasi = st.radio("Status Imunisasi", ["Lengkap", "Tidak Lengkap"])
        akses_air_bersih = st.radio("Akses Air Bersih", ["Layak", "Tidak Layak"])
        paparan_asap_rokok = st.radio("Paparan Asap Rokok", ["Ya", "Tidak"])

    st.subheader("2. Data Ibu & Kehamilan")
    col1, col2, col3 = st.columns(3)
    with col1:
        tinggi_ibu = st.number_input(
            "Tinggi Badan Ibu (cm)", min_value=130, max_value=200, value=155
        )
        lila_saat_hamil = st.number_input(
            "LiLA saat Hamil (cm)", min_value=15.0, max_value=40.0, value=25.0, step=0.1
        )
        bmi_pra_hamil = st.number_input(
            "BMI Pra-Hamil", min_value=10.0, max_value=40.0, value=22.0, step=0.1
        )
    with col2:
        usia_ibu_hamil = st.number_input(
            "Usia Ibu saat Hamil (tahun)", min_value=15, max_value=50, value=28
        )
        kenaikan_bb_hamil = st.number_input(
            "Kenaikan BB saat Hamil (kg)", min_value=0, max_value=30, value=12
        )
        jarak_kehamilan = st.number_input(
            "Jarak Kehamilan Sebelumnya (bulan)", min_value=0, max_value=120, value=24
        )
    with col3:
        kadar_hb = st.number_input(
            "Kadar Hb (g/dL)", min_value=5.0, max_value=20.0, value=11.0, step=0.1
        )
        jumlah_kunjungan_anc = st.number_input(
            "Jumlah Kunjungan ANC", min_value=0, max_value=20, value=4
        )
        kepatuhan_ttd = st.selectbox("Kepatuhan Konsumsi TTD", ["Baik", "Kurang"])

    st.subheader("3. Kondisi Keluarga & Lainnya")
    col1, col2, col3 = st.columns(3)
    with col1:
        # Input ini tetap ada untuk dikirim ke LLM, tapi tidak untuk model ML
        pendidikan_ibu = st.selectbox(
            "Pendidikan Terakhir Ibu", ["SD", "SMP", "SMA", "Diploma/S1", "S2/S3"]
        )
        pekerjaan_ortu = st.selectbox(
            "Pekerjaan Orang Tua",
            ["PNS", "Wiraswasta", "Petani", "Buruh", "Tidak Bekerja"],
        )
        status_pernikahan = st.selectbox(
            "Status Pernikahan", ["Menikah", "Cerai", "Lainnya"]
        )
    with col2:
        jumlah_anak = st.number_input(
            "Total Jumlah Anak", min_value=1, max_value=15, value=1
        )
        riwayat_hipertensi = st.radio("Riwayat Hipertensi Ibu", ["Ya", "Tidak"])
    with col3:
        riwayat_diabetes = st.radio("Riwayat Diabetes Ibu", ["Ya", "Tidak"])
        program_bantuan = st.selectbox(
            "Program Bantuan Diterima", ["Tidak Ada", "BPNT", "PKH", "Lainnya"]
        )

    # Tombol untuk submit prediksi dan upload data baru
    col1, col2 = st.columns(2)
    with col1:
        submit_button = st.form_submit_button(label="🔬 Prediksi Risiko")
    with col2:
        upload_button = st.form_submit_button(label="📤 Upload Data Baru")

# Initialize prediction_proba in session state if not already set
if "prediction_proba" not in st.session_state:
    st.session_state["prediction_proba"] = 0.0

# Initialize session state for upload form visibility
if "show_upload_form" not in st.session_state:
    st.session_state["show_upload_form"] = False

# Jika tombol prediksi ditekan
if submit_button:
    # Kumpulkan semua data input, termasuk yang kategorikal untuk LLM
    input_data_for_llm = {
        "Usia Anak (bulan)": usia_anak,
        "Berat Lahir (gram)": berat_lahir,
        "Jenis Kelamin": 1 if jenis_kelamin == "Laki-laki" else 0,
        "ASI Eksklusif": 1 if asi_eksklusif == "Ya" else 0,
        "Status Imunisasi": 1 if status_imunisasi == "Lengkap" else 0,
        "Akses Air Bersih": 1 if akses_air_bersih == "Layak" else 0,
        "Paparan Asap Rokok": 1 if paparan_asap_rokok == "Ya" else 0,
        "Pendidikan Terakhir Ibu": pendidikan_ibu,  # Untuk LLM
        "Pekerjaan Orang Tua": pekerjaan_ortu,  # Untuk LLM
    }

    # **PERBAIKAN:** Buat DataFrame hanya dengan 19 fitur yang diharapkan model
    feature_names = [
        "usia_anak",
        "berat_lahir",
        "jenis_kelamin",
        "asi_eksklusif",
        "status_imunisasi",
        "akses_air_bersih",
        "paparan_asap_rokok",
        "tinggi_ibu",
        "lila_saat_hamil",
        "bmi_pra_hamil",
        "usia_ibu_hamil",
        "kenaikan_bb_hamil",
        "jarak_kehamilan",
        "kadar_hb",
        "jumlah_kunjungan_anc",
        "kepatuhan_ttd",
        "jumlah_anak",
        "riwayat_hipertensi_ibu",
        "riwayat_diabetes_ibu",
    ]

    # Data untuk input ke model machine learning
    input_for_model = {
        "usia_anak": [usia_anak],
        "berat_lahir": [berat_lahir],
        "jenis_kelamin": [1 if jenis_kelamin == "Laki-laki" else 0],
        "asi_eksklusif": [1 if asi_eksklusif == "Ya" else 0],
        "status_imunisasi": [1 if status_imunisasi == "Lengkap" else 0],
        "akses_air_bersih": [1 if akses_air_bersih == "Layak" else 0],
        "paparan_asap_rokok": [1 if paparan_asap_rokok == "Ya" else 0],
        "tinggi_ibu": [tinggi_ibu],
        "lila_saat_hamil": [lila_saat_hamil],
        "bmi_pra_hamil": [bmi_pra_hamil],
        "usia_ibu_hamil": [usia_ibu_hamil],
        "kenaikan_bb_hamil": [kenaikan_bb_hamil],
        "jarak_kehamilan": [jarak_kehamilan],
        "kadar_hb": [kadar_hb],
        "jumlah_kunjungan_anc": [jumlah_kunjungan_anc],
        "kepatuhan_ttd": [1 if kepatuhan_ttd == "Baik" else 0],
        "jumlah_anak": [jumlah_anak],
        "riwayat_hipertensi_ibu": [1 if riwayat_hipertensi == "Ya" else 0],
        "riwayat_diabetes_ibu": [1 if riwayat_diabetes == "Ya" else 0],
    }

    input_df = pd.DataFrame(input_for_model)
    # Pastikan urutan kolom sesuai (meskipun dalam kasus ini seharusnya sudah benar)
    input_df = input_df[feature_names]

    # Lakukan prediksi
    prediction_proba = model.predict_proba(input_df)[0][1] * 100
    prediction = "Stunting" if prediction_proba > 50 else "Tidak Stunting"

    # Simpan prediction_proba ke session state
    st.session_state["prediction_proba"] = prediction_proba

    # Tampilkan hasil
    st.subheader("Hasil Prediksi Model")
    st.info(
        "🔬 Simulasi prediksi tanpa standard scaling. Akurasi mungkin berbeda dari notebook."
    )

    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Probabilitas Stunting", value=f"{prediction_proba:.2f}%")
        st.write(f"Kategori: **{prediction}**")

    with col2:
        st.subheader("Rekomendasi Cepat dari AI 💡")
        with st.spinner("Membuat rekomendasi personal untuk Anda..."):
            # Dapatkan rekomendasi dari LLM
            recommendation = get_llm_recommendation(
                input_data_for_llm, prediction_proba, prediction
            )
            st.markdown(recommendation)

# Data UMP berdasarkan wilayah
UMP = {
    "Kabupaten Bandung": 3_700_000,
    "Kabupaten Bandung Barat": 3_600_000,
    "Kabupaten Bekasi": 5_200_000,
    "Kabupaten Bogor": 4_500_000,
    "Kabupaten Ciamis": 2_100_000,
    "Kabupaten Cianjur": 2_700_000,
    "Kabupaten Cirebon": 2_500_000,
    "Kabupaten Garut": 2_200_000,
    "Kabupaten Indramayu": 2_700_000,
    "Kabupaten Karawang": 5_300_000,
    "Kabupaten Kuningan": 2_300_000,
    "Kabupaten Majalengka": 2_400_000,
    "Kabupaten Pangandaran": 2_200_000,
    "Kabupaten Purwakarta": 4_800_000,
    "Kabupaten Subang": 3_000_000,
    "Kabupaten Sukabumi": 3_000_000,
    "Kabupaten Sumedang": 3_200_000,
    "Kabupaten Tasikmalaya": 2_400_000,
    "Kota Bandung": 4_000_000,
    "Kota Banjar": 2_300_000,
    "Kota Bekasi": 5_200_000,
    "Kota Bogor": 4_800_000,
    "Kota Cimahi": 3_800_000,
    "Kota Cirebon": 3_200_000,
    "Kota Depok": 4_800_000,
    "Kota Sukabumi": 3_200_000,
    "Kota Tasikmalaya": 2_600_000,
}

# Jika tombol upload data baru ditekan
if upload_button:
    st.session_state["show_upload_form"] = True

# Tampilkan form upload hanya jika tombol upload data baru ditekan
if st.session_state["show_upload_form"]:
    st.subheader("📤 Form Input Tambahan")
    with st.expander("Klik untuk membuka form upload data"):
        wilayah = st.selectbox("Wilayah", options=list(UMP.keys()))
        kecamatan = st.text_input("Kecamatan")
        tipe_wilayah = st.selectbox("Tipe Wilayah", ["Urban", "Rural"])
        nama_kepala_keluarga = st.text_input("Nama Kepala Keluarga")
        jenis_pekerjaan_ortu = st.selectbox(
            "Jenis Pekerjaan Orang Tua", ["PNS", "Wiraswasta", "Petani", "Buruh", "Tidak Bekerja"]
        )
        upah_keluarga = st.number_input("Upah Keluarga (Rp/bulan)", min_value=0, step=100000)
        
        # Auto-fill Rata-rata UMP Wilayah based on selected Wilayah
        rata_rata_ump = UMP.get(wilayah, 0)
        st.number_input(
            "Rata-rata UMP Wilayah (Rp/bulan)", value=rata_rata_ump, step=100000, disabled=True
        )
        
        z_score_tbu = st.number_input("Z-Score TB/U", step=0.01)
        prob_stunting_simulasi = st.number_input(
            "Probabilitas Stunting (simulasi)", value=st.session_state["prediction_proba"], step=0.01
        )

        submit_upload = st.button(label="Unggah Data")

        if submit_upload:
            # Gabungkan data tambahan dengan data prediksi
            new_data = {
                "Wilayah": wilayah,
                "Kecamatan": kecamatan,
                "Tipe Wilayah": tipe_wilayah,
                "Nama Kepala Keluarga": nama_kepala_keluarga,
                "Jenis Kelamin Anak": "Laki-laki" if jenis_kelamin == "Laki-laki" else "Perempuan",
                "Jenis Pekerjaan Orang Tua": jenis_pekerjaan_ortu,
                "Pendidikan Ibu": pendidikan_ibu,
                "Status Pernikahan": status_pernikahan,
                "Jumlah Anak": jumlah_anak,
                "Upah Keluarga (Rp/bulan)": upah_keluarga,
                "Rata-rata UMP Wilayah (Rp/bulan)": rata_rata_ump,
                "Akses Air Bersih": akses_air_bersih,
                "Status Imunisasi Anak": status_imunisasi,
                "Berat Lahir (gram)": berat_lahir,
                "ASI Eksklusif": asi_eksklusif,
                "Usia Anak (bulan)": usia_anak,
                "Tinggi Badan Ibu (cm)": tinggi_ibu,
                "LiLA saat Hamil (cm)": lila_saat_hamil,
                "BMI Pra-Hamil": bmi_pra_hamil,
                "Hb (g/dL)": kadar_hb,
                "Kenaikan BB Hamil (kg)": kenaikan_bb_hamil,
                "Usia Ibu saat Hamil (tahun)": usia_ibu_hamil,
                "Jarak Kehamilan Sebelumnya (bulan)": jarak_kehamilan,
                "Hipertensi Ibu": riwayat_hipertensi,
                "Diabetes Ibu": riwayat_diabetes,
                "Kunjungan ANC (x)": jumlah_kunjungan_anc,
                "Kepatuhan TTD": kepatuhan_ttd,
                "Paparan Asap Rokok": paparan_asap_rokok,
                "Kepesertaan Program Bantuan": program_bantuan,
                "Prob_raw": st.session_state["prediction_proba"] / 100,
                "Status Stunting (Biner)": "1" if prediction == "Stunting" else "0",
                "Kategori Stunting (3L)": prediction,
                "Z-Score TB/U": z_score_tbu,
                "Probabilitas Stunting (simulasi)": prob_stunting_simulasi,
            }

            # Kirim data ke database
            result = upload_to_database(new_data)
            st.success(result) if "berhasil" in result else st.error(result)
