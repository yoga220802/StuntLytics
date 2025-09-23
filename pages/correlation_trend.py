import streamlit as st
import pandas as pd
import plotly.express as px

from src import config, styles
from src import elastic_client as es
from src.components import sidebar


def render_page():
    # --- Setup ---
    st.subheader("Tren & Korelasi – Analitik Pendukung Kebijakan")
    filters = sidebar.render()

    # --- Pengambilan Data ---
    try:
        df_trend = es.get_monthly_trend(filters)
        df_corr_sample = es.get_numeric_sample_for_corr(filters)
    except Exception as e:
        st.error(f"Gagal mengambil data dari Elasticsearch: {e}")
        return

    # --- Halaman Utama ---
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Tren Proporsi Stunting per Bulan**")
        if not df_trend.empty:
            st.line_chart(df_trend)
        else:
            st.warning("Data tren tidak tersedia untuk filter saat ini.")

    with c2:
        st.markdown("**Faktor Paling Berpengaruh (Korelasi thd Z-Score)**")

        # FINAL: Gunakan 'ZScore TB/U' sebagai target korelasi.
        target_col = "ZScore TB/U"

        # Pengecekan data yang lebih kuat
        if (
            not df_corr_sample.empty
            and target_col in df_corr_sample.columns
            and df_corr_sample.shape[1] > 1
        ):
            try:
                corr = df_corr_sample.corr(numeric_only=True)

                # Pastikan target kolom ada di hasil korelasi (tidak di-drop karena varians nol)
                if target_col in corr:
                    corr_risk = corr[target_col].drop(target_col, errors="ignore")

                    # Pastikan ada data untuk di-plot
                    if not corr_risk.empty:
                        top_features = corr_risk.abs().nlargest(6)
                        top_corr_values = corr_risk.loc[top_features.index]

                        df_radar = pd.DataFrame(
                            {
                                "Faktor": top_corr_values.index,
                                "Korelasi Asli": top_corr_values.values,
                                "Kekuatan Korelasi": top_corr_values.abs().values,
                            }
                        )

                        fig = px.line_polar(
                            df_radar,
                            r="Kekuatan Korelasi",
                            theta="Faktor",
                            line_close=True,
                            template="plotly_dark",
                            title="Kekuatan Pengaruh Faktor terhadap Z-Score TB/U",
                            range_r=[0, 1],
                        )
                        fig.update_traces(
                            fill="toself",
                            fillcolor="rgba(239, 68, 68, 0.3)",
                            line=dict(color="rgba(239, 68, 68, 0.8)"),
                            hovertemplate="<b>%{theta}</b><br>Kekuatan: %{r:.2f}<br>Korelasi Asli: %{customdata[0]:.2f}<extra></extra>",
                            customdata=df_radar[["Korelasi Asli"]],
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        st.caption(
                            "Menunjukkan **kekuatan** pengaruh. Semakin rendah Z-Score, semakin tinggi risiko stunting."
                        )
                    else:
                        st.warning(
                            "Tidak ada cukup fitur lain untuk menghitung korelasi."
                        )
                else:
                    st.warning(
                        f"Kolom target '{target_col}' tidak dapat dihitung korelasinya (kemungkinan nilainya konstan)."
                    )
            except Exception as e:
                st.error(f"Gagal menghitung korelasi: {e}")
        else:
            st.warning(
                "Data tidak cukup untuk menghitung korelasi dengan filter saat ini."
            )

    # --- Insight Otomatis ---
    st.markdown("### Insight Otomatis (Rule-based)")
    try:
        msgs = []
        if not df_corr_sample.empty:
            df_insight = df_corr_sample.rename(
                columns={
                    "ZScore TB/U": "risk_score",
                    "BMI Pra-Hamil": "bmi_pra_hamil",
                    "Hb (g/dL)": "hb_g_dl",
                }
            )
            for key, rule in config.INSIGHT_RULES.items():
                if rule["when"](df_insight):
                    msgs.append(rule["msg"])
        if msgs:
            st.success("\n".join([f"• {m}" for m in msgs]))
        else:
            st.info(
                "Tidak ada insight khusus dari rule sederhana untuk data yang ditampilkan."
            )
    except Exception as e:
        st.error(f"Gagal menjalankan beberapa rule insight: {e}")


# --- Main Execution ---
if "page_config_set" not in st.session_state:
    st.set_page_config(layout="wide")
    st.session_state.page_config_set = True
styles.load_css()
render_page()
