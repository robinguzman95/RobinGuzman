"""API de LotoLab. En la Fase 1 solo expone /health y /games; el resto llega en fases 2–4."""

from datetime import date

from fastapi import Depends, FastAPI
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_session
from app.games import GAMES

app = FastAPI(title="LotoLab", version="0.1.0")


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


@app.get("/games")
def games() -> list[dict]:
    return [
        {
            "code": g.code,
            "name": g.name,
            "main_count": g.main_count,
            "main_max": g.main_max,
            "extra_max": g.extra_max,
            "colors": list(g.colors) if g.colors else None,
            "combinations": g.combinations(),
            "jackpot_odds": g.odds_text(),
        }
        for g in GAMES.values()
    ]
