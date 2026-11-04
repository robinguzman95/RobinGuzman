"""API de LotoLab."""

from datetime import date

from fastapi import Depends, FastAPI
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.games import router as games_router
from app.db import get_session

app = FastAPI(title="LotoLab", version="0.2.0")
app.include_router(games_router)


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
