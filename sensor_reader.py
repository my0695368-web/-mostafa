"""
sensor_reader.py — قراءة بيانات الحساسات
يدعم: MPU-6050 (اهتزاز) + MLX90614 (حرارة) عبر Zigbee أو I2C مباشر
"""

import logging, math, random, time
import numpy as np

try:
    import smbus2
    I2C_AVAILABLE = True
except ImportError:
    I2C_AVAILABLE = False
    logging.warning("smbus2 غير متوفر — وضع المحاكاة")

MPU6050_ADDR = 0x68
MLX90614_ADDR = 0x5A
PWR_MGMT_1 = 0x6B
ACCEL_XOUT_H = 0x3B

class SensorReader:
    def __init__(self, config):
        self.config = config
        self.simulation_mode = not I2C_AVAILABLE
        self._machine_state = {}  # لمحاكاة تدهور تدريجي

        if not self.simulation_mode:
            try:
                self.bus = smbus2.SMBus(1)
                self._init_mpu6050()
                logging.info("I2C جاهز — قراءة حقيقية")
            except Exception as e:
                logging.warning(f"خطأ I2C: {e} — تحويل لوضع المحاكاة")
                self.simulation_mode = True

    def _init_mpu6050(self):
        self.bus.write_byte_data(MPU6050_ADDR, PWR_MGMT_1, 0)

    def _read_mpu6050(self):
        raw = self.bus.read_i2c_block_data(MPU6050_ADDR, ACCEL_XOUT_H, 14)
        def to_int(h, l): v = (h << 8) | l; return v - 65536 if v > 32767 else v
        ax = to_int(raw[0], raw[1]) / 16384.0
        ay = to_int(raw[2], raw[3]) / 16384.0
        az = to_int(raw[4], raw[5]) / 16384.0
        gx = to_int(raw[8], raw[9]) / 131.0
        gy = to_int(raw[10], raw[11]) / 131.0
        gz = to_int(raw[12], raw[13]) / 131.0
        rms = math.sqrt(ax**2 + ay**2 + az**2)
        return {'ax':ax,'ay':ay,'az':az,'gx':gx,'gy':gy,'gz':gz,'vibration_rms':rms}

    def _read_mlx90614(self):
        raw = self.bus.read_word_data(MLX90614_ADDR, 0x07)
        temp = raw * 0.02 - 273.15
        return round(temp, 1)

    def _simulate(self, machine):
        """محاكاة واقعية مع تدهور تدريجي"""
        mid = machine['id']
        if mid not in self._machine_state:
            self._machine_state[mid] = {'health': random.uniform(60, 95), 'cycle': 0}

        state = self._machine_state[mid]
        state['cycle'] += 1

        # تدهور تدريجي
        if mid == 'CNC-01':
            state['health'] = max(5, state['health'] - random.uniform(0.1, 0.4))
        elif mid == 'PRESS-02':
            state['health'] = max(30, state['health'] - random.uniform(0.05, 0.2))
        else:
            state['health'] = min(100, state['health'] + random.uniform(-0.1, 0.2))

        h = state['health']
        vib_base = 3.5 - (h / 100) * 2.5
        temp_base = 45 + (100 - h) * 0.5

        return {
            'ax': random.gauss(0, vib_base * 0.3),
            'ay': random.gauss(0, vib_base * 0.2),
            'az': random.gauss(1, vib_base * 0.1),
            'gx': random.gauss(0, vib_base * 5),
            'gy': random.gauss(0, vib_base * 4),
            'gz': random.gauss(0, vib_base * 3),
            'vibration_rms': abs(random.gauss(vib_base, vib_base * 0.15)),
            'temp': random.gauss(temp_base, 2),
            '_sim_health': h
        }

    def read(self, machine):
        """قراءة البيانات من الحساس أو المحاكاة"""
        try:
            if self.simulation_mode:
                return self._simulate(machine)
            else:
                vib = self._read_mpu6050()
                temp = self._read_mlx90614()
                vib['temp'] = temp
                return vib
        except Exception as e:
            logging.error(f"خطأ قراءة {machine['id']}: {e}")
            return self._simulate(machine)

    def read_batch(self, machine, n=50, delay=0.02):
        """قراءة مجموعة لتدريب النموذج"""
        readings = []
        for _ in range(n):
            d = self.read(machine)
            if d:
                readings.append([
                    d['ax'], d['ay'], d['az'],
                    d['gx'], d['gy'], d['gz'],
                    d.get('temp', 25)
                ])
            time.sleep(delay)
        return np.array(readings)
