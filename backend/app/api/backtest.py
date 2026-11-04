"""POST /backtest y GET /backtest/{id}."""

import json
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.games import DISCLAIMER, odds_of
from app.api.schemas import Odds
from app.backtest.engine import ALPHA, PRIMARY_WINDOW, run_backtest
from app.backtest.strategies import STRATEGIES, get_strategy
from app.db import get_session
from app.games import get_game
from app.ingest.records import records_from_db
from app.models import BacktestResult, BacktestRun, GameRow

router = APIRouter(prefix="/backtest", tags=["backtest"])


class BacktestIn(BaseModel):
    game: str
    strategy: str = Field(description=f"una de: {', '.join(STRATEGIES)}")
    window: int = Field(PRIMARY_WINDOW, ge=1, le=2000)
    date_from: date | None = None
    date_to: date | None = None
    seed: int = 0


class BacktestOut(BaseModel):
    id: int
    game: str
    strategy: str
    window: int
    is_primary_window: bool
    date_from: date
    date_to: date
    n_draws: int
    avg_hits: float
    hit_distribution: dict[int, int]
    extra_hit_rate: float | None
    baseline_mean: float
    baseline_p5: float
    baseline_p95: float
    p_value: float
    beats_random: bool
    verdict: str
    odds: Odds
    disclaimer: str


def _out(run: BacktestRun, res: BacktestResult, game_code: str) -> BacktestOut:
    extra = json.loads(res.hit_distribution_json)
    beats = res.p_value < ALPHA and res.avg_hits > res.baseline_p95
    return BacktestOut(
        id=run.id, game=game_code, strategy=run.strategy, window=run.window_draws,
        is_primary_window=run.window_draws == PRIMARY_WINDOW,
        date_from=run.date_from, date_to=run.date_to, n_draws=extra["n_draws"],
        avg_hits=res.avg_hits, hit_distribution={int(k): v for k, v in extra["main"].items()},
        extra_hit_rate=extra["extra_hit_rate"], baseline_mean=res.baseline_mean,
        baseline_p5=res.baseline_p5, baseline_p95=res.baseline_p95, p_value=res.p_value,
        beats_random=beats,
        verdict=("le gana al azar en esta corrida (una sola prueba, sin corrección por "
                 "comparaciones múltiples)" if beats else "dentro de la banda aleatoria: no le gana al azar"),
        odds=odds_of(get_game(game_code)), disclaimer=DISCLAIMER,
    )


@router.post("", response_model=BacktestOut, status_code=201)
def create_backtest(body: BacktestIn, session: Session = Depends(get_session)) -> BacktestOut:
    try:
        game = get_game(body.game)
        strategy = get_strategy(body.strategy)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from None
    try:
        out = run_backtest(records_from_db(session, game.code), game, strategy, body.strategy,
                           window=body.window, date_from=body.date_from, date_to=body.date_to, seed=body.seed)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None

    game_row = session.scalar(select(GameRow).where(GameRow.code == game.code))
    run = BacktestRun(
        game_id=game_row.id, strategy=body.strategy, window_draws=body.window,
        params_json=json.dumps({"seed": body.seed, "sims": out.baseline.sims}),
        date_from=out.date_from, date_to=out.date_to,
    )
    run.results.append(BacktestResult(
        avg_hits=out.avg_hits,
        hit_distribution_json=json.dumps({"main": out.hit_distribution, "extra_hit_rate": out.extra_hit_rate,
                                          "n_draws": out.n_draws}),
        baseline_mean=out.baseline.mean, baseline_p5=out.baseline.p5, baseline_p95=out.baseline.p95,
        p_value=out.p_value,
    ))
    session.add(run)
    session.commit()
    return _out(run, run.results[0], game.code)


@router.get("/{run_id}", response_model=BacktestOut)
def get_backtest(run_id: int, session: Session = Depends(get_session)) -> BacktestOut:
    run = session.get(BacktestRun, run_id)
    if run is None or not run.results:
        raise HTTPException(404, f"no existe la corrida {run_id}")
    code = session.get(GameRow, run.game_id).code
    return _out(run, run.results[0], code)
