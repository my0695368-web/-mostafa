"""
CVFPM - Collective Vibration Fingerprint for Predictive Maintenance
نظام الصيانة التنبؤية الذكي
المطور: Mostafa Eisaa | 775166114
تشغيل: python main.py
"""

import json, time, threading, logging, os, signal, sys
from datetime import datetime
from sensor_reader import SensorReader
from ai_engine import AIEngine
from alert_system import AlertSystem
from web_dashboard import create_app

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('cvfpm.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')

def load_config():
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def monitoring_loop(config_ref, ai_engine, alert_system, shared_state, stop_event):
    """حلقة المراقبة الرئيسية — تدعم hot reload للإعدادات"""
    sensor_reader = SensorReader(config_ref[0])

    while not stop_event.is_set():
        config = config_ref[0]          # ← يقرأ الإعدادات المحدّثة دائماً
        interval = config.get('monitoring_interval_seconds', 30)

        try:
            for machine in config['machines']:
                mid = machine['id']
                data = sensor_reader.read(machine)

                if data is None:
                    logging.warning(f"لم يتم قراءة بيانات {mid}")
                    continue

                result = ai_engine.analyze(mid, data)

                shared_state['machines'][mid] = {
                    'name':       machine['name'],
                    'type':       machine['type'],
                    'line':       machine['line'],
                    'ip':         machine['ip'],
                    'health':     round(result['health'], 1),
                    'rul_days':   round(result['rul_days'], 1),
                    'status':     result['status'],
                    'temp':       round(data.get('temp', 0), 1),
                    'vibration':  round(data.get('vibration_rms', 0), 3),
                    'last_update': datetime.now().strftime('%H:%M:%S')
                }

                if result['status'] in ('danger', 'warning'):
                    alert_system.trigger(machine, result, data)

            shared_state['last_scan'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logging.info(f"دورة مراقبة مكتملة — {len(config['machines'])} آلة")

        except Exception as e:
            logging.error(f"خطأ في حلقة المراقبة: {e}")

        stop_event.wait(interval)

def main():
    logging.info("=== بدء تشغيل نظام CVFPM ===")
    logging.info("المطور: Mostafa Eisaa | 775166114")

    config = load_config()
    config_ref = [config]       # قائمة بعنصر واحد → يمكن تعديلها من الخيوط

    shared_state = {
        'machines': {},
        'alerts': [],
        'last_scan': None,
        'config_ref': config_ref   # يتيح للـ API الوصول للـ config
    }

    ai_engine    = AIEngine(config)
    alert_system = AlertSystem(config, shared_state)

    stop_event = threading.Event()

    # خيط المراقبة
    t = threading.Thread(
        target=monitoring_loop,
        args=(config_ref, ai_engine, alert_system, shared_state, stop_event),
        daemon=True
    )
    t.start()
    logging.info("خيط المراقبة بدأ")

    # تشغيل لوحة الويب
    app  = create_app(config_ref, shared_state)
    port = config.get('dashboard_port', 5000)
    logging.info(f"لوحة التحكم: http://0.0.0.0:{port}")

    # إيقاف نظيف
    def shutdown(sig, frame):
        logging.info("إيقاف النظام...")
        stop_event.set()
        sys.exit(0)

    signal.signal(signal.SIGINT,  shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Flask بإعدادات إنتاج (سريعة)
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        threaded=True,          # ← كل طلب في خيط منفصل = استجابة سريعة
        use_reloader=False
    )

if __name__ == '__main__':
    main()
