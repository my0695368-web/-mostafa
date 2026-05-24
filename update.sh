#!/usr/bin/env bash
# ============================================================
#  CVFPM — سكريبت التحديث
#  يحدّث الملفات ويُطبّق التغييرات بدون إيقاف الخدمة
#  الاستخدام:
#    bash update.sh              ← تحديث الكود فقط
#    bash update.sh new.zip      ← تثبيت إصدار جديد من ملف ZIP
# ============================================================
set -e

INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_NAME="cvfpm"
BACKUP_DIR="$INSTALL_DIR/.backups"
VENV_DIR="$INSTALL_DIR/.venv"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✔ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠ $1${NC}"; }
step() { echo -e "\n${YELLOW}━━ $1${NC}"; }

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║       CVFPM — نظام التحديث التلقائي          ║"
echo "║  المطور: Mostafa Eisaa  |  775166114          ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ── حفظ نسخة احتياطية ───────────────────────────────────────
step "حفظ نسخة احتياطية"
mkdir -p "$BACKUP_DIR"
# احفظ الكود فقط (ليس السجلات والبيانات)
for f in main.py web_dashboard.py ai_engine.py alert_system.py sensor_reader.py; do
    [ -f "$INSTALL_DIR/$f" ] && cp "$INSTALL_DIR/$f" "$BACKUP_DIR/${f}.${TIMESTAMP}.bak"
done
ok "نسخة احتياطية محفوظة في .backups/"

# ── تحديث من ZIP ────────────────────────────────────────────
if [ -n "$1" ] && [ -f "$1" ]; then
    ZIP_FILE="$1"
    step "تحديث من ملف ZIP: $ZIP_FILE"

    TMP_DIR=$(mktemp -d)
    unzip -q "$ZIP_FILE" -d "$TMP_DIR"

    # اكتشاف المجلد داخل ZIP تلقائياً
    SRC_DIR=$(find "$TMP_DIR" -name "main.py" -printf '%h\n' | head -1)
    [ -z "$SRC_DIR" ] && { echo -e "${RED}✘ لم يُوجد main.py داخل ZIP${NC}"; exit 1; }

    # انسخ الكود فقط (احتفظ بـ config.json وقواعد البيانات)
    for f in main.py web_dashboard.py ai_engine.py alert_system.py sensor_reader.py requirements.txt; do
        [ -f "$SRC_DIR/$f" ] && cp "$SRC_DIR/$f" "$INSTALL_DIR/$f" && echo "  ← $f"
    done

    rm -rf "$TMP_DIR"
    ok "تم نسخ الملفات الجديدة"

    # تحديث المكتبات
    step "تحديث المكتبات"
    if [ -d "$VENV_DIR" ]; then
        source "$VENV_DIR/bin/activate"
        pip install -r "$INSTALL_DIR/requirements.txt" -q
        ok "تم تحديث المكتبات"
    fi
fi

# ── تحديث config.json بدون إعادة تشغيل ─────────────────────
step "تطبيق تغييرات الإعدادات (hot reload)"
# إرسال إشارة reload للخدمة
if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
    # إرسال طلب hot reload عبر API
    PORT=$(python3 -c "import json; c=json.load(open('$INSTALL_DIR/config.json')); print(c.get('dashboard_port',5000))" 2>/dev/null || echo "5000")
    RELOAD_RESP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "http://localhost:${PORT}/api/reload" 2>/dev/null || echo "000")

    if [ "$RELOAD_RESP" = "200" ]; then
        ok "تم تطبيق تغييرات config.json بدون إعادة تشغيل ✨"
    else
        warn "فشل hot reload — سيتم إعادة تشغيل الخدمة..."
        sudo systemctl restart "$SERVICE_NAME"
        sleep 2
        ok "تم إعادة تشغيل الخدمة"
    fi
else
    warn "الخدمة غير نشطة — شغّل: bash start.sh"
fi

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║         ✔  تم التحديث بنجاح                 ║"
echo "║  إعادة نسخة سابقة: ls .backups/              ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
