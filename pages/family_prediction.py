import streamlit as st
from src import data_loader, styles, utils, model_loader
from src.components import sidebar

def render_page():
    # Panggil sidebar untuk UI konsisten & akses konfigurasi API
    df_all = data_loader.load_data()
    sidebar.render_sidebar(df_all)
    
    st.subheader("Prediksi Risiko Keluarga – Scoring & Rekomendasi")
    st.caption("Isi form berikut untuk memprediksi risiko stunting berdasarkan model Machine Learning.")

    with st.form("pred_form_ml"):
        # --- Bagian 1: Data Anak ---
        st.markdown("##### 1. Data Anak")
        c1, c2, c3 = st.columns(3)
        with c1:
            usia_anak_bulan = st.number_input("Usia Anak (bulan)", 0, 72, 24)
            berat_lahir_gram = st.number_input("Berat Lahir (gram)", 1000, 5000, 3000)
            jenis_kelamin_anak = st.selectbox("Jenis Kelamin", ["Laki-laki", "Perempuan"])
        with c2:
            asi_eksklusif = st.selectbox("ASI Eksklusif?", ["Ya", "Tidak"])
            status_imunisasi_anak = st.selectbox("Status Imunisasi", ["Lengkap", "Tidak Lengkap", "Dasar Tidak Lengkap"])
        with c3:
             akses_air_bersih = st.selectbox("Akses Air Bersih", ["Layak", "Tidak Layak"])
             paparan_asap_rokok = st.selectbox("Paparan Asap Rokok", ["Ya", "Tidak"])

        # --- Bagian 2: Data Ibu & Kehamilan ---
        st.markdown("##### 2. Data Ibu & Kehamilan")
        c4, c5, c6 = st.columns(3)
        with c4:
            tinggi_badan_ibu_cm = st.number_input("Tinggi Badan Ibu (cm)", 130, 200, 155)
            lila_saat_hamil_cm = st.number_input("LiLA saat Hamil (cm)", 15.0, 40.0, 23.5, 0.1)
            bmi_pra_hamil = st.number_input("BMI Pra-Hamil", 10.0, 40.0, 21.0, 0.1)
        with c5:
            usia_ibu_saat_hamil_tahun = st.number_input("Usia Ibu saat Hamil (tahun)", 15, 50, 28)
            kenaikan_bb_hamil_kg = st.number_input("Kenaikan BB saat Hamil (kg)", 1, 30, 12)
            jarak_kehamilan_sebelumnya_bulan = st.number_input("Jarak Kehamilan Sebelumnya (bulan)", 0, 120, 24, help="Isi 0 jika ini kehamilan pertama")
        with c6:
            hb_g_dl = st.number_input("Kadar Hb (g/dL)", 5.0, 20.0, 11.5, 0.1)
            kunjungan_anc_x = st.number_input("Jumlah Kunjungan ANC", 0, 20, 8)
            kepatuhan_ttd = st.selectbox("Kepatuhan Konsumsi TTD", ["Baik", "Kurang"])

        # --- Bagian 3: Kondisi Keluarga & Lainnya ---
        st.markdown("##### 3. Kondisi Keluarga & Lainnya")
        c7, c8, c9 = st.columns(3)
        with c7:
            pendidikan_ibu = st.selectbox("Pendidikan Terakhir Ibu", ["SD", "SMP", "SMA", "Diploma", "S1"])
            jenis_pekerjaan_orang_tua = st.selectbox("Pekerjaan Orang Tua", ["PNS", "Wiraswasta", "Buruh", "Petani", "Lainnya"])
            status_pernikahan = st.selectbox("Status Pernikahan", ["Menikah", "Belum Menikah"])
        with c8:
            jumlah_anak = st.number_input("Total Jumlah Anak", 1, 15, 2)
            hipertensi_ibu = st.selectbox("Riwayat Hipertensi Ibu", ["Tidak", "Ya"])
            diabetes_ibu = st.selectbox("Riwayat Diabetes Ibu", ["Tidak", "Ya"])
        with c9:
             kepesertaan_program_bantuan = st.selectbox("Program Bantuan Diterima", ["Tidak Ada", "PKH", "BPNT"])
        
        submitted = st.form_submit_button("Hitung Risiko Stunting")

    if submitted:
        # Siapkan payload untuk model lokal. Nama key harus sama persis dengan yang di `predict_local`
        payload = {
            'jenis_kelamin_anak': jenis_kelamin_anak, 'jenis_pekerjaan_orang_tua': jenis_pekerjaan_orang_tua,
            'pendidikan_ibu': pendidikan_ibu, 'status_pernikahan': status_pernikahan, 'jumlah_anak': jumlah_anak,
            'akses_air_bersih': akses_air_bersih, 'status_imunisasi_anak': status_imunisasi_anak,
            'berat_lahir_gram': berat_lahir_gram, 'asi_eksklusif': asi_eksklusif, 'usia_anak_bulan': usia_anak_bulan,
            'tinggi_badan_ibu_cm': tinggi_badan_ibu_cm, 'lila_saat_hamil_cm': lila_saat_hamil_cm,
            'bmi_pra_hamil': bmi_pra_hamil, 'hb_g_dl': hb_g_dl, 'kenaikan_bb_hamil_kg': kenaikan_bb_hamil_kg,
            'usia_ibu_saat_hamil_tahun': usia_ibu_saat_hamil_tahun,
            'jarak_kehamilan_sebelumnya_bulan': jarak_kehamilan_sebelumnya_bulan, 'hipertensi_ibu': hipertensi_ibu,
            'diabetes_ibu': diabetes_ibu, 'kunjungan_anc_x': kunjungan_anc_x, 'kepatuhan_ttd': kepatuhan_ttd,
            'paparan_asap_rokok': paparan_asap_rokok, 'kepesertaan_program_bantuan': kepesertaan_program_bantuan
        }
        
        # Panggil model lokal (karena API tidak disiapkan untuk fitur ini)
        model = model_loader.load_model()
        if model:
            with st.spinner("Melakukan prediksi lokal..."):
                prediction_result = model_loader.predict_local(model, payload)

            if prediction_result and "error" not in prediction_result:
                score = float(prediction_result.get("risk_score", 0))
                label = prediction_result.get("risk_label", "- ")
                
                colA, colB = st.columns([1, 2])
                with colA:
                    st.markdown("#### Hasil Prediksi Model")
                    st.metric("Probabilitas Stunting", f"{score:.2%}")
                    if label == "Stunting":
                        st.error(f"Kategori: **{label}**")
                    else:
                        st.success(f"Kategori: **{label}**")
                with colB:
                    st.markdown("#### Rekomendasi Cepat (Contoh)")
                    recs = []
                    if berat_lahir_gram < 2500: recs.append("Perkuat pemantauan BBLR dan pastikan asupan gizi.")
                    if status_imunisasi_anak != "Lengkap": recs.append("Segera lengkapi imunisasi dasar di Posyandu/Puskesmas.")
                    if hb_g_dl < 11.0: recs.append("Konsultasi gizi terkait anemia dan konsumsi tablet tambah darah (TTD).")
                    if not recs: recs.append("Pertahankan pola asuh dan gizi yang baik, lakukan monitoring berkala.")
                    st.write("\n".join([f"• {r}" for r in recs]))
            else:
                st.error("Gagal melakukan prediksi. Cek log untuk detail.")
        else:
            st.error("Model lokal tidak dapat dimuat. Prediksi dibatalkan.")

# --- Main Execution ---
st.set_page_config(layout="wide", page_title="Prediksi Keluarga")
styles.load_css()
render_page()

