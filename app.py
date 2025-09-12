import streamlit as st
import pandas as pd

# Import modul-modul yang sudah kita refactor
from src import config, styles, data_loader
from src.components import sidebar

def main():
    # --- 1. Konfigurasi Halaman ---
    st.set_page_config(
        page_title=config.APP_TITLE,
        page_icon="🧒🏽",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    styles.load_css()

    # --- 2. Memuat Data ---
    df_all = data_loader.load_data()

    # --- 3. Merender Sidebar & Mendapatkan Filter ---
    filters = sidebar.render_sidebar(df_all)
    
    # --- 4. Menerapkan Filter ---
    df_filtered = sidebar.apply_filters(df_all, filters)

    # --- 5. Menampilkan Konten Halaman Utama ---
    
    # Header
    st.markdown(f'<div class="app-header">{config.APP_TITLE}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="app-subtitle">{config.APP_DESCRIPTION}</div>', unsafe_allow_html=True)

    # Metrik / KPI Utama
    st.markdown("### Ringkasan Eksekutif")
    col1, col2, col3, col4 = st.columns(4)
    
    # Kalkulasi metrik
    total_observasi = len(df_filtered)
    pct_high = (df_filtered["risk_label"].eq("Tinggi").mean() * 100) if total_observasi > 0 else 0
    imun_cov = df_filtered["imunisasi_lengkap"].mean() * 100 if total_observasi > 0 else 0
    air_cov = df_filtered["akses_air_layak"].mean() * 100 if total_observasi > 0 else 0

    with col1:
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        st.metric("Total Observasi", f"{total_observasi:,}")
        st.markdown("<span class='small-muted'>setelah filter diterapkan</span>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with col2:
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        st.metric("Proporsi Risiko Tinggi", f"{pct_high:.1f}%")
        st.markdown("<span class='small-muted'>target ↓ per triwulan</span>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with col3:
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        st.metric("Cakupan Imunisasi", f"{imun_cov:.1f}%")
        st.markdown("<span class='small-muted'>indikator kunci SSGI</span>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with col4:
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        st.metric("Akses Air Layak", f"{air_cov:.1f}%")
        st.markdown("<span class='small-muted'>sektor WASH</span>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    st.info("Selamat datang di Dashboard StuntingGuard. Gunakan navigasi di sebelah kiri untuk menjelajahi fitur-fitur analisis.", icon="👋")

    # Footer
    st.markdown(
        """
        <div class="footer">\n
        <b>Catatan:</b> Data pada demo ini dapat berupa dummy data. Integrasi penuh mendukung koneksi ke database dan API.
        </div>
        """,
        unsafe_allow_html=True,
    )

if __name__ == "__main__":
    main()
