import os

# --- Main App Config ---
APP_TITLE = "StuntLytics - Dashboard Pemerintah"
APP_DESCRIPTION = (
    "Dashboard e-Government untuk prediksi risiko stunting, monitoring, dan rekomendasi intervensi berbasis AI."
)

# --- API Endpoints (default values, can be overridden by environment variables) ---
DEFAULT_PREDICT_API = os.getenv("PREDICT_API", "http://127.0.0.1:8005/predict")
DEFAULT_INSIGHT_API = os.getenv("INSIGHT_API", "http://127.0.0.1:8006/insight")
DEFAULT_ELASTIC = os.getenv("ELASTICSEARCH_URL", "http://127.0.0.1:9200")

# --- Fallback Rules ---
# Aturan sederhana jika API Insight tidak tersedia
INSIGHT_RULES = {
    "sanitasi": {
        "when": lambda d: (1-d["akses_air_layak"]).mean() > 0.35 or (1-d["jamban_sehat"]).mean() > 0.35,
        "msg": "Prioritaskan program PAMSIMAS/air bersih & jamban sehat di wilayah dengan sanitasi buruk."
    },
    "imunisasi": {
        "when": lambda d: (1-d["imunisasi_lengkap"]).mean() > 0.35,
        "msg": "Lakukan sweeping imunisasi dasar lengkap di kecamatan dengan cakupan rendah."
    },
    "bblr": {
        "when": lambda d: d["bblr"].mean() > 0.18,
        "msg": "Perkuat kelas ibu hamil & pemantauan BBLR, distribusikan PMT spesifik gizi."
    },
}
