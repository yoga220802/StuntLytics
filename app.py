import streamlit as st
import pandas as pd
import plotly.graph_objects as go  # Import plotly for the donut chart

from src import config, styles, data_loader
from src.components import sidebar


def main():
    st.set_page_config(
        page_title=config.APP_TITLE,
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    styles.load_css()

    df_all = data_loader.load_data()
    filters = sidebar.render_sidebar(df_all)
    df_filtered = sidebar.apply_filters(df_all, filters)

    # Header
    st.markdown(
        f'<div class="app-header">{config.APP_TITLE}</div>', unsafe_allow_html=True
    )
    st.markdown(
        f'<div class="app-subtitle">{config.APP_DESCRIPTION}</div>',
        unsafe_allow_html=True,
    )

    # Metrik / KPI Utama - dengan struktur HTML baru
    col1, col2, col3, col4 = st.columns(4)

    total_observasi = len(df_filtered)
    total_bayi_lahir = df_filtered["total_bayi_lahir"].sum()
    total_bayi_stunting = df_filtered["total_bayi_stunting"].sum()
    pct_high = (
        (df_filtered["risk_label"].eq("Tinggi").mean() * 100)
        if total_observasi > 0
        else 0
    )
    imun_cov = (
        df_filtered["imunisasi_lengkap"].mean() * 100 if total_observasi > 0 else 0
    )
    air_cov = df_filtered["akses_air_layak"].mean() * 100 if total_observasi > 0 else 0
    total_nakes = df_filtered["jumlah_nakes"].sum()  # Calculate total healthcare workers

    with col1:
        # Metric for Total Bayi Stunting / Total Bayi Lahir
        st.markdown(
            """
            <div class="metric-card">
                <div class="metric-card-title">Total Bayi Stunting / Total Bayi Lahir</div>
        """,
            unsafe_allow_html=True,
        )
        st.metric(
            "Total Bayi Stunting / Total Bayi Lahir",
            f"{total_bayi_stunting:,} / {total_bayi_lahir:,}",
            label_visibility="hidden",
        )
        st.markdown(
            '<div class="small-muted">setelah filter</div></div>',
            unsafe_allow_html=True,
        )

        # Donut Chart for Stunting Proportion
        stunting_data = {
            "Bayi Stunting": total_bayi_stunting,
            "Bayi Tidak Stunting": total_bayi_lahir - total_bayi_stunting,
        }
        fig_stunting = go.Figure(
            data=[
                go.Pie(
                    labels=list(stunting_data.keys()),
                    values=list(stunting_data.values()),
                    hole=0.5,  # Creates the donut hole
                    textinfo="percent",  # Show only percentages
                )
            ]
        )
        fig_stunting.update_layout(
            showlegend=False,
            margin=dict(t=0, b=0, l=0, r=0),
            height=150,  # Smaller height for the chart
            paper_bgcolor="rgba(0,0,0,0)",  # Transparent background
            plot_bgcolor="rgba(0,0,0,0)",  # Transparent plot area
        )
        st.plotly_chart(fig_stunting, use_container_width=True, config={"displayModeBar": False})

    with col2:
        st.markdown(
            """
            <div class="metric-card">
                <div class="metric-card-title">Jumlah Nakes</div>
        """,
            unsafe_allow_html=True,
        )
        st.metric(
            "Jumlah Nakes", f"{total_nakes:,}", label_visibility="hidden"
        )
        st.markdown(
            '<div class="small-muted">per wilayah setelah filter</div></div>',
            unsafe_allow_html=True,
        )

        # Determine grouping level based on filter
        if filters["selected_kecamatan"] == "(Semua)":
            # Group by kecamatan if only kabupaten is selected
            nakes_grouped = (
                df_filtered.groupby("kecamatan")["jumlah_nakes"]
                .sum()
                .sort_values(ascending=False)
            )
            title = "Jumlah Nakes per Kecamatan"
            yaxis_title = "Kecamatan"
        else:
            # Group by kabupaten if kecamatan is also selected
            nakes_grouped = (
                df_filtered.groupby("kabupaten")["jumlah_nakes"]
                .sum()
                .sort_values(ascending=False)
            )
            title = "Jumlah Nakes per Kabupaten"
            yaxis_title = "Kabupaten"

        # Bar Chart for Jumlah Nakes
        fig_nakes = go.Figure(
            data=[
                go.Bar(
                    x=nakes_grouped.values,
                    y=nakes_grouped.index,
                    orientation="h",
                    marker=dict(color="blue"),
                )
            ]
        )
        fig_nakes.update_layout(
            title=title,
            xaxis_title="Jumlah Nakes",
            yaxis_title=yaxis_title,
            margin=dict(t=30, b=10, l=10, r=10),
            height=200,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_nakes, use_container_width=True, config={"displayModeBar": False})

    with col3:
        st.markdown(
            """
            <div class="metric-card">
                <div class="metric-card-title">Cakupan Imunisasi</div>
        """,
            unsafe_allow_html=True,
        )
        st.metric("Cakupan Imunisasi", f"{imun_cov:.1f}%", label_visibility="hidden")
        st.markdown(
            '<div class="small-muted">indikator kunci SSGI</div></div>',
            unsafe_allow_html=True,
        )

        # Line Chart for Cakupan Imunisasi over Time
        imunisasi_per_bulan = (
            df_filtered.groupby(df_filtered["tanggal"].dt.to_period("M"))["imunisasi_lengkap"]
            .mean()
            .reset_index()
        )
        imunisasi_per_bulan["tanggal"] = imunisasi_per_bulan["tanggal"].dt.to_timestamp()
        fig_imun = go.Figure(
            data=[
                go.Scatter(
                    x=imunisasi_per_bulan["tanggal"],
                    y=imunisasi_per_bulan["imunisasi_lengkap"] * 100,
                    mode="lines+markers",
                    line=dict(color="green"),
                )
            ]
        )
        fig_imun.update_layout(
            title="Cakupan Imunisasi per Bulan",
            xaxis_title="Bulan",
            yaxis_title="Cakupan (%)",
            margin=dict(t=30, b=10, l=10, r=10),
            height=200,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_imun, use_container_width=True, config={"displayModeBar": False})

    with col4:
        st.markdown(
            """
            <div class="metric-card">
                <div class="metric-card-title">Akses Air Layak</div>
        """,
            unsafe_allow_html=True,
        )
        st.metric("Akses Air Layak", f"{air_cov:.1f}%", label_visibility="hidden")
        st.markdown(
            '<div class="small-muted">sektor WASH</div></div>', unsafe_allow_html=True
        )

        # Pie Chart for Akses Air Layak
        air_layak_data = df_filtered["akses_air_layak"].value_counts(normalize=True) * 100
        labels = ["Layak", "Tidak Layak"]
        fig_air = go.Figure(
            data=[
                go.Pie(
                    labels=labels,
                    values=air_layak_data,
                    hole=0.4,
                    textinfo="percent+label",
                )
            ]
        )
        fig_air.update_layout(
            title="Proporsi Akses Air Layak",
            margin=dict(t=30, b=10, l=10, r=10),
            height=200,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_air, use_container_width=True, config={"displayModeBar": False})

    st.info(
        "Selamat datang di Dashboard StuntLytics. Gunakan navigasi di sebelah kiri untuk menjelajahi fitur-fitur analisis.",
        icon="👋",
    )


if __name__ == "__main__":
    main()
