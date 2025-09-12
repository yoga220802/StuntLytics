import streamlit as st
from src import data_loader, styles, utils
from src.components import sidebar

def render_page():
    # --- Load data and apply filters ---
    df_all = data_loader.load_data()
    filters = sidebar.render_sidebar(df_all)
    df_filtered = sidebar.apply_filters(df_all, filters)

    st.subheader("InsightNow – Rekomendasi Intervensi Berbasis AI")
    st.caption("Masukkan konteks wilayah lalu minta saran program prioritas. Sistem akan memanggil API jika tersedia.")

    user_ctx = st.text_area("Konteks Wilayah", value=(
        "Kecamatan dengan proporsi risiko tinggi > 20%, cakupan imunisasi rendah, akses air layak 60%."
    ))

    if st.button("Dapatkan Rekomendasi"):
        metrics = {
            "pct_high_risk": float((df_filtered["risk_label"].eq("Tinggi").mean()*100) if not df_filtered.empty else 0),
            "immunization_coverage": float(df_filtered["imunisasi_lengkap"].mean()*100 if not df_filtered.empty else 0),
            "water_access": float(df_filtered["akses_air_layak"].mean()*100 if not df_filtered.empty else 0),
        }
        payload = {"context": user_ctx, "metrics": metrics}
        
        with st.spinner("Menganalisis dan mencari rekomendasi..."):
            res = utils.post_json(st.session_state["insight_api"], payload)
        
        if res and "recommendations" in res:
            st.success("Rekomendasi dari model AI:")
            st.write("\n".join([f"• {r}" for r in res["recommendations"]]))
        else:
            # Fallback heuristic
            fallback = []
            if metrics["water_access"] < 70: fallback.append("Prioritaskan program PAMSIMAS/air bersih.")
            if metrics["immunization_coverage"] < 80: fallback.append("Lakukan sweeping imunisasi & kampanye posyandu.")
            if metrics["pct_high_risk"] > 15: fallback.append("Perluas PMT dan kunjungan rumah keluarga berisiko.")
            if not fallback: fallback.append("Pertahankan program berjalan, lakukan monitoring triwulanan.")
            st.info("Fallback (API tidak tersedia): Rekomendasi berdasarkan rule sederhana.")
            st.write("\n".join([f"• {r}" for r in fallback]))

# --- Main Execution ---
st.set_page_config(layout="wide")
styles.load_css()
render_page()
