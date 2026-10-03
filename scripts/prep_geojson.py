# -*- coding: utf-8 -*-
"""
Menyederhanakan batas kab/kota agar peta ringan dimuat di browser.

Masukan : data/raw/kabkota_karhutla.geojson   (514 kab/kota, +- 4 MB)
Keluaran: data/kabkota_karhutla.geojson       (atribut sama, geometri disederhanakan)

Langkah:
  1. buang koordinat z (selalu 0)
  2. Douglas-Peucker per cincin poligon (toleransi TOL derajat, +- 550 m untuk 0.005)
  3. buang pulau kecil (luas < MIN_AREA derajat^2) kecuali poligon terbesar tiap wilayah
  4. bulatkan koordinat ke 3 desimal (+- 110 m)

Atribut (kode_kabkota, LISA, kejadian per tahun, dst.) tidak diubah.
Jalankan dari akar repo:  python scripts/prep_geojson.py
"""
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "raw" / "kabkota_karhutla.geojson"
DST = ROOT / "data" / "kabkota_karhutla.geojson"
TOL = 0.005          # derajat (+- 550 m)
MIN_AREA = 2e-5      # derajat^2 (+- 0.25 km2)
DEC = 3


def rdp(pts: np.ndarray, tol: float) -> np.ndarray:
    """Douglas-Peucker iteratif untuk polyline terbuka (n x 2)."""
    n = len(pts)
    if n < 3:
        return pts
    keep = np.zeros(n, bool)
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        a, b = stack.pop()
        if b <= a + 1:
            continue
        p, q = pts[a], pts[b]
        seg = pts[a + 1:b]
        d = q - p
        L = np.hypot(*d)
        if L == 0:
            dist = np.hypot(seg[:, 0] - p[0], seg[:, 1] - p[1])
        else:
            dist = np.abs(d[0] * (seg[:, 1] - p[1]) - d[1] * (seg[:, 0] - p[0])) / L
        i = int(np.argmax(dist))
        if dist[i] > tol:
            m = a + 1 + i
            keep[m] = True
            stack += [(a, m), (m, b)]
    return pts[keep]


def simplify_ring(ring, tol):
    pts = np.asarray(ring, float)[:, :2]
    if len(pts) <= 4:
        return pts
    m = int(np.argmax(np.hypot(*(pts - pts[0]).T)))      # titik terjauh -> pecah cincin jadi dua
    out = np.vstack([rdp(pts[:m + 1], tol), rdp(pts[m:], tol)[1:]])
    return out


def ring_area(p):
    x, y = p[:, 0], p[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def simplify_polygon(poly, tol):
    rings = []
    for k, r in enumerate(poly):
        s = simplify_ring(r, tol)
        if len(s) >= 4 and ring_area(s) > 0:
            rings.append(s)
        elif k == 0:
            return None
    return rings


def main():
    g = json.loads(SRC.read_text(encoding="utf-8"))
    n_in = n_out = 0
    for f in g["features"]:
        geom = f["geometry"]
        polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
        res = []
        for poly in polys:
            n_in += sum(len(r) for r in poly)
            s = simplify_polygon(poly, TOL)
            if s:
                res.append(s)
        big = [s for s in res if ring_area(s[0]) >= MIN_AREA]
        res = big or [max(res, key=lambda s: ring_area(s[0]))]
        coords = [[np.round(r, DEC).tolist() for r in s] for s in res]
        n_out += sum(len(r) for s in coords for r in s)
        f["geometry"] = ({"type": "Polygon", "coordinates": coords[0]} if len(coords) == 1
                         else {"type": "MultiPolygon", "coordinates": coords})
    g.pop("xy_coordinate_resolution", None)
    DST.write_text(json.dumps(g, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"titik: {n_in:,} -> {n_out:,}  |  {SRC.stat().st_size/1e6:.2f} MB -> {DST.stat().st_size/1e6:.2f} MB")


if __name__ == "__main__":
    main()
