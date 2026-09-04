"""
SettleSync FastAPI backend — thin HTTP layer over the existing deterministic
core/ pipeline. No business logic lives here; see core/, audit/, agent/.

Run: uvicorn api.main:app --reload --port 8000
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routers import batch, records, gates, close, vendors, audit, gst, query

app = FastAPI(title="SettleSync API")

app.include_router(batch.router)
app.include_router(records.router)
app.include_router(gates.router)
app.include_router(close.router)
app.include_router(vendors.router)
app.include_router(audit.router)
app.include_router(gst.router)
app.include_router(query.router)

FRONTEND_DIST = Path("frontend/dist")

if FRONTEND_DIST.exists():
    # Hashed JS/CSS bundle — served directly, with normal static-file caching.
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="static-assets")

    # Everything else falls through to the SPA shell so React Router can
    # handle client-side routes (e.g. a hard refresh on /close-review).
    # A plain StaticFiles(html=True) mount at "/" only serves index.html for
    # the root and directory-style paths — it 404s on arbitrary client
    # routes, which breaks refresh/deep-link on every page but Control Tower.
    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
