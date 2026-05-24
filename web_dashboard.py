"""
web_dashboard.py — لوحة تحكم الويب عالية الأداء
المطور: Mostafa Eisaa | 775166114
الوصول: http://<ip>:5000
"""

import json, os
from flask import Flask, jsonify, render_template_string, request
from datetime import datetime
from functools import wraps

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')

# ─── تعطيل Cache للـ API (استجابة فورية) ────────────────────
def no_cache(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        resp = f(*args, **kwargs)
        if hasattr(resp, 'headers'):
            resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
            resp.headers['Pragma'] = 'no-cache'
        return resp
    return decorated

DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CVFPM — لوحة التحكم</title>
<style>
/* ─── Reset & Base ─────────────────────────────────────── */
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --blue:#185FA5;--red:#E24B4A;--orange:#EF9F27;--green:#4CAF50;
  --bg:#f0f2f5;--card:#fff;--border:#e8eaed;--text:#1a1a2e;--sub:#666;
  --radius:10px;--shadow:0 2px 8px rgba(0,0,0,.08);
  --transition:all .2s ease;
}
html,body{height:100%;font-family:'Segoe UI',Arial,sans-serif;background:var(--bg);color:var(--text)}

/* ─── Topbar ────────────────────────────────────────────── */
.topbar{
  background:linear-gradient(135deg,#185FA5 0%,#1a78cc 100%);
  color:#fff;padding:0 20px;height:60px;
  display:flex;align-items:center;justify-content:space-between;
  box-shadow:0 2px 12px rgba(24,95,165,.4);position:sticky;top:0;z-index:100;
}
.logo{display:flex;align-items:center;gap:10px}
.logo-icon{width:34px;height:34px;background:rgba(255,255,255,.2);border-radius:8px;
  display:flex;align-items:center;justify-content:center;font-size:18px}
.logo-text .title{font-size:16px;font-weight:700;letter-spacing:.3px}
.logo-text .sub{font-size:11px;opacity:.75}
.topbar-right{text-align:left;font-size:11px;opacity:.8}
.status-dot{display:inline-block;width:8px;height:8px;border-radius:50%;
  background:#4ade80;animation:pulse-green 2s infinite;margin-left:5px}
@keyframes pulse-green{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.6;transform:scale(1.3)}}

/* ─── Content ───────────────────────────────────────────── */
.content{padding:16px 20px;max-width:1300px;margin:0 auto}

/* ─── Metric Cards ──────────────────────────────────────── */
.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:12px;margin-bottom:18px}
.metric{
  background:var(--card);border-radius:var(--radius);padding:16px 12px;
  text-align:center;border:1px solid var(--border);box-shadow:var(--shadow);
  transition:var(--transition);
}
.metric:hover{transform:translateY(-2px);box-shadow:0 6px 20px rgba(0,0,0,.1)}
.metric-val{font-size:30px;font-weight:800;line-height:1;margin-bottom:5px}
.metric-label{font-size:11px;color:var(--sub);font-weight:500}

/* ─── Machine Cards ─────────────────────────────────────── */
.section-title{font-size:14px;font-weight:700;color:var(--text);margin-bottom:12px;
  display:flex;align-items:center;gap:6px}
.section-title::before{content:"";display:block;width:3px;height:16px;
  background:var(--blue);border-radius:2px}
.machines{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:12px;margin-bottom:18px}
.m-card{
  background:var(--card);border-radius:var(--radius);padding:14px;
  border:2px solid var(--border);box-shadow:var(--shadow);
  transition:var(--transition);cursor:default;position:relative;overflow:hidden;
}
.m-card::before{content:"";position:absolute;top:0;right:0;width:4px;height:100%;border-radius:0 var(--radius) var(--radius) 0}
.m-card.ok::before{background:var(--green)}
.m-card.warning::before{background:var(--orange)}
.m-card.danger::before{background:var(--red)}
.m-card:hover{transform:translateY(-3px);box-shadow:0 8px 24px rgba(0,0,0,.12)}
.m-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}
.m-name{font-weight:700;font-size:14px}
.status-badge{font-size:10px;padding:3px 8px;border-radius:20px;font-weight:700}
.badge-ok{background:#e8f5e9;color:#2e7d32}
.badge-warning{background:#fff8e1;color:#e65100}
.badge-danger{background:#ffebee;color:#c62828}
.health-bar-bg{height:7px;background:#f0f0f0;border-radius:4px;margin:8px 0;overflow:hidden}
.health-bar{height:100%;border-radius:4px;transition:width .6s ease}
.health-bar.ok{background:linear-gradient(90deg,#81c784,#4caf50)}
.health-bar.warning{background:linear-gradient(90deg,#ffb74d,#ef9f27)}
.health-bar.danger{background:linear-gradient(90deg,#e57373,#e24b4a)}
.m-stats{display:flex;justify-content:space-between;font-size:11px;margin-bottom:6px}
.m-stats span{color:var(--sub)}
.m-stats strong{color:var(--text)}
.m-meta{font-size:10px;color:#aaa;border-top:1px solid var(--border);padding-top:6px;margin-top:6px}

/* ─── Alerts ────────────────────────────────────────────── */
.alerts-section{background:var(--card);border-radius:var(--radius);
  padding:16px;border:1px solid var(--border);box-shadow:var(--shadow)}
.alerts-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}
.alert-count-badge{background:var(--red);color:#fff;font-size:11px;
  padding:2px 10px;border-radius:20px;font-weight:700;min-width:22px;text-align:center}
.alert-item{
  padding:12px;border-radius:8px;margin-bottom:10px;border:1px solid;
  animation:fadeIn .3s ease;
}
@keyframes fadeIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
.alert-danger{background:#fff5f5;border-color:#fca5a5}
.alert-warning{background:#fffbf0;border-color:#fcd34d}
.alert-ok{background:#f0fdf4;border-color:#86efac}
.alert-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:6px}
.alert-machine{font-weight:700;font-size:13px;display:flex;align-items:center;gap:6px}
.alert-time{font-size:11px;color:#999}
.alert-body{font-size:12px;color:#555;line-height:1.6}
.resolve-btn{
  margin-top:8px;font-size:11px;padding:5px 14px;background:var(--green);
  color:#fff;border:none;border-radius:6px;cursor:pointer;transition:var(--transition);font-weight:600;
}
.resolve-btn:hover{background:#388e3c;transform:scale(1.03)}
.no-alerts{text-align:center;color:#aaa;padding:30px;font-size:13px}
.no-alerts-icon{font-size:32px;margin-bottom:8px}

/* ─── Footer ─────────────────────────────────────────────── */
.footer{
  text-align:center;padding:18px;margin-top:20px;
  font-size:11px;color:#aaa;border-top:1px solid var(--border);
}
.footer strong{color:var(--blue)}

/* ─── Loading Skeleton ──────────────────────────────────── */
.skeleton{background:linear-gradient(90deg,#f0f0f0 25%,#e0e0e0 50%,#f0f0f0 75%);
  background-size:200% 100%;animation:shimmer 1.2s infinite;border-radius:6px}
@keyframes shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}

/* ─── Responsive ────────────────────────────────────────── */
@media(max-width:600px){
  .content{padding:12px};
  .metrics{grid-template-columns:repeat(3,1fr)};
  .metric-val{font-size:22px};
}
</style>
</head>
<body>

<div class="topbar">
  <div class="logo">
    <div class="logo-icon">⚙</div>
    <div class="logo-text">
      <div class="title">CVFPM — نظام الصيانة الذكية</div>
      <div class="sub">Collective Vibration Fingerprint for Predictive Maintenance</div>
    </div>
  </div>
  <div class="topbar-right">
    <div><span class="status-dot"></span> <span id="sys-status">متصل</span></div>
    <div id="last-scan" style="margin-top:3px">جاري التحديث...</div>
  </div>
</div>

<div class="content">

  <!-- Metric Cards -->
  <div class="metrics" id="metrics">
    <div class="metric"><div class="metric-val skeleton" style="height:36px;width:60px;margin:0 auto 8px"></div><div class="metric-label skeleton" style="height:12px;width:80px;margin:0 auto"></div></div>
    <div class="metric"><div class="metric-val skeleton" style="height:36px;width:60px;margin:0 auto 8px"></div><div class="metric-label skeleton" style="height:12px;width:80px;margin:0 auto"></div></div>
    <div class="metric"><div class="metric-val skeleton" style="height:36px;width:60px;margin:0 auto 8px"></div><div class="metric-label skeleton" style="height:12px;width:80px;margin:0 auto"></div></div>
    <div class="metric"><div class="metric-val skeleton" style="height:36px;width:60px;margin:0 auto 8px"></div><div class="metric-label skeleton" style="height:12px;width:80px;margin:0 auto"></div></div>
    <div class="metric"><div class="metric-val skeleton" style="height:36px;width:60px;margin:0 auto 8px"></div><div class="metric-label skeleton" style="height:12px;width:80px;margin:0 auto"></div></div>
  </div>

  <!-- Machines -->
  <div class="section-title">الآلات المراقبة</div>
  <div class="machines" id="machines"></div>

  <!-- Alerts -->
  <div class="alerts-section">
    <div class="alerts-header">
      <div class="section-title" style="margin-bottom:0">التنبيهات النشطة</div>
      <span class="alert-count-badge" id="alert-count">0</span>
    </div>
    <div id="alerts-list"><div class="no-alerts"><div class="no-alerts-icon">✓</div>لا توجد تنبيهات</div></div>
  </div>

</div>

<!-- Footer -->
<div class="footer">
  CVFPM — نظام الصيانة التنبؤية الذكي &nbsp;|&nbsp;
  المطور: <strong>Mostafa Eisaa</strong> &nbsp;|&nbsp; 📞 <strong>775166114</strong>
</div>

<script>
// ─── Helpers ──────────────────────────────────────────────
const $ = id => document.getElementById(id);
const statusColor = s => s==='danger'?'red':s==='warning'?'orange':'green';
const statusLabel  = s => s==='danger'?'عطل وشيك':s==='warning'?'تحذير':'جيد';
const badgeClass   = s => `status-badge badge-${s}`;
let failCount = 0;

// ─── Render ────────────────────────────────────────────────
function renderMetrics(ms, alerts) {
  const danger  = ms.filter(m=>m.status==='danger').length;
  const warn    = ms.filter(m=>m.status==='warning').length;
  const avgH    = ms.length ? Math.round(ms.reduce((s,m)=>s+m.health,0)/ms.length) : 0;
  const active  = alerts.filter(a=>!a.resolved).length;

  $('metrics').innerHTML = `
    <div class="metric"><div class="metric-val" style="color:var(--blue)">${ms.length}</div><div class="metric-label">إجمالي الآلات</div></div>
    <div class="metric"><div class="metric-val" style="color:var(--green)">${avgH}%</div><div class="metric-label">متوسط الصحة</div></div>
    <div class="metric"><div class="metric-val" style="color:var(--red)">${danger}</div><div class="metric-label">أعطال وشيكة</div></div>
    <div class="metric"><div class="metric-val" style="color:var(--orange)">${warn}</div><div class="metric-label">تحذيرات</div></div>
    <div class="metric"><div class="metric-val" style="color:${active?'var(--red)':'var(--green)'}">${active}</div><div class="metric-label">تنبيهات نشطة</div></div>
  `;
}

function renderMachines(ms) {
  if (!ms.length) { $('machines').innerHTML='<p style="color:#aaa;font-size:13px">لا توجد آلات متصلة بعد</p>'; return; }
  $('machines').innerHTML = ms.map(m => `
    <div class="m-card ${m.status}">
      <div class="m-header">
        <span class="m-name">${m.name}</span>
        <span class="${badgeClass(m.status)}">${statusLabel(m.status)}</span>
      </div>
      <div class="health-bar-bg"><div class="health-bar ${m.status}" style="width:${m.health}%"></div></div>
      <div class="m-stats">
        <span>صحة <strong style="color:${m.status==='danger'?'var(--red)':m.status==='warning'?'var(--orange)':'var(--green)'}">${m.health}%</strong></span>
        <span>RUL <strong>${m.rul_days} يوم</strong></span>
      </div>
      <div class="m-meta">${m.type} — ${m.line} — ${m.temp}°C — ${m.vibration}g<br>آخر قراءة: ${m.last_update}</div>
    </div>
  `).join('');
}

function renderAlerts(alerts) {
  const active = alerts.filter(a=>!a.resolved);
  $('alert-count').textContent = active.length;
  if (!active.length) {
    $('alerts-list').innerHTML='<div class="no-alerts"><div class="no-alerts-icon">✅</div>لا توجد تنبيهات نشطة</div>';
    return;
  }
  $('alerts-list').innerHTML = active.map(a=>`
    <div class="alert-item alert-${a.status}">
      <div class="alert-header">
        <div class="alert-machine">
          <span class="${badgeClass(a.status)}">${statusLabel(a.status)}</span>
          ${a.machine_name}
        </div>
        <span class="alert-time">${a.time}</span>
      </div>
      <div class="alert-body">
        صحة: <strong>${a.health}%</strong> &nbsp;|&nbsp; RUL: <strong>${a.rul_days} يوم</strong>
        &nbsp;|&nbsp; ${a.temp}°C &nbsp;|&nbsp; ${a.vibration}g<br>
        ${a.diagnosis.join(' — ')}
      </div>
      <button class="resolve-btn" onclick="resolve('${a.id}')">✔ تم الإصلاح</button>
    </div>
  `).join('');
}

// ─── Fetch & Refresh ───────────────────────────────────────
async function refresh() {
  try {
    const r = await fetch('/api/state', {cache:'no-store'});
    if (!r.ok) throw new Error(r.status);
    const d = await r.json();
    failCount = 0;

    $('sys-status').textContent = 'متصل';
    $('sys-status').style.color = '';
    $('last-scan').textContent  = 'آخر فحص: ' + (d.last_scan || '...');

    const ms = Object.values(d.machines || {});
    renderMetrics(ms, d.alerts || []);
    renderMachines(ms);
    renderAlerts(d.alerts || []);

  } catch(e) {
    failCount++;
    if (failCount >= 3) {
      $('sys-status').textContent = 'انقطع الاتصال';
      $('sys-status').style.color = 'var(--red)';
    }
  }
}

async function resolve(id) {
  await fetch('/api/resolve/'+id, {method:'POST'});
  refresh();
}

// ─── أول تحديث فوري، ثم كل 5 ثواني ──────────────────────
refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>'''


def create_app(config_ref, shared_state):
    """
    config_ref: قائمة بعنصر واحد [config_dict] — قابلة للتحديث من الخارج
    """
    app = Flask(__name__)
    app.config['JSON_ENSURE_ASCII'] = False      # عربي بدون escape
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

    @app.route('/')
    def index():
        return render_template_string(DASHBOARD_HTML)

    @app.route('/api/state')
    @no_cache
    def api_state():
        return jsonify({
            'machines':  shared_state.get('machines', {}),
            'alerts':    shared_state.get('alerts', []),
            'last_scan': shared_state.get('last_scan', 'لم يبدأ بعد')
        })

    @app.route('/api/resolve/<alert_id>', methods=['POST'])
    def api_resolve(alert_id):
        for a in shared_state.get('alerts', []):
            if a['id'] == alert_id:
                a['resolved'] = True
        return jsonify({'ok': True})

    @app.route('/api/reload', methods=['POST'])
    def api_reload():
        """Hot reload — تحديث الإعدادات بدون إعادة تشغيل"""
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                new_config = json.load(f)
            config_ref[0] = new_config
            return jsonify({'ok': True, 'msg': 'تم تحديث الإعدادات'})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 500

    @app.route('/api/machines', methods=['GET'])
    @no_cache
    def api_get_machines():
        return jsonify(config_ref[0].get('machines', []))

    @app.route('/api/machines', methods=['POST'])
    def api_add_machine():
        data = request.json
        config_ref[0]['machines'].append(data)
        # احفظ في الملف أيضاً
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config_ref[0], f, ensure_ascii=False, indent=2)
        except Exception as e:
            pass
        return jsonify({'ok': True, 'id': data.get('id')})

    @app.route('/api/config', methods=['GET'])
    @no_cache
    def api_get_config():
        """يُرجع الإعدادات الحالية (بدون كلمة المرور)"""
        cfg = dict(config_ref[0])
        if 'email' in cfg:
            cfg['email'] = dict(cfg['email'])
            cfg['email']['password'] = '***'
        return jsonify(cfg)

    return app
