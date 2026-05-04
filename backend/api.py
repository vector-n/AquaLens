"""
╔══════════════════════════════════════════════════════════════════════╗
║           AquaLens — backend/api.py  (v1.1 — Integrated)           ║
║           FastAPI Server — يربط النموذج Python بالموقع             ║
╚══════════════════════════════════════════════════════════════════════╝
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import numpy as np
import uvicorn
import sys, os

sys.path.insert(0, os.path.dirname(__file__))
from aqualens_model import (
    AquaLensModel,
    ArchieFormationEvaluator,
    generate_well_database,
)
# ── KEY INTEGRATION: استيراد معالج GRACE الحقيقي ──────────────────────
from grace_processor_real import get_grace_for_location, simulate_grace_basin

app = FastAPI(
    title       = "AquaLens API",
    description = "AI-Powered Groundwater Exploration · Sana'a Basin",
    version     = "1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

print("⚙️  جارٍ تحميل النموذج...")
_df    = generate_well_database(300)
_model = AquaLensModel()
_model.train(_df)
_fe    = ArchieFormationEvaluator()
print("✅ النموذج جاهز!\n")


class AnalyzeRequest(BaseModel):
    latitude:   float = Field(..., ge=14.8, le=16.0,  example=15.3544)
    longitude:  float = Field(..., ge=43.5, le=44.8,  example=44.2067)
    year:       int   = Field(2026, ge=2024, le=2040,  example=2026)
    use_grace:  bool  = Field(True)
    use_geo:    bool  = Field(True)
    use_fe:     bool  = Field(True)


@app.get("/")
def root():
    return {"status": "online", "message": "AquaLens API جاهز 💧",
            "version": "1.1.0", "docs": "/docs"}


@app.get("/health")
def health():
    grace_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'grace')
    real_grace = (os.path.isdir(grace_dir) and
                  any(f.endswith('.nc') for f in os.listdir(grace_dir)))
    return {
        "status": "ok",
        "model_trained": _model.is_trained,
        "wells_in_db": len(_df),
        "grace_real_data": real_grace,
        "grace_note": "REAL DATA" if real_grace else "SIMULATION — download from grace.jpl.nasa.gov",
    }


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    """
    النقطة الرئيسية — تستقبل إحداثيات وترجع التحليل الكامل.
    get_grace_for_location() تتحقق تلقائياً من وجود data/grace/*.nc
    وتستخدم البيانات الحقيقية إذا وُجدت، والمحاكاة بخلاف ذلك.
    """
    try:
        result = _model.predict({"latitude": req.latitude, "longitude": req.longitude})

        # ── GRACE: حقيقي أو محاكاة تلقائياً ──────────────────────────
        grace = get_grace_for_location(req.latitude, req.longitude)

        # ── تعديل العمق للسنة المطلوبة ────────────────────────────────
        delta  = req.year - 2010
        base   = result["depth_p50_m"] * 0.75
        adj    = base + grace["depletion_m_year"] * delta
        depth_p50 = round(adj)
        depth_p10 = round(adj * 0.87)
        depth_p90 = round(adj * 1.16)

        fe = _fe.evaluate(result["aquifer"]) if req.use_fe else None

        return {
            "aquifer":        result["aquifer"],
            "confidence_pct": result["confidence_pct"],
            "aquifer_proba":  result["aquifer_proba"],
            "depth_p10_m":    depth_p10,
            "depth_p50_m":    depth_p50,
            "depth_p90_m":    depth_p90,
            "depletion_rate_m_year": grace["depletion_m_year"],
            "grace_years":    grace["years"],
            "grace_tws":      grace["tws_anomaly_cm"],
            "grace_source":   grace.get("data_source", "simulation"),
            "constraints":    result["constraints"] if req.use_geo else [],
            "formation_eval": {
                "Sw":          round(fe["water_saturation_Sw"] * 100, 1) if fe else None,
                "phi":         round(fe["porosity_phi"] * 100, 1)        if fe else None,
                "pay_m":       fe["pay_thickness_m"]                     if fe else None,
                "Rt":          fe["resistivity_true_Rt"]                 if fe else None,
                "zone_arabic": fe["zone_arabic"]                         if fe else None,
            },
            "drilling_specs": result["drilling_specs"],
            "yield_class":    result["yield_class"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/wells")
def get_wells():
    wells = _df[["well_id","latitude","longitude","aquifer",
                  "depth_2026_m","yield_class","data_quality"]]\
              .head(50).to_dict(orient="records")
    return {"wells": wells, "total": len(_df)}


@app.get("/grace/basin")
def get_grace_basin():
    """السلسلة الزمنية GRACE لكامل الحوض — للرسم البياني في الداشبورد"""
    return simulate_grace_basin(target_year=2026)


if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
