import os
import pandas as pd
import numpy as np
import streamlit as st

@st.cache_data(show_spinner="Memuat data awal...")
def load_data(csv_path: str = "data/data_keluarga.csv") -> pd.DataFrame:
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
    else:
        st.warning(f"File data tidak ditemukan di '{csv_path}'. Membuat dummy data untuk demo.")
        np.random.seed(42)
        kabupaten = [
            "Kab. Garut","Kab. Bandung","Kota Bandung","Kab. Tasikmalaya","Kab. Cirebon",
            "Kab. Bogor","Kota Bogor","Kab. Sukabumi","Kota Depok","Kab. Sumedang",
        ]
        kecamatan = [f"Kec. {x}" for x in [
            "Tarogong Kidul","Cibatu","Leles","Cicalengka","Rancaekek","Sukajadi","Lengkong",
            "Cisayong","Sumber","Cibinong","Cimanggung"
        ]]
        n = 2000
        df = pd.DataFrame({
            "kabupaten": np.random.choice(kabupaten, n),
            "kecamatan": np.random.choice(kecamatan, n),
            "desa": [f"Desa-{i%50:02d}" for i in range(n)],
            "tanggal": pd.to_datetime(np.random.choice(pd.date_range("2024-01-01","2025-08-01"), n)),
            "usia_anak_bulan": np.random.randint(0, 60, n),
            "jenis_kelamin": np.random.choice(["L","P"], n),
            "bblr": np.random.choice([0,1], n, p=[0.85,0.15]),
            "asi_eksklusif": np.random.choice([0,1], n, p=[0.4,0.6]),
            "mp_asi_tepatsesuai": np.random.choice([0,1], n, p=[0.5,0.5]),
            "imunisasi_lengkap": np.random.choice([0,1], n, p=[0.3,0.7]),
            "pendidikan_ibu": np.random.choice(["SD","SMP","SMA","D3","S1+"], n, p=[0.25,0.3,0.3,0.1,0.05]),
            "akses_air_layak": np.random.choice([0,1], n, p=[0.2,0.8]),
            "jamban_sehat": np.random.choice([0,1], n, p=[0.25,0.75]),
            "pengeluaran_bulan": np.random.normal(3200000, 1000000, n).clip(500000, 10000000).round(),
            "tanggungan": np.random.randint(1, 7, n),
        })
        # Add dummy data for total bayi lahir and total bayi stunting
        df["total_bayi_lahir"] = np.random.randint(1, 10, n)
        df["total_bayi_stunting"] = np.random.randint(0, df["total_bayi_lahir"] + 1)
        
        # Add dummy data for jumlah_nakes (healthcare workers) per year
        years = pd.date_range("2024-01-01", "2025-12-31", freq="Y").year
        df["tahun"] = df["tanggal"].dt.year
        df["jumlah_nakes"] = df["kabupaten"].map(
            lambda x: np.random.randint(50, 500) if x else 0
        ) + np.random.choice(range(10, 50), len(df))

        score = (
            0.25*df["bblr"] + 0.15*(1-df["asi_eksklusif"]) + 0.12*(1-df["imunisasi_lengkap"]) +
            0.18*(1-df["akses_air_layak"]) + 0.12*(1-df["jamban_sehat"]) +
            0.08*(df["usia_anak_bulan"]/60.0) + 0.10*(df["tanggungan"]/7.0)
        )
        df["risk_score"] = (score - score.min()) / (score.max() - score.min() + 1e-9)
        bins = [-0.01, 0.33, 0.66, 1.0]
        df["risk_label"] = pd.cut(df["risk_score"], bins=bins, labels=["Rendah","Sedang","Tinggi"]).astype(str)
    
    # Konversi tipe data tanggal jika belum
    df['tanggal'] = pd.to_datetime(df['tanggal'])
    return df
