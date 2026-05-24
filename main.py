"""
CVFPM - الملف الرئيسي للنظام (النسخة السحابية المستقرة)
المطور: Mostafa Eisaa
التعديل: دعم التشغيل الهجين (حقيقي/محاكاة) والتوافق الكامل مع Render
"""

import json, time, threading, logging, os, signal, sys
from datetime import datetime

# استيراد مكونات النظام
from sensor_reader import SensorReader
from ai_engine import AIEngine
from alert_system import AlertSystem
from web_dashboard import create_app

# إعداد السجلات (Logging)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)

# تحديد مسار ملف الإعدادات
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')

def load_config():
    """تحميل الإعدادات من ملف JSON"""
    if not os.path.exists(CONFIG_FILE):
        # إعدادات افتراضية في حال فقدان الملف
        return {
            "monitoring_interval_seconds": 10,
            "dashboard_port": 5000,
            "machines": [{"id": "DEFAULT", "name": "ماكينة افتراضية", "type": "Test"}]
        }
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def monitoring_loop(config_ref, ai_engine, alert_system, shared_state, stop_event):
    """حلقة المراقبة الرئيسية"""
    # تهيئة قارئ الحساسات (سيكتشف تلقائياً إذا كان هناك حساسات أم لا)
    sensor_reader = SensorReader(config_ref[0])
    
    logging.info(f"وضع العمل الحالي: {sensor_reader.source_label}")

    while not stop_event.is_set():
        config = config_ref[0]
        interval = config.get('monitoring_interval_seconds', 10)

        try:
            for machine in config.get('machines', []):
                mid = machine['id']
                # قراءة البيانات (إما حقيقية أو محاكاة ذكية)
                data = sensor_reader.read(machine)

                if data is None: continue

                # تحليل البيانات بواسطة محرك الذكاء الاصطناعي
                result = ai_engine.analyze(mid, data)

                # تحديث الحالة المشتركة التي تظهر على لوحة التحكم
                shared_state['machines'][mid] = {
                    'name':       machine.get('name', mid),
                    'health':     result.get('health', 100),
                    'rul_days':   result.get('rul_days', 0),
                    'status':     result.get('status', 'ok'),
                    'temp':       data.get('temp', 0),
                    'vibration':  data.get('vibration_rms', 0),
                    'source':     data.get('source', 'Unknown'),
                    'is_simulated': data.get('is_simulated', True),
                    'last_update': datetime.now().strftime('%H:%M:%S')
                }

                # تفعيل التنبيهات إذا كانت الحالة خطر أو تحذير
                if result.get('status') in ('danger', 'warning'):
                    alert_system.trigger(machine, result, data)

            shared_state['last_scan'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        except Exception as e:
            logging.error(f"خطأ في دورة المراقبة: {e}")

        stop_event.wait(interval)

def main():
    logging.info("=== بدء تشغيل نظام CVFPM الاحترافي ===")
    
    # 1. تحميل الإعدادات
    try:
        config = load_config()
    except Exception as e:
        logging.error(f"فشل تحميل الإعدادات: {e}")
        return

    config_ref = [config] # مرجع للإعدادات لدعم التحديث الحي

    # 2. تهيئة الحالة المشتركة والمحركات
    shared_state = {
        'machines': {},
        'alerts': [],
        'last_scan': None,
        'config_ref': config_ref
    }

    ai_engine = AIEngine(config)
    alert_system = AlertSystem(config, shared_state)
    stop_event = threading.Event()

    # 3. تشغيل خيط المراقبة في الخلفية
    monitor_thread = threading.Thread(
        target=monitoring_loop,
        args=(config_ref, ai_engine, alert_system, shared_state, stop_event),
        daemon=True
    )
    monitor_thread.start()

    # 4. تشغيل لوحة الويب (Flask)
    app = create_app(config_ref, shared_state)
    
    # 🔥 أهم جزء لـ Render: الحصول على البورت من متغيرات البيئة
    port = int(os.environ.get("PORT", config.get('dashboard_port', 5000)))
    
    logging.info(f"لوحة التحكم تعمل على الرابط: http://0.0.0.0:{port}")

    # إعداد إيقاف النظام بشكل نظيف
    def shutdown_handler(sig, frame):
        logging.info("جاري إغلاق النظام...")
        stop_event.set()
        sys.exit(0)

    signal.signal(signal.SIGINT,  shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    # تشغيل السيرفر
    app.run(
        host='0.0.0.
