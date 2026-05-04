"""
╔══════════════════════════════════════════════════════════════════════╗
║  AquaLens — backend/grace_processor_real.py                         ║
║  معالجة بيانات GRACE-FO الحقيقية                                   ║
║                                                                      ║
║  الخطوات قبل التشغيل:                                               ║
║  1. سجّل على: https://urs.earthdata.nasa.gov (مجاني)               ║
║  2. حمّل البيانات من: https://grace.jpl.nasa.gov/data/             ║
║     → اختر: GRACE/GRACE-FO Mascon Solutions                        ║
║     → اختر: CSR RL06 v03                                           ║
║     → نوع الملف: NetCDF (.nc)                                      ║
║  3. ضع الملف في: data/grace/                                        ║
║  4. شغّل: python grace_processor_real.py                            ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
import pandas as pd
from pathlib import Path
import json

# ── مسارات الملفات ────────────────────────────────────────────────────
DATA_DIR  = Path(__file__).parent.parent / "data" / "grace"
OUT_DIR   = Path(__file__).parent.parent / "data" / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── حدود حوض صنعاء ───────────────────────────────────────────────────
LAT_MIN, LAT_MAX = 14.90, 15.75
LON_MIN, LON_MAX = 43.75, 44.65


# ══════════════════════════════════════════════════════════════════════
#  الدالة الرئيسية — تعالج ملف GRACE الحقيقي
# ══════════════════════════════════════════════════════════════════════
def process_grace_real(grace_file: str, gldas_file: str = None) -> dict:
    """
    معالجة بيانات GRACE-FO الحقيقية واستخراج اتجاهات استنزاف المياه الجوفية.

    المدخلات:
        grace_file:  مسار ملف GRACE NetCDF
        gldas_file:  مسار ملف GLDAS (اختياري — لطرح رطوبة التربة)

    المخرجات:
        قاموس يحتوي على:
        - depletion_map: خريطة الاستنزاف لكل نقطة شبكية
        - basin_average: المتوسط للحوض كاملاً
        - time_series:   السلسلة الزمنية الكاملة
    """
    try:
        import netCDF4 as nc
    except ImportError:
        print("❌ مكتبة netCDF4 غير مثبتة")
        print("   شغّل: pip install netCDF4")
        return None

    print(f"📂 تحميل: {grace_file}")
    ds = nc.Dataset(grace_file)

    # ── استخراج المتغيرات ─────────────────────────────────────────
    # اسم المتغير يختلف حسب نسخة الملف
    var_names = list(ds.variables.keys())
    print(f"   المتغيرات المتاحة: {var_names}")

    # TWSA (Terrestrial Water Storage Anomaly)
    twsa_var = next((v for v in ['lwe_thickness','TWS','twsa'] if v in var_names), None)
    if not twsa_var:
        print("❌ لم يُعثَر على متغير TWSA في الملف")
        return None

    twsa = ds.variables[twsa_var][:]   # شكل: (time, lat, lon) أو (lat, lon, time)
    lats = ds.variables['lat'][:]
    lons = ds.variables['lon'][:]
    time = ds.variables['time'][:]     # أيام منذ تاريخ مرجعي

    # تحويل الزمن إلى سنوات
    time_units = ds.variables['time'].units  # "days since 2002-01-01"
    try:
        from netCDF4 import num2date
        dates = num2date(time, time_units)
        years = np.array([d.year + d.month/12 for d in dates])
    except Exception:
        years = 2002 + time / 365.25

    print(f"   الفترة الزمنية: {years[0]:.1f} — {years[-1]:.1f}")
    print(f"   عدد الإطارات الزمنية: {len(time)}")

    # ── قناع حوض صنعاء ────────────────────────────────────────────
    lat_mask = (lats >= LAT_MIN) & (lats <= LAT_MAX)
    lon_mask = (lons >= LON_MIN) & (lons <= LON_MAX)

    # استخراج الحوض
    if twsa.ndim == 3 and twsa.shape[0] == len(time):
        # شكل: (time, lat, lon)
        twsa_basin = twsa[:, lat_mask, :][:, :, lon_mask]
    else:
        # شكل: (lat, lon, time)
        twsa_basin = twsa[lat_mask, :, :][:, lon_mask, :].T

    # التعامل مع القيم المفقودة
    twsa_basin = np.ma.filled(twsa_basin, np.nan)

    # ── طرح رطوبة التربة من GLDAS (اختياري) ─────────────────────
    gws_basin = twsa_basin.copy()
    if gldas_file and Path(gldas_file).exists():
        print("   طرح رطوبة التربة من GLDAS...")
        ds_gl = nc.Dataset(gldas_file)
        # اجمع طبقات التربة: 0-10cm + 10-40cm + 40-100cm
        sm_layers = []
        for layer in ['SoilMoi0_10cm_inst','SoilMoi10_40cm_inst','SoilMoi40_100cm_inst']:
            if layer in ds_gl.variables:
                sm_layers.append(ds_gl.variables[layer][:])
        if sm_layers:
            sm_total = sum(sm_layers) / 10.0  # تحويل kg/m² إلى cm EWH
            sm_basin = sm_total[:, lat_mask, :][:, :, lon_mask]
            sm_basin = np.ma.filled(sm_basin, 0)
            min_len = min(gws_basin.shape[0], sm_basin.shape[0])
            gws_basin[:min_len] -= sm_basin[:min_len]
        ds_gl.close()

    ds.close()

    # ── متوسط الحوض ────────────────────────────────────────────────
    basin_avg = np.nanmean(gws_basin, axis=(1,2))

    # ── حساب معدل الاستنزاف بالانحدار الخطي ──────────────────────
    valid_mask = ~np.isnan(basin_avg)
    if valid_mask.sum() < 10:
        print("⚠️  بيانات غير كافية للتحليل")
        return None

    x = years[valid_mask]
    y = basin_avg[valid_mask]
    slope_val, intercept = np.polyfit(x, y, 1)

    # المعدل بالسنة (cm EWH/year)
    depletion_cm_per_year = abs(slope_val)

    # تحويل تقريبي cm EWH → أمتار في الطبقة الحاملة (معامل ≈ 0.55)
    depletion_m_per_year  = round(depletion_cm_per_year * 0.55, 2)

    print(f"\n📊 نتائج GRACE لحوض صنعاء:")
    print(f"   معدل الاستنزاف: {depletion_cm_per_year:.3f} cm EWH/year")
    print(f"   ما يعادل تقريباً: {depletion_m_per_year} م/سنة في الطبقة الحاملة")
    print(f"   إجمالي الخسارة {int(years[0])}–{int(years[-1])}: {depletion_m_per_year*(years[-1]-years[0]):.1f} م تقريباً")

    # ── خريطة الاستنزاف لكل خلية شبكية ──────────────────────────
    basin_lats = lats[lat_mask]
    basin_lons = lons[lon_mask]
    depletion_map = []

    for i, lat_v in enumerate(basin_lats):
        for j, lon_v in enumerate(basin_lons):
            cell = gws_basin[:, i, j]
            valid = ~np.isnan(cell)
            if valid.sum() < 8:
                continue
            sl, _ = np.polyfit(years[valid], cell[valid], 1)
            depletion_map.append({
                'lat':          float(round(lat_v, 3)),
                'lon':          float(round(lon_v, 3)),
                'depletion_cm_yr': float(round(abs(sl), 3)),
                'depletion_m_yr':  float(round(abs(sl)*0.55, 2)),
            })

    # ── حفظ النتائج ───────────────────────────────────────────────
    result = {
        'basin_name':          'Sana\'a Basin, Yemen',
        'period':              f"{int(years[0])}–{int(years[-1])}",
        'n_months':            int(len(time)),
        'depletion_cm_per_year': float(round(depletion_cm_per_year, 3)),
        'depletion_m_per_year':  float(depletion_m_per_year),
        'total_loss_m':          float(round(depletion_m_per_year * (years[-1]-years[0]), 1)),
        'time_series': {
            'years':  [float(round(y,3)) for y in years],
            'gws_cm': [float(round(v,2)) if not np.isnan(v) else None for v in basin_avg],
        },
        'depletion_map': depletion_map,
    }

    # حفظ JSON
    out_file = OUT_DIR / 'grace_sanaa_result.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n✅ النتائج محفوظة في: {out_file}")

    return result


# ══════════════════════════════════════════════════════════════════════
#  محاكاة واقعية (للاستخدام حين لا تتوفر البيانات بعد)
#  تعكس النمط الحقيقي المرصود في الأدبيات لحوض صنعاء
# ══════════════════════════════════════════════════════════════════════
def simulate_grace_basin(target_year: int = 2026) -> dict:
    """
    محاكاة بيانات GRACE مبنية على قيم الأدبيات المنشورة لحوض صنعاء.
    تُستخدم كـ placeholder حتى تتوفر البيانات الحقيقية.

    المصدر: Van der Gun et al. 1995 + NWRA 2021 + قيم FEFLOW 2012
    """
    np.random.seed(42)
    years = np.arange(2003, target_year + 0.1, 1/12)

    # المعدل الحقيقي المُقدَّر من الأدبيات: ~7 م/سنة في المركز
    # يعادل تقريباً ~12.7 cm EWH/year
    TRUE_RATE = -12.7

    tws = []
    for i, yr in enumerate(years):
        trend    = TRUE_RATE * 0.083 * i      # انخفاض خطي
        seasonal = 2.1 * np.sin(2*np.pi*i/12) # تذبذب موسمي
        noise    = np.random.normal(0, 1.2)    # ضوضاء طبيعية
        tws.append(round(trend + seasonal + noise, 2))

    return {
        'source':       'SIMULATION (replace with real GRACE data)',
        'period':       f'2003–{target_year}',
        'depletion_cm_per_year': 12.7,
        'depletion_m_per_year':  6.99,
        'time_series': {
            'years': [float(round(y,3)) for y in years],
            'gws_cm': tws,
        }
    }


# ══════════════════════════════════════════════════════════════════════
#  دالة للاستخدام من api.py
# ══════════════════════════════════════════════════════════════════════
def get_grace_for_location(lat: float, lon: float) -> dict:
    """
    تُستدعى من api.py لكل طلب تحليل.
    تستخدم البيانات الحقيقية إذا توفرت، والمحاكاة بخلاف ذلك.
    """
    grace_file = DATA_DIR / 'GRCTellus.JPL.200204_202312.GLO.RL06.nc'

    if grace_file.exists():
        result = process_grace_real(str(grace_file))
    else:
        result = simulate_grace_basin()

    if result is None:
        result = simulate_grace_basin()

    # تعديل معدل الاستنزاف بحسب موقع النقطة داخل الحوض
    dist_center = np.sqrt((lat - 15.35)**2 + (lon - 44.20)**2)
    # الاستنزاف أعلى في المركز وأقل على الأطراف
    spatial_factor = max(0.5, 1.0 - dist_center * 0.8)
    local_rate = round(result['depletion_m_per_year'] * spatial_factor, 2)

    return {
        'depletion_m_year':  local_rate,
        'years':             result['time_series']['years'],
        'tws_anomaly_cm':    result['time_series']['gws_cm'],
        'data_source':       result.get('source', 'GRACE-FO CSR RL06'),
    }


# ══════════════════════════════════════════════════════════════════════
#  نقطة البداية
# ══════════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    import sys

    print("═" * 55)
    print("  AquaLens — معالج GRACE-FO")
    print("═" * 55)

    # ابحث عن ملف GRACE
    grace_files = list(DATA_DIR.glob('*.nc')) if DATA_DIR.exists() else []

    if grace_files:
        print(f"\n✅ عُثر على ملف GRACE: {grace_files[0].name}")
        result = process_grace_real(str(grace_files[0]))
    else:
        print(f"\n⚠️  لم يُعثَر على ملفات GRACE في: {DATA_DIR}")
        print("\nلتحميل البيانات الحقيقية:")
        print("  1. افتح: https://urs.earthdata.nasa.gov → سجّل (مجاني)")
        print("  2. افتح: https://grace.jpl.nasa.gov/data/")
        print("  3. اختر: CSR RL06 Mascon → NetCDF")
        print("  4. ضع الملف في: data/grace/")
        print("\n▶  تشغيل المحاكاة الاحتياطية...")
        result = simulate_grace_basin()
        print(f"\n📊 نتائج المحاكاة:")
        print(f"   معدل الاستنزاف: {result['depletion_m_per_year']} م/سنة")
        print(f"   الفترة: {result['period']}")

    print("\n✅ اكتمل المعالج\n")
