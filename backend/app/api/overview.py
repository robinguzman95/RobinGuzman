"""GET /overview: las cifras clave del proyecto en una sola respuesta (para la portada).

Reúne datos de la BD (sorteos por juego) y de los resúmenes precalculados (backtest, valor
esperado, modelo de ML). Si un resumen no existe, su sección sale en null.
"""

import json
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_session
from app.games import GAMES

router = APIRouter(tags=["resumen"])


def _load(path: Path) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


@router.get("/overview")
def overview(session: Session = Depends(get_session)) -> dict:
    from app.models import Draw, GameRow

    rows = session.execute(
        select(GameRow.code, func.count(Draw.id), func.min(Draw.draw_date), func.max(Draw.draw_date))
        .join(Draw, isouter=True)
        .group_by(GameRow.code)
    ).all()
    games = {
        code: {"name": GAMES[code].name, "draws": n, "date_from": d0, "date_to": d1,
               "odds": GAMES[code].odds_text()}
        for code, n, d0, d1 in rows if code in GAMES
    }
    s = get_settings()

    bt = _load(s.backtest_summary_path)
    backtest = None
    if bt:
        rows_bt = bt["rows"]
        backtest = {
            "combinations": bt["combinations"],
            "significant": sum(r["significant_bonferroni"] for r in rows_bt),
            "nominal": sum(r["above_p95"] and r["p_value"] < bt["alpha"] for r in rows_bt),
            "alpha_bonferroni": bt["alpha_bonferroni"],
            "strategies": sorted({r["strategy"] for r in rows_bt}),
        }

    ev = _load(s.expected_value_path)
    expected = None
    if ev:
        expected = {
            code: {"price": g["price"], "return_current": g["return_current"],
                   "non_jackpot_return": g["non_jackpot_return"], "median_plays": g["median_plays"],
                   "popularity_rho": (g["popularity"] or {}).get("spearman_rho"),
                   "popularity_p": (g["popularity"] or {}).get("p_value"),
                   "min_bias": g["power"]["ball_bias"]["min_relative_bias"]}
            for code, g in ev["games"].items()
        }

    ml = _load(s.ml_eval_path)
    model = None
    if ml:
        model = {}
        for code, g in ml["games"].items():
            main = g["units"]["main"]
            model[code] = {
                kind: {"skill": e["skill"], "ci_low": e["delta_ci"][0], "ci_high": e["delta_ci"][1],
                       "avg_hits": e["avg_hits"], "base_p5": e["base_p5"], "base_p95": e["base_p95"],
                       "beats_random": e["delta_ci"][0] > 0}
                for kind, e in main.items()
            }

    return {
        "total_draws": sum(g["draws"] for g in games.values()),
        "games": games,
        "backtest": backtest,
        "expected_value": expected,
        "ml": model,
    }
