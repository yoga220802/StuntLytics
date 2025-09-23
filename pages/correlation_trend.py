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
        st.code(e)  # Tampilkan detail error
        return

    # --- MODE DEBUG PERMANEN ---
    with st.expander("🕵️‍♂️ Buka Panel Debug 🕵️‍♂️", expanded=True):
        st.warning(
            "Mode Debug Aktif. Panel ini akan menunjukkan data mentah yang ditarik dari Elasticsearch."
        )

        st.markdown("---")
        st.markdown("#### Data untuk Grafik Tren")
        st.dataframe(df_trend)

        st.markdown("---")
        st.markdown("#### Data untuk Grafik Korelasi")
        st.dataframe(df_corr_sample)

        st.markdown("**Kolom yang tersedia untuk korelasi:**")
        st.write(df_corr_sample.columns.tolist())

        st.markdown("**Struktur DataFrame Korelasi (.info()):**")
        if not df_corr_sample.empty:
            buffer = pd.io.common.StringIO()
            df_corr_sample.info(buf=buffer)
            st.text(buffer.getvalue())
        else:
            st.error("DataFrame untuk korelasi kosong.")

    # --- Halaman Utama ---
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Tren Proporsi Stunting per Bulan**")
        if not df_trend.empty:
            st.line_chart(df_trend)
        else:
            st.warning("Data tren tidak tersedia.")

    with c2:
        st.markdown("**Faktor Paling Berpengaruh (Korelasi thd Z-Score)**")

        # DIGANTI: Gunakan 'ZScore TB/U' sebagai target korelasi karena ini pasti ada dan valid.
        target_col = "ZScore TB/U"

        if (
            not df_corr_sample.empty
            and target_col in df_corr_sample.columns
            and len(df_corr_sample.columns) > 1
        ):
            try:
                corr = df_corr_sample.corr(numeric_only=True)

                if target_col in corr:
                    # Korelasi negatif dengan Z-Score berarti berhubungan positif dengan stunting
                    corr_risk = corr[target_col].drop(target_col, errors="ignore")
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
                        f"Kolom target '{target_col}' tidak ditemukan setelah korelasi."
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
            # Sesuaikan nama kolom untuk rules
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
