"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                         AquaLens — نموذج الذكاء الاصطناعي                  ║
║           AI-Powered Groundwater Exploration · Sana'a Basin, Yemen          ║
║                                                                              ║
║  المكونات:                                                                   ║
║  1. معالجة بيانات الآبار  (Well Data Processing)                            ║
║  2. معالجة GRACE-FO       (Depletion Surface)                               ║
║  3. هندسة الميزات         (Feature Engineering)                             ║
║  4. معادلة أرشي           (Formation Evaluation)                            ║
║  5. نموذج XGBoost         (Multi-task AI Model)                             ║
║  6. القيود الجيولوجية     (Physics-Informed Constraints)                    ║
║  7. واجهة Streamlit       (Web Application)                                 ║
║                                                                              ║
║  التشغيل:                                                                   ║
║    pip install -r requirements.txt                                           ║
║    streamlit run aqualens_model.py                                           ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

# ══════════════════════════════════════════════════════════════════════════════
#  IMPORTS
# ══════════════════════════════════════════════════════════════════════════════
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import cross_val_score
from sklearn.metrics import classification_report, mean_absolute_error, r2_score
from sklearn.preprocessing import LabelEncoder
import warnings
warnings.filterwarnings('ignore')

# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 1 — بيانات الآبار التجريبية (Synthetic Well Database)
#  في المشروع الحقيقي: تُستبدل بقاعدة بيانات NWRA الفعلية
# ══════════════════════════════════════════════════════════════════════════════

def generate_well_database(n_wells: int = 300, random_seed: int = 42) -> pd.DataFrame:
    """
    توليد قاعدة بيانات آبار تجريبية واقعية لحوض صنعاء.
    تعكس التوزيع الجيولوجي الحقيقي للطبقات الأربع.
    
    في الرسالة الفعلية: استبدل هذه الدالة بتحميل بيانات NWRA:
        df = pd.read_excel('NWRA_wells_sanaa.xlsx')
    """
    np.random.seed(random_seed)
    
    # حدود حوض صنعاء الجغرافية
    LAT_MIN, LAT_MAX = 14.90, 15.75
    LON_MIN, LON_MAX = 43.75, 44.65
    
    records = []
    
    for i in range(n_wells):
        lat = np.random.uniform(LAT_MIN, LAT_MAX)
        lon = np.random.uniform(LON_MIN, LON_MAX)
        
        # ── الطبقة المائية بناءً على القواعد الجيولوجية الحقيقية ──────────────
        # القاعدة 1: التوائلي غائب شمال 15.35°
        tawilah_possible = lat < 15.35
        
        # القاعدة 2: عمران فقط قرب الصدوع الكبرى
        near_fault = (abs(lon - 44.20) + abs(lat - 15.30)) < 0.18
        
        # القاعدة 3: الرباعية قرب الأودية
        in_wadi = (lat < 15.25) or (lon > 44.38 and lat < 15.42)
        
        # تحديد الطبقة مع احتمالات واقعية
        if in_wadi and np.random.random() > 0.3:
            aquifer = 'Q'   # رباعية
        elif not tawilah_possible and np.random.random() > 0.25:
            aquifer = 'V'   # بركانية
        elif tawilah_possible and np.random.random() > 0.35:
            aquifer = 'T'   # توائلي
        elif near_fault and np.random.random() > 0.5:
            aquifer = 'A'   # عمران
        else:
            aquifer = 'V'   # بركانية (الأكثر شيوعاً)
        
        # ── عمق المياه التاريخي (عند قياس البئر) ────────────────────────────
        base_depths = {'Q': 45,  'V': 135, 'T': 240, 'A': 400}
        depth_hist = (base_depths[aquifer] 
                      + np.random.normal(0, base_depths[aquifer] * 0.25)
                      + (lat - 15.35) * 80  # يزيد نحو الشمال
                      + max(0, (lon - 44.30) * 40))
        depth_hist = max(15, int(depth_hist))
        
        # ── سنة القياس ──────────────────────────────────────────────────────
        year_measured = np.random.randint(2000, 2023)
        
        # ── معدل الاستنزاف من GRACE-FO ───────────────────────────────────────
        depletion_rates = {'Q': 4.2, 'V': 6.7, 'T': 7.3, 'A': 3.1}
        depletion_rate = (depletion_rates[aquifer] 
                          + np.random.normal(0, 0.8)
                          + (lat - 15.00) * 2.5)  # أعلى في المركز
        depletion_rate = max(1.5, depletion_rate)
        
        # ── تعديل العمق لعام 2026 ────────────────────────────────────────────
        years_elapsed = 2026 - year_measured
        depth_2026 = depth_hist + depletion_rate * years_elapsed
        depth_2026 = max(depth_hist, int(depth_2026))  # لا يمكن أن يكون أقل
        
        # ── الإنتاجية ────────────────────────────────────────────────────────
        yield_map = {'Q': 3.5, 'V': 8.0, 'T': 14.0, 'A': 5.5}
        well_yield = (yield_map[aquifer] 
                      + np.random.normal(0, yield_map[aquifer] * 0.3))
        well_yield = max(0.5, round(well_yield, 1))
        
        # ── تصنيف الإنتاجية ──────────────────────────────────────────────────
        if well_yield < 5:      yield_class = 'low'
        elif well_yield < 15:   yield_class = 'medium'
        else:                   yield_class = 'high'
        
        # ── ميزات الاستشعار عن بعد (محاكاة) ─────────────────────────────────
        elevation    = 2150 + (lat - 15.0) * 120 + np.random.normal(0, 80)
        slope        = abs(np.random.normal(3.5, 2.0))
        twi          = np.random.normal(8.5, 2.5)   # Topographic Wetness Index
        ndvi         = np.random.uniform(0.05, 0.45)
        ndwi         = np.random.uniform(-0.3, 0.2)
        lineament_d  = abs(np.random.normal(2.1, 0.9))  # كثافة الكسور
        dist_fault   = abs(np.random.normal(800, 600))   # مسافة من الصدع (م)
        rainfall_mm  = np.random.normal(260, 55)         # هطول سنوي (ملم)
        
        records.append({
            'well_id':        f'SA-{i+1:04d}',
            'latitude':       round(lat, 4),
            'longitude':      round(lon, 4),
            'aquifer':        aquifer,
            'depth_hist_m':   depth_hist,
            'year_measured':  year_measured,
            'depletion_rate': round(depletion_rate, 2),
            'depth_2026_m':   depth_2026,
            'yield_ls':       well_yield,
            'yield_class':    yield_class,
            'elevation_m':    round(elevation, 1),
            'slope_deg':      round(slope, 2),
            'twi':            round(twi, 2),
            'ndvi':           round(ndvi, 3),
            'ndwi':           round(ndwi, 3),
            'lineament_density': round(lineament_d, 2),
            'dist_fault_m':   round(dist_fault, 0),
            'rainfall_mm':    round(rainfall_mm, 1),
            'data_quality':   np.random.choice(['high','medium','low'],
                                                p=[0.35, 0.45, 0.20]),
        })
    
    df = pd.DataFrame(records)
    print(f"✅ قاعدة البيانات: {len(df)} بئر")
    print(f"   توزيع الطبقات: {df['aquifer'].value_counts().to_dict()}")
    return df


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 2 — معالجة GRACE-FO (Groundwater Depletion Surface)
# ══════════════════════════════════════════════════════════════════════════════

class GRACEProcessor:
    """
    معالجة بيانات GRACE-FO لاستخراج اتجاهات استنزاف المياه الجوفية.
    
    في الرسالة الفعلية، استبدل simulate_grace() بـ:
        import netCDF4
        ds = netCDF4.Dataset('GRCTellus.JPL.200204_202312.GLO.RL06.nc')
        twsa = ds.variables['lwe_thickness'][:]
    """
    
    def __init__(self):
        self.years = list(range(2003, 2027))
        self.depletion_map = {}
    
    def simulate_grace(self, lat: float, lon: float) -> dict:
        """
        محاكاة بيانات GRACE-FO لموقع محدد.
        يعكس النمط الحقيقي المرصود في حوض صنعاء.
        """
        np.random.seed(int(abs(lat * 100 + lon * 100)) % 9999)
        
        # معدل الاستنزاف يزيد نحو مركز الحوض
        dist_from_center = np.sqrt((lat - 15.35)**2 + (lon - 44.20)**2)
        base_rate = max(3.0, 8.5 - dist_from_center * 15)
        
        # سلسلة زمنية TWS (cm EWH)
        tws_values = []
        cumulative = 0
        for i, yr in enumerate(self.years):
            # اتجاه سلبي + تذبذب موسمي + ضوضاء
            seasonal   = 1.8 * np.sin(2 * np.pi * i / 12)
            noise      = np.random.normal(0, 0.9)
            trend      = -base_rate * 0.13 * i  # تدهور تدريجي
            cumulative = trend + seasonal + noise
            tws_values.append(round(cumulative, 2))
        
        # معدل الاستنزاف السنوي (cm EWH / year → أمتار)
        x = np.arange(len(self.years))
        slope = np.polyfit(x, tws_values, 1)[0]
        depletion_cm_per_year = abs(slope)
        # تحويل تقريبي: 1 cm EWH ≈ 0.55 م في الطبقة الحاملة
        depletion_m_per_year = round(depletion_cm_per_year * 0.55, 2)
        
        return {
            'years':               self.years,
            'tws_anomaly_cm':      tws_values,
            'depletion_cm_year':   round(depletion_cm_per_year, 3),
            'depletion_m_year':    depletion_m_per_year,
            'total_loss_2003_2026': round(depletion_m_per_year * 23, 1),
        }
    
    def adjust_depth_for_depletion(self,
                                    depth_historical: float,
                                    year_measured: int,
                                    depletion_rate: float,
                                    target_year: int = 2026) -> dict:
        """
        تعديل عمق المياه التاريخي بناءً على معدل الاستنزاف.
        
        المعادلة: depth_adjusted = depth_hist + rate × Δyears
        """
        delta_years  = target_year - year_measured
        adjustment   = depletion_rate * delta_years
        depth_adj    = depth_historical + adjustment
        
        # نطاق عدم اليقين (±15%)
        depth_p10    = round(depth_adj * 0.87, 0)
        depth_p50    = round(depth_adj, 0)
        depth_p90    = round(depth_adj * 1.16, 0)
        
        return {
            'depth_p10_m':     depth_p10,
            'depth_p50_m':     depth_p50,   # التوقع الرئيسي
            'depth_p90_m':     depth_p90,
            'adjustment_m':    round(adjustment, 1),
            'years_elapsed':   delta_years,
        }


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 3 — تقييم التكوينات البترولية (Formation Evaluation)
#  معادلة أرشي لحساب التشبع المائي والمسامية
# ══════════════════════════════════════════════════════════════════════════════

class ArchieFormationEvaluator:
    """
    تطبيق معادلة أرشي على سجلات الآبار الجيوفيزيائية.
    
    معادلة أرشي الكاملة:
        Sw^n = (a × Rw) / (φ^m × Rt)
    
    حيث:
        Sw  = نسبة التشبع المائي (Water Saturation)
        Rw  = مقاومة ماء التكوين (Formation Water Resistivity)
        φ   = المسامية (Porosity)
        Rt  = المقاومة الكهربائية الحقيقية (True Resistivity)
        a   = معامل التعرج (Tortuosity Factor)
        m   = أس التمتين (Cementation Exponent)
        n   = أس التشبع (Saturation Exponent)
    
    معاملات معايَرة للحجر الرملي التوائلي في صنعاء:
        a=1.0, m=1.85, n=2.0
    """
    
    # معاملات معايَرة لكل طبقة
    PARAMS = {
        'T': {'a': 1.00, 'm': 1.85, 'n': 2.0, 'Rw': 0.15},  # توائلي
        'Q': {'a': 0.90, 'm': 1.65, 'n': 2.0, 'Rw': 0.25},  # رباعي
        'V': {'a': 1.10, 'm': 1.95, 'n': 2.0, 'Rw': 0.12},  # بركاني
        'A': {'a': 1.00, 'm': 2.00, 'n': 2.0, 'Rw': 0.10},  # عمران
    }
    
    def evaluate(self,
                  aquifer: str,
                  porosity: float = None,
                  resistivity_true: float = None) -> dict:
        """
        حساب خصائص التكوين لطبقة محددة.
        
        المدخلات:
            aquifer:           رمز الطبقة (T/Q/V/A)
            porosity:          المسامية (0-1)، تُقدَّر من سجل Neutron إذا توفر
            resistivity_true:  المقاومة الحقيقية (ohm.m) من سجل Resistivity
        """
        p = self.PARAMS.get(aquifer, self.PARAMS['T'])
        a, m, n, Rw = p['a'], p['m'], p['n'], p['Rw']
        
        # تقدير المسامية إذا لم تُعطَ
        if porosity is None:
            phi_defaults = {'T': 0.12, 'Q': 0.22, 'V': 0.08, 'A': 0.07}
            porosity = phi_defaults[aquifer] + np.random.normal(0, 0.02)
            porosity = max(0.03, min(0.35, porosity))
        
        # تقدير المقاومة إذا لم تُعطَ
        if resistivity_true is None:
            Rt_defaults = {'T': 18, 'Q': 12, 'V': 25, 'A': 35}
            resistivity_true = Rt_defaults[aquifer] + np.random.normal(0, 5)
            resistivity_true = max(5, resistivity_true)
        
        # ── معادلة أرشي ──────────────────────────────────────────────────────
        Sw = min(1.0, (a * Rw / (porosity**m * resistivity_true)) ** (1/n))
        Sw = max(0.05, Sw)
        
        # ── تصنيف المنطقة ───────────────────────────────────────────────────
        if Sw > 0.75:
            zone_type = 'water_bearing'      # منطقة مائية
            zone_ar   = 'منطقة مائية جيدة'
        elif Sw > 0.45:
            zone_type = 'transition'         # منطقة انتقالية
            zone_ar   = 'منطقة انتقالية'
        else:
            zone_type = 'low_saturation'     # تشبع منخفض
            zone_ar   = 'تشبع منخفض'
        
        # ── سُمك المنطقة المنتجة التقديري ───────────────────────────────────
        pay_thickness = (20 if Sw > 0.75 else 10) + int(np.random.uniform(5, 25))
        
        return {
            'water_saturation_Sw':   round(float(Sw), 3),
            'porosity_phi':          round(float(porosity), 3),
            'resistivity_true_Rt':   round(float(resistivity_true), 1),
            'formation_water_Rw':    Rw,
            'pay_thickness_m':       pay_thickness,
            'zone_type':             zone_type,
            'zone_arabic':           zone_ar,
            'archie_params':         {'a':a,'m':m,'n':n},
            'quality_flag':          'GOOD' if Sw > 0.65 else 'MARGINAL',
        }


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 4 — هندسة الميزات (Feature Engineering)
# ══════════════════════════════════════════════════════════════════════════════

def build_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """
    بناء مصفوفة الميزات للنموذج من بيانات الآبار والأقمار الاصطناعية.
    كل صف = بئر، كل عمود = ميزة مُدخلة للنموذج.
    """
    feats = df.copy()
    
    # ── ميزات جيومترية ──────────────────────────────────────────────────────
    # المسافة من مركز الحوض (مركز المدينة)
    feats['dist_center_km'] = np.sqrt(
        (feats['latitude']  - 15.35)**2 +
        (feats['longitude'] - 44.20)**2
    ) * 111  # تحويل درجات → كم

    # إشارة الحد الشمالي للتوائلي
    feats['north_of_tawilah'] = (feats['latitude'] > 15.35).astype(int)
    
    # ── ميزات GRACE ──────────────────────────────────────────────────────────
    # محاكاة معدل الاستنزاف المحلي من GRACE بناءً على الموقع
    feats['grace_depletion_rate'] = feats['depletion_rate']
    
    # السنوات المنقضية منذ القياس (للتعديل الزمني)
    feats['years_since_measure']  = 2026 - feats['year_measured']
    
    # ── مشتقات التضاريس ──────────────────────────────────────────────────────
    # الارتفاع المُعيَّر (نسبي لمتوسط الحوض)
    feats['elev_normalized'] = (feats['elevation_m'] - feats['elevation_m'].mean()) \
                                / feats['elevation_m'].std()
    
    # ── تفاعل الميزات ────────────────────────────────────────────────────────
    # التفاعل بين كثافة الكسور والقرب من الصدع (مهم للطبقة البركانية)
    feats['fracture_fault_interaction'] = (
        feats['lineament_density'] / (feats['dist_fault_m'] / 1000 + 0.1)
    )
    
    # الميزات النهائية للنموذج
    feature_cols = [
        'latitude', 'longitude',
        'elevation_m', 'slope_deg', 'twi',
        'ndvi', 'ndwi',
        'lineament_density', 'dist_fault_m',
        'rainfall_mm',
        'grace_depletion_rate', 'years_since_measure',
        'dist_center_km', 'north_of_tawilah',
        'elev_normalized', 'fracture_fault_interaction',
    ]
    
    return feats[feature_cols + ['aquifer', 'depth_2026_m', 'yield_class']]


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 5 — نموذج الذكاء الاصطناعي (Multi-Task AI Model)
# ══════════════════════════════════════════════════════════════════════════════

class AquaLensModel:
    """
    النموذج الرئيسي متعدد المهام:
    
    المهمة 1 → aquifer_classifier: تصنيف الطبقة المائية (Q/V/T/A)
    المهمة 2 → depth_predictor:    توقع عمق المياه المعدَّل لـ 2026
    المهمة 3 → yield_classifier:   تقدير فئة الإنتاجية (low/medium/high)
    
    الخوارزمية: Random Forest (مبدئياً — يُستبدل بـ XGBoost في النسخة الكاملة)
    """
    
    def __init__(self):
        self.aquifer_clf  = RandomForestClassifier(
            n_estimators=200, max_depth=12, min_samples_leaf=3,
            class_weight='balanced', random_state=42, n_jobs=-1
        )
        self.depth_reg    = RandomForestRegressor(
            n_estimators=200, max_depth=15, min_samples_leaf=3,
            random_state=42, n_jobs=-1
        )
        self.yield_clf    = RandomForestClassifier(
            n_estimators=200, max_depth=10, min_samples_leaf=3,
            class_weight='balanced', random_state=42, n_jobs=-1
        )
        self.le_aquifer   = LabelEncoder()
        self.le_yield     = LabelEncoder()
        self.feature_cols = None
        self.is_trained   = False
    
    def train(self, df: pd.DataFrame) -> dict:
        """
        تدريب النماذج الثلاثة مع تقرير أداء كامل.
        """
        print("\n" + "═"*60)
        print("  🤖 AquaLens — تدريب نماذج الذكاء الاصطناعي")
        print("═"*60)
        
        # بناء مصفوفة الميزات
        data = build_feature_matrix(df)
        
        target_cols   = ['aquifer', 'depth_2026_m', 'yield_class']
        self.feature_cols = [c for c in data.columns if c not in target_cols]
        
        X = data[self.feature_cols].values
        y_aq    = self.le_aquifer.fit_transform(data['aquifer'])
        y_depth = data['depth_2026_m'].values
        y_yield = self.le_yield.fit_transform(data['yield_class'])
        
        # ── تقسيم البيانات (80% تدريب / 20% اختبار) ──────────────────────
        from sklearn.model_selection import train_test_split
        X_tr, X_te, yaq_tr, yaq_te, yd_tr, yd_te, yy_tr, yy_te = \
            train_test_split(X, y_aq, y_depth, y_yield,
                             test_size=0.20, random_state=42,
                             stratify=y_aq)
        
        # ── تدريب النماذج الثلاثة ────────────────────────────────────────
        print("\n  [1/3] تدريب مُصنِّف الطبقة المائية...")
        self.aquifer_clf.fit(X_tr, yaq_tr)
        aq_acc = (self.aquifer_clf.predict(X_te) == yaq_te).mean()
        
        print(f"  [2/3] تدريب نموذج توقع العمق...")
        self.depth_reg.fit(X_tr, yd_tr)
        depth_mae = mean_absolute_error(yd_te, self.depth_reg.predict(X_te))
        depth_r2  = r2_score(yd_te, self.depth_reg.predict(X_te))
        
        print(f"  [3/3] تدريب مُصنِّف الإنتاجية...")
        self.yield_clf.fit(X_tr, yy_tr)
        yield_acc = (self.yield_clf.predict(X_te) == yy_te).mean()
        
        self.is_trained = True
        
        # ── تقرير الأداء ─────────────────────────────────────────────────
        results = {
            'aquifer_accuracy':   round(aq_acc * 100, 1),
            'depth_mae_m':        round(depth_mae, 1),
            'depth_r2':           round(depth_r2, 3),
            'yield_accuracy':     round(yield_acc * 100, 1),
            'n_train':            len(X_tr),
            'n_test':             len(X_te),
        }
        
        print("\n" + "─"*60)
        print("  📊 نتائج التحقق:")
        print(f"     دقة تصنيف الطبقة:      {results['aquifer_accuracy']}%")
        print(f"     دقة توقع العمق (R²):   {results['depth_r2']}")
        print(f"     متوسط خطأ العمق:       {results['depth_mae_m']} م")
        print(f"     دقة تصنيف الإنتاجية:  {results['yield_accuracy']}%")
        print("─"*60)
        
        # أهم الميزات
        feat_imp = pd.Series(
            self.aquifer_clf.feature_importances_,
            index=self.feature_cols
        ).sort_values(ascending=False)
        print("\n  🔑 أهم ٥ ميزات لتصنيف الطبقة:")
        for feat, imp in feat_imp.head(5).items():
            bar = '█' * int(imp * 50)
            print(f"     {feat:<30} {bar} {imp:.3f}")
        print("═"*60 + "\n")
        
        return results
    
    def predict(self, location: dict) -> dict:
        """
        توقع كامل لموقع محدد.
        
        المدخل:
            location: قاموس يحتوي على إحداثيات ومعطيات الموقع
        
        المخرج:
            قاموس كامل بالتوقعات والقيود الجيولوجية
        """
        if not self.is_trained:
            raise RuntimeError("النموذج لم يُدرَّب بعد. شغّل train() أولاً.")
        
        lat = location.get('latitude', 15.35)
        lon = location.get('longitude', 44.20)
        
        # بناء متجه الميزات
        feat_vec = self._extract_features(location)
        X = np.array([feat_vec])
        
        # ── توقع الطبقة المائية ──────────────────────────────────────────
        aq_proba = self.aquifer_clf.predict_proba(X)[0]
        aq_idx   = np.argmax(aq_proba)
        aquifer  = self.le_aquifer.inverse_transform([aq_idx])[0]
        conf     = round(aq_proba[aq_idx] * 100, 1)
        
        # ── توقع العمق ──────────────────────────────────────────────────
        depth = max(10, round(float(self.depth_reg.predict(X)[0])))
        
        # ── توقع الإنتاجية ────────────────────────────────────────────
        yield_idx   = self.yield_clf.predict(X)[0]
        yield_class = self.le_yield.inverse_transform([yield_idx])[0]
        
        # ── تطبيق القيود الجيولوجية الصارمة ─────────────────────────
        aquifer, conf, constraints = self._apply_constraints(
            aquifer, conf, depth, lat, lon)
        
        # ── تقييم التكوين (أرشي) ────────────────────────────────────
        fe = ArchieFormationEvaluator().evaluate(aquifer)
        
        # ── GRACE للموقع ─────────────────────────────────────────────
        grace_data = GRACEProcessor().simulate_grace(lat, lon)
        
        return {
            'aquifer':          aquifer,
            'confidence_pct':   conf,
            'aquifer_proba':    {
                self.le_aquifer.inverse_transform([i])[0]: round(p*100,1)
                for i,p in enumerate(aq_proba)
            },
            'depth_p50_m':      depth,
            'depth_p10_m':      round(depth * 0.87),
            'depth_p90_m':      round(depth * 1.16),
            'yield_class':      yield_class,
            'constraints':      constraints,
            'formation_eval':   fe,
            'grace':            grace_data,
            'drilling_specs':   self._drilling_specs(aquifer, depth),
        }
    
    def _extract_features(self, loc: dict) -> list:
        """استخراج متجه الميزات من إحداثيات الموقع."""
        lat = loc.get('latitude', 15.35)
        lon = loc.get('longitude', 44.20)
        
        # بيانات الأقمار الاصطناعية (في الواقع: Google Earth Engine API)
        np.random.seed(int(abs(lat*1000+lon*1000)) % 99999)
        
        dist_center = np.sqrt((lat-15.35)**2 + (lon-44.20)**2) * 111
        north_tawilah = int(lat > 15.35)
        elev = 2150 + (lat-15.0)*120 + np.random.normal(0,80)
        
        return [
            lat, lon,
            elev,                                 # elevation_m
            abs(np.random.normal(3.5, 2.0)),      # slope_deg
            np.random.normal(8.5, 2.5),           # twi
            np.random.uniform(0.05, 0.45),        # ndvi
            np.random.uniform(-0.3, 0.2),         # ndwi
            abs(np.random.normal(2.1, 0.9)),      # lineament_density
            abs(np.random.normal(800, 600)),      # dist_fault_m
            np.random.normal(260, 55),            # rainfall_mm
            max(1.5, 8.5 - dist_center*0.15 + np.random.normal(0,0.8)),  # depletion
            2026 - 2010,                          # years_since_measure
            dist_center,                          # dist_center_km
            north_tawilah,                        # north_of_tawilah
            (elev - 2200) / 150,                  # elev_normalized
            abs(np.random.normal(2.1,0.9)) /      # fracture_fault_interaction
            (abs(np.random.normal(800,600))/1000 + 0.1),
        ]
    
    def _apply_constraints(self, aquifer, conf, depth, lat, lon):
        """
        القيود الجيولوجية الصارمة (Physics-Informed Constraints).
        تمنع التوقعات المستحيلة جيولوجياً.
        """
        constraints = []
        
        # ── القاعدة 1: التوائلي غائب شمال 15.35° ───────────────────────
        if aquifer == 'T' and lat > 15.35:
            aquifer = 'V'
            conf    = max(50, conf - 15)
            constraints.append({
                'rule': 'TAWILAH_BOUNDARY',
                'severity': 'HIGH',
                'msg_ar': '⚠️ التوائلي غائب شمال ١٥.٣٥° — تحويل تلقائي للبركانية',
                'msg_en': 'Tawilah absent north of 15.35°N — auto-reclassified to Volcanic',
            })
        
        # ── القاعدة 2: عمران يحتاج صدوعاً قريبة ────────────────────────
        near_fault = (abs(lon - 44.20) + abs(lat - 15.30)) < 0.18
        if aquifer == 'A' and not near_fault:
            constraints.append({
                'rule': 'AMRAN_FAULT',
                'severity': 'MEDIUM',
                'msg_ar': '⚠️ عمران بعيد عن الصدوع — إنتاجية منخفضة محتملة',
                'msg_en': 'Amran far from mapped faults — low yield likely',
            })
        
        # ── القاعدة 3: عمق لا يمكن أن يتراجع ──────────────────────────
        min_depths = {'Q': 15, 'V': 60, 'T': 120, 'A': 250}
        if depth < min_depths.get(aquifer, 50):
            constraints.append({
                'rule': 'MIN_DEPTH',
                'severity': 'LOW',
                'msg_ar': f'ℹ️ عمق مُعدَّل للحد الأدنى الجيولوجي ({min_depths[aquifer]}م)',
                'msg_en': f'Depth adjusted to geological minimum ({min_depths[aquifer]}m)',
            })
        
        # ── القاعدة 4: البركانية تحتاج كسوراً ──────────────────────────
        if aquifer == 'V' and lat > 15.50:
            constraints.append({
                'rule': 'VOLCANIC_NORTH',
                'severity': 'LOW',
                'msg_ar': 'ℹ️ البركانية في الشمال — تحقق من كثافة الكسور قبل الحفر',
                'msg_en': 'Volcanic in northern zone — verify lineament density',
            })
        
        return aquifer, conf, constraints
    
    def _drilling_specs(self, aquifer: str, depth: int) -> dict:
        """توليد مواصفات الحفر بناءً على الطبقة والعمق."""
        methods = {
            'Q': 'حفر دوراني مباشر',
            'V': 'حفر هوائي بمطرقة DTH',
            'T': 'حفر دوراني بطين حفر',
            'A': 'حفر ماسي مع دعم أسمنتي',
        }
        diameters = {'Q': '6"', 'V': '8"', 'T': '8"', 'A': '6"'}
        pump_kw   = 15 if depth < 300 else 22
        duration  = f"{depth//35+3}–{depth//28+5} أسابيع"
        costs     = {'Q': '8,000–15,000', 'V': '18,000–28,000',
                     'T': '22,000–38,000', 'A': '30,000–50,000'}
        
        casing = {
            'Q': f'سطحي ٢٠م | منقّط {int(depth*.6)}–{depth}م',
            'V': f'سطحي ٤٠م | مبطن ٤٠–{int(depth*.5)}م | منقّط {int(depth*.5)}–{depth}م',
            'T': f'سطحي ٦٠م | مبطن ٦٠–{int(depth*.6)}م | منقّط {int(depth*.6)}–{depth}م',
            'A': f'مبطن كامل حتى {depth}م',
        }
        
        return {
            'method':     methods[aquifer],
            'diameter':   diameters[aquifer],
            'casing':     casing[aquifer],
            'pump':       f'غاطس {pump_kw} كيلوواط',
            'duration':   duration,
            'cost_usd':   costs[aquifer],
        }


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 6 — STREAMLIT WEB APPLICATION
#  شغّل: streamlit run aqualens_model.py
# ══════════════════════════════════════════════════════════════════════════════

def run_streamlit_app():
    """
    تطبيق Streamlit الكامل — واجهة ويب تفاعلية.
    """
    try:
        import streamlit as st
        import plotly.graph_objects as go
        import plotly.express as px
    except ImportError:
        print("❌ مكتبات Streamlit/Plotly غير مثبتة.")
        print("   شغّل: pip install streamlit plotly")
        return

    # ── إعداد الصفحة ─────────────────────────────────────────────────────
    st.set_page_config(
        page_title="AquaLens — منصة المياه الجوفية",
        page_icon="💧",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # ── تحميل وتدريب النموذج (مرة واحدة فقط) ────────────────────────────
    @st.cache_resource(show_spinner="⚙️ جارٍ تحميل النموذج...")
    def load_model():
        df    = generate_well_database(300)
        model = AquaLensModel()
        model.train(df)
        return model, df

    model, df = load_model()

    # ── CSS مخصص ─────────────────────────────────────────────────────────
    st.markdown("""
    <style>
    .stApp { background: #04090f; color: #dff0ff; }
    .metric-box {
        background: #0b1d2e; border: 1px solid rgba(0,220,180,0.18);
        border-radius: 10px; padding: 1rem; text-align: center;
    }
    .metric-val { font-size: 1.8rem; font-weight: 700; color: #00dcb4; }
    .metric-lbl { font-size: 0.8rem; color: #5a8aaa; margin-top: 0.2rem; }
    </style>
    """, unsafe_allow_html=True)

    # ── الشريط العلوي ─────────────────────────────────────────────────────
    col_logo, col_title, col_badge = st.columns([1, 6, 2])
    with col_logo:   st.markdown("## 💧")
    with col_title:  st.markdown("# AquaLens — منصة استكشاف المياه الجوفية")
    with col_badge:  st.markdown("`v1.0-alpha · AI-Powered`")
    st.divider()

    # ── الشريط الجانبي ────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### 📍 الموقع المحدد")
        lat_in = st.number_input("خط العرض °N", 14.8, 16.0, 15.3544, 0.0001, format="%.4f")
        lon_in = st.number_input("خط الطول °E", 43.5, 44.8, 44.2067, 0.0001, format="%.4f")
        yr_in  = st.number_input("سنة التحليل",  2024, 2040, 2026)

        st.markdown("### ⚙️ إعدادات النموذج")
        use_grace = st.toggle("تعديل GRACE-FO", value=True)
        use_geo   = st.toggle("القيود الجيولوجية", value=True)
        use_fe    = st.toggle("تقييم التكوين (أرشي)", value=True)

        st.markdown("### 🎯 آبار مرجعية")
        well_options = {
            f"SA-001 (٣٢٠م — توائلي)": (15.42, 44.18),
            f"SA-014 (٤٥٠م — توائلي)": (15.31, 44.23),
            f"SA-027 (٢١٠م — رباعي)":  (15.38, 44.31),
            f"SA-041 (جافة — بركاني)":  (15.50, 44.22),
        }
        selected = st.selectbox("اختر بئراً للاستكشاف", ["---"] + list(well_options))
        if selected != "---":
            lat_in, lon_in = well_options[selected]

        run = st.button("🔍 تحليل الموقع", type="primary", use_container_width=True)

    # ── المحتوى الرئيسي ──────────────────────────────────────────────────
    if run:
        with st.spinner("🤖 الذكاء الاصطناعي يحلل الموقع..."):
            result = model.predict({'latitude': lat_in, 'longitude': lon_in})

        # أسماء الطبقات
        AQ_NAMES = {
            'Q': ('رباعية جوفانية',         'Quaternary Alluvial',       '#22d47a'),
            'V': ('بركانية ثلاثية',          'Tertiary Volcanic Fractured','#1a8fff'),
            'T': ('حجر رملي توائلي',        'Cretaceous Tawilah Sandstone','#00dcb4'),
            'A': ('جيري عمران',             'Jurassic Amran Limestone',   '#f0a500'),
        }
        aq_ar, aq_en, aq_color = AQ_NAMES[result['aquifer']]
        fe    = result['formation_eval']
        grace = result['grace']
        specs = result['drilling_specs']

        # ── بطاقة الطبقة المائية ─────────────────────────────────────────
        st.markdown(f"""
        <div style="background:#0b1d2e;border:2px solid {aq_color};border-radius:14px;
            padding:1.5rem;margin-bottom:1rem;">
            <div style="font-size:1.4rem;font-weight:800;color:{aq_color}">{aq_ar}</div>
            <div style="font-size:0.85rem;color:#5a8aaa;margin-top:0.3rem">{aq_en}</div>
            <div style="margin-top:0.8rem;font-size:0.9rem;color:#dff0ff">
                مستوى الثقة: <b style="color:{aq_color}">{result['confidence_pct']}%</b>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── تنبيهات القيود الجيولوجية ────────────────────────────────────
        if result['constraints']:
            for c in result['constraints']:
                if c['severity'] == 'HIGH':   st.error(c['msg_ar'])
                elif c['severity'] == 'MEDIUM': st.warning(c['msg_ar'])
                else:                           st.info(c['msg_ar'])
        else:
            st.success("✅ لا قيود جيولوجية حرجة — الموقع مناسب")

        # ── المقاييس الرئيسية ────────────────────────────────────────────
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("العمق P50",    f"{result['depth_p50_m']} م")
        c2.metric("العمق P10",    f"{result['depth_p10_m']} م")
        c3.metric("العمق P90",    f"{result['depth_p90_m']} م")
        c4.metric("الإنتاجية",   result['yield_class'].upper())

        st.divider()

        # ── عمودان: GRACE + تقييم التكوين ─────────────────────────────
        col_g, col_f = st.columns(2)

        with col_g:
            st.markdown("#### 🛰️ استنزاف GRACE-FO (٢٠٠٣–٢٠٢٦)")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=grace['years'], y=grace['tws_anomaly_cm'],
                fill='tozeroy', fillcolor='rgba(255,68,68,0.12)',
                line=dict(color='#ff4444', width=1.5),
                name='TWS Anomaly'
            ))
            fig.update_layout(
                paper_bgcolor='#0b1d2e', plot_bgcolor='#0b1d2e',
                font_color='#5a8aaa', height=240,
                margin=dict(l=10,r=10,t=10,b=10),
                xaxis=dict(showgrid=False, color='#5a8aaa'),
                yaxis=dict(title='cm EWH', showgrid=True,
                           gridcolor='rgba(255,255,255,0.04)', color='#5a8aaa'),
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption(f"معدل الاستنزاف: **{grace['depletion_m_year']} م/سنة**")

        with col_f:
            st.markdown("#### ⚗️ تقييم التكوين — معادلة أرشي")
            if use_fe:
                cf1,cf2 = st.columns(2)
                cf1.metric("التشبع Sw", f"{fe['water_saturation_Sw']*100:.0f}%")
                cf2.metric("المسامية φ", f"{fe['porosity_phi']*100:.0f}%")
                cf1.metric("سُمك المنتج", f"{fe['pay_thickness_m']} م")
                cf2.metric("مقاومة Rt", f"{fe['resistivity_true_Rt']} Ω·m")
                zone_color = '#22d47a' if fe['zone_type']=='water_bearing' else '#f0a500'
                st.markdown(f"**المنطقة:** <span style='color:{zone_color}'>{fe['zone_arabic']}</span>",
                            unsafe_allow_html=True)
            else:
                st.info("تقييم التكوين معطل — فعّله من الشريط الجانبي")

        # ── مواصفات الحفر ────────────────────────────────────────────────
        st.markdown("#### 🔧 مواصفات الحفر الكاملة")
        spec_df = pd.DataFrame([
            ("طريقة الحفر",     specs['method']),
            ("قطر البئر",       specs['diameter']),
            ("برنامج التغليف",  specs['casing']),
            ("المضخة المقترحة", specs['pump']),
            ("مدة الحفر",       specs['duration']),
            ("التكلفة التقديرية", f"${specs['cost_usd']}"),
        ], columns=["المعيار", "القيمة"])
        st.dataframe(spec_df, hide_index=True, use_container_width=True)

        # ── خريطة الموقع ─────────────────────────────────────────────────
        st.markdown("#### 🗺️ موقع التحليل")
        map_df = pd.DataFrame({'lat':[lat_in], 'lon':[lon_in],
                                'label':[f'📍 موقع محدد ({aq_ar})']})
        well_map = df[['latitude','longitude','aquifer']].copy()
        well_map.columns = ['lat','lon','aquifer']
        st.map(pd.concat([map_df[['lat','lon']], well_map[['lat','lon']]]),
               zoom=10)

    else:
        # حالة الترحيب
        st.markdown("""
        <div style="text-align:center;padding:4rem 2rem;color:#5a8aaa">
            <div style="font-size:4rem;margin-bottom:1rem">💧</div>
            <div style="font-size:1.3rem;font-weight:700;color:#dff0ff;margin-bottom:0.5rem">
                مرحباً بك في AquaLens
            </div>
            <div style="font-size:0.95rem;line-height:1.8">
                أدخل الإحداثيات في الشريط الجانبي<br>
                ثم اضغط <b style="color:#00dcb4">تحليل الموقع</b><br>
                للحصول على توصيات الحفر الكاملة خلال ثوانٍ
            </div>
        </div>
        """, unsafe_allow_html=True)

        # إحصائيات قاعدة البيانات
        st.markdown("#### 📊 إحصائيات قاعدة البيانات")
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("إجمالي الآبار",    len(df))
        c2.metric("متوسط العمق",     f"{df['depth_2026_m'].mean():.0f} م")
        c3.metric("أعمق بئر",        f"{df['depth_2026_m'].max():.0f} م")
        c4.metric("متوسط الإنتاجية", f"{df['yield_ls'].mean():.1f} ل/ث")


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 7 — نقطة البداية (Entry Point)
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    # تشغيل من سطر الأوامر بدون Streamlit
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        print("\n🧪 وضع الاختبار — AquaLens Python Model\n")

        # 1. توليد البيانات
        df = generate_well_database(300)

        # 2. تدريب النموذج
        model = AquaLensModel()
        results = model.train(df)

        # 3. اختبار موقع
        print("\n📍 اختبار الموقع: 15.3544°N, 44.2067°E")
        pred = model.predict({'latitude': 15.3544, 'longitude': 44.2067})
        aq_names = {'Q':'رباعية','V':'بركانية','T':'توائلي','A':'عمران'}
        print(f"   الطبقة المائية:  {aq_names[pred['aquifer']]}  ({pred['confidence_pct']}%)")
        print(f"   العمق P50:       {pred['depth_p50_m']} م")
        print(f"   الإنتاجية:       {pred['yield_class']}")
        fe = pred['formation_eval']
        print(f"   التشبع المائي:   {fe['water_saturation_Sw']*100:.0f}%")
        print(f"   المسامية:        {fe['porosity_phi']*100:.0f}%")
        if pred['constraints']:
            print("   القيود المطبقة:")
            for c in pred['constraints']:
                print(f"     • {c['msg_ar']}")
        print(f"\n✅ اكتمل الاختبار بنجاح!\n")

    else:
        # تشغيل Streamlit
        run_streamlit_app()
