# 💧 AquaLens — AI Groundwater Exploration Platform

> استكشاف المياه الجوفية بالذكاء الاصطناعي والبيانات الفضائية

---

## 📁 File Structure

```
aqualens/
│
├── index.html              ← الصفحة الرئيسية (Landing Page)
├── dashboard.html          ← لوحة التحكم — AI Analysis Dashboard
│
├── assets/
│   ├── css/
│   │   ├── base.css        ← متغيرات CSS المشتركة، Reset، Animation tokens
│   │   ├── landing.css     ← أنماط الصفحة الرئيسية فقط  [TODO]
│   │   └── dashboard.css   ← أنماط لوحة التحكم فقط      [TODO]
│   │
│   ├── js/
│   │   ├── shared.js       ← أدوات مشتركة: cursor, toast, counter, device utils
│   │   ├── landing.js      ← Particles, typewriter, scroll reveal, stats counter
│   │   └── dashboard.js    ← Map engine, AI analysis, results renderer, drawers
│   │
│   └── img/
│       ├── logo.svg        ← شعار AquaLens (SVG)          [TODO]
│       ├── favicon.ico     ← أيقونة الموقع                [TODO]
│       └── og-image.png    ← صورة مشاركة السوشيال ميديا   [TODO]
│
├── pages/
│   ├── research.html       ← الورقة البحثية               [Placeholder]
│   └── about.html          ← عن المشروع                   [Placeholder]
│
└── README.md               ← هذا الملف
```

---

## 🔗 Page Navigation

| من | إلى | الزناد |
|---|---|---|
| `index.html` | `dashboard.html` | زر "ابدأ التحليل" في Nav |
| `index.html` | `dashboard.html` | زر "ابدأ التحليل مجاناً" في Hero |
| `index.html` | `dashboard.html` | زر "جرّب النموذج الأولي" في CTA |
| `dashboard.html` | `index.html` | شعار AquaLens في TopBar |

---

## 📱 Mobile Support

`dashboard.html` يدعم الأجهزة المحمولة بالكامل:
- **Bottom Navigation** — تبديل بين الخريطة / الإدخال / النتائج
- **Slide-up Drawers** — لوحة الإدخال ولوحة النتائج
- **Floating Action Button (FAB)** — زر تحليل عائم فوق الخريطة
- **Safe Area Insets** — دعم الـ notch في iPhone وأجهزة Android الحديثة
- **Touch Events** — `tap: true` في Leaflet لدعم الإسقاط باللمس

---

## 🚀 Deployment (Free Hosting)

### Netlify (موصى به)
1. اذهب إلى [netlify.com](https://netlify.com)
2. اسحب مجلد `aqualens/` كاملاً وأفلته على واجهة Netlify
3. الموقع يعمل فوراً على `yourname.netlify.app`

### بدائل
- **Vercel** → `vercel --prod` من command line
- **GitHub Pages** → ارفع المجلد على GitHub ثم فعّل Pages من الإعدادات

---

## 🛠 Tech Stack

| المكوّن | التقنية |
|---|---|
| خريطة تفاعلية | Leaflet.js 1.9 |
| مخططات البيانات | Chart.js 4.4 |
| الخطوط | Tajawal · IBM Plex Mono · Syne |
| تحليل AI | محاكاة XGBoost + Archie's Law |
| بيانات الاستنزاف | GRACE-FO (محاكاة) |
| مرئيات فضائية | Sentinel-2 / SRTM (محاكاة) |
| الاستضافة | Netlify / Vercel / GitHub Pages |

---

## 🎨 Logo Prompt

```
A minimalist logo for "AquaLens" —
a circular lens shape made of water ripple rings,
with a subtle satellite signal beam passing through it from above.
The center glows in teal (#00c9a7) with deep navy blue (#050d1a) background.
Geometric, technical, clean.
Style: flat vector icon, suitable for dark UI dashboards.
No text. High contrast. 2D.
```

> أفضل أداة لتوليد SVG: **[Recraft.ai](https://recraft.ai)**

---

## 📌 TODO

- [ ] استخراج CSS إلى `landing.css` و `dashboard.css`
- [ ] إضافة شعار SVG حقيقي
- [ ] تكامل GRACE-FO API الحقيقي
- [ ] صفحة `research.html` الكاملة
- [ ] صفحة `about.html` الكاملة
- [ ] تصدير PDF حقيقي بـ ReportLab أو jsPDF
- [ ] نظام مصادقة للمستخدمين
