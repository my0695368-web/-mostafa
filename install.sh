#!/usr/bin/env bash
# ============================================================
#  CVFPM — سكريبت التثبيت التلقائي
#  المطور: Mostafa Eisaa  |  775166114
#  الاستخدام: bash install.sh
# ============================================================
set -e

INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_NAME="cvfpm"
PYTHON="python3"
PIP="pip3"
SERVICE_USER="${SUDO_USER:-$USER}"
VENV_DIR="$INSTALL_DIR/.venv"

# ألوان
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✔ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠ $1${NC}"; }
err()  { echo -e "${RED}✘ $1${NC}"; exit 1; }
step() { echo -e "\n${YELLOW}━━ $1${NC}"; }

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  CVFPM — نظام الصيانة التنبؤية الذكي         ║"
echo "║  المطور: Mostafa Eisaa  |  775166114          ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ── 1. Python ───────────────────────────────────────────────
step "فحص Python"
$PYTHON --version &>/dev/null || err "Python3 غير مثبت — قم بتثبيته أولاً"
ok "Python متوفر: $($PYTHON --version)"

# ── 2. بيئة افتراضية ────────────────────────────────────────
step "إنشاء البيئة الافتراضية (venv)"
if [ ! -d "$VENV_DIR" ]; then
    $PYTHON -m venv "$VENV_DIR"
    ok "تم إنشاء .venv"
else
    ok "البيئة الافتراضية موجودة مسبقاً"
fi

source "$VENV_DIR/bin/activate"
pip install --upgrade pip -q

# ── 3. المكتبات ──────────────────────────────────────────────
step "تثبيت المكتبات"
pip install -r "$INSTALL_DIR/requirements.txt" -q
ok "تم تثبيت جميع المكتبات"

# PyTorch اختياري
read -p "هل تريد تثبيت PyTorch؟ (يستغرق وقتاً طويلاً) [y/N]: " TORCH_CHOICE
if [[ "$TORCH_CHOICE" =~ ^[Yy]$ ]]; then
    pip install torch --index-url https://download.pytorch.org/whl/cpu -q
    ok "تم تثبيت PyTorch"
fi

# ── 4. صلاحيات التنفيذ ──────────────────────────────────────
step "إعداد صلاحيات الملفات"
chmod +x "$INSTALL_DIR/update.sh"
chmod +x "$INSTALL_DIR/start.sh"
ok "تم إعداد الصلاحيات"

# ── 5. خدمة systemd ─────────────────────────────────────────
step "إعداد خدمة systemd"
if command -v systemctl &>/dev/null; then

    VENV_PYTHON="$VENV_DIR/bin/python"
    GUNICORN_BIN="$VENV_DIR/bin/gunicorn"

    sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null <<EOF
[Unit]
Description=CVFPM — نظام الصيانة التنبؤية الذكي
After=network.target

[Service]
Type=simple
User=${SERVICE_USER}
WorkingDirectory=${INSTALL_DIR}
ExecStart=${VENV_PYTHON} ${INSTALL_DIR}/main.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable ${SERVICE_NAME}
    ok "خدمة systemd مُعدَّة ومفعّلة"

    read -p "هل تريد تشغيل الخدمة الآن؟ [y/N]: " START_NOW
    if [[ "$START_NOW" =~ ^[Yy]$ ]]; then
        sudo systemctl start ${SERVICE_NAME}
        sleep 2
        sudo systemctl status ${SERVICE_NAME} --no-pager | head -15
        ok "الخدمة تعمل الآن"
    fi
else
    warn "systemd غير متوفر — استخدم ./start.sh للتشغيل اليدوي"
fi

# ── 6. ملخص ─────────────────────────────────────────────────
PORT=$(python3 -c "import json; c=json.load(open('config.json')); print(c.get('dashboard_port',5000))" 2>/dev/null || echo "5000")

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║         ✔  تم التثبيت بنجاح                 ║"
echo "╠══════════════════════════════════════════════╣"
echo "║  لوحة التحكم: http://$(hostname -I | awk '{print $1}'):${PORT}   ║"
echo "║  التشغيل اليدوي:  bash start.sh              ║"
echo "║  التحديث:         bash update.sh             ║"
echo "║  السجلات:         tail -f cvfpm.log           ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
