# -*- coding: utf-8 -*-
"""
TITIK API NUSANTARA - Web story deteksi potensi Karhutla per provinsi (2025)
UAS Visualisasi Data dan Informasi 2026 - Politeknik Statistika STIS

Topik visualisasi:
  (a) Data berdimensi tinggi : PCA + radar chart + clustered heatmap (brushing & linking)
  (c) Data berhierarki       : sunburst + treemap (drill-down + breadcrumb)
  (d) Data teks              : word cloud + jaringan ko-okurensi + tren topik (LDA)
  (e) Data geospasial        : choropleth + lingkaran proporsional + klaster LISA (514 kab/kota)

Susunan halaman: satu halaman panjang; menu tetap di atas (topnav) melompat ke tiap bagian.
"""
import base64
import html as _html
import itertools
import random
import collections
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import networkx as nx
from scipy.cluster.hierarchy import linkage, leaves_list
from sklearn.decomposition import PCA, LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.preprocessing import StandardScaler
from matplotlib.colors import LinearSegmentedColormap
from wordcloud import WordCloud

from geo_utils import (YEARS, YEAR_PARSIAL, KELAS_WARNA, LISA_URUT, LISA_WARNA, LISA_ARTI, NASIONAL_PUSAT, NASIONAL_ZOOM,
                       load_geo, class_breaks, classify, class_labels, count_col, rate_col, fit_view)

# =============================================================================
# 0. KONFIGURASI  (EDIT BAGIAN INI)
# =============================================================================
BASE = Path(__file__).parent
DATA_PROV = BASE / "data" / "Data_Provinsi_2025.xlsx"
DATA_TEKS = BASE / "data" / "Korpus.xlsx"
DATA_GEO = BASE / "data" / "kabkota_karhutla.geojson"     # hasil scripts/prep_geojson.py (geometri disederhanakan)
ICON_DIR = BASE / "assets" / "icons"

TAHUN = 2025
JUDUL = "TITIK API NUSANTARA"
SUBJUDUL = "Api tidak menyala tanpa jejak."

# TODO: isi sesuai sumber aslimu. Teks ini muncul di footer dan pada anotasi grafik.
SUMBER_BENCANA = "BPS - Statistik Bencana per Provinsi 2025"            # TODO: judul tabel BPS persisnya
URL_BENCANA = "https://www.bps.go.id/"                                   # TODO: URL tabel
SUMBER_SATELIT = "citra satelit (NDVI, LST, NBR, curah hujan, RH)"       # TODO: mis. MODIS / CHIRPS / ERA5 via GEE
SUMBER_TEKS = "BPS - judul dan abstrak publikasi (korpus 193 dokumen)"   # TODO: URL / metode pengambilan
SUMBER_GEO = "kejadian Karhutla per kab/kota 2021-2026 + batas wilayah"   # TODO: sebut sumber kejadian & batas wilayah persisnya
TGL_AKSES = "........ 2026"                                              # TODO: tanggal akses data
URL_REPO = "https://github.com/USERNAME/REPO"                            # TODO: URL repositori publik

# --- IKON: taruh file di assets/icons/<nama>.png (atau .svg/.webp). Kalau file tidak ada,
#     otomatis dipakai emoji di bawah. Nama file = kunci di dict ini. ---
IKON = {
    "api": "🔥",        # assets/icons/api.png        -> logo di hero
    "satelit": "🛰️",    # assets/icons/satelit.png    -> Bab 1
    "hutan": "🌲",      # assets/icons/hutan.png      -> Bab 2
    "teks": "📰",       # assets/icons/teks.png       -> Bab 3
    "siaga": "🚨",      # assets/icons/siaga.png      -> Bab 4
    "peta": "🗺️",       # assets/icons/peta.png       -> Bab 5
}

# Menu atas: (id bagian, label menu, keterangan saat kursor di atas menu)
MENU = [
    ("beranda", "Beranda", "Kembali ke awal cerita"),
    ("bab-1", "Multivariat", "Bab 1 · Visualisasi data berdimensi tinggi (PCA, radar, heatmap)"),
    ("bab-2", "Hierarki", "Bab 2 · Visualisasi data hierarki (sunburst, treemap)"),
    ("bab-3", "Teks", "Bab 3 · Visualisasi data teks (word cloud, jaringan kata, tren topik)"),
    ("bab-4", "Provinsi siaga", "Bab 4 · Ringkasan tingkat provinsi"),
    ("bab-5", "Geospasial", "Bab 5 · Visualisasi data geospasial kab/kota (choropleth, simbol proporsional, LISA)"),
]

# Palet ramah buta warna (Okabe-Ito)
OKABE = ["#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7"]
API = "#D55E00"       # vermilion: warna sorotan Kalimantan
NETRAL = "#56B4E9"    # biru langit: provinsi lain
FIRE_SCALE = ["#ffe9a8", "#ffb347", "#ff6b1a", "#c1121f", "#5c0a0a"]  # luminans monoton
DIVERGING = [[0, "#2166ac"], [0.25, "#92c5de"], [0.5, "#f7f7f7"], [0.75, "#f4a582"], [1, "#b2182b"]]

st.set_page_config(page_title=f"{JUDUL} | Karhutla {TAHUN}", page_icon="🔥",
                   layout="wide", initial_sidebar_state="collapsed")

# Kompatibilitas parameter lebar antar-versi Streamlit
STRETCH = {"width": "stretch"}


# =============================================================================
# 1. CSS + ANIMASI API
# =============================================================================
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;500;600&display=swap');
#MainMenu, footer, header[data-testid="stHeader"] {visibility:hidden; height:0;}
.block-container {max-width:1180px; padding-top:4.6rem; padding-bottom:4rem;}
html, [data-testid="stMain"], section.main {scroll-behavior:smooth;}
html, body, [class*="css"] {font-family:'Inter','Segoe UI',sans-serif;}
h1,h2,h3 {font-family:'Bebas Neue','Inter',sans-serif; letter-spacing:.04em;}
.stApp {background:
  radial-gradient(1200px 500px at 50% -10%, rgba(255,107,26,.16), transparent 60%),
  linear-gradient(180deg,#0e0909 0%,#140c0c 60%,#0e0909 100%);}

/* ---------- MENU ATAS (tetap di layar, melompat ke bagian) ---------- */
.topnav {position:fixed; top:0; left:0; right:0; z-index:999990; display:flex; align-items:center; gap:1rem;
  padding:.5rem max(.8rem, calc((100vw - 1180px) / 2)); background:rgba(14,9,9,.9); backdrop-filter:blur(10px);
  border-bottom:1px solid rgba(255,140,60,.28);}
.topnav .brand {font-family:'Bebas Neue','Inter',sans-serif; font-size:1.35rem; letter-spacing:.06em; color:#ffb347 !important;
  text-decoration:none !important; white-space:nowrap;}
.topnav .menu {display:flex; gap:.4rem; overflow-x:auto; scrollbar-width:none; flex:1; justify-content:flex-end;}
.topnav .menu::-webkit-scrollbar {display:none;}
.topnav .menu a {color:#ffd9a8 !important; text-decoration:none !important; font-size:.86rem; white-space:nowrap; padding:.32rem .85rem;
  border-radius:99px; border:1px solid rgba(255,179,71,.3); transition:background .2s, border-color .2s;}
.topnav .menu a:hover {background:rgba(255,107,26,.22);}
.topnav .menu a:focus-visible, .topnav .brand:focus-visible {outline:2px solid #F0E442; outline-offset:2px;}
.topnav .menu a.active {background:#ff6b1a; border-color:#ff6b1a; color:#1a0b0b !important; font-weight:600;}
#beranda, .chapter {scroll-margin-top:76px;}
@media (max-width:640px){ .topnav .brand {display:none;} .topnav {padding:.45rem .6rem;} .topnav .menu {justify-content:flex-start;} }

/* ---------- LEGENDA PETA ---------- */
.maplegend {display:flex; flex-wrap:wrap; align-items:center; gap:.3rem 1rem; margin:.2rem 0 .4rem; font-size:.8rem; color:#e9d8c4;}
.maplegend b {color:#ffb347; font-weight:600;}
.maplegend .lg {display:inline-flex; align-items:center; gap:.35rem; white-space:nowrap;}
.maplegend .lg i {display:inline-block; width:14px; height:14px; border-radius:3px; border:1px solid rgba(255,255,255,.25);}
.maplegend .lg em {display:inline-block; border-radius:50%; background:rgba(86,180,233,.6); border:1px solid rgba(255,255,255,.45);}

/* ---------- HERO ---------- */
.hero {position:relative; overflow:hidden; border-radius:26px; padding:4.2rem 1.6rem 8.5rem;
  background:radial-gradient(900px 380px at 50% 100%, rgba(255,90,0,.55), rgba(120,20,0,.25) 55%, rgba(14,9,9,.0) 80%),
             linear-gradient(180deg,#1a0b0b,#0e0909);
  border:1px solid rgba(255,140,60,.25); box-shadow:0 0 60px rgba(255,90,0,.18) inset;}
.hero-content {position:relative; z-index:3; text-align:center;}
.eyebrow {display:inline-block; font-size:.78rem; letter-spacing:.28em; color:#ffb347; border:1px solid rgba(255,179,71,.4);
  padding:.3rem .9rem; border-radius:99px; background:rgba(255,179,71,.07); animation:fadeUp .9s ease both;}
.hero-title {font-size:clamp(3rem,10vw,7rem); line-height:.95; margin:.6rem 0 .3rem; color:#fff4e0;
  text-shadow:0 0 18px rgba(255,140,40,.8),0 0 50px rgba(255,70,0,.6); animation:fadeUp 1s .1s ease both, glow 2.4s ease-in-out infinite alternate;}
.hero-title span {background:linear-gradient(180deg,#fff2a8,#ff9f1c 45%,#e63946); -webkit-background-clip:text; background-clip:text;
  color:transparent; text-shadow:none; filter:drop-shadow(0 0 14px rgba(255,100,0,.7));}
.hero-sub {max-width:720px; margin:.4rem auto 1.4rem; color:#e9d8c4; font-size:1.08rem; animation:fadeUp 1s .25s ease both;}
.hero .hero-sub {max-width:760px; width:100%; margin:.4rem auto 1.4rem !important; text-align:center !important;}
.hero-logo {font-size:3rem; animation:bob 2.6s ease-in-out infinite;}
.hero-logo img {height:64px; filter:drop-shadow(0 0 14px rgba(255,120,0,.8));}
.kpis {display:flex; flex-wrap:wrap; gap:.8rem; justify-content:center; animation:fadeUp 1s .4s ease both;}
.kpi {min-width:150px; background:rgba(20,10,10,.62); border:1px solid rgba(255,140,60,.3); border-radius:16px; padding:.8rem 1.1rem; backdrop-filter:blur(6px);}
.kpi b {display:block; font-family:'Bebas Neue'; font-size:2.1rem; color:#ffb347; line-height:1.05;}
.kpi small {color:#d9c7b3;}
.nav {display:flex; flex-wrap:wrap; gap:.5rem; justify-content:center; margin-top:1.2rem; animation:fadeUp 1s .55s ease both;}
.nav a {color:#ffd9a8 !important; text-decoration:none !important; font-size:.85rem; padding:.3rem .8rem; border-radius:99px;
  border:1px solid rgba(255,179,71,.35); transition:.25s;}
.nav a:hover {background:rgba(255,107,26,.25); transform:translateY(-2px);}

/* nyala api */
.flames {position:absolute; left:0; right:0; bottom:-14px; height:170px; display:flex; justify-content:space-around; align-items:flex-end;
  z-index:2; filter:blur(7px) saturate(1.3); mix-blend-mode:screen; pointer-events:none;}
.flame {background:linear-gradient(to top,#ff3d00 0%,#ff8c00 45%,#ffd23f 75%,rgba(255,210,63,0) 100%);
  border-radius:50% 50% 45% 45% / 70% 70% 30% 30%; transform-origin:50% 100%; animation:flicker 1.4s ease-in-out infinite alternate;}
@keyframes flicker {0%{transform:scaleY(.82) scaleX(1.05) skewX(-4deg); opacity:.85}
  50%{transform:scaleY(1.08) scaleX(.92) skewX(3deg); opacity:1} 100%{transform:scaleY(.9) scaleX(1) skewX(-2deg); opacity:.9}}
.embers {position:absolute; inset:0; z-index:1; pointer-events:none;}
.ember {position:absolute; bottom:-10px; width:var(--s); height:var(--s); border-radius:50%; background:#ffb347;
  box-shadow:0 0 10px 2px #ff7b00; opacity:0; animation:rise linear infinite;}
@keyframes rise {0%{transform:translate(0,0) scale(1); opacity:0} 10%{opacity:.95}
  100%{transform:translate(var(--dx),-480px) scale(.2); opacity:0}}
@keyframes glow {from{text-shadow:0 0 14px rgba(255,140,40,.7),0 0 40px rgba(255,70,0,.45);} to{text-shadow:0 0 26px rgba(255,170,60,.95),0 0 70px rgba(255,70,0,.75);}}
@keyframes fadeUp {from{opacity:0; transform:translateY(22px);} to{opacity:1; transform:none;}}
@keyframes bob {0%,100%{transform:translateY(0)} 50%{transform:translateY(-8px)}}

/* ---------- BAB ---------- */
.chapter {margin:3.2rem 0 .6rem; padding-left:1rem; border-left:4px solid #ff6b1a; animation:fadeUp .8s ease both;}
.chap-num {font-size:.78rem; letter-spacing:.3em; color:#ff9f1c;}
.chapter h2 {font-size:clamp(2rem,5vw,3.2rem); margin:.1rem 0; color:#fff4e0;}
.chapter h2 img {height:1.1em; vertical-align:-.15em; margin-right:.3rem;}
.chap-kicker {color:#d9c7b3; max-width:820px; margin:.2rem 0 0;}
.story {background:linear-gradient(135deg,rgba(255,107,26,.10),rgba(255,107,26,.02)); border:1px solid rgba(255,140,60,.22);
  border-radius:16px; padding:.9rem 1.1rem; margin:.8rem 0; color:#f0e2d0; line-height:1.65;}
.story b {color:#ffb347;}
.tag {display:inline-block; font-size:.72rem; padding:.15rem .6rem; border-radius:99px; background:rgba(86,180,233,.15);
  border:1px solid rgba(86,180,233,.4); color:#9fd7f5; margin-right:.4rem;}
div[data-testid="stPlotlyChart"] {background:rgba(255,255,255,.015); border:1px solid rgba(255,140,60,.12); border-radius:16px; padding:.3rem;}
.stButton>button {border-radius:99px; border:1px solid rgba(255,140,60,.45); background:rgba(255,107,26,.08);}
.stButton>button:hover {border-color:#ff9f1c; background:rgba(255,107,26,.25);}
.footer {margin-top:3rem; padding:1.2rem; border-top:1px solid rgba(255,140,60,.25); color:#bba998; font-size:.85rem;}

@media (max-width:640px){ .hero{padding:3rem 1rem 7rem;} .kpi{min-width:42%;} .flames{height:120px;} }
@media (prefers-reduced-motion:reduce){ *{animation:none !important;} }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# =============================================================================
# 2. HELPER UMUM
# =============================================================================
def ikon(nama: str, ukuran: int | None = None) -> str:
    """Kembalikan <img> jika assets/icons/<nama>.(png|svg|webp|jpg) ada, selain itu emoji."""
    for ext in ("png", "svg", "webp", "jpg", "jpeg"):
        f = ICON_DIR / f"{nama}.{ext}"
        if f.exists():
            mime = "image/svg+xml" if ext == "svg" else f"image/{'jpeg' if ext in ('jpg','jpeg') else ext}"
            b64 = base64.b64encode(f.read_bytes()).decode()
            style = f' style="height:{ukuran}px"' if ukuran else ""
            return f'<img src="data:{mime};base64,{b64}"{style}/>'
    return IKON.get(nama, "")


def html(s: str):
    """Render HTML satu-baris (hindari blok kode markdown akibat indentasi)."""
    st.markdown(" ".join(line.strip() for line in s.splitlines()), unsafe_allow_html=True)


def bab(no: int, judul: str, kicker: str, nama_ikon: str):
    html(f"""<div class="chapter" id="bab-{no}"><div class="chap-num">BAB {no}</div>
    <h2>{ikon(nama_ikon)} {judul}</h2><p class="chap-kicker">{kicker}</p></div>""")


def cerita(teks: str):
    html(f'<div class="story">{teks}</div>')


def finish(fig, judul=None, tinggi=460, sumber_extra="", y_src=-0.16, legend=True, sumber_teks=None):
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=tinggi, margin=dict(l=10, r=10, t=56 if judul else 18, b=64),
        font=dict(family="Inter, Segoe UI, sans-serif", color="#f3e9dc", size=12),
        title=dict(text=judul, x=0.0, xanchor="left", font=dict(size=16)) if judul else None,
        showlegend=legend, legend=dict(orientation="h", y=1.02, x=1, xanchor="right", yanchor="bottom",
                                       bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor="#1b1212", font_color="#fff4e0"),
    )
    fig.add_annotation(text=sumber_teks or f"Sumber: BPS ({TAHUN}){'; ' + sumber_extra if sumber_extra else ''}",
                       xref="paper", yref="paper", x=0, y=y_src, showarrow=False, xanchor="left",
                       font=dict(size=10, color="#b8a99a"))
    return fig


def minmax(s: pd.Series) -> pd.Series:
    r = s.max() - s.min()
    return (s - s.min()) / r if r else s * 0


# =============================================================================
# 3. DATA
# =============================================================================
PULAU = {
    "Aceh": "Sumatera", "Sumatera Utara": "Sumatera", "Sumatera Barat": "Sumatera", "Riau": "Sumatera",
    "Jambi": "Sumatera", "Sumatera Selatan": "Sumatera", "Bengkulu": "Sumatera", "Lampung": "Sumatera",
    "Kepulauan Bangka Belitung": "Sumatera", "Kepulauan Riau": "Sumatera",
    "DKI Jakarta": "Jawa", "Jawa Barat": "Jawa", "Jawa Tengah": "Jawa", "Daerah Istimewa Yogyakarta": "Jawa",
    "Jawa Timur": "Jawa", "Banten": "Jawa",
    "Bali": "Bali & Nusa Tenggara", "Nusa Tenggara Barat": "Bali & Nusa Tenggara", "Nusa Tenggara Timur": "Bali & Nusa Tenggara",
    "Kalimantan Barat": "Kalimantan", "Kalimantan Tengah": "Kalimantan", "Kalimantan Selatan": "Kalimantan",
    "Kalimantan Timur": "Kalimantan", "Kalimantan Utara": "Kalimantan",
    "Sulawesi Utara": "Sulawesi", "Sulawesi Tengah": "Sulawesi", "Sulawesi Selatan": "Sulawesi",
    "Sulawesi Tenggara": "Sulawesi", "Gorontalo": "Sulawesi", "Sulawesi Barat": "Sulawesi",
    "Maluku": "Maluku", "Maluku Utara": "Maluku",
    "Papua Barat": "Papua", "Papua Barat Daya": "Papua", "Papua": "Papua", "Papua Selatan": "Papua",
    "Papua Tengah": "Papua", "Papua Pegunungan": "Papua",
}
RENAME = {"WADMPR": "prov", "NDVI_avg": "ndvi", "LST_avg_C": "lst", "NBR_avg": "nbr",
          "Curah_Hujan_Total": "hujan", "Kelembapan_RH_avg": "rh", "Tanah Longsor": "longsor",
          "Banjir": "banjir", "Kekeringan": "kering", "Kebakaran Hutan dan Lahan": "karhutla",
          "Cuaca Ekstrem": "cuaca"}
LABEL = {"ndvi": "NDVI", "lst": "LST (°C)", "nbr": "NBR", "hujan": "Curah hujan (mm)", "rh": "Kelembapan RH (%)",
         "longsor": "Tanah longsor", "banjir": "Banjir", "kering": "Kekeringan", "karhutla": "Karhutla",
         "cuaca": "Cuaca ekstrem"}
SAT = ["ndvi", "lst", "nbr", "hujan", "rh"]
BENCANA = ["longsor", "banjir", "kering", "karhutla", "cuaca"]
NUM = SAT + BENCANA


@st.cache_data
def load_prov() -> pd.DataFrame:
    d = pd.read_excel(DATA_PROV).rename(columns=RENAME)
    d["pulau"] = d["prov"].map(PULAU).fillna("Lainnya")
    d["kalimantan"] = d["pulau"].eq("Kalimantan")
    # Indeks Kondisi Rentan (0-100): rata-rata lima indikator "kekeringan" ternormalisasi min-max
    #   LST tinggi, curah hujan rendah, RH rendah, NBR rendah, NDVI rendah (bobot sama)
    comp = pd.concat([minmax(d.lst), 1 - minmax(d.hujan), 1 - minmax(d.rh), 1 - minmax(d.nbr), 1 - minmax(d.ndvi)], axis=1)
    d["indeks"] = comp.mean(axis=1) * 100
    return d


@st.cache_data
def load_teks() -> pd.DataFrame:
    k = pd.read_excel(DATA_TEKS)
    k["tanggal_rilis"] = pd.to_datetime(k["tanggal_rilis"])
    k["tahun"] = k["tanggal_rilis"].dt.year
    k["teks_bersih"] = k["teks_bersih"].fillna("").astype(str)
    k["kata_kunci"] = k["kata_kunci"].fillna("-").astype(str)
    return k


@st.cache_data
def pca_fit(df: pd.DataFrame):
    X = df[NUM].astype(float).copy()
    for c in BENCANA:                       # skala hitung -> log1p agar pencilan tidak mendominasi
        X[c] = np.log1p(X[c])
    Z = StandardScaler().fit_transform(X)
    p = PCA(n_components=2, random_state=0).fit(Z)
    sc = p.transform(Z)
    return sc, p.explained_variance_ratio_, p.components_.T   # skor, varians, loading (10 x 2)


df = load_prov()
corpus = load_teks()


# =============================================================================
# 4. MENU ATAS + HERO
# =============================================================================
# Skrip kecil: klik menu -> gulir mulus ke bagian itu; menu yang sedang dibaca ditandai (scroll-spy).
# Dipasang lewat st.html(unsafe_allow_javascript=True). Jika versi Streamlit lama tidak mendukung,
# menu tetap berfungsi lewat tautan jangkar (href="#bab-N") + CSS scroll-behavior.
NAV_JS = """
<script>
(function () {
  var IDS = %s;
  if (window.__karhutlaNav) { window.__karhutlaNav.refresh(); return; }
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var last = null;

  function section(id) {            // cadangan jika atribut id disaring oleh renderer markdown
    var el = document.getElementById(id);
    if (el) return el;
    if (id === 'beranda') return document.querySelector('.hero');
    var n = id.replace('bab-', '').trim(), hs = document.querySelectorAll('.chapter');
    for (var i = 0; i < hs.length; i++) {
      var c = hs[i].querySelector('.chap-num');
      if (c && c.textContent.replace(/\\s+/g, ' ').trim() === 'BAB ' + n) return hs[i];
    }
    return null;
  }
  function setActive(id) {
    if (id === last) return;
    last = id;
    document.querySelectorAll('.topnav .menu a').forEach(function (a) {
      var on = a.getAttribute('data-target') === id;
      a.classList.toggle('active', on);
      if (on) {
        a.setAttribute('aria-current', 'true');
        var m = a.parentElement;
        if (m && m.scrollWidth > m.clientWidth) m.scrollTo({left: a.offsetLeft - m.clientWidth / 2 + a.clientWidth / 2, behavior: 'smooth'});
      } else { a.removeAttribute('aria-current'); }
    });
  }
  function spy() {
    var cur = IDS[0];
    for (var i = 0; i < IDS.length; i++) {
      var el = section(IDS[i]);
      if (el && el.getBoundingClientRect().top <= 150) cur = IDS[i];
    }
    setActive(cur);
  }
  var tick = false;
  document.addEventListener('scroll', function () {
    if (tick) return; tick = true;
    requestAnimationFrame(function () { tick = false; spy(); });
  }, true);
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('.topnav a[data-target]');
    if (!a) return;
    var el = section(a.getAttribute('data-target'));
    if (!el) return;
    e.preventDefault();
    el.scrollIntoView({behavior: reduce ? 'auto' : 'smooth', block: 'start'});
    setActive(a.getAttribute('data-target'));
  });
  window.__karhutlaNav = {refresh: function () { last = null; spy(); }};
  spy();
})();
</script>
""" % str([m[0] for m in MENU])


def topnav():
    links = "".join(f'<a href="#{i}" data-target="{i}" title="{tip}">{lab}</a>' for i, lab, tip in MENU)
    html(f"""<nav class="topnav" aria-label="Navigasi cerita">
      <a class="brand" href="#beranda" data-target="beranda">🔥 Titik Api</a>
      <div class="menu">{links}</div></nav>""")
    try:
        st.html(NAV_JS, unsafe_allow_javascript=True)
    except TypeError:
        pass


def hero():
    rnd = random.Random(11)
    flames = "".join(
        f'<div class="flame" style="width:{rnd.randint(60,110)}px;height:{rnd.randint(80,170)}px;'
        f'animation-duration:{rnd.uniform(0.9,2.1):.2f}s;animation-delay:-{rnd.uniform(0,2):.2f}s"></div>'
        for _ in range(18))
    embers = "".join(
        f'<span class="ember" style="left:{rnd.randint(2,98)}%;--s:{rnd.uniform(2,6):.1f}px;--dx:{rnd.randint(-70,70)}px;'
        f'animation-duration:{rnd.uniform(4,9):.1f}s;animation-delay:-{rnd.uniform(0,9):.1f}s"></span>'
        for _ in range(46))
    tot = int(df.karhutla.sum())
    top = df.loc[df.karhutla.idxmax()]
    share_sk = df[df.pulau.isin(["Sumatera", "Kalimantan"])].karhutla.sum() / tot * 100
    html(f"""
    <div class="hero" id="beranda">
      <div class="embers">{embers}</div>
      <div class="hero-content">
        <div class="hero-logo">{ikon('api')}</div>
        <div class="eyebrow">DATA STORYTELLING &nbsp;•&nbsp; KARHUTLA {TAHUN}</div>
        <h1 class="hero-title">TITIK API <span>NUSANTARA</span></h1>
        <p class="hero-sub">{SUBJUDUL} Dari panas yang terekam di angkasa, rekam jejak bencana di atas tanah, hingga makna yang tersembunyi dalam publikasi resmi BPS, ini adalah narasi data tentang kerentanan 38 provinsi di Indonesia, sebuah kompas untuk menebak arah datangnya titik api.</p>
        <div class="kpis">
          <div class="kpi"><b>{tot:,}</b><small>kejadian Karhutla {TAHUN}</small></div>
          <div class="kpi"><b>{top.prov}</b><small>provinsi tertinggi ({int(top.karhutla)} kejadian)</small></div>
          <div class="kpi"><b>{share_sk:.0f}%</b><small>terjadi di Sumatera + Kalimantan</small></div>
          <div class="kpi"><b>{len(df)}</b><small>provinsi &bull; {len(NUM)} variabel</small></div>
        </div>
      </div>
      <div class="flames">{flames}</div>
    </div>""")


topnav()
hero()


# =============================================================================
# 5. BAB 1 - DATA BERDIMENSI TINGGI (PCA + RADAR + HEATMAP, brushing & linking)
# =============================================================================
bab(1, "PETA KERENTANAN",
    "Mengekstraksi sepuluh variabel, lima indikator satelit dan lima jenis bencana, ke dalam dua dimensi utama. "
    "Jarak antarprovinsi pada peta ini menyingkap kemiripan profil ekologi dan kerentanannya. "
    "Gunakan fitur lasso atau blok titik di bawah untuk melihat bagaimana grafik radar dan matriks korelasi "
    "mengungkap detailnya secara dinamis.", "satelit")

if "reset" not in st.session_state:
    st.session_state.reset = 0

scores, evr, load = pca_fit(df)
df["pc1"], df["pc2"] = scores[:, 0], scores[:, 1]

# Baris kontrol: kiri = pengaturan PCA, kanan = pemilihan provinsi untuk radar
ctl_l, ctl_r = st.columns([1.1, 1])
with ctl_l:
    k1, k2 = st.columns([1.5, 1])
    biplot = k1.toggle("Tampilkan panah variabel (biplot)", value=False)
    if k2.button("↺ Reset pilihan", use_container_width=True):
        st.session_state.reset += 1
        st.rerun()
with ctl_r:
    manual = st.multiselect("Provinsi untuk dibandingkan di radar", df.prov.tolist(), key=f"manual_{st.session_state.reset}",
                            placeholder="Pilih provinsi untuk radar (atau blok di PCA)…", label_visibility="collapsed")

TINGGI = 560
col_a, col_b = st.columns([1.1, 1])
SINGKAT = {"ndvi": "NDVI", "lst": "LST", "nbr": "NBR", "hujan": "Hujan", "rh": "RH", "longsor": "Longsor",
           "banjir": "Banjir", "kering": "Kering", "karhutla": "Karhutla", "cuaca": "Cuaca"}


def rgba(hex_, a):
    h = hex_.lstrip("#")
    return f"rgba({int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)},{a})"


with col_a:
    ukuran = 8 + np.sqrt(df.karhutla) * 1.5
    teratas = list(df.nlargest(6, "karhutla").index)
    posisi = ["top center"] * len(df)
    for r, i in enumerate(teratas):                       # selang-seling agar label tidak bertabrakan
        posisi[i] = ["top center", "bottom center", "middle right", "middle left", "top center", "bottom center"][r]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.pc1, y=df.pc2, mode="markers+text", text=[p if i in teratas else "" for i, p in zip(df.index, df.prov)],
        textposition=posisi, textfont=dict(size=10, color="#f3e9dc"), cliponaxis=False,
        marker=dict(size=ukuran, color=NETRAL, line=dict(width=1, color="#140d0d"), opacity=0.9),
        customdata=np.c_[df.prov, df.pulau, df.karhutla, df.indeks.round(1)],
        hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<br>Karhutla: %{customdata[2]} kejadian"
                      "<br>Indeks kondisi rentan: %{customdata[3]}<extra></extra>",
        selected=dict(marker=dict(opacity=1, color=API)), unselected=dict(marker=dict(opacity=0.3))))
    xs, ys = df.pc1.abs().max(), df.pc2.abs().max()
    xr, yr = [-xs * 1.15, xs * 1.15], [-ys * 1.2, ys * 1.2]
    if biplot:
        sk = 0.85 * min(xs / np.abs(load[:, 0]).max(), ys / np.abs(load[:, 1]).max())
        for i, v in enumerate(NUM):
            tx, ty = load[i, 0] * sk, load[i, 1] * sk
            fig.add_annotation(x=tx, y=ty, ax=0, ay=0, xref="x", yref="y", axref="x", ayref="y", showarrow=True,
                               arrowhead=2, arrowsize=0.9, arrowwidth=1, arrowcolor="rgba(240,228,66,.7)", text="")
            fig.add_annotation(x=tx, y=ty, text=SINGKAT[v], showarrow=False, font=dict(size=9, color="#F0E442"),
                               xanchor="left" if tx >= 0 else "right", yanchor="bottom" if ty >= 0 else "top",
                               xshift=4 if tx >= 0 else -4)
    fig.update_xaxes(title=dict(text=f"PC1 ({evr[0]*100:.1f}% varians)", standoff=8), range=xr, zeroline=True,
                     zerolinecolor="rgba(255,255,255,.18)", gridcolor="rgba(255,255,255,.05)")
    fig.update_yaxes(title=dict(text=f"PC2 ({evr[1]*100:.1f}% varians)", standoff=8), range=yr, zeroline=True,
                     zerolinecolor="rgba(255,255,255,.18)", gridcolor="rgba(255,255,255,.05)")
    fig.update_layout(dragmode="lasso")
    finish(fig, "PCA: kemiripan profil 38 provinsi", TINGGI, "ukuran titik = jumlah kejadian Karhutla", -0.2, legend=False)
    fig.update_layout(margin=dict(l=10, r=10, t=56, b=90))
    ev = st.plotly_chart(fig, key=f"pca_{st.session_state.reset}", on_select="rerun",
                         selection_mode=("lasso", "box", "points"), **STRETCH)

picked = set()
try:
    pts = ev["selection"]["points"]
    picked |= {int(p["point_index"]) for p in pts if int(p.get("curve_number", 0)) == 0}
except Exception:
    pass
picked |= set(df.index[df.prov.isin(manual)])
sel = df.loc[sorted(picked)] if picked else df.iloc[0:0]

# ---------- RADAR ----------
with col_b:
    RADAR_WARNA = [API, "#F0E442", "#009E73", "#CC79A7", "#56B4E9", "#0072B2"]
    RADAR = [("lst", "LST<br>tinggi", False), ("ndvi", "NDVI<br>terbalik", True), ("hujan", "Hujan<br>rendah", True),
             ("karhutla", "Kejadian<br>Karhutla", False), ("kering", "Kekeringan", False)]
    rn = pd.DataFrame({lab: (1 - minmax(df[c]) if inv else minmax(df[c])) for c, lab, inv in RADAR})
    labels = list(rn.columns)
    nasional = rn.mean()
    fokus = sel if len(sel) else df[df.kalimantan]
    judul_fokus = "provinsi terpilih" if len(sel) else "Kalimantan"
    figr = go.Figure()
    figr.add_trace(go.Scatterpolar(r=list(nasional) + [nasional.iloc[0]], theta=labels + [labels[0]], name="Rata-rata nasional",
                                   line=dict(color="#f3e9dc", dash="dash", width=2), fill="toself", fillcolor="rgba(243,233,220,.08)",
                                   hovertemplate="%{theta}: %{r:.2f}<extra>Nasional</extra>"))
    if len(fokus) <= 6:      # perbandingan per provinsi: garis saja agar tidak saling menimpa
        for i, (ix, rw) in enumerate(fokus.iterrows()):
            vals = rn.loc[ix]
            figr.add_trace(go.Scatterpolar(r=list(vals) + [vals.iloc[0]], theta=labels + [labels[0]], name=rw.prov,
                                           mode="lines+markers", marker=dict(size=5),
                                           line=dict(color=RADAR_WARNA[i % len(RADAR_WARNA)], width=2.2),
                                           hovertemplate="%{theta}: %{r:.2f}<extra>" + rw.prov + "</extra>"))
    else:
        vals = rn.loc[fokus.index].mean()
        figr.add_trace(go.Scatterpolar(r=list(vals) + [vals.iloc[0]], theta=labels + [labels[0]], name=f"Rata-rata {len(fokus)} provinsi",
                                       line=dict(color=API, width=2.6), fill="toself", fillcolor=rgba(API, 0.25),
                                       hovertemplate="%{theta}: %{r:.2f}<extra>Rata-rata terpilih</extra>"))
    figr.update_layout(polar=dict(bgcolor="rgba(0,0,0,0)", domain=dict(x=[0.12, 0.88], y=[0.2, 0.9]),
                                 radialaxis=dict(range=[0, 1], tickvals=[0.25, 0.5, 0.75, 1], tickfont=dict(size=9, color="#b8a99a"),
                                                 gridcolor="rgba(255,255,255,.12)", angle=90),
                                 angularaxis=dict(gridcolor="rgba(255,255,255,.12)", tickfont=dict(size=11))))
    finish(figr, f"Radar profil: {judul_fokus} vs nasional", TINGGI,
           "skala 0-1; NDVI dan hujan dibalik sehingga makin ke luar = makin kering", -0.2)
    figr.update_layout(margin=dict(l=10, r=10, t=56, b=90),
                       legend=dict(orientation="h", x=0.5, xanchor="center", y=0.1, yanchor="top", bgcolor="rgba(0,0,0,0)"))
    st.plotly_chart(figr, key="radar", **STRETCH)

# ---------- HEATMAP BERKLASTER ----------
def order(M: np.ndarray) -> list[int]:
    return list(leaves_list(linkage(M, "average"))) if len(M) > 2 else list(range(len(M)))


use_sub = len(sel) >= 5
base = sel if use_sub else df
C = base[SAT + BENCANA].corr(method="spearman").loc[SAT, BENCANA].fillna(0)
ro, co = order(C.values), order(C.values.T)
Cs = C.iloc[ro, co]
fh = go.Figure(go.Heatmap(z=Cs.values, x=[LABEL[c] for c in Cs.columns], y=[LABEL[r] for r in Cs.index],
                          zmin=-1, zmax=1, colorscale=DIVERGING, text=np.round(Cs.values, 2), texttemplate="%{text}",
                          colorbar=dict(title="ρ Spearman", thickness=12),
                          hovertemplate="%{y} × %{x}<br>ρ = %{z:.2f}<extra></extra>"))
cakupan = f"{len(sel)} provinsi terpilih" if use_sub else "38 provinsi"
finish(fh, f"Heatmap berklaster: korelasi satelit × bencana ({cakupan})", 400, "korelasi peringkat Spearman; baris/kolom diurutkan dengan klaster hierarkis", -0.2, legend=False)
st.plotly_chart(fh, key="heat", **STRETCH)
if 0 < len(sel) < 5:
    st.caption("Pilih minimal 5 provinsi agar korelasi dihitung ulang untuk subset; kurang dari itu heatmap tetap menampilkan seluruh provinsi.")

# ---------- Narasi dinamis ----------
rho = df[NUM].corr(method="spearman")["karhutla"].drop("karhutla")
kuat = rho.abs().sort_values(ascending=False).index[0]
kal = df[df.kalimantan]
cerita(
    f"<b>Di balik titik dan garis korelasi:</b> Peta dua dimensi ini menyingkap <b>{evr.sum()*100:.0f}%</b> rahasia dari data kita. "
    f"Api nyatanya paling cepat menyala saat kelembapan udara terkikis (ρ = {rho['rh']:.2f}) dan panas permukaan memuncak "
    f"(ρ = {rho['lst']:.2f}). Namun, cuaca seolah mengelabui kita. Kalimantan adalah bukti nyatanya: meski indeks kerentanan "
    f"iklimnya tergolong rendah di angka {kal.indeks.mean():.0f} (di bawah rata-rata nasional {df.indeks.mean():.0f}), "
    f"kelima provinsinya justru membara dengan rata-rata {kal.karhutla.mean():.0f} kejadian Karhutla. Anomali tajam ini "
    f"menegaskan bahwa suhu dan cuaca hanyalah pemantik; bahan bakar utamanya diduga kuat berasal dari jenis lahan dan "
    f"jejak aktivitas manusia."
)


# =============================================================================
# 6. BAB 2 - DATA BERHIERARKI (SUNBURST + TREEMAP, drill-down + breadcrumb)
# =============================================================================
bab(2, "ANATOMI BENCANA",
    "Membedah anatomi bencana lapis demi lapis: dari skala nasional, mengerucut ke pulau, provinsi, hingga jenis insidennya. "
    "Luas bidang merepresentasikan frekuensi kejadian, sementara intensitas warna merah menyingkap persentase Karhutla.", "hutan")


@st.cache_data
def build_tree(d: pd.DataFrame):
    names = {"longsor": "Tanah longsor", "banjir": "Banjir", "kering": "Kekeringan", "karhutla": "Karhutla", "cuaca": "Cuaca ekstrem"}
    d = d.copy()
    d["total"] = d[BENCANA].sum(axis=1)
    rows = []
    tot, kar = d.total.sum(), d.karhutla.sum()
    rows.append(("ID", "Indonesia", "", tot, kar / tot * 100, kar))
    for pl, g in d.groupby("pulau"):
        rows.append((f"P|{pl}", pl, "ID", g.total.sum(), g.karhutla.sum() / g.total.sum() * 100, g.karhutla.sum()))
        for _, r in g.iterrows():
            rt = r.karhutla / r.total * 100 if r.total else 0
            rows.append((f"V|{r.prov}", r.prov, f"P|{pl}", r.total, rt, r.karhutla))
            for b in BENCANA:
                if r[b] > 0:
                    rows.append((f"L|{r.prov}|{b}", names[b], f"V|{r.prov}", r[b], rt, r.karhutla))
    t = pd.DataFrame(rows, columns=["id", "label", "parent", "value", "rasio", "karhutla"])
    return t


tree = build_tree(df)
if "path" not in st.session_state:
    st.session_state.path = []
path = st.session_state.path

# --- breadcrumb ---
crumbs = ["Indonesia"] + path
with st.container(horizontal=True, gap="small", key="crumbbar"):
    for i, nm in enumerate(crumbs):
        if st.button(("🔥 " if i == 0 else "› ") + nm, key=f"crumb_{i}_{nm}"):
            st.session_state.path = path[:i]
            st.rerun()

# --- pilihan anak (drill-down) ---
if len(path) == 0:
    anak = sorted(df.pulau.unique())
elif len(path) == 1:
    anak = df[df.pulau == path[0]].prov.tolist()
else:
    anak = []
if anak:
    st.caption("Telusuri rekam jejak di:")
    with st.container(horizontal=True, gap="small", key="drillbar"):
        for nm in anak:
            if st.button(nm, key=f"go_{len(path)}_{nm}"):
                st.session_state.path = path + [nm]
                st.rerun()
else:
    st.caption("Level terdalam: rincian jenis bencana. Klik breadcrumb di atas untuk kembali.")

level_id = None
if len(path) == 1:
    level_id = f"P|{path[0]}"
elif len(path) == 2:
    level_id = f"V|{path[1]}"

cmax = float(np.ceil(tree[tree.id.str.startswith("V|")].rasio.max() / 5) * 5)


def tree_kwargs():
    return dict(ids=tree.id, labels=tree.label, parents=tree.parent, values=tree.value, branchvalues="total",
                customdata=np.c_[tree.karhutla, tree.rasio],
                marker=dict(colors=tree.rasio, colorscale=FIRE_SCALE, cmin=0, cmax=cmax, line=dict(color="#2a1d1d", width=1.2),
                            colorbar=dict(title="% Karhutla", thickness=12, ticksuffix="%")),
                hovertemplate="<b>%{label}</b><br>Kejadian: %{value:,.0f}<br>Karhutla wilayah ini: %{customdata[0]:,.0f} "
                              "(%{customdata[1]:.1f}% dari total bencana)<extra></extra>")


h1, h2 = st.columns(2)
with h1:
    fs = go.Figure(go.Sunburst(level=level_id, maxdepth=3, insidetextorientation="radial", **tree_kwargs()))
    finish(fs, "Sunburst: proporsi bencana", 520, "ukuran = jumlah kejadian; warna = % Karhutla", -0.1, legend=False)
    st.plotly_chart(fs, key=f"sun_{len(path)}_{'_'.join(path)}", **STRETCH)
with h2:
    ft = go.Figure(go.Treemap(level=level_id, pathbar=dict(visible=False), textinfo="label+value",
                              tiling=dict(pad=2), **tree_kwargs()))
    finish(ft, "Treemap: membandingkan besaran", 520, "ukuran = jumlah kejadian; warna = % Karhutla", -0.1, legend=False)
    st.plotly_chart(ft, key=f"tm_{len(path)}_{'_'.join(path)}", **STRETCH)

prov_tot = df.assign(total=df[BENCANA].sum(axis=1))
prov_tot["rasio"] = prov_tot.karhutla / prov_tot.total * 100
tp = prov_tot.sort_values("rasio", ascending=False).iloc[0]
tk = prov_tot.sort_values("karhutla", ascending=False).iloc[0]
cerita(
    f"<b>Siapa yang paling \"terbakar\"?</b> Secara jumlah, <b>{tk.prov}</b> memimpin dengan {int(tk.karhutla)} kejadian Karhutla "
    f"({tk.rasio:.0f}% dari seluruh bencana di sana). Secara proporsi, <b>{tp.prov}</b> paling didominasi api "
    f"({tp.rasio:.0f}%). Pulau Jawa sebaliknya didominasi banjir dan cuaca ekstrem, sehingga warnanya tetap kuning pucat "
    f"meskipun total kejadiannya besar. Ukuran dan warna sengaja memetakan dua hal berbeda: <i>seberapa sering</i> bencana "
    f"terjadi, dan <i>seberapa besar porsi api</i> di dalamnya."
)


# =============================================================================
# 7. BAB 3 - DATA TEKS (WORD CLOUD + KO-OKURENSI + TREN TOPIK)
# =============================================================================
bab(3, "SUARA DOKUMEN BPS", f"{len(corpus)} judul dan abstrak publikasi BPS bertema lingkungan, kehutanan, dan kebencanaan "
    "(sudah dibersihkan: case folding, tokenisasi, stopword, stemming). Apa yang sebenarnya dibicarakan, dan sejak kapan?", "teks")

UMUM = {"indonesia", "saji", "hasil", "informasi", "manfaat", "muat", "booklet", "tuju", "harap", "guna", "cakup",
        "susun", "lengkap", "jelas", "gambar", "lanjut", "dasar", "bangun", "kait", "sumber", "usaha", "kerja",
        "kembang", "olah", "tingkat", "banding", "perintah", "giat", "peran", "sosial", "ekonomi"}

f1, f2, f3 = st.columns([1.4, 1.6, 1])
tmin, tmax = int(corpus.tahun.min()), int(corpus.tahun.max())
with f1:
    rentang = st.slider("Periode rilis", tmin, tmax, (tmin, tmax))
with f2:
    temas = sorted(corpus.kata_kunci.unique())
    tema_pilih = st.multiselect("Tema (kata kunci dokumen)", temas, default=temas)
with f3:
    sembunyi = st.checkbox("Sembunyikan kata umum publikasi", value=True)

sub = corpus[corpus.tahun.between(*rentang) & corpus.kata_kunci.isin(tema_pilih)].copy()
stop = UMUM if sembunyi else set()
tok = [[w for w in t.split() if len(w) >= 3 and w not in stop] for t in sub.teks_bersih]

if len(sub) < 10:
    st.warning("Dokumen terlalu sedikit untuk dianalisis. Longgarkan filter periode / tema.")
else:
    t1, t2 = st.columns(2)
    # ---------- Word cloud ----------
    with t1:
        freq = collections.Counter(w for d in tok for w in d)
        cmap = LinearSegmentedColormap.from_list("api", ["#ffd166", "#ff9f1c", "#ff5d1f", "#ff8a80"])
        wc = WordCloud(width=1000, height=640, mode="RGBA", background_color=None, colormap=cmap, max_words=70,
                       prefer_horizontal=0.92, random_state=7).generate_from_frequencies(freq)
        st.markdown(f"**Word cloud** &nbsp;<span class='tag'>{len(sub)} dokumen</span>", unsafe_allow_html=True)
        st.image(wc.to_array(), **STRETCH)
        st.caption(f"Ukuran kata = frekuensi pada {len(sub)} dokumen. Sumber: BPS ({SUMBER_TEKS}).")

    # ---------- Ko-okurensi ----------
    with t2:
        dfreq = collections.Counter(w for d in tok for w in set(d))
        vocab = {w for w, c in dfreq.items() if c >= 3}
        pair = collections.Counter()
        for d in tok:
            ws = sorted(set(d) & vocab)
            pair.update(itertools.combinations(ws, 2))
        kandidat = [w for w in ["hutan", "lahan", "bencana", "iklim", "emisi", "kalimantan", "lingkung"] if w in vocab]
        kandidat += [w for w, _ in dfreq.most_common(15) if w not in kandidat]
        a, b = st.columns([1.2, 1])
        fokus_kata = a.selectbox("Kata fokus", kandidat, index=0)
        k_nb = b.slider("Jumlah tetangga", 5, 20, 12)
        nb = sorted(((p[1] if p[0] == fokus_kata else p[0], c) for p, c in pair.items() if fokus_kata in p), key=lambda x: -x[1])[:k_nb]
        nodes = [fokus_kata] + [n for n, _ in nb]
        G = nx.Graph()
        G.add_nodes_from(nodes)
        for (u, v), c in pair.items():
            if u in nodes and v in nodes and c >= 2:
                G.add_edge(u, v, weight=c)
        if G.number_of_edges() == 0:
            st.info("Tidak ada pasangan kata yang cukup sering muncul bersama. Coba kata fokus lain.")
        else:
            pos = nx.spring_layout(G, weight="weight", seed=7, k=0.9)
            comm = {n: i for i, cset in enumerate(nx.community.greedy_modularity_communities(G, weight="weight")) for n in cset}
            wmax = max(d["weight"] for *_, d in G.edges(data=True))
            fg = go.Figure()
            for u, v, d in G.edges(data=True):
                fg.add_trace(go.Scatter(x=[pos[u][0], pos[v][0]], y=[pos[u][1], pos[v][1]], mode="lines", hoverinfo="skip",
                                        line=dict(width=0.6 + 4.5 * d["weight"] / wmax, color="rgba(255,179,71,.35)"), showlegend=False))
            deg = dict(G.degree(weight="weight"))
            fg.add_trace(go.Scatter(
                x=[pos[n][0] for n in G], y=[pos[n][1] for n in G], mode="markers+text", text=list(G.nodes), textposition="top center",
                textfont=dict(size=11, color="#fff4e0"), showlegend=False,
                marker=dict(size=[34 if n == fokus_kata else 12 + 22 * deg[n] / max(deg.values()) for n in G],
                            color=[API if n == fokus_kata else OKABE[(comm[n] + 1) % 7] for n in G],
                            line=dict(width=1, color="#140d0d")),
                customdata=[deg[n] for n in G], hovertemplate="<b>%{text}</b><br>Bobot ko-okurensi: %{customdata}<extra></extra>"))
            fg.update_xaxes(visible=False)
            fg.update_yaxes(visible=False)
            finish(fg, f"Jaringan ko-okurensi: \"{fokus_kata}\"", 470,
                   "ukuran = bobot koneksi; warna = komunitas; tebal garis = frekuensi muncul bersama", -0.05, legend=False)
            st.plotly_chart(fg, key="net", **STRETCH)

    # ---------- Tren topik ----------
    @st.cache_data
    def lda_run(teks: tuple, k: int, stopw: tuple):
        cv = CountVectorizer(min_df=3, max_df=0.7, token_pattern=r"(?u)\b[a-z]{3,}\b", stop_words=list(stopw))
        X = cv.fit_transform(teks)
        lda = LatentDirichletAllocation(n_components=k, random_state=42, learning_method="batch", max_iter=60).fit(X)
        terms = np.array(cv.get_feature_names_out())
        lab = [", ".join(terms[np.argsort(c)[::-1][:4]]) for c in lda.components_]
        return lda.transform(X), lab

    k_top = st.slider("Jumlah topik (LDA)", 3, 6, 4)
    dt, tlabel = lda_run(tuple(sub.teks_bersih), k_top, tuple(sorted(stop)))
    sub["topik"] = dt.argmax(axis=1)
    thn = list(range(rentang[0], rentang[1] + 1))
    ct = sub.groupby(["tahun", "topik"]).size().unstack(fill_value=0).reindex(thn, fill_value=0)
    fb = go.Figure()
    for k in range(k_top):
        y = ct[k] if k in ct.columns else [0] * len(thn)
        fb.add_trace(go.Bar(x=thn, y=y, name=f"T{k+1}: {tlabel[k]}", marker_color=OKABE[[1, 5, 2, 0, 6, 4][k]],
                            hovertemplate="%{x}<br>%{y} dokumen<extra>T" + str(k + 1) + "</extra>"))
    fb.update_layout(barmode="stack", legend=dict(orientation="h", y=-0.28, x=0, xanchor="left", yanchor="top"))
    fb.update_yaxes(title="Jumlah publikasi", gridcolor="rgba(255,255,255,.06)")
    fb.update_xaxes(title="Tahun rilis", dtick=2)
    finish(fb, "Tren topik publikasi BPS (topic modeling LDA)", 480, "topik = topik dominan tiap dokumen", -0.42)
    st.plotly_chart(fb, key="trend", **STRETCH)

    n_bakar = int(sub.teks_bersih.str.contains(r"\bbakar\b|\bkarhutla\b|\bapi\b").sum())
    puncak = int(sub.tahun.value_counts().idxmax())
    pct_baru = (sub.tahun >= 2019).mean() * 100
    cerita(
        f"<b>Temuan penting:</b> dari {len(sub)} dokumen terpilih, hanya <b>{n_bakar}</b> yang menyinggung kata terkait kebakaran "
        f"secara langsung. BPS membahas Karhutla secara <i>tidak langsung</i>, lewat tema hutan, lahan, iklim, emisi, dan kebencanaan. "
        f"Jumlah publikasi memuncak pada <b>{puncak}</b>, dan <b>{pct_baru:.0f}%</b> dokumen terpilih dirilis sejak 2019. "
        f"Celah ini menjadi alasan mengapa analisis berbasis citra satelit dan data kejadian (Bab 1 dan 2) layak melengkapi "
        f"publikasi resmi."
    )


# =============================================================================
# 8. BAB 4 - PROVINSI SIAGA (KESIMPULAN)
# =============================================================================
bab(4, "PROVINSI SIAGA", "Indeks Kondisi Rentan (0-100) merangkum lima indikator kekeringan: LST tinggi, hujan rendah, "
    "kelembapan rendah, NBR rendah, NDVI rendah. Bandingkan dengan kejadian Karhutla yang benar-benar tercatat.", "siaga")

ex = st.checkbox("Kecualikan DKI Jakarta (suhu tinggi karena wilayah perkotaan, bukan lahan vegetasi)", value=True)
dd = df[df.prov != "DKI Jakarta"] if ex else df
b1, b2 = st.columns([1, 1.2])
with b1:
    top = dd.sort_values("indeks", ascending=False).head(10).iloc[::-1]
    fr = go.Figure(go.Bar(x=top.indeks, y=top.prov, orientation="h",
                          marker=dict(color=top.indeks, colorscale=FIRE_SCALE, cmin=0, cmax=100),
                          text=top.indeks.round(0).astype(int), textposition="outside",
                          customdata=top.karhutla, hovertemplate="<b>%{y}</b><br>Indeks: %{x:.1f}<br>Karhutla: %{customdata} kejadian<extra></extra>"))
    fr.update_xaxes(range=[0, 105], title="Indeks kondisi rentan", gridcolor="rgba(255,255,255,.06)")
    finish(fr, "10 provinsi dengan kondisi paling rentan", 480, "indeks = rata-rata 5 indikator ternormalisasi", -0.14, legend=False)
    st.plotly_chart(fr, key="rank", **STRETCH)
with b2:
    mx, my = dd.indeks.median(), dd.karhutla.median()
    fq = go.Figure(go.Scatter(
        x=dd.indeks, y=dd.karhutla, mode="markers+text", text=np.where((dd.karhutla >= 75) | (dd.indeks >= 52), dd.prov, ""),
        textposition="top center", textfont=dict(size=10),
        marker=dict(size=12, color=np.where(dd.kalimantan, API, NETRAL), line=dict(width=1, color="#140d0d")),
        customdata=dd.prov, hovertemplate="<b>%{customdata}</b><br>Indeks: %{x:.1f}<br>Karhutla: %{y}<extra></extra>"))
    fq.add_vline(x=mx, line_dash="dot", line_color="rgba(255,255,255,.35)")
    fq.add_hline(y=my, line_dash="dot", line_color="rgba(255,255,255,.35)")
    fq.add_annotation(x=dd.indeks.max(), y=dd.karhutla.max(), text="SIAGA: rentan & sering terbakar", showarrow=False, xanchor="right", font=dict(color="#ffb347", size=11))
    fq.add_annotation(x=dd.indeks.max(), y=0, text="WASPADA: rentan, belum banyak tercatat", showarrow=False, xanchor="right", yanchor="bottom", font=dict(color="#9fd7f5", size=11))
    fq.update_xaxes(title="Indeks kondisi rentan (satelit)", gridcolor="rgba(255,255,255,.05)")
    fq.update_yaxes(title="Kejadian Karhutla tercatat", gridcolor="rgba(255,255,255,.05)")
    finish(fq, "Potensi vs kejadian", 480, "garis putus-putus = median; oranye = Kalimantan", -0.17, legend=False)
    st.plotly_chart(fq, key="quad", **STRETCH)

waspada = dd[(dd.indeks >= mx) & (dd.karhutla <= my)].sort_values("indeks", ascending=False).head(3).prov.tolist()
siaga = dd[(dd.indeks >= mx) & (dd.karhutla > my)].sort_values("karhutla", ascending=False).head(3).prov.tolist()
cerita(
    f"<b>Kesimpulan tingkat provinsi.</b> Provinsi yang sudah menunjukkan kombinasi kondisi rentan dan kejadian tinggi (<b>siaga</b>) antara lain "
    f"{', '.join(siaga) if siaga else '-'}. Provinsi yang kondisi satelitnya mirip tetapi belum banyak mencatat Karhutla "
    f"(<b>waspada</b>) antara lain {', '.join(waspada) if waspada else '-'}. Perlu dicatat, indeks ini hanyalah ringkasan sederhana "
    f"dari kondisi kekeringan, bukan model prediksi. Riau dan Kalimantan Selatan, misalnya, mencatat kejadian sangat tinggi "
    f"tanpa indeks yang ekstrem, sehingga data tutupan lahan, tipe tanah gambut, dan titik panas harian akan menjadi langkah lanjutan yang wajar. "
    f"Namun provinsi hanyalah rata-rata dari puluhan kab/kota. Bab 5 turun ke tingkat kab/kota untuk melihat di mana api benar-benar mengelompok."
)


# =============================================================================
# 9. BAB 5 - DATA GEOSPASIAL (choropleth + lingkaran proporsional + klaster LISA)
# =============================================================================
bab(5, "PETA KAB/KOTA", "Bab 1-4 membaca provinsi. Di sini 514 kab/kota diperiksa satu per satu: di mana kejadian Karhutla "
    "paling padat per luas wilayah, di mana jumlahnya terbanyak, dan di mana api mengelompok secara spasial (klaster LISA).", "peta")


@st.cache_resource
def load_geo_cached():
    return load_geo(DATA_GEO)


gdf, GEO, PBOX = load_geo_cached()
esc = _html.escape
PERIODE = {"2021–2026": "all", **{str(y): y for y in YEARS}}


def src_geo(extra: str = "") -> str:
    return f"Sumber: BPS (kode wilayah kab/kota)<br>{SUMBER_GEO}" + (f"<br>{extra}" if extra else "")


def legenda_html(dasar: str, labels: list[str], tampil_lingkaran: bool) -> str:
    labels = [esc(x) for x in labels]
    if dasar == "Kepadatan kejadian":
        item = "".join(f'<span class="lg"><i style="background:{KELAS_WARNA[i]}"></i>{labels[i]}</span>' for i in range(6))
        isi = f"<b>Kejadian per 1.000 km²</b> {item}"
    else:
        item = "".join(f'<span class="lg"><i style="background:{LISA_WARNA[k]}"></i>{k}</span>' for k in LISA_URUT)
        isi = f"<b>Klaster LISA</b> {item}"
    if tampil_lingkaran:
        lg = "".join(f'<span class="lg"><em style="width:{3 + 2.6 * n ** .5:.0f}px;height:{3 + 2.6 * n ** .5:.0f}px"></em>{n}</span>'
                     for n in (1, 10, 50))
        isi += f'<b>Jumlah kejadian</b> {lg}'
    return f'<div class="maplegend">{isi}</div>'


@st.fragment
def peta_kabkota():
    """Seluruh kontrol Bab 5 ada di dalam fragment: mengubah filter hanya me-render ulang bagian ini."""
    r1a, r1b = st.columns([1.5, 1])
    with r1a:
        per_lab = st.select_slider("Periode kejadian", options=list(PERIODE), value="2021–2026", key="geo_per")
    with r1b:
        fokus = st.selectbox("Fokus wilayah (zoom otomatis)", ["Seluruh Indonesia"] + sorted(PBOX), key="geo_fokus")
    r2a, r2b = st.columns([1.5, 1])
    with r2a:
        dasar = st.radio("Layer dasar", ["Kepadatan kejadian", "Klaster LISA"], horizontal=True, key="geo_dasar")
    with r2b:
        lingkaran = st.checkbox("Layer lingkaran proporsional (jumlah kejadian)", value=True, key="geo_bubble")

    p = PERIODE[per_lab]
    d = gdf.copy()
    d["rate"], d["n"] = d[rate_col(p)], d[count_col(p)]
    breaks = class_breaks(gdf, p)
    labels = class_labels(breaks)
    d["kelas"] = classify(d["rate"], breaks)
    scope = d if fokus == "Seluruh Indonesia" else d[d.provinsi == fokus]
    ket_per = "2021–2026" if p == "all" else (f"{p}, data parsial" if p == YEAR_PARSIAL else str(p))

    # ---------- peta ----------
    hover = [f"<b>{r.kabkota}</b> ({r.provinsi})<br>{int(r.n):,} kejadian, {ket_per}<br>"
             f"{r.rate:,.2f} kejadian per 1.000 km² (luas {r.luas_km2:,.0f} km²)<br>"
             f"LISA: {r.lisa_klaster} (I = {r.lisa_I:.2f}, p = {r.lisa_p:.3f})" for r in d.itertuples()]
    fig = go.Figure()
    if dasar == "Kepadatan kejadian":
        z, zmax = d["kelas"], 5
        skala = [[i / 5, c] for i, c in enumerate(KELAS_WARNA)]
        judul = f"Kepadatan kejadian Karhutla per kab/kota ({ket_per})"
    else:
        idx = {k: i for i, k in enumerate(LISA_URUT)}
        z, zmax = d["lisa_klaster"].map(idx), 4
        skala = [[i / 4, LISA_WARNA[k]] for i, k in enumerate(LISA_URUT)]
        judul = "Klaster LISA kejadian Karhutla per kab/kota (2021–2026)"
    fig.add_trace(go.Choroplethmap(
        geojson=GEO, locations=d["kode_kabkota"], featureidkey="properties.kode_kabkota", z=z, zmin=0, zmax=zmax,
        colorscale=skala, showscale=False, text=hover, hovertemplate="%{text}<extra></extra>",
        marker=dict(opacity=0.9, line=dict(width=0.4, color="rgba(15,10,10,.85)"))))
    if lingkaran:
        b = d[d["n"] > 0]
        fig.add_trace(go.Scattermap(
            lat=b["lat"], lon=b["lon"], mode="markers", hoverinfo="skip", showlegend=False,
            marker=dict(size=3 + 2.6 * np.sqrt(b["n"]), color="#56B4E9" if dasar == "Kepadatan kejadian" else "#ffffff", opacity=0.6)))
    pusat, zoom = (NASIONAL_PUSAT, NASIONAL_ZOOM) if fokus == "Seluruh Indonesia" else fit_view(PBOX[fokus])
    fig.update_layout(map=dict(style="carto-darkmatter", center=pusat, zoom=zoom), uirevision=fokus)
    finish(fig, judul, 580, legend=False, y_src=-0.06, sumber_teks=src_geo())
    fig.update_layout(margin=dict(l=0, r=0, t=52, b=70))

    cm, cr = st.columns([1.55, 1])
    with cm:
        st.plotly_chart(fig, key="geo_map", config={"scrollZoom": True, "displaylogo": False}, **STRETCH)
        html(legenda_html(dasar, labels, lingkaran))
        st.caption("Gulir atau cubit untuk zoom, seret untuk menggeser, atau pilih provinsi pada \"Fokus wilayah\". "
                   "Arahkan kursor / ketuk wilayah untuk rincian."
                   + (" Klaster LISA bersifat tetap (tidak mengikuti filter periode)." if dasar == "Klaster LISA" else ""))

    # ---------- peringkat ----------
    with cr:
        urut = st.radio("Peringkat berdasarkan", ["Kepadatan per 1.000 km²", "Jumlah kejadian"], horizontal=True, key="geo_urut")
        kol = "rate" if urut.startswith("Kepadatan") else "n"
        top = scope[scope[kol] > 0].nlargest(10, kol).iloc[::-1]
        if top.empty:
            st.info("Tidak ada kejadian pada filter ini.")
        else:
            teks = [f"{int(n)} kejadian" for n in top["n"]] if kol == "rate" else [f"{r:,.1f} per 1.000 km²" for r in top["rate"]]
            fr = go.Figure(go.Bar(
                x=top[kol], y=top["kabkota"], orientation="h", marker_color=API, text=teks, textposition="outside", cliponaxis=False,
                customdata=np.c_[top["provinsi"], top["luas_km2"].map(lambda v: f"{v:,.0f}")],
                hovertemplate="<b>%{y}</b><br>%{customdata[0]}<br>Luas %{customdata[1]} km²<extra></extra>"))
            fr.update_xaxes(title="Kejadian per 1.000 km²" if kol == "rate" else "Jumlah kejadian", gridcolor="rgba(255,255,255,.06)")
            fr.update_xaxes(range=[0, float(top[kol].max()) * 1.45])
            cakupan = "Indonesia" if fokus == "Seluruh Indonesia" else fokus
            finish(fr, f"10 kab/kota teratas: {cakupan} ({ket_per})", 580, legend=False, y_src=-0.06, sumber_teks=src_geo())
            fr.update_layout(margin=dict(l=10, r=10, t=52, b=70))
            st.plotly_chart(fr, key="geo_rank", **STRETCH)

    # ---------- tren tahunan + komposisi LISA ----------
    t1, t2 = st.columns([1.3, 1])
    with t1:
        per_thn = [int(scope[f"kej_{y}"].sum()) for y in YEARS]
        warna = [API if p == y else NETRAL for y in YEARS]
        ft = go.Figure(go.Bar(
            x=[str(y) + ("*" if y == YEAR_PARSIAL else "") for y in YEARS], y=per_thn,
            marker=dict(color=warna, pattern=dict(shape=["/" if y == YEAR_PARSIAL else "" for y in YEARS])),
            text=per_thn, textposition="outside",
            cliponaxis=False, hovertemplate="%{x}: %{y:,} kejadian<extra></extra>"))
        ft.update_yaxes(title="Jumlah kejadian", gridcolor="rgba(255,255,255,.06)", range=[0, max(per_thn + [1]) * 1.18])
        cakupan = "Indonesia" if fokus == "Seluruh Indonesia" else fokus
        finish(ft, f"Kejadian per tahun: {cakupan}", 380, legend=False, y_src=-0.3,
               sumber_teks=src_geo("* 2026 data parsial; oranye = periode terpilih"))
        ft.update_layout(margin=dict(l=10, r=10, t=52, b=96))
        st.plotly_chart(ft, key="geo_trend", **STRETCH)
    with t2:
        cnt = scope["lisa_klaster"].value_counts().reindex(LISA_URUT, fill_value=0)
        fl = go.Figure(go.Bar(
            x=cnt.values, y=cnt.index, orientation="h", marker_color=[LISA_WARNA[k] for k in cnt.index],
            marker_line_color="rgba(255,255,255,.35)", marker_line_width=1, text=cnt.values, textposition="outside", cliponaxis=False,
            customdata=[LISA_ARTI[k] for k in cnt.index], hovertemplate="<b>%{y}</b><br>%{x} kab/kota<br>%{customdata}<extra></extra>"))
        fl.update_yaxes(autorange="reversed")
        fl.update_xaxes(title="Jumlah kab/kota", gridcolor="rgba(255,255,255,.06)", range=[0, float(cnt.max()) * 1.2 + 1])
        finish(fl, f"Komposisi klaster LISA: {cakupan}", 380, legend=False, y_src=-0.3, sumber_teks=src_geo())
        fl.update_layout(margin=dict(l=10, r=10, t=52, b=96))
        st.plotly_chart(fl, key="geo_lisa", **STRETCH)


peta_kabkota()

# ---------- narasi (dihitung dari seluruh data, tidak bergantung filter) ----------
tot_g = int(gdf.n_kejadian.sum())
thn_g = {y: int(gdf[f"kej_{y}"].sum()) for y in YEARS}
pk_y = max(thn_g, key=thn_g.get)
ada_g = int((gdf.n_kejadian > 0).sum())
hh = gdf[gdf.lisa_klaster == "High-High"]
hh_prov = hh.provinsi.value_counts()
prov_g = gdf.groupby("provinsi").n_kejadian.sum().sort_values(ascending=False)
top3 = gdf.nlargest(3, "kejadian_per_1000km2")
tc = gdf.loc[gdf.n_kejadian.idxmax()]
cerita(
    f"<b>Apa yang terlihat?</b> Selama 2021–2026 tercatat <b>{tot_g:,}</b> kejadian di <b>{ada_g}</b> dari {len(gdf)} kab/kota "
    f"({ada_g / len(gdf) * 100:.0f}%). Puncaknya <b>{pk_y}</b> dengan {thn_g[pk_y]:,} kejadian ({thn_g[pk_y] / tot_g * 100:.0f}% dari total); "
    f"2026 belum berakhir, tetapi sudah mencatat {thn_g[2026]:,} kejadian, "
    f"{'lebih banyak' if thn_g[2026] > thn_g[2025] else 'lebih sedikit'} dari seluruh 2025 ({thn_g[2025]:,}). "
    f"Provinsi dengan kejadian terbanyak adalah {prov_g.index[0]} ({prov_g.iloc[0]:,}) dan {prov_g.index[1]} ({prov_g.iloc[1]:,}). "
    f"Secara spasial, <b>{len(hh)}</b> kab/kota membentuk hotspot (High-High), terbanyak di {hh_prov.index[0]} ({hh_prov.iloc[0]}) "
    f"dan {hh_prov.index[1]} ({hh_prov.iloc[1]}): api tidak menyebar acak, ia mengelompok."
)
cerita(
    f"<b>Hati-hati membaca angka per luas.</b> Tiga kab/kota dengan kepadatan tertinggi ({', '.join(top3.kabkota)}) luasnya "
    f"tidak lebih dari {top3.luas_km2.max():,.0f} km²: beberapa kejadian saja sudah menaikkan angka per km². Sebaliknya, jumlah kejadian terbanyak ada di "
    f"<b>{tc.kabkota}</b> ({tc.provinsi}, {int(tc.n_kejadian)} kejadian). Karena itu choropleth (rasio) selalu dibaca bersama lingkaran "
    f"proporsional (angka absolut) dan klaster LISA, bukan sendirian. Karena api mengelompok lintas kab/kota "
    f"dan sangat bervariasi di dalam satu provinsi, pemantauan Karhutla layak turun ke tingkat kab/kota, tidak berhenti di provinsi."
)


# =============================================================================
# 10. FOOTER / SUMBER DATA
# =============================================================================
with st.expander("📚 Sumber data, metodologi, dan keterbatasan"):
    st.markdown(f"""
**Sumber data**
- Kejadian bencana per provinsi {TAHUN}: {SUMBER_BENCANA}. URL: {URL_BENCANA}. Diakses: {TGL_AKSES}.
- Indikator satelit per provinsi (rata-rata): {SUMBER_SATELIT}.
- Korpus teks: {SUMBER_TEKS}.
- Peta kab/kota (Bab 5): {SUMBER_GEO}. Kode wilayah BPS (`kode_kabkota`) menjadi kunci gabungan atribut dengan batas wilayah. Diakses: {TGL_AKSES}.

**Pra-pemrosesan.** Jumlah kejadian bencana ditransformasi `log1p` sebelum PCA, lalu seluruh 10 variabel distandardisasi (z-score).
Korelasi memakai Spearman karena n = 38 dan distribusi miring. Teks sudah melalui case folding, tokenisasi, penghapusan stopword Bahasa Indonesia, dan stemming;
topic modeling memakai LDA (scikit-learn, `random_state=42`).

**Peta kab/kota.** Choropleth memakai rasio (kejadian per 1.000 km²), bukan angka absolut. Klasifikasi: satu kelas khusus untuk wilayah tanpa kejadian,
lalu kuintil (lima kelas berisi sama banyak) dari wilayah yang pernah terbakar, sehingga warna tidak didominasi segelintir pencilan. Batas kelas untuk
tiap tahun dihitung dari gabungan data enam tahun agar warna antar-tahun sebanding. Palet inferno (luminans monoton, aman buta warna). Lingkaran proporsional
berukuran ∝ √jumlah kejadian. Klaster LISA dibaca dari kolom `lisa_klaster` pada berkas GeoJSON. Geometri disederhanakan (Douglas-Peucker, toleransi ±550 m)
dengan `scripts/prep_geojson.py` agar ringan di browser.

**Keterbatasan.** Satu tahun data (2025) dan agregasi provinsi menyembunyikan variasi antar-kabupaten; Indeks Kondisi Rentan berbobot sama dan tidak divalidasi
terhadap titik panas; korpus hanya memuat judul dan abstrak. Pada peta kab/kota, kota kecil mudah tampil ekstrem karena penyebut luas yang kecil, data 2026 masih parsial,
dan klaster LISA tidak mengikuti filter periode.

**Alat bantu AI.** TODO: tuliskan deklarasi penggunaan alat bantu AI sesuai ketentuan ujian (juga di bagian Metodologi makalah).
""")

html(f"""<div class="footer">Dibuat untuk UAS Visualisasi Data dan Informasi 2026 &bull; Politeknik Statistika STIS &bull;
Kode: <a href="{URL_REPO}" style="color:#ffb347">{URL_REPO}</a> &bull; Sumber: BPS</div>""")
