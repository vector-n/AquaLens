/* ═══════════════════════════════════════════════════════════════════
   AquaLens — dashboard.js
   AI Analysis Engine, Map Logic, and Mobile Drawer Manager
   Depends on: shared.js, Leaflet, Chart.js
═══════════════════════════════════════════════════════════════════ */

'use strict';

// ══════════════════════════════════════════════════════════════════════
//  GLOBAL STATE
// ══════════════════════════════════════════════════════════════════════
const State = {
  selectedLat:   15.3544,
  selectedLon:   44.2067,
  marker:        null,
  graceChart:    null,   // desktop chart instance
  graceChartM:   null,   // mobile chart instance
  isArabic:      true,
  layers:        { faults: true, grace: true, wells: true, tawilah: false },
  lastResult:    null,
};

// ══════════════════════════════════════════════════════════════════════
//  AQUIFER DATA
// ══════════════════════════════════════════════════════════════════════
const AQ_LABELS = {
  Q: { ar: 'رباعية جوفانية',      en: 'Quaternary Alluvial',           color: '#22c55e' },
  V: { ar: 'بركانية ثلاثية',      en: 'Tertiary Volcanic',             color: '#0ea5e9' },
  T: { ar: 'حجر رملي توائلي',    en: 'Cretaceous Tawilah Sandstone',  color: '#00c9a7' },
  A: { ar: 'جيري عمراني',         en: 'Jurassic Amran Limestone',      color: '#f59e0b' },
};

const WELL_DATA = [
  { lat: 15.42, lon: 44.18, id: 'SA-001', depth: 320,  yield: 'متوسطة', aq: 'V', ok: true  },
  { lat: 15.31, lon: 44.23, id: 'SA-014', depth: 450,  yield: 'عالية',  aq: 'T', ok: true  },
  { lat: 15.38, lon: 44.31, id: 'SA-027', depth: 210,  yield: 'منخفضة', aq: 'Q', ok: true  },
  { lat: 15.25, lon: 44.15, id: 'SA-033', depth: 680,  yield: 'عالية',  aq: 'T', ok: true  },
  { lat: 15.50, lon: 44.22, id: 'SA-041', depth: null, yield: 'جافة',   aq: 'V', ok: false },
  { lat: 15.35, lon: 44.40, id: 'SA-058', depth: 385,  yield: 'متوسطة', aq: 'T', ok: true  },
  { lat: 15.28, lon: 44.35, id: 'SA-072', depth: 290,  yield: 'منخفضة', aq: 'Q', ok: true  },
  { lat: 15.44, lon: 44.38, id: 'SA-089', depth: 520,  yield: 'عالية',  aq: 'T', ok: true  },
];

// ══════════════════════════════════════════════════════════════════════
//  MAP
// ══════════════════════════════════════════════════════════════════════
function initMap() {
  const map = L.map('map', {
    center:           [15.35, 44.20],
    zoom:             AQ.Device.isMobile() ? 10 : 11,
    zoomControl:      false,
    attributionControl: false,
    tap:              true,
  });

  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 18
  }).addTo(map);

  L.control.zoom({ position: 'topright' }).addTo(map);

  // ── Marker icon ────────────────────────────────────────────────
  const markerIcon = L.divIcon({
    html: `<div style="
      width:20px;height:20px;
      background:radial-gradient(circle,#00c9a7,#009980);
      border:2px solid #050d1a;border-radius:50%;
      box-shadow:0 0 0 4px rgba(0,201,167,0.25),0 0 20px rgba(0,201,167,0.4);
      animation:pulse 2s infinite"></div>`,
    className: '', iconSize: [20, 20], iconAnchor: [10, 10]
  });

  // ── Well markers ───────────────────────────────────────────────
  const wellLayerGroup = L.layerGroup();
  WELL_DATA.forEach(w => {
    const color = w.ok
      ? (w.aq === 'T' ? '#00c9a7' : w.aq === 'Q' ? '#22c55e' : '#0ea5e9')
      : '#ef4444';

    const icon = L.divIcon({
      html: `<div style="width:10px;height:10px;background:${color};
        border:1.5px solid #050d1a;border-radius:50%;
        box-shadow:0 0 6px ${color}55"></div>`,
      className: '', iconSize: [10, 10], iconAnchor: [5, 5]
    });

    L.marker([w.lat, w.lon], { icon })
      .bindPopup(`
        <div style="direction:rtl;min-width:140px">
          <div style="font-weight:700;color:#00c9a7;margin-bottom:4px">${w.id}</div>
          <div>العمق: ${w.depth ? w.depth + 'م' : 'بئرٌ جافة'}</div>
          <div>الإنتاجية: ${w.yield}</div>
          <div>الطبقة: ${{ Q: 'رباعية', V: 'بركانية', T: 'توائلي', A: 'عمران' }[w.aq]}</div>
        </div>
      `)
      .addTo(wellLayerGroup);
  });
  wellLayerGroup.addTo(map);

  // ── Fault lines ────────────────────────────────────────────────
  const faultLayerGroup = L.layerGroup();
  [[15.20, 44.10, 15.55, 44.45], [15.15, 44.30, 15.60, 44.15], [15.30, 44.05, 15.48, 44.50]]
    .forEach(([y1, x1, y2, x2]) => {
      L.polyline([[y1, x1], [y2, x2]], {
        color: 'rgba(239,68,68,0.35)', weight: 1.5, dashArray: '6,4'
      }).addTo(faultLayerGroup);
    });
  faultLayerGroup.addTo(map);

  // ── Tawilah boundary ───────────────────────────────────────────
  const tawilahLayerGroup = L.layerGroup();
  L.polyline([[15.35, 43.7], [15.35, 44.9]], {
    color: 'rgba(245,158,11,0.6)', weight: 2, dashArray: '8,4'
  }).bindPopup(
    '<div style="color:#f59e0b;font-weight:700">حدّ انتشار التوائلي الشمالي<br>' +
    '<span style="font-size:0.75rem;color:#999">شمال خط عرض 15.35° — لا توجد طبقة توائلي</span></div>'
  ).addTo(tawilahLayerGroup);

  // ── GRACE heatmap ──────────────────────────────────────────────
  const graceLayerGroup = L.layerGroup();
  [
    { c: [15.38, 44.22], r: 4000, color: '#ef4444', op: 0.12 },
    { c: [15.45, 44.15], r: 3000, color: '#f59e0b', op: 0.10 },
    { c: [15.28, 44.30], r: 3500, color: '#f59e0b', op: 0.09 },
    { c: [15.20, 44.20], r: 2500, color: '#22c55e', op: 0.08 },
  ].forEach(z => {
    L.circle(z.c, {
      radius: z.r, color: z.color,
      fillColor: z.color, fillOpacity: z.op, weight: 0
    }).addTo(graceLayerGroup);
  });
  graceLayerGroup.addTo(map);

  // ── Layer registry ─────────────────────────────────────────────
  const layerMap = {
    faults: faultLayerGroup, grace: graceLayerGroup,
    wells: wellLayerGroup,   tawilah: tawilahLayerGroup,
  };

  // ── Map events ─────────────────────────────────────────────────
  map.on('click', e => {
    State.selectedLat = +e.latlng.lat.toFixed(4);
    State.selectedLon = +e.latlng.lng.toFixed(4);
    placeMarker(map, markerIcon, State.selectedLat, State.selectedLon);
    updateCoordDisplay();
    if (AQ.Device.isMobile()) pulseFAB();
  });

  map.on('mousemove', e => {
    if (!State.marker) {
      const el = document.getElementById('mapCoords');
      if (el) el.textContent = `${e.latlng.lat.toFixed(4)}°N · ${e.latlng.lng.toFixed(4)}°E`;
    }
  });

  // Place initial marker
  placeMarker(map, markerIcon, State.selectedLat, State.selectedLon);

  // Resize fix
  window.addEventListener('resize', AQ.debounce(() => map.invalidateSize(), 200));
  window.addEventListener('load', () => setTimeout(() => map.invalidateSize(), 200));

  return { map, markerIcon, layerMap };
}

// ══════════════════════════════════════════════════════════════════════
//  MARKER & COORD HELPERS
// ══════════════════════════════════════════════════════════════════════
function placeMarker(map, icon, lat, lon) {
  if (State.marker) map.removeLayer(State.marker);
  State.marker = L.marker([lat, lon], { icon }).addTo(map);

  ['latInput', 'lonInput', 'latInputM', 'lonInputM'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = id.includes('lat') ? lat : lon;
  });
}

function updateCoordDisplay() {
  const t = `${State.selectedLat.toFixed(4)}°N · ${State.selectedLon.toFixed(4)}°E · تم تحديد الموقع ✓`;
  const el = document.getElementById('coordDisplay');
  if (el) el.textContent = t;
  const coords = document.getElementById('mapCoords');
  if (coords) {
    coords.textContent = `${State.selectedLat.toFixed(4)}°N · ${State.selectedLon.toFixed(4)}°E` +
      ` · ارتفاع ~${Math.round(2150 + Math.random() * 300)}م`;
  }
}

function pulseFAB() {
  const fab = document.getElementById('mapFab');
  if (!fab) return;
  fab.style.boxShadow = '0 4px 36px rgba(0,201,167,0.75)';
  setTimeout(() => { fab.style.boxShadow = '0 4px 24px rgba(0,201,167,0.45)'; }, 600);
}

// ══════════════════════════════════════════════════════════════════════
//  AI ANALYSIS ENGINE
// ══════════════════════════════════════════════════════════════════════
// ══════════════════════════════════════════════════════════════════════
//  API CONFIG
//  غيّر هذا العنوان عند نشر الـ Backend على سيرفر حقيقي
// ══════════════════════════════════════════════════════════════════════
const API_URL = 'http://localhost:8000';
let   API_ONLINE = false;

// فحص إذا كان الـ API يعمل عند تحميل الصفحة
async function checkAPIStatus() {
  try {
    const res = await fetch(`${API_URL}/health`, { signal: AbortSignal.timeout(3000) });
    if (res.ok) {
      API_ONLINE = true;
      const badge = document.getElementById('apiBadge');
      if (badge) {
        badge.textContent = '🟢 Python API';
        badge.style.color = 'var(--teal, #00dcb4)';
      }
      console.log('✅ AquaLens Python API متصل');
    }
  } catch {
    API_ONLINE = false;
    console.warn('⚠️  Python API غير متصل — سيعمل وضع المحاكاة');
  }
}
checkAPIStatus();

// ══════════════════════════════════════════════════════════════════════
//  تحويل استجابة API إلى الشكل الذي يتوقعه fillPanel()
// ══════════════════════════════════════════════════════════════════════
function normalizeAPIResponse(r, lat, lon) {
  const mobile  = AQ.Device.isMobile();
  const sfx     = mobile ? 'M' : '';
  const useFE   = document.getElementById('feToggle' + sfx)?.checked ?? true;

  const yieldMap = {
    low:    { val: '٢–٥',  label: 'منخفضة',       cost: '$8,000–$15,000'  },
    medium: { val: '٥–١٢', label: 'متوسطة',        cost: '$18,000–$28,000' },
    high:   { val: '٨–٢٠', label: 'متوسطة–عالية',  cost: '$22,000–$38,000' },
  };

  const depth    = r.depth_p50_m;
  const depthMin = r.depth_p10_m;
  const depthMax = r.depth_p90_m;
  const yClass   = r.yield_class || 'medium';

  // القيود الجيولوجية → risk
  let risk = '✅ الموقع ملائمٌ — لا قيود جيولوجية حرجة';
  let riskLevel = 'low';
  if (r.constraints && r.constraints.length > 0) {
    const worst = r.constraints.find(c => c.severity === 'HIGH')
               || r.constraints.find(c => c.severity === 'MEDIUM')
               || r.constraints[0];
    risk      = worst.msg_ar;
    riskLevel = worst.severity === 'HIGH' ? 'high' : 'med';
  } else if (r.depletion_rate_m_year > 7) {
    risk      = '🔴 معدل استنزافٍ مرتفع — يُستحسن التوسع نحو الجنوب';
    riskLevel = 'med';
  }

  const fe = r.formation_eval;

  return {
    aquifer:      r.aquifer,
    confidence:   r.confidence_pct,
    depletionRate: r.depletion_rate_m_year,
    depth, depthMin, depthMax,
    yield:    yieldMap[yClass] || yieldMap.medium,
    risk, riskLevel,
    feData: (useFE && fe && fe.Sw !== null) ? {
      Sw:  fe.Sw / 100,
      phi: fe.phi / 100,
      pay: fe.pay_m + ' م',
      Rt:  fe.Rt + ' Ω·m',
    } : null,
    specs: {
      method:   r.drilling_specs.method,
      diameter: r.drilling_specs.dia || (r.aquifer === 'Q' ? '٦ إنش' : '٨ إنش'),
      casing:   r.drilling_specs.casing,
      pump:     r.drilling_specs.pump,
      duration: r.drilling_specs.dur,
      cost:     r.drilling_specs.cost_usd,
    },
    graceData: {
      years: r.grace_years,
      tws:   r.grace_tws,
    },
  };
}

// ══════════════════════════════════════════════════════════════════════
//  المحاكاة (Fallback) — تعمل عند عدم اتصال API
// ══════════════════════════════════════════════════════════════════════
function simulateLocally(lat, lon) {
  const mobile     = AQ.Device.isMobile();
  const sfx        = mobile ? 'M' : '';
  const useGrace   = document.getElementById('graceToggle' + sfx)?.checked ?? true;
  const useGeo     = document.getElementById('geoToggle'   + sfx)?.checked ?? true;
  const useFE      = document.getElementById('feToggle'    + sfx)?.checked ?? true;
  const year       = parseInt(document.getElementById('yearInput' + sfx)?.value ?? '2026');
  const yearDelta  = year - 2010;

  const northOfTawilah = lat > 15.35;
  const nearFault      = (Math.abs(lon - 44.2) + Math.abs(lat - 15.3)) < 0.15;
  const inWadi         = lat < 15.28 || (lon > 44.35 && lat < 15.40);

  let aquifer, confBase;
  if      (inWadi && !northOfTawilah)                    { aquifer = 'Q'; confBase = 72; }
  else if (northOfTawilah && useGeo)                     { aquifer = 'V'; confBase = 68; }
  else if (!northOfTawilah && lon > 44.05 && lon < 44.5) { aquifer = 'T'; confBase = 76; }
  else if (nearFault)                                    { aquifer = 'A'; confBase = 62; }
  else                                                   { aquifer = 'V'; confBase = 65; }

  const confidence    = confBase + Math.round((Math.random() - 0.5) * 8);
  const baseDepletion = { Q: 4.2, V: 6.8, T: 7.3, A: 3.1 }[aquifer];
  const depletionRate = useGrace ? +(baseDepletion + (Math.random() - 0.5) * 1.2).toFixed(1) : null;
  const baseDepths    = { Q: 35, V: 120, T: 220, A: 380 };
  const depth         = Math.round(baseDepths[aquifer] + Math.round(Math.random() * 40) + (depletionRate ? depletionRate * yearDelta : 0));
  const depthMin      = Math.round(depth * 0.88);
  const depthMax      = Math.round(depth * 1.15);
  const yieldMap      = {
    Q: { val: '٢–٥',  label: 'منخفضة',       cost: '$8,000–$15,000'  },
    V: { val: '٥–١٢', label: 'متوسطة',        cost: '$18,000–$28,000' },
    T: { val: '٨–٢٠', label: 'متوسطة–عالية',  cost: '$22,000–$38,000' },
    A: { val: '٣–٨',  label: 'منخفضة–متوسطة', cost: '$30,000–$50,000' },
  };
  let risk = '✅ الموقع ملائمٌ — لا قيود جيولوجية حرجة', riskLevel = 'low';
  if (northOfTawilah && aquifer === 'T' && useGeo) { risk = '⚠️ التوائلي غائب شمال 15.35°'; riskLevel = 'high'; }
  else if (aquifer === 'A' && !nearFault)           { risk = '⚠️ عمران بعيد عن الصدوع';      riskLevel = 'med';  }
  else if (depletionRate && depletionRate > 7)      { risk = '🔴 استنزاف مرتفع';              riskLevel = 'med';  }
  const feData = useFE ? { Sw: +(0.55 + Math.random() * 0.25).toFixed(2), phi: +(0.08 + Math.random() * 0.10).toFixed(2), pay: Math.round(15 + Math.random() * 30) + ' م', Rt: Math.round(8 + Math.random() * 20) + ' Ω·m' } : null;
  const drillMethods = { Q: 'حفر دوراني مباشر', V: 'حفر هوائي DTH', T: 'حفر دوراني بطين', A: 'حفر ماسي' };
  const casingMap    = { Q: `سطحي ٢٠م | منقّب ${Math.round(depthMin*0.6)}–${depthMin}م`, V: `سطحي ٤٠م | مُبطّن ٤٠–${Math.round(depth*0.5)}م`, T: `سطحي ٦٠م | مُبطّن ٦٠–${Math.round(depth*0.6)}م`, A: `مُبطّن كامل حتى ${depth}م` };
  const graceYears = Array.from({ length: 24 }, (_, i) => 2003 + i);
  const graceTWS   = graceYears.map(y => +(-(depletionRate ?? 5) * (y - 2003) * 0.12 + (Math.random() - 0.5) * 1.8).toFixed(2));

  return { aquifer, confidence, depletionRate, depth, depthMin, depthMax, yield: yieldMap[aquifer], risk, riskLevel, feData,
    specs: { method: drillMethods[aquifer], diameter: aquifer === 'Q' ? '٦ إنش' : '٨ إنش', casing: casingMap[aquifer], pump: `غاطس ${depth < 300 ? '١٥' : '٢٢'} كيلوواط`, duration: `${Math.round(depth/35)+3}–${Math.round(depth/28)+5} أسابيع`, cost: yieldMap[aquifer].cost },
    graceData: { years: graceYears, tws: graceTWS },
  };
}

// ══════════════════════════════════════════════════════════════════════
//  getAquiferData — الدالة الرئيسية (API أولاً، ثم محاكاة احتياطية)
// ══════════════════════════════════════════════════════════════════════
async function getAquiferData(lat, lon) {
  const mobile   = AQ.Device.isMobile();
  const sfx      = mobile ? 'M' : '';
  const useGrace = document.getElementById('graceToggle' + sfx)?.checked ?? true;
  const useGeo   = document.getElementById('geoToggle'   + sfx)?.checked ?? true;
  const useFE    = document.getElementById('feToggle'    + sfx)?.checked ?? true;
  const year     = parseInt(document.getElementById('yearInput' + sfx)?.value ?? '2026');

  // ── محاولة استدعاء الـ API الحقيقي ──────────────────────────────
  if (API_ONLINE) {
    try {
      const res = await fetch(`${API_URL}/analyze`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({
          latitude:  lat,
          longitude: lon,
          year,
          use_grace: useGrace,
          use_geo:   useGeo,
          use_fe:    useFE,
        }),
        signal: AbortSignal.timeout(15000),
      });

      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const data = await res.json();
      console.log('📡 نتيجة من Python API:', data);
      return normalizeAPIResponse(data, lat, lon);

    } catch (err) {
      console.warn('⚠️  API فشل، التحويل للمحاكاة:', err.message);
      API_ONLINE = false;
    }
  }

  // ── المحاكاة الاحتياطية ───────────────────────────────────────
  console.log('🔄 وضع المحاكاة (API غير متصل)');
  return simulateLocally(lat, lon);
}

// ══════════════════════════════════════════════════════════════════════
//  RENDER RESULTS
// ══════════════════════════════════════════════════════════════════════
function fillPanel(data, aq, suffix, setChart) {
  const g = id => document.getElementById(id + suffix);

  g('aqNameAr').textContent  = aq.ar;
  g('aqNameAr').style.color  = aq.color;
  g('aqNameEn').textContent  = aq.en;
  g('confVal').textContent   = data.confidence + '%';
  g('confFill').style.width  = data.confidence + '%';
  g('confFill').style.background = `linear-gradient(90deg,${aq.color},#0ea5e9)`;

  const riskEl = g('riskAlert');
  riskEl.className = 'risk-alert ' + { low: 'risk-low', med: 'risk-med', high: 'risk-high' }[data.riskLevel];
  riskEl.textContent = data.risk;

  g('depthMain').textContent     = data.depth + ' م';
  g('depletionRate').textContent = data.depletionRate ? '▼ ' + data.depletionRate + ' م/سنة' : 'غير مُفعَّل';
  g('yieldVal').textContent      = data.yield.val + ' ل/ث';
  g('costVal').textContent       = '$' + data.yield.cost.split('$')[1].split('–')[0] + 'k';

  // Depth uncertainty bar
  const total    = 1200;
  const leftPct  = (data.depthMin / total * 100).toFixed(1);
  const widthPct = ((data.depthMax - data.depthMin) / total * 100).toFixed(1);
  const midPct   = (data.depth / total * 100).toFixed(1);
  g('rangeFill').style.left  = leftPct + '%';
  g('rangeFill').style.width = widthPct + '%';
  g('rangeMarker').style.left = midPct + '%';
  g('rangeMin').textContent  = data.depthMin + 'م';
  g('rangeMid').textContent  = data.depth + ' م (P50)';
  g('rangeMax').textContent  = data.depthMax + 'م';

  // Spec table
  const specs = [
    ['طريقة الحفر',        data.specs.method],
    ['قطر البئر',          data.specs.diameter],
    ['برنامج التغليف',     data.specs.casing],
    ['المضخة المقترحة',    data.specs.pump],
    ['مدة الحفر التقديرية',data.specs.duration],
    ['التكلفة الإجمالية',  data.specs.cost],
  ];
  g('specTable').innerHTML = specs.map(([l, v]) =>
    `<tr><td>${l}</td><td>${v}</td></tr>`
  ).join('');

  // Formation evaluation
  if (data.feData) {
    g('swVal').textContent  = (data.feData.Sw  * 100).toFixed(0) + '%';
    g('phiVal').textContent = (data.feData.phi * 100).toFixed(0) + '%';
    g('payVal').textContent = data.feData.pay;
    g('rtVal').textContent  = data.feData.Rt;
  }

  // GRACE Chart
  const canvas = document.getElementById('graceChart' + suffix);
  if (canvas) {
    if (setChart._current) setChart._current.destroy();
    const ctx  = canvas.getContext('2d');
    const grad = ctx.createLinearGradient(0, 0, 0, 120);
    grad.addColorStop(0, 'rgba(239,68,68,0.3)');
    grad.addColorStop(1, 'rgba(239,68,68,0.02)');

    const chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: data.graceData.years,
        datasets: [{
          label: 'TWS Anomaly (cm)',
          data:  data.graceData.tws,
          borderColor:     '#ef4444',
          backgroundColor: grad,
          borderWidth: 1.5,
          pointRadius: 0,
          fill: true,
          tension: 0.35,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: c => `${c.parsed.y.toFixed(2)} cm EWH` } }
        },
        scales: {
          x: { ticks: { color: '#6b9ab8', font: { size: 9 }, maxTicksLimit: 6 }, grid: { color: 'rgba(255,255,255,0.04)' } },
          y: { ticks: { color: '#6b9ab8', font: { size: 9 } },                   grid: { color: 'rgba(255,255,255,0.04)' },
               title: { display: true, text: 'cm EWH', color: '#6b9ab8', font: { size: 9 } } }
        }
      }
    });
    setChart._current = chart;
  }
}

// ══════════════════════════════════════════════════════════════════════
//  EXPORT
// ══════════════════════════════════════════════════════════════════════
window.Dashboard = {
  State, AQ_LABELS, WELL_DATA,
  initMap, placeMarker, updateCoordDisplay,
  getAquiferData, fillPanel,
};
