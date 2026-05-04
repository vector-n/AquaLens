// ══════════════════════════════════════════════════════════════════════
//  AquaLens — Google Earth Engine Script
//  كيفية الاستخدام:
//  1. افتح: https://code.earthengine.google.com
//  2. انسخ هذا الكود كاملاً والصقه في المحرر
//  3. اضغط "Run"
//  4. انتظر التصدير في Google Drive
// ══════════════════════════════════════════════════════════════════════

// ── حدود حوض صنعاء ──────────────────────────────────────────────────
var BASIN = ee.Geometry.Rectangle([43.75, 14.90, 44.65, 15.75]);
var SCALE = 30; // دقة الإخراج بالمتر (30m = SRTM)

Map.centerObject(BASIN, 10);
Map.setOptions('SATELLITE');

// ════════════════════════════════════════════════════════════════════
//  1. نموذج الارتفاع الرقمي (SRTM DEM)
// ════════════════════════════════════════════════════════════════════
var dem   = ee.Image('USGS/SRTMGL1_003').clip(BASIN);
var slope = ee.Terrain.slope(dem);
var aspect= ee.Terrain.aspect(dem);

// Topographic Wetness Index (TWI)
// TWI = ln( Flow Accumulation / tan(slope) )
var flowAcc = ee.Image('WWF/HydroSHEDS/15ACC').clip(BASIN);
var slopeRad= slope.multiply(Math.PI/180);
var twi     = flowAcc.add(1).log()
              .subtract(slopeRad.tan().add(0.001).log())
              .rename('TWI');

// Profile Curvature (انحناء التضاريس)
var curvature = dem.convolve(ee.Kernel.laplacian8()).rename('curvature');

// Valley Depth (عمق الوادي — مهم لتحديد مناطق التغذية)
var valleyDepth = dem.subtract(
  dem.focal_max({radius:500, units:'meters'})
).abs().rename('valley_depth');

print('✅ DEM layers ready');

// ════════════════════════════════════════════════════════════════════
//  2. صور Sentinel-2 (متوسط 2022-2024)
// ════════════════════════════════════════════════════════════════════
var s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterBounds(BASIN)
  .filterDate('2022-01-01', '2024-12-31')
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10))
  .median()
  .clip(BASIN);

// NDVI — مؤشر الغطاء النباتي (يدل على المياه الضحلة)
var ndvi = s2.normalizedDifference(['B8','B4']).rename('NDVI');

// NDWI — مؤشر الماء (يحدد مجاري الأودية)
var ndwi = s2.normalizedDifference(['B3','B8']).rename('NDWI');

// BSI — مؤشر التربة العارية (يكشف الصخور المكشوفة)
var bsi = s2.expression(
  '((SWIR1 + RED) - (NIR + BLUE)) / ((SWIR1 + RED) + (NIR + BLUE))',
  { SWIR1:s2.select('B11'), RED:s2.select('B4'),
    NIR:s2.select('B8'),   BLUE:s2.select('B2') }
).rename('BSI');

// NDSI — مؤشر الجيولوجيا (يساعد في تمييز الصخور)
var ndsi = s2.normalizedDifference(['B11','B8']).rename('NDSI');

print('✅ Sentinel-2 indices ready');

// ════════════════════════════════════════════════════════════════════
//  3. هطول الأمطار CHIRPS (2000-2024)
// ════════════════════════════════════════════════════════════════════
var chirps = ee.ImageCollection('UCSB-CHG/CHIRPS/PENTAD')
  .filterBounds(BASIN)
  .filterDate('2000-01-01', '2024-12-31')
  .sum() // مجموع الهطول (mm)
  .clip(BASIN)
  .rename('rainfall_total_mm');

var chirpsAnnual = chirps.divide(24); // متوسط سنوي تقريبي (24 سنة)
print('✅ CHIRPS rainfall ready');

// ════════════════════════════════════════════════════════════════════
//  4. بيانات التربة (FAO/HWSDv2)
// ════════════════════════════════════════════════════════════════════
var soil = ee.Image('OpenLandMap/SOL/SOL_TEXTURE-CLASS_USDA-TT_M/v02')
  .select('b0')
  .clip(BASIN)
  .rename('soil_texture');
print('✅ Soil data ready');

// ════════════════════════════════════════════════════════════════════
//  5. شبكة الصرف (Drainage Network)
// ════════════════════════════════════════════════════════════════════
var drainage = ee.Image('WWF/HydroSHEDS/15DIR').clip(BASIN);
var wadi_mask= flowAcc.gt(500).rename('wadi_network'); // الأودية الرئيسية
print('✅ Drainage network ready');

// ════════════════════════════════════════════════════════════════════
//  6. عرض على الخريطة
// ════════════════════════════════════════════════════════════════════
Map.addLayer(dem, {min:1800, max:3500, palette:['006633','E5FFCC','662A00','D8D8D8','F5F5F5']}, 'DEM');
Map.addLayer(slope, {min:0, max:45, palette:['white','orange','red']}, 'Slope');
Map.addLayer(twi, {min:0, max:15, palette:['white','00BFFF','000080']}, 'TWI');
Map.addLayer(ndvi, {min:-0.2, max:0.6, palette:['brown','yellow','green']}, 'NDVI');
Map.addLayer(ndwi, {min:-0.5, max:0.3, palette:['red','white','blue']}, 'NDWI (Water)');
Map.addLayer(wadi_mask.selfMask(), {palette:['0000FF']}, 'Wadi Network');
Map.addLayer(chirpsAnnual, {min:100, max:500, palette:['white','lightblue','darkblue']}, 'Rainfall (mm/yr)');

// ════════════════════════════════════════════════════════════════════
//  7. دمج كل الطبقات في صورة واحدة للتصدير
// ════════════════════════════════════════════════════════════════════
var allBands = dem.rename('elevation')
  .addBands(slope.rename('slope'))
  .addBands(aspect.rename('aspect'))
  .addBands(twi)
  .addBands(curvature)
  .addBands(valleyDepth)
  .addBands(ndvi)
  .addBands(ndwi)
  .addBands(bsi)
  .addBands(ndsi)
  .addBands(chirpsAnnual.rename('rainfall_mm_yr'))
  .addBands(soil)
  .addBands(wadi_mask)
  .float();

print('📦 Final stack bands:', allBands.bandNames());

// ════════════════════════════════════════════════════════════════════
//  8. التصدير إلى Google Drive
//  ⚠️  يحتاج حساب Google Earth Engine نشط
//  الملفات ستظهر في: Google Drive → "AquaLens_GEE"
// ════════════════════════════════════════════════════════════════════

// تصدير الطبقات المجمَّعة (الأهم)
Export.image.toDrive({
  image:       allBands,
  description: 'AquaLens_Sanaa_Features_30m',
  folder:      'AquaLens_GEE',
  fileNamePrefix: 'sanaa_features_30m',
  region:      BASIN,
  scale:       SCALE,
  crs:         'EPSG:4326',
  maxPixels:   1e13,
  fileFormat:  'GeoTIFF'
});

// تصدير خريطة NDVI منفصلة
Export.image.toDrive({
  image:       ndvi,
  description: 'AquaLens_NDVI',
  folder:      'AquaLens_GEE',
  fileNamePrefix: 'sanaa_ndvi',
  region:      BASIN, scale:30, crs:'EPSG:4326', maxPixels:1e13
});

// تصدير شبكة الأودية
Export.image.toDrive({
  image:       wadi_mask,
  description: 'AquaLens_Wadis',
  folder:      'AquaLens_GEE',
  fileNamePrefix: 'sanaa_wadis',
  region:      BASIN, scale:30, crs:'EPSG:4326', maxPixels:1e13
});

print('');
print('═══════════════════════════════════════');
print('✅ تم إعداد التصدير!');
print('اضغط Run ثم انتظر مهمة التصدير في:');
print('Tasks → Run (الزاوية اليمنى العليا)');
print('الملفات ستظهر في Google Drive/AquaLens_GEE');
print('═══════════════════════════════════════');
