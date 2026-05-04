#!/bin/bash
# ══════════════════════════════════════════════════════
#  AquaLens — backend/run.sh
#  سكريبت تشغيل الـ Backend
#
#  الاستخدام:
#    cd backend
#    bash run.sh
# ══════════════════════════════════════════════════════

echo ""
echo "💧 AquaLens — Python Backend"
echo "════════════════════════════"

# تثبيت المكتبات إذا لم تكن موجودة
if ! python3 -c "import fastapi" 2>/dev/null; then
  echo "⚙️  تثبيت المكتبات..."
  pip install -r requirements.txt
fi

echo ""
echo "🚀 تشغيل الـ API على http://localhost:8000"
echo "📖 التوثيق على  http://localhost:8000/docs"
echo "⏹  للإيقاف: Ctrl+C"
echo ""

python3 api.py
