import streamlit as st
import pandas as pd
from src.utils import get_kabupaten_list, get_kecamatan_list
from src.config import DEFAULT_PREDICT_API, DEFAULT_INSIGHT_API

def render_sidebar(df: pd.DataFrame) -> dict:
    st.sidebar.title("🎛️ Kontrol & Filter")
    st.sidebar.markdown("**Sasaran:** Pemerintah Daerah (Pemda)")
    st.sidebar.caption("Filter memengaruhi seluruh tampilan halaman.")

    # Filter Rentang Tanggal
    min_d, max_d = df["tanggal"].min().date(), df["tanggal"].max().date()
    date_range = st.sidebar.date_input(
        "Rentang Tanggal", 
        value=(min_d, max_d), 
        min_value=min_d, 
        max_value=max_d
    )

    # Filter Wilayah (Kabupaten & Kecamatan)
    kabupaten_pilihan = st.sidebar.selectbox(
        "Kabupaten/Kota", 
        options=get_kabupaten_list(df)
    )
    kecamatan_pilihan = st.sidebar.selectbox(
        "Kecamatan", 
        options=get_kecamatan_list(df, kabupaten_pilihan)
    )

    # Filter Kategori Risiko
    risk_filter = st.sidebar.multiselect(
        "Kategori Risiko", 
        options=["Rendah", "Sedang", "Tinggi"], 
        default=["Rendah", "Sedang", "Tinggi"]
    )

    # Expander untuk Konfigurasi API (menggunakan session_state)
    with st.sidebar.expander("Konfigurasi API"):
        st.session_state.setdefault("predict_api", DEFAULT_PREDICT_API)
        st.session_state.setdefault("insight_api", DEFAULT_INSIGHT_API)
        
        st.session_state["predict_api"] = st.text_input(
            "Prediction API", st.session_state["predict_api"]
        )    
        st.session_state["insight_api"] = st.text_input(
            "Insight API", st.session_state["insight_api"]
        )

    # Pastikan date_range memiliki 2 elemen sebelum di-return
    start_date, end_date = date_range if len(date_range) == 2 else (min_d, max_d)

    return {
        "start_date": start_date,
        "end_date": end_date,
        "selected_kabupaten": kabupaten_pilihan,
        "selected_kecamatan": kecamatan_pilihan,
        "selected_risk": risk_filter,
    }

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
