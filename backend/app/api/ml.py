"""GET /games/{code}/ml: probabilidades del modelo para el próximo sorteo + su evaluación."""

import json
from functools import lru_cache
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.analysis.frequency import all_balls, ball_label
from app.api.games import odds_of
from app.config import get_settings
from app.db import get_session
from app.games import Game, get_game
from app.ingest.records import DrawRecord, records_from_db
from app.ml.model import MODELS, NextDraw, predict_next

router = APIRouter(tags=["machine learning"])

NOTICE = (
    "El modelo estima, con la historia de cada balota, qué tan probable es que salga. Evaluado sin "
    "mirar al futuro, no predice mejor que suponer que todas tienen la misma probabilidad. La "
    "probabilidad real del premio mayor no cambia."
)


@lru_cache(maxsize=32)
def _cached(code: str, last_draw: int, kind: str, unit: str, records: tuple[DrawRecord, ...]) -> NextDraw:
    return predict_next(list(records), get_game(code), kind, unit)


def next_draw(game: type[Game], records: list[DrawRecord], kind: str, unit: str = "main") -> NextDraw:
    last = max(r.draw_number for r in records)
    return _cached(game.code, last, kind, unit, tuple(sorted(records, key=lambda r: r.draw_number)))


def labels(game: type[Game], unit: str) -> list[str]:
    if unit == "extra":
        return [str(i) for i in range(1, (game.extra_max or 0) + 1)]
    return [ball_label(b) for b in all_balls(game)]


def evaluation(code: str) -> dict | None:
    path = get_settings().ml_eval_path
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))["games"].get(code)


@router.get("/games/{code}/ml")
def game_ml(
    code: str,
    model: Literal["gb", "logit"] = Query("gb"),
    session: Session = Depends(get_session),
) -> dict:
    try:
        game = get_game(code)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from None
    recs = records_from_db(session, game.code)
    if len(recs) < 150:
        raise HTTPException(422, "no hay suficientes sorteos para entrenar el modelo")
    units = {}
    for unit in ["main"] + (["extra"] if game.extra_max else []):
        nd = next_draw(game, recs, model, unit)
        names = labels(game, unit)
        ranked = sorted(zip(names, nd.probabilities), key=lambda x: -x[1])
        units[unit] = {
            "base": nd.base,
            "trained_on": nd.trained_on,
            "probabilities": [{"label": n, "probability": p} for n, p in zip(names, nd.probabilities)],
            "top": [{"label": n, "probability": p} for n, p in ranked[: game.main_count if unit == "main" else 3]],
        }
    return {
        "game": game.code,
        "name": game.name,
        "model": model,
        "model_name": MODELS[model],
        "last_draw": max(r.draw_number for r in recs),
        "odds": odds_of(game).model_dump(),
        "notice": NOTICE,
        "units": units,
        "evaluation": evaluation(game.code),
    }
