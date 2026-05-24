#!/usr/bin/env bash
# ============================================================
#  CVFPM — تشغيل يدوي سريع
# ============================================================
INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$INSTALL_DIR/.venv"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  CVFPM — نظام الصيانة التنبؤية"
echo "  المطور: Mostafa Eisaa  |  775166114"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd "$INSTALL_DIR"

# تنشيط venv إن وُجد
if [ -d "$VENV_DIR" ]; then
    source "$VENV_DIR/bin/activate"
    echo "✔ البيئة الافتراضية نشطة"
fi

PORT=$(python3 -c "import json; c=json.load(open('config.json')); print(c.get('dashboard_port',5000))" 2>/dev/null || echo "5000")
IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

echo "✔ بدء التشغيل على: http://${IP}:${PORT}"
echo "  (اضغط Ctrl+C للإيقاف)"
echo ""

python3 main.py
