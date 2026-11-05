"""Resumen de la evaluación del modelo de ML (data/ml_eval.json), generado con `lotolab ml`."""

from dataclasses import asdict
from datetime import date

from app.games import get_game
from app.ingest.records import DrawRecord
from app.ml.model import MODELS, walk_forward


def evaluate_game(code: str, records: list[DrawRecord]) -> dict:
    game = get_game(code)
    units = ["main"] + (["extra"] if game.extra_max else [])
    out = {"game": code, "name": game.name, "n_draws": len(records), "units": {}}
    for unit in units:
        out["units"][unit] = {kind: asdict(walk_forward(records, game, kind=kind, unit=unit)) for kind in MODELS}
    first = out["units"]["main"]["gb"]
    out["test_draws"] = first["n_test"]
    recs = sorted(records, key=lambda r: r.draw_number)
    out["test_from"] = recs[len(recs) - first["n_test"]].draw_date.isoformat()
    out["test_to"] = recs[-1].draw_date.isoformat()
    return out


def build(per_game: dict[str, dict]) -> dict:
    return {"generated": date.today().isoformat(), "models": MODELS, "games": per_game}
