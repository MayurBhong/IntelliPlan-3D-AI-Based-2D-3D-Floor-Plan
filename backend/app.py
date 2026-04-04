# ═══════════════════════════════════════════════════════════════
# app.py
# IntelliPlan·3D — Main Flask entry point
#
# API Endpoints:
#   GET  /api/health                    → server status
#   POST /api/layout/generate           → run GA, return layouts
#   GET  /api/export/pdf/<layout_id>    → download PDF report
#   GET  /api/export/json/<layout_id>   → download JSON export
#   GET  /api/export/svg/<layout_id>    → download SVG floor plan
#   GET  /api/layouts                   → list cached layout IDs
#
# Frontend connects to:  http://localhost:5000
# ═══════════════════════════════════════════════════════════════

import os
import io
import sys
import json
import logging

# ── Path setup — MUST be before all local imports ───────────────
# Ensures Python finds ga_engine, vastu_engine, geometry, etc.
# relative to this file regardless of where the script is launched.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from flask import (
    Flask, request, jsonify,
    Response, send_file, abort,
)

# ── Config ───────────────────────────────────────────────────────
from config import config

# ── App factory ──────────────────────────────────────────────────
app = Flask(__name__)
app.config.from_object(config)

# ── Logging ──────────────────────────────────────────────────────
logging.basicConfig(
    level   = getattr(logging, config.LOG_LEVEL, logging.DEBUG),
    format  = "%(asctime)s  [%(levelname)-8s]  %(name)s — %(message)s",
    datefmt = "%H:%M:%S",
    stream  = sys.stdout,
)
logger = logging.getLogger("intelliplan.app")

# ── CORS — manual (no flask-cors dependency) ─────────────────────
ALLOWED_ORIGINS = set(o.strip() for o in config.CORS_ORIGINS if o.strip())


@app.after_request
def _cors(response: Response) -> Response:
    """
    Add CORS headers to every response.
    Allows the HTML frontend served from file:// or a dev server
    to call this API without a proxy.
    """
    origin = request.headers.get("Origin", "")
    if origin in ALLOWED_ORIGINS or "*" in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"]  = origin or "*"
    else:
        # Still allow local dev — loopback origins always permitted
        if "localhost" in origin or "127.0.0.1" in origin:
            response.headers["Access-Control-Allow-Origin"] = origin
        else:
            response.headers["Access-Control-Allow-Origin"] = "*"

    response.headers["Access-Control-Allow-Methods"] = (
        "GET, POST, PUT, DELETE, OPTIONS"
    )
    response.headers["Access-Control-Allow-Headers"] = (
        "Content-Type, Authorization, X-Requested-With"
    )
    response.headers["Access-Control-Max-Age"] = "600"
    return response


@app.before_request
def _handle_preflight():
    """Handle CORS pre-flight OPTIONS requests before routing."""
    if request.method == "OPTIONS":
        return Response(status=204)


# ── Service singletons ────────────────────────────────────────────
from services.layout_service import LayoutService
from services.export_service import ExportService

_layout_svc = LayoutService()
_export_svc = ExportService()


# ════════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════════

def _ok(data: dict, status: int = 200) -> Response:
    """Return a JSON success response."""
    return jsonify(data), status


def _err(message: str, status: int = 400) -> Response:
    """Return a JSON error response."""
    return jsonify({"success": False, "error": message}), status


def _get_json() -> dict:
    """
    Parse the request body as JSON.
    Returns {} (not an error) if the body is empty.
    """
    if not request.data and not request.is_json:
        return {}
    try:
        return request.get_json(force=True, silent=True) or {}
    except Exception:
        return {}


# ════════════════════════════════════════════════════════════════
#  ROUTE 1 — Health check
#  GET /api/health
# ════════════════════════════════════════════════════════════════

@app.route("/api/health", methods=["GET"])
def health():
    """
    Frontend polls this on page load to show the API status indicator.

    Response:
        { status, env, version, cached_layouts }
    """
    return _ok({
        "status":          "ok",
        "env":             config.ENV,
        "version":         "1.0.0",
        "engine":          "GA + 16-Rule Vastu Engine",
        "cached_layouts":  len(_layout_svc.list_cached_ids()),
        "ga_config": {
            "population_size": config.GA_POPULATION_SIZE,
            "max_generations": config.GA_MAX_GENERATIONS,
            "top_layouts":     config.GA_TOP_LAYOUTS,
        },
    })


# ════════════════════════════════════════════════════════════════
#  ROUTE 2 — Generate floor plan layout
#  POST /api/layout/generate
# ════════════════════════════════════════════════════════════════

@app.route("/api/layout/generate", methods=["POST"])
def generate_layout():
    """
    Run the Genetic Algorithm and return the top N floor plan layouts.

    Request body (JSON):
        {
          "plot_size":        "40x60",        // required  e.g. "30x40", "50x80"
          "bhk_type":         "2BHK",         // required  "1BHK"|"2BHK"|"3BHK"|"4BHK"
          "facing_direction": "East",         // required  "North"|"East"|"South"|"West"
          "pop_size":         60,             // optional  GA population size
          "max_generations":  50,             // optional  GA generations
          "top_n":            3,              // optional  layouts to return
          "seed":             null            // optional  RNG seed for reproducibility
        }

    Response (success):
        {
          "success":    true,
          "count":      3,
          "elapsed_ms": 1240,
          "layouts": [
            {
              "layout_id":       "layout-abc123",
              "rooms":           [...],
              "vastu_score":     78.5,
              "fitness":         0.8812,
              "space_util":      72.3,
              "total_room_area": 1680.0,
              "vastu_rules":     [...],
              "plot":            { "width": 40, "height": 60, ... }
            },
            ...
          ]
        }

    Response (error):
        { "success": false, "error": "Invalid plot_size ..." }
    """
    body = _get_json()
    if not body:
        return _err("Request body must be JSON with plot_size, bhk_type, facing_direction")

    # Required fields
    plot_size  = body.get("plot_size")
    bhk_type   = body.get("bhk_type")
    facing     = body.get("facing_direction")

    if not all([plot_size, bhk_type, facing]):
        return _err(
            "Missing required fields: plot_size, bhk_type, facing_direction"
        )

    # Optional GA tuning params
    pop_size        = body.get("pop_size",        config.GA_POPULATION_SIZE)
    max_generations = body.get("max_generations", config.GA_MAX_GENERATIONS)
    top_n           = body.get("top_n",           config.GA_TOP_LAYOUTS)
    seed            = body.get("seed",            None)

    logger.info(
        "POST /api/layout/generate | plot=%s bhk=%s facing=%s",
        plot_size, bhk_type, facing,
    )

    result = _layout_svc.generate(
        plot_size        = str(plot_size),
        bhk_type         = str(bhk_type),
        facing_direction = str(facing),
        pop_size         = int(pop_size),
        max_generations  = int(max_generations),
        top_n            = int(top_n),
        seed             = int(seed) if seed is not None else None,
    )

    if not result.success:
        return _err(result.error or "Generation failed", 400)

    return _ok(result.to_dict())


# ════════════════════════════════════════════════════════════════
#  ROUTE 3 — Export PDF
#  GET /api/export/pdf/<layout_id>
# ════════════════════════════════════════════════════════════════

@app.route("/api/export/pdf/<layout_id>", methods=["GET"])
def export_pdf(layout_id: str):
    """
    Generate and stream an A4 PDF report for a previously generated layout.

    The layout must have been generated in the current session
    (held in LayoutService's in-memory cache).

    Response:
        Binary PDF stream with Content-Disposition: attachment
    """
    layout = _layout_svc.get_layout(layout_id)
    if layout is None:
        return _err(
            f"Layout '{layout_id}' not found. "
            "Generate a floor plan first or regenerate it.", 404
        )

    logger.info("GET /api/export/pdf/%s", layout_id)

    try:
        pdf_bytes = _export_svc.export_pdf(layout)
    except RuntimeError as exc:
        return _err(str(exc), 503)
    except Exception as exc:
        logger.exception("PDF export failed: %s", exc)
        return _err("PDF generation failed — check server logs", 500)

    filename = f"intelliplan-{layout_id[:8]}.pdf"
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype     = "application/pdf",
        as_attachment = True,
        download_name = filename,
    )


# ════════════════════════════════════════════════════════════════
#  ROUTE 4 — Export JSON
#  GET /api/export/json/<layout_id>
# ════════════════════════════════════════════════════════════════

@app.route("/api/export/json/<layout_id>", methods=["GET"])
def export_json(layout_id: str):
    """
    Return the full layout as a downloadable JSON file.

    Response:
        JSON file attachment (same schema as the generate response)
    """
    layout = _layout_svc.get_layout(layout_id)
    if layout is None:
        return _err(f"Layout '{layout_id}' not found.", 404)

    logger.info("GET /api/export/json/%s", layout_id)

    json_str  = _export_svc.export_json(layout)
    filename  = f"intelliplan-{layout_id[:8]}.json"

    return Response(
        json_str,
        mimetype    = "application/json",
        headers     = {
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


# ════════════════════════════════════════════════════════════════
#  ROUTE 5 — Export SVG
#  GET /api/export/svg/<layout_id>
# ════════════════════════════════════════════════════════════════

@app.route("/api/export/svg/<layout_id>", methods=["GET"])
def export_svg(layout_id: str):
    """
    Return the floor plan as a standalone SVG file.

    Query params:
        ?width=800    SVG canvas width in px  (default 800)
        ?height=600   SVG canvas height in px (default 600)

    Response:
        SVG file attachment
    """
    layout = _layout_svc.get_layout(layout_id)
    if layout is None:
        return _err(f"Layout '{layout_id}' not found.", 404)

    try:
        width  = max(400, min(3000, int(request.args.get("width",  800))))
        height = max(300, min(2000, int(request.args.get("height", 600))))
    except (ValueError, TypeError):
        width, height = 800, 600

    logger.info("GET /api/export/svg/%s (%dx%d)", layout_id, width, height)

    svg_str  = _export_svc.export_svg(layout, width=width, height=height)
    filename = f"intelliplan-{layout_id[:8]}.svg"

    return Response(
        svg_str,
        mimetype = "image/svg+xml",
        headers  = {
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


# ════════════════════════════════════════════════════════════════
#  ROUTE 6 — List cached layouts
#  GET /api/layouts
# ════════════════════════════════════════════════════════════════

@app.route("/api/layouts", methods=["GET"])
def list_layouts():
    """
    Return a list of all currently cached layout IDs and their
    key metrics. Useful for debugging and the frontend's layout tabs.

    Response:
        {
          "count": 3,
          "layouts": [
            { "layout_id", "bhk_type", "facing", "vastu_score",
              "fitness", "rooms", "plot_size" },
            ...
          ]
        }
    """
    ids = _layout_svc.list_cached_ids()
    summaries = []
    for lid in ids:
        lay = _layout_svc.get_layout(lid)
        if lay:
            summaries.append({
                "layout_id":   lay.layout_id,
                "bhk_type":    lay.bhk_type,
                "facing":      lay.facing,
                "vastu_score": lay.vastu_score,
                "fitness":     lay.fitness,
                "rooms":       len(lay.rooms),
                "plot_size":   f"{lay.plot_width:.0f}x{lay.plot_height:.0f}",
            })

    return _ok({"count": len(summaries), "layouts": summaries})


# ════════════════════════════════════════════════════════════════
#  ERROR HANDLERS
# ════════════════════════════════════════════════════════════════

@app.errorhandler(400)
def bad_request(e):
    return _err(str(e), 400)


@app.errorhandler(404)
def not_found(e):
    return _err("Endpoint not found", 404)


@app.errorhandler(405)
def method_not_allowed(e):
    return _err("Method not allowed", 405)


@app.errorhandler(500)
def internal_error(e):
    logger.exception("Internal server error: %s", e)
    return _err("Internal server error", 500)


# ════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")

    logger.info("=" * 56)
    logger.info("  IntelliPlan·3D Backend")
    logger.info("  GA Engine + 16-Rule Vastu Shastra Scoring")
    logger.info("  http://%s:%d", host, port)
    logger.info("  ENV: %s  |  DEBUG: %s", config.ENV, config.DEBUG)
    logger.info("  GA: pop=%d  gen=%d  top=%d",
                config.GA_POPULATION_SIZE,
                config.GA_MAX_GENERATIONS,
                config.GA_TOP_LAYOUTS)
    logger.info("=" * 56)

    app.run(
        host   = host,
        port   = port,
        debug  = config.DEBUG,
        use_reloader = config.DEBUG,
    )