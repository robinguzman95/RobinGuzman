"""GET /expected-value y /games/{code}/expected-value: valor esperado y potencia.

Sirve el resumen precalculado (data/expected_value.json). El VE para un acumulado arbitrario se
calcula al vuelo con los parámetros del resumen, sin volver a leer las tablas de premios.
"""

import json
from math import exp

from fastapi import APIRouter, HTTPException, Query

from app.analysis.expected import JACKPOT_CATEGORY, category_probabilities, net_prize
from app.config import get_settings

router = APIRouter(tags=["valor esperado"])


def _summary() -> dict:
    path = get_settings().expected_value_path
    if not path.exists():
        raise HTTPException(404, "aún no se ha corrido `lotolab expected-value`")
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/expected-value")
def all_expected_value() -> dict:
    s = _summary()
    # Versión liviana para la portada: sin curvas ni series.
    light = {
        code: {k: v for k, v in g.items() if k not in ("curve", "sales_series")}
        for code, g in s["games"].items()
    }
    return {"generated": s["generated"], "tax": s["tax"], "games": light}


@router.get("/games/{code}/expected-value")
def game_expected_value(
    code: str,
    jackpot: float | None = Query(None, gt=0, description="acumulado en pesos para calcular el VE"),
    popularity: float = Query(1.0, gt=0, le=10, description="1 = jugada promedio; 0,5 = la mitad de popular"),
) -> dict:
    s = _summary()
    g = s["games"].get(code)
    if g is None:
        raise HTTPException(404, f"sin datos de valor esperado para {code!r}")
    out = {**g, "generated": s["generated"], "tax": s["tax"]}
    if jackpot is not None:
        p_j = category_probabilities(code)[JACKPOT_CATEGORY[code]]
        m = g["sales_model"]
        plays = max(m["a"] + m["b_per_million"] * jackpot / 1e6, 1.0)
        lam = popularity * plays * p_j
        share = (1 - exp(-lam)) / lam
        ev = g["non_jackpot_ev"] + p_j * net_prize(jackpot) * share
        out["query"] = {"jackpot": jackpot, "popularity": popularity, "plays": plays, "ev": ev,
                        "return": ev / g["price"]}
    return out
