import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os

from src import data_loader, styles
from src.components import sidebar

# Path ke file GeoJSON yang sudah lo punya
GEOJSON_PATH = "geojson/jawa-barat.geojson"


def render_page():
    # --- Load data and apply filters ---
    df_all = data_loader.load_data()
    filters = sidebar.render_sidebar(df_all)
    df_filtered = sidebar.apply_filters(df_all, filters)

    st.subheader("Peta Risiko – Choropleth per Kecamatan")
    st.caption(
        "Warna pada peta menunjukkan rata-rata skor risiko stunting per kecamatan. Semakin gelap warnanya, semakin tinggi rata-rata risikonya."
    )

    # Cek ketersediaan file GeoJSON
    if not os.path.exists(GEOJSON_PATH):
        st.error(
            f"File peta GeoJSON tidak ditemukan di '{GEOJSON_PATH}'. Pastikan file sudah diletakkan di folder yang benar."
        )
        return

    if df_filtered.empty:
        st.info("Tidak ada data untuk ditampilkan dengan filter saat ini.")
        return

    # --- Agregasi data per KECAMATAN ---
    df_agg = df_filtered.groupby("kecamatan")["risk_score"].mean().reset_index()

    # --- NORMALISASI NAMA KECAMATAN (PENTING!) ---
    # Samakan format nama kecamatan antara DataFrame dan GeoJSON
    # Contoh: "Kec. Cibatu" -> "CIBATU"
    df_agg["kecamatan_key"] = df_agg["kecamatan"].str.upper().str.replace("KEC. ", "")

    # --- Load file GeoJSON ---
    with open(GEOJSON_PATH) as f:
        geojson_jabar = json.load(f)

    # --- Membuat Peta Choropleth ---
    fig = px.choropleth_mapbox(
        df_agg,
        geojson=geojson_jabar,
        locations="kecamatan_key",  # Kolom kunci di dataframe
        featureidkey="properties.KECAMATAN",  # Path ke kunci nama di GeoJSON (sesuai file lo)
        color="risk_score",  # Kolom sebagai dasar pewarnaan
        color_continuous_scale="Reds",
        range_color=(0, df_agg["risk_score"].max()),
        mapbox_style="carto-positron",  # Style peta dasar yang bersih
        zoom=7.5,
        center={"lat": -6.9175, "lon": 107.6191},  # Center di Jawa Barat
        opacity=0.7,
        labels={"risk_score": "Rata-rata Skor Risiko"},
    )
    # Atur layout agar peta memenuhi kontainer
    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0}
        # Baris mapbox_accesstoken dihapus dari sini untuk menghilangkan error
    )

    st.plotly_chart(fig, use_container_width=True)
    st.info(
        "Peta ini bersifat interaktif. Anda dapat zoom, geser, dan mengarahkan kursor ke sebuah kecamatan untuk melihat detail skor risikonya.",
        icon="ℹ️",
    )

    # --- Tabel ringkasan per KABUPATEN (tetap dipertahankan untuk overview) ---
    st.markdown("### Ringkasan Proporsi Risiko per Kabupaten/Kota")
    g = (
        df_filtered.groupby("kabupaten")["risk_label"]
        .value_counts(normalize=True)
        .mul(100)
        .rename("persen")
        .reset_index()
    )
    g_pivot = (
        g.pivot(index="kabupaten", columns="risk_label", values="persen")
        .fillna(0)
        .sort_values("Tinggi", ascending=False)
    )
    st.dataframe(
        g_pivot.style.format("{:.1f}%").bar(color="#fca5a5", subset=["Tinggi"]),
        width="stretch",
    )


# --- Main Execution ---
st.set_page_config(layout="wide", page_title="Peta Risiko Stunting")
styles.load_css()
render_page()
