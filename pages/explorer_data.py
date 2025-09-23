import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

from src import styles
from src import elastic_client as es
from src.components import sidebar


def render_page():
    # --- Sidebar & Filter Utama ---
    st.subheader("Explorer Data – Filter, Visualisasi & Ekspor")
    main_filters = sidebar.render()

    # --- Filter Lanjutan (khusus halaman ini) ---
    st.markdown("##### Filter Lanjutan")
    c1, c2, c3 = st.columns(3)
    with c1:
        try:
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

    advanced_filters = {"pendidikan_ibu": edu, "asi_eksklusif": asi, "akses_air": air}

    # --- Pengambilan Data & Tampilan Tabel ---
    try:
        df_explorer = es.get_explorer_data(main_filters, advanced_filters, size=1000)

        st.caption(
            f"Menampilkan hingga 1.000 data teratas yang paling berisiko. Gunakan fitur ekspor di bawah untuk mengunduh data lebih lengkap."
        )
        if not df_explorer.empty:
            df_display = df_explorer.copy()
            df_display["id_baris"] = range(len(df_display))
            st.dataframe(
                df_display.drop(columns=["id_baris"]),
                use_container_width=True,
                height=420,
            )

            # --- Chart Berjenjang ---
            st.markdown("---")
            # (Logika chart berjenjang dari sebelumnya, tidak berubah)
            if main_filters.get("kecamatan"):
                st.markdown(
                    "##### Top 5 Keluarga Paling Berisiko (Berdasarkan Z-Score)"
                )
                df_chart_data = df_display.nsmallest(5, "Z-Score").copy()
                df_chart_data["Identifier"] = (
                    "ID Baris: "
                    + df_chart_data["id_baris"].astype(str)
                    + " (Z-Score: "
                    + df_chart_data["Z-Score"].round(2).astype(str)
                    + ")"
                )
                fig = px.bar(
                    df_chart_data.sort_values("Z-Score", ascending=False),
                    x="Z-Score",
                    y="Identifier",
                    orientation="h",
                    title=f"5 Kasus Z-Score Terendah di Kec. {main_filters['kecamatan'][0]}",
                    labels={"Z-Score": "Z-Score", "Identifier": "Data Individual"},
                    text="Z-Score",
                )
                fig.update_traces(
                    texttemplate="%{text:.2f}",
                    textposition="outside",
                    marker_color="#ef4444",
                )
                fig.update_layout(yaxis={"categoryorder": "total ascending"})
            else:
                df_agg = es.get_top_counts_for_explorer_chart(
                    main_filters, advanced_filters
                )
                if not df_agg.empty:
                    y_col = df_agg.columns[0]
                    title = f"Top 5 {y_col} (Jumlah Data)"
                    if main_filters.get("wilayah"):
                        title = f"Top 5 Kecamatan di {main_filters['wilayah'][0]} (Jumlah Data)"
                    st.markdown(f"##### {title}")
                    fig = px.bar(
                        df_agg.sort_values("Jumlah Data", ascending=True),
                        x="Jumlah Data",
                        y=y_col,
                        orientation="h",
                        title=title,
                        labels={"Jumlah Data": "Jumlah Data", y_col: y_col},
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
            if "fig" in locals() and fig is not None:
                st.plotly_chart(fig, use_container_width=True)

            # --- ZONA EKSPOR BARU ---
            st.markdown("---")
            with st.expander("📥 Buka Panel Ekspor Data"):
                st.markdown(
                    "Unduh data yang Anda lihat (sesuai filter di atas) dalam format CSV atau JSON."
                )

                # Menggabungkan semua filter untuk fungsi ekspor
                all_filters = {**main_filters, **advanced_filters}

                export_col1, export_col2 = st.columns(2)
                with export_col1:
                    if st.button("Siapkan File CSV (hingga 5.000 baris)"):
                        with st.spinner("Mempersiapkan file CSV..."):
                            df_export = es.get_explorer_data_for_export(
                                main_filters, advanced_filters, size=5000
                            )
                            st.session_state.export_df = (
                                df_export  # Simpan di session state
                            )
                            st.session_state.csv_ready = True
                            st.success("File CSV siap!")

                    if st.session_state.get("csv_ready"):
                        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                        csv_bytes = st.session_state.export_df.to_csv(
                            index=False
                        ).encode("utf-8")
                        st.download_button(
                            "⬇️ Unduh CSV",
                            csv_bytes,
                            f"stuntlytics_export_{now_str}.csv",
                            "text/csv",
                        )

                with export_col2:
                    if st.button("Siapkan File JSON (hingga 5.000 baris)"):
                        with st.spinner("Mempersiapkan file JSON..."):
                            # Kita bisa pakai data yang sama jika sudah di-fetch untuk CSV
                            if "export_df" not in st.session_state:
                                df_export = es.get_explorer_data_for_export(
                                    main_filters, advanced_filters, size=5000
                                )
                                st.session_state.export_df = df_export
                            st.session_state.json_ready = True
                            st.success("File JSON siap!")

                    if st.session_state.get("json_ready"):
                        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                        json_string = st.session_state.export_df.to_json(
                            orient="records", indent=4, force_ascii=False
                        )
                        st.download_button(
                            "⬇️ Unduh JSON",
                            json_string,
                            f"stuntlytics_export_{now_str}.json",
                            "application/json",
                        )

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
