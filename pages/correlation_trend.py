import streamlit as st
import pandas as pd
import plotly.express as px

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
        st.markdown("**Faktor Paling Berpengaruh (Kekuatan Korelasi)**")

        num_cols = [
            "bblr",
            "asi_eksklusif",
            "imunisasi_lengkap",
            "akses_air_layak",
            "jamban_sehat",
            "usia_anak_bulan",
            "tanggungan",
            "risk_score",
        ]
        valid_cols = [col for col in num_cols if col in df_filtered.columns]

        if len(valid_cols) > 1:
            corr = df_filtered[valid_cols].corr(numeric_only=True)

            corr_risk = corr["risk_score"].drop("risk_score")

            top_features = corr_risk.abs().nlargest(6)
            top_corr_values = corr_risk.loc[top_features.index]

            # Siapkan data untuk radar chart
            df_radar = pd.DataFrame(
                {
                    "Faktor": top_corr_values.index,
                    "Korelasi Asli": top_corr_values.values,
                    "Kekuatan Korelasi": top_corr_values.abs().values,  # BARU: Pakai nilai absolut untuk radius plot
                }
            )

            # Buat Radar Chart dengan range 0-1
            fig = px.line_polar(
                df_radar,
                r="Kekuatan Korelasi",  # Gunakan kolom nilai absolut
                theta="Faktor",
                line_close=True,
                template="plotly_dark",
                title="Kekuatan Pengaruh Faktor terhadap Risiko",
                range_r=[0, 1],  # BARU: Paksa skala chart dari 0 sampai 1
            )

            # Styling dan custom hover data
            fig.update_traces(
                fill="toself",
                fillcolor="rgba(239, 68, 68, 0.3)",
                line=dict(color="rgba(239, 68, 68, 0.8)"),
                # BARU: Custom hover template untuk menampilkan nilai asli
                hovertemplate="<b>%{theta}</b><br>Kekuatan: %{r:.2f}<br>Korelasi Asli: %{customdata[0]:.2f}<extra></extra>",
                customdata=df_radar[["Korelasi Asli"]],
            )

            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                "Menunjukkan **kekuatan** pengaruh (nilai absolut korelasi) dari 0 (pusat) hingga 1 (tepi). Arahkan kursor untuk melihat nilai korelasi asli (positif/negatif)."
            )

        else:
            st.warning("Data tidak cukup untuk menampilkan grafik korelasi.")

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
