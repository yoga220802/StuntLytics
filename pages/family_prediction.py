import streamlit as st
import pandas as pd
import joblib
import requests
import json
import os

# Helper aman untuk ambil API key
def _get_openrouter_api_key():
    env_key = os.getenv("OPENROUTER_API_KEY", "")
    if env_key:
        return env_key
    try:
        # Akses dibungkus try agar tidak memicu StreamlitSecretNotFoundError
        return st.secrets["OPENROUTER_API_KEY"]
    except Exception:
        return ""

# Muat model yang telah dilatih
try:
    model = joblib.load("models\modell_stunting_terbaik (1).joblib")
    MODEL_FEATURES = list(getattr(model, "feature_names_in_", []))
except FileNotFoundError:
    st.error("File model tidak ditemukan di folder 'models/'.")
    st.stop()
except Exception as e:
    st.error(f"Gagal memuat model: {e}")
    st.stop()


# Fungsi untuk memanggil API OpenRouter dan mendapatkan rekomendasi
def get_llm_recommendation(user_data, prediction_proba, prediction_result):
    api_key = _get_openrouter_api_key()
    if not api_key:
        return "API Key LLM tidak tersedia. Set OPENROUTER_API_KEY sebagai environment variable atau tambahkan ke .streamlit/secrets.toml."
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

# Data UMP (dipindah ke atas agar bisa dipakai saat prediksi)
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

# Membuat form input
with st.form(key="prediction_form"):
    # Tambah pemilihan wilayah untuk derivasi UMP (Wilayah sendiri tidak menjadi fitur)
    wilayah_pred = st.selectbox("Wilayah (untuk hitung UMP)", options=list(UMP.keys()))
    rata_rata_ump_pred = UMP.get(wilayah_pred, 0)
    st.caption(f"Rata-rata UMP Wilayah: Rp {rata_rata_ump_pred:,}")

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
        # INPUT BARU (dipindah dari form upload agar bisa dipakai model)
        tipe_wilayah = st.selectbox("Tipe Wilayah", ["Urban", "Rural"])
    with col2:
        jumlah_anak = st.number_input(
            "Total Jumlah Anak", min_value=1, max_value=15, value=1
        )
        riwayat_hipertensi = st.radio("Riwayat Hipertensi Ibu", ["Ya", "Tidak"])
        # INPUT BARU
        upah_keluarga = st.number_input(
            "Upah Keluarga (Rp/bulan)", min_value=0, step=100000, value=0
        )
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

def build_model_input(
    riwayat_hipertensi,
    riwayat_diabetes,
    kepatuhan_ttd,
    paparan_asap_rokok,
    tipe_wilayah,
    pekerjaan_ortu,
    pendidikan_ibu,
    status_pernikahan,
    program_bantuan,
    lila_saat_hamil,
    bmi_pra_hamil,
    kadar_hb,
    kenaikan_bb_hamil,
    usia_ibu_hamil,
    jarak_kehamilan,
    jumlah_kunjungan_anc,
    jumlah_anak,
    upah_keluarga,
    akses_air_bersih,
    # fitur anak & ekonomi tambahan
    jenis_kelamin,
    berat_lahir,
    asi_eksklusif,
    usia_anak,
    tinggi_ibu,
    status_imunisasi,
    rata_rata_ump
):
    # Encoder sederhana
    map_simple = {
        'Tipe Wilayah': {'Rural': 0, 'Urban': 1},
        'Jenis Pekerjaan Orang Tua': {
            'Tidak Bekerja': 0, 'Buruh': 1, 'Petani': 2, 'Wiraswasta': 3, 'PNS': 4
        },
        'Pendidikan Ibu': {
            'SD': 0, 'SMP': 1, 'SMA': 2, 'Diploma/S1': 3, 'S2/S3': 4
        },
        'Status Pernikahan': {
            'Lainnya': 0, 'Cerai': 1, 'Menikah': 2
        },
        'Kepesertaan Program Bantuan': {
            'Tidak Ada': 0, 'Lainnya': 1, 'BPNT': 2, 'PKH': 3
        }
    }
    def bin01(val, pos): return 1 if val == pos else 0

    # Base row disesuaikan dengan 28 fitur training (tanpa target & tanpa kolom yang di-drop)
    base_row = {
        'Tipe Wilayah': map_simple['Tipe Wilayah'][tipe_wilayah],
        'Jenis Kelamin Anak': bin01(jenis_kelamin, 'Laki-laki'),
        'Jenis Pekerjaan Orang Tua': map_simple['Jenis Pekerjaan Orang Tua'][pekerjaan_ortu],
        'Pendidikan Ibu': map_simple['Pendidikan Ibu'][pendidikan_ibu],
        'Status Pernikahan': map_simple['Status Pernikahan'][status_pernikahan],
        'Jumlah Anak': jumlah_anak,
        'Upah Keluarga (Rp/bulan)': upah_keluarga,
        'Rata-rata UMP Wilayah (Rp/bulan)': rata_rata_ump,
        'Akses Air Bersih': bin01(akses_air_bersih, 'Layak'),
        'Status Imunisasi Anak': bin01(status_imunisasi, 'Lengkap'),
        'Berat Lahir (gram)': berat_lahir,
        'ASI Eksklusif': bin01(asi_eksklusif, 'Ya'),
        'Usia Anak (bulan)': usia_anak,
        'Tinggi Badan Ibu (cm)': tinggi_ibu,
        'LiLA saat Hamil (cm)': lila_saat_hamil,
        'BMI Pra-Hamil': bmi_pra_hamil,
        'Hb (g/dL)': kadar_hb,
        'Kenaikan BB Hamil (kg)': kenaikan_bb_hamil,
        'Usia Ibu saat Hamil (tahun)': usia_ibu_hamil,
        'Jarak Kehamilan Sebelumnya (bulan)': jarak_kehamilan,
        'Hipertensi Ibu': bin01(riwayat_hipertensi, 'Ya'),
        'Diabetes Ibu': bin01(riwayat_diabetes, 'Ya'),
        'Kunjungan ANC (x)': jumlah_kunjungan_anc,
        'Kepatuhan TTD': bin01(kepatuhan_ttd, 'Baik'),
        'Paparan Asap Rokok': bin01(paparan_asap_rokok, 'Ya'),
        'Kepesertaan Program Bantuan': map_simple['Kepesertaan Program Bantuan'][program_bantuan],
        # Placeholder probabilitas (di-training ada sebagai fitur rekayasa)
        'Prob_raw': 0.0,
        'Probabilitas Stunting (simulasi)': 0.0
    }

    if not MODEL_FEATURES:
        return pd.DataFrame([base_row])

    missing = [f for f in MODEL_FEATURES if f not in base_row]
    for f in missing:
        base_row[f] = 0  # fallback
    aligned_row = {k: base_row[k] for k in MODEL_FEATURES}

    if missing:
        st.warning(f"Fitur (default=0) ditambahkan otomatis: {missing}")
    return pd.DataFrame([aligned_row], columns=MODEL_FEATURES)

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

    input_df = build_model_input(
        riwayat_hipertensi=riwayat_hipertensi,
        riwayat_diabetes=riwayat_diabetes,
        kepatuhan_ttd=kepatuhan_ttd,
        paparan_asap_rokok=paparan_asap_rokok,
        tipe_wilayah=tipe_wilayah,
        pekerjaan_ortu=pekerjaan_ortu,
        pendidikan_ibu=pendidikan_ibu,
        status_pernikahan=status_pernikahan,
        program_bantuan=program_bantuan,
        lila_saat_hamil=lila_saat_hamil,
        bmi_pra_hamil=bmi_pra_hamil,
        kadar_hb=kadar_hb,
        kenaikan_bb_hamil=kenaikan_bb_hamil,
        usia_ibu_hamil=usia_ibu_hamil,
        jarak_kehamilan=jarak_kehamilan,
        jumlah_kunjungan_anc=jumlah_kunjungan_anc,
        jumlah_anak=jumlah_anak,
        upah_keluarga=upah_keluarga,
        akses_air_bersih=akses_air_bersih,
        jenis_kelamin=jenis_kelamin,
        berat_lahir=berat_lahir,
        asi_eksklusif=asi_eksklusif,
        usia_anak=usia_anak,
        tinggi_ibu=tinggi_ibu,
        status_imunisasi=status_imunisasi,
        rata_rata_ump=rata_rata_ump_pred
    )

    # Validasi jumlah fitur sebelum prediksi
    expected = getattr(model, "n_features_in_", None)
    if expected and input_df.shape[1] != expected:
        st.error(
            f"Jumlah fitur tidak sesuai. Model mengharapkan {expected}, tetapi input memiliki {input_df.shape[1]}. "
            f"Nama fitur model: {list(getattr(model, 'feature_names_in_', []))}"
        )
    else:
        try:
            prediction_proba = model.predict_proba(input_df)[0][1] * 100
            prediction = "Stunting" if prediction_proba > 50 else "Tidak Stunting"
            st.session_state["prediction_proba"] = prediction_proba
        except Exception as e:
            st.error(f"Gagal melakukan prediksi: {e}")
            prediction_proba = 0
            prediction = "Tidak Diketahui"

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
