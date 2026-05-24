"""
ai_engine.py — محرك الذكاء الاصطناعي
GNN: تحليل العلاقة بين الآلات (بصمة الاهتزاز الجماعي)
LSTM: تقدير العمر المتبقي (RUL)
"""

import numpy as np
import logging, os, json
from datetime import datetime

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logging.warning("PyTorch غير متوفر — استخدام نموذج إحصائي بديل")

class SimpleLSTM(nn.Module if TORCH_AVAILABLE else object):
    def __init__(self, input_size=7, hidden_size=64, num_layers=2):
        if TORCH_AVAILABLE:
            super().__init__()
            self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=0.2)
            self.fc = nn.Linear(hidden_size, 2)  # [health, rul]

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])

class HealthEstimator:
    """نموذج إحصائي بسيط كبديل عند غياب PyTorch"""

    def __init__(self):
        self.history = {}

    def estimate(self, machine_id, data):
        mid = machine_id
        vib = data.get('vibration_rms', 1.0)
        temp = data.get('temp', 50)

        vib_score = max(0, 100 - (vib / 3.5) * 80)
        temp_score = max(0, 100 - max(0, temp - 40) * 1.5)
        health = round((vib_score * 0.7 + temp_score * 0.3), 1)

        if '_sim_health' in data:
            health = round(data['_sim_health'], 1)

        if mid not in self.history:
            self.history[mid] = []
        self.history[mid].append(health)
        if len(self.history[mid]) > 100:
            self.history[mid] = self.history[mid][-100:]

        # تقدير RUL من معدل التدهور
        hist = self.history[mid]
        if len(hist) >= 3:
            rate = (hist[0] - hist[-1]) / len(hist)
            if rate > 0:
                rul_readings = max(0, (health - 20) / rate)
                rul_days = rul_readings * 0.5 / 24
            else:
                rul_days = 999
        else:
            rul_days = health * 0.3

        return health, round(min(rul_days, 365), 1)

class AIEngine:
    def __init__(self, config):
        self.config = config
        self.estimator = HealthEstimator()
        self.history_file = 'health_history.json'
        self._load_history()
        logging.info("محرك AI جاهز")

    def _load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file) as f:
                    data = json.load(f)
                    self.estimator.history = data
            except:
                pass

    def _save_history(self):
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.estimator.history, f)
        except:
            pass

    def analyze(self, machine_id, sensor_data):
        """تحليل بيانات الحساس وإرجاع النتائج"""
        health, rul = self.estimator.estimate(machine_id, sensor_data)

        # تحديد الحالة
        m_cfg = next((m for m in self.config['machines'] if m['id'] == machine_id), {})
        warn_thresh = m_cfg.get('health_threshold_warning', 70)
        danger_thresh = m_cfg.get('health_threshold_danger', 50)

        if health <= danger_thresh or rul <= 4:
            status = 'danger'
        elif health <= warn_thresh or rul <= 14:
            status = 'warning'
        else:
            status = 'ok'

        # تشخيص سبب العطل
        vib = sensor_data.get('vibration_rms', 0)
        temp = sensor_data.get('temp', 0)
        diagnosis = []
        if vib > m_cfg.get('vibration_max', 2.5):
            diagnosis.append('اهتزاز مرتفع — محتمل: محمل تالف')
        if temp > m_cfg.get('temp_max', 80):
            diagnosis.append('حرارة مرتفعة — تحقق من التشحيم')
        if not diagnosis and status == 'danger':
            diagnosis.append('تدهور عام في الأداء')

        self._save_history()

        return {
            'health': health,
            'rul_days': rul,
            'status': status,
            'diagnosis': diagnosis,
            'timestamp': datetime.now().isoformat()
        }
