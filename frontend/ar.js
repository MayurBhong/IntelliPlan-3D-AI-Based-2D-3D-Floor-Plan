/* ═══════════════════════════════════════════════════════════════
   IntelliPlan·3D — AR MODULE  (ar.js)
   Immersive 3D Floor Plan Viewer · Three.js r128
═══════════════════════════════════════════════════════════════ */

window.ARViewer = (() => {
  'use strict';

  /* ── Room colour palette
     — balcony and store removed
     — bathroom_master, toilet_master, bathroom_attached, toilet_attached added
  ───────────────────────────────────────────────────────────── */
  const PAL = {
    entrance:            { hex:0xec4899, css:'#ec4899', fill:'rgba(236,72,153,0.5)'  },
    living:              { hex:0x3b82f6, css:'#3b82f6', fill:'rgba(59,130,246,0.5)'  },
    dining:              { hex:0xeab308, css:'#eab308', fill:'rgba(234,179,8,0.5)'   },
    kitchen:             { hex:0xf59e0b, css:'#f59e0b', fill:'rgba(245,158,11,0.5)'  },
    master_bedroom:      { hex:0x8b5cf6, css:'#8b5cf6', fill:'rgba(139,92,246,0.5)'  },
    bedroom:             { hex:0x6366f1, css:'#6366f1', fill:'rgba(99,102,241,0.5)'  },
    bathroom:            { hex:0x14b8a6, css:'#14b8a6', fill:'rgba(20,184,166,0.5)'  },
    toilet:              { hex:0x06b6d4, css:'#06b6d4', fill:'rgba(6,182,212,0.5)'   },
    bathroom_master:     { hex:0x2dd4bf, css:'#2dd4bf', fill:'rgba(45,212,191,0.5)'  },
    toilet_master:       { hex:0x22d3ee, css:'#22d3ee', fill:'rgba(34,211,238,0.5)'  },
    bathroom_attached:   { hex:0x34d399, css:'#34d399', fill:'rgba(52,211,153,0.5)'  },
    toilet_attached:     { hex:0x38bdf8, css:'#38bdf8', fill:'rgba(56,189,248,0.5)'  },
    pooja:               { hex:0xf97316, css:'#f97316', fill:'rgba(249,115,22,0.5)'  },
    utility:             { hex:0x94a3b8, css:'#94a3b8', fill:'rgba(148,163,184,0.5)' },
  };
  const DEF = { hex:0x64748b, css:'#64748b', fill:'rgba(100,116,139,0.5)' };

  /* ── Light presets ─────────────────────────────────────────── */
  const LIGHT_PRESETS = {
    day:   { bg:0x020b18, fogDens:0.006, ambient:[0x334155,0.9],  sun:[0xffffff,1.3],  fill:[0x38bdf8,0.55], warm:[0xc9962a,0.4]  },
    dusk:  { bg:0x100510, fogDens:0.009, ambient:[0x3b1825,0.75], sun:[0xff8855,1.0],  fill:[0xf97316,0.6],  warm:[0xff6633,0.5]  },
    night: { bg:0x010308, fogDens:0.013, ambient:[0x080f20,0.5],  sun:[0x4466bb,0.35], fill:[0x5577ff,0.9],  warm:[0x334488,0.3]  },
  };

  const WALL_H      = 9;
  const CANVAS_H    = 580;
  const SPIN_SPEED  = 0.0025;
  const EXPLODE_MUL = 1.6;
  const ZOOM_MIN    = 18;
  const ZOOM_MAX    = 420;

  let renderer, scene, camera, raycaster, mouse3;
  let animId = null, resizeObs = null;
  let layout = null, plot = null;
  let roomObjs = [];
  let lAmbient, lSun, lFill, lWarm;
  let theta = 0.55, phi = 0.65, radius = 100;
  let panX  = 0,    panZ = 0;
  let isDrag = false, isRightDrag = false;
  let lastX  = 0, lastY = 0;
  let touches = [], lastPinch = 0;
  let autoSpin  = true;
  let wireframe = false;
  let exploded  = false;
  let lightMode = 'day';
  let camMode   = 'orbit';
  let hoveredMesh = null;
  let cvs, wrap;
  let elLabel, elPanel, elMinimap, elCompass, elHelp;

  /* ═══ PUBLIC API ════════════════════════════════════════════ */
  function init(layoutData) {
    layout = layoutData;
    plot   = layout.plot || { width:40, height:60, facing:'East' };
    radius = Math.sqrt(plot.width**2 + plot.height**2) * 1.4;

    cvs  = document.getElementById('ar-canvas');
    wrap = cvs.parentElement;
    wrap.style.position = 'relative';

    _destroy3D();
    _removeOverlays();
    _buildOverlays();
    _initRenderer();
    _initScene();
    _buildFloor();
    _buildRooms();
    _buildLights();
    _buildCompassFloor();
    _initCamera();
    _bindEvents();
    _loop();
    _drawMinimap();
  }

  function destroy() {
    _stopLoop();
    _unbindEvents();
    _destroy3D();
    _removeOverlays();
    if (resizeObs) { resizeObs.disconnect(); resizeObs = null; }
  }

  function reset() {
    theta = 0.55; phi = 0.65;
    radius = Math.sqrt(plot.width**2 + plot.height**2) * 1.4;
    panX = 0; panZ = 0;
    camMode  = 'orbit';
    autoSpin = true;
    _updateCamera();
    _toast('⊹ Camera reset');
  }

  function toggleWireframe() {
    wireframe = !wireframe;
    roomObjs.forEach(o => { o.mesh.material.wireframe = wireframe; });
    _setCtrlActive('ar-btn-wire', wireframe);
    _toast(wireframe ? '⬡ Wireframe on' : '⬡ Wireframe off');
  }

  function toggleExplode() {
    exploded = !exploded;
    const cx = plot.width/2, cz = plot.height/2;
    roomObjs.forEach(o => {
      const bp = o.basePos;
      const tx = exploded ? cx + (bp.x - cx) * EXPLODE_MUL : bp.x;
      const tz = exploded ? cz + (bp.z - cz) * EXPLODE_MUL : bp.z;
      _animateTo(o.mesh,  new THREE.Vector3(tx, bp.y, tz));
      _animateTo(o.edges, new THREE.Vector3(tx, bp.y, tz));
      _animateTo(o.roof,  new THREE.Vector3(tx, WALL_H + 0.02, tz));
    });
    _setCtrlActive('ar-btn-explode', exploded);
    _toast(exploded ? '⊞ Explode on' : '⊞ Rooms collapsed');
  }

  function setTop()   { camMode = 'top';   autoSpin = false; _updateCamera(); _toast('⊡ Top view'); }
  function setIso()   { camMode = 'iso';   autoSpin = false; _updateCamera(); _toast('⬧ Isometric view'); }
  function setOrbit() { camMode = 'orbit'; autoSpin = true;  _updateCamera(); }

  function setLight(mode) {
    lightMode = mode;
    const p = LIGHT_PRESETS[mode] || LIGHT_PRESETS.day;
    scene.background.setHex(p.bg);
    scene.fog = new THREE.FogExp2(p.bg, p.fogDens);
    lAmbient.color.setHex(p.ambient[0]); lAmbient.intensity = p.ambient[1];
    lSun.color.setHex(p.sun[0]);         lSun.intensity     = p.sun[1];
    lFill.color.setHex(p.fill[0]);       lFill.intensity    = p.fill[1];
    lWarm.color.setHex(p.warm[0]);       lWarm.intensity    = p.warm[1];
    const labels = { day:'☀ Day lighting', dusk:'🌅 Dusk lighting', night:'🌙 Night mode' };
    _toast(labels[mode] || 'Lighting changed');
    ['day','dusk','night'].forEach(k => _setCtrlActive('ar-btn-'+k, k === mode));
  }

  function screenshot() {
    renderer.render(scene, camera);
    const a = document.createElement('a');
    a.download = `intelliplan-ar-${Date.now()}.png`;
    a.href     = cvs.toDataURL('image/png');
    a.click();
    _toast('📷 Screenshot saved');
  }

  function fullscreen() {
    if (document.fullscreenElement) document.exitFullscreen();
    else (wrap.requestFullscreen || wrap.webkitRequestFullscreen).call(wrap);
  }

  function closePanel() { elPanel.classList.remove('ar2-panel-visible'); }
  function showHelp()   { elHelp.classList.add('ar2-help-visible');    }
  function closeHelp()  { elHelp.classList.remove('ar2-help-visible'); }

  /* ═══ RENDERER + SCENE ══════════════════════════════════════ */
  function _initRenderer() {
    const w = wrap.clientWidth || 900;
    cvs.width = w; cvs.height = CANVAS_H;
    cvs.style.height = CANVAS_H + 'px';
    renderer = new THREE.WebGLRenderer({ canvas: cvs, antialias: true });
    renderer.setSize(w, CANVAS_H);
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type    = THREE.PCFSoftShadowMap;
    renderer.toneMapping       = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;
  }

  function _initScene() {
    scene  = new THREE.Scene();
    scene.background = new THREE.Color(0x020b18);
    scene.fog = new THREE.FogExp2(0x020b18, 0.006);
    raycaster = new THREE.Raycaster();
    mouse3    = new THREE.Vector2(-10, -10);
  }

  function _initCamera() {
    const w = cvs.clientWidth || 900;
    camera = new THREE.PerspectiveCamera(45, w / CANVAS_H, 0.1, 1200);
    _updateCamera();
  }

  /* ═══ SCENE OBJECTS ════════════════════════════════════════ */
  function _buildFloor() {
    const gGeo  = new THREE.PlaneGeometry(plot.width*3.5, plot.height*3.5);
    const gMesh = new THREE.Mesh(gGeo, new THREE.MeshLambertMaterial({ color:0x020d1f }));
    gMesh.rotation.x = -Math.PI/2;
    gMesh.position.set(plot.width/2, -0.12, plot.height/2);
    gMesh.receiveShadow = true; scene.add(gMesh);

    const grid = new THREE.GridHelper(Math.max(plot.width, plot.height)*3.2, 64, 0x071529, 0x071529);
    grid.position.set(plot.width/2, 0.01, plot.height/2); scene.add(grid);

    const bPts = [
      new THREE.Vector3(0,           0.06, 0),
      new THREE.Vector3(plot.width,  0.06, 0),
      new THREE.Vector3(plot.width,  0.06, plot.height),
      new THREE.Vector3(0,           0.06, plot.height),
      new THREE.Vector3(0,           0.06, 0),
    ];
    scene.add(new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(bPts),
      new THREE.LineBasicMaterial({ color:0x38bdf8, transparent:true, opacity:0.4 })
    ));

    [[0,0],[plot.width,0],[plot.width,plot.height],[0,plot.height]].forEach(([x,z]) => {
      const m = new THREE.Mesh(
        new THREE.CylinderGeometry(0.22, 0.22, 0.7, 6),
        new THREE.MeshLambertMaterial({ color:0xd9aa3f, emissive:0xd9aa3f, emissiveIntensity:0.25 })
      );
      m.position.set(x, 0.35, z); scene.add(m);
    });
  }

  function _buildRooms() {
    roomObjs = [];
    layout.rooms.forEach(r => {
      const pal = PAL[r.type] || DEF;
      const rw  = r.width  || r.w;
      const rh  = r.height || r.h;
      const cx  = r.x + rw/2;
      const cz  = r.y + rh/2;
      const cy  = WALL_H/2;

      const geo  = new THREE.BoxGeometry(rw*0.93, WALL_H, rh*0.93);
      const mat  = new THREE.MeshLambertMaterial({ color:pal.hex, transparent:true, opacity:0.88 });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.set(cx, cy, cz);
      mesh.castShadow = mesh.receiveShadow = true;
      mesh.userData = { room:r, pal };
      scene.add(mesh);

      const edges = new THREE.LineSegments(
        new THREE.EdgesGeometry(geo),
        new THREE.LineBasicMaterial({ color:0xffffff, transparent:true, opacity:0.08 })
      );
      edges.position.copy(mesh.position); scene.add(edges);

      const rGeo = new THREE.PlaneGeometry(rw*0.93, rh*0.93);
      const rMat = new THREE.MeshLambertMaterial({ color:pal.hex, transparent:true, opacity:0.2, side:THREE.DoubleSide });
      const roof = new THREE.Mesh(rGeo, rMat);
      roof.rotation.x = -Math.PI/2;
      roof.position.set(cx, WALL_H+0.03, cz); scene.add(roof);

      roomObjs.push({ mesh, edges, roof, room:r, pal, basePos: new THREE.Vector3(cx, cy, cz) });
    });
  }

  function _buildLights() {
    const p = LIGHT_PRESETS.day;
    lAmbient = new THREE.AmbientLight(p.ambient[0], p.ambient[1]); scene.add(lAmbient);
    lSun = new THREE.DirectionalLight(p.sun[0], p.sun[1]);
    lSun.position.set(plot.width*1.7, plot.height*2.3, plot.height*1.4);
    lSun.castShadow = true;
    lSun.shadow.mapSize.set(2048, 2048);
    lSun.shadow.camera.near = 1; lSun.shadow.camera.far = 600;
    lSun.shadow.camera.left = lSun.shadow.camera.bottom = -120;
    lSun.shadow.camera.right = lSun.shadow.camera.top   =  120;
    scene.add(lSun);
    lFill = new THREE.PointLight(p.fill[0], p.fill[1], 500);
    lFill.position.set(plot.width/2, 60, plot.height/2); scene.add(lFill);
    lWarm = new THREE.PointLight(p.warm[0], p.warm[1], 300);
    lWarm.position.set(plot.width, 35, plot.height); scene.add(lWarm);
    scene.add(new THREE.HemisphereLight(0x0e1e38, 0x030810, 0.45));
  }

  function _buildCompassFloor() {
    const deg = { North:[0,-1], East:[1,0], South:[0,1], West:[-1,0] };
    const R   = Math.max(plot.width, plot.height) * 0.55;
    const cx  = plot.width/2, cz = plot.height/2;
    Object.entries(deg).forEach(([dir, [dx, dz]]) => {
      const pts = [ new THREE.Vector3(cx, 0.08, cz), new THREE.Vector3(cx+dx*R, 0.08, cz+dz*R) ];
      const col = dir === 'North' ? 0xf87171 : 0x38bdf8;
      const op  = dir === 'North' ? 0.55 : 0.18;
      scene.add(new THREE.Line(
        new THREE.BufferGeometry().setFromPoints(pts),
        new THREE.LineBasicMaterial({ color:col, transparent:true, opacity:op })
      ));
    });
  }

  /* ═══ CAMERA ════════════════════════════════════════════════ */
  function _tgt() { return new THREE.Vector3(plot.width/2+panX, 0, plot.height/2+panZ); }

  function _updateCamera() {
    const t = _tgt();
    if (camMode === 'top') {
      camera.position.set(t.x, radius*1.25, t.z);
    } else if (camMode === 'iso') {
      const d = radius*0.72;
      camera.position.set(t.x+d, d*0.9, t.z+d);
    } else {
      camera.position.set(
        t.x + radius * Math.sin(phi) * Math.sin(theta),
        t.y + radius * Math.cos(phi),
        t.z + radius * Math.sin(phi) * Math.cos(theta)
      );
    }
    camera.lookAt(t);
  }

  /* ═══ RENDER LOOP ═══════════════════════════════════════════ */
  function _loop() {
    animId = requestAnimationFrame(_loop);
    if (autoSpin && camMode === 'orbit') { theta += SPIN_SPEED; _updateCamera(); }
    _tickHover();
    renderer.render(scene, camera);
  }

  function _stopLoop() { if (animId) { cancelAnimationFrame(animId); animId = null; } }

  /* ═══ HOVER + PICK ══════════════════════════════════════════ */
  function _tickHover() {
    raycaster.setFromCamera(mouse3, camera);
    const hits = raycaster.intersectObjects(roomObjs.map(o => o.mesh));
    if (hits.length) {
      const obj = hits[0].object;
      if (obj !== hoveredMesh) { if (hoveredMesh) _unhover(hoveredMesh); hoveredMesh = obj; _hover(obj); }
      _positionLabel(obj.userData.room, hits[0].point);
    } else {
      if (hoveredMesh) { _unhover(hoveredMesh); hoveredMesh = null; }
      _hideLabel();
    }
  }

  function _hover(mesh) {
    mesh.material.emissive = mesh.material.emissive || new THREE.Color(0);
    mesh.material.emissiveIntensity = 0.32;
    mesh.material.emissive.setHex(0x223355);
    mesh.scale.set(1, 1.05, 1);
    cvs.style.cursor = 'pointer';
  }

  function _unhover(mesh) {
    mesh.material.emissiveIntensity = 0;
    mesh.scale.set(1, 1, 1);
    cvs.style.cursor = '';
  }

  function _positionLabel(room, point) {
    const proj = point.clone().project(camera);
    const w = cvs.clientWidth, h = cvs.clientHeight;
    const sx = ( proj.x * 0.5 + 0.5) * w;
    const sy = (-proj.y * 0.5 + 0.5) * h;
    elLabel.style.left    = sx + 'px';
    elLabel.style.top     = (sy - 52) + 'px';
    elLabel.style.opacity = '1';
    const pal = PAL[room.type] || DEF;
    elLabel.style.borderColor = pal.css;
    elLabel.querySelector('.arl-name').textContent = room.label;
    const a = room.area || Math.round((room.width||room.w)*(room.height||room.h));
    elLabel.querySelector('.arl-area').textContent = Math.round(a) + ' sqft';
  }

  function _hideLabel() { elLabel.style.opacity = '0'; }

  function _openPanel(mesh) {
    const { room, pal } = mesh.userData;
    const w = (room.width  || room.w  || 0).toFixed(1);
    const h = (room.height || room.h  || 0).toFixed(1);
    const a = Math.round(room.area || parseFloat(w)*parseFloat(h));

    elPanel.querySelector('.arp-dot').style.background  = pal.css;
    elPanel.querySelector('.arp-name').textContent      = room.label;
    elPanel.querySelector('.arp-name').style.color      = pal.css;
    elPanel.querySelector('#arp-w').textContent = w + ' ft';
    elPanel.querySelector('#arp-h').textContent = h + ' ft';
    elPanel.querySelector('#arp-a').textContent = a + ' sqft';
    elPanel.querySelector('#arp-t').textContent = room.type.replace(/_/g,' ');

    const rule = (window.activeLayout?.vastu_rules || [])
      .find(r => r.label.toLowerCase().includes(room.type.split('_')[0].toLowerCase()));
    const ruleEl = elPanel.querySelector('#arp-rule');
    if (rule) {
      const statusMap = { compliant:'✓ Compliant', partial:'~ Partial', violation:'✗ Violation', missing:'— Missing' };
      const colorMap  = { compliant:'#4ade80', partial:'#fbbf24', violation:'#f87171', missing:'#64748b' };
      ruleEl.textContent = statusMap[rule.status] || rule.status;
      ruleEl.style.color = colorMap[rule.status]  || '#94a3b8';
    } else {
      ruleEl.textContent = '— No rule data'; ruleEl.style.color = '#64748b';
    }
    elPanel.classList.add('ar2-panel-visible');
  }

  /* ═══ MINI-MAP ═══════════════════════════════════════════════ */
  function _drawMinimap() {
    if (!elMinimap || !layout) return;
    const ctx = elMinimap.getContext('2d');
    const mw  = elMinimap.width, mh = elMinimap.height;
    const pad = 7;
    const sc  = Math.min((mw-pad*2)/plot.width, (mh-pad*2)/plot.height);

    ctx.clearRect(0, 0, mw, mh);
    ctx.fillStyle = 'rgba(2,11,24,0.9)'; ctx.fillRect(0, 0, mw, mh);
    ctx.strokeStyle = 'rgba(56,189,248,0.5)'; ctx.lineWidth = 0.8;
    ctx.strokeRect(pad, pad, plot.width*sc, plot.height*sc);

    layout.rooms.forEach(r => {
      const pal = PAL[r.type] || DEF;
      const rx  = pad + r.x*sc, ry = pad + r.y*sc;
      const rw  = (r.width||r.w)*sc, rh = (r.height||r.h)*sc;
      ctx.fillStyle   = pal.fill;
      ctx.strokeStyle = pal.css + 'bb';
      ctx.lineWidth   = 0.5;
      ctx.fillRect(rx, ry, rw, rh);
      ctx.strokeRect(rx, ry, rw, rh);
    });

    ctx.fillStyle = 'rgba(56,189,248,0.35)';
    ctx.font      = '5px JetBrains Mono, monospace';
    ctx.fillText('MINIMAP', pad, mh - 3);
  }

  /* ═══ DOM OVERLAYS ══════════════════════════════════════════ */
  function _buildOverlays() {
    elLabel = _div('ar2-label');
    elLabel.innerHTML = `<span class="arl-name"></span><span class="arl-area"></span>`;
    wrap.appendChild(elLabel);

    elPanel = _div('ar2-panel');
    elPanel.innerHTML = `
      <div class="arp-header">
        <span class="arp-dot"></span>
        <span class="arp-name">Room</span>
        <button class="arp-close" onclick="ARViewer.closePanel()">✕</button>
      </div>
      <div class="arp-body">
        <div class="arp-row"><span class="arp-key">Width</span><span class="arp-val" id="arp-w">—</span></div>
        <div class="arp-row"><span class="arp-key">Depth</span><span class="arp-val" id="arp-h">—</span></div>
        <div class="arp-row"><span class="arp-key">Area</span><span class="arp-val" id="arp-a">—</span></div>
        <div class="arp-row"><span class="arp-key">Type</span><span class="arp-val" id="arp-t">—</span></div>
        <div class="arp-row"><span class="arp-key">Vastu</span><span class="arp-val" id="arp-rule">—</span></div>
      </div>`;
    wrap.appendChild(elPanel);

    elMinimap = document.createElement('canvas');
    elMinimap.className = 'ar2-minimap';
    elMinimap.width = 140; elMinimap.height = 140;
    elMinimap.title = 'Floor plan overview';
    wrap.appendChild(elMinimap);

    elCompass = _div('ar2-compass');
    _renderCompass();
    wrap.appendChild(elCompass);

    elHelp = _div('ar2-help');
    elHelp.innerHTML = `
      <div class="arh-title">Keyboard Shortcuts</div>
      <div class="arh-grid">
        <kbd>R</kbd><span>Reset camera</span>
        <kbd>W</kbd><span>Wireframe toggle</span>
        <kbd>E</kbd><span>Explode view</span>
        <kbd>T</kbd><span>Top view</span>
        <kbd>I</kbd><span>Isometric view</span>
        <kbd>O</kbd><span>Orbit view</span>
        <kbd>1</kbd><span>Day lighting</span>
        <kbd>2</kbd><span>Dusk lighting</span>
        <kbd>3</kbd><span>Night mode</span>
        <kbd>S</kbd><span>Screenshot</span>
        <kbd>F</kbd><span>Fullscreen</span>
        <kbd>?</kbd><span>This help</span>
        <kbd>Esc</kbd><span>Close panels</span>
        <kbd>Dbl-click</kbd><span>Room details</span>
      </div>
      <button class="arh-close" onclick="ARViewer.closeHelp()">✕ Close</button>`;
    wrap.appendChild(elHelp);
  }

  function _removeOverlays() {
    [elLabel, elPanel, elMinimap, elCompass, elHelp].forEach(el => el?.remove());
    elLabel = elPanel = elMinimap = elCompass = elHelp = null;
  }

  function _renderCompass() {
    const facing = plot.facing || 'East';
    const rotMap = { North:0, East:90, South:180, West:270 };
    const rot    = rotMap[facing] ?? 0;
    elCompass.innerHTML = `<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
      <circle cx="32" cy="32" r="30" fill="rgba(2,11,24,0.88)" stroke="rgba(56,189,248,0.22)" stroke-width="1"/>
      <text x="32" y="11"  text-anchor="middle" fill="#f87171" font-size="7.5" font-family="JetBrains Mono,monospace" font-weight="700">N</text>
      <text x="55" y="35"  text-anchor="middle" fill="rgba(148,163,184,0.55)" font-size="6.5" font-family="JetBrains Mono,monospace">E</text>
      <text x="32" y="58"  text-anchor="middle" fill="rgba(148,163,184,0.55)" font-size="6.5" font-family="JetBrains Mono,monospace">S</text>
      <text x="9"  y="35"  text-anchor="middle" fill="rgba(148,163,184,0.55)" font-size="6.5" font-family="JetBrains Mono,monospace">W</text>
      <g transform="rotate(${rot} 32 32)">
        <polygon points="32,6 35.5,32 32,37 28.5,32" fill="#f87171" opacity="0.92"/>
        <polygon points="32,58 35.5,32 32,27 28.5,32" fill="rgba(148,163,184,0.32)"/>
      </g>
      <circle cx="32" cy="32" r="3" fill="#d9aa3f"/>
      <text x="32" y="47" text-anchor="middle" fill="#d9aa3f" font-size="5" font-family="JetBrains Mono,monospace" opacity="0.7">${facing.toUpperCase()}</text>
    </svg>`;
  }

  /* ═══ EVENTS ════════════════════════════════════════════════ */
  function _onMD(e) { isDrag = true; isRightDrag = e.button === 2; autoSpin = false; lastX = e.clientX; lastY = e.clientY; }
  function _onMU()  { isDrag = false; }
  function _onMM(e) {
    const r = cvs.getBoundingClientRect();
    mouse3.x = ((e.clientX - r.left) / r.width)  *  2 - 1;
    mouse3.y = ((e.clientY - r.top)  / r.height) * -2 + 1;
    if (!isDrag) return;
    const dx = e.clientX - lastX, dy = e.clientY - lastY;
    lastX = e.clientX; lastY = e.clientY;
    if (isRightDrag) {
      const s = radius * 0.0011;
      panX -= dx * s * Math.cos(theta) + dy * s * Math.sin(theta) * 0.5;
      panZ -= -dx * s * Math.sin(theta) + dy * s * Math.cos(theta) * 0.5;
    } else {
      theta -= dx * 0.007;
      phi    = Math.max(0.05, Math.min(1.45, phi - dy * 0.007));
    }
    _updateCamera();
  }
  function _onWheel(e) {
    radius = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, radius + e.deltaY * 0.11));
    autoSpin = false; if (camMode !== 'orbit') camMode = 'orbit';
    _updateCamera(); e.preventDefault();
  }
  function _onDbl(e) {
    const r = cvs.getBoundingClientRect();
    mouse3.x = ((e.clientX - r.left) / r.width)  *  2 - 1;
    mouse3.y = ((e.clientY - r.top)  / r.height) * -2 + 1;
    raycaster.setFromCamera(mouse3, camera);
    const hits = raycaster.intersectObjects(roomObjs.map(o => o.mesh));
    if (hits.length) _openPanel(hits[0].object);
  }
  function _onCtx(e) { e.preventDefault(); }
  function _onTS(e)  { autoSpin = false; touches = Array.from(e.touches); if (touches.length === 2) lastPinch = _pinchDist(touches); }
  function _onTM(e) {
    e.preventDefault();
    const now = Array.from(e.touches);
    if (now.length === 1 && touches.length === 1) {
      const dx = now[0].clientX - touches[0].clientX;
      const dy = now[0].clientY - touches[0].clientY;
      theta -= dx * 0.011; phi = Math.max(0.05, Math.min(1.45, phi - dy * 0.011));
      _updateCamera();
    } else if (now.length === 2 && touches.length >= 2) {
      const d = _pinchDist(now);
      radius = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, radius + (lastPinch - d) * 0.22));
      lastPinch = d; _updateCamera();
    }
    touches = now;
  }
  function _onTE(e) { touches = Array.from(e.touches); }
  function _onKey(e) {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
    switch (e.key.toLowerCase()) {
      case 'r': reset();            break; case 'w': toggleWireframe(); break;
      case 'e': toggleExplode();    break; case 't': setTop();          break;
      case 'i': setIso();           break; case 'o': setOrbit();        break;
      case '1': setLight('day');    break; case '2': setLight('dusk');   break;
      case '3': setLight('night');  break; case 's': screenshot();      break;
      case 'f': fullscreen();       break; case '?': showHelp();        break;
      case 'escape': closeHelp(); closePanel(); break;
    }
  }

  function _bindEvents() {
    cvs.addEventListener('mousedown',   _onMD);
    cvs.addEventListener('dblclick',    _onDbl);
    cvs.addEventListener('contextmenu', _onCtx);
    cvs.addEventListener('wheel',       _onWheel, { passive:false });
    cvs.addEventListener('touchstart',  _onTS, { passive:false });
    cvs.addEventListener('touchmove',   _onTM, { passive:false });
    cvs.addEventListener('touchend',    _onTE);
    window.addEventListener('mouseup',   _onMU);
    window.addEventListener('mousemove', _onMM);
    window.addEventListener('keydown',   _onKey);

    resizeObs = new ResizeObserver(() => {
      const w = wrap.clientWidth || 900;
      renderer.setSize(w, CANVAS_H);
      camera.aspect = w / CANVAS_H;
      camera.updateProjectionMatrix();
    });
    resizeObs.observe(wrap);
  }

  function _unbindEvents() {
    cvs?.removeEventListener('mousedown',   _onMD);
    cvs?.removeEventListener('dblclick',    _onDbl);
    cvs?.removeEventListener('contextmenu', _onCtx);
    cvs?.removeEventListener('wheel',       _onWheel);
    cvs?.removeEventListener('touchstart',  _onTS);
    cvs?.removeEventListener('touchmove',   _onTM);
    cvs?.removeEventListener('touchend',    _onTE);
    window.removeEventListener('mouseup',   _onMU);
    window.removeEventListener('mousemove', _onMM);
    window.removeEventListener('keydown',   _onKey);
  }

  /* ═══ HELPERS ═══════════════════════════════════════════════ */
  function _animateTo(obj, target) {
    if (!obj) return;
    const from = obj.position.clone();
    const t0 = performance.now(), dur = 480;
    (function step(now) {
      const p  = Math.min((now - t0) / dur, 1);
      const ep = p < 0.5 ? 2*p*p : -1+(4-2*p)*p;
      obj.position.lerpVectors(from, target, ep);
      if (p < 1) requestAnimationFrame(step);
    })(performance.now());
  }

  function _setCtrlActive(id, on) {
    const el = document.getElementById(id);
    if (el) el.classList.toggle('ar-ctrl-active', on);
  }

  function _pinchDist(ts) {
    const dx = ts[0].clientX - ts[1].clientX;
    const dy = ts[0].clientY - ts[1].clientY;
    return Math.sqrt(dx*dx + dy*dy);
  }

  function _div(cls) { const d = document.createElement('div'); d.className = cls; return d; }
  function _toast(msg) { if (typeof showToast === 'function') showToast(msg, '🔮'); }

  function _destroy3D() {
    _stopLoop(); 
    if (renderer) { renderer.dispose(); renderer = null; }
    scene = camera = raycaster = null; roomObjs = [];
  }

  return {
    init, destroy,
    reset, toggleWireframe, toggleExplode,
    setTop, setIso, setOrbit,
    setLight, screenshot, fullscreen,
    closePanel, showHelp, closeHelp,
  };
})();