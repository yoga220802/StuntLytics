import streamlit as st
import pandas as pd

from src import data_loader, styles, config
from src.components import sidebar

def render_page():
    # --- Load data and apply filters ---
    df_all = data_loader.load_data()
    filters = sidebar.render_sidebar(df_all)
    df_filtered = sidebar.apply_filters(df_all, filters)

    st.subheader("Tren & Korelasi – Analitik Pendukung Kebijakan")
    
    if df_filtered.empty:
        st.info("Tidak ada data untuk ditampilkan dengan filter saat ini.")
        return

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Tren Proporsi Risiko Tinggi per Bulan**")
        t = df_filtered.assign(bulan=df_filtered["tanggal"].dt.to_period("M").dt.to_timestamp())
        tt = t.groupby("bulan")["risk_label"].apply(lambda s: (s=="Tinggi").mean()*100).rename("Tinggi %").reset_index()
        st.line_chart(tt.set_index("bulan"))

    with c2:
        st.markdown("**Korelasi Sederhana terhadap Skor Risiko**")
        num_cols = ["bblr","asi_eksklusif","imunisasi_lengkap","akses_air_layak","jamban_sehat","usia_anak_bulan","tanggungan","risk_score"]
        corr = df_filtered[num_cols].corr(numeric_only=True)
        st.dataframe(corr.style.background_gradient(cmap='coolwarm', axis=None))

    st.markdown("### Insight Otomatis (Rule-based)")
    msgs = []
    try:
        for key, rule in config.INSIGHT_RULES.items():
            if rule["when"](df_filtered):
                msgs.append(rule["msg"])
    except Exception:
        pass
    
    if msgs:
        st.success("\n".join([f"• {m}" for m in msgs]))
    else:
        st.info("Tidak ada insight khusus dari rule sederhana untuk data yang ditampilkan.")

# --- Main Execution ---
st.set_page_config(layout="wide")
styles.load_css()
render_page()
