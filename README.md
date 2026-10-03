# 🔥 Titik Api Nusantara - Deteksi Potensi Karhutla per Provinsi (2025)

Web data storytelling berbasis Streamlit untuk **UAS Visualisasi Data dan Informasi 2026** (Politeknik Statistika STIS).

**Demo publik:** https://NAMA-APP.streamlit.app  <!-- TODO -->
**Repositori:** https://github.com/USERNAME/REPO  <!-- TODO -->

## Topik visualisasi (4 dari 6)
| Topik | Teknik | Interaksi |
|---|---|---|
| Berdimensi tinggi (10 variabel x 38 provinsi) | PCA (+biplot), radar chart, clustered heatmap | Brushing & linking: lasso/box pada PCA menyaring radar dan heatmap |
| Berhierarki (Indonesia > Pulau > Provinsi > Jenis bencana) | Sunburst + treemap | Drill-down dengan breadcrumb; ukuran = jumlah kejadian, warna = % Karhutla |
| Teks (193 dokumen BPS) | Word cloud, jaringan ko-okurensi, tren topik (LDA) | Filter periode, tema, kata fokus |
| Geospasial (514 kab/kota) | Choropleth (kepadatan), lingkaran proporsional (jumlah), peta klaster LISA | Tooltip, zoom/pan, filter tahun, fokus provinsi, kontrol layer |

## Data
| Berkas | Isi |
|---|---|
| `data/Data_Provinsi_2025.xlsx` | 38 provinsi: NDVI, LST, NBR, curah hujan, RH, dan 5 jenis bencana (BPS) |
| `data/Korpus.xlsx` | 193 judul/abstrak publikasi BPS yang sudah dibersihkan |
| `data/kabkota_karhutla.geojson` | 514 kab/kota: kejadian Karhutla 2021-2026 (total dan per tahun), kepadatan per 1.000 km², klaster LISA. Geometri sudah disederhanakan |
| `data/raw/kabkota_karhutla.geojson` | Berkas asli (4 MB) sebelum disederhanakan |

Sumber, URL, dan tanggal akses: lihat bagian konfigurasi di `app.py` (blok `TODO`) dan panel "Sumber data" di aplikasi.

## Struktur halaman
Satu halaman panjang dengan **menu tetap di atas**. Klik menu (Multivariat, Hierarki, Teks, Provinsi siaga, Geospasial) untuk gulir mulus ke bagian itu;
menu yang sedang dibaca ditandai otomatis. Menu memakai `st.html(..., unsafe_allow_javascript=True)` (Streamlit >= 1.52); pada versi lebih lama
menu tetap bekerja sebagai tautan jangkar.

```
app.py                 # seluruh halaman cerita (Bab 1-5)
geo_utils.py           # fungsi bantu peta: muat GeoJSON, klasifikasi kuintil, zoom ke provinsi (python geo_utils.py = uji cepat)
scripts/prep_geojson.py# penyederhana geometri (Douglas-Peucker) data/raw -> data
```

## Menjalankan lokal
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy (Streamlit Community Cloud)
1. Push seluruh folder ini ke repo GitHub **publik**.
2. Buka https://share.streamlit.io → New app → pilih repo, branch `main`, file `app.py`.
3. Setelah jadi, salin URL ke README ini dan ke makalah.

## Mengganti ikon
Taruh file di `assets/icons/` dengan nama: `api`, `satelit`, `hutan`, `teks`, `siaga`, `peta` (`.png`/`.svg`/`.webp`).
Jika file tidak ada, otomatis dipakai emoji (lihat dict `IKON` di `app.py`).

## Catatan metodologi
- Jumlah kejadian bencana: `log1p` lalu z-score sebelum PCA; korelasi memakai Spearman.
- Indeks Kondisi Rentan = rata-rata min-max dari LST (tinggi), curah hujan, RH, NBR, NDVI (rendah), bobot sama. Ini ringkasan deskriptif, **bukan model prediksi**.
- Peta kab/kota: choropleth memakai rasio (kejadian per 1.000 km²). Kelas = 1 kelas "tanpa kejadian" + kuintil dari wilayah yang pernah terbakar (identik dengan kolom `kelas_kepadatan`);
  batas kelas per tahun dihitung dari gabungan 2021-2026 agar warna antar-tahun sebanding. Kota kecil mudah tampil ekstrem (penyebut luas kecil), jadi peta dibaca bersama lingkaran proporsional.
  Klaster LISA dibaca dari kolom `lisa_klaster` (tidak mengikuti filter periode). Data 2026 masih parsial.
- Palet: Okabe-Ito (ramah buta warna), skala api bermonoton luminans, diverging biru-oranye.
- Penggunaan alat bantu AI: TODO deklarasikan di bagian Metodologi makalah.
