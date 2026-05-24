"""
alert_system.py — نظام التنبيهات
إرسال بريد إلكتروني + ظهور في لوحة التحكم
"""

import smtplib, logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta

class AlertSystem:
    def __init__(self, config, shared_state):
        self.config = config
        self.shared_state = shared_state
        self.email_cfg = config.get('email', {})
        self.cooldowns = {}  # machine_id -> last_alert_time
        logging.info("نظام التنبيهات جاهز")

    def _is_cooldown(self, machine_id):
        """منع إرسال تنبيهات متكررة خلال وقت قصير"""
        cooldown_min = self.email_cfg.get('cooldown_minutes', 30)
        last = self.cooldowns.get(machine_id)
        if last and datetime.now() - last < timedelta(minutes=cooldown_min):
            return True
        return False

    def trigger(self, machine, result, sensor_data):
        """تفعيل التنبيه — لوحة + بريد"""
        mid = machine['id']
        status = result['status']

        # إضافة للوحة دائماً
        alert = {
            'id': f"{mid}-{datetime.now().strftime('%H%M%S')}",
            'machine': mid,
            'machine_name': machine['name'],
            'status': status,
            'health': result['health'],
            'rul_days': result['rul_days'],
            'diagnosis': result['diagnosis'],
            'temp': round(sensor_data.get('temp', 0), 1),
            'vibration': round(sensor_data.get('vibration_rms', 0), 3),
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'resolved': False
        }

        alerts = self.shared_state.setdefault('alerts', [])
        # تجنب التكرار — احذف القديم لنفس الآلة
        self.shared_state['alerts'] = [a for a in alerts if a['machine'] != mid]
        self.shared_state['alerts'].insert(0, alert)
        if len(self.shared_state['alerts']) > 50:
            self.shared_state['alerts'] = self.shared_state['alerts'][:50]

        # إرسال بريد (مع cooldown)
        if self.email_cfg.get('enabled') and not self._is_cooldown(mid):
            try:
                self._send_email(machine, result, sensor_data)
                self.cooldowns[mid] = datetime.now()
            except Exception as e:
                logging.error(f"فشل إرسال البريد لـ {mid}: {e}")

    def _send_email(self, machine, result, sensor_data):
        cfg = self.email_cfg
        status = result['status']
        icon = '🔴' if status == 'danger' else '🟡'
        subject = f"{icon} CVFPM تنبيه: {machine['name']} — {'عطل وشيك' if status == 'danger' else 'تحذير'}"

        diagnosis_html = ''.join(f'<li>{d}</li>' for d in result['diagnosis']) or '<li>لا يوجد تشخيص محدد</li>'

        html = f"""
        <div dir="rtl" style="font-family:Arial;max-width:600px;margin:auto;border:1px solid #ddd;border-radius:8px;overflow:hidden">
          <div style="background:{'#E24B4A' if status=='danger' else '#EF9F27'};color:white;padding:20px">
            <h2 style="margin:0">{'⚠️ عطل وشيك' if status=='danger' else '⚡ تحذير'} — {machine['name']}</h2>
            <p style="margin:4px 0 0;opacity:.9">{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
          </div>
          <div style="padding:20px">
            <table style="width:100%;border-collapse:collapse">
              <tr style="border-bottom:1px solid #eee">
                <td style="padding:8px;color:#666">الآلة</td>
                <td style="padding:8px;font-weight:bold">{machine['name']} ({machine['type']})</td>
              </tr>
              <tr style="border-bottom:1px solid #eee">
                <td style="padding:8px;color:#666">الخط</td>
                <td style="padding:8px">{machine['line']}</td>
              </tr>
              <tr style="border-bottom:1px solid #eee">
                <td style="padding:8px;color:#666">صحة الآلة</td>
                <td style="padding:8px;font-weight:bold;color:{'#E24B4A' if result['health']<50 else '#EF9F27'}">{result['health']}%</td>
              </tr>
              <tr style="border-bottom:1px solid #eee">
                <td style="padding:8px;color:#666">العمر المتبقي (RUL)</td>
                <td style="padding:8px;font-weight:bold">{result['rul_days']} يوم</td>
              </tr>
              <tr style="border-bottom:1px solid #eee">
                <td style="padding:8px;color:#666">درجة الحرارة</td>
                <td style="padding:8px">{sensor_data.get('temp', 'N/A')} °C</td>
              </tr>
              <tr>
                <td style="padding:8px;color:#666">الاهتزاز</td>
                <td style="padding:8px">{round(sensor_data.get('vibration_rms', 0), 3)} g</td>
              </tr>
            </table>
            <div style="margin-top:16px;background:#fff8f0;border-radius:6px;padding:12px">
              <strong>التشخيص:</strong>
              <ul style="margin:8px 0 0">{diagnosis_html}</ul>
            </div>
            <div style="margin-top:16px;background:#f0f8ff;border-radius:6px;padding:12px">
              <strong>الإجراء المطلوب:</strong>
              {'جدول صيانة طارئة خلال 24 ساعة' if status == 'danger' else 'راقب الآلة وجدول فحصاً خلال أسبوع'}
            </div>
          </div>
          <div style="background:#f5f5f5;padding:12px;text-align:center;font-size:12px;color:#999">
            CVFPM — نظام الصيانة التنبؤية الذكي
          </div>
        </div>
        """

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = cfg['sender']
        msg['To'] = ', '.join(cfg['recipients'])
        msg.attach(MIMEText(html, 'html', 'utf-8'))

        with smtplib.SMTP(cfg['smtp_host'], cfg['smtp_port']) as server:
            server.starttls()
            server.login(cfg['sender'], cfg['password'])
            server.sendmail(cfg['sender'], cfg['recipients'], msg.as_string())

        logging.info(f"تم إرسال تنبيه {machine['name']} لـ {cfg['recipients']}")

    def resolve(self, alert_id):
        for a in self.shared_state.get('alerts', []):
            if a['id'] == alert_id:
                a['resolved'] = True
                break
