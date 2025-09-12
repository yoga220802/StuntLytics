import streamlit as st
import pandas as pd

from src import data_loader, styles
from src.components import sidebar

def render_page():
    # --- Load data and apply filters ---
    df_all = data_loader.load_data()
    filters = sidebar.render_sidebar(df_all)
    df_filtered = sidebar.apply_filters(df_all, filters)

    # --- Page Content ---
    st.subheader("Explorer Data – Filter Lanjutan & Pencarian Cepat")
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        edu = st.multiselect("Pendidikan Ibu", ["SD","SMP","SMA","D3","S1+"], [])
    with c2:
        asi = st.select_slider("ASI Eksklusif", options=["Semua","Ya","Tidak"], value="Semua")
    with c3:
        air = st.select_slider("Akses Air Layak", options=["Semua","Ada","Tidak"], value="Semua")
    with c4:
        jam = st.select_slider("Jamban Sehat", options=["Semua","Ada","Tidak"], value="Semua")

    # filter lanjutan
    dfe = df_filtered.copy()
    if edu: dfe = dfe[dfe["pendidikan_ibu"].isin(edu)]
    if asi != "Semua": dfe = dfe[dfe["asi_eksklusif"] == (1 if asi=="Ya" else 0)]
    if air != "Semua": dfe = dfe[dfe["akses_air_layak"] == (1 if air=="Ada" else 0)]
    if jam != "Semua": dfe = dfe[dfe["jamban_sehat"] == (1 if jam=="Ada" else 0)]

    st.caption("Tabel dapat di-scroll & difilter. Gunakan ikon search di kanan atas tabel.")
    st.dataframe(
        dfe[["tanggal","kabupaten","kecamatan","desa","risk_label","risk_score","usia_anak_bulan","bblr","asi_eksklusif","mp_asi_tepatsesuai","imunisasi_lengkap","pendidikan_ibu","akses_air_layak","jamban_sehat","pengeluaran_bulan","tanggungan"]]
        .sort_values("risk_score", ascending=False),
        use_container_width=True,
        height=420,
    )

# --- Main Execution ---
st.set_page_config(layout="wide")
styles.load_css()
render_page()
