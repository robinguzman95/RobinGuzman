"""Rutas /games, /games/{code}/draws y /games/{code}/stats."""

from dataclasses import asdict
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.analysis import frequency as fq
from app.analysis.stat_tests import runs_by_ball, uniformity_tests
from app.api.schemas import (
    BallOut,
    BallStatOut,
    ChiSquareOut,
    ComboOut,
    DrawOut,
    DrawPage,
    GameOut,
    Odds,
    RunsOut,
    ShapeOut,
    StatsOut,
)
from app.db import get_session
from app.games import GAMES, Game, get_game
from app.ingest.records import records_from_db

router = APIRouter(prefix="/games", tags=["juegos"])

DISCLAIMER = (
    "Cada sorteo es independiente: las frecuencias pasadas no cambian la probabilidad del "
    "próximo. Este análisis describe el histórico; no predice resultados."
)


def odds_of(game: type[Game]) -> Odds:
    return Odds(
        combinations=game.combinations(),
        jackpot_odds=game.odds_text(),
        jackpot_probability=float(game.jackpot_odds()),
    )


def _game_or_404(code: str) -> type[Game]:
    try:
        return get_game(code)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from None


@router.get("", response_model=list[GameOut])
def list_games() -> list[GameOut]:
    return [
        GameOut(
            code=g.code, name=g.name, main_count=g.main_count, main_max=g.main_max,
            extra_max=g.extra_max, colors=list(g.colors) if g.colors else None, odds=odds_of(g),
        )
        for g in GAMES.values()
    ]


@router.get("/{code}/draws", response_model=DrawPage)
def list_draws(
    code: str,
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    session: Session = Depends(get_session),
) -> DrawPage:
    game = _game_or_404(code)
    recs = [
        r for r in records_from_db(session, game.code)
        if (date_from is None or r.draw_date >= date_from) and (date_to is None or r.draw_date <= date_to)
    ]
    recs.sort(key=lambda r: r.draw_number, reverse=True)  # más reciente primero
    chunk = recs[(page - 1) * page_size: page * page_size]
    return DrawPage(
        game=game.code, page=page, page_size=page_size, total=len(recs),
        items=[
            DrawOut(
                draw_number=r.draw_number, draw_date=r.draw_date,
                balls=[BallOut(number=n, color=c) for n, c in r.ticket.balls()],
                extra=r.extra, source_url=r.source_url,
            )
            for r in chunk
        ],
    )


def _stat_out(s: fq.BallStat) -> BallStatOut:
    return BallStatOut(label=s.label, number=s.ball[0], color=s.ball[1], count=s.count,
                       draws_since=s.draws_since, days_since=s.days_since)


def _combos(recs, k: int) -> list[ComboOut]:
    return [ComboOut(balls=[fq.ball_label(b) for b in combo], count=n) for combo, n in fq.top_combos(recs, k)]


def compute_stats(game: type[Game], records, window: fq.Window) -> StatsOut:
    recs = fq.apply_window(records, window)
    hot, cold = fq.hot_cold(recs, game)
    shape = fq.shape_stats(recs, game)
    return StatsOut(
        game=game.code,
        window=str(window),
        n_draws=len(recs),
        date_from=recs[0].draw_date if recs else None,
        date_to=recs[-1].draw_date if recs else None,
        odds=odds_of(game),
        disclaimer=DISCLAIMER,
        frequency={fq.ball_label(b): n for b, n in fq.ball_frequency(recs, game).items()},
        number_frequency=fq.number_frequency(recs, game) if game.colors else None,
        color_frequency=fq.color_frequency(recs, game),
        extra_frequency=fq.extra_frequency(recs, game),
        hot=[_stat_out(s) for s in hot],
        cold=[_stat_out(s) for s in cold],
        overdue=[_stat_out(s) for s in fq.overdue(recs, game)],
        top_pairs=_combos(recs, 2),
        pair_counts=[(fq.ball_label(a), fq.ball_label(b), n) for (a, b), n in sorted(
            fq.combo_frequency(recs, 2).items(), key=lambda kv: [(x[0], str(x[1])) for x in kv[0]])],
        top_triples=_combos(recs, 3),
        shape=ShapeOut(**{k: v for k, v in asdict(shape).items() if k != "sums"}) if shape else None,
        uniformity=[ChiSquareOut(**{k: v for k, v in asdict(t).items() if k != "n_draws"})
                    for t in uniformity_tests(recs, game)],
        runs=RunsOut(**asdict(runs_by_ball(recs, game))),
    )


@router.get("/{code}/stats", response_model=StatsOut)
def game_stats(
    code: str,
    window: str = Query("12m", description="'all', '<n>m' (meses) o número de sorteos"),
    session: Session = Depends(get_session),
) -> StatsOut:
    game = _game_or_404(code)
    try:
        w = fq.parse_window(window)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    return compute_stats(game, records_from_db(session, game.code), w)
