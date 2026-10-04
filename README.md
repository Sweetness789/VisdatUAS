# 🔥 Titik Api Nusantara: Deteksi Potensi Karhutla per Provinsi (2025)

Web *data storytelling* berbasis Streamlit untuk **UAS Visualisasi Data dan Informasi 2026**, Politeknik Statistika STIS (Program Studi D-IV Komputasi Statistik).

| | |
|---|---|
| **Demo publik** | https://NAMA-APP.streamlit.app |
| **Repositori** | https://github.com/Sweetness789/VisdatUAS |

## Ringkasan

Aplikasi ini menelusuri pertanyaan: *provinsi mana yang kondisi lingkungannya paling rentan terhadap kebakaran hutan dan lahan (karhutla), dan di mana kejadiannya benar-benar terkonsentrasi?* Data bencana BPS dipadukan dengan indikator satelit (vegetasi, suhu, hujan, kelembapan) dan kejadian karhutla tingkat kabupaten/kota, lalu disajikan dalam lima bab pada satu halaman.

## Topik visualisasi (4 dari 6)

| Topik | Teknik | Interaksi |
|---|---|---|
| Berdimensi tinggi (10 variabel × 38 provinsi) | PCA (+ biplot), radar chart, heatmap korelasi berklaster | *Brushing & linking*: lasso/box pada PCA menyaring radar dan heatmap |
| Berhierarki (Indonesia → Pulau → Provinsi → Jenis bencana) | Sunburst dan treemap | *Drill-down* dengan *breadcrumb*; ukuran = jumlah kejadian, warna = % karhutla |
| Teks (193 dokumen BPS) | Word cloud, jaringan ko-okurensi, tren topik (LDA) | Filter periode, tema, dan kata fokus |
| Geospasial (514 kab/kota) | Choropleth (kepadatan), lingkaran proporsional (jumlah), peta klaster LISA | *Tooltip*, zoom/pan, filter tahun, fokus provinsi, kontrol layer |

## Sumber data

Data utama bersumber dari **BPS**. Data lain bersifat pendukung.

| Data | Sumber | Tahun | Level |
|---|---|---|---|
| Jumlah bencana alam menurut provinsi dan jenis bencana | **BPS**, tabel statistik [Jumlah Bencana Alam Menurut Provinsi dan Jenis Bencana Alam (Kejadian), 2025](https://www.bps.go.id/id/statistics-table/3/TUZaMGVteFVjSEJ4T1RCMlIyRjRTazVvVDJocVFUMDkjMw==/jumlah-bencana-alam-menurut-provinsi-dan-jenis-bencana-alam--kejadian---2024.html?year=2025) | 2025 | Provinsi (38) |
| Judul dan abstrak publikasi (korpus teks) | **BPS**, publikasi BPS | 2001–2026 | 193 dokumen |
| NDVI | Google Earth Engine, `MODIS/061/MOD13A1` | 2025 | Provinsi |
| Suhu permukaan siang hari (LST) | Google Earth Engine, `MODIS/061/MOD11A2` | 2025 | Provinsi |
| NBR | Google Earth Engine, `MODIS/061/MOD09A1` | 2025 | Provinsi |
| Curah hujan | Google Earth Engine, `UCSB-CHG/CHIRPS/DAILY` | 2025 | Provinsi |
| Kelembapan relatif (RH) | Google Earth Engine, `ECMWF/ERA5_LAND/MONTHLY_AGGR` | 2025 | Provinsi |
| Kejadian karhutla | BNPB, [GIS BNPB](https://gis.bnpb.go.id/) | 2021–2026 (2026 parsial) | Kab/kota (514) |
| Batas wilayah | Shapefile [lapakgis.com](https://www.lapakgis.com/2022/01/shapefile-batas-provinsi-indonesia.html) | 2022 | Provinsi, kab/kota |

Tanggal akses data: **3 Oktober 2026**. Kode wilayah BPS (`kode_kabkota`) dipakai sebagai kunci penggabungan atribut dengan batas wilayah.

## Berkas data

| Berkas | Isi |
|---|---|
| `data/Data_Provinsi_2025.xlsx` | 38 provinsi: NDVI, LST, NBR, curah hujan, RH, dan 5 jenis bencana (BPS) |
| `data/Korpus.xlsx` | 193 judul/abstrak publikasi BPS yang sudah dibersihkan |
| `data/kabkota_karhutla.geojson` | 514 kab/kota: kejadian karhutla 2021–2026 (total dan per tahun), kepadatan per 1.000 km², klaster LISA. Geometri sudah disederhanakan |
| `data/raw/kabkota_karhutla.geojson` | Berkas asli (±4 MB) sebelum disederhanakan |

## Struktur repositori

```
app.py                    # seluruh halaman cerita (Bab 1–5)
geo_utils.py              # fungsi bantu peta: muat GeoJSON, klasifikasi kuintil, zoom ke provinsi
scripts/
  gee_satelit.js          # kode Google Earth Engine untuk indikator satelit
  prep_geojson.py         # penyederhana geometri (Douglas-Peucker): data/raw → data
data/                     # data terolah (lihat tabel di atas)
requirements.txt
```

## Alur pengolahan

1. **Excel**: pembersihan tabel BPS, penyeragaman nama provinsi, dan penggabungan dengan indikator satelit menjadi `Data_Provinsi_2025.xlsx`.
2. **Google Earth Engine** (`scripts/gee_satelit.js`): rata-rata NDVI, LST, NBR, dan RH serta total curah hujan sepanjang 2025, diekstraksi ke batas provinsi dengan `reduceRegions` (reducer rata-rata, skala 5.000 m) lalu diekspor ke CSV.
   Skrip memakai aset batas provinsi pribadi (`projects/project-tbd-493500/assets/BatasProvinsi`). Untuk menjalankan ulang, unggah shapefile batas provinsi sendiri ke GEE (kolom nama provinsi `WADMPR`) dan ganti ID aset di baris pertama.
3. **QGIS**: pemeriksaan geometri, penyamaan sistem koordinat (WGS84), perhitungan luas wilayah, dan penggabungan atribut ke batas wilayah.
4. **Python**: analisis statistik (PCA, klaster, LDA, ko-okurensi) dan pembuatan visualisasi. `scripts/prep_geojson.py` menyederhanakan geometri agar ringan dimuat di peramban.

## Menjalankan lokal

```bash
git clone https://github.com/Sweetness789/VisdatUAS.git
cd VisdatUAS
pip install -r requirements.txt
streamlit run app.py
```

Menu navigasi memakai `st.html(..., unsafe_allow_javascript=True)` (Streamlit ≥ 1.52). Pada versi lebih lama, menu tetap berfungsi sebagai tautan jangkar.

## Deploy (Streamlit Community Cloud)

1. Push seluruh folder ke repo GitHub **publik**.
2. Buka https://share.streamlit.io → *New app* → pilih repo, branch `main`, file `app.py`.
3. Setelah jadi, salin URL aplikasi ke README ini dan ke makalah.

## Catatan metodologi

- Jumlah kejadian bencana: `log1p` lalu z-score sebelum PCA. Korelasi memakai Spearman (n = 38, distribusi miring).
- **Indeks Kondisi Rentan** = rata-rata min–max dari LST (tinggi), curah hujan, RH, NBR, dan NDVI (rendah) dengan bobot sama. Ini ringkasan deskriptif, **bukan model prediksi**.
- Peta kab/kota: choropleth memakai rasio (kejadian per 1.000 km²). Kelas = 1 kelas "tanpa kejadian" + kuintil dari wilayah yang pernah terbakar (identik dengan kolom `kelas_kepadatan`). Batas kelas dihitung dari gabungan 2021–2026 agar warna antar-tahun sebanding.
- Klaster LISA dibaca dari kolom `lisa_klaster` dan tidak mengikuti filter periode.
- Palet: Okabe-Ito (ramah buta warna), skala api dengan luminans monoton, dan diverging biru–oranye. Teks dan angka disertai satuan, legenda, dan keterangan "Sumber: BPS".

## Keterbatasan

- Data provinsi hanya satu tahun (2025). Data kab/kota 2026 masih parsial.
- Rata-rata per provinsi menyembunyikan variasi antar-kabupaten. Ekstraksi satelit memakai skala 5 km sehingga provinsi kecil (DKI Jakarta, DI Yogyakarta) hanya diwakili sedikit piksel, dan tidak ada penyaringan awan/QA.
- NBR rata-rata setahun hanya penanda kondisi vegetasi, bukan ukuran keparahan area terbakar. RH adalah perkiraan dari suhu dan titik embun bulanan.
- Indeks Kondisi Rentan berbobot sama dan belum divalidasi terhadap kejadian aktual. Dengan n = 38, PCA dan korelasi bersifat eksploratif, dan korelasi bukan sebab-akibat.
- Kota kecil mudah tampil ekstrem pada rasio per 1.000 km² karena penyebut luas kecil.
- Shapefile non-resmi dapat berbeda dari batas dan kode wilayah BPS terbaru (mis. pemekaran Papua).
- Pencatatan kejadian BNPB dan BPS memiliki definisi berbeda dan bergantung pada pelaporan daerah.

## Penggunaan alat bantu AI

Claude (Anthropic) digunakan sebagai alat bantu untuk menyusun struktur halaman web dan kode aplikasi. Pengumpulan dan pengolahan data (Excel, Google Earth Engine, QGIS, Python), pemilihan teknik visualisasi, interpretasi, dan seluruh isi proyek menjadi tanggung jawab penulis.

## Identitas

**Penulis:** Alisha Islami Zukhruf · 3SD2 · Politeknik Statistika STIS
Mata kuliah Visualisasi Data dan Informasi (K203407), UAS Semester Genap TA 2025/2026.
