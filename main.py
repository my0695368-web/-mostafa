"""
CVFPM - المنسق الرئيسي للنظام (النسخة السحابية المعتمدة)
المطور: Mostafa Eisaa
الغرض: تشغيل النظام بالكامل وتوافق بورت السيرفر مع Render
"""

import json, time, threading, logging, os, signal, sys
from datetime import datetime

# استيراد مكونات النظام الخاصة بك
from sensor_reader import SensorReader
from ai_engine import AIEngine
from alert_system import AlertSystem
from web_dashboard import create_app

# إعداد السجلات (Logs) لمراقبة الأخطاء في Render
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)

# تحديد المسارات
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')

def load_config():
    """تحميل الإعدادات بأمان"""
    if not os.path.exists(CONFIG_FILE):
        return {
            "monitoring_interval_seconds": 10,
            "dashboard_port": 5000,
            "machines": [{"id": "DEMO-01", "name": "ماكينة تجريبية", "type": "Demo"}]
        }
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def monitoring_loop(config_ref, ai_engine, alert_system, shared_state, stop_event):
    """حلقة قراءة الحساسات والذكاء الاصطناعي"""
    # تهيئة القارئ (سيفحص تلقائياً وجود الحساسات أو يفعل المحاكاة)
    sensor_reader = SensorReader(config_ref[0])
    logging.info(f"⚙️ النظام يعمل الآن بنمط: {sensor_reader.source_label}")

    while not stop_event.is_set():
        config = config_ref[0]
        interval = config.get('monitoring_interval_seconds', 10)

        try:
            for machine in config.get('machines', []):
                mid = machine['id']
                # قراءة البيانات
                data = sensor_reader.read(machine)
                if data is None: continue

                # تحليل الذكاء الاصطناعي
                result = ai_engine.analyze(mid, data)

                # تحديث الحالة المشتركة للوحة التحكم
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

                # التنبيهات
                if result.get('status') in ('danger', 'warning'):
                    alert_system.trigger(machine, result, data)

            shared_state['last_scan'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        except Exception as e:
            logging.error(f"⚠️ خطأ في دورة المراقبة: {e}")

        stop_event.wait(interval)

def main():
    logging.info("=== بدء تشغيل نظام CVFPM - Mostafa Eisaa ===")
    
    config = load_config()
    config_ref = [config]

    shared_state = {
        'machines': {},
        'alerts': [],
        'last_scan': None,
        'config_ref': config_ref
    }

    # تهيئة المحركات
    ai_engine = AIEngine(config)
    alert_system = AlertSystem(config, shared_state)
    stop_event = threading.Event()

    # 1. تشغيل خيط المراقبة (Background Thread)
    monitor_thread = threading.Thread(
        target=monitoring_loop,
        args=(config_ref, ai_engine, alert_system, shared_state, stop_event),
        daemon=True
    )
    monitor_thread.start()

    # 2. إنشاء تطبيق الويب
    app = create_app(config_ref, shared_state)
    
    # 3. 🔥 ضبط البورت ليتوافق مع Render (إلزامي)
    # نأخذ البورت من نظام التشغيل، وإذا لم يوجد نستخدم 5000
    port = int(os.environ.get("PORT", 5000))
    
    logging.info(f"🚀 السيرفر جاهز للاستقبال على الرابط الخارجي بورت: {port}")

    # 4. تشغيل السيرفر (Host 0.0.0.0 ضروري جداً للسحابة)
    app.run(
        host='0.0.0.0', 
        port=port, 
        debug=False, 
        threaded=True, 
        use_reloader=False
    )

if __name__ == '__main__':
    main()
