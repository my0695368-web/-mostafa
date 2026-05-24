# CVFPM — نظام الصيانة التنبؤية الذكي
## Collective Vibration Fingerprint for Predictive Maintenance

**المطور:** Mostafa Eisaa  |  📞 775166114

---

## هيكل الملفات
```
cvfpm/
├── main.py             ← نقطة الدخول (يدعم hot reload)
├── config.json         ← إعدادات الآلات والبريد
├── sensor_reader.py    ← قراءة MPU-6050 + MLX90614
├── ai_engine.py        ← تحليل الاهتزاز وتقدير RUL
├── alert_system.py     ← تنبيهات البريد ولوحة التحكم
├── web_dashboard.py    ← Flask — لوحة ويب سريعة
├── requirements.txt    ← المكتبات المطلوبة
├── install.sh          ← تثبيت تلقائي (أمر واحد)
├── update.sh           ← تحديث النظام بدون إيقاف
├── start.sh            ← تشغيل يدوي سريع
└── README.md           ← هذا الملف
```

---

## التثبيت (أمر واحد)

```bash
bash install.sh
```

يقوم بـ:
- إنشاء بيئة Python افتراضية
- تثبيت كل المكتبات
- تسجيل خدمة systemd (تعمل تلقائياً عند الإقلاع)

---

## التشغيل اليدوي

```bash
bash start.sh
```

---

## التحديث

### تحديث الإعدادات (config.json) بدون إيقاف:
```bash
bash update.sh
```
يرسل طلب hot reload للنظام — لا حاجة لإعادة التشغيل.

### تثبيت إصدار جديد من ملف ZIP:
```bash
bash update.sh CVFPM_vNew.zip
```
- يحفظ نسخة احتياطية تلقائياً في `.backups/`
- يحتفظ بـ `config.json` وبيانات المحاكاة
- يحدّث المكتبات تلقائياً

---

## إدارة الخدمة

```bash
sudo systemctl status  cvfpm     # حالة الخدمة
sudo systemctl restart cvfpm     # إعادة تشغيل
sudo systemctl stop    cvfpm     # إيقاف
sudo systemctl start   cvfpm     # تشغيل
tail -f cvfpm.log                # متابعة السجلات
```

---

## إعداد config.json

```json
{
  "monitoring_interval_seconds": 30,
  "dashboard_port": 5000,
  "email": {
    "enabled": true,
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "sender": "your_email@gmail.com",
    "password": "xxxx xxxx xxxx xxxx",
    "recipients": ["manager@company.com"],
    "cooldown_minutes": 30
  },
  "machines": [ ... ]
}
```

---

## API Endpoints

| Endpoint | Method | الوظيفة |
|----------|--------|---------|
| `/` | GET | لوحة التحكم |
| `/api/state` | GET | حالة الآلات والتنبيهات |
| `/api/reload` | POST | **hot reload** للإعدادات |
| `/api/machines` | GET | قائمة الآلات |
| `/api/machines` | POST | إضافة آلة جديدة |
| `/api/config` | GET | الإعدادات الحالية |
| `/api/resolve/<id>` | POST | تعليم تنبيه كمُحلّ |

---

## متطلبات
- Raspberry Pi 4 أو أي Linux
- Python 3.10+
- حساسات: MPU-6050 × 3 + MLX90614 × 3 (اختياري — وضع محاكاة تلقائي)
