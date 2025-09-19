import streamlit as st
import pandas as pd
from src.utils import get_kabupaten_list, get_kecamatan_list
from src.config import DEFAULT_PREDICT_API, DEFAULT_INSIGHT_API

def _unique_sorted(values):
    return sorted(list({v for v in values if v and v.strip()}))

def render_sidebar(df: pd.DataFrame) -> dict:
    """Sidebar untuk dashboard data utama (mengembalikan dict filter)."""
    st.sidebar.header("Filter Data")
    # Tanggal
    if "tanggal" in df.columns:
        min_date = pd.to_datetime(df["tanggal"]).min().date()
        max_date = pd.to_datetime(df["tanggal"]).max().date()
    else:
        today = pd.Timestamp.today().date()
        min_date = max_date = today
    start_date, end_date = st.sidebar.date_input(
        "Rentang Tanggal",
        (min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    # Risiko
    risk_options = sorted(df["risk_label"].dropna().unique()) if "risk_label" in df.columns else []
    selected_risk = st.sidebar.multiselect("Risk Level", risk_options, default=risk_options)

    # Kabupaten
    kab_options = ["(Semua)"] + sorted(df["kabupaten"].dropna().unique()) if "kabupaten" in df.columns else ["(Semua)"]
    selected_kabupaten = st.sidebar.selectbox("Kabupaten", kab_options, index=0)

    # Kecamatan (tergantung kabupaten)
    if selected_kabupaten != "(Semua)" and "kecamatan" in df.columns:
        kec_pool = df.loc[df["kabupaten"] == selected_kabupaten, "kecamatan"].dropna().unique()
    else:
        kec_pool = df["kecamatan"].dropna().unique() if "kecamatan" in df.columns else []
    kec_options = ["(Semua)"] + sorted(kec_pool)
    selected_kecamatan = st.sidebar.selectbox("Kecamatan", kec_options, index=0)

    return {
        "start_date": start_date,
        "end_date": end_date,
        "selected_risk": selected_risk,
        "selected_kabupaten": selected_kabupaten,
        "selected_kecamatan": selected_kecamatan,
    }

def render_geo_sidebar(geojson):
    """Sidebar khusus halaman peta (geojson)."""
    st.sidebar.header("Filter Wilayah (Peta)")
    features = geojson.get("features", [])
    kab_list = _unique_sorted(f["properties"].get("KABKOT", "") for f in features)
    kab_options = ["Semua"] + kab_list
    kabupaten = st.sidebar.selectbox("Kabupaten / Kota", kab_options, index=0)

    kecamatan = "Semua"
    if kabupaten != "Semua":
        kec_list = _unique_sorted(
            f["properties"].get("KECAMATAN", "")
            for f in features
            if f["properties"].get("KABKOT", "").upper() == kabupaten.upper()
        )
        kec_options = ["Semua"] + kec_list
        kecamatan = st.sidebar.selectbox("Kecamatan", kec_options, index=0)
    else:
        st.sidebar.markdown("<small>Pilih kabupaten/kota untuk mengaktifkan filter kecamatan.</small>", unsafe_allow_html=True)
    return kabupaten, kecamatan

def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """
    Menerapkan filter ke DataFrame berdasarkan dictionary filter.

    Args:
        df (pd.DataFrame): DataFrame asli.
        filters (dict): Dictionary dari output render_sidebar.

    Returns:
        pd.DataFrame: DataFrame yang sudah difilter.
    """
    df_filtered = df.copy()
    
    # Apply date filter
    df_filtered = df_filtered[
        df_filtered["tanggal"].between(
            pd.to_datetime(filters["start_date"]), 
            pd.to_datetime(filters["end_date"])
        )
    ]
    
    # Apply risk filter
    if filters["selected_risk"]:
        df_filtered = df_filtered[df_filtered["risk_label"].isin(filters["selected_risk"])]

    # Apply kabupaten filter
    if filters["selected_kabupaten"] != "(Semua)":
        df_filtered = df_filtered[df_filtered["kabupaten"] == filters["selected_kabupaten"]]

    # Apply kecamatan filter
    if filters["selected_kecamatan"] != "(Semua)":
        df_filtered = df_filtered[df_filtered["kecamatan"] == filters["selected_kecamatan"]]
        
    return df_filtered
