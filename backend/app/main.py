"""API de LotoLab."""

from datetime import date

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.backtest import router as backtest_router
from app.api.games import router as games_router
from app.api.generate import router as generate_router
from app.api.ingest import router as ingest_router
from app.api.ml import router as ml_router
from app.api.picks import router as picks_router
from app.api.value import router as value_router
from app.config import get_settings
from app.db import get_session

app = FastAPI(
    title="LotoLab",
    version="0.4.0",
    description="Laboratorio estadístico de loterías colombianas. No predice resultados. "
    "Datos: baloto.com (Operador Nacional de Juegos S.A.S.); proyecto académico, no comercial.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(games_router)
app.include_router(backtest_router)
app.include_router(generate_router)
app.include_router(ingest_router)
app.include_router(value_router)
app.include_router(picks_router)
app.include_router(ml_router)


@app.get("/health")
def health(session: Session = Depends(get_session)) -> dict:
    from app.models import Draw, GameRow

    rows = session.execute(
        select(GameRow.code, func.max(Draw.draw_date), func.count(Draw.id))
        .join(Draw, isouter=True)
        .group_by(GameRow.code)
    ).all()
    last: dict[str, dict[str, date | int | None]] = {
        code: {"last_draw_date": d, "draws": n} for code, d, n in rows
    }
    return {"status": "ok", "games": last}
