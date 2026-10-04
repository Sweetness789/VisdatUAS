// 1. INPUT BATAS PROVINSI & WAKTU
var batas_provinsi = ee.FeatureCollection("projects/project-tbd-493500/assets/BatasProvinsi");

var startDate = '2025-01-01';
var endDate = '2025-12-31';

// 2. PENGAMBILAN & PENGOLAHAN DATA SATELIT

// A. NDVI (Tingkat Kehijauan Vegetasi dari MODIS 16-Day)
var ndvi = ee.ImageCollection('MODIS/061/MOD13A1')
  .filterDate(startDate, endDate)
  .select('NDVI')
  .mean()
  .multiply(0.0001) // Scale factor MODIS NDVI
  .rename('NDVI_avg');

// B. LST (Suhu Permukaan Siang Hari dari MODIS 8-Day)
var lst = ee.ImageCollection('MODIS/061/MOD11A2')
  .filterDate(startDate, endDate)
  .select('LST_Day_1km')
  .mean()
  .multiply(0.02).subtract(273.15) // Scale factor + Konversi dari Kelvin ke Celcius
  .rename('LST_avg_C');

// C. NBR (Normalized Burn Ratio dari MODIS Surface Reflectance 8-Day)
// Rumus: (NIR - SWIR) / (NIR + SWIR) -> Pada MODIS: (Band 2 - Band 7)
var nbr = ee.ImageCollection('MODIS/061/MOD09A1')
  .filterDate(startDate, endDate)
  .map(function(img) {
    return img.normalizedDifference(['sur_refl_b02', 'sur_refl_b07']).rename('NBR_avg')
              .copyProperties(img, ['system:time_start']);
  })
  .mean();

// D. Curah Hujan (Total Akumulasi Curah Hujan setahun dari CHIRPS)
var curah_hujan = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY')
  .filterDate(startDate, endDate)
  .select('precipitation')
  .sum() 
  .rename('Curah_Hujan_Total');

// E. Kelembapan Udara (Dihitung dari Temperature & Dewpoint ECMWF ERA5-Land)
var kelembapan = ee.ImageCollection('ECMWF/ERA5_LAND/MONTHLY_AGGR')
  .filterDate(startDate, endDate)
  .map(function(img) {
    var t = img.select('temperature_2m').subtract(273.15); // Konversi Kelvin ke Celcius
    var td = img.select('dewpoint_temperature_2m').subtract(273.15);
    
    // Rumus pendekatan Relative Humidity (Magnus-Tetens)
    var e = t.expression('exp((17.625 * T) / (243.04 + T))', {'T': t});
    var ed = td.expression('exp((17.625 * Td) / (243.04 + Td))', {'Td': td});
    var rh = ed.divide(e).multiply(100).rename('Kelembapan_RH_avg');
    
    return rh.copyProperties(img, ['system:time_start']);
  })
  .mean();

// 3. PENGGABUNGAN & EKSTRAKSI KE POLIGON (SHP)
var image_gabungan = ee.Image([ndvi, lst, nbr, curah_hujan, kelembapan]);

var hasil_ekstraksi = image_gabungan.reduceRegions({
  collection: batas_provinsi,
  reducer: ee.Reducer.mean(),
  scale: 5000, // Skala resolusi 5000 meter (5km) agar GEE tidak Memory Limit/Error untuk ukuran Indonesia
  tileScale: 4 // Membagi komputasi untuk mencegah error
});

// 4. EXPORT KE GOOGLE DRIVE SEBAGAI CSV
Export.table.toDrive({
  collection: hasil_ekstraksi,
  description: 'Data_Satelit_Provinsi_2025', 
  folder: 'GEE_Ekspor',
  fileFormat: 'CSV',
  selectors: ['WADMPR', 'NDVI_avg', 'LST_avg_C', 'NBR_avg', 'Curah_Hujan_Total', 'Kelembapan_RH_avg']
});
