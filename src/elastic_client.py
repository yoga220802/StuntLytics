# StuntLytics/src/elastic_client.py
# VERSI FINAL (dengan perbaikan bug .keyword) - Mesin utama untuk mengambil data dari Elasticsearch
import os
import requests
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple

try:
    from pathlib import Path
    from dotenv import load_dotenv

    ROOT = Path(__file__).resolve().parents[1]
    load_dotenv(ROOT / ".env")
except Exception:
    pass

ES_URL = os.getenv("ES_URL", "http://178.128.219.5:9200")
STUNTING_INDEX = os.getenv("STUNTING_INDEX", "stunting-data")
NUTRITION_INDEX = os.getenv("NUTRITION_INDEX", "jabar-tenaga-gizi")

CANDIDATES_WILAYAH = ["nama_kabupaten_kota", "Wilayah"]
CANDIDATES_KECAMATAN = ["Kecamatan"]


# --- Helper Functions (ping, _es_post, build_query) ---
def _es_post(
    index: str, path: str, body: Dict[str, Any], timeout: int = 60
) -> Dict[str, Any]:
    try:
        r = requests.post(f"{ES_URL}/{index}{path}", json=body, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Gagal menghubungi Elasticsearch di {ES_URL}: {e}")


def ping() -> Tuple[bool, str]:
    try:
        r = requests.get(ES_URL, timeout=5)
        return r.status_code == 200, f"ES {ES_URL} status {r.status_code}"
    except Exception as e:
        return False, f"Gagal hubungi ES: {e}"


def build_query(filters: Dict[str, Any]) -> Dict[str, Any]:
    must = []
    if filters.get("date_from") or filters.get("date_to"):
        rng = {}
        if filters.get("date_from"):
            rng["gte"] = filters["date_from"].isoformat()
        if filters.get("date_to"):
            rng["lte"] = filters["date_to"].isoformat()
        must.append({"range": {"Tanggal": rng}})
    if filters.get("wilayah_field") and filters.get("wilayah"):
        must.append({"terms": {filters["wilayah_field"]: filters["wilayah"]}})
    if filters.get("kecamatan_field") and filters.get("kecamatan"):
        must.append({"terms": {filters["kecamatan_field"]: filters["kecamatan"]}})
    return {"query": {"bool": {"must": must}}} if must else {"query": {"match_all": {}}}


# --- Fungsi untuk Sidebar ---
def get_filter_options(
    base_filters: Dict[str, Any], field_candidates: List[str], size: int = 500
) -> Tuple[Optional[str], List[str]]:
    for field in field_candidates:
        try:
            body = build_query(base_filters)
            # FIX: Gunakan nama field langsung dari candidates, tanpa menambahkan .keyword
            body.update(
                {"size": 0, "aggs": {"opts": {"terms": {"field": field, "size": size}}}}
            )
            data = _es_post(STUNTING_INDEX, "/_search", body)
            buckets = data.get("aggregations", {}).get("opts", {}).get("buckets", [])
            if buckets:
                options = [b["key"] for b in buckets]
                # FIX: Kembalikan nama field yang berhasil, bukan field + .keyword
                return field, sorted(options)
        except Exception:
            continue
    return None, []


# --- Fungsi Utama untuk app.py ---
def get_main_page_summary(filters: Dict[str, Any]) -> Dict[str, Any]:
    """Satu fungsi untuk mengambil SEMUA data yang dibutuhkan halaman utama."""
    stunting_labels = ["Stunting", "Ya", "YA", "ya", "1", "true", "TRUE", "True"]

    # 1. Query Utama untuk Index Stunting
    stunting_body = build_query(filters)
    stunting_body.update(
        {
            "size": 0,
            "track_total_hits": True,
            "aggs": {
                "stunting_count": {
                    "filter": {
                        "bool": {
                            "should": [
                                # FIX: Menghapus .keyword
                                {"terms": {"Status Stunting (Biner)": stunting_labels}},
                                {"range": {"Z-Score TB/U": {"lte": -2.0}}},
                            ],
                            "minimum_should_match": 1,
                        }
                    }
                },
                # FIX: Menghapus .keyword
                "imunisasi_lengkap": {
                    "filter": {
                        "terms": {"Status Imunisasi Anak": ["lengkap", "Lengkap"]}
                    }
                },
                # FIX: Menghapus .keyword
                "total_imunisasi_field": {
                    "value_count": {"field": "Status Imunisasi Anak"}
                },
                # FIX: Menghapus .keyword
                "air_bersih_dist": {"terms": {"field": "Akses Air Bersih", "size": 5}},
                "imunisasi_trend": {
                    "date_histogram": {
                        "field": "Tanggal",
                        "calendar_interval": "month",
                        "format": "yyyy-MM",
                    },
                    "aggs": {
                        "imunisasi_lengkap_in_bucket": {
                            "filter": {
                                "terms": {
                                    "Status Imunisasi Anak": ["lengkap", "Lengkap"]
                                }
                            }
                        }
                    },
                },
            },
        }
    )

    # 2. Query untuk Index Nakes
    nakes_must_clause = []
    if filters.get("wilayah_field") and filters.get("wilayah"):
        # FIX: Menghapus .keyword
        nakes_must_clause.append({"terms": {"nama_kabupaten_kota": filters["wilayah"]}})

    nakes_query = (
        {"bool": {"must": nakes_must_clause}}
        if nakes_must_clause
        else {"match_all": {}}
    )
    nakes_body = {"size": 0, "query": nakes_query}
    nakes_body["aggs"] = {
        "total_nakes": {"sum": {"field": "jumlah_nakes_gizi"}},
        "nakes_by_region": {
            # FIX: Menghapus .keyword
            "terms": {"field": "nama_kabupaten_kota", "size": 100},
            "aggs": {"sum_nakes_in_bucket": {"sum": {"field": "jumlah_nakes_gizi"}}},
        },
    }

    # Eksekusi Query
    stunting_data = _es_post(STUNTING_INDEX, "/_search", stunting_body)
    nakes_data = _es_post(NUTRITION_INDEX, "/_search", nakes_body)

    # Proses Hasil
    s_agg = stunting_data.get("aggregations", {})
    n_agg = nakes_data.get("aggregations", {})

    total_lahir = stunting_data.get("hits", {}).get("total", {}).get("value", 0)
    total_stunting = s_agg.get("stunting_count", {}).get("doc_count", 0)

    imun_lengkap = s_agg.get("imunisasi_lengkap", {}).get("doc_count", 0)
    imun_total = s_agg.get("total_imunisasi_field", {}).get("value", 0)
    imun_cov_pct = (imun_lengkap / imun_total * 100) if imun_total > 0 else 0

    air_buckets = s_agg.get("air_bersih_dist", {}).get("buckets", [])
    air_layak_count = sum(
        b["doc_count"]
        for b in air_buckets
        if b["key"] in ["Layak", "Ya", "Bersih", "Aman"]
    )
    air_total = sum(b["doc_count"] for b in air_buckets)
    air_cov_pct = (air_layak_count / air_total * 100) if air_total > 0 else 0

    nakes_buckets = n_agg.get("nakes_by_region", {}).get("buckets", [])
    if nakes_buckets:
        nakes_grouped = (
            pd.DataFrame(
                [
                    {
                        "region": b["key"],
                        "jumlah_nakes": b["sum_nakes_in_bucket"]["value"],
                    }
                    for b in nakes_buckets
                ]
            )
            .set_index("region")["jumlah_nakes"]
            .sort_values(ascending=False)
        )
    else:
        nakes_grouped = pd.Series([], dtype="float64", name="jumlah_nakes")

    imun_trend_rows = []
    for b in s_agg.get("imunisasi_trend", {}).get("buckets", []):
        total_in_bucket = b["doc_count"]
        lengkap_in_bucket = b["imunisasi_lengkap_in_bucket"]["doc_count"]
        imun_trend_rows.append(
            {
                "tanggal": pd.to_datetime(b["key_as_string"]),
                "imunisasi_lengkap": (lengkap_in_bucket / total_in_bucket)
                if total_in_bucket > 0
                else 0,
            }
        )
    imunisasi_per_bulan = pd.DataFrame(imun_trend_rows)

    air_layak_data = pd.Series(
        {"Layak": air_layak_count, "Tidak Layak": air_total - air_layak_count}
    )

    return {
        "kpi": {
            "total_bayi_lahir": total_lahir,
            "total_bayi_stunting": total_stunting,
            "jumlah_nakes": n_agg.get("total_nakes", {}).get("value", 0),
            "cakupan_imunisasi_pct": imun_cov_pct,
            "akses_air_layak_pct": air_cov_pct,
        },
        "charts": {
            "nakes_by_region": nakes_grouped,
            "imunisasi_trend": imunisasi_per_bulan,
            "air_distribusi": air_layak_data,
        },
    }


# --- Fungsi BARU untuk correlation_trend.py (Meniru Referensi ES) ---


def get_monthly_trend(filters: Dict[str, Any]) -> pd.DataFrame:
    """
    VERSI BARU: Meniru 100% logika `trend_monthly` dari referensi es.py.
    Menghitung persentase stunting (bukan risiko tinggi).
    """
    body = build_query(filters)
    body.update(
        {
            "size": 0,
            "aggs": {
                "per_month": {
                    "date_histogram": {
                        "field": "Tanggal",
                        "calendar_interval": "month",
                    },
                    "aggs": {
                        "stunting_any": {
                            "filter": {
                                "bool": {
                                    "should": [
                                        {
                                            "terms": {
                                                "Status Stunting (Biner)": [
                                                    "Stunting",
                                                    "Ya",
                                                    "YA",
                                                    "ya",
                                                    "1",
                                                    "true",
                                                    "TRUE",
                                                    "True",
                                                ]
                                            }
                                        },
                                        {
                                            "terms": {
                                                "Status Stunting (Stunting / Berisiko / Normal)": [
                                                    "Stunting",
                                                    "stunting",
                                                ]
                                            }
                                        },
                                        {"range": {"Z-Score TB/U": {"lte": -2.0}}},
                                    ],
                                    "minimum_should_match": 1,
                                }
                            }
                        },
                        "total_in_month": {"filter": {"match_all": {}}},
                    },
                }
            },
        }
    )
    res = _es_post(STUNTING_INDEX, "/_search", body)
    rows = []
    for b in res["aggregations"]["per_month"]["buckets"]:
        total = b["total_in_month"]["doc_count"]
        stunting = b["stunting_any"]["doc_count"]
        percent = (stunting / total * 100) if total > 0 else 0
        rows.append({"Bulan": b["key_as_string"][:7], "Stunting %": round(percent, 2)})
    return pd.DataFrame(rows).set_index("Bulan")


def get_numeric_sample_for_corr(
    filters: Dict[str, Any], size: int = 5000
) -> pd.DataFrame:
    """
    VERSI BARU: Meniru 100% logika `numeric_sample_for_corr` dari referensi es.py.
    """
    # 1. Tarik sampel mentah, apa adanya.
    body = build_query(filters)
    body.update({"size": size})
    data = _es_post(STUNTING_INDEX, "/_search", body)
    hits = data.get("hits", {}).get("hits", [])
    df_sample = pd.DataFrame([h.get("_source", {}) for h in hits])

    if df_sample.empty:
        return pd.DataFrame()

    # 2. Biarkan Pandas memilih kolom numerik. Ini cara paling tangguh.
    return df_sample.select_dtypes(include=["number"]).copy()


# --- Fungsi untuk Halaman Explorer Data ---
def _apply_advanced_filters_to_query(body: dict, advanced_filters: dict) -> dict:
    """Helper untuk menerapkan filter lanjutan ke body query yang sudah ada."""
    has_advanced_filters = any(
        (isinstance(advanced_filters.get(key), list) and advanced_filters.get(key))
        or (
            not isinstance(advanced_filters.get(key), list)
            and advanced_filters.get(key)
            and advanced_filters.get(key) != "Semua"
        )
        for key in advanced_filters
    )

    if not has_advanced_filters:
        return body

    if "match_all" in body["query"]:
        body["query"] = {"bool": {"must": []}}

    must_clauses = body["query"]["bool"]["must"]

    if advanced_filters.get("pendidikan_ibu"):
        must_clauses.append(
            {"terms": {"Pendidikan Ibu": advanced_filters["pendidikan_ibu"]}}
        )

    if advanced_filters.get("asi_eksklusif") != "Semua":
        val = (
            ["Ya", "ya", "True", "true", "1"]
            if advanced_filters["asi_eksklusif"] == "Ya"
            else ["Tidak", "tidak", "False", "false", "0"]
        )
        must_clauses.append(
            {
                "bool": {
                    "should": [
                        {"terms": {"ASI Eksklusif": val}},
                        {"terms": {"ASI Eksklusif (ya/tidak)": val}},
                    ],
                    "minimum_should_match": 1,
                }
            }
        )

    if advanced_filters.get("akses_air") != "Semua":
        val = (
            ["Layak", "Ada", "Ya", "Bersih", "Aman"]
            if advanced_filters["akses_air"] == "Ada"
            else ["Tidak Layak", "Tidak", "Tidak Ada"]
        )
        must_clauses.append(
            {
                "bool": {
                    "should": [
                        {"terms": {"Akses Air": val}},
                        {"terms": {"Akses Air Bersih": val}},
                    ],
                    "minimum_should_match": 1,
                }
            }
        )

    return body


def get_explorer_data(
    filters: dict, advanced_filters: dict, size: int = 1000
) -> pd.DataFrame:
    body = build_query(filters)
    body = _apply_advanced_filters_to_query(body, advanced_filters)

    source_fields = [
        "Tanggal",
        "nama_kabupaten_kota",
        "Kecamatan",
        "Status Stunting (Biner)",
        "ZScore TB/U",
        "Usia Anak (bulan)",
        "Berat Lahir (gram)",
        "ASI Eksklusif",
        "Status Imunisasi Anak",
        "Pendidikan Ibu",
        "Akses Air Bersih",
    ]

    body["_source"] = source_fields
    body["size"] = size
    body["sort"] = [{"ZScore TB/U": "asc"}]

    data = _es_post(STUNTING_INDEX, "/_search", body)

    hits = data.get("hits", {}).get("hits", [])
    df = pd.DataFrame([h.get("_source", {}) for h in hits])

    if not df.empty:
        df = df.rename(
            columns={
                "nama_kabupaten_kota": "Kabupaten/Kota",
                "Status Stunting (Biner)": "Status Stunting",
                "ZScore TB/U": "Z-Score",
                "Usia Anak (bulan)": "Usia Anak (bln)",
                "Berat Lahir (gram)": "Berat Lahir (gr)",
                "Status Imunisasi Anak": "Imunisasi",
                "Akses Air Bersih": "Akses Air",
            }
        )
    return df


def get_top_counts_for_explorer_chart(
    filters: dict, advanced_filters: dict
) -> pd.DataFrame:
    """Fungsi baru untuk chart berjenjang."""
    if filters.get("wilayah"):
        agg_field = "Kecamatan"
        level_label = "Kecamatan"
    else:
        agg_field = "nama_kabupaten_kota"
        level_label = "Kabupaten/Kota"

    body = build_query(filters)
    body = _apply_advanced_filters_to_query(body, advanced_filters)

    body["size"] = 0
    body["aggs"] = {"counts_by_region": {"terms": {"field": agg_field, "size": 5}}}

    data = _es_post(STUNTING_INDEX, "/_search", body)
    buckets = (
        data.get("aggregations", {}).get("counts_by_region", {}).get("buckets", [])
    )

    if not buckets:
        return pd.DataFrame(columns=[level_label, "Jumlah Data"])

    df = pd.DataFrame(buckets)
    df = df.rename(columns={"key": level_label, "doc_count": "Jumlah Data"})

    return df
