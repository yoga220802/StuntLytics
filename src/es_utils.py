# src/es_utils.py
import os
import requests
import pandas as pd
import streamlit as st
from typing import Dict, Any, List, Optional, Tuple

# --- Load .env configuration ---
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    print("dotenv not installed, skipping...")

ES_URL = os.getenv("ES_URL", "http://127.0.0.1:9200")
STUNTING_INDEX = os.getenv("STUNTING_INDEX", "stunting-data")
# ... (variabel index lain bisa ditambahkan jika perlu)


# --- HTTP Helpers (imitasi dari referensi) ---
def _es_post(path: str, body: Dict[str, Any], timeout: int = 60) -> Dict[str, Any]:
    """Generic function to send a POST request to Elasticsearch."""
    try:
        r = requests.post(f"{ES_URL}{path}", json=body, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error koneksi ke Elasticsearch: {e}")
        return {}


def ping() -> Tuple[bool, str]:
    """Checks connection to Elasticsearch."""
    try:
        r = requests.get(ES_URL, timeout=5)
        r.raise_for_status()
        info = r.json()
        version = info.get("version", {}).get("number", "unknown")
        return True, f"Terhubung ke Elasticsearch v{version}"
    except requests.exceptions.RequestException as e:
        return False, f"Gagal terhubung ke Elasticsearch: {e}"


# --- Query Builder ---
def build_query_filters(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Builds the 'filter' part of an Elasticsearch query."""
    query_filters = []

    # Date filter
    date_from = filters.get("date_from")
    date_to = filters.get("date_to")
    if date_from or date_to:
        range_q = {"range": {"Tanggal": {}}}
        if date_from:
            range_q["range"]["Tanggal"]["gte"] = date_from.strftime("%Y-%m-%d")
        if date_to:
            range_q["range"]["Tanggal"]["lte"] = date_to.strftime("%Y-%m-%d")
        query_filters.append(range_q)

    # Location filters
    if filters.get("kabupaten"):
        # Menggunakan 'nama_kabupaten_kota' sesuai mapping ES
        query_filters.append({"term": {"nama_kabupaten_kota": filters["kabupaten"]}})
    if filters.get("kecamatan"):
        query_filters.append({"term": {"Kecamatan": filters["kecamatan"]}})

    return query_filters


# --- Data Fetching Functions ---


@st.cache_data(show_spinner="Mengambil opsi filter...")
def get_filter_options() -> Dict[str, List[str]]:
    """Fetches unique values for filter dropdowns."""
    options = {"kabupaten": [], "kecamatan": []}

    # Get Kabupaten
    body = {
        "size": 0,
        "aggs": {
            "unique_terms": {"terms": {"field": "nama_kabupaten_kota", "size": 1000}}
        },
    }
    res = _es_post(f"/{STUNTING_INDEX}/_search", body)
    if res:
        options["kabupaten"] = sorted(
            [
                b["key"]
                for b in res.get("aggregations", {})
                .get("unique_terms", {})
                .get("buckets", [])
            ]
        )

    # Get Kecamatan
    body = {
        "size": 0,
        "aggs": {"unique_terms": {"terms": {"field": "Kecamatan", "size": 5000}}},
    }
    res = _es_post(f"/{STUNTING_INDEX}/_search", body)
    if res:
        options["kecamatan"] = sorted(
            [
                b["key"]
                for b in res.get("aggregations", {})
                .get("unique_terms", {})
                .get("buckets", [])
            ]
        )

    return options


@st.cache_data(show_spinner="Menghitung ringkasan data...")
def get_main_screen_summary(filters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetches a full aggregated summary for the main screen directly from Elasticsearch.
    This is the core of the new, efficient approach.
    """
    base_filters = build_query_filters(filters)

    query = {
        "size": 0,
        "query": {"bool": {"filter": base_filters}},
        "aggs": {
            "total_stunting": {
                "filter": {
                    "term": {
                        "Status Stunting (Stunting / Berisiko / Normal)": "Stunting"
                    }
                }
            },
            "avg_usia_anak": {"avg": {"field": "Usia Anak (bulan)"}},
            # Agregasi untuk Faktor Risiko
            "risk_bblr": {"filter": {"range": {"Berat Lahir (gram)": {"lt": 2500}}}},
            "risk_anemia": {"filter": {"range": {"Hb (g/dL)": {"lt": 11}}}},
            "risk_lila": {"filter": {"range": {"LiLA (cm)": {"lt": 23.5}}}},
            "risk_imunisasi": {
                "filter": {
                    "term": {"Imunisasi (lengkap/tidak lengkap)": "Tidak Lengkap"}
                }
            },
            "risk_asi": {"filter": {"term": {"ASI Eksklusif (ya/tidak)": "Tidak"}}},
            # Agregasi untuk Top Kecamatan
            "top_kecamatan": {
                "terms": {"field": "Kecamatan", "size": 10},
                "aggs": {
                    "stunting_count": {
                        "filter": {
                            "term": {
                                "Status Stunting (Stunting / Berisiko / Normal)": "Stunting"
                            }
                        }
                    }
                },
            },
        },
    }

    res = _es_post(f"/{STUNTING_INDEX}/_search", query)

    # --- Parse the complex response ---
    summary = {}
    if not res:
        return {}  # Return empty dict on error

    aggregations = res.get("aggregations", {})
    total_observasi = res.get("hits", {}).get("total", {}).get("value", 0)

    summary["total_observasi"] = total_observasi
    summary["total_stunting"] = aggregations.get("total_stunting", {}).get(
        "doc_count", 0
    )
    summary["avg_usia_anak"] = aggregations.get("avg_usia_anak", {}).get("value", 0)

    # Parse risk factors
    def _pct(val, total):
        return (val / total) * 100 if total > 0 else 0

    risk_factors = {
        "BBLR (<2500 gr)": _pct(
            aggregations.get("risk_bblr", {}).get("doc_count", 0), total_observasi
        ),
        "Anemia Ibu (Hb < 11)": _pct(
            aggregations.get("risk_anemia", {}).get("doc_count", 0), total_observasi
        ),
        "LiLA Ibu (<23.5 cm)": _pct(
            aggregations.get("risk_lila", {}).get("doc_count", 0), total_observasi
        ),
        "Imunisasi Tidak Lengkap": _pct(
            aggregations.get("risk_imunisasi", {}).get("doc_count", 0), total_observasi
        ),
        "ASI Tidak Eksklusif": _pct(
            aggregations.get("risk_asi", {}).get("doc_count", 0), total_observasi
        ),
    }
    # Sort by percentage descending
    summary["risk_factors"] = dict(
        sorted(risk_factors.items(), key=lambda item: item[1], reverse=True)
    )

    # Parse top kecamatan
    top_kec_buckets = aggregations.get("top_kecamatan", {}).get("buckets", [])
    top_kec_data = {
        b["key"]: {
            "total": b["doc_count"],
            "stunting": b.get("stunting_count", {}).get("doc_count", 0),
        }
        for b in top_kec_buckets
    }
    summary["top_kecamatan"] = top_kec_data

    return summary
