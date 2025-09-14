import streamlit as st
import pandas as pd

from src import config, styles, data_loader
from src.components import sidebar


def main():
    st.set_page_config(
        page_title=config.APP_TITLE,
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    styles.load_css()

    df_all = data_loader.load_data()
    filters = sidebar.render_sidebar(df_all)
    df_filtered = sidebar.apply_filters(df_all, filters)

    # Header
    st.markdown(
        f'<div class="app-header">{config.APP_TITLE}</div>', unsafe_allow_html=True
    )
    st.markdown(
        f'<div class="app-subtitle">{config.APP_DESCRIPTION}</div>',
        unsafe_allow_html=True,
    )

    # Metrik / KPI Utama - dengan struktur HTML baru
    col1, col2, col3, col4 = st.columns(4)

    total_observasi = len(df_filtered)
    pct_high = (
        (df_filtered["risk_label"].eq("Tinggi").mean() * 100)
        if total_observasi > 0
        else 0
    )
    imun_cov = (
        df_filtered["imunisasi_lengkap"].mean() * 100 if total_observasi > 0 else 0
    )
    air_cov = df_filtered["akses_air_layak"].mean() * 100 if total_observasi > 0 else 0

    with col1:
        st.markdown(
            """
            <div class="metric-card">
                <div class="metric-card-title">Total Observasi</div>
        """,
            unsafe_allow_html=True,
        )
        # FIX: Added non-empty label and visibility parameter
        st.metric("Total Observasi", f"{total_observasi:,}", label_visibility="hidden")
        st.markdown(
            '<div class="small-muted">setelah filter</div></div>',
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            """
            <div class="metric-card">
                <div class="metric-card-title">Proporsi Risiko Tinggi</div>
        """,
            unsafe_allow_html=True,
        )
        # FIX: Added non-empty label and visibility parameter
        st.metric(
            "Proporsi Risiko Tinggi", f"{pct_high:.1f}%", label_visibility="hidden"
        )
        st.markdown(
            '<div class="small-muted">target ↓ per triwulan</div></div>',
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            """
            <div class="metric-card">
                <div class="metric-card-title">Cakupan Imunisasi</div>
        """,
            unsafe_allow_html=True,
        )
        # FIX: Added non-empty label and visibility parameter
        st.metric("Cakupan Imunisasi", f"{imun_cov:.1f}%", label_visibility="hidden")
        st.markdown(
            '<div class="small-muted">indikator kunci SSGI</div></div>',
            unsafe_allow_html=True,
        )

    with col4:
        st.markdown(
            """
            <div class="metric-card">
                <div class="metric-card-title">Akses Air Layak</div>
        """,
            unsafe_allow_html=True,
        )
        # FIX: Added non-empty label and visibility parameter
        st.metric("Akses Air Layak", f"{air_cov:.1f}%", label_visibility="hidden")
        st.markdown(
            '<div class="small-muted">sektor WASH</div></div>', unsafe_allow_html=True
        )

    st.info(
        "Selamat datang di Dashboard StuntLytics. Gunakan navigasi di sebelah kiri untuk menjelajahi fitur-fitur analisis.",
        icon="👋",
    )


if __name__ == "__main__":
    main()
