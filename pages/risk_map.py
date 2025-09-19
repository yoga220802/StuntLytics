import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os
import math
import pathlib
import pydeck as pdk

from src import data_loader, styles
from src.components import sidebar

# Path ke file GeoJSON yang sudah lo punya
GEOJSON_PATH = pathlib.Path(__file__).parents[1] / "geojson" / "jawa-barat.geojson"

@st.cache_data(show_spinner=False)
def load_geojson():
    with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

# --- Normalization helpers & enrichment ---

def _norm_kab(v: str) -> str:
    if not v: return ""
    s = v.upper().strip()
    if s.startswith("KOTA"):
        return " ".join(s.split())
    for pre in ["KABUPATEN", "KAB.", "KAB " , "KAB"]:
        if s.startswith(pre):
            s = s[len(pre):].strip(" .")
            break
    return " ".join(s.split())

def _norm_kec(v: str) -> str:
    if not v: return ""
    s = v.upper().strip()
    for pre in ["KEC.", "KEC " , "KEC"]:
        if s.startswith(pre):
            s = s[len(pre):].strip(" .")
            break
    return " ".join(s.split())

def _risk_to_color(score: float):
    if score is None or pd.isna(score):
        return [210,210,210,60]
    # green -> yellow -> red
    score = max(0.0, min(1.0, float(score)))
    if score < 0.5:
        t = score / 0.5  # 0..1
        r = int(0 + t * 255)
        g = int(180 + t * (215-180))
        b = 0
    else:
        t = (score - 0.5) / 0.5
        r = int(255 - t * (255-200))
        g = int(215 - t * 215)
        b = 0
    return [r, g, b, 160]

def _aggregate_risk(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["kab_key","kec_key","risk_mean","n","p_tinggi","p_sedang","p_rendah"])
    grp = df.groupby(["kab_key","kec_key"])
    out = grp.agg(
        n=("risk_score","size"),
        risk_mean=("risk_score","mean"),
        p_tinggi=("risk_label", lambda s: (s=="Tinggi").mean()),
        p_sedang=("risk_label", lambda s: (s=="Sedang").mean()),
        p_rendah=("risk_label", lambda s: (s=="Rendah").mean()),
    ).reset_index()
    return out

def _enrich_geojson(geojson: dict, agg: pd.DataFrame):
    lookup = {(r.kab_key, r.kec_key): r for r in agg.itertuples()}
    for f in geojson.get("features", []):
        prop = f.get("properties", {})
        kab_key = _norm_kab(prop.get("KABKOT",""))
        kec_key = _norm_kec(prop.get("KECAMATAN",""))
        rec = lookup.get((kab_key, kec_key))
        if rec:
            prop.update({
                "risk_mean": round(rec.risk_mean, 4),
                "risk_count": int(rec.n),
                "p_tinggi": round(rec.p_tinggi, 3),
                "p_sedang": round(rec.p_sedang, 3),
                "p_rendah": round(rec.p_rendah, 3),
            })
            prop["risk_color"] = _risk_to_color(rec.risk_mean)
        else:
            prop.setdefault("risk_mean", None)
            prop.setdefault("risk_count", 0)
            prop.setdefault("p_tinggi", None)
            prop.setdefault("p_sedang", None)
            prop.setdefault("p_rendah", None)
            prop["risk_color"] = _risk_to_color(None)
        f["properties"] = prop
    return geojson

# Helper: filter geojson
def filter_geojson(geojson, kabupaten=None, kecamatan=None):
    """
    kabupaten / kecamatan boleh:
      - None / "Semua" -> diabaikan
    """
    feats = []
    want_kab = kabupaten and kabupaten.lower() != "semua"
    want_kec = kecamatan and kecamatan.lower() != "semua"
    for f in geojson.get("features", []):
        prop = f.get("properties", {})
        if want_kab and prop.get("KABKOT", "").upper() != kabupaten.upper():
            continue
        if want_kec and prop.get("KECAMATAN", "").upper() != kecamatan.upper():
            continue
        feats.append(f)
    return {"type": "FeatureCollection", "features": feats}

# Helper: extract bbox & compute center / zoom
def _walk_coords(coords, lats, lons):
    # coords bisa nested (MultiPolygon)
    if isinstance(coords, (list, tuple)):
        if len(coords) == 0:
            return
        if isinstance(coords[0], (int, float)) and len(coords) == 2:
            lon, lat = coords
            lats.append(lat); lons.append(lon)
        else:
            for c in coords:
                _walk_coords(c, lats, lons)

def _approximate_zoom(lat_span, lon_span):
    # Hindari zero
    lat_span = max(lat_span, 1e-5)
    lon_span = max(lon_span, 1e-5)
    # Konversi kasar: 360 derajat ~ zoom 0
    z_lon = math.log2(360.0 / lon_span)
    z_lat = math.log2(180.0 / lat_span)
    zoom = min(z_lon, z_lat)
    # Batasi
    return max(5, min(zoom, 14))

def compute_view(features, default_center={"lat": -6.9175, "lon": 107.6191}, default_zoom=7.5):
    if not features:
        return default_center, default_zoom

    lats, lons = [], []
    for f in features:
        geom = f.get("geometry") or {}
        coords = geom.get("coordinates")
        _walk_coords(coords, lats, lons)

    if not lats or not lons:
        return default_center, default_zoom

    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)
    center = {"lat": (min_lat + max_lat) / 2, "lon": (min_lon + max_lon) / 2}
    zoom = _approximate_zoom(max_lat - min_lat, max_lon - min_lon)
    return center, zoom

def render_map():
    geojson = load_geojson()
    from src.components.sidebar import render_geo_sidebar
    kabupaten, kecamatan = render_geo_sidebar(geojson)

    # Load & prepare risk data
    df = data_loader.load_data()
    # Normalisasi kolom matching geojson
    df["kab_key"] = df["kabupaten"].apply(_norm_kab)
    df["kec_key"] = df["kecamatan"].apply(_norm_kec) if "kecamatan" in df.columns else ""

    # Terapkan filter wilayah ke DataFrame
    df_filtered = df.copy()
    if kabupaten and kabupaten.lower() != "semua":
        norm_kab_sel = _norm_kab(kabupaten)
        df_filtered = df_filtered[df_filtered["kab_key"] == norm_kab_sel]
    if kecamatan and kecamatan.lower() != "semua":
        norm_kec_sel = _norm_kec(kecamatan)
        df_filtered = df_filtered[df_filtered["kec_key"] == norm_kec_sel]

    agg = _aggregate_risk(df_filtered)

    # Filter geojson fitur untuk viewport & warna hanya yang tampil
    filtered = filter_geojson(geojson, kabupaten, kecamatan)
    enriched = _enrich_geojson(filtered, agg)

    feats = enriched["features"]
    center, zoom = compute_view(feats)

    st.subheader("Peta Risiko Stunting (Agregasi per Kecamatan)")

    if not feats:
        st.info("Tidak ada fitur untuk filter yang dipilih.")
        return

    # Layer dengan warna berdasarkan risk_mean
    layer = pdk.Layer(
        "GeoJsonLayer",
        enriched,
        stroked=True,
        filled=True,
        get_fill_color="risk_color",
        get_line_color=[255, 255, 255],
        line_width_min_pixels=1,
        pickable=True,
        auto_highlight=True,
    )

    tooltip = {
        "html": """
        <b>{KABKOT} - {KECAMATAN}</b><br/>
        Mean Risk: {risk_mean}<br/>
        N: {risk_count}<br/>
        Prop Tinggi: {p_tinggi}<br/>
        Prop Sedang: {p_sedang}<br/>
        Prop Rendah: {p_rendah}
        """,
        "style": {"backgroundColor": "rgba(30,30,30,0.8)", "color": "white"}
    }

    r = pdk.Deck(
        layers=[layer],
        initial_view_state=pdk.ViewState(
            latitude=center["lat"],
            longitude=center["lon"],
            zoom=zoom,
            pitch=0
        ),
        tooltip=tooltip
    )
    st.pydeck_chart(r)

    # Legend sederhana
    st.markdown("""
    <div style="margin-top:8px;">
      <b>Legenda Mean Risk</b><br/>
      <div style="display:flex;align-items:center;font-size:12px;">
        <div style="width:160px;height:14px;
          background:linear-gradient(90deg, rgba(0,180,0,1) 0%, rgba(255,215,0,1) 50%, rgba(200,0,0,1) 100%);
          border:1px solid #999;"></div>
        <div style="margin-left:8px;">0 &larr; rendah ... tinggi &rarr; 1</div>
      </div>
      <div style="font-size:11px;color:#666;">Abu-abu: tidak ada data</div>
    </div>
    """, unsafe_allow_html=True)

# Jalankan saat halaman dibuka
def main():
    st.title("Risk Map - Jawa Barat")
    render_map()

if __name__ == "__main__":
    main()
