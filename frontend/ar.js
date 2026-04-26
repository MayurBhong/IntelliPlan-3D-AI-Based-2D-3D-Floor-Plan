/* ═══════════════════════════════════════════════════════════════
   IntelliPlan·3D  —  AR Viewer  v5  "Premium Architectural"
   Three.js r128 · physically-correct · ACESFilmic · sRGB

   Public API  ──────────────────────────────────────────────────
     ARViewer.init(layout)           build scene from layout obj
     ARViewer.destroy()              full cleanup
     ARViewer.reset()                reset camera
     ARViewer.toggleWireframe()
     ARViewer.toggleExplode()
     ARViewer.setTop() / setIso() / setOrbit()
     ARViewer.setLight('day'|'dusk'|'night')
     ARViewer.screenshot() / fullscreen()
     ARViewer.closePanel() / showHelp() / closeHelp()
═══════════════════════════════════════════════════════════════ */
window.ARViewer = (() => {
  'use strict';

  /* ───────────────────────────────────────────────────────────
     PALETTE  — room floor tones (must stay darker than walls)
     wall tones are generated per-room in mWall() with slight
     variation.  css / fill used by minimap only.
  ─────────────────────────────────────────────────────────────*/
  const PAL = {
    //  floor = rich wood/tile tone,  wallTint = off-white per room, border = dark inner edge
    entrance:       { floor:0x9e8c78, wallTint:0xf3f0eb, border:0x6e5c48, css:'#ec4899', fill:'rgba(236,72,153,.4)'  },
    living:         { floor:0xa09070, wallTint:0xf2efea, border:0x705030, css:'#3b82f6', fill:'rgba(59,130,246,.4)'  },
    dining:         { floor:0x988060, wallTint:0xf2efea, border:0x684828, css:'#eab308', fill:'rgba(234,179,8,.4)'   },
    kitchen:        { floor:0xb0a888, wallTint:0xf3f1ec, border:0x807868, css:'#f59e0b', fill:'rgba(245,158,11,.4)'  },
    master_bedroom: { floor:0xb09880, wallTint:0xf5f2ef, border:0x806848, css:'#8b5cf6', fill:'rgba(139,92,246,.4)'  },
    bedroom:        { floor:0xa89880, wallTint:0xf4f2ef, border:0x786050, css:'#6366f1', fill:'rgba(99,102,241,.4)'  },
    bathroom:       { floor:0x80a8a5, wallTint:0xf1f5f4, border:0x507875, css:'#14b8a6', fill:'rgba(20,184,166,.4)'  },
    toilet:         { floor:0x78a0b0, wallTint:0xf0f4f6, border:0x487080, css:'#06b6d4', fill:'rgba(6,182,212,.4)'   },
    balcony:        { floor:0x88a878, wallTint:0xf2f5f2, border:0x587848, css:'#22c55e', fill:'rgba(34,197,94,.4)'   },
    utility:        { floor:0x9098a8, wallTint:0xf2f2f4, border:0x606878, css:'#94a3b8', fill:'rgba(148,163,184,.4)' },
    store:          { floor:0x988c80, wallTint:0xf2f1ef, border:0x685c50, css:'#78716c', fill:'rgba(120,113,108,.4)' },
  };
  const DP = { floor:0x989080, wallTint:0xf2f2f2, border:0x686058, css:'#64748b', fill:'rgba(100,116,139,.4)' };

  /* ───────────────────────────────────────────────────────────
     LIGHT PRESETS
  ─────────────────────────────────────────────────────────────*/
  const LP = {
    day:{
      bg:0xe6e1d8, fog:0.0012,
      amb:{ col:0xfff4e6, int:0.22 },
      sun:{ col:0xffd9b3, int:0.90 },
      fill:{ col:0xc8dcf0, int:0.18 },
      hemi:{ sky:0xfff5e0, gnd:0xb8aa90, int:0.30 },
      ri:0.70,
    },
    dusk:{
      bg:0x1a0d0a, fog:0.009,
      amb:{ col:0x3d180e, int:0.35 },
      sun:{ col:0xff5500, int:0.95 },
      fill:{ col:0xf97316, int:0.45 },
      hemi:{ sky:0x280c06, gnd:0x070204, int:0.28 },
      ri:1.40,
    },
    night:{
      bg:0x020408, fog:0.016,
      amb:{ col:0x08101e, int:0.18 },
      sun:{ col:0x2244bb, int:0.30 },
      fill:{ col:0x3355dd, int:0.55 },
      hemi:{ sky:0x081018, gnd:0x010206, int:0.22 },
      ri:1.80,
    },
  };

  /* ───────────────────────────────────────────────────────────
     CONSTANTS
  ─────────────────────────────────────────────────────────────*/
  const WH   = 9.0;   // wall height ft
  const WH_CUT = 3.8; // interior partition visible height (cut-section)
  const WT   = 0.28;  // interior wall thickness
  const XT   = 0.42;  // exterior shell thickness
  const FT   = 0.10;  // floor slab
  const CT   = 0.08;  // ceiling slab
  const SK   = 0.055; // skirting height
  const SKD  = 0.035; // skirting depth
  const PAD  = 1.6;   // platform overhang
  const ZMIN = 12, ZMAX = 520, CANVAS_H = 580;
  const SPIN = 0.0014, EXPL = 1.65;

  /* ───────────────────────────────────────────────────────────
     STATE
  ─────────────────────────────────────────────────────────────*/
  let renderer, scene, camera, raycaster, mouse3;
  let animId = null, resObs = null;
  let layout = null, plot = null;
  let roomGrps = [], pick = [];
  let lAmb, lSun, lFill, lHemi, roomLights = [];
  let theta=0.52, phi=0.28, radius=130, panX=0, panZ=0;
  let drag=false, rDrag=false, lx=0, ly=0, tch=[], lpin=0;
  let autoSpin=true, wire=false, expl=false, lmode='day', cmode='orbit';
  let hov=null;
  let elLabel, elPanel, elMap, elCmp, elHelp, cvs, wrap;

  /* ═══════════════════════════════════════════════════════════
     PUBLIC API
  ═══════════════════════════════════════════════════════════ */
  function init(data){
    layout=data; plot=data.plot||{width:40,height:60,facing:'North'};
    radius=Math.sqrt(plot.width**2+plot.height**2)*1.52;
    cvs=document.getElementById('ar-canvas');
    wrap=cvs.parentElement; wrap.style.position='relative';
    _kill(); _rmOv();
    _mkOv(); _mkRend(); _mkScene();
    _mkGround(); _mkRooms(); _mkShell(); _mkLights();
    _mkCam(); _bind(); _loop(); _drawMap();
  }
  function destroy(){ _stop();_unbind();_kill();_rmOv();if(resObs){resObs.disconnect();resObs=null;} }
  function reset(){ theta=0.52;phi=0.28;radius=Math.sqrt(plot.width**2+plot.height**2)*1.52;panX=panZ=0;cmode='orbit';autoSpin=true;_cam();_toast('Camera reset'); }

  function toggleWireframe(){
    wire=!wire;
    pick.forEach(m=>{if(m.material)m.material.wireframe=wire;});
    _act('ar-btn-wire',wire); _toast(wire?'Wireframe ON':'OFF');
  }
  function toggleExplode(){
    expl=!expl;
    const cx=plot.width/2, cz=plot.height/2;
    roomGrps.forEach(g=>{
      const dx=(g.cx-cx)*(expl?EXPL-1:0), dz=(g.cz-cz)*(expl?EXPL-1:0);
      [...g.walls,g.flr,g.ceil,...g.furn].filter(Boolean).forEach(m=>{
        const bp=m.userData.bp; if(!bp)return;
        _anim(m,new THREE.Vector3(bp.x+dx,bp.y,bp.z+dz));
      });
    });
    _act('ar-btn-explode',expl); _toast(expl?'Explode ON':'Collapsed');
  }
  function setTop(){cmode='top';autoSpin=false;_cam();_toast('Top view');}
  function setIso(){cmode='iso';autoSpin=false;_cam();_toast('Isometric');}
  function setOrbit(){cmode='orbit';autoSpin=true;_cam();}
  function setLight(m){
    lmode=m; const L=LP[m]||LP.day;
    scene.background.setHex(L.bg);
    scene.fog=new THREE.FogExp2(L.bg,L.fog);
    lAmb.color.setHex(L.amb.col);   lAmb.intensity=L.amb.int;
    lSun.color.setHex(L.sun.col);   lSun.intensity=L.sun.int;
    lFill.color.setHex(L.fill.col); lFill.intensity=L.fill.int;
    lHemi.color.setHex(L.hemi.sky); lHemi.groundColor.setHex(L.hemi.gnd);
    lHemi.intensity=L.hemi.int;
    roomLights.forEach(l=>l.intensity=L.ri);
    ['day','dusk','night'].forEach(k=>_act('ar-btn-'+k,k===m));
    _toast({day:'☀ Day',dusk:'🌅 Dusk',night:'🌙 Night'}[m]);
  }
  function screenshot(){ renderer.render(scene,camera);const a=document.createElement('a');a.download=`intelliplan-${Date.now()}.png`;a.href=cvs.toDataURL();a.click();_toast('Screenshot saved'); }
  function fullscreen(){ document.fullscreenElement?document.exitFullscreen():(wrap.requestFullscreen||wrap.webkitRequestFullscreen).call(wrap); }
  function closePanel(){ elPanel.classList.remove('ar2-panel-visible'); }
  function showHelp(){ elHelp.classList.add('ar2-help-visible'); }
  function closeHelp(){ elHelp.classList.remove('ar2-help-visible'); }

  /* ═══════════════════════════════════════════════════════════
     RENDERER  — physically correct, ACESFilmic, sRGB
  ═══════════════════════════════════════════════════════════ */
  function _mkRend(){
    const w=wrap.clientWidth||900;
    cvs.width=w; cvs.height=CANVAS_H; cvs.style.height=CANVAS_H+'px';
    renderer=new THREE.WebGLRenderer({canvas:cvs,antialias:true,powerPreference:'high-performance'});
    renderer.setSize(w,CANVAS_H);
    renderer.setPixelRatio(Math.min(devicePixelRatio,2));
    renderer.physicallyCorrectLights = true;
    renderer.outputEncoding          = THREE.sRGBEncoding;
    renderer.shadowMap.enabled       = true;
    renderer.shadowMap.type          = THREE.PCFSoftShadowMap;
    renderer.toneMapping             = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure     = 0.62;   // low — prevents washout on bright interiors
  }

  /* ═══════════════════════════════════════════════════════════
     SCENE + CAMERA
  ═══════════════════════════════════════════════════════════ */
  function _mkScene(){
    const L=LP.day;
    scene=new THREE.Scene();
    scene.background=new THREE.Color(L.bg);
    scene.fog=new THREE.FogExp2(L.bg,L.fog);
    raycaster=new THREE.Raycaster();
    mouse3=new THREE.Vector2(-9,-9);
  }
  function _mkCam(){
    camera=new THREE.PerspectiveCamera(35,(cvs.clientWidth||900)/CANVAS_H,0.1,1500);
    _cam();
  }
  function _tgt(){ return new THREE.Vector3(plot.width/2+panX,0,plot.height/2+panZ); }
  function _cam(){
    const t=_tgt();
    if(cmode==='top'){
      camera.position.set(t.x,radius*1.4,t.z);
    } else if(cmode==='iso'){
      // near-top-down iso — full interior visible
      camera.position.set(t.x+plot.width*0.55, plot.height*1.80, t.z+plot.height*0.55);
    } else {
      camera.position.set(
        t.x+radius*Math.sin(phi)*Math.sin(theta),
        t.y+radius*Math.cos(phi),
        t.z+radius*Math.sin(phi)*Math.cos(theta)
      );
    }
    camera.lookAt(t);
  }

  /* ═══════════════════════════════════════════════════════════
     MATERIALS  — all MeshStandardMaterial
     Contrast law:  wall lightness > floor lightness always.
  ═══════════════════════════════════════════════════════════ */
  // Off-white wall — roughness 0.88, NO metalness
  function mWall(hex){ return new THREE.MeshStandardMaterial({color:hex||0xf2f0ec,roughness:0.88,metalness:0.0}); }
  // Floor — visibly darker, wood-tile range, slight sheen
  function mFloor(hex){ return new THREE.MeshStandardMaterial({color:hex||0xb0a898,roughness:0.70,metalness:0.02}); }
  // Furniture base
  function mFurn(hex,r,m){ return new THREE.MeshStandardMaterial({color:hex,roughness:r??0.78,metalness:m??0.0}); }
  // Fabric — maximum roughness
  function mFab(hex){ return new THREE.MeshStandardMaterial({color:hex,roughness:0.96,metalness:0.0}); }
  // Solid wood — mid roughness
  function mWood(hex){ return new THREE.MeshStandardMaterial({color:hex||0x8a6a48,roughness:0.62,metalness:0.01}); }
  // Polished metal
  function mMetal(hex){ return new THREE.MeshStandardMaterial({color:hex||0xaaaaaa,roughness:0.30,metalness:0.80}); }
  // Glass — low roughness, low opacity
  function mGlass(hex,op){ return new THREE.MeshStandardMaterial({color:hex||0x88bbcc,roughness:0.04,metalness:0.06,transparent:true,opacity:op||0.26}); }
  // Ceiling — near-invisible so interior shows
  function mCeil(){ return new THREE.MeshStandardMaterial({color:0xf4f2ef,roughness:0.92,metalness:0,transparent:true,opacity:0.12}); }

  /* ═══════════════════════════════════════════════════════════
     GROUND PLATFORM  — wooden base (miniature feel)
  ═══════════════════════════════════════════════════════════ */
  function _mkGround(){
    const pw=plot.width, ph=plot.height;
    const sw=pw+PAD*2, sh=ph+PAD*2;

    // Wooden ground plane
    const gnd=_mesh(new THREE.PlaneGeometry(sw*5,sh*5), mFloor(0xc2b8a3));
    gnd.rotation.x=-Math.PI/2; gnd.position.set(pw/2,-0.24,ph/2);
    gnd.receiveShadow=true; scene.add(gnd);

    // Two-layer base platform
    _addM(new THREE.BoxGeometry(sw,0.30,sh),      mFloor(0xd5cdc0), pw/2,-0.10,ph/2, 1,1);
    _addM(new THREE.BoxGeometry(sw+0.14,0.10,sh+0.14), mFloor(0xc5bdb0), pw/2,-0.18,ph/2, 1,1);

    // Building footprint (inner polished slab)
    _addM(new THREE.BoxGeometry(pw,FT,ph), mFloor(0xd8d2c8), pw/2,FT/2,ph/2, 0,1);
  }

  /* ═══════════════════════════════════════════════════════════
     ROOMS  — floor, ceiling, partition walls, skirting
  ═══════════════════════════════════════════════════════════ */
  function _mkRooms(){
    roomGrps=[]; pick=[];
    layout.rooms.forEach(r=>{
      const pal=PAL[r.type]||DP;
      const rw=r.width||r.w, rh=r.height||r.h;
      const rx=r.x, rz=r.y, cx=rx+rw/2, cz=rz+rh/2;
      const walls=[], furn=[];

      // Floor slab — darkened by pal.floor
      const flr=_mesh(
        new THREE.BoxGeometry(rw-WT*0.5,FT,rh-WT*0.5),
        mFloor(pal.floor)
      );
      flr.position.set(cx,FT*1.2,cz);
      flr.receiveShadow=true;
      flr.userData={room:r,pal,bp:flr.position.clone()};
      scene.add(flr); pick.push(flr);

      // Ceiling — omitted: cut-section view, interior must stay open
      const ceil=null; // no ceiling slab

      // Skirting boards (where wall meets floor — adds realism)
      const ysk=FT*2+SK/2;
      [
        [cx,      ysk, cz-rh/2, rw-WT*2, SKD,'H'],
        [cx,      ysk, cz+rh/2, rw-WT*2, SKD,'H'],
        [cx-rw/2, ysk, cz,      SKD, rh-WT*2,'V'],
        [cx+rw/2, ysk, cz,      SKD, rh-WT*2,'V'],
      ].forEach(([x,y,z,w2,d2,ax])=>{
        const sg=ax==='H'
          ? new THREE.BoxGeometry(w2,SK,SKD)
          : new THREE.BoxGeometry(SKD,SK,d2);
        const sm=_mesh(sg, mWall(0xe6e0d8));
        sm.position.set(x,y,z); scene.add(sm);
      });

      // 4 interior partition walls — cut height so interior visible
      [
        {ox:0,    oz:-rh/2, ww:rw,  wd:WT},
        {ox:0,    oz: rh/2, ww:rw,  wd:WT},
        {ox:-rw/2,oz:0,     ww:WT,  wd:rh},
        {ox: rw/2,oz:0,     ww:WT,  wd:rh},
      ].forEach(d=>{
        const wm=_mesh(
          new THREE.BoxGeometry(d.ww,WH_CUT,d.wd),
          mWall(pal.wallTint)
        );
        wm.position.set(cx+d.ox, WH_CUT/2+FT*2, cz+d.oz);
        wm.castShadow=wm.receiveShadow=true;
        wm.userData={room:r,pal,bp:wm.position.clone()};
        scene.add(wm); pick.push(wm); walls.push(wm);
      });

      // Dark inner border strip — defines room edge clearly
      const bT=0.06, bH2=FT*0.8;
      const bCol=pal.border||0x605040;
      [
        [cx,      FT*1.5+bH2/2, cz-rh/2+bT/2,  rw,   bH2, bT],
        [cx,      FT*1.5+bH2/2, cz+rh/2-bT/2,  rw,   bH2, bT],
        [cx-rw/2+bT/2, FT*1.5+bH2/2, cz, bT, bH2, rh],
        [cx+rw/2-bT/2, FT*1.5+bH2/2, cz, bT, bH2, rh],
      ].forEach(([x,y,z,w2,h2,d2])=>{
        const bm=_mesh(new THREE.BoxGeometry(w2,h2,d2),
          new THREE.MeshStandardMaterial({color:bCol,roughness:0.85,metalness:0}));
        bm.position.set(x,y,z); bm.receiveShadow=true; scene.add(bm);
      });

      _mkFurn(r,rw,rh,cx,cz,furn);
      roomGrps.push({walls,flr,ceil,furn,room:r,pal,cx,cz});
    });
  }

  /* ═══════════════════════════════════════════════════════════
     OUTER SHELL  — exterior walls, parapet, corner posts, glass
  ═══════════════════════════════════════════════════════════ */
  function _mkShell(){
    const pw=plot.width, ph=plot.height, H=WH+FT*2;

    // Exterior walls — cut to WH_CUT+1 so interior visible from iso angle
    const SH=WH_CUT+1.0;
    [
      [pw/2,   SH/2+FT, -XT/2,   pw+XT*2, SH, XT],
      [pw/2,   SH/2+FT, ph+XT/2, pw+XT*2, SH, XT],
      [-XT/2,  SH/2+FT, ph/2,    XT,      SH, ph],
      [pw+XT/2,SH/2+FT, ph/2,    XT,      SH, ph],
    ].forEach(([x,y,z,w,h,d])=>{
      const m=_mesh(new THREE.BoxGeometry(w,h,d), mWall(0xeeeae4));
      m.position.set(x,y,z); m.castShadow=m.receiveShadow=true; scene.add(m);
    });

    // Parapet cap on cut shell
    const PC=0.28;
    [
      [pw/2,   SH+FT+PC/2, -XT/2,   pw+XT*2+0.1, PC, XT+0.1],
      [pw/2,   SH+FT+PC/2, ph+XT/2, pw+XT*2+0.1, PC, XT+0.1],
      [-XT/2,  SH+FT+PC/2, ph/2,    XT+0.1,      PC, ph],
      [pw+XT/2,SH+FT+PC/2, ph/2,    XT+0.1,      PC, ph],
    ].forEach(([x,y,z,w,h,d])=>{
      const m=_mesh(new THREE.BoxGeometry(w,h,d), mWall(0xdedad2));
      m.position.set(x,y,z); m.castShadow=true; scene.add(m);
    });

    // Corner posts at cut height
    [[0,0],[pw,0],[pw,ph],[0,ph]].forEach(([x,z])=>{
      const m=_mesh(new THREE.BoxGeometry(XT*1.6,SH+PC,XT*1.6), mWall(0xe5e1d8));
      m.position.set(x,(SH+PC)/2+FT,z); m.castShadow=true; scene.add(m);
    });

    // Glass window strips on south wall — adds transparent depth
    const gM=mGlass(0x90c0d4,0.20);
    for(let x=XT+0.5;x<pw-XT-0.5;x+=4.2){
      const gp=_mesh(new THREE.BoxGeometry(2.0,WH*0.52,0.06),gM);
      gp.position.set(x+1.0,WH*0.38+FT*2,-XT*0.5);
      scene.add(gp);
    }

    // Balcony railing — glass panel on east wall
    const bH=1.1, bM=mGlass(0xaaccdd,0.30);
    for(let z=1;z<ph-1;z+=3.0){
      const bp=_mesh(new THREE.BoxGeometry(0.06,bH,2.4),bM);
      bp.position.set(pw+XT*0.5,FT*2+bH/2,z+1.2);
      scene.add(bp);
    }
  }

  /* ═══════════════════════════════════════════════════════════
     FURNITURE  — layered, distinct colors, realistic shapes
     Color philosophy:
       sofa/armchair   → warm tan/terracotta family
       tables          → dark wood browns
       beds            → cream/linen with darker frame
       kitchen         → warm grey-white with oak
       metal           → brushed brass/chrome
     All castShadow=true, all receiveShadow where horizontal
  ═══════════════════════════════════════════════════════════ */
  function _mkFurn(r,rw,rh,cx,cz,lst){
    const rx=r.x, rz=r.y;
    const Y=FT*2+0.08;
    const MP=0.55; // minimum padding from wall (ft)

    // ── bounding-box registry — prevents overlap ─────────────
    const placed=[];
    function fits(x,z,w,d){
      const x0=x-w/2, x1=x+w/2, z0=z-d/2, z1=z+d/2;
      // room boundary check (with wall padding)
      if(x0 < rx+MP || x1 > rx+rw-MP) return false;
      if(z0 < rz+MP || z1 > rz+rh-MP) return false;
      // overlap check against placed items
      for(const p of placed){
        const gap=0.08;
        if(x0 < p.x1+gap && x1 > p.x0-gap && z0 < p.z1+gap && z1 > p.z0-gap) return false;
      }
      return true;
    }
    function reg(x,z,w,d){ placed.push({x0:x-w/2,x1:x+w/2,z0:z-d/2,z1:z+d/2}); }

    // ── safe mesh builders — only place if fits ───────────────
    function box(mat,x,y,z,w,h,d,cast,recv){
      if(!fits(x,z,w,d)) return null;
      reg(x,z,w,d);
      const m=_mesh(new THREE.BoxGeometry(w,h,d),mat);
      m.position.set(x,y,z);
      if(cast!==false) m.castShadow=true;
      if(recv) m.receiveShadow=true;
      m.userData={room:r,pal:PAL[r.type]||DP,bp:m.position.clone()};
      scene.add(m); pick.push(m); lst.push(m); return m;
    }
    // force-place: skip bounds check (used for stacked layers on already-registered base)
    function fbox(mat,x,y,z,w,h,d,cast,recv){
      const m=_mesh(new THREE.BoxGeometry(w,h,d),mat);
      m.position.set(x,y,z);
      if(cast!==false) m.castShadow=true;
      if(recv) m.receiveShadow=true;
      m.userData={room:r,pal:PAL[r.type]||DP,bp:m.position.clone()};
      scene.add(m); pick.push(m); lst.push(m); return m;
    }
    function cyl(mat,x,y,z,rt,rb,h,seg){
      const m=_mesh(new THREE.CylinderGeometry(rt,rb,h,seg||10),mat);
      m.position.set(x,y,z); m.castShadow=true;
      m.userData={room:r,pal:PAL[r.type]||DP,bp:m.position.clone()};
      scene.add(m); lst.push(m); return m;
    }
    function cushion(c,x,y,z,w,d){ fbox(mFab(c),x,y,z,w,0.10,d); }

    // ── dynamic scale helpers ─────────────────────────────────
    // clamp fraction so object never exceeds usable room dimension
    function fw(f){ return Math.min(rw*f, rw-MP*2-0.1); }
    function fh(f){ return Math.min(rh*f, rh-MP*2-0.1); }

    switch(r.type){

    case 'living':{
      // sofa — pushed to back wall, safe padding
      const sw=fw(0.50), sd=fh(0.18);
      const sy=rz+rh-MP-sd/2;
      if(box(mFab(0xc4aa88), cx-fw(0.06), Y+.22, sy, sw, .44, sd)){
        fbox(mFab(0xa08860), cx-fw(0.06), Y+.64, sy, sw, .12, sd*.35);
        cushion(0xe0cba8, cx-fw(0.18), Y+.48, sy, fw(0.14), sd*.85);
        cushion(0xe0cba8, cx-fw(0.03), Y+.48, sy, fw(0.14), sd*.85);
        cushion(0xe0cba8, cx+fw(0.11), Y+.48, sy, fw(0.10), sd*.85);
        fbox(mFab(0x887060), cx-fw(0.25), Y+.62, sy, .30, .26, .08);
      }
      // chaise arm
      const csw=fw(0.14), csy=rz+rh-MP-sd/2;
      box(mFab(0xc4aa88), cx+fw(0.22), Y+.22, csy, csw, .44, sd);

      // coffee table — center of room, clear of sofa
      const tw=fw(0.28), td=fh(0.15), tZ=rz+rh*0.48;
      if(box(mWood(0x5c3a1a), cx, Y+.36, tZ, tw, .06, td, true,true)){
        fbox(mWood(0x4a2c12), cx, Y+.18, tZ, tw*.85, .30, td*.7);
        fbox(mMetal(0xb0945a), cx, Y+.40, tZ, tw*.45, .03, td*.55);
      }

      // TV unit on front wall
      const tvw=fw(0.55);
      if(box(mWood(0x3a2810), cx, Y+.28, rz+MP+.17, tvw, .56, .34)){
        fbox(mFurn(0x0e0e12,.15,.6), cx, Y+1.05, rz+MP+.02, tvw*.75, .62, .04);
        fbox(mMetal(0x808078), cx, Y+.56, rz+MP+.28, tvw*.28, .03, .06);
      }

      // rug
      fbox(mFab(0xddd0b8), cx, Y+.01, rz+rh*.52, fw(0.50), .03, fh(0.32), false,true);

      // side table + lamp — only if room wide enough
      const stX=rx+rw-MP-.25, stZ=rz+rh*0.55;
      if(box(mWood(0x8a6840), stX, Y+.44, stZ, .46, .44, .46)){
        cyl(mMetal(0xc8b470), stX, Y+.96, stZ, .04,.034,.50,8);
        cyl(mFab(0xf8f0d4),   stX, Y+1.26, stZ, .15,.12,.18,12);
      }

      // plant — corner
      const pX=rx+MP+.22, pZ=rz+MP+.22;
      if(fits(pX,pZ,.50,.50)){
        reg(pX,pZ,.50,.50);
        cyl(mWood(0x7a4e28), pX, Y+.30, pZ, .13,.17,.34,8);
        cyl(mFurn(0x285018,.88), pX, Y+.70, pZ, .24,.18,.65,10);
      }
      break;
    }

    case 'master_bedroom':{
      // bed — centered width, back-wall aligned
      const bw=fw(0.60), bd=fh(0.52);
      const bz=rz+rh-MP-bd/2;
      if(box(mWood(0x5a3818), cx, Y+.10, bz, bw, .20, bd)){
        fbox(mFab(0xd8c8a8),  cx, Y+.38, bz, bw*.90, .28, bd*.90);
        fbox(mFab(0xece0cc),  cx, Y+.50, bz, bw*.84, .18, bd*.80);
        fbox(mFab(0x806048),  cx, Y+.84, rz+rh-MP-.12, bw*.94, .62, .20);
        fbox(mFab(0x9a7860),  cx, Y+.90, rz+rh-MP-.12, bw*.84, .52, .14);
        // pillows
        const pw2=bw*.13, ph2=bw*.13;
        fbox(mFab(0xf6eee0), cx-bw*.18, Y+.70, rz+rh-MP-bd*.22, pw2, .22, ph2);
        fbox(mFab(0xf0e8d8), cx-bw*.03, Y+.70, rz+rh-MP-bd*.22, pw2, .22, ph2);
        fbox(mFab(0xf6eee0), cx+bw*.03, Y+.70, rz+rh-MP-bd*.22, pw2*.9, .22, ph2);
        fbox(mFab(0xf0e8d8), cx+bw*.16, Y+.70, rz+rh-MP-bd*.22, pw2*.9, .22, ph2);
      }

      // wardrobe — side wall
      const wdW=Math.min(rw*.18,2.2), wdD=Math.min(rh*.35,2.0);
      const wdX=rx+rw-MP-wdW/2, wdZ=rz+MP+wdD/2;
      if(box(mWood(0xcec6b4), wdX, Y+1.30, wdZ, wdW, 2.55, wdD)){
        fbox(mWood(0xbeb6a4),  wdX, Y+1.30, wdZ, wdW+.04, 2.57, .04);
        fbox(mMetal(0xb0a890), wdX+wdW*.5, Y+1.26, wdZ, .03,1.20,.06);
      }

      // bedside tables — dynamically placed beside bed
      const btW=Math.min(rw*.11,1.0), btD=Math.min(rh*.12,0.9);
      const btZ=bz;
      [-bw/2-btW/2-0.15, bw/2+btW/2+0.15].forEach(ox=>{
        const btX=cx+ox;
        if(fits(btX,btZ,btW,btD) && btX-btW/2>rx+MP && btX+btW/2<rx+rw-MP){
          reg(btX,btZ,btW,btD);
          fbox(mWood(0x9a7a58), btX, Y+.46, btZ, btW, .46, btD);
          cyl(mMetal(0xd0c06e), btX, Y+1.00, btZ, .04,.034,.38,8);
          cyl(mFab(0xfaf6e6),   btX, Y+1.28, btZ, .14,.11,.18,12);
        }
      });

      // artwork on wall — skip bounds (wall-mounted, no floor collision)
      fbox(mFurn(0x4a6880,.9), cx-fw(0.12), Y+2.25, rz+.05, fw(0.30), .50, .03);
      fbox(mWood(0x826a50),    cx-fw(0.12), Y+2.25, rz+.06, fw(0.32), .52, .02);
      break;
    }

    case 'bedroom':{
      const bw=fw(0.56), bd=fh(0.50);
      const bz=rz+rh-MP-bd/2;
      if(box(mWood(0x5a3818), cx, Y+.10, bz, bw, .18, bd)){
        fbox(mFab(0xd8c8a8), cx, Y+.35, bz, bw*.88, .26, bd*.88);
        fbox(mFab(0xece0cc), cx, Y+.46, bz, bw*.82, .17, bd*.80);
        fbox(mFab(0x806048), cx, Y+.80, rz+rh-MP-.10, bw*.90, .52, .18);
        fbox(mFab(0xf6eee0), cx-bw*.16, Y+.68, rz+rh-MP-bd*.22, bw*.12, .20, bw*.12);
        fbox(mFab(0xf6eee0), cx+bw*.06, Y+.68, rz+rh-MP-bd*.22, bw*.12, .20, bw*.12);
      }
      // wardrobe
      const wdW=Math.min(rw*.16,1.8), wdD=Math.min(rh*.28,1.6);
      box(mWood(0xaaa090), rx+rw-MP-wdW/2, Y+1.08, rz+MP+wdD/2, wdW, 2.20, wdD);
      // bedside lamp
      const bsW=Math.min(rw*.10,.90), bsD=Math.min(rh*.11,.80);
      const bsX=cx-bw/2-bsW/2-.12;
      if(fits(bsX,bz,bsW,bsD) && bsX-bsW/2>rx+MP){
        reg(bsX,bz,bsW,bsD);
        fbox(mWood(0x988870), bsX, Y+.42, bz, bsW, .42, bsD);
        cyl(mMetal(0xd0c06e), bsX, Y+.88, bz, .04,.034,.38,8);
        cyl(mFab(0xfaf6e6),   bsX, Y+1.16, bz, .14,.11,.18,10);
      }
      break;
    }

    case 'kitchen':{
      const KW=mWood(0xd0c8bc), KT=mFurn(0xe8e0d5,.68,.02);
      const ctrW=fw(0.68), ctrD=Math.min(rh*.12,1.0);
      // back counter — clamped to room
      if(box(KW, cx, Y+.90, rz+rh-MP-ctrD/2, ctrW, .92, ctrD)){
        fbox(KT,  cx, Y+.96, rz+rh-MP-ctrD/2, ctrW, .06, ctrD+.04, false,true);
        fbox(mWood(0xc0b8ac), cx, Y+2.18, rz+rh-MP-ctrD/2, ctrW*.97, .64, ctrD*.90);
        // sink on back counter
        fbox(mMetal(0xbcb8b4), cx+ctrW*.15, Y+.96, rz+rh-MP-ctrD/2, ctrW*.22, .06, ctrD*.80, false,true);
        fbox(mMetal(0xa0a090), cx+ctrW*.15, Y+.82, rz+rh-MP-ctrD/2, ctrW*.16, .13, ctrD*.68);
        cyl(mMetal(0xa0a090), cx+ctrW*.15, Y+1.02, rz+rh-MP-ctrD*.52, .022,.018,.18,8);
        fbox(mWall(0xdedad4), cx, Y+1.60, rz+rh-MP-ctrD*.48, ctrW*.97, .64, .03);
      }
      // side counter — only if room wide enough
      const scD=Math.min(rh*.52,4.0), scW=Math.min(rw*.10,.90);
      box(KW, rx+rw-MP-scW/2, Y+.90, rz+rh/2-scD*.06, scW, .92, scD);

      // island — only if room large enough
      const isW=Math.min(rw*.26,2.2), isD=Math.min(rh*.18,1.4);
      const isX=cx-rw*.06, isZ=rz+rh*.42;
      if(rw>10 && rh>10 && box(KW, isX, Y+.90, isZ, isW, .92, isD)){
        fbox(KT, isX, Y+.96, isZ, isW+.04, .06, isD+.04, false,true);
        // bar stools beside island — only if they fit
        const stW=.22, stD=.22;
        [isX-isW*.30, isX+isW*.30].forEach(sx=>{
          const stZ=isZ+isD/2+.40;
          if(fits(sx,stZ,stW,stD)){
            reg(sx,stZ,stW,stD);
            cyl(mMetal(0xa09078), sx, Y+.52, stZ, .05,.06,.82,8);
            fbox(mFab(0xa09070),   sx, Y+.94, stZ, stW, .10, stD);
          }
        });
      }

      // pendants — wall-mounted, no floor check
      [cx-fw(0.12), cx+fw(0.08)].forEach(px=>{
        cyl(mMetal(0xc8b84a), px, Y+2.58, isZ, .10,.13,.20,10);
        cyl(mMetal(0x888880), px, Y+2.08, isZ, .009,.009,.84,6);
      });
      break;
    }

    case 'dining':{
      // ── fully dynamic dining placement ─────────────────────
      const usableW = rw - MP*2;
      const usableH = rh - MP*2;

      // Table radius: max 35% of smaller usable dimension, min 1.2ft
      const tRad = Math.max(1.2, Math.min(usableW, usableH)*0.32);
      const tDiam = tRad*2;

      // Table position: centered in room
      const tX=cx, tZ=cz;

      // Only place if table fits with padding
      if(fits(tX, tZ, tDiam+0.2, tDiam+0.2)){
        reg(tX, tZ, tDiam+0.2, tDiam+0.2);
        cyl(mWood(0x6a4020), tX, Y+.74, tZ, tRad*.92, tRad, .07, 14);
        cyl(mWood(0x582e12), tX, Y+.38, tZ, .07, .10, .68, 8);
        cyl(mWood(0x582e12), tX, Y+.06, tZ, tRad*.48, tRad*.48, .08, 12);
        cyl(mFab(0xe5ddd0), tX, Y+.79, tZ, .12,.15,.06,12);
        cyl(mFurn(0x7888a0,.7), tX-tRad*.35, Y+.79, tZ-tRad*.15, .034,.048,.24,8);
      }

      // Chairs: evenly distributed around table
      // Number of chairs based on table radius
      const nChairs = tRad >= 1.8 ? 6 : tRad >= 1.4 ? 4 : 3;
      const chairR  = tRad + 0.65;   // distance from center to chair seat
      const seatW   = Math.min(0.50, tRad*0.35);
      const seatD   = Math.min(0.46, tRad*0.32);
      const backH   = Math.min(0.52, seatW*1.10);

      for(let i=0;i<nChairs;i++){
        const ang = (Math.PI*2/nChairs)*i - Math.PI/2;
        const sX  = tX + Math.cos(ang)*chairR;
        const sZ  = tZ + Math.sin(ang)*chairR;

        // bounding-box check for each chair individually
        if(!fits(sX,sZ,seatW+.12,seatD+.12)) continue;
        reg(sX,sZ,seatW+.12,seatD+.12);

        // seat + backrest
        fbox(mFab(0xb8a880), sX, Y+.42, sZ, seatW, .08, seatD, true,true);
        // backrest — oriented away from table center
        const bX = sX + Math.cos(ang)*seatD*.42;
        const bZ = sZ + Math.sin(ang)*seatD*.42;
        fbox(mFab(0xa89870), bX, Y+.80, bZ, seatW*.86, backH, .05);

        // 4 legs per chair
        const lOff=seatW*.38, lOffD=seatD*.38;
        [[lOff,lOffD],[lOff,-lOffD],[-lOff,lOffD],[-lOff,-lOffD]].forEach(([lx2,lz2])=>{
          cyl(mWood(0x9a7848), sX+lx2, Y+.22, sZ+lz2, .016,.020,.38,6);
        });
      }

      // pendant light — above table, no floor collision needed
      cyl(mMetal(0xcc9e28), tX, Y+2.48, tZ, .14,.17,.22,12);
      cyl(mMetal(0x848480), tX, Y+2.04, tZ, .009,.009,.78,6);
      break;
    }

    case 'entrance':{
      // console table — safe from front wall
      const ctW=fw(0.42), ctD=Math.min(rh*.14,.90);
      const ctZ=rz+MP+ctD/2;
      if(box(mWood(0x8a6a48), cx, Y+.72, ctZ, ctW, .06, ctD, true,true)){
        fbox(mWood(0x6c4e30), cx-ctW*.44, Y+.36, ctZ, .04, .64, .04);
        fbox(mWood(0x6c4e30), cx+ctW*.44, Y+.36, ctZ, .04, .64, .04);
        fbox(mGlass(0x90b4c0,.08), cx, Y+1.54, ctZ, ctW*.84, .68, .03);
        fbox(mWood(0x7c6048),      cx, Y+1.54, ctZ, ctW*.88, .70, .02);
      }
      // mat
      fbox(mFab(0xb89470), cx, Y+.01, rz+rh*.35, fw(0.40), .04, fh(0.18), false,true);
      // plant corner
      const pX=rx+rw-MP-.20, pZ=rz+rh-MP-.20;
      if(fits(pX,pZ,.42,.42)){
        reg(pX,pZ,.42,.42);
        cyl(mFurn(0x4e6e68,.7,.08), pX, Y+.38, pZ, .07,.10,.40,10);
        cyl(mFurn(0x285820,.88),    pX, Y+.72, pZ, .15,.11,.48,10);
      }
      break;
    }

    case 'bathroom':{
      // bathtub — left third of room, padded
      const tbW=Math.min(rw*.36,2.0), tbD=Math.min(rh*.52,3.0);
      const tbX=rx+MP+tbW/2, tbZ=cz;
      if(box(mWall(0xf4f2f0), tbX, Y+.34, tbZ, tbW, .40, tbD)){
        fbox(mGlass(0x88b8cc,.05), tbX, Y+.46, tbZ, tbW*.80, .24, tbD*.82);
        [[-.42,-.40],[.42,-.40],[-.42,.40],[.42,.40]].forEach(([ox,oz])=>
          cyl(mMetal(0xb0a888), tbX+tbW*ox, Y+.14, tbZ+tbD*oz, .035,.035,.26,8)
        );
      }
      // vanity — right side
      const vaW=Math.min(rw*.26,1.8), vaD=Math.min(rh*.34,2.0);
      const vaX=rx+rw-MP-vaW/2, vaZ=cz;
      if(box(mWood(0xece8e0), vaX, Y+.88, vaZ, vaW, .92, vaD)){
        fbox(mFloor(0xf0ece6), vaX, Y+.96, vaZ, vaW+.02, .06, vaD+.04, false,true);
        fbox(mMetal(0xc0bab4), vaX, Y+.84, vaZ, vaW*.52, .06, vaD*.40, false,true);
        cyl(mMetal(0xb0b0a8), vaX, Y+1.02, vaZ-vaD*.08, .020,.016,.18,8);
        fbox(mGlass(0x98b8c8,.10), vaX, Y+1.62, rz+.04, vaW*.95, .64, .02);
        fbox(mMetal(0xaaa8a4),     vaX, Y+1.62, rz+.05, vaW+.04, .66, .02);
      }
      // towel rail
      fbox(mMetal(0xb8b4b0), tbX, Y+1.20, rz+.04, tbW*.55, .04, .04);
      break;
    }

    case 'toilet':{
      // WC — back wall
      const wcW=Math.min(rw*.40,.90), wcD=Math.min(rh*.28,.70);
      box(mWall(0xf5f5f3), cx, Y+.27, rz+rh-MP-wcD/2, wcW, .28, wcD);
      fbox(mWall(0xf0f0ee), cx, Y+.52, rz+rh-MP-wcD*.38, wcW*.86, .10, wcD*.80);
      // sink — front
      const skW=Math.min(rw*.38,.85), skD=Math.min(rh*.24,.65);
      if(box(mWall(0xf5f5f3), cx, Y+.86, rz+MP+skD/2, skW, .08, skD, false,true)){
        fbox(mWall(0xeeecea), cx, Y+.44, rz+MP+skD/2, skW*.84, .80, skD*.88);
        fbox(mGlass(0x98b8c8,.09), cx, Y+1.54, rz+.04, skW*.90, .58, .02);
      }
      break;
    }

    case 'utility':{
      // washer + dryer side by side, front wall
      const apW=Math.min(rw*.26,.90), apD=Math.min(rh*.27,.80);
      const apZ=rz+MP+apD/2;
      box(mWall(0xf0f0ee), rx+MP+apW/2,       Y+.90, apZ, apW, .92, apD);
      fbox(mGlass(0x88aabb,.32), rx+MP+apW/2, Y+.62, apZ, apW*.50,.14,apD*.52);
      box(mWall(0xeeeeec), rx+MP+apW*1.5+.08, Y+.90, apZ, apW, .92, apD);
      // shelves — opposite wall
      const shW=Math.min(rw*.20,1.4), shD=Math.min(rh*.62,3.5);
      const shX=rx+rw-MP-shW/2;
      if(fits(shX,cz,shW,shD)){ reg(shX,cz,shW,shD);
        [.55,1.20,1.85].forEach(sy=>
          fbox(mWood(0xd0cab8), shX, Y+sy, cz, shW, .05, shD, false,true)
        );
        fbox(mWood(0xc8c2b0), shX+shW*.42, Y+1.20, cz, .04,1.80,.05);
      }
      break;
    }

    } // end switch
  }


  /* ═══════════════════════════════════════════════════════════
     LIGHTS  — warm sun + low ambient + fill + per-room points
  ═══════════════════════════════════════════════════════════ */
  function _mkLights(){
    const L=LP.day;

    // Ambient — very low so shadows remain visible
    lAmb=new THREE.AmbientLight(L.amb.col, L.amb.int);
    scene.add(lAmb);

    // Hemisphere bounce
    lHemi=new THREE.HemisphereLight(L.hemi.sky, L.hemi.gnd, L.hemi.int);
    scene.add(lHemi);

    // Main sun — warm, casts soft shadows
    lSun=new THREE.DirectionalLight(L.sun.col, L.sun.int);
    lSun.position.set(50,80,50);
    lSun.castShadow=true;
    lSun.shadow.mapSize.width  = 2048;
    lSun.shadow.mapSize.height = 2048;
    lSun.shadow.bias           = -0.0004;
    lSun.shadow.normalBias     = 0.025;
    lSun.shadow.radius         = 6;      // soft penumbra
    lSun.shadow.camera.left    = lSun.shadow.camera.bottom = -180;
    lSun.shadow.camera.right   = lSun.shadow.camera.top    =  180;
    lSun.shadow.camera.near    = 1;
    lSun.shadow.camera.far     = 900;
    scene.add(lSun);

    // Fill — cool from opposite direction
    lFill=new THREE.DirectionalLight(L.fill.col, L.fill.int);
    lFill.position.set(-40,30,-40);
    scene.add(lFill);

    // Per-room ceiling point lights — warm interior glow
    const RC={
      living:0xffe8c8, master_bedroom:0xffeedd, bedroom:0xfff0e0,
      kitchen:0xfff8d4, dining:0xffeec4, bathroom:0xd4f5f8,
      toilet:0xd0f0ff,  entrance:0xfff0d0, utility:0xf8f8f0,
    };
    roomLights=[];
    layout.rooms.forEach(r=>{
      const rw=r.width||r.w, rh=r.height||r.h;
      const rl=new THREE.PointLight(RC[r.type]||0xfff8f0, L.ri, Math.max(rw,rh)*3.0);
      rl.position.set(r.x+rw/2, WH-0.30, r.y+rh/2);
      scene.add(rl); roomLights.push(rl);
    });
  }

  /* ═══════════════════════════════════════════════════════════
     RENDER LOOP
  ═══════════════════════════════════════════════════════════ */
  function _loop(){
    animId=requestAnimationFrame(_loop);
    if(autoSpin&&cmode==='orbit'){theta+=SPIN;_cam();}
    _hover(); renderer.render(scene,camera);
  }
  function _stop(){ if(animId){cancelAnimationFrame(animId);animId=null;} }

  /* ═══════════════════════════════════════════════════════════
     HOVER + CLICK  — room highlight + detail panel
  ═══════════════════════════════════════════════════════════ */
  function _hover(){
    raycaster.setFromCamera(mouse3,camera);
    const hits=raycaster.intersectObjects(pick);
    if(hits.length&&hits[0].object.userData.room){
      const m=hits[0].object;
      if(m!==hov){if(hov)_unhigh(hov);hov=m;_high(m);}
      _showLbl(m.userData.room,hits[0].point);
    }else{
      if(hov){_unhigh(hov);hov=null;} _hideLbl();
    }
  }
  function _high(m){
    if(!m.material)return;
    m.material.emissive=m.material.emissive||new THREE.Color(0);
    m.material.emissive.setHex(0x223348); m.material.emissiveIntensity=0.20;
    cvs.style.cursor='pointer';
  }
  function _unhigh(m){ if(m.material)m.material.emissiveIntensity=0; cvs.style.cursor=''; }

  function _showLbl(room,pt){
    const p=pt.clone().project(camera);
    const cw=cvs.clientWidth, ch=cvs.clientHeight;
    elLabel.style.left   =((p.x*.5+.5)*cw)+'px';
    elLabel.style.top    =((-p.y*.5+.5)*ch-58)+'px';
    elLabel.style.opacity='1';
    const pal=PAL[room.type]||DP;
    elLabel.style.borderColor=pal.css;
    elLabel.querySelector('.arl-name').textContent=room.label;
    const a=room.area||Math.round((room.width||room.w)*(room.height||room.h));
    elLabel.querySelector('.arl-area').textContent=Math.round(a)+' sqft';
  }
  function _hideLbl(){ elLabel.style.opacity='0'; }

  function _openPanel(m){
    if(!m?.userData?.room)return;
    const{room,pal}=m.userData;
    const w=(room.width||room.w||0).toFixed(1);
    const h=(room.height||room.h||0).toFixed(1);
    const a=Math.round(room.area||parseFloat(w)*parseFloat(h));
    elPanel.querySelector('.arp-dot').style.background=pal.css;
    elPanel.querySelector('.arp-name').textContent=room.label;
    elPanel.querySelector('.arp-name').style.color=pal.css;
    elPanel.querySelector('#arp-w').textContent=w+' ft';
    elPanel.querySelector('#arp-h').textContent=h+' ft';
    elPanel.querySelector('#arp-a').textContent=a+' sqft';
    elPanel.querySelector('#arp-t').textContent=room.type.replace(/_/g,' ');
    const rule=(window.activeLayout?.vastu_rules||[])
      .find(rv=>rv.label.toLowerCase().includes(room.type.split('_')[0].toLowerCase()));
    const re=elPanel.querySelector('#arp-rule');
    if(rule){
      re.textContent={compliant:'✓ Compliant',partial:'~ Partial',violation:'✗ Violation',missing:'— Missing'}[rule.status]||rule.status;
      re.style.color={compliant:'#4ade80',partial:'#fbbf24',violation:'#f87171',missing:'#64748b'}[rule.status]||'#94a3b8';
    }else{ re.textContent='— No data'; re.style.color='#64748b'; }
    elPanel.classList.add('ar2-panel-visible');
  }

  /* ═══════════════════════════════════════════════════════════
     MINI-MAP
  ═══════════════════════════════════════════════════════════ */
  function _drawMap(){
    if(!elMap||!layout)return;
    const ctx=elMap.getContext('2d'), mw=elMap.width, mh=elMap.height, pad=7;
    const sc=Math.min((mw-pad*2)/plot.width,(mh-pad*2)/plot.height);
    ctx.clearRect(0,0,mw,mh);
    ctx.fillStyle='rgba(235,230,220,.96)'; ctx.fillRect(0,0,mw,mh);
    ctx.strokeStyle='rgba(90,70,50,.6)'; ctx.lineWidth=1.2;
    ctx.strokeRect(pad,pad,plot.width*sc,plot.height*sc);
    layout.rooms.forEach(r=>{
      const pal=PAL[r.type]||DP;
      const x2=pad+r.x*sc, y2=pad+r.y*sc;
      const w2=(r.width||r.w)*sc, h2=(r.height||r.h)*sc;
      ctx.fillStyle=pal.fill.replace('.4','.48');
      ctx.strokeStyle=pal.css+'aa'; ctx.lineWidth=0.7;
      ctx.fillRect(x2,y2,w2,h2); ctx.strokeRect(x2,y2,w2,h2);
    });
    ctx.fillStyle='rgba(90,70,50,.45)'; ctx.font='5px monospace';
    ctx.fillText('PLAN',pad,mh-4);
  }

  /* ═══════════════════════════════════════════════════════════
     DOM OVERLAYS
  ═══════════════════════════════════════════════════════════ */
  function _mkOv(){
    elLabel=_div('ar2-label');
    elLabel.innerHTML='<span class="arl-name"></span><span class="arl-area"></span>';
    wrap.appendChild(elLabel);

    elPanel=_div('ar2-panel');
    elPanel.innerHTML=`
      <div class="arp-header">
        <span class="arp-dot"></span><span class="arp-name">Room</span>
        <button class="arp-close" onclick="ARViewer.closePanel()">✕</button>
      </div>
      <div class="arp-body">
        <div class="arp-row"><span class="arp-key">Width</span><span class="arp-val" id="arp-w">—</span></div>
        <div class="arp-row"><span class="arp-key">Depth</span><span class="arp-val" id="arp-h">—</span></div>
        <div class="arp-row"><span class="arp-key">Area</span> <span class="arp-val" id="arp-a">—</span></div>
        <div class="arp-row"><span class="arp-key">Type</span> <span class="arp-val" id="arp-t">—</span></div>
        <div class="arp-row"><span class="arp-key">Vastu</span><span class="arp-val" id="arp-rule">—</span></div>
      </div>`;
    wrap.appendChild(elPanel);

    elMap=document.createElement('canvas');
    elMap.className='ar2-minimap'; elMap.width=elMap.height=140;
    wrap.appendChild(elMap);

    elCmp=_div('ar2-compass'); _mkCmp(); wrap.appendChild(elCmp);

    elHelp=_div('ar2-help');
    elHelp.innerHTML=`
      <div class="arh-title">Keyboard Shortcuts</div>
      <div class="arh-grid">
        <kbd>R</kbd><span>Reset camera</span>  <kbd>W</kbd><span>Wireframe</span>
        <kbd>E</kbd><span>Explode view</span>   <kbd>T</kbd><span>Top view</span>
        <kbd>I</kbd><span>Isometric</span>      <kbd>O</kbd><span>Orbit</span>
        <kbd>1</kbd><span>Day light</span>      <kbd>2</kbd><span>Dusk</span>
        <kbd>3</kbd><span>Night</span>          <kbd>S</kbd><span>Screenshot</span>
        <kbd>F</kbd><span>Fullscreen</span>     <kbd>Esc</kbd><span>Close panels</span>
        <kbd>Dbl-click</kbd><span>Room details</span>
      </div>
      <button class="arh-close" onclick="ARViewer.closeHelp()">✕ Close</button>`;
    wrap.appendChild(elHelp);
  }
  function _rmOv(){ [elLabel,elPanel,elMap,elCmp,elHelp].forEach(e=>e?.remove()); elLabel=elPanel=elMap=elCmp=elHelp=null; }
  function _mkCmp(){
    const f=plot.facing||'North', rot={North:0,East:90,South:180,West:270}[f]||0;
    elCmp.innerHTML=`<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
      <circle cx="32" cy="32" r="30" fill="rgba(242,238,230,.92)" stroke="rgba(90,70,50,.3)" stroke-width="1"/>
      <text x="32" y="11" text-anchor="middle" fill="#c03838" font-size="7.5" font-family="monospace" font-weight="700">N</text>
      <text x="55" y="35" text-anchor="middle" fill="#806050" font-size="6.5" font-family="monospace">E</text>
      <text x="32" y="58" text-anchor="middle" fill="#806050" font-size="6.5" font-family="monospace">S</text>
      <text x="9"  y="35" text-anchor="middle" fill="#806050" font-size="6.5" font-family="monospace">W</text>
      <g transform="rotate(${rot} 32 32)">
        <polygon points="32,7 35,32 32,37 29,32" fill="#c03838" opacity=".9"/>
        <polygon points="32,57 35,32 32,27 29,32" fill="rgba(90,70,50,.3)"/>
      </g>
      <circle cx="32" cy="32" r="3" fill="#b88c28"/>
      <text x="32" y="47" text-anchor="middle" fill="#b88c28" font-size="5" font-family="monospace">${f.toUpperCase()}</text>
    </svg>`;
  }

  /* ═══════════════════════════════════════════════════════════
     EVENTS
  ═══════════════════════════════════════════════════════════ */
  const _eMD=e=>{drag=true;rDrag=e.button===2;autoSpin=false;lx=e.clientX;ly=e.clientY;};
  const _eMU=()=>drag=false;
  const _eMM=e=>{
    const r=cvs.getBoundingClientRect();
    mouse3.x=((e.clientX-r.left)/r.width)*2-1;
    mouse3.y=((e.clientY-r.top)/r.height)*-2+1;
    if(!drag)return;
    const dx=e.clientX-lx, dy=e.clientY-ly; lx=e.clientX; ly=e.clientY;
    if(rDrag){
      const s=radius*.0012;
      panX-=dx*s*Math.cos(theta)+dy*s*Math.sin(theta)*.5;
      panZ-=-dx*s*Math.sin(theta)+dy*s*Math.cos(theta)*.5;
    }else{ theta-=dx*.007; phi=Math.max(.05,Math.min(1.48,phi-dy*.007)); }
    _cam();
  };
  const _eW=e=>{ radius=Math.max(ZMIN,Math.min(ZMAX,radius+e.deltaY*.12));autoSpin=false;if(cmode!=='orbit')cmode='orbit';_cam();e.preventDefault(); };
  const _eD=e=>{
    const r=cvs.getBoundingClientRect();
    mouse3.x=((e.clientX-r.left)/r.width)*2-1;
    mouse3.y=((e.clientY-r.top)/r.height)*-2+1;
    raycaster.setFromCamera(mouse3,camera);
    const hits=raycaster.intersectObjects(pick);
    if(hits.length)_openPanel(hits[0].object);
  };
  const _eCx=e=>e.preventDefault();
  const _eTS=e=>{ autoSpin=false;tch=Array.from(e.touches);if(tch.length===2)lpin=_pd(tch); };
  const _eTM=e=>{
    e.preventDefault();
    const n=Array.from(e.touches);
    if(n.length===1&&tch.length===1){
      const dx=n[0].clientX-tch[0].clientX, dy=n[0].clientY-tch[0].clientY;
      theta-=dx*.011; phi=Math.max(.05,Math.min(1.48,phi-dy*.011)); _cam();
    }else if(n.length===2){
      const d=_pd(n);
      radius=Math.max(ZMIN,Math.min(ZMAX,radius+(lpin-d)*.23));
      lpin=d; _cam();
    }
    tch=n;
  };
  const _eTE=e=>tch=Array.from(e.touches);
  const _eK=e=>{
    if(e.target.tagName==='INPUT'||e.target.tagName==='SELECT')return;
    ({r:reset,w:toggleWireframe,e:toggleExplode,t:setTop,i:setIso,o:setOrbit,
      1:()=>setLight('day'),2:()=>setLight('dusk'),3:()=>setLight('night'),
      s:screenshot,f:fullscreen,'?':showHelp,
      escape:()=>{closeHelp();closePanel();}
    }[e.key.toLowerCase()]||(_=>{}))();
  };
  function _bind(){
    cvs.addEventListener('mousedown',_eMD); cvs.addEventListener('dblclick',_eD);
    cvs.addEventListener('contextmenu',_eCx); cvs.addEventListener('wheel',_eW,{passive:false});
    cvs.addEventListener('touchstart',_eTS,{passive:false}); cvs.addEventListener('touchmove',_eTM,{passive:false});
    cvs.addEventListener('touchend',_eTE);
    window.addEventListener('mouseup',_eMU); window.addEventListener('mousemove',_eMM);
    window.addEventListener('keydown',_eK);
    resObs=new ResizeObserver(()=>{
      const w=wrap.clientWidth||900;
      renderer.setSize(w,CANVAS_H); camera.aspect=w/CANVAS_H;
      camera.updateProjectionMatrix();
    });
    resObs.observe(wrap);
  }
  function _unbind(){
    cvs?.removeEventListener('mousedown',_eMD); cvs?.removeEventListener('dblclick',_eD);
    cvs?.removeEventListener('contextmenu',_eCx); cvs?.removeEventListener('wheel',_eW);
    cvs?.removeEventListener('touchstart',_eTS); cvs?.removeEventListener('touchmove',_eTM);
    cvs?.removeEventListener('touchend',_eTE);
    window.removeEventListener('mouseup',_eMU); window.removeEventListener('mousemove',_eMM);
    window.removeEventListener('keydown',_eK);
  }

  /* ═══════════════════════════════════════════════════════════
     UTILS
  ═══════════════════════════════════════════════════════════ */
  function _mesh(geo,mat){ const m=new THREE.Mesh(geo,mat); return m; }
  function _addM(geo,mat,x,y,z,cast,recv){
    const m=_mesh(geo,mat); m.position.set(x,y,z);
    if(cast)m.castShadow=true; if(recv)m.receiveShadow=true;
    scene.add(m); return m;
  }
  function _anim(obj,tgt){
    if(!obj)return;
    const f=obj.position.clone(), t0=performance.now(), dur=520;
    (function s(now){
      const p=Math.min((now-t0)/dur,1), ep=p<.5?2*p*p:-1+(4-2*p)*p;
      obj.position.lerpVectors(f,tgt,ep);
      if(p<1)requestAnimationFrame(s);
    })(performance.now());
  }
  function _act(id,on){ document.getElementById(id)?.classList.toggle('ar-ctrl-active',on); }
  function _pd(ts){ const dx=ts[0].clientX-ts[1].clientX,dy=ts[0].clientY-ts[1].clientY;return Math.sqrt(dx*dx+dy*dy); }
  function _div(cls){ const d=document.createElement('div');d.className=cls;return d; }
  function _toast(msg){ if(typeof showToast==='function')showToast(msg,'🔮'); }
  function _kill(){ _stop();if(renderer){renderer.dispose();renderer=null;}scene=camera=raycaster=null;roomGrps=[];pick=[];roomLights=[]; }

  /* ═══════════════════════════════════════════════════════════
     EXPOSE
  ═══════════════════════════════════════════════════════════ */
  return {
    init,destroy,reset,
    toggleWireframe,toggleExplode,
    setTop,setIso,setOrbit,
    setLight,screenshot,fullscreen,
    closePanel,showHelp,closeHelp,
  };
})();