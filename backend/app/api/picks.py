"""GET /games/{code}/picks: jugadas armadas desde el histórico + cómo les habría ido."""

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.analysis import frequency as fq
from app.analysis.picks import build_picks, typical_shape
from app.api.games import odds_of
from app.config import get_settings
from app.db import get_session
from app.games import get_game
from app.ingest.records import records_from_db

router = APIRouter(tags=["analizador"])

NOTICE = (
    "Estas jugadas resumen lo que más ha salido. No tienen más probabilidad de acertar que "
    "cualquier otra: cada sorteo es independiente. Mira abajo cómo les habría ido de verdad."
)


@router.get("/games/{code}/picks")
def game_picks(
    code: str,
    window: str = Query("12m", description="'all', '<n>m' (meses) o número de sorteos"),
    session: Session = Depends(get_session),
) -> dict:
    try:
        game = get_game(code)
        w = fq.parse_window(window)
    except ValueError as exc:
        raise HTTPException(404 if "juego" in str(exc) else 422, str(exc)) from None
    recs = records_from_db(session, game.code)
    if len(recs) < 30:
        raise HTTPException(422, "no hay suficientes sorteos cargados")
    win = fq.apply_window(recs, w)
    shape = typical_shape(recs, game)
    picks = build_picks(recs, game, w)

    evaluation = None
    path = get_settings().picks_eval_path
    if path.exists():
        evaluation = json.loads(path.read_text(encoding="utf-8"))["games"].get(game.code)

    return {
        "game": game.code,
        "name": game.name,
        "window": str(w),
        "n_draws": len(win),
        "date_from": win[0].draw_date.isoformat(),
        "date_to": win[-1].draw_date.isoformat(),
        "last_draw": win[-1].draw_number,
        "odds": odds_of(game).model_dump(),
        "notice": NOTICE,
        "shape": {"sum_low": shape.sum_low, "sum_high": shape.sum_high, "evens": list(shape.evens),
                  "highs": list(shape.highs), "high_from": game.main_max // 2 + 1},
        "picks": [
            {"criterion": p.criterion, "label": p.label, "text": p.text, "reason": p.reason,
             "balls": [{"number": n, "color": c} for n, c in sorted(p.balls, key=lambda b: (b[0], str(b[1])))],
             "extra": p.extra}
            for p in picks
        ],
        "evaluation": evaluation,
    }
