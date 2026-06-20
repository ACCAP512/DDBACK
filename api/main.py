"""FastAPI backend for the Drawback Engine (Layers 1-3).

Thin transport over the pure-stdlib engine: ingest data -> Estimate -> glass-box pairs -> stubbed
CATAIR claim + simulated lifecycle. Serves the built React SPA from ``web/dist`` when present, so a
single ``uvicorn api.main:app`` runs the whole app.

Preparation/decision-support only — not the filer of record (19 CFR 190.6).
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))  # make ``drawback`` importable however we're launched

from fastapi import FastAPI, HTTPException, UploadFile, File  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from drawback.config import tariff_eligibility as cfg  # noqa: E402
from drawback.data.generator import generate  # noqa: E402
from drawback.data.parser import parse_dataset  # noqa: E402
from drawback.estimate import build_estimate  # noqa: E402
from drawback.filing.catair import build_claims, mock_submit  # noqa: E402
from drawback.filing.lifecycle import simulate_lifecycle  # noqa: E402
from drawback.serialize import estimate_to_dict, to_jsonable  # noqa: E402

app = FastAPI(title="Drawback Engine API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

SAMPLES = ROOT / "samples"
_SESSIONS: dict[str, dict] = {}  # token -> {dataset, estimate, charges_by_key}


def _store(dataset, estimate) -> str:
    token = uuid.uuid4().hex[:12]
    _SESSIONS[token] = {
        "dataset": dataset,
        "estimate": estimate,
        "charges_by_key": {(im.entry_number, im.line_number): im.charges for im in dataset.imports},
    }
    # keep only the few most-recent sessions (single-user local demo)
    if len(_SESSIONS) > 8:
        for k in list(_SESSIONS)[:-8]:
            _SESSIONS.pop(k, None)
    return token


def _session(token: str) -> dict:
    s = _SESSIONS.get(token)
    if not s:
        raise HTTPException(404, "unknown or expired session token")
    return s


def _estimate_payload(token: str, dataset, estimate) -> dict:
    return {"token": token, "config": cfg.config_summary(), **estimate_to_dict(estimate)}


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "as_of": cfg.AS_OF.isoformat(), "config": cfg.VERSION}


@app.get("/api/config")
def config() -> dict:
    return cfg.config_summary()


@app.get("/api/assumptions")
def assumptions() -> dict:
    """The engine's assumption registry (tags + the one user-correctable assumption, A-21)."""
    from drawback.assumptions import registry_summary
    return registry_summary()


@app.post("/api/estimate/sample")
def estimate_sample(scale: str = "demo") -> dict:
    """Build an estimate from the committed sample CSVs (or generate if absent)."""
    imp, exp = SAMPLES / "imports.csv", SAMPLES / "exports.csv"
    if imp.exists() and exp.exists() and scale == "demo":
        dataset = parse_dataset(imp, exp)
    else:
        dataset = generate(scale=scale)
    estimate = build_estimate(dataset)
    token = _store(dataset, estimate)
    return _estimate_payload(token, dataset, estimate)


@app.post("/api/estimate/upload")
async def estimate_upload(imports: UploadFile = File(...), exports: UploadFile = File(...)) -> dict:
    """Ingest a client's import + export CSVs and return an instant estimate (FR1.1)."""
    try:
        imp_text = (await imports.read()).decode("utf-8", errors="replace")
        exp_text = (await exports.read()).decode("utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"could not read uploads: {e}")
    dataset = parse_dataset(imp_text, exp_text)
    if not dataset.imports:
        raise HTTPException(422, "no valid import rows parsed — check the file format (see samples/imports.csv)")
    estimate = build_estimate(dataset)
    token = _store(dataset, estimate)
    return _estimate_payload(token, dataset, estimate)


@app.get("/api/claims/{token}")
def claims(token: str) -> dict:
    s = _session(token)
    cl = build_claims(s["estimate"], import_charges_by_key=s["charges_by_key"])
    from drawback.filing.catair import serialize_claim_text, validate_claim
    return {
        "simulated": True,
        "banner": "SIMULATED — not connected to CBP. A licensed broker/filer must certify & transmit (19 CFR 190.6).",
        "claims": [
            {**to_jsonable(c), "issues": validate_claim(c), "transmission_text": serialize_claim_text(c)}
            for c in cl
        ],
    }


@app.post("/api/claims/{token}/submit")
def submit(token: str) -> dict:
    s = _session(token)
    cl = build_claims(s["estimate"], import_charges_by_key=s["charges_by_key"])
    manifest = mock_submit(cl, ROOT / "filing_out")
    return manifest


@app.get("/api/defensibility/{token}")
def defensibility(token: str) -> dict:
    """The per-claim defensibility report (COMPLIANCE §4 P6): the structurally [VERIFIED]-only defensible
    headline, the reconciliation check, and the rules-fired/tier/citation breakdown — validatable from the
    trace alone. Non-strict so a (hypothetical) violation surfaces in the report rather than 500-ing."""
    s = _session(token)
    from drawback.defensibility import harden
    return harden(s["estimate"], strict=False).report()


@app.get("/api/lifecycle/{token}")
def lifecycle(token: str, accelerated_payment: bool = True) -> dict:
    s = _session(token)
    return simulate_lifecycle(cfg.AS_OF, accelerated_payment=accelerated_payment,
                              estimated_amount=s["estimate"].headline_point, today=cfg.AS_OF)


# ── serve the built SPA (single-process run) ────────────────────────────────
_DIST = ROOT / "web" / "dist"
if _DIST.exists():
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="spa")
else:
    @app.get("/")
    def _no_spa() -> JSONResponse:
        return JSONResponse({
            "message": "Drawback Engine API is running. Build the SPA (cd web && npm install && npm run build) "
                       "or run the Vite dev server (npm run dev). API is under /api.",
            "api": ["/api/health", "/api/config", "/api/estimate/sample", "/api/estimate/upload"],
        })
