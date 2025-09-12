import streamlit as st
import json
from datetime import datetime
from src import data_loader, styles
from src.components import sidebar

def render_page():
    # --- Load data and apply filters ---
    df_all = data_loader.load_data()
    filters = sidebar.render_sidebar(df_all)
    df_filtered = sidebar.apply_filters(df_all, filters)

    st.subheader("Ekspor Laporan & Data")
    st.caption("Unduh data hasil filter & ringkasan KPI untuk keperluan rapat.")

    # Tombol Unduh CSV
    csv_bytes = df_filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Unduh Data Terfilter (CSV)",
        data=csv_bytes,
        file_name="stuntingguard_filtered.csv",
        mime="text/csv",
    )

    # Buat dan tampilkan ringkasan JSON
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    report = {
        "generated_at": now,
        "filters": {
            "date_range": [str(filters["start_date"]), str(filters["end_date"])],
            "kabupaten": filters["selected_kabupaten"],
            "kecamatan": filters["selected_kecamatan"],
            "risks": filters["selected_risk"],
        },
        "kpi": {
            "total_observasi": int(len(df_filtered)),
            "pct_high_risk": float((df_filtered["risk_label"].eq("Tinggi").mean()*100) if not df_filtered.empty else 0),
            "immunization_coverage": float(df_filtered["imunisasi_lengkap"].mean()*100 if not df_filtered.empty else 0),
            "water_access": float(df_filtered["akses_air_layak"].mean()*100 if not df_filtered.empty else 0),
        }
    }
    rep_json = json.dumps(report, ensure_ascii=False, indent=2)
    st.download_button(
        label="Unduh Ringkasan (JSON)",
        data=rep_json.encode("utf-8"),
        file_name="stuntingguard_report.json",
        mime="application/json",
    )
    
    st.info("Untuk ekspor PDF terformat, diperlukan integrasi dengan service pelaporan eksternal.")

# --- Main Execution ---
st.set_page_config(layout="wide")
styles.load_css()
render_page()
