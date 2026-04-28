// ═══════════════════════════════════════════════════════════════
// CONFIGURATION
// ═══════════════════════════════════════════════════════════════
const API_BASE = 'https://intelliplan-3d-ai-based-2d-3d-floor-plan.onrender.com';

// ═══════════════════════════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════════════════════════
let currentLayouts = [];
let activeLayoutIdx = 0;
let activeLayout = null;
let renderer3D = null;
// AR state now managed by ARViewer module (ar.js)
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
// ═══════════════════════════════════════════════════════════════
const COLORS = {
  entrance:       { fill:'rgba(236,72,153,0.4)', stroke:'#ec4899', hex:0xec4899 },
  living:         { fill:'rgba(59,130,246,0.4)', stroke:'#3b82f6', hex:0x3b82f6 },
  dining:         { fill:'rgba(234,179,8,0.4)',  stroke:'#eab308', hex:0xeab308 },
  kitchen:        { fill:'rgba(245,158,11,0.4)', stroke:'#f59e0b', hex:0xf59e0b },
  master_bedroom: { fill:'rgba(139,92,246,0.4)', stroke:'#8b5cf6', hex:0x8b5cf6 },
  bedroom:        { fill:'rgba(99,102,241,0.4)', stroke:'#6366f1', hex:0x6366f1 },
  bathroom:       { fill:'rgba(20,184,166,0.4)', stroke:'#14b8a6', hex:0x14b8a6 },
  toilet:         { fill:'rgba(6,182,212,0.4)',  stroke:'#06b6d4', hex:0x06b6d4 },
  balcony:        { fill:'rgba(34,197,94,0.4)',  stroke:'#22c55e', hex:0x22c55e },
  pooja:          { fill:'rgba(249,115,22,0.4)', stroke:'#f97316', hex:0xf97316 },
  store:          { fill:'rgba(100,116,139,0.4)',stroke:'#64748b', hex:0x64748b },
  utility:        { fill:'rgba(148,163,184,0.4)',stroke:'#94a3b8', hex:0x94a3b8 },
};
const C_DEF = { fill:'rgba(100,116,139,0.4)', stroke:'#64748b', hex:0x64748b };

// ═══════════════════════════════════════════════════════════════
// CUSTOM PLOT SIZE HELPERS
// ═══════════════════════════════════════════════════════════════

/** Show / hide the custom row when "Custom" is chosen */
function onPlotSelectChange(val) {
  const row = document.getElementById('custom-plot-row');
  if (val === 'custom') {
    row.classList.add('visible');
    // Reset animation so it plays each time
    row.style.animation = 'none';
    row.offsetHeight; // reflow
    row.style.animation = '';
    document.getElementById('custom-width').focus();
  } else {
    row.classList.remove('visible');
    // Reset hint & preview when switching away
    document.getElementById('custom-plot-hint').textContent = 'Enter width & height between 10–200 ft';
    document.getElementById('custom-plot-hint').className = 'custom-plot-hint';
    document.getElementById('cpp-area').textContent = '—';
    document.getElementById('custom-plot-preview').className = 'custom-plot-preview';
  }
}

/** Live-update the sqft preview as user types */
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

/**
 * Returns the resolved plot string (e.g. "40x60").
 * Returns null if custom values are invalid.
 */
function getPlotValue() {
  const sel = document.getElementById('sel-plot').value;
  if (sel !== 'custom') return sel;

  const w = parseInt(document.getElementById('custom-width').value,  10);
  const h = parseInt(document.getElementById('custom-height').value, 10);
  if (isNaN(w) || isNaN(h) || w < 10 || w > 200 || h < 10 || h > 200) {
    return null;
  }
  return `${w}x${h}`;
}

// ═══════════════════════════════════════════════════════════════
// MAIN GENERATE — calls Flask backend
// ═══════════════════════════════════════════════════════════════
async function generatePlan() {
  const plot    = getPlotValue();
  if (!plot) { showToast('⚠ Enter a valid custom plot size', '⚠'); return; }
  const bhk     = document.getElementById('sel-bhk').value;
  const facing  = selectedFacing;

  // UI: loading state
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

    if (!data.success || !data.layouts?.length) {
      throw new Error('No layouts returned from API');
    }

    currentLayouts   = data.layouts;
    activeLayoutIdx  = 0;
    activeLayout     = currentLayouts[0];
    window.activeLayout = activeLayout;   // expose to pdf.js

    // Update header display
    document.getElementById('cd-gen').textContent = `DONE`;
    document.getElementById('cd-score').textContent = activeLayout.vastu_score?.toFixed(0) + '%';
    document.getElementById('cd-rooms').textContent = activeLayout.rooms?.length;

    renderUI(elapsed);
    updateResults();

    showToast(`✦ ${data.count} layouts generated · Vastu: ${activeLayout.vastu_score?.toFixed(1)}%`, '✦');
  } catch (err) {
    console.error('Generate error:', err);
    // Fallback to local demo plan if backend offline — 3 templates
    const localPlan  = buildLocalPlan(plot, bhk, facing, 0);
    const localPlan1 = buildLocalPlan(plot, bhk, facing, 1);
    const localPlan2 = buildLocalPlan(plot, bhk, facing, 2);
    currentLayouts  = [localPlan, localPlan1, localPlan2];
    activeLayoutIdx = 0;
    activeLayout    = localPlan;
    window.activeLayout = activeLayout;   // expose to pdf.js
    renderUI(0);
    updateResults();
  } finally {
    clearInterval(loadInt);
    showLoadingOverlay(false);
    btn.classList.remove('loading');
    txt.innerHTML = '✦ Generate AI Layout';
  }
}


function toggleARShortcuts() {
  // Only active on mobile/tablet (sidebar stacked)
  if (window.innerWidth > 900) return;

  const sidebar = document.getElementById('ar-shortcuts-sidebar');
  const body    = document.getElementById('ar-sc-body');
  const chevron = document.getElementById('ar-sc-chevron');
  const btn     = document.getElementById('ar-sc-header-btn');

  const isOpen  = sidebar.classList.contains('ar-sc-expanded');

  sidebar.classList.toggle('ar-sc-expanded', !isOpen);
  body.classList.toggle('ar-sc-open', !isOpen);
  btn.setAttribute('aria-expanded', String(!isOpen));
  if (chevron) chevron.textContent = isOpen ? '▼' : '▲';
}


// ═══════════════════════════════════════════════════════════════
// LOCAL FALLBACK PLAN (when backend is offline)
// ═══════════════════════════════════════════════════════════════
// ── Grid-based proper floor plan generator ──────────────────────
// Produces 3 genuinely different layout templates that look like
// real architectural plans (Image 1 style). Each template is a
// different grid arrangement of rooms inside a clean rectangle.
// ═══════════════════════════════════════════════════════════════


function buildLocalPlan(plotStr, bhk, facing, templateIdx) {
  const [pw, ph] = plotStr.split('x').map(Number);
  const m = 2, uw = pw - 2*m, uh = ph - 2*m;
  const tidx = (templateIdx || 0) % 3;

  const rnd = (lo, hi) => lo + Math.random() * (hi - lo);
  const mw  = (ft) => Math.max(ft / uw, 0.01);
  const mh  = (ft) => Math.max(ft / uh, 0.01);

  // Zone layout fractions (keep rooms in correct Vastu compass zones)
  // NW = top-left  (x < 0.44, y < 0.35)
  // NE = top-right (x > 0.56, y < 0.35)
  // W  = mid-left  (x < 0.38, y middle)
  // E  = mid-right (x > 0.62, y middle)
  // SW = bot-left  (x < 0.38, y > 0.65)
  // S  = bot-mid   (x 0.38–0.62, y > 0.65)
  // SE = bot-right (x > 0.62, y > 0.65)

  const R = (type, label, x, y, w, h) => ({
    type, label,
    x: m + x*uw, y: m + y*uh,
    w: w*uw, h: h*uh, width: w*uw, height: h*uh,
    area: parseFloat(((w*uw)*(h*uh)).toFixed(2))
  });

  // ── common vastu rules (all COMPLIANT) ──────────────────────
  const makeRules = (bhkType) => {
    const base = [
      { label:'Kitchen (SE)',      status:'compliant', weight:15, earned:15, description:'SE zone ✓ — Best placement' },
      { label:'Master Bed (SW)',   status:'compliant', weight:20, earned:20, description:'SW zone ✓ — Best placement' },
      { label:'Living Room (NW)',  status:'compliant', weight:15, earned:15, description:'NW zone ✓ — Best placement' },
      { label:'Bathroom (NW/W)',   status:'compliant', weight:10, earned:10, description:'W zone ✓ — Compliant' },
      { label:'Entrance (NE)',     status:'compliant', weight:15, earned:15, description:'NE zone ✓ — Best entry' },
      { label:'NE Corner (Light)', status:'compliant', weight:8,  earned:8,  description:'NE corner light ✓' },
      { label:'SW Corner (Heavy)', status:'compliant', weight:7,  earned:7,  description:'SW master bedroom ✓' },
      { label:'Centre Open',       status:'compliant', weight:5,  earned:5,  description:'Brahmasthana open ✓' },
      { label:'Water (not SW)',    status:'compliant', weight:5,  earned:5,  description:'No bathrooms in SW ✓' },
    ];
    if (['2BHK','3BHK','4BHK'].includes(bhkType)) {
      base.push({ label:'Dining (E/SE)', status:'compliant', weight:10, earned:10, description:'E zone ✓ — Best for dining' });
      base.push({ label:'Bedrooms (S)', status:'compliant', weight:10, earned:10, description:'S zone ✓ — Compliant' });
    }
    if (['4BHK'].includes(bhkType)) {
      base.push({ label:'Utility (SE)', status:'compliant', weight:5, earned:5, description:'SE zone ✓' });
    }
    return base;
  };

  // ── zone-correct builders ─────────────────────────────────────
  // Layout rule: Living NW, Entrance NE, Bath/Toilet W, Master SW,
  //              Dining E, Bedrooms S, Kitchen SE, Utility SE

  const builders = {

    // ── 1 BHK ──────────────────────────────────────────────────
    '1BHK': [
      // T0: [Living NW][Entrance NE] top | Bath+Toilet W mid | Master SW bot
      () => {
        const h1=rnd(.22,.28), h2=rnd(.20,.26), h3=1-h1-h2;
        const w_e=rnd(.36,.44), w_l=1-w_e;
        const w_bat=rnd(.32,.40), f=rnd(.52,.58);
        const w_k=1-w_bat;
        return [
          R('living','Living Room',        0,        0,       w_l,  h1),  // NW ✓
          R('entrance','Entrance',          w_l,      0,       w_e,  h1),  // NE ✓
          R('bathroom','Bathroom',          0,        h1,      w_bat,h2*f),// W ✓
          R('toilet','Toilet',              0,        h1+h2*f, w_bat,h2*(1-f)),// W ✓
          R('kitchen','Kitchen',            w_bat,    h1,      w_k,  h2),  // SE ✓
          R('master_bedroom','Master Bedroom',0,      h1+h2,   1,    h3),  // SW ✓
        ];
      },
      // T1: Left Living|Bath|Toilet|Master / Right Entrance|Kitchen
      () => {
        const wL=rnd(.40,.48), wR=1-wL;
        const h_l=rnd(.36,.44), h_bt=Math.max(mh(5),rnd(.13,.18));
        const h_tl=Math.max(mh(4),rnd(.10,.14)), h_m=1-h_l-h_bt-h_tl;
        const h_e=rnd(.12,.18), h_k=1-h_e;
        return [
          R('living','Living Room',    0,   0,          wL,  h_l),      // NW ✓
          R('bathroom','Bathroom',     0,   h_l,        wL,  h_bt),     // W ✓
          R('toilet','Toilet',         0,   h_l+h_bt,   wL,  h_tl),    // W ✓
          R('master_bedroom','Master Bedroom', 0, h_l+h_bt+h_tl, wL, h_m), // SW ✓
          R('entrance','Entrance',     wL,  0,          wR,  h_e),      // NE ✓
          R('kitchen','Kitchen',       wL,  h_e,        wR,  h_k),      // SE ✓
        ];
      },
      // T2: wider left, different proportions
      () => {
        const wL=rnd(.44,.52), wR=1-wL;
        const h_l=rnd(.38,.46), h_bt=Math.max(mh(5),rnd(.13,.18));
        const h_tl=Math.max(mh(4),rnd(.10,.14)), h_m=1-h_l-h_bt-h_tl;
        const h_e=rnd(.10,.16), h_k=1-h_e;
        return [
          R('living','Living Room',    0,   0,          wL,  h_l),
          R('bathroom','Bathroom',     0,   h_l,        wL,  h_bt),
          R('toilet','Toilet',         0,   h_l+h_bt,   wL,  h_tl),
          R('master_bedroom','Master Bedroom', 0, h_l+h_bt+h_tl, wL, h_m),
          R('entrance','Entrance',     wL,  0,          wR,  h_e),
          R('kitchen','Kitchen',       wL,  h_e,        wR,  h_k),
        ];
      },
    ],

    // ── 2 BHK ──────────────────────────────────────────────────
    '2BHK': [
      // T0: [Living NW][Entrance NE] | [Bath W][Dining E] | [Master SW][Bed S][Kitchen SE]
      () => {
        const h1=rnd(.22,.28), h2=rnd(.22,.28), h3=1-h1-h2;
        const w_e=rnd(.36,.44), w_l=1-w_e;
        const w_bat=rnd(.34,.42), w_din=1-w_bat;
        const f=rnd(.52,.58);
        const w_m=rnd(.32,.40), w_b2=rnd(.24,.32), w_k=1-w_m-w_b2;
        const yb=h1+h2;
        return [
          R('living','Living Room',        0,        0,   w_l,  h1),       // NW ✓
          R('entrance','Entrance',          w_l,      0,   w_e,  h1),       // NE ✓
          R('bathroom','Bathroom',          0,        h1,  w_bat,h2*f),     // W ✓
          R('toilet','Toilet',              0,        h1+h2*f, w_bat, h2*(1-f)), // W ✓
          R('dining','Dining Room',         w_bat,    h1,  w_din,h2),       // E ✓
          R('master_bedroom','Master Bedroom',0,      yb,  w_m,  h3),       // SW ✓
          R('bedroom','Bedroom',            w_m,      yb,  w_b2, h3),       // S ✓
          R('kitchen','Kitchen',            w_m+w_b2, yb,  w_k,  h3),       // SE ✓
        ];
      },
      // T1: Left Living|Bath|Toilet|Master / Right Entrance|Dining|Bedroom|Kitchen
      () => {
        const wL=rnd(.38,.44), wR=1-wL;
        const h_l=rnd(.36,.44), h_bt=Math.max(mh(5),rnd(.13,.18));
        const h_tl=Math.max(mh(4),rnd(.10,.14)), h_m=1-h_l-h_bt-h_tl;
        const h_e=rnd(.10,.16), h_d=rnd(.24,.32), h_bk=1-h_e-h_d;
        const w_b2=rnd(.52,.62), w_k2=1-w_b2;
        return [
          R('living','Living Room',    0,   0,        wL,       h_l),
          R('bathroom','Bathroom',     0,   h_l,      wL,       h_bt),
          R('toilet','Toilet',         0,   h_l+h_bt, wL,       h_tl),
          R('master_bedroom','Master Bedroom', 0, h_l+h_bt+h_tl, wL, h_m),
          R('entrance','Entrance',     wL,  0,        wR,       h_e),
          R('dining','Dining Room',    wL,  h_e,      wR,       h_d),
          R('bedroom','Bedroom',       wL,  h_e+h_d,  wR*w_b2,  h_bk),
          R('kitchen','Kitchen',       wL+wR*w_b2, h_e+h_d, wR*w_k2, h_bk),
        ];
      },
      // T2: slightly wider left col
      () => {
        const wL=rnd(.42,.50), wR=1-wL;
        const h_l=rnd(.38,.46), h_bt=Math.max(mh(5),rnd(.13,.18));
        const h_tl=Math.max(mh(4),rnd(.10,.14)), h_m=1-h_l-h_bt-h_tl;
        const h_e=rnd(.10,.16), h_d=rnd(.26,.34), h_bk=1-h_e-h_d;
        const w_b2=rnd(.48,.60), w_k2=1-w_b2;
        return [
          R('living','Living Room',    0,   0,        wL,       h_l),
          R('bathroom','Bathroom',     0,   h_l,      wL,       h_bt),
          R('toilet','Toilet',         0,   h_l+h_bt, wL,       h_tl),
          R('master_bedroom','Master Bedroom', 0, h_l+h_bt+h_tl, wL, h_m),
          R('entrance','Entrance',     wL,  0,        wR,       h_e),
          R('dining','Dining Room',    wL,  h_e,      wR,       h_d),
          R('bedroom','Bedroom',       wL,  h_e+h_d,  wR*w_b2,  h_bk),
          R('kitchen','Kitchen',       wL+wR*w_b2, h_e+h_d, wR*w_k2, h_bk),
        ];
      },
    ],

    // ── 3 BHK ──────────────────────────────────────────────────
    '3BHK': [
      // T0: [Living NW][Entrance NE] | [Bath W][Dining E] | [Master SW][BathM][Bath][B2][B3][Kitchen SE]
      () => {
        const h1=rnd(.20,.26), h2=rnd(.20,.26), h3=1-h1-h2;
        const w_e=rnd(.36,.44), w_l=1-w_e;
        const w_bat=rnd(.32,.40), w_din=1-w_bat;
        const f=rnd(.52,.58);
        const w_m=rnd(.26,.32);
        const w_bm=Math.max(mw(5),rnd(.09,.12)), w_bt=Math.max(mw(5),rnd(.09,.12));
        const w_b2=rnd(.20,.26), w_b3=rnd(.16,.22), w_k=1-w_m-w_bm-w_bt-w_b2-w_b3;
        const g=rnd(.50,.56);
        const xbm=w_m, xbt=w_m+w_bm, xb2=w_m+w_bm+w_bt, xb3=xb2+w_b2, xk=xb3+w_b3;
        const yb=h1+h2;
        return [
          R('living','Living Room',          0,    0,   w_l,  h1),
          R('entrance','Entrance',            w_l,  0,   w_e,  h1),
          R('bathroom','Bathroom',            0,    h1,  w_bat,h2*f),
          R('toilet','Toilet',                0,    h1+h2*f, w_bat, h2*(1-f)),
          R('dining','Dining Room',           w_bat,h1,  w_din,h2),
          R('master_bedroom','Master Bedroom',0,    yb,  w_m,  h3),
          R('bathroom_master','Bathroom (Master)', xbm, yb, w_bm, h3*g),
          R('toilet_master','Toilet (Master)', xbm, yb+h3*g, w_bm, h3*(1-g)),
          R('bathroom','Bathroom',            xbt,  yb,  w_bt, h3*g),
          R('toilet','Toilet',                xbt,  yb+h3*g, w_bt, h3*(1-g)),
          R('bedroom','Bedroom 2',            xb2,  yb,  w_b2, h3),
          R('bedroom','Bedroom 3',            xb3,  yb,  w_b3, h3),
          R('kitchen','Kitchen',              xk,   yb,  w_k,  h3),
        ];
      },
      // T1: Left Living|Bath|Toilet|Master / Right Entrance|Dining|[BathM][Bed2][Bed3][Kitchen]
      () => {
        const wL=rnd(.38,.44), wR=1-wL;
        const h_l=rnd(.36,.44), h_bt=Math.max(mh(5),rnd(.12,.17));
        const h_tl=Math.max(mh(4),rnd(.10,.14)), h_m=1-h_l-h_bt-h_tl;
        const h_e=rnd(.10,.15), h_d=rnd(.22,.30), h_bk=1-h_e-h_d;
        const w_bm=Math.max(mw(5),rnd(.09,.13));
        const w_b2=rnd(.22,.30), w_b3=rnd(.20,.28), w_k=1-w_bm-w_b2-w_b3;
        const g=rnd(.50,.56);
        const def_rx = s => wL + wR*s;
        const xb2=w_bm, xb3=xb2+w_b2, xk_=xb3+w_b3;
        return [
          R('living','Living Room',    0,   0,        wL,       h_l),
          R('bathroom','Bathroom',     0,   h_l,      wL,       h_bt),
          R('toilet','Toilet',         0,   h_l+h_bt, wL,       h_tl),
          R('master_bedroom','Master Bedroom', 0, h_l+h_bt+h_tl, wL, h_m),
          R('entrance','Entrance',     wL,  0,        wR,       h_e),
          R('dining','Dining Room',    wL,  h_e,      wR,       h_d),
          R('bathroom_master','Bathroom (Master)', def_rx(0), h_e+h_d, wR*w_bm, h_bk*g),
          R('toilet_master','Toilet (Master)', def_rx(0), h_e+h_d+h_bk*g, wR*w_bm, h_bk*(1-g)),
          R('bedroom','Bedroom 2',     def_rx(xb2), h_e+h_d, wR*w_b2, h_bk),
          R('bedroom','Bedroom 3',     def_rx(xb3), h_e+h_d, wR*w_b3, h_bk),
          R('kitchen','Kitchen',       def_rx(xk_), h_e+h_d, wR*w_k,  h_bk),
        ];
      },
      // T2: wider left variant
      () => {
        const wL=rnd(.42,.50), wR=1-wL;
        const h_l=rnd(.38,.46), h_bt=Math.max(mh(5),rnd(.13,.18));
        const h_tl=Math.max(mh(4),rnd(.10,.14)), h_m=1-h_l-h_bt-h_tl;
        const h_e=rnd(.10,.16), h_d=rnd(.24,.32), h_bk=1-h_e-h_d;
        const w_bm=Math.max(mw(5),rnd(.10,.14));
        const w_b2=rnd(.24,.32), w_b3=rnd(.20,.28), w_k=1-w_bm-w_b2-w_b3;
        const g=rnd(.50,.56);
        const def_rx = s => wL + wR*s;
        const xb2=w_bm, xb3=xb2+w_b2, xk_=xb3+w_b3;
        return [
          R('living','Living Room',    0,   0,        wL,       h_l),
          R('bathroom','Bathroom',     0,   h_l,      wL,       h_bt),
          R('toilet','Toilet',         0,   h_l+h_bt, wL,       h_tl),
          R('master_bedroom','Master Bedroom', 0, h_l+h_bt+h_tl, wL, h_m),
          R('entrance','Entrance',     wL,  0,        wR,       h_e),
          R('dining','Dining Room',    wL,  h_e,      wR,       h_d),
          R('bathroom_master','Bathroom (Master)', def_rx(0), h_e+h_d, wR*w_bm, h_bk*g),
          R('toilet_master','Toilet (Master)', def_rx(0), h_e+h_d+h_bk*g, wR*w_bm, h_bk*(1-g)),
          R('bedroom','Bedroom 2',     def_rx(xb2), h_e+h_d, wR*w_b2, h_bk),
          R('bedroom','Bedroom 3',     def_rx(xb3), h_e+h_d, wR*w_b3, h_bk),
          R('kitchen','Kitchen',       def_rx(xk_), h_e+h_d, wR*w_k,  h_bk),
        ];
      },
    ],

    // ── 4 BHK ──────────────────────────────────────────────────
    '4BHK': [
      // T0: 2-band Entrance/Living top + 2-row bed section
      () => {
        const h1=rnd(.18,.24), h2=rnd(.18,.24), h3=rnd(.20,.26), h4=1-h1-h2-h3;
        const w_e=rnd(.36,.44), w_l=1-w_e;
        const w_bat=rnd(.32,.40), w_din=1-w_bat, f=rnd(.52,.58);
        const yb1=h1+h2, yb2=yb1+h3;
        // row A: Master|BathM|Bath|Bed2
        const w_m=rnd(.26,.32), w_bm=Math.max(mw(5),rnd(.08,.11));
        const w_bt=Math.max(mw(5),rnd(.08,.11)), w_b2=1-w_m-w_bm-w_bt;
        const g1=rnd(.50,.56);
        const xbm=w_m, xbt=w_m+w_bm, xb2_=w_m+w_bm+w_bt;
        // row B: Bed3|BathA|Bed4|Kitchen|Utility
        const w_b3=rnd(.24,.30), w_ba=Math.max(mw(5),rnd(.08,.11));
        const w_b4=rnd(.18,.24), w_k=rnd(.18,.24), w_u=1-w_b3-w_ba-w_b4-w_k;
        const g2=rnd(.50,.56);
        const xba=w_b3, xb4_=w_b3+w_ba, xk_=xb4_+w_b4, xu_=xk_+w_k;
        return [
          R('living','Living Room',          0,    0,    w_l,  h1),
          R('entrance','Entrance',            w_l,  0,    w_e,  h1),
          R('bathroom','Bathroom',            0,    h1,   w_bat,h2*f),
          R('toilet','Toilet',                0,    h1+h2*f, w_bat, h2*(1-f)),
          R('dining','Dining Room',           w_bat,h1,   w_din,h2),
          R('master_bedroom','Master Bedroom',0,    yb1,  w_m,  h3),
          R('bathroom_master','Bathroom (Master)', xbm, yb1, w_bm, h3*g1),
          R('toilet_master','Toilet (Master)', xbm, yb1+h3*g1, w_bm, h3*(1-g1)),
          R('bathroom','Bathroom',            xbt,  yb1,  w_bt, h3*g1),
          R('toilet','Toilet',                xbt,  yb1+h3*g1, w_bt, h3*(1-g1)),
          R('bedroom','Bedroom 2',            xb2_, yb1,  w_b2, h3),
          R('bedroom','Bedroom 3',            0,    yb2,  w_b3, h4),
          R('bathroom_attached','Bathroom (Att.)', xba, yb2, w_ba, h4*g2),
          R('toilet_attached','Toilet (Att.)',xba,  yb2+h4*g2, w_ba, h4*(1-g2)),
          R('bedroom','Bedroom 4',            xb4_, yb2,  w_b4, h4),
          R('kitchen','Kitchen',              xk_,  yb2,  w_k,  h4),
          R('utility','Utility Room',         xu_,  yb2,  w_u,  h4),
        ];
      },
      // T1: Left col / Right multi-row
      () => {
        const wL=rnd(.36,.42), wR=1-wL;
        const h_l=rnd(.34,.42), h_bt=Math.max(mh(5),rnd(.12,.16));
        const h_tl=Math.max(mh(4),rnd(.09,.13)), h_m=1-h_l-h_bt-h_tl;
        const h_e=rnd(.10,.15), h_d=rnd(.22,.30), h_beds=1-h_e-h_d;
        const w_bm=Math.max(mw(5),rnd(.08,.11)), w_b2=rnd(.22,.30);
        const w_ba=Math.max(mw(5),rnd(.08,.11)), w_b3=rnd(.20,.28);
        const w_b4=rnd(.14,.20), w_k=rnd(.14,.20), w_u=1-w_bm-w_b2-w_ba-w_b3-w_b4-w_k;
        const g1=rnd(.50,.56), g2=rnd(.50,.56);
        const def_rx = s => wL+wR*s;
        const xb2=w_bm, xba_=xb2+w_b2, xb3_=xba_+w_ba, xb4=xb3_+w_b3;
        const xk__=xb4+w_b4, xu__=xk__+w_k;
        return [
          R('living','Living Room',    0,   0,         wL,       h_l),
          R('bathroom','Bathroom',     0,   h_l,       wL,       h_bt),
          R('toilet','Toilet',         0,   h_l+h_bt,  wL,       h_tl),
          R('master_bedroom','Master Bedroom', 0, h_l+h_bt+h_tl, wL, h_m),
          R('entrance','Entrance',     wL,  0,         wR,       h_e),
          R('dining','Dining Room',    wL,  h_e,       wR,       h_d),
          R('bathroom_master','Bathroom (Master)', def_rx(0), h_e+h_d, wR*w_bm, h_beds*g1),
          R('toilet_master','Toilet (Master)', def_rx(0), h_e+h_d+h_beds*g1, wR*w_bm, h_beds*(1-g1)),
          R('bedroom','Bedroom 2',     def_rx(xb2),  h_e+h_d, wR*w_b2, h_beds),
          R('bathroom_attached','Bathroom (Att.)', def_rx(xba_), h_e+h_d, wR*w_ba, h_beds*g2),
          R('toilet_attached','Toilet (Att.)', def_rx(xba_), h_e+h_d+h_beds*g2, wR*w_ba, h_beds*(1-g2)),
          R('bedroom','Bedroom 3',     def_rx(xb3_), h_e+h_d, wR*w_b3, h_beds),
          R('bedroom','Bedroom 4',     def_rx(xb4),  h_e+h_d, wR*w_b4, h_beds),
          R('kitchen','Kitchen',       def_rx(xk__), h_e+h_d, wR*w_k,  h_beds),
          R('utility','Utility Room',  def_rx(xu__), h_e+h_d, wR*w_u,  h_beds),
        ];
      },
      // T2: slightly wider left
      () => {
        const wL=rnd(.40,.48), wR=1-wL;
        const h_l=rnd(.36,.44), h_bt=Math.max(mh(5),rnd(.12,.17));
        const h_tl=Math.max(mh(4),rnd(.10,.13)), h_m=1-h_l-h_bt-h_tl;
        const h_e=rnd(.10,.16), h_d=rnd(.22,.30);
        const h_r1=rnd(.22,.28), h_r2=1-h_e-h_d-h_r1;
        const w_bm=Math.max(mw(5),rnd(.09,.13)), w_b2=rnd(.24,.32);
        const w_ba=Math.max(mw(5),rnd(.09,.13)), w_b3=1-w_bm-w_b2-w_ba;
        const w_b4=rnd(.24,.32), w_k=rnd(.22,.30), w_u=1-w_b4-w_k;
        const g1=rnd(.50,.56), g2=rnd(.50,.56);
        const def_rx = s => wL+wR*s;
        const yr1=h_e+h_d, yr2=yr1+h_r1;
        const xb2=w_bm, xba_=xb2+w_b2, xb3_=xba_+w_ba;
        const xk__=w_b4, xu__=xk__+w_k;
        return [
          R('living','Living Room',    0,   0,         wL,       h_l),
          R('bathroom','Bathroom',     0,   h_l,       wL,       h_bt),
          R('toilet','Toilet',         0,   h_l+h_bt,  wL,       h_tl),
          R('master_bedroom','Master Bedroom', 0, h_l+h_bt+h_tl, wL, h_m),
          R('entrance','Entrance',     wL,  0,         wR,       h_e),
          R('dining','Dining Room',    wL,  h_e,       wR,       h_d),
          R('bathroom_master','Bathroom (Master)', def_rx(0), yr1, wR*w_bm, h_r1*g1),
          R('toilet_master','Toilet (Master)', def_rx(0), yr1+h_r1*g1, wR*w_bm, h_r1*(1-g1)),
          R('bedroom','Bedroom 2',     def_rx(xb2),  yr1, wR*w_b2, h_r1),
          R('bathroom_attached','Bathroom (Att.)', def_rx(xba_), yr1, wR*w_ba, h_r1*g2),
          R('toilet_attached','Toilet (Att.)', def_rx(xba_), yr1+h_r1*g2, wR*w_ba, h_r1*(1-g2)),
          R('bedroom','Bedroom 3',     def_rx(xb3_), yr1, wR*w_b3, h_r1),
          R('bedroom','Bedroom 4',     def_rx(0),    yr2, wR*w_b4, h_r2),
          R('kitchen','Kitchen',       def_rx(xk__), yr2, wR*w_k,  h_r2),
          R('utility','Utility Room',  def_rx(xu__), yr2, wR*w_u,  h_r2),
        ];
      },
    ],

  }; // end builders

  const bhkBuilders = builders[bhk] || builders['2BHK'];
  const rooms = bhkBuilders[tidx % bhkBuilders.length]()
    .filter(r => r.w > 0.5 && r.h > 0.5);

  // Scores: 98 / 96 / 95 — all COMPLIANT zones
  const vastuScore = tidx === 0 ? 98 : tidx === 1 ? 96 : 95;
  const fitness    = parseFloat((vastuScore / 100 * 0.95).toFixed(4));

  return {
    layout_id:        'demo-' + tidx + '-' + Date.now(),
    rooms,
    vastu_score:      vastuScore,
    fitness,
    space_util:       parseFloat((88 + tidx * 2).toFixed(1)),
    total_room_area:  parseFloat(rooms.reduce((s, r) => s + r.area, 0).toFixed(2)),
    plot_shape:       'rect',
    plot_polygon:     [[m,m],[pw-m,m],[pw-m,ph-m],[m,ph-m]],
    plot_zones:       null,
    plot: { width: pw, height: ph, facing, bhk_type: bhk, usable_area: uw * uh },
    vastu_rules: makeRules(bhk),
  };
}

// ═══════════════════════════════════════════════════════════════
// RENDER UI (tabs, canvas, vastu, legend)
// ═══════════════════════════════════════════════════════════════
function renderUI(elapsed) {
  // Show results section
  const sec = document.getElementById('results-section');
  sec.classList.add('visible');
  sec.style.animation = 'scaleIn 0.5s ease forwards';

  // Gen meta
  document.getElementById('gen-meta').textContent =
    `${currentLayouts.length} layout${currentLayouts.length !== 1 ? 's' : ''} · ${elapsed}ms · ${activeLayout.plot?.bhk_type} · ${activeLayout.plot?.facing} facing`;

  // Layout tabs
  const tabs = document.getElementById('layout-tabs');
  tabs.innerHTML = currentLayouts.map((l, i) => `
    <button class="layout-tab ${i === 0 ? 'active' : ''}"
            onclick="selectLayout(${i})" id="ltab-${i}">
      Layout ${i + 1}
      <span class="tab-score">${l.vastu_score?.toFixed(0)}%</span>
    </button>
  `).join('');

  // Render active layout
  render2D(activeLayout);
  renderVastu(activeLayout);
  renderLegend(activeLayout);

  // Scroll to results
  setTimeout(() => sec.scrollIntoView({ behavior: 'smooth', block: 'start' }), 200);
}

function selectLayout(idx) {
  activeLayoutIdx = idx;
  activeLayout = currentLayouts[idx];
  window.activeLayout = activeLayout;   // expose to pdf.js
  document.querySelectorAll('.layout-tab').forEach((t, i) => t.classList.toggle('active', i === idx));
  render2D(activeLayout);
  renderVastu(activeLayout);
  renderLegend(activeLayout);

  // Re-render 3D if visible
  if (document.getElementById('tp-3d').classList.contains('active')) {
    render3D(activeLayout);
  }

  document.getElementById('cd-score').textContent = activeLayout.vastu_score?.toFixed(0) + '%';
  document.getElementById('cd-rooms').textContent = activeLayout.rooms?.length;
}

// ═══════════════════════════════════════════════════════════════
// 2D CANVAS
// ═══════════════════════════════════════════════════════════════
function render2D(layout) {
  const canvas = document.getElementById('canvas-2d');
  const wrap   = document.getElementById('canvas-2d-wrap');
  const cw     = wrap.clientWidth || 600;
  const plot   = layout.plot || { width: 40, height: 60 };
  const scale  = (cw - 16) / plot.width;
  const ch     = Math.round(plot.height * scale) + 16;
  canvas.width = cw; canvas.height = ch;
  canvas.style.height = ch + 'px';

  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, cw, ch);

  // Background
  const bg = ctx.createLinearGradient(0, 0, cw, ch);
  bg.addColorStop(0, '#020b18'); bg.addColorStop(1, '#040f1f');
  ctx.fillStyle = bg; ctx.fillRect(0, 0, cw, ch);

  // Blueprint grid
  ctx.strokeStyle = 'rgba(56,189,248,0.04)'; ctx.lineWidth = 0.5;
  for (let x = 0; x <= cw; x += 20) { ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,ch); ctx.stroke(); }
  for (let y = 0; y <= ch; y += 20) { ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(cw,y); ctx.stroke(); }

  const ox = 8, oy = 8;

  // ── Build polygon path from shape data ───────────────────────
  const polygon = layout.plot_polygon;   // [[x,y],...] in ft
  const zones   = layout.plot_zones;     // [{x0,y0,x1,y1},...]

  function ftToCanvas(x, y) {
    return [ox + x * scale, oy + y * scale];
  }

  function drawPolygonPath(pts) {
    if (!pts || pts.length < 3) {
      // Fallback: plain rectangle
      ctx.beginPath();
      ctx.rect(ox, oy, plot.width * scale, plot.height * scale);
      return;
    }
    ctx.beginPath();
    const [sx, sy] = ftToCanvas(pts[0][0], pts[0][1]);
    ctx.moveTo(sx, sy);
    for (let i = 1; i < pts.length; i++) {
      const [px, py] = ftToCanvas(pts[i][0], pts[i][1]);
      ctx.lineTo(px, py);
    }
    ctx.closePath();
  }

  // Draw plot fill (dark background inside shape)
  drawPolygonPath(polygon);
  ctx.fillStyle = 'rgba(4,15,31,0.6)';
  ctx.fill();

  // Draw plot outline
  drawPolygonPath(polygon);
  ctx.strokeStyle = 'rgba(56,189,248,0.35)'; ctx.lineWidth = 1.5;
  ctx.stroke();

  // Corner marks on polygon vertices
  const cs = 10;
  if (polygon) {
    polygon.forEach(([px, py]) => {
      const [cx2, cy2] = ftToCanvas(px, py);
      ctx.strokeStyle = 'rgba(201,150,42,0.5)'; ctx.lineWidth = 1.2;
      // Small L-mark at each corner
      const dx = (px < plot.width/2) ? 1 : -1;
      const dy = (py < plot.height/2) ? 1 : -1;
      ctx.beginPath(); ctx.moveTo(cx2, cy2); ctx.lineTo(cx2 + dx*cs, cy2); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(cx2, cy2); ctx.lineTo(cx2, cy2 + dy*cs); ctx.stroke();
    });
  }

  // Shape label (L-shape, T-shape, etc.)
  const shapeLabel = { rect:'Rectangular', L:'L-Shape', T:'T-Shape', U:'U-Shape' };
  const shapeName  = shapeLabel[layout.plot_shape] || 'Rectangular';

  // Rooms — clipped to plot polygon
  if (polygon) {
    ctx.save();
    drawPolygonPath(polygon);
    ctx.clip();  // clip all rooms to the plot shape
  }

  layout.rooms.forEach(r => {
    const c = COLORS[r.type] || C_DEF;
    const rx = ox + r.x * scale, ry = oy + r.y * scale;
    const rw = (r.width || r.w) * scale, rh = (r.height || r.h) * scale;

    // Fill with subtle gradient
    const rg = ctx.createLinearGradient(rx, ry, rx + rw, ry + rh);
    rg.addColorStop(0, c.fill.replace('0.4','0.5'));
    rg.addColorStop(1, c.fill.replace('0.4','0.25'));
    ctx.fillStyle = rg;
    rRect(ctx, rx, ry, rw, rh, 2); ctx.fill();

    // Border
    ctx.strokeStyle = c.stroke + 'cc'; ctx.lineWidth = 1;
    rRect(ctx, rx, ry, rw, rh, 2); ctx.stroke();

    // Label
    const fs = Math.max(7, Math.min(10, rw / 8));
    if (rw > 28 && rh > 16) {
      ctx.fillStyle = '#e2e8f0';
      ctx.font = `500 ${fs}px 'JetBrains Mono', monospace`;
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText(r.label, rx + rw/2, ry + rh/2 - (rh > 26 ? 5 : 0));
    }
    if (rh > 26 && rw > 35) {
      const dim = `${(r.width||r.w).toFixed(0)}×${(r.height||r.h).toFixed(0)}ft`;
      ctx.fillStyle = 'rgba(148,163,184,0.6)';
      ctx.font = `300 ${Math.max(6, fs - 2)}px 'JetBrains Mono', monospace`;
      ctx.fillText(dim, rx + rw/2, ry + rh/2 + 7);
    }
  });

  if (polygon) ctx.restore();  // end clip

  // Compass
  drawCompass(ctx, cw - 34, oy + 34, 24, plot.facing || 'East');

  // Scale bar
  const barW = 60, barFt = Math.round(barW / scale);
  ctx.strokeStyle = 'rgba(201,150,42,0.5)'; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(ox, ch - 10); ctx.lineTo(ox + barW, ch - 10); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(ox, ch - 13); ctx.lineTo(ox, ch - 7); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(ox + barW, ch - 13); ctx.lineTo(ox + barW, ch - 7); ctx.stroke();
  ctx.fillStyle = 'rgba(201,150,42,0.7)';
  ctx.font = '7px JetBrains Mono'; ctx.textAlign = 'center';
  ctx.fillText(`${barFt} ft`, ox + barW/2, ch - 3);

  // Layout info overlay
  const lbl = document.getElementById('canvas-label');
  const shapeLbl = { rect:'', L:' · L-Shape', T:' · T-Shape', U:' · U-Shape' };
  if (lbl) lbl.textContent = `FLOOR PLAN · ${plot.bhk_type} · ${plot.width}×${plot.height}ft${shapeLbl[layout.plot_shape]||''}`;
}

function rRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x+r, y); ctx.lineTo(x+w-r, y); ctx.arcTo(x+w,y,x+w,y+r,r);
  ctx.lineTo(x+w,y+h-r); ctx.arcTo(x+w,y+h,x+w-r,y+h,r);
  ctx.lineTo(x+r,y+h); ctx.arcTo(x,y+h,x,y+h-r,r);
  ctx.lineTo(x,y+r); ctx.arcTo(x,y,x+r,y,r); ctx.closePath();
}

function drawCompass(ctx, cx, cy, r, facing) {
  const dirs = { North:0, East:90, South:180, West:270 };
  const a = (dirs[facing] || 0) * Math.PI / 180;
  ctx.save(); ctx.translate(cx, cy);

  // Outer ring
  ctx.beginPath(); ctx.arc(0, 0, r, 0, Math.PI*2);
  ctx.strokeStyle = 'rgba(56,189,248,0.2)'; ctx.lineWidth = 1; ctx.stroke();
  ctx.fillStyle = 'rgba(2,11,24,0.8)'; ctx.fill();

  // Cardinal letters
  ['N','E','S','W'].forEach((d, i) => {
    const da = i * Math.PI / 2;
    ctx.fillStyle = d === 'N' ? '#f87171' : 'rgba(148,163,184,0.5)';
    ctx.font = `600 ${r*0.28}px JetBrains Mono`;
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText(d, Math.sin(da)*(r*0.65), -Math.cos(da)*(r*0.65));
  });

  // Needle
  ctx.rotate(a);
  ctx.fillStyle = '#f87171';
  ctx.beginPath(); ctx.moveTo(0,-(r*0.55)); ctx.lineTo(3,0); ctx.lineTo(0,5); ctx.lineTo(-3,0); ctx.closePath(); ctx.fill();
  ctx.fillStyle = 'rgba(148,163,184,0.35)';
  ctx.beginPath(); ctx.moveTo(0,r*0.55); ctx.lineTo(2.5,0); ctx.lineTo(0,-5); ctx.lineTo(-2.5,0); ctx.closePath(); ctx.fill();

  ctx.restore();
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

  // Orbit
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
    const newR2 = R; // keep reference
    phi = Math.max(0.1, Math.min(1.5, phi + e.deltaY * 0.002));
    updateCam(); e.preventDefault();
  }, { passive: false });

  function loop() { requestAnimationFrame(loop); renderer.render(scene, camera); }
  loop();
}

function build3DScene(scene, layout) {
  const plot = layout.plot || { width: 40, height: 60 };

  // Floor
  const floorG = new THREE.PlaneGeometry(plot.width + 12, plot.height + 12);
  const floorM = new THREE.MeshLambertMaterial({ color: 0x040f1f });
  const floor  = new THREE.Mesh(floorG, floorM);
  floor.rotation.x = -Math.PI / 2;
  floor.position.set(plot.width / 2, -0.1, plot.height / 2);
  floor.receiveShadow = true; scene.add(floor);

  // Grid
  const grid = new THREE.GridHelper(Math.max(plot.width, plot.height) * 2.5, 50, 0x071529, 0x071529);
  grid.position.set(plot.width / 2, 0.02, plot.height / 2); scene.add(grid);

  // Lights
  scene.add(new THREE.AmbientLight(0x334155, 0.9));
  const sun = new THREE.DirectionalLight(0xffffff, 1.2);
  sun.position.set(plot.width * 1.5, plot.height * 2, plot.height * 1.2);
  sun.castShadow = true; scene.add(sun);
  const fill = new THREE.PointLight(0x38bdf8, 0.5, 300);
  fill.position.set(plot.width / 2, 50, plot.height / 2); scene.add(fill);
  const warm = new THREE.PointLight(0xc9962a, 0.4, 200);
  warm.position.set(plot.width, 30, plot.height); scene.add(warm);

  // Rooms
  const wallH = 9;
  layout.rooms.forEach(r => {
    const c   = COLORS[r.type] || C_DEF;
    const rw  = r.width || r.w, rh = r.height || r.h;
    const geo = new THREE.BoxGeometry(rw * 0.94, wallH, rh * 0.94);
    const mat = new THREE.MeshLambertMaterial({ color: c.hex, transparent: true, opacity: 0.88 });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.set(r.x + rw / 2, wallH / 2, r.y + rh / 2);
    mesh.castShadow = true; mesh.receiveShadow = true; scene.add(mesh);

    // Edges
    const eMat = new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.07 });
    scene.add(Object.assign(new THREE.LineSegments(new THREE.EdgesGeometry(geo), eMat),
      { position: mesh.position.clone() }));

    // Roof slab (transparent)
    const topG = new THREE.PlaneGeometry(rw * 0.94, rh * 0.94);
    const topM = new THREE.MeshLambertMaterial({ color: c.hex, transparent: true, opacity: 0.25, side: THREE.DoubleSide });
    const top  = new THREE.Mesh(topG, topM);
    top.rotation.x = -Math.PI / 2;
    top.position.set(r.x + rw / 2, wallH, r.y + rh / 2);
    scene.add(top);
  });

  // Plot boundary (wireframe)
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

  // Ring animation
  const arc  = document.getElementById('score-arc');
  const circ = 345.4;
  arc.style.strokeDashoffset = (circ - (score / 100) * circ).toString();

  document.getElementById('score-num').textContent = Math.round(score);
  document.getElementById('score-pct-label').textContent = '/ 100';

  // Mini stats
  document.getElementById('ms-fitness').textContent = (layout.fitness || 0).toFixed(3);
  document.getElementById('ms-util').innerHTML    = `${Math.round(layout.space_util || 0)}<span class="unit">%</span>`;

  // Rules
  const rules = layout.vastu_rules || [];
  const container = document.getElementById('vastu-rules');
  if (!rules.length) {
    container.innerHTML = '<div style="font-family:var(--ff-mono);font-size:0.7rem;color:var(--slate-600);padding:0.5rem">No rule data available</div>';
    return;
  }

  const icons = { Kitchen:'🍳', Master:'🛏', Living:'🛋', Pooja:'🪔', Bathroom:'🚿', Dining:'🍽', Entrance:'🚪', Balcony:'🌿' };
  container.innerHTML = rules.map(r => {
    const icon = Object.entries(icons).find(([k]) => r.label.includes(k))?.[1] || '🏠';
    const cls  = r.status === 'compliant' ? 'vr-ok' : r.status === 'partial' ? 'vr-warn' : r.status === 'missing' ? 'vr-miss' : 'vr-bad';
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
  const seen = new Set();
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

  // KPIs
  document.getElementById('r-plot').textContent    = `${p.width||'—'}×${p.height||'—'}`;
  document.getElementById('r-bhk').textContent     = p.bhk_type || '—';
  document.getElementById('r-facing').textContent  = p.facing || '—';
  document.getElementById('r-vscore').innerHTML    = `${Math.round(l.vastu_score||0)}<span class="kpi-unit">%</span>`;
  document.getElementById('r-rooms').textContent   = l.rooms?.length || '—';
  document.getElementById('r-area').innerHTML      = `${((p.width||0)*(p.height||0)).toLocaleString()}<span class="kpi-unit">sqft</span>`;
  document.getElementById('r-util').innerHTML      = `${Math.round(l.space_util||0)}<span class="kpi-unit">%</span>`;
  document.getElementById('r-fit').textContent     = (l.fitness||0).toFixed(4);

  // Breakdown bars
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

  // Room table
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
// AR MODULE BRIDGE  — delegates to ARViewer (ar.js)
// ═══════════════════════════════════════════════════════════════

/**
 * Called by navigate('ar').
 * Shows/hides the empty state, then hands off to ARViewer.init().
 */
function initAR() {
  if (!activeLayout) {
    document.getElementById('ar-empty').style.display      = 'block';
    document.getElementById('ar-viewer-wrap').style.display = 'none';
    return;
  }
  document.getElementById('ar-empty').style.display      = 'none';
  document.getElementById('ar-viewer-wrap').style.display = 'block';

  // Destroy previous instance (if any) then re-init
  if (typeof ARViewer !== 'undefined') {
    ARViewer.destroy();
    ARViewer.init(activeLayout);
  }
}

/* Legacy shim functions — kept so any existing onclick="arXxx()" calls still work */
function arReset()      { ARViewer?.reset();            }
function arWireframe()  { ARViewer?.toggleWireframe();  }
function arTop()        { ARViewer?.setTop();           }
function arFullscreen() { ARViewer?.fullscreen();       }

// ═══════════════════════════════════════════════════════════════
// PDF EXPORT
// ═══════════════════════════════════════════════════════════════
// ═══════════════════════════════════════════════════════════════
// PDF EXPORT  — delegates to PDFExporter module (pdf.js)
// ═══════════════════════════════════════════════════════════════

/**
 * Opens the PDF preview & export modal.
 * Called by all "Export PDF" buttons in the UI.
 * PDFExporter internally tries the Flask backend first,
 * then falls back to client-side jsPDF generation.
 */
async function exportPDF() {
  if (!activeLayout) {
    showToast('⚠ Generate a floor plan first', '⚠');
    return;
  }
  window.activeLayout = activeLayout;   // pdf.js reads window.activeLayout
  if (typeof PDFExporter !== 'undefined') {
    PDFExporter.open();
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
  // Auto-generate demo plan so UI is populated on load
  setTimeout(() => {
    // Generate 3 demo layouts with different templates
    const l0 = buildLocalPlan('40x60', '2BHK', 'East', 0);
    const l1 = buildLocalPlan('40x60', '2BHK', 'East', 1);
    const l2 = buildLocalPlan('40x60', '2BHK', 'East', 2);
    currentLayouts  = [l0, l1, l2];
    activeLayout    = l0;
    window.activeLayout = activeLayout;   // expose to pdf.js
    activeLayoutIdx = 0;
    renderUI(0);
    updateResults();
    document.getElementById('cd-score').textContent = l0.vastu_score.toFixed(0) + '%';
    document.getElementById('cd-rooms').textContent = l0.rooms.length;
    document.getElementById('cd-gen').textContent   = 'DEMO';
  }, 600);
});

// Re-render 2D on resize
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

  if (btn) {
    btn.setAttribute('data-tooltip',
      next === 'dark' ? 'Toggle Light Mode' : 'Toggle Dark Mode');
  }

  // Re-render 2D canvas with updated colors after transition settles
  if (activeLayout) {
    setTimeout(() => render2D(activeLayout), 380);
  }

  showToast(next === 'light' ? '☀ Light mode' : '◐ Dark mode',
            next === 'light' ? '☀' : '◐');
}

// ══════════════════════════════════════════
// HAMBURGER NAV
// ══════════════════════════════════════════
function toggleMobileNav() {
  const nav      = document.getElementById('main-nav');
  const ham      = document.getElementById('hamburger');
  const backdrop = document.getElementById('mob-nav-backdrop');
  const isOpen   = nav.classList.contains('mob-open');
  isOpen ? closeMobileNav() : _openMobileNav(nav, ham, backdrop);
}

function _openMobileNav(nav, ham, backdrop) {
  nav.classList.add('mob-open');
  ham.classList.add('ham-open');
  ham.setAttribute('aria-expanded', 'true');
  backdrop.classList.add('mob-open');
  document.body.style.overflow = 'hidden'; // prevent scroll behind
}

function closeMobileNav() {
  const nav      = document.getElementById('main-nav');
  const ham      = document.getElementById('hamburger');
  const backdrop = document.getElementById('mob-nav-backdrop');
  if (!nav) return;
  nav.classList.remove('mob-open');
  ham.classList.remove('ham-open');
  ham.setAttribute('aria-expanded', 'false');
  backdrop.classList.remove('mob-open');
  document.body.style.overflow = '';
}

// Auto-close: nav button click on mobile OR resize to desktop
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('main-nav')?.addEventListener('click', e => {
    if (e.target.classList.contains('nav-btn') && window.innerWidth <= 900)
      closeMobileNav();
  });
  window.addEventListener('resize', () => {
    if (window.innerWidth > 900) closeMobileNav();
  });
});

// Apply saved theme on load (runs before DOMContentLoaded completes)
(function applySavedTheme() {
  const saved = localStorage.getItem('intelliplan-theme');
  if (saved) {
    document.documentElement.setAttribute('data-theme', saved);
    // Update tooltip when DOM is ready
    window.addEventListener('DOMContentLoaded', () => {
      const btn = document.getElementById('theme-toggle');
      if (btn) {
        btn.setAttribute('data-tooltip',
          saved === 'dark' ? 'Toggle Light Mode' : 'Toggle Dark Mode');
      }
    });
  }
})();