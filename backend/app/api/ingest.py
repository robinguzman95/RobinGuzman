"""POST /ingest/run: dispara la actualización post-sorteo. Protegido con token."""

import hmac
from dataclasses import asdict

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_session
from app.ingest.scraper import Scraper

router = APIRouter(prefix="/ingest", tags=["ingesta"])


def get_scraper() -> Scraper:
    s = get_settings()
    return Scraper(s.cache_dir, s.scraper_delay_seconds, s.scraper_user_agent, use_cache=False)


@router.post("/run")
def run_ingest(
    x_ingest_token: str | None = Header(None),
    session: Session = Depends(get_session),
    scraper: Scraper = Depends(get_scraper),
) -> dict:
    expected = get_settings().ingest_token
    if not expected:
        raise HTTPException(503, "LOTOLAB_INGEST_TOKEN no está configurado en el servidor")
    if not x_ingest_token or not hmac.compare_digest(x_ingest_token.encode(), expected.encode()):
        raise HTTPException(401, "token inválido")
    from jobs.update_draws import run_update

    summary = run_update(session, scraper)
    return {"ok": summary.ok, **asdict(summary)}
