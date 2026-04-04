# ═══════════════════════════════════════════════════════════════
# services/export_service.py
# PDF & data export for IntelliPlan·3D
#
# Produces:
#   ▸ PDF report (A4) via ReportLab
#       Page 1 — Cover: branding, metadata, 2-D floor plan drawing,
#                Vastu score ring, compass rose, KPI strip
#       Page 2 — Analysis: Vastu rule breakdown bars, room table
#   ▸ JSON export — full layout dict (same schema as API response)
#   ▸ SVG floor plan — vector drawing for embedding
# ═══════════════════════════════════════════════════════════════

import io
import json
import math
from datetime import datetime
from typing import Optional

import os, sys
_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from utils.logger  import get_logger
from geometry.layout import Layout

logger = get_logger(__name__)

# ── ReportLab imports (graceful if not installed) ────────────────
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units     import mm
    from reportlab.lib           import colors
    from reportlab.pdfgen        import canvas as rl_canvas
    from reportlab.graphics      import renderPDF
    _REPORTLAB = True
except ImportError:
    _REPORTLAB = False
    logger.warning("ReportLab not installed — PDF export unavailable. "
                   "Run:  pip install reportlab")

# ── Page geometry (A4 in mm → points via mm helper) ──────────────
PAGE_W, PAGE_H = A4 if _REPORTLAB else (595.0, 842.0)
MARGIN         = 18 * mm if _REPORTLAB else 51.0
INNER_W        = PAGE_W - 2 * MARGIN

# ── Brand colours ────────────────────────────────────────────────
C_DARK    = (0.008, 0.043, 0.094)   # #020b18  deep navy
C_SURFACE = (0.016, 0.059, 0.122)   # #040f1f  card surface
C_CYAN    = (0.220, 0.741, 0.984)   # #38bdf8
C_GOLD    = (0.788, 0.588, 0.165)   # #c9962a
C_WHITE   = (1.0,   1.0,   1.0)
C_MUTED   = (0.580, 0.639, 0.722)   # #94a3b8
C_FAINT   = (0.392, 0.455, 0.545)   # #64748b

# ── Room colours (RGB 0-1, matches frontend COLORS palette) ─────
ROOM_COLORS = {
    "entrance":       (0.925, 0.282, 0.600),
    "living":         (0.231, 0.510, 0.965),
    "dining":         (0.918, 0.702, 0.031),
    "kitchen":        (0.961, 0.620, 0.043),
    "master_bedroom": (0.545, 0.361, 0.965),
    "bedroom":        (0.388, 0.400, 0.945),
    "bathroom":       (0.078, 0.722, 0.651),
    "toilet":         (0.024, 0.714, 0.831),
    "balcony":        (0.133, 0.773, 0.369),
    "pooja":          (0.980, 0.451, 0.086),
    "store":          (0.392, 0.455, 0.545),
    "utility":        (0.580, 0.639, 0.722),
}
C_ROOM_DEF = (0.392, 0.455, 0.545)

# ── Vastu status colours ─────────────────────────────────────────
STATUS_COLORS = {
    "compliant": (0.290, 0.871, 0.502),   # green
    "partial":   (0.984, 0.749, 0.141),   # amber
    "violation": (0.973, 0.443, 0.424),   # red
    "missing":   (0.392, 0.455, 0.545),   # gray
}


# ════════════════════════════════════════════════════════════════
#  EXPORT SERVICE
# ════════════════════════════════════════════════════════════════

class ExportService:
    """
    Generates PDF reports and JSON/SVG exports for floor plan layouts.

    Usage:
        svc = ExportService()
        pdf_bytes = svc.export_pdf(layout)          # → bytes
        json_str  = svc.export_json(layout)         # → str
        svg_str   = svc.export_svg(layout)          # → str
    """

    # ── PDF ───────────────────────────────────────────────────────

    def export_pdf(self, layout: Layout) -> bytes:
        """
        Generate a full A4 PDF report for the given layout.
        Returns raw PDF bytes suitable for Flask send_file().
        Raises RuntimeError if ReportLab is not installed.
        """
        if not _REPORTLAB:
            raise RuntimeError(
                "ReportLab is required for PDF export. "
                "Install with:  pip install reportlab"
            )

        buf = io.BytesIO()
        c   = rl_canvas.Canvas(buf, pagesize=A4)
        c.setTitle(f"IntelliPlan·3D — Floor Plan Report")
        c.setAuthor("IntelliPlan·3D — GA + Vastu Engine")

        self._draw_page1(c, layout)
        c.showPage()
        self._draw_page2(c, layout)
        c.showPage()

        c.save()
        buf.seek(0)
        logger.info("PDF generated | %s | %.0f×%.0f ft | vastu=%.1f%%",
                    layout.layout_id, layout.plot_width,
                    layout.plot_height, layout.vastu_score)
        return buf.read()

    # ── JSON ──────────────────────────────────────────────────────

    def export_json(self, layout: Layout, indent: int = 2) -> str:
        """
        Return the full layout as a pretty-printed JSON string.
        Identical schema to the API response.
        """
        return json.dumps(layout.to_dict(), indent=indent, default=str)

    # ── SVG ───────────────────────────────────────────────────────

    def export_svg(self, layout: Layout,
                   width: int = 800, height: int = 600) -> str:
        """
        Generate a standalone SVG floor plan (dark theme, blueprint style).
        Returns an SVG string embeddable in HTML or saveable as .svg.
        """
        plot  = layout.plot_width
        ploth = layout.plot_height
        pad   = 40
        scale = min((width - pad * 2) / plot, (height - pad * 2) / ploth)
        ox    = pad + (width  - pad * 2 - plot  * scale) / 2
        oy    = pad + (height - pad * 2 - ploth * scale) / 2

        lines = [
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">',
            # Background
            f'  <rect width="{width}" height="{height}" fill="#020b18"/>',
            # Grid lines
            *self._svg_grid(ox, oy, plot, ploth, scale),
            # Plot boundary
            f'  <rect x="{ox:.1f}" y="{oy:.1f}" '
            f'width="{plot*scale:.1f}" height="{ploth*scale:.1f}" '
            f'fill="none" stroke="#38bdf8" stroke-width="1.5" '
            f'stroke-opacity="0.4"/>',
        ]

        # Rooms
        for room in layout.rooms:
            rw   = (room.width  or room.width)  * scale
            rh   = (room.height or room.height) * scale
            rx   = ox + room.x * scale
            ry   = oy + room.y * scale
            col  = ROOM_COLORS.get(room.type, C_ROOM_DEF)
            fill = f"rgba({int(col[0]*255)},{int(col[1]*255)},{int(col[2]*255)},0.45)"
            stroke = f"rgb({int(col[0]*255)},{int(col[1]*255)},{int(col[2]*255)})"

            lines.append(
                f'  <rect x="{rx:.1f}" y="{ry:.1f}" '
                f'width="{rw:.1f}" height="{rh:.1f}" rx="3" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="1"/>'
            )
            # Room label (if large enough)
            if rw > 40 and rh > 22:
                fs = max(9, min(14, int(rw / 8)))
                lines.append(
                    f'  <text x="{rx + rw/2:.1f}" y="{ry + rh/2:.1f}" '
                    f'text-anchor="middle" dominant-baseline="middle" '
                    f'fill="#e2e8f0" font-family="monospace" '
                    f'font-size="{fs}px" font-weight="500">'
                    f'{room.label}</text>'
                )
                if rh > 38 and rw > 55:
                    dim = f'{room.width:.0f}×{room.height:.0f} ft'
                    lines.append(
                        f'  <text x="{rx + rw/2:.1f}" y="{ry + rh/2 + fs + 3:.1f}" '
                        f'text-anchor="middle" dominant-baseline="middle" '
                        f'fill="#64748b" font-family="monospace" '
                        f'font-size="{max(8, fs-3)}px">'
                        f'{dim}</text>'
                    )

        # Compass
        compass_x = ox + plot * scale + 12
        compass_y = oy + 30
        if compass_x + 36 < width:
            lines += self._svg_compass(compass_x, compass_y, 22, layout.facing)

        lines.append('</svg>')
        return "\n".join(lines)

    # ════════════════════════════════════════════════════════════
    #  PAGE 1 — Cover + Floor Plan
    # ════════════════════════════════════════════════════════════

    def _draw_page1(self, c, layout: Layout) -> None:
        p = layout.plot_width
        q = layout.plot_height

        # ── Dark background ──────────────────────────────────────
        self._fill_rect(c, 0, 0, PAGE_W, PAGE_H, C_DARK)

        # ── Header strip ────────────────────────────────────────
        self._fill_rect(c, 0, PAGE_H - 28*mm, PAGE_W, 28*mm, C_SURFACE)

        # Logo text
        c.setFont("Helvetica-Bold", 18)
        self._set_fill(c, C_GOLD);  c.drawString(MARGIN, PAGE_H - 16*mm, "IntelliPlan")
        self._set_fill(c, C_CYAN);  c.drawString(MARGIN + 80, PAGE_H - 16*mm, "·3D")

        # Tagline
        c.setFont("Helvetica", 7)
        self._set_fill(c, C_FAINT)
        c.drawString(MARGIN, PAGE_H - 22*mm, "AI FLOOR PLAN STUDIO  ·  GA + VASTU ENGINE")

        # Date (right-aligned)
        dt = datetime.now().strftime("%d %b %Y  %H:%M")
        c.setFont("Helvetica", 7)
        self._set_fill(c, C_FAINT)
        c.drawRightString(PAGE_W - MARGIN, PAGE_H - 16*mm, dt)

        # ── Title block ──────────────────────────────────────────
        y = PAGE_H - 38*mm
        c.setFont("Helvetica-Bold", 20)
        self._set_fill(c, C_WHITE)
        c.drawString(MARGIN, y, "Floor Plan Report")
        y -= 7*mm

        subtitle = (
            f"{layout.bhk_type}  ·  "
            f"{p:.0f}×{q:.0f} ft  ·  "
            f"{layout.facing} facing  ·  "
            f"Vastu Score: {layout.vastu_score:.0f}%"
        )
        c.setFont("Helvetica", 9)
        self._set_fill(c, C_MUTED)
        c.drawString(MARGIN, y, subtitle)
        y -= 4*mm

        # Gold rule
        self._set_stroke(c, C_GOLD, 0.5)
        c.line(MARGIN, y, PAGE_W - MARGIN, y)
        y -= 5*mm

        # ── KPI strip ────────────────────────────────────────────
        kpis = [
            ("Plot",        f"{p:.0f}×{q:.0f} ft"),
            ("BHK",         layout.bhk_type),
            ("Facing",      layout.facing),
            ("Vastu",       f"{layout.vastu_score:.0f}%"),
            ("Rooms",       str(len(layout.rooms))),
            ("Area",        f"{int(p*q):,} sqft"),
            ("Util",        f"{layout.space_util:.0f}%"),
            ("Fitness",     f"{layout.fitness:.3f}"),
        ]
        kpi_w = INNER_W / len(kpis)
        kpi_h = 10*mm
        for i, (lbl, val) in enumerate(kpis):
            kx = MARGIN + i * kpi_w
            self._fill_rect(c, kx, y - kpi_h, kpi_w - 1, kpi_h, C_SURFACE)
            c.setFont("Helvetica-Bold", 9)
            self._set_fill(c, C_WHITE)
            c.drawCentredString(kx + kpi_w/2, y - kpi_h/2 + 1.5*mm, val)
            c.setFont("Helvetica", 6)
            self._set_fill(c, C_FAINT)
            c.drawCentredString(kx + kpi_w/2, y - kpi_h + 2*mm, lbl.upper())
        y -= kpi_h + 5*mm

        # ── 2-D Floor Plan ───────────────────────────────────────
        c.setFont("Helvetica-Bold", 7)
        self._set_fill(c, C_CYAN)
        c.drawString(MARGIN, y, "FLOOR PLAN  —  2D BLUEPRINT")
        y -= 3.5*mm

        # Determine plan height — leave room for Vastu bars below
        plan_h = 85*mm
        self._draw_floor_plan(c, layout, MARGIN, y - plan_h, INNER_W, plan_h)
        y -= plan_h + 5*mm

        # ── Vastu score ring + bars ──────────────────────────────
        ring_size = 32*mm
        ring_x    = PAGE_W - MARGIN - ring_size

        # Score ring
        self._draw_score_ring(c, ring_x + ring_size/2, y - ring_size/2,
                              ring_size/2, layout.vastu_score)

        # Vastu bars
        c.setFont("Helvetica-Bold", 7)
        self._set_fill(c, C_CYAN)
        c.drawString(MARGIN, y, "VASTU COMPLIANCE")
        y -= 4*mm

        bar_w = ring_x - MARGIN - 8*mm
        rules = layout.vastu_rules or []
        for rule in rules[:8]:
            pct     = (rule["earned"] / rule["weight"]) if rule["weight"] > 0 else 0
            col     = STATUS_COLORS.get(rule["status"], STATUS_COLORS["missing"])
            row_h   = 5.5*mm

            # Label
            c.setFont("Helvetica", 6.5)
            self._set_fill(c, C_MUTED)
            c.drawString(MARGIN, y - row_h/2 + 1.5*mm, rule["label"])

            # Track
            track_x = MARGIN + 44*mm
            track_w = bar_w - 44*mm
            track_y = y - row_h * 0.65
            self._fill_rect(c, track_x, track_y, track_w, 2.8*mm, C_SURFACE)

            # Fill
            if pct > 0:
                self._fill_rect(c, track_x, track_y, track_w * pct, 2.8*mm, col)

            # % label
            c.setFont("Helvetica-Bold", 6)
            self._set_fill_rgb(c, *col)
            c.drawString(track_x + track_w + 2*mm,
                         y - row_h/2 + 1.5*mm,
                         f"{int(pct*100)}%")
            y -= row_h

        # ── Page footer ──────────────────────────────────────────
        self._draw_page_footer(c, layout, 1)

    # ════════════════════════════════════════════════════════════
    #  PAGE 2 — Analysis Report
    # ════════════════════════════════════════════════════════════

    def _draw_page2(self, c, layout: Layout) -> None:
        # Dark background
        self._fill_rect(c, 0, 0, PAGE_W, PAGE_H, C_DARK)

        # Header strip
        self._fill_rect(c, 0, PAGE_H - 18*mm, PAGE_W, 18*mm, C_SURFACE)
        c.setFont("Helvetica-Bold", 10)
        self._set_fill(c, C_GOLD)
        c.drawString(MARGIN, PAGE_H - 10*mm, "IntelliPlan·3D")
        c.setFont("Helvetica", 7)
        self._set_fill(c, C_FAINT)
        c.drawRightString(PAGE_W - MARGIN, PAGE_H - 10*mm, "ANALYSIS REPORT")

        y = PAGE_H - 26*mm

        # Section title
        c.setFont("Helvetica-Bold", 14)
        self._set_fill(c, C_WHITE)
        c.drawString(MARGIN, y, "Layout Analysis")
        y -= 4*mm
        self._set_stroke(c, C_GOLD, 0.4)
        c.line(MARGIN, y, PAGE_W - MARGIN, y)
        y -= 7*mm

        # ── Full Vastu breakdown ─────────────────────────────────
        c.setFont("Helvetica-Bold", 7.5)
        self._set_fill(c, C_CYAN)
        c.drawString(MARGIN, y, "VASTU COMPLIANCE BREAKDOWN")
        y -= 4*mm

        rules = layout.vastu_rules or []
        for rule in rules:
            pct  = (rule["earned"] / rule["weight"]) if rule["weight"] > 0 else 0
            col  = STATUS_COLORS.get(rule["status"], STATUS_COLORS["missing"])
            row_h = 7.5*mm

            # Row background
            self._fill_rect(c, MARGIN, y - row_h + 1.5*mm,
                            INNER_W, row_h - 1*mm, C_SURFACE)

            # Label
            c.setFont("Helvetica", 7)
            self._set_fill(c, (0.796, 0.835, 0.898))
            c.drawString(MARGIN + 2*mm, y - row_h/2 + 1.5*mm, rule["label"])

            # Description
            c.setFont("Helvetica", 6)
            self._set_fill(c, C_FAINT)
            c.drawString(MARGIN + 42*mm, y - row_h/2 + 1.5*mm,
                         rule.get("description", ""))

            # Bar
            track_x = MARGIN + 82*mm
            track_w = 48*mm
            track_y = y - row_h * 0.6
            self._fill_rect(c, track_x, track_y, track_w, 3*mm, (0.027, 0.082, 0.161))
            if pct > 0:
                self._fill_rect(c, track_x, track_y, track_w * pct, 3*mm, col)

            # % and status
            c.setFont("Helvetica-Bold", 6.5)
            self._set_fill_rgb(c, *col)
            c.drawString(track_x + track_w + 2*mm, y - row_h/2 + 1.5*mm,
                         f"{int(pct*100)}%")

            status_txt = {
                "compliant": "✓ Compliant",
                "partial":   "~ Partial",
                "violation": "✗ Violation",
                "missing":   "— Missing",
            }.get(rule["status"], rule["status"])
            c.setFont("Helvetica", 6)
            self._set_fill_rgb(c, *col)
            c.drawRightString(PAGE_W - MARGIN, y - row_h/2 + 1.5*mm, status_txt)

            y -= row_h

        y -= 4*mm

        # ── Room specifications table ────────────────────────────
        c.setFont("Helvetica-Bold", 7.5)
        self._set_fill(c, C_CYAN)
        c.drawString(MARGIN, y, "ROOM SPECIFICATIONS")
        y -= 4*mm

        # Table header
        cols = [
            ("Room Name",   38*mm),
            ("Type",        28*mm),
            ("Width (ft)",  20*mm),
            ("Depth (ft)",  20*mm),
            ("Area (sqft)", 20*mm),
            ("Vastu",       15*mm),
        ]
        row_h = 6.5*mm
        self._fill_rect(c, MARGIN, y - row_h + 2*mm, INNER_W, row_h - 1*mm, C_SURFACE)
        cx = MARGIN + 2*mm
        for lbl, w in cols:
            c.setFont("Helvetica-Bold", 6)
            self._set_fill(c, C_FAINT)
            c.drawString(cx, y - row_h/2 + 2*mm, lbl.upper())
            cx += w
        y -= row_h

        # Divider
        self._set_stroke(c, C_CYAN, 0.2)
        c.line(MARGIN, y + 1*mm, PAGE_W - MARGIN, y + 1*mm)

        # Data rows
        for i, room in enumerate(layout.rooms):
            rw   = room.width
            rh_v = room.height
            area = room.area

            # Matching Vastu rule
            rule_match = next(
                (r for r in rules
                 if room.type.split("_")[0].lower() in r["label"].lower()),
                None,
            )
            vstu_txt = {
                "compliant": "✓",
                "partial":   "~",
                "violation": "✗",
                "missing":   "—",
            }.get(rule_match["status"] if rule_match else "missing", "—")
            vstu_col = STATUS_COLORS.get(
                rule_match["status"] if rule_match else "missing",
                STATUS_COLORS["missing"],
            )

            if i % 2 == 0:
                self._fill_rect(c, MARGIN, y - row_h + 2*mm,
                                INNER_W, row_h - 1*mm, C_SURFACE)

            # Colour swatch
            room_col = ROOM_COLORS.get(room.type, C_ROOM_DEF)
            self._fill_rect_rgb(c,
                                MARGIN + 1*mm, y - row_h/2,
                                2*mm, 3.5*mm, *room_col)

            cx = MARGIN + 4*mm
            # Room name
            c.setFont("Helvetica", 7); self._set_fill(c, (0.796, 0.835, 0.898))
            c.drawString(cx, y - row_h/2 + 1.5*mm, room.label)
            cx += cols[0][1] - 2*mm

            # Type
            c.setFont("Helvetica", 6); self._set_fill(c, C_FAINT)
            c.drawString(cx, y - row_h/2 + 1.5*mm, room.type.replace("_"," "))
            cx += cols[1][1]

            # Width, depth
            c.setFont("Helvetica", 7); self._set_fill(c, (0.796, 0.835, 0.898))
            c.drawCentredString(cx + cols[2][1]/2, y - row_h/2 + 1.5*mm, f"{rw:.1f}")
            cx += cols[2][1]
            c.drawCentredString(cx + cols[3][1]/2, y - row_h/2 + 1.5*mm, f"{rh_v:.1f}")
            cx += cols[3][1]

            # Area (gold)
            c.setFont("Helvetica-Bold", 7); self._set_fill(c, C_GOLD)
            c.drawCentredString(cx + cols[4][1]/2, y - row_h/2 + 1.5*mm, str(int(area)))
            cx += cols[4][1]

            # Vastu status
            c.setFont("Helvetica-Bold", 7); self._set_fill_rgb(c, *vstu_col)
            c.drawCentredString(cx + cols[5][1]/2, y - row_h/2 + 1.5*mm, vstu_txt)

            # Row divider (subtle)
            self._set_stroke(c, C_SURFACE, 0.1)
            c.line(MARGIN, y - row_h + 2*mm, PAGE_W - MARGIN, y - row_h + 2*mm)

            y -= row_h

        # Total row
        total_area = layout.total_room_area
        y -= 1*mm
        self._fill_rect(c, MARGIN, y - row_h + 2*mm, INNER_W, row_h - 1*mm, C_SURFACE)
        c.setFont("Helvetica-Bold", 7)
        self._set_fill(c, C_GOLD)
        c.drawString(MARGIN + 2*mm, y - row_h/2 + 1.5*mm, "TOTAL")
        cx = MARGIN + 4*mm + cols[0][1] - 2*mm + cols[1][1] + cols[2][1] + cols[3][1]
        c.drawCentredString(cx + cols[4][1]/2, y - row_h/2 + 1.5*mm,
                            str(int(total_area)))

        # ── Page footer ──────────────────────────────────────────
        self._draw_page_footer(c, layout, 2)

    # ════════════════════════════════════════════════════════════
    #  DRAWING HELPERS
    # ════════════════════════════════════════════════════════════

    def _draw_floor_plan(self, c, layout: Layout,
                         x: float, y: float,
                         w: float, h: float) -> None:
        """Draw the 2-D floor plan inside the bounding box (x, y, w, h)."""
        plot_w = layout.plot_width
        plot_h = layout.plot_height

        # Scale to fit
        scale  = min(w / plot_w, h / plot_h)
        ox     = x + (w - plot_w * scale) / 2
        oy     = y + (h - plot_h * scale) / 2

        # Plan background + grid
        self._fill_rect(c, ox, oy, plot_w * scale, plot_h * scale, C_SURFACE)

        # Grid lines (subtle)
        c.saveState()
        c.setStrokeColorRGB(0.022, 0.059, 0.122)
        c.setLineWidth(0.3)
        grid_step = 5 * scale
        gx = ox
        while gx <= ox + plot_w * scale:
            c.line(gx, oy, gx, oy + plot_h * scale)
            gx += grid_step
        gy = oy
        while gy <= oy + plot_h * scale:
            c.line(ox, gy, ox + plot_w * scale, gy)
            gy += grid_step
        c.restoreState()

        # Plot boundary
        c.saveState()
        c.setStrokeColorRGB(*C_CYAN); c.setLineWidth(0.8)
        c.rect(ox, oy, plot_w * scale, plot_h * scale, stroke=1, fill=0)
        c.restoreState()

        # Corner markers (gold)
        cm = 3 * scale
        for cx2, cy2 in [(ox, oy), (ox + plot_w*scale, oy),
                         (ox, oy + plot_h*scale), (ox + plot_w*scale, oy + plot_h*scale)]:
            sx = 1 if cx2 == ox else -1
            sy = 1 if cy2 == oy else -1
            c.saveState()
            c.setStrokeColorRGB(*C_GOLD); c.setLineWidth(1.0)
            c.line(cx2, cy2, cx2 + sx * cm, cy2)
            c.line(cx2, cy2, cx2, cy2 + sy * cm)
            c.restoreState()

        # Rooms
        for room in layout.rooms:
            rw    = room.width  * scale
            rh    = room.height * scale
            rx    = ox + room.x * scale
            ry    = oy + room.y * scale
            col   = ROOM_COLORS.get(room.type, C_ROOM_DEF)
            fill  = tuple(v * 0.6 for v in col)  # slightly darker fill

            c.saveState()
            c.setFillColorRGB(*fill, alpha=0.55 if hasattr(c, '_alpha') else 0.0)
            c.setFillColorRGB(*fill)
            c.setStrokeColorRGB(*col)
            c.setLineWidth(0.7)
            c.rect(rx, ry, rw, rh, stroke=1, fill=1)

            # Room label
            if rw > 20 and rh > 12:
                fs = max(4, min(8, int(rw / 10)))
                c.setFillColorRGB(*C_WHITE)
                c.setFont("Helvetica-Bold", fs)
                c.drawCentredString(rx + rw/2, ry + rh/2 + fs*0.2, room.label)
            if rh > 22 and rw > 30:
                fs2 = max(4, min(6, int(rw / 14)))
                c.setFillColorRGB(*C_FAINT)
                c.setFont("Helvetica", fs2)
                dim = f"{room.width:.0f}×{room.height:.0f}"
                c.drawCentredString(rx + rw/2, ry + rh/2 - fs2*0.9, dim)

            c.restoreState()

        # Scale bar
        bar_ft = 10
        bar_px = bar_ft * scale
        bx, by = ox, oy - 4.5*mm
        c.saveState()
        c.setStrokeColorRGB(*C_GOLD); c.setLineWidth(0.7)
        c.line(bx, by, bx + bar_px, by)
        c.line(bx, by - 1*mm, bx, by + 1*mm)
        c.line(bx + bar_px, by - 1*mm, bx + bar_px, by + 1*mm)
        c.setFont("Helvetica", 5.5); c.setFillColorRGB(*C_GOLD)
        c.drawCentredString(bx + bar_px/2, by - 3*mm, f"{bar_ft} ft")
        c.restoreState()

        # Compass
        comp_x = ox + plot_w * scale + 8*mm
        comp_y = oy + plot_h * scale - 12*mm
        if comp_x + 8*mm < x + w:
            self._draw_compass_rl(c, comp_x, comp_y, 6*mm, layout.facing)

    def _draw_score_ring(self, c, cx: float, cy: float,
                         radius: float, score: float) -> None:
        """Draw a circular Vastu score ring at (cx, cy)."""
        pct      = score / 100.0
        start_a  = 90          # start at top
        sweep    = pct * 360

        # Track
        c.saveState()
        c.setStrokeColorRGB(0.027, 0.082, 0.161)
        c.setLineWidth(radius * 0.18)
        c.circle(cx, cy, radius * 0.82, stroke=1, fill=0)
        c.restoreState()

        # Arc (cyan → gold gradient approximated with cyan)
        c.saveState()
        c.setStrokeColorRGB(*C_CYAN)
        c.setLineWidth(radius * 0.18)
        if sweep > 0:
            c.arc(cx - radius*0.82, cy - radius*0.82,
                  cx + radius*0.82, cy + radius*0.82,
                  startAng=start_a, extent=sweep)
        c.restoreState()

        # Score text
        c.saveState()
        c.setFont("Helvetica-Bold", radius * 0.55)
        self._set_fill(c, C_WHITE)
        c.drawCentredString(cx, cy + radius * 0.05, f"{int(score)}")
        c.setFont("Helvetica", radius * 0.22)
        self._set_fill(c, C_CYAN)
        c.drawCentredString(cx, cy - radius * 0.28, "/ 100")
        c.setFont("Helvetica", radius * 0.16)
        self._set_fill(c, C_FAINT)
        c.drawCentredString(cx, cy - radius * 0.55, "VASTU")
        c.restoreState()

    def _draw_compass_rl(self, c, cx: float, cy: float,
                         r: float, facing: str) -> None:
        """Draw a small compass rose using ReportLab at (cx, cy)."""
        degs = {"North": 0, "East": 90, "South": 180, "West": 270}
        rot  = math.radians(degs.get(facing, 0))

        c.saveState()
        c.setFillColorRGB(0.016, 0.059, 0.122)
        c.setStrokeColorRGB(*C_CYAN)
        c.setLineWidth(0.4)
        c.circle(cx, cy, r, stroke=1, fill=1)

        # North needle
        nx = cx + r * 0.8 * math.sin(rot)
        ny = cy + r * 0.8 * math.cos(rot)
        c.setFillColorRGB(0.973, 0.443, 0.424)
        c.setStrokeColorRGB(0.973, 0.443, 0.424)
        c.setLineWidth(0.8)
        c.line(cx, cy, nx, ny)

        # N label
        c.setFont("Helvetica-Bold", r * 0.4)
        c.setFillColorRGB(0.973, 0.443, 0.424)
        c.drawCentredString(
            cx + (r * 1.25) * math.sin(rot),
            cy + (r * 1.25) * math.cos(rot) - r * 0.15,
            "N"
        )
        c.restoreState()

    def _draw_page_footer(self, c, layout: Layout, page_num: int) -> None:
        """Draw the page footer bar."""
        self._fill_rect(c, 0, 0, PAGE_W, 10*mm, C_SURFACE)
        dt = datetime.now().strftime("%d %b %Y")
        c.setFont("Helvetica", 5.5)
        self._set_fill(c, C_FAINT)
        c.drawString(
            MARGIN, 3.5*mm,
            f"IntelliPlan·3D  ·  GA + 16-Rule Vastu Engine  ·  {dt}"
        )
        c.drawCentredString(PAGE_W / 2, 3.5*mm, f"ID: {layout.layout_id}")
        c.drawRightString(PAGE_W - MARGIN, 3.5*mm, f"Page {page_num} of 2")

    # ── SVG helpers ───────────────────────────────────────────────

    def _svg_grid(self, ox, oy, plot_w, plot_h, scale):
        lines = []
        step = 10 * scale
        x = ox
        while x <= ox + plot_w * scale:
            lines.append(
                f'  <line x1="{x:.1f}" y1="{oy:.1f}" '
                f'x2="{x:.1f}" y2="{oy + plot_h*scale:.1f}" '
                f'stroke="#071529" stroke-width="0.5"/>'
            )
            x += step
        y = oy
        while y <= oy + plot_h * scale:
            lines.append(
                f'  <line x1="{ox:.1f}" y1="{y:.1f}" '
                f'x2="{ox + plot_w*scale:.1f}" y2="{y:.1f}" '
                f'stroke="#071529" stroke-width="0.5"/>'
            )
            y += step
        return lines

    def _svg_compass(self, cx, cy, r, facing):
        degs = {"North": 0, "East": 90, "South": 180, "West": 270}
        rot  = math.radians(degs.get(facing, 0))
        nx   = cx + r * math.sin(rot)
        ny   = cy - r * math.cos(rot)
        return [
            f'  <circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" '
            f'fill="rgba(2,11,24,0.88)" stroke="#38bdf8" stroke-width="0.8"/>',
            f'  <line x1="{cx:.1f}" y1="{cy:.1f}" '
            f'x2="{nx:.1f}" y2="{ny:.1f}" '
            f'stroke="#f87171" stroke-width="1.5"/>',
            f'  <text x="{cx + (r+7)*math.sin(rot):.1f}" '
            f'y="{cy - (r+7)*math.cos(rot) + 4:.1f}" '
            f'text-anchor="middle" fill="#f87171" '
            f'font-family="monospace" font-size="9" font-weight="bold">N</text>',
        ]

    # ── Low-level ReportLab colour helpers ────────────────────────

    @staticmethod
    def _set_fill(c, rgb):
        c.setFillColorRGB(*rgb)

    @staticmethod
    def _set_fill_rgb(c, r, g, b):
        c.setFillColorRGB(r, g, b)

    @staticmethod
    def _set_stroke(c, rgb, width=0.5):
        c.setStrokeColorRGB(*rgb)
        c.setLineWidth(width)

    @staticmethod
    def _fill_rect(c, x, y, w, h, rgb):
        c.setFillColorRGB(*rgb)
        c.rect(x, y, w, h, stroke=0, fill=1)

    @staticmethod
    def _fill_rect_rgb(c, x, y, w, h, r, g, b):
        c.setFillColorRGB(r, g, b)
        c.rect(x, y, w, h, stroke=0, fill=1)