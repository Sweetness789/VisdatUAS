# -*- coding: utf-8 -*-
"""
Fungsi bantu untuk Bab 5 (data geospasial kab/kota). Tanpa dependensi Streamlit/Plotly
supaya mudah diuji: `python -m pytest tests/` atau jalankan langsung `python geo_utils.py`.
"""
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

YEARS = list(range(2021, 2027))
YEAR_PARSIAL = 2026          # tahun terakhir belum penuh

# Kelas kepadatan: 0 = tanpa kejadian (abu gelap), 1-5 = kuintil dari wilayah yang pernah terbakar.
# Palet "inferno" (luminans monoton, aman buta warna); terang = tinggi agar terbaca di basemap gelap.
KELAS_WARNA = ["#2b2323", "#6a176e", "#bc3754", "#f37819", "#f6d746", "#fcffa4"]

# Klaster LISA (Anselin) dengan warna Okabe-Ito
LISA_URUT = ["High-High", "High-Low", "Low-High", "Low-Low", "Tidak signifikan"]
LISA_WARNA = {"High-High": "#D55E00", "High-Low": "#E69F00", "Low-High": "#56B4E9",
              "Low-Low": "#0072B2", "Tidak signifikan": "#3a3030"}
LISA_ARTI = {"High-High": "tinggi, dikelilingi tinggi (hotspot)",
             "High-Low": "tinggi, dikelilingi rendah (pencilan)",
             "Low-High": "rendah, dikelilingi tinggi",
             "Low-Low": "rendah, dikelilingi rendah (coldspot)",
             "Tidak signifikan": "tidak signifikan secara statistik"}


def periode_label(p) -> str:
    return "2021–2026 (kumulatif)" if p == "all" else str(p)


def count_col(p) -> str:
    return "n_kejadian" if p == "all" else f"kej_{p}"


def rate_col(p) -> str:
    return "kejadian_per_1000km2" if p == "all" else f"kej_per_1000km2_{p}"


def load_geo(path):
    """Kembalikan (atribut: DataFrame, geojson_ringan: dict, batas_provinsi: dict).

    geojson_ringan hanya membawa `kode_kabkota` sebagai properti agar payload ke browser kecil.
    batas_provinsi[nama] = (lon_min, lon_max, lat_min, lat_max).
    """
    g = json.loads(Path(path).read_text(encoding="utf-8"))
    props, ringan, box = [], [], {}
    for f in g["features"]:
        p = f["properties"]
        props.append(p)
        ringan.append({"type": "Feature", "properties": {"kode_kabkota": p["kode_kabkota"]},
                       "geometry": f["geometry"]})
        xs, ys = _flatten(f["geometry"]["coordinates"])
        b = box.setdefault(p["provinsi"], [1e9, -1e9, 1e9, -1e9])
        b[0], b[1] = min(b[0], min(xs)), max(b[1], max(xs))
        b[2], b[3] = min(b[2], min(ys)), max(b[3], max(ys))
    df = pd.DataFrame(props)
    df["kode_kabkota"] = df["kode_kabkota"].astype(str)
    df["tanggal_pertama"] = pd.to_datetime(df["tanggal_pertama"])
    df["tanggal_terakhir"] = pd.to_datetime(df["tanggal_terakhir"])
    return df, {"type": "FeatureCollection", "features": ringan}, {k: tuple(v) for k, v in box.items()}


def _flatten(c):
    xs, ys = [], []
    stack = [c]
    while stack:
        x = stack.pop()
        if isinstance(x[0], (int, float)):
            xs.append(x[0]); ys.append(x[1])
        else:
            stack.extend(x)
    return xs, ys


def class_breaks(df: pd.DataFrame, p) -> np.ndarray:
    """Empat batas kuintil dari kepadatan non-nol.

    p == "all": kuintil kepadatan kumulatif 2021-2026 (sama dengan kolom `kelas_kepadatan`).
    p == tahun: kuintil dari gabungan enam kolom tahunan, supaya warna antar-tahun sebanding.
    """
    if p == "all":
        v = df["kejadian_per_1000km2"]
    else:
        v = pd.concat([df[rate_col(y)] for y in YEARS])
    v = v[v > 0]
    return v.quantile([.2, .4, .6, .8]).to_numpy()


def classify(values, breaks) -> np.ndarray:
    v = np.asarray(values, float)
    return np.where(v <= 0, 0, 1 + np.searchsorted(breaks, v, side="left")).astype(int)


def _f(x: float) -> str:
    return f"{x:.2f}" if x < 10 else f"{x:.1f}"


def class_labels(breaks) -> list[str]:
    b = [_f(x) for x in breaks]
    return ["Tidak ada kejadian", f"≤ {b[0]}", f"{b[0]}–{b[1]}", f"{b[1]}–{b[2]}", f"{b[2]}–{b[3]}", f"> {b[3]}"]


def fit_view(bounds, w_px=760, h_px=560, pad=0.35):
    """Pusat dan zoom (Web Mercator) agar kotak batas muat di peta."""
    x0, x1, y0, y1 = bounds
    lon_c, lat_c = (x0 + x1) / 2, (y0 + y1) / 2
    span_x = max(x1 - x0, 0.05)
    span_y = max(y1 - y0, 0.05)
    z_x = math.log2(360 * w_px / (256 * span_x))
    z_y = math.log2(360 * h_px * math.cos(math.radians(lat_c)) / (256 * span_y))
    return {"lat": lat_c, "lon": lon_c}, max(2.0, min(z_x, z_y) - pad)


NASIONAL_PUSAT = {"lat": -2.6, "lon": 118.0}
NASIONAL_ZOOM = 3.7


if __name__ == "__main__":      # uji cepat
    here = Path(__file__).parent
    d, geo, box = load_geo(here / "data" / "kabkota_karhutla.geojson")
    assert len(d) == 514 and len(geo["features"]) == 514 and len(box) == 38
    b = class_breaks(d, "all")
    assert (classify(d.kejadian_per_1000km2, b) == d.kelas_kepadatan).all(), "kuintil tidak sama dengan kelas_kepadatan"
    print("breaks kumulatif :", np.round(b, 2), class_labels(b))
    for y in YEARS:
        by = class_breaks(d, y)
        print(y, np.bincount(classify(d[rate_col(y)], by), minlength=6))
    c, z = fit_view(box["Kalimantan Selatan"])
    print("Kalsel:", c, round(z, 2))
    print("OK")
