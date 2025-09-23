import streamlit as st
import pandas as pd
import plotly.express as px

from src import styles
from src import elastic_client as es
from src.components import sidebar


def render_page():
    # --- Sidebar & Filter Utama ---
    st.subheader("Explorer Data – Filter Lanjutan & Pencarian Cepat")
    main_filters = sidebar.render()

    # --- Filter Lanjutan (khusus halaman ini) ---
    st.markdown("##### Filter Lanjutan")
    c1, c2, c3 = st.columns(3)
    with c1:
        try:
            # Ambil opsi dari data live, sediakan fallback jika gagal
            edu_opts = es.get_unique_field_values(main_filters, "Pendidikan Ibu")
            if not edu_opts:
                edu_opts = ["SD", "SMP", "SMA", "D3", "S1+"]
            edu = st.multiselect("Pendidikan Ibu", edu_opts, [])
        except Exception:
            edu = st.multiselect(
                "Pendidikan Ibu", ["SD", "SMP", "SMA", "D3", "S1+"], []
            )  # Fallback

    with c2:
        asi = st.select_slider(
            "ASI Eksklusif", options=["Semua", "Ya", "Tidak"], value="Semua"
        )
    with c3:
        air = st.select_slider(
            "Akses Air Layak", options=["Semua", "Ada", "Tidak"], value="Semua"
        )

    advanced_filters = {
        "pendidikan_ibu": edu,
        "asi_eksklusif": asi,
        "akses_air": air,
    }

    # --- Pengambilan Data & Tampilan ---
    try:
        df_explorer = es.get_explorer_data(main_filters, advanced_filters, size=1000)

        st.caption(
            f"Menampilkan hingga 1.000 data teratas yang paling berisiko (diurutkan berdasarkan Z-Score). Gunakan ikon 🔍 di kanan atas tabel untuk mencari."
        )
        if not df_explorer.empty:
            # Buat ID unik untuk setiap baris agar bisa diidentifikasi di chart
            df_explorer["id_baris"] = range(len(df_explorer))

            st.dataframe(
                df_explorer.drop(columns=["id_baris"]),
                use_container_width=True,
                height=420,
            )

            # --- Chart Berjenjang ---
            st.markdown("---")

            if main_filters.get("kecamatan"):
                # Level 3: Filter kecamatan aktif, tampilkan top 5 Z-Score
                st.markdown(
                    "##### Top 5 Keluarga Paling Berisiko (Berdasarkan Z-Score)"
                )
                df_chart_data = df_explorer.nsmallest(5, "Z-Score").copy()

                # Buat label yang lebih informatif untuk chart
                df_chart_data["Identifier"] = (
                    "ID Baris: "
                    + df_chart_data["id_baris"].astype(str)
                    + " (Z-Score: "
                    + df_chart_data["Z-Score"].round(2).astype(str)
                    + ")"
                )

                fig = px.bar(
                    df_chart_data.sort_values(
                        "Z-Score", ascending=False
                    ),  # Ascending=False agar bar terendah di atas
                    x="Z-Score",
                    y="Identifier",
                    orientation="h",
                    title=f"5 Kasus Z-Score Terendah di Kec. {main_filters['kecamatan'][0]}",
                    labels={
                        "Z-Score": "Z-Score (semakin rendah, semakin berisiko)",
                        "Identifier": "Data Individual",
                    },
                    text="Z-Score",
                )
                fig.update_traces(
                    texttemplate="%{text:.2f}",
                    textposition="outside",
                    marker_color="#ef4444",
                )
                fig.update_layout(yaxis={"categoryorder": "total ascending"})

            else:
                # Level 1 & 2: Ambil data agregat (kabupaten atau kecamatan)
                df_agg = es.get_top_counts_for_explorer_chart(
                    main_filters, advanced_filters
                )

                if not df_agg.empty:
                    y_col = df_agg.columns[
                        0
                    ]  # Kolom pertama adalah 'Kabupaten/Kota' atau 'Kecamatan'

                    if main_filters.get("wilayah"):
                        title = f"Top 5 Kecamatan di {main_filters['wilayah'][0]} (Jumlah Data)"
                    else:
                        title = "Top 5 Kabupaten/Kota (Jumlah Data)"

                    st.markdown(f"##### {title}")
                    fig = px.bar(
                        df_agg.sort_values(
                            "Jumlah Data", ascending=True
                        ),  # Ascending=True agar bar terbesar di atas
                        x="Jumlah Data",
                        y=y_col,
                        orientation="h",
                        title=title,
                        labels={"Jumlah Data": "Jumlah Data Tercatat", y_col: y_col},
                        text="Jumlah Data",
                    )
                    fig.update_traces(
                        texttemplate="%{text}",
                        textposition="outside",
                        marker_color="#3b82f6",
                    )
                    fig.update_layout(yaxis={"categoryorder": "total descending"})
                else:
                    fig = None

            # Tampilkan chart jika fig sudah didefinisikan
            if "fig" in locals() and fig is not None:
                st.plotly_chart(fig, use_container_width=True)

        else:
            st.info("Tidak ada data yang cocok dengan kriteria filter yang dipilih.")

    except Exception as e:
        st.error(f"Gagal memproses data: {e}")
        st.exception(e)


# --- Main Execution ---
if "page_config_set" not in st.session_state:
    st.set_page_config(layout="wide")
    st.session_state.page_config_set = True

styles.load_css()
render_page()
