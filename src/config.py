import os
from dotenv import load_dotenv

# Muat environment variables dari file .env
load_dotenv()

# --- Konfigurasi Koneksi Elasticsearch ---
ES_URL = os.getenv("ES_URL", "http://127.0.0.1:9200")
STUNTING_INDEX = os.getenv("STUNTING_INDEX", "stunting-data")
BALITA_INDEX = os.getenv("BALITA_INDEX", "jabar-balita-desa")
NUTRITION_INDEX = os.getenv("NUTRITION_INDEX", "jabar-tenaga-gizi")

# --- Konfigurasi API Lain ---
DEFAULT_INSIGHT_API = os.getenv("OPENAI_API_KEY")
DEFAULT_PREDICT_API = None
# --- Konfigurasi Aplikasi Utama ---
APP_TITLE = "StuntLytics - Dashboard Pemerintah"
APP_DESCRIPTION = "Dashboard e-Government untuk prediksi risiko stunting, monitoring, dan rekomendasi intervensi berbasis AI."
