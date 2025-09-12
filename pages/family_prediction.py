import streamlit as st
from src import data_loader, styles, utils
from src.components import sidebar

def render_page():
    df_all = data_loader.load_data()
    sidebar.render_sidebar(df_all)
    
    st.subheader("Prediksi Risiko Keluarga – Scoring & Rekomendasi")
    st.caption("Isi form berikut untuk memprediksi risiko stunting. Data tidak disimpan.")

    with st.form("pred_form"):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            usia = st.number_input("Usia Anak (bulan)", 0, 60, 18)
            bblr = st.selectbox("BBLR (< 2500g)", ["Tidak", "Ya"], 0)
            asi = st.selectbox("ASI Eksklusif", ["Ya", "Tidak"], 0)
        with c2:
            mpasi = st.selectbox("MP-ASI Tepat & Sesuai", ["Ya", "Tidak"], 0)
            imun = st.selectbox("Imunisasi Lengkap", ["Ya", "Tidak"], 0)
            jk = st.selectbox("Jenis Kelamin Anak", ["L", "P"], 0)
        with c3:
            akses_air = st.selectbox("Akses Air Layak", ["Ada", "Tidak"], 0)
            jamban = st.selectbox("Jamban Sehat", ["Ada", "Tidak"], 0)
            edu = st.selectbox("Pendidikan Ibu", ["SD","SMP","SMA","D3","S1+"], 2)
        with c4:
            pengeluaran = st.number_input("Pengeluaran/Bulan (Rp)", 0, 20000000, 3000000, 50000)
            tanggungan = st.number_input("Jumlah Tanggungan", 1, 12, 4)
            st.text_input("Wilayah (opsional)", "Kab. Garut – Tarogong Kidul – Desa-01")

        submitted = st.form_submit_button("Hitung Risiko")

    if submitted:
        # Siapkan payload untuk API
        payload = {
            "usia_anak_bulan": usia, "jenis_kelamin": jk, "bblr": 1 if bblr == "Ya" else 0,
            "asi_eksklusif": 1 if asi == "Ya" else 0, "mp_asi_tepatsesuai": 1 if mpasi == "Ya" else 0,
            "imunisasi_lengkap": 1 if imun == "Ya" else 0, "pendidikan_ibu": edu,
            "akses_air_layak": 1 if akses_air == "Ada" else 0, "jamban_sehat": 1 if jamban == "Ada" else 0,
            "pengeluaran_bulan": int(pengeluaran), "tanggungan": int(tanggungan),
        }

        # Coba panggil API
        res = utils.post_json(st.session_state["predict_api"], payload)

        if res and "risk_score" in res:
            score = float(res.get("risk_score", 0))
            label = res.get("risk_label", "- ")
        else: # Fallback jika API gagal
            score = float(0.28*(1-payload["asi_eksklusif"]) + 0.20*(1-payload["imunisasi_lengkap"]) + 0.16*(1-payload["akses_air_layak"]) + 0.12*(1-payload["jamban_sehat"]) + 0.14*payload["bblr"] + 0.05*(payload["usia_anak_bulan"]/60.0) + 0.05*(payload["tanggungan"]/7.0))
            score = max(0.0, min(1.0, score))
            label = "Tinggi" if score > 0.66 else ("Sedang" if score > 0.33 else "Rendah")

        # Tampilkan hasil
        colA, colB = st.columns([1, 2])
        with colA:
            st.markdown("#### Hasil Prediksi")
            st.metric("Skor Risiko", f"{score:.2f}")
            st.markdown(f"Kategori: <span class='pill'>{label}</span>", unsafe_allow_html=True)
        with colB:
            recs = []
            if payload["bblr"]: recs.append("Pantau BBLR & PMT spesifik gizi")
            if not payload["asi_eksklusif"]: recs.append("Konseling ASI & dukungan laktasi")
            if not payload["imunisasi_lengkap"]: recs.append("Lengkapi imunisasi dasar")
            if not payload["akses_air_layak"] or not payload["jamban_sehat"]: recs.append("Program WASH (air & jamban sehat)")
            if not recs: recs.append("Monitoring berkala oleh kader/posyandu")
            st.markdown("#### Rekomendasi Cepat")
            st.write("\n".join([f"• {r}" for r in recs]))

# --- Main Execution ---
st.set_page_config(layout="wide")
styles.load_css()
render_page()
