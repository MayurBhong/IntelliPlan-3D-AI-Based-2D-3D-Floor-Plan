/* ═══════════════════════════════════════════════════════════════
   IntelliPlan·3D  —  PDF EXPORT MODULE  (pdf.js)
═══════════════════════════════════════════════════════════════ */

window.PDFExporter = (() => {
  'use strict';

  const JSPDF_CDN = 'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js';

  /* ── Room colour palette
     — balcony and store removed
     — bathroom_master, toilet_master, bathroom_attached, toilet_attached added
  ───────────────────────────────────────────────────────────── */
  const PAL = {
    entrance:            { r:236, g:72,  b:153 },
    living:              { r:59,  g:130, b:246 },
    dining:              { r:234, g:179, b:8   },
    kitchen:             { r:245, g:158, b:11  },
    master_bedroom:      { r:139, g:92,  b:246 },
    bedroom:             { r:99,  g:102, b:241 },
    bathroom:            { r:20,  g:184, b:166 },
    toilet:              { r:6,   g:182, b:212 },
    bathroom_master:     { r:45,  g:212, b:191 },
    toilet_master:       { r:34,  g:211, b:238 },
    bathroom_attached:   { r:52,  g:211, b:153 },
    toilet_attached:     { r:56,  g:189, b:248 },
    pooja:               { r:249, g:115, b:22  },
    utility:             { r:148, g:163, b:184 },
  };
  const DEF_C = { r:100, g:116, b:139 };

  const PW = 210, PH = 297;
  const MARGIN = 14;
  const INNER  = PW - MARGIN * 2;

  let modalEl = null;
  let jsPDFReady = false;

  /* ═══ PUBLIC API ════════════════════════════════════════════ */
  async function open() {
    if (!window.activeLayout) { showToast('⚠ Generate a floor plan first', '⚠'); return; }
    _buildModal();
    await _loadPreview();
  }

  async function exportPDF() {
    if (!window.activeLayout) { showToast('⚠ Generate a floor plan first', '⚠'); return; }

    const id = window.activeLayout.layout_id;
    if (id && !id.startsWith('demo') && window.API_BASE) {
      try {
        showToast('📄 Requesting PDF from server…', '📄');
        const res = await fetch(`${window.API_BASE}/api/export/pdf/${id}`);
        if (res.ok) {
          const blob = await res.blob();
          _download(URL.createObjectURL(blob), `intelliplan-${id.slice(0,8)}.pdf`);
          showToast('✓ PDF downloaded', '✓');
          return;
        }
      } catch (_) { /* fall through */ }
    }

    showToast('📄 Generating PDF…', '📄');
    try {
      await _ensureJsPDF();
      const doc = await _buildPDF();
      const filename = `intelliplan-${Date.now()}.pdf`;
      doc.save(filename);
      showToast('✓ PDF saved: ' + filename, '✓');
    } catch (err) {
      console.error('PDF generation failed:', err);
      showToast('⚠ PDF generation failed', '⚠');
    }
  }

  function close() {
    if (modalEl) {
      modalEl.classList.remove('pdf-modal-visible');
      setTimeout(() => { modalEl?.remove(); modalEl = null; }, 300);
    }
  }

  /* ═══ MODAL ═════════════════════════════════════════════════ */
  function _buildModal() {
    document.getElementById('pdf-modal')?.remove();
    modalEl = document.createElement('div');
    modalEl.id = 'pdf-modal';
    modalEl.className = 'pdf-modal';
    modalEl.innerHTML = `
      <div class="pdf-modal-backdrop" onclick="PDFExporter.close()"></div>
      <div class="pdf-modal-dialog">
        <div class="pdf-modal-header">
          <div class="pdf-modal-title"><span class="pdf-modal-icon">📄</span>Export Floor Plan Report</div>
          <div class="pdf-modal-meta" id="pdf-meta">Preparing preview…</div>
          <button class="pdf-modal-close" onclick="PDFExporter.close()">✕</button>
        </div>
        <div class="pdf-preview-wrap">
          <div class="pdf-preview-pages" id="pdf-preview-pages">
            <div class="pdf-preview-loading" id="pdf-preview-loading">
              <div class="pdf-spinner"></div><span>Rendering preview…</span>
            </div>
          </div>
        </div>
        <div class="pdf-options-row">
          <div class="pdf-option-group">
            <label class="pdf-opt-label">Include</label>
            <label class="pdf-check-wrap"><input type="checkbox" id="pdf-opt-floorplan" checked /><span class="pdf-checkmark"></span>Floor Plan</label>
            <label class="pdf-check-wrap"><input type="checkbox" id="pdf-opt-vastu" checked /><span class="pdf-checkmark"></span>Vastu Analysis</label>
            <label class="pdf-check-wrap"><input type="checkbox" id="pdf-opt-table" checked /><span class="pdf-checkmark"></span>Room Table</label>
          </div>
          <div class="pdf-option-group">
            <label class="pdf-opt-label">Quality</label>
            <select class="pdf-select" id="pdf-quality">
              <option value="2">High (2×)</option>
              <option value="1.5">Medium (1.5×)</option>
              <option value="1">Standard (1×)</option>
            </select>
          </div>
        </div>
        <div class="pdf-modal-footer">
          <button class="pdf-btn-secondary" onclick="PDFExporter.close()">Cancel</button>
          <button class="pdf-btn-primary" id="pdf-export-btn" onclick="PDFExporter._doExportFromModal()">
            <span class="pdf-btn-icon">⬇</span>Download PDF
          </button>
        </div>
      </div>`;
    document.body.appendChild(modalEl);
    requestAnimationFrame(() => modalEl.classList.add('pdf-modal-visible'));
    const _kh = e => { if (e.key === 'Escape') { PDFExporter.close(); document.removeEventListener('keydown', _kh); } };
    document.addEventListener('keydown', _kh);
  }

  async function _loadPreview() {
    try {
      await _ensureJsPDF();
      const l  = window.activeLayout;
      const p  = l.plot || {};
      const dt = new Date().toLocaleString('en-IN', { dateStyle:'medium', timeStyle:'short' });
      const meta = document.getElementById('pdf-meta');
      if (meta) meta.textContent = `${p.bhk_type||'—'} · ${p.width||'?'}×${p.height||'?'} ft · ${p.facing||'—'} · ${dt}`;

      const pagesEl = document.getElementById('pdf-preview-pages');
      const loadEl  = document.getElementById('pdf-preview-loading');
      const pg1 = await _renderPage1Canvas(1.5);
      const pg2 = await _renderPage2Canvas(1.5);
      if (loadEl) loadEl.remove();

      [pg1, pg2].forEach((c, i) => {
        const wrap  = document.createElement('div');
        wrap.className = 'pdf-page-thumb';
        const label = document.createElement('div');
        label.className = 'pdf-page-label';
        label.textContent = `Page ${i+1} of 2`;
        wrap.appendChild(c); wrap.appendChild(label);
        pagesEl?.appendChild(wrap);
      });
    } catch (err) {
      console.error('Preview failed:', err);
      const l = document.getElementById('pdf-preview-loading');
      if (l) l.innerHTML = '<span style="color:#f87171">Preview unavailable — export will still work</span>';
    }
  }

  async function _doExportFromModal() {
    const btn = document.getElementById('pdf-export-btn');
    if (btn) { btn.textContent = '⏳ Generating…'; btn.disabled = true; }
    try {
      await _ensureJsPDF();
      const doc = await _buildPDF();
      const filename = `intelliplan-${Date.now()}.pdf`;
      doc.save(filename);
      showToast('✓ PDF saved: ' + filename, '✓');
      close();
    } catch (err) {
      console.error('PDF export error:', err);
      showToast('⚠ Export failed — see console', '⚠');
      if (btn) { btn.textContent = '⬇ Download PDF'; btn.disabled = false; }
    }
  }

  /* ═══ PDF BUILDING ══════════════════════════════════════════ */
  async function _buildPDF() {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF({ orientation:'portrait', unit:'mm', format:'a4' });
    const incFloor = document.getElementById('pdf-opt-floorplan')?.checked ?? true;
    const incVastu = document.getElementById('pdf-opt-vastu')?.checked ?? true;
    const incTable = document.getElementById('pdf-opt-table')?.checked ?? true;
    const quality  = parseFloat(document.getElementById('pdf-quality')?.value || '2');
    await _writePage1(doc, quality, incFloor, incVastu);
    if (incVastu || incTable) { doc.addPage(); await _writePage2(doc, incVastu, incTable); }
    return doc;
  }

  async function _writePage1(doc, quality, incFloor, incVastu) {
    const l = window.activeLayout;
    const p = l.plot || {};
    let y   = MARGIN;

    doc.setFillColor(2, 11, 24); doc.rect(0, 0, PW, 22, 'F');
    doc.setFont('helvetica', 'bold'); doc.setFontSize(16);
    doc.setTextColor(232, 192, 96); doc.text('IntelliPlan', MARGIN, 13);
    doc.setTextColor(56, 189, 248); doc.text('·3D', MARGIN + 34, 13);
    doc.setFont('helvetica', 'normal'); doc.setFontSize(7);
    doc.setTextColor(100, 116, 139);
    doc.text('AI FLOOR PLAN STUDIO  ·  GA + VASTU ENGINE', MARGIN, 18.5);
    const dt = new Date().toLocaleString('en-IN', { dateStyle:'medium', timeStyle:'short' });
    doc.setTextColor(71, 85, 105); doc.setFontSize(6.5);
    doc.text(dt, PW - MARGIN, 13, { align:'right' });
    y = 28;

    doc.setFont('helvetica', 'bold'); doc.setFontSize(20);
    doc.setTextColor(255, 255, 255); doc.text('Floor Plan Report', MARGIN, y); y += 7;
    doc.setFont('helvetica', 'normal'); doc.setFontSize(9);
    doc.setTextColor(148, 163, 184);
    doc.text(`${p.bhk_type||'—'}  ·  ${p.width||'?'}×${p.height||'?'} ft  ·  ${p.facing||'—'} Facing  ·  Vastu Score: ${Math.round(l.vastu_score||0)}%`, MARGIN, y); y += 6;
    doc.setDrawColor(201, 150, 42); doc.setLineWidth(0.3); doc.line(MARGIN, y, PW - MARGIN, y); y += 5;

    const kpis = [
      ['Plot Size',    `${p.width||'?'}×${p.height||'?'} ft`],
      ['BHK',          p.bhk_type   || '—'],
      ['Facing',       p.facing     || '—'],
      ['Vastu Score',  `${Math.round(l.vastu_score||0)}%`],
      ['Rooms',        String(l.rooms?.length || '—')],
      ['Area',         `${((p.width||0)*(p.height||0)).toLocaleString()} sqft`],
      ['Space Util',   `${Math.round(l.space_util||0)}%`],
      ['Fitness',      (l.fitness||0).toFixed(3)],
    ];
    const kpiW = INNER / kpis.length;
    kpis.forEach(([lbl, val], i) => {
      const kx = MARGIN + i * kpiW;
      doc.setFillColor(4, 15, 31); doc.roundedRect(kx, y, kpiW - 1, 13, 1, 1, 'F');
      doc.setFont('helvetica', 'bold'); doc.setFontSize(9.5); doc.setTextColor(255, 255, 255);
      doc.text(val, kx + kpiW/2 - 0.5, y + 7, { align:'center' });
      doc.setFont('helvetica', 'normal'); doc.setFontSize(6); doc.setTextColor(100, 116, 139);
      doc.text(lbl.toUpperCase(), kx + kpiW/2 - 0.5, y + 11.5, { align:'center' });
    });
    y += 17;

    if (incFloor) {
      doc.setFont('helvetica', 'bold'); doc.setFontSize(8); doc.setTextColor(56, 189, 248);
      doc.text('FLOOR PLAN  —  2D BLUEPRINT', MARGIN, y); y += 4;
      const fpH = incVastu ? 110 : 138;
      const fpCanvas = await _renderFloorPlanCanvas(Math.round(INNER*quality*3.78), Math.round(fpH*quality*3.78), l);
      doc.addImage(fpCanvas.toDataURL('image/png'), 'PNG', MARGIN, y, INNER, fpH);
      doc.setDrawColor(56, 189, 248); doc.setLineWidth(0.2); doc.rect(MARGIN, y, INNER, fpH);
      y += fpH + 4;
    }

    if (incVastu) {
      const ringCanvas = _renderScoreRingCanvas(180, l.vastu_score || 0);
      const ringSize   = 38;
      const ringX      = PW - MARGIN - ringSize;
      doc.setFont('helvetica', 'bold'); doc.setFontSize(8); doc.setTextColor(56, 189, 248);
      doc.text('VASTU SCORE', MARGIN, y + 12);
      doc.addImage(ringCanvas.toDataURL('image/png'), 'PNG', ringX, y, ringSize, ringSize);

      const rules = l.vastu_rules || [];
      const barX  = MARGIN, barY = y + 3;
      const barW  = ringX - MARGIN - 6;
      rules.slice(0, 8).forEach((r, i) => {
        const ry  = barY + i * 6.5;
        const pct = r.weight > 0 ? (r.earned / r.weight) : 0;
        const [cr,cg,cb] = pct>=0.8?[74,222,128]:pct>=0.5?[251,191,36]:[248,113,113];
        doc.setFontSize(6); doc.setFont('helvetica','normal'); doc.setTextColor(148,163,184);
        doc.text(r.label, barX, ry + 3.5);
        doc.setFillColor(7,21,41); doc.roundedRect(barX+52, ry+0.5, barW-52, 3.5, 1, 1, 'F');
        if (pct > 0) { doc.setFillColor(cr,cg,cb); doc.roundedRect(barX+52, ry+0.5, (barW-52)*pct, 3.5, 1, 1, 'F'); }
        doc.setTextColor(cr,cg,cb); doc.text(`${Math.round(pct*100)}%`, barX+barW+1, ry+3.5);
      });
      y += ringSize + 5;
    }

    _writePageFooter(doc, 1);
  }

  async function _writePage2(doc, incVastu, incTable) {
    const l = window.activeLayout;
    let y   = MARGIN;

    doc.setFillColor(2,11,24); doc.rect(0,0,PW,14,'F');
    doc.setFont('helvetica','bold'); doc.setFontSize(10); doc.setTextColor(232,192,96);
    doc.text('IntelliPlan·3D', MARGIN, 9);
    doc.setFont('helvetica','normal'); doc.setFontSize(7); doc.setTextColor(100,116,139);
    doc.text('ANALYSIS REPORT', PW-MARGIN, 9, { align:'right' });
    y = 20;

    doc.setFont('helvetica','bold'); doc.setFontSize(14); doc.setTextColor(255,255,255);
    doc.text('Layout Analysis', MARGIN, y); y += 5;
    doc.setDrawColor(201,150,42); doc.setLineWidth(0.3); doc.line(MARGIN,y,PW-MARGIN,y); y += 6;

    if (incVastu) {
      doc.setFont('helvetica','bold'); doc.setFontSize(8); doc.setTextColor(56,189,248);
      doc.text('VASTU COMPLIANCE BREAKDOWN', MARGIN, y); y += 5;
      (l.vastu_rules||[]).forEach(r => {
        const pct = r.weight>0 ? r.earned/r.weight : 0;
        const [cr,cg,cb] = pct>=0.8?[74,222,128]:pct>=0.5?[251,191,36]:[248,113,113];
        const statusTxt = r.status==='compliant'?'✓ Compliant':r.status==='partial'?'~ Partial':r.status==='missing'?'— Missing':'✗ Violation';
        doc.setFillColor(4,15,31); doc.rect(MARGIN,y-3,INNER,8,'F');
        doc.setFont('helvetica','normal'); doc.setFontSize(7.5); doc.setTextColor(203,213,225);
        doc.text(r.label, MARGIN+2, y+2);
        doc.setFontSize(6); doc.setTextColor(100,116,139);
        doc.text(r.description||'', MARGIN+55, y+2);
        const trackX=MARGIN+100, trackW=62;
        doc.setFillColor(7,21,41); doc.roundedRect(trackX,y-1,trackW,4,1,1,'F');
        if (pct>0) { doc.setFillColor(cr,cg,cb); doc.roundedRect(trackX,y-1,trackW*pct,4,1,1,'F'); }
        doc.setFont('helvetica','bold'); doc.setFontSize(6.5); doc.setTextColor(cr,cg,cb);
        doc.text(`${Math.round(pct*100)}%`, trackX+trackW+2, y+2.5);
        doc.setFontSize(6); doc.setTextColor(cr,cg,cb);
        doc.text(statusTxt, PW-MARGIN, y+2, { align:'right' });
        y += 10;
      });
      y += 4;
    }

    if (incTable) {
      doc.setFont('helvetica','bold'); doc.setFontSize(8); doc.setTextColor(56,189,248);
      doc.text('ROOM SPECIFICATIONS', MARGIN, y); y += 5;

      const cols = [
        { lbl:'Room Name',  w:50 },
        { lbl:'Type',       w:40 },
        { lbl:'Width (ft)', w:28 },
        { lbl:'Depth (ft)', w:28 },
        { lbl:'Area (sqft)',w:28 },
        { lbl:'Vastu',      w:22 },
      ];
      const rowH = 7.5;

      doc.setFillColor(7,21,41); doc.rect(MARGIN,y-3.5,INNER,rowH,'F');
      doc.setFont('helvetica','bold'); doc.setFontSize(6.5); doc.setTextColor(100,116,139);
      let cx = MARGIN+2;
      cols.forEach(c => { doc.text(c.lbl.toUpperCase(), cx, y+1); cx += c.w; });
      y += rowH;
      doc.setDrawColor(56,189,248); doc.setLineWidth(0.15); doc.line(MARGIN,y-0.5,PW-MARGIN,y-0.5);

      (l.rooms||[]).forEach((r, i) => {
        const pal = PAL[r.type] || DEF_C;
        const w   = (r.width  || r.w || 0).toFixed(1);
        const h   = (r.height || r.h || 0).toFixed(1);
        const a   = Math.round(r.area || (parseFloat(w)*parseFloat(h)));
        const rule = (l.vastu_rules||[]).find(rv => rv.label.toLowerCase().includes(r.type.split('_')[0].toLowerCase()));
        const vstTxt = rule ? ({ compliant:'✓', partial:'~', violation:'✗', missing:'—' }[rule.status]||'—') : '—';
        const vstClr = rule ? ({ compliant:[74,222,128], partial:[251,191,36], violation:[248,113,113], missing:[100,116,139] }[rule.status]||[100,116,139]) : [100,116,139];

        if (i%2===0) { doc.setFillColor(4,15,31); doc.rect(MARGIN,y-3.5,INNER,rowH,'F'); }
        doc.setFillColor(pal.r,pal.g,pal.b); doc.roundedRect(MARGIN+1,y-2,2.5,4,0.5,0.5,'F');

        cx = MARGIN+5; doc.setFont('helvetica','normal'); doc.setFontSize(7);
        doc.setTextColor(203,213,225); doc.text(r.label, cx, y+1); cx += cols[0].w-3;
        doc.setTextColor(100,116,139); doc.text(r.type.replace(/_/g,' '), cx, y+1); cx += cols[1].w;
        doc.setTextColor(203,213,225);
        doc.text(w, cx+cols[2].w/2, y+1, { align:'center' }); cx += cols[2].w;
        doc.text(h, cx+cols[3].w/2, y+1, { align:'center' }); cx += cols[3].w;
        doc.setTextColor(217,170,63);
        doc.text(String(a), cx+cols[4].w/2, y+1, { align:'center' }); cx += cols[4].w;
        doc.setTextColor(...vstClr);
        doc.text(vstTxt, cx+cols[5].w/2, y+1, { align:'center' });
        y += rowH;
        doc.setDrawColor(7,21,41); doc.setLineWidth(0.1); doc.line(MARGIN,y-0.5,PW-MARGIN,y-0.5);
      });

      y += 4;
      const totalArea = (l.rooms||[]).reduce((s,r)=>s+(r.area||(r.width||r.w||0)*(r.height||r.h||0)),0);
      doc.setFillColor(4,15,31); doc.rect(MARGIN,y-3.5,INNER,rowH,'F');
      doc.setFont('helvetica','bold'); doc.setFontSize(7); doc.setTextColor(232,192,96);
      doc.text('TOTAL', MARGIN+2, y+1);
      cx = MARGIN+5+cols[0].w-3+cols[1].w+cols[2].w+cols[3].w;
      doc.text(String(Math.round(totalArea)), cx+cols[4].w/2, y+1, { align:'center' });
    }

    _writePageFooter(doc, 2);
  }

  function _writePageFooter(doc, pageNum) {
    const l = window.activeLayout;
    doc.setFillColor(2,11,24); doc.rect(0,PH-10,PW,10,'F');
    doc.setFont('helvetica','normal'); doc.setFontSize(6); doc.setTextColor(71,85,105);
    doc.text(`IntelliPlan·3D  ·  GA + Vastu Engine  ·  Generated ${new Date().toLocaleDateString('en-IN')}`, MARGIN, PH-4);
    doc.setTextColor(100,116,139); doc.text(`Page ${pageNum}`, PW-MARGIN, PH-4, { align:'right' });
    doc.text(`ID: ${l.layout_id||'demo'}`, PW/2, PH-4, { align:'center' });
  }

  /* ═══ CANVAS RENDERERS ══════════════════════════════════════ */
  async function _renderFloorPlanCanvas(cw, ch, layout) {
    const canvas = document.createElement('canvas');
    canvas.width = cw; canvas.height = ch;
    const ctx  = canvas.getContext('2d');
    const plot = layout.plot || { width:40, height:60 };
    const sc   = Math.min((cw-24)/plot.width, (ch-24)/plot.height);
    const ox   = Math.round((cw - plot.width*sc) / 2);
    const oy   = Math.round((ch - plot.height*sc) / 2);

    ctx.fillStyle='#020b18'; ctx.fillRect(0,0,cw,ch);
    ctx.strokeStyle='rgba(56,189,248,0.04)'; ctx.lineWidth=0.6;
    for(let x=0;x<cw;x+=20){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,ch);ctx.stroke();}
    for(let y=0;y<ch;y+=20){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(cw,y);ctx.stroke();}

    ctx.strokeStyle='rgba(56,189,248,0.3)'; ctx.lineWidth=1.5;
    ctx.strokeRect(ox,oy,plot.width*sc,plot.height*sc);

    [[ox,oy],[ox+plot.width*sc,oy],[ox,oy+plot.height*sc],[ox+plot.width*sc,oy+plot.height*sc]].forEach(([px,py],i)=>{
      const dx=i%2===0?1:-1,dy=i<2?1:-1,cs=14;
      ctx.strokeStyle='rgba(201,150,42,0.7)'; ctx.lineWidth=1.5;
      ctx.beginPath();ctx.moveTo(px,py);ctx.lineTo(px+dx*cs,py);ctx.stroke();
      ctx.beginPath();ctx.moveTo(px,py);ctx.lineTo(px,py+dy*cs);ctx.stroke();
    });

    layout.rooms.forEach(r=>{
      const pal=PAL[r.type]||DEF_C;
      const rx=ox+r.x*sc,ry=oy+r.y*sc;
      const rw=(r.width||r.w)*sc,rh=(r.height||r.h)*sc;
      const grad=ctx.createLinearGradient(rx,ry,rx+rw,ry+rh);
      grad.addColorStop(0,`rgba(${pal.r},${pal.g},${pal.b},0.55)`);
      grad.addColorStop(1,`rgba(${pal.r},${pal.g},${pal.b},0.28)`);
      ctx.fillStyle=grad; _rr(ctx,rx,ry,rw,rh,3); ctx.fill();
      ctx.strokeStyle=`rgba(${pal.r},${pal.g},${pal.b},0.85)`; ctx.lineWidth=1.2;
      _rr(ctx,rx,ry,rw,rh,3); ctx.stroke();
      if(rw>36&&rh>20){
        const fs=Math.max(9,Math.min(14,rw/7));
        ctx.fillStyle='#e2e8f0'; ctx.font=`600 ${fs}px "JetBrains Mono",monospace`;
        ctx.textAlign='center'; ctx.textBaseline='middle';
        ctx.fillText(r.label,rx+rw/2,ry+rh/2-(rh>32?5:0));
      }
      if(rh>32&&rw>50){
        const dfs=Math.max(7,Math.min(10,rw/9));
        ctx.fillStyle='rgba(148,163,184,0.6)'; ctx.font=`300 ${dfs}px "JetBrains Mono",monospace`;
        ctx.fillText(`${(r.width||r.w).toFixed(0)}×${(r.height||r.h).toFixed(0)} ft`,rx+rw/2,ry+rh/2+9);
      }
    });

    _drawCompassCanvas(ctx,cw-40,oy+40,28,plot.facing||'East');

    const barW=80,barFt=Math.round(barW/sc);
    ctx.strokeStyle='rgba(201,150,42,0.55)'; ctx.lineWidth=1.2;
    ctx.beginPath();ctx.moveTo(ox,ch-14);ctx.lineTo(ox+barW,ch-14);ctx.stroke();
    [ox,ox+barW].forEach(bx=>{ctx.beginPath();ctx.moveTo(bx,ch-18);ctx.lineTo(bx,ch-10);ctx.stroke();});
    ctx.fillStyle='rgba(201,150,42,0.75)';
    ctx.font='9px "JetBrains Mono",monospace';ctx.textAlign='center';
    ctx.fillText(`${barFt} ft`,ox+barW/2,ch-4);
    ctx.fillStyle='rgba(56,189,248,0.5)'; ctx.textAlign='left';
    ctx.fillText(`FLOOR PLAN · ${plot.bhk_type||''} · ${plot.width}×${plot.height} ft`,ox,oy-6);

    return canvas;
  }

  function _renderScoreRingCanvas(size, score) {
    const canvas=document.createElement('canvas');
    canvas.width=canvas.height=size;
    const ctx=canvas.getContext('2d');
    const cx=size/2,cy=size/2,r=size*0.4;
    ctx.fillStyle='#020b18'; ctx.fillRect(0,0,size,size);
    ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);
    ctx.strokeStyle='rgba(7,21,41,0.9)';ctx.lineWidth=size*0.08;ctx.stroke();
    const pct=score/100;
    const grad=ctx.createLinearGradient(0,0,size,0);
    grad.addColorStop(0,'#38bdf8');grad.addColorStop(1,'#c9962a');
    ctx.beginPath();ctx.arc(cx,cy,r,-Math.PI/2,-Math.PI/2+Math.PI*2*pct);
    ctx.strokeStyle=grad;ctx.lineWidth=size*0.08;ctx.lineCap='round';ctx.stroke();
    ctx.fillStyle='#ffffff';ctx.font=`bold ${size*0.25}px helvetica`;
    ctx.textAlign='center';ctx.textBaseline='middle';
    ctx.fillText(String(Math.round(score)),cx,cy-size*0.04);
    ctx.fillStyle='#38bdf8';ctx.font=`${size*0.09}px "JetBrains Mono"`;
    ctx.fillText('/ 100',cx,cy+size*0.13);
    ctx.fillStyle='rgba(100,116,139,0.7)';ctx.font=`${size*0.07}px "JetBrains Mono"`;
    ctx.fillText('VASTU SCORE',cx,cy+size*0.28);
    return canvas;
  }

  async function _renderPage1Canvas(scale) {
    const W=Math.round(PW*scale*3.78*0.38);
    const H=Math.round(PH*scale*3.78*0.38);
    const canvas=document.createElement('canvas');
    canvas.width=W;canvas.height=H;
    canvas.style.width=W+'px';canvas.style.height=H+'px';
    const ctx=canvas.getContext('2d');
    const l=window.activeLayout,p=l.plot||{};
    ctx.fillStyle='#020b18';ctx.fillRect(0,0,W,H);
    ctx.fillStyle='#040f1f';ctx.fillRect(0,0,W,H*0.09);
    ctx.fillStyle='#e8c060';ctx.font=`bold ${W*0.065}px helvetica`;
    ctx.fillText('IntelliPlan·3D',W*0.04,H*0.06);
    const fpH=H*0.5;
    const fpCanvas=await _renderFloorPlanCanvas(W-8,fpH,l);
    ctx.drawImage(fpCanvas,4,H*0.11,W-8,fpH);
    const kpis=[`${p.bhk_type}`,`${p.facing} Facing`,`Vastu ${Math.round(l.vastu_score||0)}%`,`${l.rooms?.length} Rooms`];
    const kw=(W-8)/kpis.length;
    kpis.forEach((k,i)=>{
      ctx.fillStyle='rgba(4,15,31,0.9)';ctx.fillRect(4+i*kw,H*0.63,kw-2,H*0.08);
      ctx.fillStyle='#ffffff';ctx.font=`bold ${W*0.045}px helvetica`;ctx.textAlign='center';
      ctx.fillText(k,4+i*kw+kw/2,H*0.685);
    });
    ctx.textAlign='left';
    (l.vastu_rules||[]).slice(0,5).forEach((r,i)=>{
      const pct=r.weight>0?r.earned/r.weight:0;
      const by=H*0.74+i*H*0.044;
      ctx.fillStyle='#071529';ctx.fillRect(4,by,W-8,H*0.036);
      const [cr,cg,cb]=pct>=0.8?[74,222,128]:pct>=0.5?[251,191,36]:[248,113,113];
      ctx.fillStyle=`rgb(${cr},${cg},${cb})`;ctx.fillRect(4,by,(W-8)*pct,H*0.036);
      ctx.fillStyle='#94a3b8';ctx.font=`${W*0.032}px monospace`;ctx.fillText(r.label,6,by+H*0.028);
    });
    return canvas;
  }

  async function _renderPage2Canvas(scale) {
    const W=Math.round(PW*scale*3.78*0.38);
    const H=Math.round(PH*scale*3.78*0.38);
    const canvas=document.createElement('canvas');
    canvas.width=W;canvas.height=H;
    canvas.style.width=W+'px';canvas.style.height=H+'px';
    const ctx=canvas.getContext('2d');
    const l=window.activeLayout;
    ctx.fillStyle='#020b18';ctx.fillRect(0,0,W,H);
    ctx.fillStyle='#040f1f';ctx.fillRect(0,0,W,H*0.07);
    ctx.fillStyle='#d9aa3f';ctx.font=`bold ${W*0.055}px helvetica`;
    ctx.fillText('Layout Analysis',W*0.04,H*0.05);
    const rooms=l.rooms||[];
    const rowH=H*0.055;
    rooms.slice(0,12).forEach((r,i)=>{
      const pal=PAL[r.type]||DEF_C;
      const ry=H*0.1+i*rowH;
      if(i%2===0){ctx.fillStyle='rgba(4,15,31,0.7)';ctx.fillRect(0,ry,W,rowH);}
      ctx.fillStyle=`rgba(${pal.r},${pal.g},${pal.b},0.8)`;ctx.fillRect(4,ry+rowH*0.2,3,rowH*0.6);
      ctx.fillStyle='#cbd5e1';ctx.font=`${W*0.038}px monospace`;ctx.textAlign='left';
      const a=Math.round(r.area||(r.width||r.w||0)*(r.height||r.h||0));
      ctx.fillText(`${r.label}`,10,ry+rowH*0.65);
      ctx.fillStyle='#d9aa3f';ctx.fillText(`${a} sqft`,W*0.75,ry+rowH*0.65);
    });
    return canvas;
  }

  /* ── Canvas helpers ──────────────────────────────────────── */
  function _rr(ctx,x,y,w,h,r){
    ctx.beginPath();
    ctx.moveTo(x+r,y);ctx.lineTo(x+w-r,y);ctx.arcTo(x+w,y,x+w,y+r,r);
    ctx.lineTo(x+w,y+h-r);ctx.arcTo(x+w,y+h,x+w-r,y+h,r);
    ctx.lineTo(x+r,y+h);ctx.arcTo(x,y+h,x,y+h-r,r);
    ctx.lineTo(x,y+r);ctx.arcTo(x,y,x+r,y,r);ctx.closePath();
  }

  function _drawCompassCanvas(ctx,cx,cy,r,facing){
    const degs={North:0,East:90,South:180,West:270};
    const a=(degs[facing]||0)*Math.PI/180;
    ctx.save();ctx.translate(cx,cy);
    ctx.beginPath();ctx.arc(0,0,r,0,Math.PI*2);
    ctx.fillStyle='rgba(2,11,24,0.88)';ctx.fill();
    ctx.strokeStyle='rgba(56,189,248,0.25)';ctx.lineWidth=1;ctx.stroke();
    ['N','E','S','W'].forEach((d,i)=>{
      const da=i*Math.PI/2;
      ctx.fillStyle=d==='N'?'#f87171':'rgba(148,163,184,0.5)';
      ctx.font=`bold ${r*0.3}px "JetBrains Mono"`;ctx.textAlign='center';ctx.textBaseline='middle';
      ctx.fillText(d,Math.sin(da)*r*0.65,-Math.cos(da)*r*0.65);
    });
    ctx.rotate(a);
    ctx.fillStyle='#f87171';
    ctx.beginPath();ctx.moveTo(0,-r*0.55);ctx.lineTo(3,0);ctx.lineTo(0,5);ctx.lineTo(-3,0);ctx.closePath();ctx.fill();
    ctx.fillStyle='rgba(148,163,184,0.35)';
    ctx.beginPath();ctx.moveTo(0,r*0.55);ctx.lineTo(2.5,0);ctx.lineTo(0,-5);ctx.lineTo(-2.5,0);ctx.closePath();ctx.fill();
    ctx.restore();
  }

  /* ═══ UTILITIES ═════════════════════════════════════════════ */
  function _ensureJsPDF() {
    return new Promise((resolve,reject)=>{
      if(window.jspdf){resolve();return;}
      const s=document.createElement('script');
      s.src=JSPDF_CDN;s.onload=()=>resolve();s.onerror=()=>reject(new Error('Failed to load jsPDF'));
      document.head.appendChild(s);
    });
  }

  function _download(url,filename){
    const a=document.createElement('a');a.href=url;a.download=filename;
    document.body.appendChild(a);a.click();document.body.removeChild(a);
    setTimeout(()=>URL.revokeObjectURL(url),5000);
  }

  function showToast(msg,icon='✦'){if(typeof window.showToast==='function')window.showToast(msg,icon);}

  return { open, close, exportPDF, _doExportFromModal };
})();