// ═══════════════════════════════════════════════════════════════
// CONFIGURATION
// ═══════════════════════════════════════════════════════════════
const API_BASE = 'http://localhost:5000';

// ═══════════════════════════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════════════════════════
let currentLayouts = [];
let activeLayoutIdx = 0;
let activeLayout = null;
let renderer3D = null;
let selectedFacing = 'East';

// ═══════════════════════════════════════════════════════════════
// CURSOR TRACKING
// ═══════════════════════════════════════════════════════════════
document.addEventListener('mousemove', e => {
  document.body.style.setProperty('--cx', e.clientX + 'px');
  document.body.style.setProperty('--cy', e.clientY + 'px');
});

// ═══════════════════════════════════════════════════════════════
// NAVIGATION
// ═══════════════════════════════════════════════════════════════
function navigate(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('page-' + page).classList.add('active');
  document.getElementById('nav-' + page).classList.add('active');
  window.scrollTo({ top: 0, behavior: 'smooth' });
  if (page === 'ar') initAR();
}

// ═══════════════════════════════════════════════════════════════
// FACING DIRECTION
// ═══════════════════════════════════════════════════════════════
function selectFacing(dir) {
  selectedFacing = dir;
  document.querySelectorAll('.facing-btn').forEach(b => {
    b.classList.toggle('selected', b.dataset.dir === dir);
  });
}

// ═══════════════════════════════════════════════════════════════
// API HEALTH CHECK
// ═══════════════════════════════════════════════════════════════
async function checkAPI() {
  const dot = document.getElementById('api-dot');
  const txt = document.getElementById('api-status-text');
  const hdr = document.getElementById('cd-api');
  dot.className = 'api-dot loading';
  txt.textContent = 'Checking…';
  try {
    const r = await fetch(`${API_BASE}/api/health`, { signal: AbortSignal.timeout(3000) });
    if (r.ok) {
      dot.className = 'api-dot connected';
      txt.textContent = 'Connected';
      if (hdr) hdr.textContent = 'ONLINE';
      document.getElementById('status-dot').style.background = '#22c55e';
    } else throw new Error();
  } catch {
    dot.className = 'api-dot error';
    txt.textContent = 'Offline';
    if (hdr) hdr.textContent = 'OFFLINE';
    document.getElementById('status-dot').style.background = '#ef4444';
    document.getElementById('status-dot').style.boxShadow = '0 0 8px #ef4444';
  }
}

// ═══════════════════════════════════════════════════════════════
// ROOM COLOURS
// — balcony and store removed
// — bathroom_master, toilet_master, bathroom_attached, toilet_attached added
// ═══════════════════════════════════════════════════════════════
const COLORS = {
  entrance:            { fill:'rgba(236,72,153,0.4)',  stroke:'#ec4899', hex:0xec4899 },
  living:              { fill:'rgba(59,130,246,0.4)',  stroke:'#3b82f6', hex:0x3b82f6 },
  dining:              { fill:'rgba(234,179,8,0.4)',   stroke:'#eab308', hex:0xeab308 },
  kitchen:             { fill:'rgba(245,158,11,0.4)',  stroke:'#f59e0b', hex:0xf59e0b },
  master_bedroom:      { fill:'rgba(139,92,246,0.4)',  stroke:'#8b5cf6', hex:0x8b5cf6 },
  bedroom:             { fill:'rgba(99,102,241,0.4)',  stroke:'#6366f1', hex:0x6366f1 },
  bathroom:            { fill:'rgba(20,184,166,0.4)',  stroke:'#14b8a6', hex:0x14b8a6 },
  toilet:              { fill:'rgba(6,182,212,0.4)',   stroke:'#06b6d4', hex:0x06b6d4 },
  bathroom_master:     { fill:'rgba(45,212,191,0.4)',  stroke:'#2dd4bf', hex:0x2dd4bf },
  toilet_master:       { fill:'rgba(34,211,238,0.4)',  stroke:'#22d3ee', hex:0x22d3ee },
  bathroom_attached:   { fill:'rgba(52,211,153,0.4)',  stroke:'#34d399', hex:0x34d399 },
  toilet_attached:     { fill:'rgba(56,189,248,0.4)',  stroke:'#38bdf8', hex:0x38bdf8 },
  pooja:               { fill:'rgba(249,115,22,0.4)',  stroke:'#f97316', hex:0xf97316 },
  utility:             { fill:'rgba(148,163,184,0.4)', stroke:'#94a3b8', hex:0x94a3b8 },
};
const C_DEF = { fill:'rgba(100,116,139,0.4)', stroke:'#64748b', hex:0x64748b };

// ═══════════════════════════════════════════════════════════════
// CUSTOM PLOT SIZE HELPERS
// ═══════════════════════════════════════════════════════════════
function onPlotSelectChange(val) {
  const row = document.getElementById('custom-plot-row');
  if (val === 'custom') {
    row.classList.add('visible');
    row.style.animation = 'none';
    row.offsetHeight;
    row.style.animation = '';
    document.getElementById('custom-width').focus();
  } else {
    row.classList.remove('visible');
    document.getElementById('custom-plot-hint').textContent = 'Enter width & height between 10–200 ft';
    document.getElementById('custom-plot-hint').className = 'custom-plot-hint';
    document.getElementById('cpp-area').textContent = '—';
    document.getElementById('custom-plot-preview').className = 'custom-plot-preview';
  }
}

function onCustomDimChange() {
  const w    = parseInt(document.getElementById('custom-width').value,  10);
  const h    = parseInt(document.getElementById('custom-height').value, 10);
  const prev = document.getElementById('custom-plot-preview');
  const area = document.getElementById('cpp-area');
  const hint = document.getElementById('custom-plot-hint');

  const wOk = w >= 10 && w <= 200;
  const hOk = h >= 10 && h <= 200;

  prev.classList.remove('valid','invalid');
  hint.classList.remove('error','success');

  if (isNaN(w) || isNaN(h)) {
    area.textContent = '—';
    hint.textContent = 'Enter width & height between 10–200 ft';
    return;
  }
  if (!wOk || !hOk) {
    area.textContent = '!';
    prev.classList.add('invalid');
    hint.textContent = 'Values must be between 10 and 200 ft';
    hint.classList.add('error');
    return;
  }
  const sqft = w * h;
  area.textContent = sqft.toLocaleString();
  prev.classList.add('valid');
  hint.textContent = `✓ ${w}×${h} ft — ${sqft.toLocaleString()} sqft`;
  hint.classList.add('success');
}

function getPlotValue() {
  const sel = document.getElementById('sel-plot').value;
  if (sel !== 'custom') return sel;
  const w = parseInt(document.getElementById('custom-width').value,  10);
  const h = parseInt(document.getElementById('custom-height').value, 10);
  if (isNaN(w) || isNaN(h) || w < 10 || w > 200 || h < 10 || h > 200) return null;
  return `${w}x${h}`;
}

// ═══════════════════════════════════════════════════════════════
// MAIN GENERATE — calls Flask backend
// ═══════════════════════════════════════════════════════════════
async function generatePlan() {
  const plot = getPlotValue();
  if (!plot) { showToast('⚠ Enter a valid custom plot size', '⚠'); return; }
  const bhk    = document.getElementById('sel-bhk').value;
  const facing = selectedFacing;

  const btn = document.getElementById('btn-gen');
  const txt = document.getElementById('btn-text');
  btn.classList.add('loading');
  txt.innerHTML = '<div class="spin"></div>&nbsp;Running GA…';
  showLoadingOverlay(true);

  const loadMsgs = [
    'Initialising population…',
    'Running tournament selection…',
    'Applying crossover & mutation…',
    'Evaluating Vastu rules…',
    'Ranking layouts by fitness…',
  ];
  let mi = 0;
  const loadInt = setInterval(() => {
    document.getElementById('loading-sub').textContent = loadMsgs[mi % loadMsgs.length];
    mi++;
  }, 600);

  const t0 = Date.now();

  try {
    const res = await fetch(`${API_BASE}/api/layout/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ plot_size: plot, bhk_type: bhk, facing_direction: facing }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `HTTP ${res.status}`);
    }

    const data = await res.json();
    const elapsed = Date.now() - t0;

    if (!data.success || !data.layouts?.length) throw new Error('No layouts returned from API');

    currentLayouts  = data.layouts;
    activeLayoutIdx = 0;
    activeLayout    = currentLayouts[0];

    document.getElementById('cd-gen').textContent   = 'DONE';
    document.getElementById('cd-score').textContent = activeLayout.vastu_score?.toFixed(0) + '%';
    document.getElementById('cd-rooms').textContent = activeLayout.rooms?.length;

    renderUI(elapsed);
    updateResults();
    showToast(`✦ ${data.count} layouts generated · Vastu: ${activeLayout.vastu_score?.toFixed(1)}%`, '✦');
  } catch (err) {
    console.error('Generate error:', err);
    const localPlan  = buildLocalPlan(plot, bhk, facing, 0);
    const localPlan1 = buildLocalPlan(plot, bhk, facing, 1);
    const localPlan2 = buildLocalPlan(plot, bhk, facing, 2);
    currentLayouts  = [localPlan, localPlan1, localPlan2];
    activeLayoutIdx = 0;
    activeLayout    = localPlan;
    renderUI(0);
    updateResults();
    showToast(`⚠ API offline — showing demo plan`, '⚠');
  } finally {
    clearInterval(loadInt);
    showLoadingOverlay(false);
    btn.classList.remove('loading');
    txt.innerHTML = '✦ Generate AI Layout';
  }
}

// ═══════════════════════════════════════════════════════════════
// LOCAL FALLBACK PLAN
// — No balcony, no store room in any template
// — 3BHK: bathroom_master + toilet_master (attached) + bathroom + toilet (common)
// — 4BHK: bathroom_master + toilet_master + bathroom_attached + toilet_attached + bathroom + toilet
// ═══════════════════════════════════════════════════════════════
function buildLocalPlan(plotStr, bhk, facing, templateIdx) {
  const [pw, ph] = plotStr.split('x').map(Number);
  const m = 2, iw = pw - 2*m, ih = ph - 2*m;
  const tidx = (templateIdx || 0) % 3;

  // Build a room dict from grid fractions of iw/ih
  const R = (type, label, x, y, w, h) => ({
    type, label,
    x: m + x, y: m + y,
    w, h, width: w, height: h,
    area: parseFloat((w * h).toFixed(2))
  });

  // ─────────────────────────────────────────────────────────────
  // TEMPLATES — zero overlaps, zero balcony, zero store room
  // Each template tiles to full iw×ih with no gaps
  // ─────────────────────────────────────────────────────────────
  const templates = {

    // ── 1BHK ─────────────────────────────────────────────────
    '1BHK': [
      // T0 — Classic 3-row: living top, kitchen mid, master bottom
      [
        R('living',         'Living Room',    0,        0,        iw*0.65,  ih*0.42),
        R('entrance',       'Entrance',       iw*0.65,  0,        iw*0.35,  ih*0.11),
        R('pooja',          'Pooja Room',     iw*0.65,  ih*0.11,  iw*0.24,  ih*0.31),
        R('toilet',         'Toilet',         iw*0.89,  ih*0.11,  iw*0.11,  ih*0.16),
        R('bathroom',       'Bathroom',       iw*0.89,  ih*0.27,  iw*0.11,  ih*0.15),
        R('kitchen',        'Kitchen',        0,        ih*0.42,  iw*1.00,  ih*0.28),
        R('master_bedroom', 'Master Bedroom', 0,        ih*0.70,  iw*1.00,  ih*0.30),
      ],
      // T1 — Bedrooms top, living+kitchen bottom
      [
        R('master_bedroom', 'Master Bedroom', 0,        0,        iw*0.60,  ih*0.38),
        R('bathroom',       'Bathroom',       iw*0.60,  0,        iw*0.22,  ih*0.22),
        R('toilet',         'Toilet',         iw*0.82,  0,        iw*0.18,  ih*0.22),
        R('entrance',       'Entrance',       iw*0.60,  ih*0.22,  iw*0.40,  ih*0.16),
        R('living',         'Living Room',    0,        ih*0.38,  iw*1.00,  ih*0.38),
        R('kitchen',        'Kitchen',        0,        ih*0.76,  iw*0.60,  ih*0.24),
        R('pooja',          'Pooja Room',     iw*0.60,  ih*0.76,  iw*0.40,  ih*0.24),
      ],
      // T2 — 2-column layout
      [
        R('living',         'Living Room',    0,        0,        iw*0.55,  ih*0.42),
        R('entrance',       'Entrance',       iw*0.55,  0,        iw*0.45,  ih*0.14),
        R('pooja',          'Pooja Room',     iw*0.55,  ih*0.14,  iw*0.45,  ih*0.28),
        R('bathroom',       'Bathroom',       iw*0.55,  ih*0.42,  iw*0.25,  ih*0.22),
        R('toilet',         'Toilet',         iw*0.80,  ih*0.42,  iw*0.20,  ih*0.22),
        R('kitchen',        'Kitchen',        0,        ih*0.42,  iw*0.55,  ih*0.30),
        R('master_bedroom', 'Master Bedroom', 0,        ih*0.72,  iw*1.00,  ih*0.28),
      ],
    ],

    // ── 2BHK ─────────────────────────────────────────────────
    '2BHK': [
      // T0 — Classic 3-row grid
      [
        R('living',         'Living Room',    0,        0,        iw*0.52,  ih*0.35),
        R('entrance',       'Entrance',       iw*0.52,  0,        iw*0.50,  ih*0.11),
        R('pooja',          'Pooja Room',     iw*0.52,  ih*0.11,  iw*0.24,  ih*0.24),
        R('toilet',         'Toilet',         iw*0.76,  ih*0.11,  iw*0.12,  ih*0.18),
        R('bathroom',       'Bathroom',       iw*0.88,  ih*0.11,  iw*0.12,  ih*0.18),
        R('dining',         'Dining Room',    0,        ih*0.35,  iw*0.45,  ih*0.28),
        R('kitchen',        'Kitchen',        iw*0.45,  ih*0.35,  iw*0.55,  ih*0.28),
        R('master_bedroom', 'Master Bedroom', 0,        ih*0.63,  iw*0.52,  ih*0.37),
        R('bedroom',        'Bedroom',        iw*0.52,  ih*0.63,  iw*0.48,  ih*0.37),
      ],
      // T1 — Bedrooms top, open plan bottom
      [
        R('master_bedroom', 'Master Bedroom', 0,        0,        iw*0.40,  ih*0.40),
        R('bedroom',        'Bedroom',        iw*0.40,  0,        iw*0.38,  ih*0.40),
        R('toilet',         'Toilet',         iw*0.78,  0,        iw*0.12,  ih*0.22),
        R('bathroom',       'Bathroom',       iw*0.90,  0,        iw*0.10,  ih*0.22),
        R('entrance',       'Entrance',       iw*0.78,  ih*0.22,  iw*0.22,  ih*0.18),
        R('living',         'Living Room',    0,        ih*0.40,  iw*0.55,  ih*0.38),
        R('dining',         'Dining Room',    iw*0.55,  ih*0.40,  iw*0.45,  ih*0.20),
        R('kitchen',        'Kitchen',        iw*0.55,  ih*0.60,  iw*0.45,  ih*0.18),
        R('pooja',          'Pooja Room',     0,        ih*0.78,  iw*0.55,  ih*0.22),
      ],
      // T2 — 2-column private/social split
      [
        R('master_bedroom', 'Master Bedroom', 0,        0,        iw*0.50,  ih*0.42),
        R('bedroom',        'Bedroom',        0,        ih*0.42,  iw*0.50,  ih*0.38),
        R('bathroom',       'Bathroom',       0,        ih*0.80,  iw*0.28,  ih*0.20),
        R('toilet',         'Toilet',         iw*0.28,  ih*0.80,  iw*0.22,  ih*0.20),
        R('living',         'Living Room',    iw*0.50,  0,        iw*0.50,  ih*0.42),
        R('dining',         'Dining Room',    iw*0.50,  ih*0.42,  iw*0.50,  ih*0.22),
        R('kitchen',        'Kitchen',        iw*0.50,  ih*0.64,  iw*0.50,  ih*0.20),
        R('entrance',       'Entrance',       iw*0.50,  ih*0.84,  iw*0.25,  ih*0.16),
        R('pooja',          'Pooja Room',     iw*0.75,  ih*0.84,  iw*0.25,  ih*0.16),
      ],
    ],

    // ── 3BHK ─────────────────────────────────────────────────
    // bathroom_master + toilet_master attached to master bedroom
    // bathroom + toilet = common wet zone
    '3BHK': [
      // T0 — 3-row grid
      [
        R('living',            'Living Room',       0,        0,        iw*0.52,  ih*0.33),
        R('entrance',          'Entrance',          iw*0.52,  0,        iw*0.50,  ih*0.11),
        R('pooja',             'Pooja Room',        iw*0.52,  ih*0.11,  iw*0.24,  ih*0.22),
        R('toilet',            'Toilet',            iw*0.76,  ih*0.11,  iw*0.12,  ih*0.18),
        R('bathroom',          'Bathroom',          iw*0.88,  ih*0.11,  iw*0.12,  ih*0.18),
        R('dining',            'Dining Room',       0,        ih*0.33,  iw*0.45,  ih*0.27),
        R('kitchen',           'Kitchen',           iw*0.45,  ih*0.33,  iw*0.55,  ih*0.27),
        R('master_bedroom',    'Master Bedroom',    0,        ih*0.60,  iw*0.38,  ih*0.40),
        R('bathroom_master',   'Bathroom (Master)', iw*0.38,  ih*0.60,  iw*0.13,  ih*0.22),
        R('toilet_master',     'Toilet (Master)',   iw*0.38,  ih*0.82,  iw*0.13,  ih*0.18),
        R('bedroom',           'Bedroom 2',         iw*0.51,  ih*0.60,  iw*0.32,  ih*0.40),
        R('bedroom',           'Bedroom 3',         iw*0.83,  ih*0.60,  iw*0.17,  ih*0.40),
      ],
      // T1 — Bedrooms across top, living bottom
      [
        R('master_bedroom',    'Master Bedroom',    0,        0,        iw*0.35,  ih*0.38),
        R('bathroom_master',   'Bathroom (Master)', iw*0.35,  0,        iw*0.15,  ih*0.22),
        R('toilet_master',     'Toilet (Master)',   iw*0.35,  ih*0.22,  iw*0.15,  ih*0.16),
        R('bedroom',           'Bedroom 2',         iw*0.50,  0,        iw*0.30,  ih*0.38),
        R('bedroom',           'Bedroom 3',         iw*0.80,  0,        iw*0.20,  ih*0.38),
        R('bathroom',          'Bathroom',          0,        ih*0.38,  iw*0.20,  ih*0.24),
        R('toilet',            'Toilet',            iw*0.20,  ih*0.38,  iw*0.15,  ih*0.24),
        R('dining',            'Dining Room',       iw*0.35,  ih*0.38,  iw*0.38,  ih*0.24),
        R('kitchen',           'Kitchen',           iw*0.73,  ih*0.38,  iw*0.27,  ih*0.24),
        R('living',            'Living Room',       0,        ih*0.62,  iw*0.55,  ih*0.38),
        R('pooja',             'Pooja Room',        iw*0.55,  ih*0.62,  iw*0.45,  ih*0.22),
        R('entrance',          'Entrance',          iw*0.55,  ih*0.84,  iw*0.45,  ih*0.16),
      ],
      // T2 — Full-width living top, bedrooms bottom
      [
        R('living',            'Living Room',       0,        0,        iw*1.00,  ih*0.35),
        R('dining',            'Dining Room',       0,        ih*0.35,  iw*0.42,  ih*0.25),
        R('kitchen',           'Kitchen',           iw*0.42,  ih*0.35,  iw*0.38,  ih*0.25),
        R('entrance',          'Entrance',          iw*0.80,  ih*0.35,  iw*0.20,  ih*0.12),
        R('pooja',             'Pooja Room',        iw*0.80,  ih*0.47,  iw*0.20,  ih*0.13),
        R('master_bedroom',    'Master Bedroom',    0,        ih*0.60,  iw*0.38,  ih*0.40),
        R('bathroom_master',   'Bathroom (Master)', iw*0.38,  ih*0.60,  iw*0.14,  ih*0.22),
        R('toilet_master',     'Toilet (Master)',   iw*0.38,  ih*0.82,  iw*0.14,  ih*0.18),
        R('bedroom',           'Bedroom 2',         iw*0.52,  ih*0.60,  iw*0.30,  ih*0.40),
        R('bedroom',           'Bedroom 3',         iw*0.82,  ih*0.60,  iw*0.18,  ih*0.28),
        R('bathroom',          'Bathroom',          iw*0.82,  ih*0.88,  iw*0.10,  ih*0.12),
        R('toilet',            'Toilet',            iw*0.92,  ih*0.88,  iw*0.08,  ih*0.12),
      ],
    ],

    // ── 4BHK ─────────────────────────────────────────────────
    // bathroom_master + toilet_master  → attached to master bedroom
    // bathroom_attached + toilet_attached → attached to bedroom 2
    // bathroom + toilet → common wet zone
    '4BHK': [
      // T0
      [
        R('living',              'Living Room',          0,        0,        iw*0.50,  ih*0.28),
        R('entrance',            'Entrance',             iw*0.50,  0,        iw*0.50,  ih*0.11),
        R('pooja',               'Pooja Room',           iw*0.50,  ih*0.11,  iw*0.24,  ih*0.17),
        R('toilet',              'Toilet',               iw*0.74,  ih*0.11,  iw*0.13,  ih*0.17),
        R('bathroom',            'Bathroom',             iw*0.87,  ih*0.11,  iw*0.13,  ih*0.17),
        R('dining',              'Dining Room',          0,        ih*0.28,  iw*0.38,  ih*0.25),
        R('kitchen',             'Kitchen',              iw*0.38,  ih*0.28,  iw*0.38,  ih*0.25),
        R('utility',             'Utility Room',         iw*0.76,  ih*0.28,  iw*0.24,  ih*0.25),
        R('master_bedroom',      'Master Bedroom',       0,        ih*0.53,  iw*0.28,  ih*0.47),
        R('bathroom_master',     'Bathroom (Master)',    iw*0.28,  ih*0.53,  iw*0.11,  ih*0.27),
        R('toilet_master',       'Toilet (Master)',      iw*0.28,  ih*0.80,  iw*0.11,  ih*0.20),
        R('bedroom',             'Bedroom 2',            iw*0.39,  ih*0.53,  iw*0.25,  ih*0.47),
        R('bathroom_attached',   'Bathroom (Attached)',  iw*0.64,  ih*0.53,  iw*0.10,  ih*0.27),
        R('toilet_attached',     'Toilet (Attached)',    iw*0.64,  ih*0.80,  iw*0.10,  ih*0.20),
        R('bedroom',             'Bedroom 3',            iw*0.74,  ih*0.53,  iw*0.26,  ih*0.25),
        R('bedroom',             'Bedroom 4',            iw*0.74,  ih*0.78,  iw*0.26,  ih*0.22),
      ],
      // T1
      [
        R('master_bedroom',      'Master Bedroom',       0,        0,        iw*0.28,  ih*0.35),
        R('bathroom_master',     'Bathroom (Master)',    iw*0.28,  0,        iw*0.12,  ih*0.20),
        R('toilet_master',       'Toilet (Master)',      iw*0.28,  ih*0.20,  iw*0.12,  ih*0.15),
        R('bedroom',             'Bedroom 2',            iw*0.40,  0,        iw*0.25,  ih*0.35),
        R('bathroom_attached',   'Bathroom (Attached)',  iw*0.65,  0,        iw*0.11,  ih*0.20),
        R('toilet_attached',     'Toilet (Attached)',    iw*0.65,  ih*0.20,  iw*0.11,  ih*0.15),
        R('bedroom',             'Bedroom 3',            iw*0.76,  0,        iw*0.24,  ih*0.35),
        R('bedroom',             'Bedroom 4',            0,        ih*0.35,  iw*0.28,  ih*0.27),
        R('bathroom',            'Bathroom',             iw*0.28,  ih*0.35,  iw*0.12,  ih*0.15),
        R('toilet',              'Toilet',               iw*0.28,  ih*0.50,  iw*0.12,  ih*0.12),
        R('utility',             'Utility Room',         iw*0.40,  ih*0.35,  iw*0.30,  ih*0.27),
        R('pooja',               'Pooja Room',           iw*0.70,  ih*0.35,  iw*0.30,  ih*0.27),
        R('entrance',            'Entrance',             0,        ih*0.62,  iw*0.20,  ih*0.38),
        R('living',              'Living Room',          iw*0.20,  ih*0.62,  iw*0.35,  ih*0.38),
        R('dining',              'Dining Room',          iw*0.55,  ih*0.62,  iw*0.25,  ih*0.38),
        R('kitchen',             'Kitchen',              iw*0.80,  ih*0.62,  iw*0.20,  ih*0.38),
      ],
      // T2
      [
        R('living',              'Living Room',          0,        0,        iw*0.48,  ih*0.35),
        R('dining',              'Dining Room',          iw*0.48,  0,        iw*0.32,  ih*0.22),
        R('kitchen',             'Kitchen',              iw*0.48,  ih*0.22,  iw*0.32,  ih*0.13),
        R('utility',             'Utility Room',         iw*0.80,  0,        iw*0.20,  ih*0.35),
        R('master_bedroom',      'Master Bedroom',       0,        ih*0.35,  iw*0.30,  ih*0.38),
        R('bathroom_master',     'Bathroom (Master)',    iw*0.30,  ih*0.35,  iw*0.12,  ih*0.22),
        R('toilet_master',       'Toilet (Master)',      iw*0.30,  ih*0.57,  iw*0.12,  ih*0.16),
        R('bedroom',             'Bedroom 2',            iw*0.42,  ih*0.35,  iw*0.28,  ih*0.38),
        R('bathroom_attached',   'Bathroom (Attached)',  iw*0.70,  ih*0.35,  iw*0.12,  ih*0.22),
        R('toilet_attached',     'Toilet (Attached)',    iw*0.70,  ih*0.57,  iw*0.12,  ih*0.16),
        R('bedroom',             'Bedroom 3',            iw*0.82,  ih*0.35,  iw*0.18,  ih*0.38),
        R('bedroom',             'Bedroom 4',            0,        ih*0.73,  iw*0.35,  ih*0.27),
        R('bathroom',            'Bathroom',             iw*0.35,  ih*0.73,  iw*0.13,  ih*0.16),
        R('toilet',              'Toilet',               iw*0.35,  ih*0.89,  iw*0.13,  ih*0.11),
        R('entrance',            'Entrance',             iw*0.48,  ih*0.73,  iw*0.22,  ih*0.27),
        R('pooja',               'Pooja Room',           iw*0.70,  ih*0.73,  iw*0.30,  ih*0.27),
      ],
    ],
  };

  const bhkTemplates = templates[bhk] || templates['2BHK'];
  const rawRooms = (bhkTemplates[tidx] || bhkTemplates[0])
    .filter(r => r.w > 0.5 && r.h > 0.5);
  const rooms = rawRooms.map(r => ({ ...r }));

  // Plot shape selection
  const area = pw * ph;
  let plotShape = 'rect';
  if (area >= 2400 && tidx === 1) plotShape = 'L';
  else if (area >= 2400 && tidx === 2) plotShape = 'T';
  if (area >= 3200 && tidx === 0) plotShape = 'L';
  if (area >= 3200 && tidx === 2) plotShape = 'U';

  function buildPolygon(shape, w, h, mg) {
    const uw = w - 2*mg, uh = h - 2*mg;
    if (shape === 'L') {
      const th = uh * 0.55, aw = uw * 0.55;
      return [[mg,mg],[w-mg,mg],[w-mg,mg+th],[mg+aw,mg+th],[mg+aw,h-mg],[mg,h-mg]];
    }
    if (shape === 'T') {
      const th = uh * 0.50, sw = uw * 0.45, sx = (uw - sw) / 2;
      return [[mg,mg],[w-mg,mg],[w-mg,mg+th],[mg+sx+sw,mg+th],[mg+sx+sw,h-mg],[mg+sx,h-mg],[mg+sx,mg+th],[mg,mg+th]];
    }
    if (shape === 'U') {
      const aw = uw * 0.28, ah = uh * 0.55;
      return [[mg,mg],[mg+aw,mg],[mg+aw,mg+ah],[w-mg-aw,mg+ah],[w-mg-aw,mg],[w-mg,mg],[w-mg,h-mg],[mg,h-mg]];
    }
    return [[mg,mg],[w-mg,mg],[w-mg,h-mg],[mg,h-mg]];
  }
  const plotPolygon = buildPolygon(plotShape, pw, ph, 2);

  const vastuScore = tidx === 0 ? 72 : tidx === 1 ? 64 : 58;
  const fitness    = parseFloat((vastuScore / 100 * 0.9).toFixed(4));

  return {
    layout_id:      'demo-' + tidx + '-' + Date.now(),
    rooms,
    vastu_score:    vastuScore,
    fitness,
    space_util:     parseFloat((82 + tidx * 2).toFixed(1)),
    total_room_area:parseFloat(rooms.reduce((s, r) => s + r.area, 0).toFixed(2)),
    plot_shape:     plotShape,
    plot_polygon:   plotPolygon,
    plot_zones:     null,
    plot: { width: pw, height: ph, facing, bhk_type: bhk, usable_area: iw * ih },
    vastu_rules: [
      { label:'Kitchen (SE/NW)',  status: tidx===0?'compliant':'partial',   weight:15, earned:tidx===0?15:8,  description:'SE or NW zone preferred' },
      { label:'Master Bed (SW)',  status: tidx===0?'partial':'compliant',   weight:20, earned:tidx===0?10:20, description:'SW zone preferred' },
      { label:'Living Room (N/E)',status:'compliant',                        weight:15, earned:15,             description:'N or E zone' },
      { label:'Pooja (NE)',       status: tidx===2?'violation':'partial',    weight:15, earned:tidx===2?0:8,   description:'NE corner preferred' },
      { label:'Bathroom (NW/SE)', status:'partial',                          weight:10, earned:5,              description:'NW or SE preferred' },
      { label:'Dining (E/SE)',    status: tidx===1?'compliant':'partial',    weight:10, earned:tidx===1?10:5,  description:'E or SE zone' },
      { label:'Entrance (N/E)',   status:'compliant',                        weight:10, earned:10,             description:'N or E facing' },
    ],
  };
}

// ═══════════════════════════════════════════════════════════════
// RENDER UI
// ═══════════════════════════════════════════════════════════════
function renderUI(elapsed) {
  const sec = document.getElementById('results-section');
  sec.classList.add('visible');
  sec.style.animation = 'scaleIn 0.5s ease forwards';

  document.getElementById('gen-meta').textContent =
    `${currentLayouts.length} layout${currentLayouts.length !== 1 ? 's' : ''} · ${elapsed}ms · ${activeLayout.plot?.bhk_type} · ${activeLayout.plot?.facing} facing`;

  const tabs = document.getElementById('layout-tabs');
  tabs.innerHTML = currentLayouts.map((l, i) => `
    <button class="layout-tab ${i === 0 ? 'active' : ''}"
            onclick="selectLayout(${i})" id="ltab-${i}">
      Layout ${i + 1}
      <span class="tab-score">${l.vastu_score?.toFixed(0)}%</span>
    </button>
  `).join('');

  render2D(activeLayout);
  renderVastu(activeLayout);
  renderLegend(activeLayout);

  setTimeout(() => sec.scrollIntoView({ behavior: 'smooth', block: 'start' }), 200);
}

function selectLayout(idx) {
  activeLayoutIdx = idx;
  activeLayout = currentLayouts[idx];
  document.querySelectorAll('.layout-tab').forEach((t, i) => t.classList.toggle('active', i === idx));
  render2D(activeLayout);
  renderVastu(activeLayout);
  renderLegend(activeLayout);

  if (document.getElementById('tp-3d').classList.contains('active')) {
    render3D(activeLayout);
  }

  document.getElementById('cd-score').textContent = activeLayout.vastu_score?.toFixed(0) + '%';
  document.getElementById('cd-rooms').textContent = activeLayout.rooms?.length;
}

// ═══════════════════════════════════════════════════════════════
// 2D CANVAS
// ═══════════════════════════════════════════════════════════════
// ═══════════════════════════════════════════════════════════════
// ARCHITECTURAL 2D FLOOR PLAN RENDERER
// Produces a proper architectural drawing: thick walls, door swings,
// dimension lines, hatched wet rooms — styled like Image 4 reference
// ═══════════════════════════════════════════════════════════════
function render2D(layout) {
  const canvas = document.getElementById('canvas-2d');
  const wrap   = document.getElementById('canvas-2d-wrap');
  const cw     = wrap.clientWidth || 700;
  const plot   = layout.plot || { width: 40, height: 60 };

  // Margins for dimension annotations
  const DIM_M  = 52;
  const scale  = (cw - DIM_M * 2 - 16) / plot.width;
  const ch     = Math.round(plot.height * scale) + DIM_M * 2 + 40;

  canvas.width  = cw;
  canvas.height = ch;
  canvas.style.height = ch + 'px';

  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, cw, ch);

  // ── Constants ──────────────────────────────────────────────
  const BG     = '#f5f0e8';    // warm paper
  const WALL_C = '#1a1a1a';    // wall ink
  const DIM_C  = '#555555';    // dimension ink
  const W_EXT  = Math.max(4, scale * 0.50);   // exterior wall thickness
  const W_INT  = Math.max(1.5, scale * 0.28); // interior wall thickness

  const ox = DIM_M + 8;        // plot left edge on canvas
  const oy = DIM_M + 8;        // plot top edge on canvas
  const pw = plot.width  * scale;
  const ph = plot.height * scale;

  // ── Paper background ───────────────────────────────────────
  ctx.fillStyle = BG;
  ctx.fillRect(0, 0, cw, ch);

  // Subtle blueprint grid (1 ft intervals)
  ctx.strokeStyle = 'rgba(140,130,110,0.14)';
  ctx.lineWidth   = 0.4;
  for (let x = 0; x <= pw + 1; x += scale) {
    ctx.beginPath(); ctx.moveTo(ox + x, oy); ctx.lineTo(ox + x, oy + ph); ctx.stroke();
  }
  for (let y = 0; y <= ph + 1; y += scale) {
    ctx.beginPath(); ctx.moveTo(ox, oy + y); ctx.lineTo(ox + pw, oy + y); ctx.stroke();
  }

  // ── Room fills ─────────────────────────────────────────────
  layout.rooms.forEach(r => {
    const c  = COLORS[r.type] || C_DEF;
    const rx = ox + r.x * scale;
    const ry = oy + r.y * scale;
    const rw = (r.width  || r.w) * scale;
    const rh = (r.height || r.h) * scale;

    // White base
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(rx, ry, rw, rh);

    // Very subtle colour wash
    ctx.fillStyle = c.fill.replace('0.4', '0.07');
    ctx.fillRect(rx, ry, rw, rh);

    // Diagonal hatching for wet rooms
    const isWet = ['bathroom','toilet','bathroom_master','toilet_master',
                    'bathroom_attached','toilet_attached'].includes(r.type);
    if (isWet) {
      ctx.save();
      ctx.beginPath(); ctx.rect(rx + 1, ry + 1, rw - 2, rh - 2); ctx.clip();
      ctx.strokeStyle = c.stroke + '44';
      ctx.lineWidth   = 0.7;
      const step = 7;
      for (let d = -(rh); d < rw + rh; d += step) {
        ctx.beginPath();
        ctx.moveTo(rx + d, ry);
        ctx.lineTo(rx + d + rh, ry + rh);
        ctx.stroke();
      }
      ctx.restore();
    }
  });

  // ── Interior walls ─────────────────────────────────────────
  layout.rooms.forEach(r => {
    const rx = ox + r.x * scale;
    const ry = oy + r.y * scale;
    const rw = (r.width  || r.w) * scale;
    const rh = (r.height || r.h) * scale;
    ctx.strokeStyle = WALL_C;
    ctx.lineWidth   = W_INT;
    ctx.strokeRect(rx, ry, rw, rh);
  });

  // ── Exterior boundary (thick walls) ────────────────────────
  ctx.strokeStyle = WALL_C;
  ctx.lineWidth   = W_EXT;
  ctx.strokeRect(ox, oy, pw, ph);

  // ── Window symbols on exterior-touching walls ──────────────
  layout.rooms.forEach(r => {
    const rft_x = r.x, rft_y = r.y;
    const rft_w = r.width || r.w, rft_h = r.height || r.h;
    const rx = ox + rft_x * scale, ry = oy + rft_y * scale;
    const rw = rft_w * scale,      rh = rft_h * scale;

    // Skip small rooms and wet rooms
    if (rw < 40 || rh < 40) return;
    const isWet = ['bathroom','toilet','bathroom_master','toilet_master',
                    'bathroom_attached','toilet_attached','entrance','pooja'].includes(r.type);
    if (isWet) return;

    // Top exterior wall?
    if (rft_y < 0.5) _drawWindow(ctx, rx + rw * 0.55, ry, rw * 0.28, true,  BG, W_INT);
    // Bottom exterior wall?
    if (rft_y + rft_h > plot.height - 0.5) _drawWindow(ctx, rx + rw * 0.55, ry + rh, rw * 0.28, true,  BG, W_INT);
    // Left exterior wall?
    if (rft_x < 0.5) _drawWindow(ctx, rx, ry + rh * 0.55, rh * 0.28, false, BG, W_INT);
    // Right exterior wall?
    if (rft_x + rft_w > plot.width - 0.5) _drawWindow(ctx, rx + rw, ry + rh * 0.55, rh * 0.28, false, BG, W_INT);
  });

  // ── Doors ──────────────────────────────────────────────────
  layout.rooms.forEach(r => {
    const rx = ox + r.x * scale;
    const ry = oy + r.y * scale;
    const rw = (r.width  || r.w) * scale;
    const rh = (r.height || r.h) * scale;

    if (rw < 22 || rh < 22) return;

    const isWet = ['bathroom','toilet','bathroom_master','toilet_master',
                    'bathroom_attached','toilet_attached'].includes(r.type);
    const dw = Math.min(isWet ? rw * 0.55 : rw * 0.40, scale * (isWet ? 2.6 : 3.3));

    const side = _doorSide(r, layout.rooms, plot);
    _drawDoor(ctx, rx, ry, rw, rh, dw, side, BG, W_INT);
  });

  // ── Room labels ────────────────────────────────────────────
  layout.rooms.forEach(r => {
    const rx = ox + r.x * scale;
    const ry = oy + r.y * scale;
    const rw = (r.width  || r.w) * scale;
    const rh = (r.height || r.h) * scale;
    if (rw < 18 || rh < 14) return;

    const fs    = Math.max(7, Math.min(11, rw / 7));
    const label = r.label.toUpperCase();
    const words = label.split(' ');
    const mid   = Math.ceil(words.length / 2);
    const line1 = words.slice(0, mid).join(' ');
    const line2 = words.length > 2 ? words.slice(mid).join(' ') : null;
    const dim   = `${(r.width||r.w).toFixed(0)}'-0" × ${(r.height||r.h).toFixed(0)}'-0"`;

    const lineH    = fs + 3;
    const numLines = (line2 ? 2 : 1) + (rh > 30 ? 1 : 0);
    let   textY    = ry + rh / 2 - (numLines * lineH) / 2 + lineH / 2;

    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillStyle = WALL_C;
    ctx.font      = `bold ${fs}px Arial, sans-serif`;
    ctx.fillText(line1, rx + rw / 2, textY); textY += lineH;
    if (line2) { ctx.fillText(line2, rx + rw / 2, textY); textY += lineH; }

    if (rh > 30) {
      ctx.font      = `${Math.max(6, fs - 2)}px Arial, sans-serif`;
      ctx.fillStyle = '#555555';
      ctx.fillText(dim, rx + rw / 2, textY);
    }
  });

  // ── Dimension lines ─────────────────────────────────────────
  // Overall plot dimensions
  _drawDimLine(ctx, ox, oy - 30, ox + pw, oy - 30,
    `${plot.width}'-0"`, true, DIM_C);
  _drawDimLine(ctx, ox - 32, oy, ox - 32, oy + ph,
    `${plot.height}'-0"`, false, DIM_C);

  // Per-room sub-dimensions along top edge
  const topRooms = layout.rooms
    .filter(r => Math.abs(r.y) < 0.5)
    .sort((a, b) => a.x - b.x);
  if (topRooms.length > 1) {
    let curX = ox;
    topRooms.forEach(r => {
      const rw  = (r.width || r.w) * scale;
      const rx2 = ox + r.x * scale + rw;
      if (rw > 24) {
        _drawDimLine(ctx, curX, oy - 14, rx2, oy - 14,
          `${(r.width||r.w).toFixed(0)}'`, true, DIM_C + '99');
      }
      curX = rx2;
    });
  }

  // ── Compass ────────────────────────────────────────────────
  _drawCompassArch(ctx, cw - DIM_M + 14, oy + 36, 24, plot.facing || 'East');

  // ── Scale bar ──────────────────────────────────────────────
  const barFt = 10, barPx = barFt * scale;
  const barX  = ox, barY  = oy + ph + 18;
  ctx.strokeStyle = '#333'; ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.moveTo(barX, barY); ctx.lineTo(barX + barPx, barY); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(barX, barY - 5); ctx.lineTo(barX, barY + 5); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(barX + barPx, barY - 5); ctx.lineTo(barX + barPx, barY + 5); ctx.stroke();
  ctx.fillStyle = '#333'; ctx.font = '8px Arial'; ctx.textAlign = 'center';
  ctx.fillText(`${barFt} FT`, barX + barPx / 2, barY + 13);

  // ── Canvas label ────────────────────────────────────────────
  const lbl = document.getElementById('canvas-label');
  const shapeLbl = { rect:'', L:' · L-Shape', T:' · T-Shape', U:' · U-Shape' };
  if (lbl) lbl.textContent =
    `FLOOR PLAN · ${plot.bhk_type} · ${plot.width}×${plot.height}ft${shapeLbl[layout.plot_shape]||''}`;
}

// ── Door side heuristic: prefer wall shared with adjacent room ─
function _doorSide(r, rooms, plot) {
  const eps = 0.8;
  const rw  = r.width || r.w, rh = r.height || r.h;
  const adj = { top:false, bottom:false, left:false, right:false };

  rooms.forEach(o => {
    if (o === r) return;
    const ow = o.width || o.w, oh = o.height || o.h;
    const overlapH = r.y < o.y + oh - eps && r.y + rh > o.y + eps;
    const overlapV = r.x < o.x + ow - eps && r.x + rw > o.x + eps;
    if (Math.abs((r.x + rw) - o.x)        < eps && overlapH) adj.right  = true;
    if (Math.abs(r.x        - (o.x + ow)) < eps && overlapH) adj.left   = true;
    if (Math.abs((r.y + rh) - o.y)        < eps && overlapV) adj.bottom = true;
    if (Math.abs(r.y        - (o.y + oh)) < eps && overlapV) adj.top    = true;
  });

  // Entrance opens toward the plot boundary (outward)
  if (r.type === 'entrance') {
    const cy = r.y + rh / 2;
    return cy > plot.height / 2 ? 'bottom' : 'top';
  }

  // Prefer interior-facing door (priority: bottom > top > right > left)
  const priority = ['bottom','top','right','left'];
  for (const s of priority) { if (adj[s]) return s; }

  // Fallback: toward plot centre
  const rCX = r.x + rw / 2, rCY = r.y + rh / 2;
  const pCX = plot.width / 2, pCY = plot.height / 2;
  return Math.abs(rCX - pCX) > Math.abs(rCY - pCY)
    ? (rCX < pCX ? 'right' : 'left')
    : (rCY < pCY ? 'bottom' : 'top');
}

// ── Door symbol: gap in wall + door leaf + quarter-circle arc ──
function _drawDoor(ctx, rx, ry, rw, rh, dw, side, bgColor, lineW) {
  const hpos = 0.18; // hinge at 18% from wall start
  ctx.fillStyle   = bgColor;
  ctx.strokeStyle = '#1a1a1a';
  ctx.lineWidth   = 1.2;

  let hx, hy;
  switch (side) {
    case 'bottom':
      hx = rx + rw * hpos; hy = ry + rh;
      ctx.fillRect(hx - 1, hy - lineW - 1, dw + 2, lineW * 2 + 2);  // erase wall
      ctx.beginPath(); ctx.moveTo(hx, hy); ctx.lineTo(hx, hy - dw); ctx.stroke(); // door leaf
      ctx.beginPath(); ctx.arc(hx, hy, dw, -Math.PI / 2, 0); ctx.stroke();        // swing arc
      break;
    case 'top':
      hx = rx + rw * hpos; hy = ry;
      ctx.fillRect(hx - 1, hy - lineW - 1, dw + 2, lineW * 2 + 2);
      ctx.beginPath(); ctx.moveTo(hx, hy); ctx.lineTo(hx, hy + dw); ctx.stroke();
      ctx.beginPath(); ctx.arc(hx, hy, dw, Math.PI / 2, 0, true); ctx.stroke();
      break;
    case 'right':
      hx = rx + rw; hy = ry + rh * hpos;
      ctx.fillRect(hx - lineW - 1, hy - 1, lineW * 2 + 2, dw + 2);
      ctx.beginPath(); ctx.moveTo(hx, hy); ctx.lineTo(hx - dw, hy); ctx.stroke();
      ctx.beginPath(); ctx.arc(hx, hy, dw, Math.PI, Math.PI / 2, true); ctx.stroke();
      break;
    case 'left':
      hx = rx; hy = ry + rh * hpos;
      ctx.fillRect(hx - lineW - 1, hy - 1, lineW * 2 + 2, dw + 2);
      ctx.beginPath(); ctx.moveTo(hx, hy); ctx.lineTo(hx + dw, hy); ctx.stroke();
      ctx.beginPath(); ctx.arc(hx, hy, dw, 0, Math.PI / 2); ctx.stroke();
      break;
  }
}

// ── Window symbol: triple-line notch in wall ───────────────────
function _drawWindow(ctx, wx, wy, wLen, isHoriz, bgColor, lineW) {
  ctx.fillStyle   = bgColor;
  ctx.strokeStyle = '#1a1a1a';

  if (isHoriz) {
    // Horizontal wall: erase and draw 3 horizontal lines
    ctx.fillRect(wx - 1, wy - lineW - 1, wLen + 2, lineW * 2 + 2);
    ctx.lineWidth = 0.7;
    const y1 = wy - 3, y2 = wy, y3 = wy + 3;
    [y1, y2, y3].forEach(y => {
      ctx.beginPath(); ctx.moveTo(wx, y); ctx.lineTo(wx + wLen, y); ctx.stroke();
    });
  } else {
    ctx.fillRect(wx - lineW - 1, wy - 1, lineW * 2 + 2, wLen + 2);
    ctx.lineWidth = 0.7;
    const x1 = wx - 3, x2 = wx, x3 = wx + 3;
    [x1, x2, x3].forEach(x => {
      ctx.beginPath(); ctx.moveTo(x, wy); ctx.lineTo(x, wy + wLen); ctx.stroke();
    });
  }
}

// ── Dimension line with tick marks ─────────────────────────────
function _drawDimLine(ctx, x1, y1, x2, y2, label, isHoriz, color) {
  ctx.strokeStyle = color; ctx.lineWidth = 0.8;
  ctx.fillStyle   = color;
  ctx.font        = '8px Arial, sans-serif';
  const tick = 5;

  if (isHoriz) {
    ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y1); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x1, y1-tick); ctx.lineTo(x1, y1+tick); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x2, y1-tick); ctx.lineTo(x2, y1+tick); ctx.stroke();
    ctx.textAlign = 'center'; ctx.textBaseline = 'bottom';
    ctx.fillText(label, (x1 + x2) / 2, y1 - 2);
  } else {
    ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x1, y2); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x1-tick, y1); ctx.lineTo(x1+tick, y1); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x1-tick, y2); ctx.lineTo(x1+tick, y2); ctx.stroke();
    ctx.save();
    ctx.translate(x1 - 5, (y1 + y2) / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.textAlign = 'center'; ctx.textBaseline = 'bottom';
    ctx.fillText(label, 0, 0);
    ctx.restore();
  }
}

// ── Architectural compass rose (light-mode) ─────────────────────
function _drawCompassArch(ctx, cx, cy, r, facing) {
  const dirs = { North:0, East:90, South:180, West:270 };
  const a    = (dirs[facing] || 0) * Math.PI / 180;
  ctx.save(); ctx.translate(cx, cy);

  // Circle
  ctx.beginPath(); ctx.arc(0, 0, r, 0, Math.PI * 2);
  ctx.strokeStyle = '#888'; ctx.lineWidth = 1; ctx.stroke();
  ctx.fillStyle   = 'rgba(255,255,255,0.88)'; ctx.fill();

  // Cardinal labels
  ['N','E','S','W'].forEach((d, i) => {
    const da = i * Math.PI / 2;
    ctx.fillStyle    = d === 'N' ? '#b91c1c' : '#444';
    ctx.font         = `bold ${r * 0.30}px Arial`;
    ctx.textAlign    = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(d, Math.sin(da) * r * 0.65, -Math.cos(da) * r * 0.65);
  });

  // Needle
  ctx.rotate(a);
  ctx.fillStyle = '#b91c1c';
  ctx.beginPath(); ctx.moveTo(0, -(r*0.60)); ctx.lineTo(3.5,0); ctx.lineTo(0,6); ctx.lineTo(-3.5,0); ctx.closePath(); ctx.fill();
  ctx.fillStyle = 'rgba(0,0,0,0.22)';
  ctx.beginPath(); ctx.moveTo(0, r*0.60); ctx.lineTo(3,0); ctx.lineTo(0,-6); ctx.lineTo(-3,0); ctx.closePath(); ctx.fill();

  // Centre dot
  ctx.beginPath(); ctx.arc(0, 0, 2.5, 0, Math.PI * 2);
  ctx.fillStyle = '#b91c1c'; ctx.fill();

  ctx.restore();
}

// ── Legacy compass (kept for 3D module compatibility) ───────────
function drawCompass(ctx, cx, cy, r, facing) {
  _drawCompassArch(ctx, cx, cy, r, facing);
}

function rRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x+r, y); ctx.lineTo(x+w-r, y); ctx.arcTo(x+w,y,x+w,y+r,r);
  ctx.lineTo(x+w,y+h-r); ctx.arcTo(x+w,y+h,x+w-r,y+h,r);
  ctx.lineTo(x+r,y+h); ctx.arcTo(x,y+h,x,y+h-r,r);
  ctx.lineTo(x,y+r); ctx.arcTo(x,y,x+r,y,r); ctx.closePath();
}

// ═══════════════════════════════════════════════════════════════
// 3D RENDERER
// ═══════════════════════════════════════════════════════════════
function render3D(layout) {
  const canvas = document.getElementById('canvas-3d');
  if (!canvas) return;
  if (renderer3D) { renderer3D.dispose(); renderer3D = null; }

  const w = canvas.parentElement.clientWidth || 600;
  const h = 420;
  canvas.style.height = h + 'px';

  const plot  = layout.plot || { width: 40, height: 60 };
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x020b18);
  scene.fog = new THREE.Fog(0x020b18, 80, 300);

  const camera = new THREE.PerspectiveCamera(50, w / h, 0.1, 600);
  const R = Math.sqrt(plot.width ** 2 + plot.height ** 2) * 1.15;
  camera.position.set(plot.width * 0.9, R * 0.7, plot.height * 0.9);
  camera.lookAt(plot.width / 2, 0, plot.height / 2);

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
  renderer.setSize(w, h);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer3D = renderer;

  build3DScene(scene, layout);

  let drag = false, px = 0, py = 0, theta = 0.7, phi = 0.75;
  const tgt = new THREE.Vector3(plot.width / 2, 0, plot.height / 2);

  function updateCam() {
    camera.position.set(
      tgt.x + R * Math.sin(phi) * Math.sin(theta),
      tgt.y + R * Math.cos(phi),
      tgt.z + R * Math.sin(phi) * Math.cos(theta)
    );
    camera.lookAt(tgt);
  }
  updateCam();

  canvas.addEventListener('mousedown', e => { drag = true; px = e.clientX; py = e.clientY; });
  window.addEventListener('mouseup',  () => { drag = false; });
  window.addEventListener('mousemove', e => {
    if (!drag) return;
    theta -= (e.clientX - px) * 0.01;
    phi    = Math.max(0.1, Math.min(1.5, phi - (e.clientY - py) * 0.01));
    px = e.clientX; py = e.clientY; updateCam();
  });
  canvas.addEventListener('wheel', e => {
    phi = Math.max(0.1, Math.min(1.5, phi + e.deltaY * 0.002));
    updateCam(); e.preventDefault();
  }, { passive: false });

  function loop() { requestAnimationFrame(loop); renderer.render(scene, camera); }
  loop();
}

function build3DScene(scene, layout) {
  const plot = layout.plot || { width: 40, height: 60 };

  const floorG = new THREE.PlaneGeometry(plot.width + 12, plot.height + 12);
  const floorM = new THREE.MeshLambertMaterial({ color: 0x040f1f });
  const floor  = new THREE.Mesh(floorG, floorM);
  floor.rotation.x = -Math.PI / 2;
  floor.position.set(plot.width / 2, -0.1, plot.height / 2);
  floor.receiveShadow = true; scene.add(floor);

  const grid = new THREE.GridHelper(Math.max(plot.width, plot.height) * 2.5, 50, 0x071529, 0x071529);
  grid.position.set(plot.width / 2, 0.02, plot.height / 2); scene.add(grid);

  scene.add(new THREE.AmbientLight(0x334155, 0.9));
  const sun = new THREE.DirectionalLight(0xffffff, 1.2);
  sun.position.set(plot.width * 1.5, plot.height * 2, plot.height * 1.2);
  sun.castShadow = true; scene.add(sun);
  const fill = new THREE.PointLight(0x38bdf8, 0.5, 300);
  fill.position.set(plot.width / 2, 50, plot.height / 2); scene.add(fill);
  const warm = new THREE.PointLight(0xc9962a, 0.4, 200);
  warm.position.set(plot.width, 30, plot.height); scene.add(warm);

  const wallH = 9;
  layout.rooms.forEach(r => {
    const c   = COLORS[r.type] || C_DEF;
    const rw  = r.width || r.w, rh = r.height || r.h;
    const geo = new THREE.BoxGeometry(rw * 0.94, wallH, rh * 0.94);
    const mat = new THREE.MeshLambertMaterial({ color: c.hex, transparent: true, opacity: 0.88 });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.set(r.x + rw / 2, wallH / 2, r.y + rh / 2);
    mesh.castShadow = true; mesh.receiveShadow = true; scene.add(mesh);

    const eMat = new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.07 });
    scene.add(Object.assign(new THREE.LineSegments(new THREE.EdgesGeometry(geo), eMat),
      { position: mesh.position.clone() }));

    const topG = new THREE.PlaneGeometry(rw * 0.94, rh * 0.94);
    const topM = new THREE.MeshLambertMaterial({ color: c.hex, transparent: true, opacity: 0.25, side: THREE.DoubleSide });
    const top  = new THREE.Mesh(topG, topM);
    top.rotation.x = -Math.PI / 2;
    top.position.set(r.x + rw / 2, wallH, r.y + rh / 2);
    scene.add(top);
  });

  const bGeo = new THREE.BoxGeometry(plot.width, 0.5, plot.height);
  const bMat = new THREE.MeshBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.1, wireframe: true });
  const boundary = new THREE.Mesh(bGeo, bMat);
  boundary.position.set(plot.width / 2, 0, plot.height / 2); scene.add(boundary);
}

// ═══════════════════════════════════════════════════════════════
// VIEW SWITCHER
// ═══════════════════════════════════════════════════════════════
function switchView(v) {
  document.querySelectorAll('.view-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.getElementById('vt-' + v).classList.add('active');
  document.getElementById('tp-' + v).classList.add('active');
  if (v === '3d' && activeLayout) render3D(activeLayout);
}

// ═══════════════════════════════════════════════════════════════
// VASTU UI
// ═══════════════════════════════════════════════════════════════
function renderVastu(layout) {
  const score = layout.vastu_score || 0;
  const arc   = document.getElementById('score-arc');
  const circ  = 345.4;
  arc.style.strokeDashoffset = (circ - (score / 100) * circ).toString();
  document.getElementById('score-num').textContent     = Math.round(score);
  document.getElementById('score-pct-label').textContent = '/ 100';
  document.getElementById('ms-fitness').textContent    = (layout.fitness || 0).toFixed(3);
  document.getElementById('ms-util').innerHTML         = `${Math.round(layout.space_util || 0)}<span class="unit">%</span>`;

  const rules     = layout.vastu_rules || [];
  const container = document.getElementById('vastu-rules');
  if (!rules.length) {
    container.innerHTML = '<div style="font-family:var(--ff-mono);font-size:0.7rem;color:var(--slate-600);padding:0.5rem">No rule data available</div>';
    return;
  }

  const icons = { Kitchen:'🍳', Master:'🛏', Living:'🛋', Pooja:'🪔', Bathroom:'🚿', Dining:'🍽', Entrance:'🚪' };
  container.innerHTML = rules.map(r => {
    const icon  = Object.entries(icons).find(([k]) => r.label.includes(k))?.[1] || '🏠';
    const cls   = r.status === 'compliant' ? 'vr-ok' : r.status === 'partial' ? 'vr-warn' : r.status === 'missing' ? 'vr-miss' : 'vr-bad';
    const badge = r.status === 'compliant' ? '✓ OK' : r.status === 'partial' ? '~ Fair' : r.status === 'missing' ? '- N/A' : '✗ Fail';
    return `<div class="vastu-rule">
      <span class="vr-icon">${icon}</span>
      <div class="vr-info">
        <div class="vr-name">${r.label}</div>
        <div class="vr-dir">${r.description || ''}</div>
      </div>
      <span class="vr-badge ${cls}">${badge}</span>
    </div>`;
  }).join('');
}

// ═══════════════════════════════════════════════════════════════
// LEGEND
// ═══════════════════════════════════════════════════════════════
function renderLegend(layout) {
  const seen  = new Set();
  const items = layout.rooms
    .filter(r => { if (seen.has(r.type)) return false; seen.add(r.type); return true; })
    .map(r => {
      const c = COLORS[r.type] || C_DEF;
      return `<div class="legend-item">
        <div class="legend-swatch" style="background:${c.fill};border:1px solid ${c.stroke}"></div>
        <span>${r.label}</span>
      </div>`;
    }).join('');
  document.getElementById('legend-grid').innerHTML = items;
}

// ═══════════════════════════════════════════════════════════════
// RESULTS PAGE DATA
// ═══════════════════════════════════════════════════════════════
function updateResults() {
  if (!activeLayout) return;
  const l = activeLayout;
  const p = l.plot || {};

  document.getElementById('results-empty').style.display = 'none';
  document.getElementById('results-data').style.display  = 'block';

  document.getElementById('r-sub').textContent =
    `Layout ID: ${l.layout_id || '—'} · Generated via ${l.layout_id?.startsWith('demo') ? 'Demo Mode' : 'Flask GA Engine'}`;

  document.getElementById('r-plot').textContent   = `${p.width||'—'}×${p.height||'—'}`;
  document.getElementById('r-bhk').textContent    = p.bhk_type || '—';
  document.getElementById('r-facing').textContent = p.facing || '—';
  document.getElementById('r-vscore').innerHTML   = `${Math.round(l.vastu_score||0)}<span class="kpi-unit">%</span>`;
  document.getElementById('r-rooms').textContent  = l.rooms?.length || '—';
  document.getElementById('r-area').innerHTML     = `${((p.width||0)*(p.height||0)).toLocaleString()}<span class="kpi-unit">sqft</span>`;
  document.getElementById('r-util').innerHTML     = `${Math.round(l.space_util||0)}<span class="kpi-unit">%</span>`;
  document.getElementById('r-fit').textContent    = (l.fitness||0).toFixed(4);

  const bars = document.getElementById('breakdown-bars');
  bars.innerHTML = (l.vastu_rules || []).map(r => {
    const pct = r.weight > 0 ? Math.round((r.earned / r.weight) * 100) : 0;
    const col = pct >= 80 ? '#4ade80' : pct >= 50 ? '#fbbf24' : '#f87171';
    return `<div class="bar-row">
      <div class="bar-label">${r.label}</div>
      <div class="bar-track"><div class="bar-fill" style="width:${pct}%;background:${col}"></div></div>
      <div class="bar-pct">${pct}%</div>
    </div>`;
  }).join('');

  const tbody = document.getElementById('room-table-body');
  tbody.innerHTML = (l.rooms || []).map(r => `
    <tr>
      <td>${r.label}</td>
      <td class="td-type">${r.type}</td>
      <td>${(r.width||r.w||0).toFixed(1)}</td>
      <td>${(r.height||r.h||0).toFixed(1)}</td>
      <td class="td-area">${(r.area||0).toFixed(0)}</td>
    </tr>
  `).join('');
}

// ═══════════════════════════════════════════════════════════════
// AR MODULE BRIDGE
// ═══════════════════════════════════════════════════════════════
function initAR() {
  if (!activeLayout) {
    document.getElementById('ar-empty').style.display       = 'block';
    document.getElementById('ar-viewer-wrap').style.display = 'none';
    return;
  }
  document.getElementById('ar-empty').style.display       = 'none';
  document.getElementById('ar-viewer-wrap').style.display = 'block';
  if (typeof ARViewer !== 'undefined') {
    ARViewer.destroy();
    ARViewer.init(activeLayout);
  }
}

function arReset()      { ARViewer?.reset();           }
function arWireframe()  { ARViewer?.toggleWireframe(); }
function arTop()        { ARViewer?.setTop();          }
function arFullscreen() { ARViewer?.fullscreen();      }

// ═══════════════════════════════════════════════════════════════
// PDF EXPORT
// ═══════════════════════════════════════════════════════════════
async function exportPDF() {
  if (!activeLayout || !window.activeLayout) {
    showToast('⚠ Generate a floor plan first.', '⚠');
    return;
  }

  if (typeof PDFExporter !== 'undefined') {
    PDFExporter.open(window.activeLayout);
  } else {
    showToast('⚠ PDF module not loaded', '⚠');
  }
}
// ═══════════════════════════════════════════════════════════════
// LOADING OVERLAY
// ═══════════════════════════════════════════════════════════════
function showLoadingOverlay(show) {
  document.getElementById('loading-overlay').classList.toggle('active', show);
}

// ═══════════════════════════════════════════════════════════════
// TOAST
// ═══════════════════════════════════════════════════════════════
let toastTimer = null;
function showToast(msg, icon = '✦') {
  const t = document.getElementById('toast');
  document.getElementById('toast-msg').textContent  = msg;
  document.getElementById('toast-icon').textContent = icon;
  t.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('show'), 3500);
}

// ═══════════════════════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════════════════════
window.addEventListener('load', () => {
  checkAPI();
  setTimeout(() => {
    const l0 = buildLocalPlan('40x60', '2BHK', 'East', 0);
    const l1 = buildLocalPlan('40x60', '2BHK', 'East', 1);
    const l2 = buildLocalPlan('40x60', '2BHK', 'East', 2);
    currentLayouts  = [l0, l1, l2];
    activeLayout    = l0;
    activeLayoutIdx = 0;
    renderUI(0);
    updateResults();
    document.getElementById('cd-score').textContent = l0.vastu_score.toFixed(0) + '%';
    document.getElementById('cd-rooms').textContent = l0.rooms.length;
    document.getElementById('cd-gen').textContent   = 'DEMO';
  }, 600);
});

window.addEventListener('resize', () => {
  if (activeLayout) render2D(activeLayout);
});

// ═══════════════════════════════════════════════════════════════
// THEME TOGGLE
// ═══════════════════════════════════════════════════════════════
function toggleTheme() {
  const html    = document.documentElement;
  const btn     = document.getElementById('theme-toggle');
  const current = html.getAttribute('data-theme') || 'dark';
  const next    = current === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', next);
  localStorage.setItem('intelliplan-theme', next);
  if (btn) btn.setAttribute('data-tooltip', next === 'dark' ? 'Toggle Light Mode' : 'Toggle Dark Mode');
  if (activeLayout) setTimeout(() => render2D(activeLayout), 380);
  showToast(next === 'light' ? '☀ Light mode' : '◐ Dark mode', next === 'light' ? '☀' : '◐');
}

(function applySavedTheme() {
  const saved = localStorage.getItem('intelliplan-theme');
  if (saved) {
    document.documentElement.setAttribute('data-theme', saved);
    window.addEventListener('DOMContentLoaded', () => {
      const btn = document.getElementById('theme-toggle');
      if (btn) btn.setAttribute('data-tooltip', saved === 'dark' ? 'Toggle Light Mode' : 'Toggle Dark Mode');
    });
  }
})();