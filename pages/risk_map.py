import streamlit as st
import pandas as pd

# Import modul-modul custom
from src import data_loader, styles
from src.components import sidebar

try:
    import pydeck as pdk
except ImportError:
    pdk = None
    
def render_page():
    # --- Load data and apply filters ---
    df_all = data_loader.load_data()
    filters = sidebar.render_sidebar(df_all)
    df_filtered = sidebar.apply_filters(df_all, filters)

    # --- Page Content ---
    st.subheader("Peta Risiko – Heatmap & Titik Keluarga")

    if df_filtered.empty:
        st.info("Tidak ada data untuk filter saat ini.")
        return

    # Visualisasi Peta
    if pdk:
        # Map color by risk category
        color_map = {"Rendah": [34, 197, 94], "Sedang": [234, 179, 8], "Tinggi": [239, 68, 68]}
        df_plot = df_filtered[["lat", "lon", "risk_label"]].dropna().copy()
        df_plot["color"] = df_plot["risk_label"].map(color_map)

        # Definisikan layers untuk Pydeck
        hex_layer = pdk.Layer(
            "HexagonLayer", data=df_plot, get_position='[lon, lat]', radius=900,
            elevation_scale=30, elevation_range=[0, 6000], pickable=True, extruded=True,
        )
        scatter_layer = pdk.Layer(
            "ScatterplotLayer", data=df_plot, get_position='[lon, lat]', get_radius=140,
            get_fill_color='color', pickable=True,
        )
        
        # Atur view state peta
        view_state = pdk.ViewState(
            latitude=float(df_plot["lat"].median()), longitude=float(df_plot["lon"].median()), zoom=7
        )
        
        # Render peta
        r = pdk.Deck(layers=[hex_layer, scatter_layer], initial_view_state=view_state, tooltip={"text": "{risk_label}"})
        st.pydeck_chart(r, use_container_width=True)
    else:
        st.warning("Library `pydeck` tidak terinstall. Menampilkan peta standar. Install dengan `pip install pydeck`.")
        st.map(df_filtered.rename(columns={"lat":"latitude", "lon":"longitude"})[["latitude","longitude"]])

    # Tabel ringkasan per wilayah
    st.markdown("### Ringkasan per Kabupaten/Kota")
    g = df_filtered.groupby("kabupaten")["risk_label"].value_counts(normalize=True).mul(100).rename("persen").reset_index()
    g_pivot = g.pivot(index="kabupaten", columns="risk_label", values="persen").fillna(0).sort_values("Tinggi", ascending=False)
    st.dataframe(
        g_pivot.style.format("{:.1f}").bar(color="#fca5a5", subset=["Tinggi"]),
        use_container_width=True
    )

# --- Main Execution ---
st.set_page_config(layout="wide")
styles.load_css()
render_page()
