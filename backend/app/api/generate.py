"""POST /generate: genera jugadas, siempre con la probabilidad real.

Dos modos:
- "historico" (por defecto): jugadas armadas con las balotas que más han salido, cada una con sus
  estadísticas (veces que salió cada balota, forma, parejas frecuentes) y cómo le habría ido
  jugándola en cada sorteo del último año con los premios reales.
- "anti_popular": jugadas al azar que evitan patrones populares (fechas, secuencias, figuras).
"""

import random
import secrets
from collections import defaultdict
from functools import lru_cache
from itertools import combinations
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.analysis import frequency as fq
from app.analysis.picks import historical_plays, play_ticket, typical_shape
from app.analysis.popularity import popularity
from app.api.games import odds_of
from app.api.schemas import BallOut, Odds
from app.backtest.strategies import anti_popular
from app.config import get_settings
from app.db import get_session
from app.games import Game, Ticket, get_game
from app.ingest.prizes import read_prizes_csv
from app.ingest.records import DrawRecord, records_from_db

router = APIRouter(prefix="/generate", tags=["generador"])

NOTICES = {
    "historico": (
        "Jugadas armadas con las balotas que más han salido. Ninguna jugada tiene más probabilidad de "
        "ganar que otra: cada sorteo es independiente. Abajo de cada una ves sus datos reales."
    ),
    "anti_popular": (
        "Ninguna jugada tiene más probabilidad de ganar que otra. Estas jugadas solo evitan patrones "
        "que mucha gente juega (fechas, secuencias, figuras), para que, si ganan, el premio se reparta "
        "entre menos personas."
    ),
}


class GenerateIn(BaseModel):
    game: str
    n: int = Field(5, ge=1, le=10)
    mode: Literal["historico", "anti_popular"] = "historico"
    window: Literal["12m", "100", "all"] = "12m"
    seed: int | None = Field(None, ge=0, description="opcional, para reproducir las mismas jugadas")


class BallCount(BaseModel):
    label: str
    count: int


class PairCount(BaseModel):
    pair: str
    count: int


class PlayHistory(BaseModel):
    draws: int
    cost: int
    won: int
    ret: float
    prize_draws: int
    best_hits: int
    hits_3plus: int
    date_from: str | None
    date_to: str | None


class PlayStats(BaseModel):
    window_draws: int
    expected_count: float
    counts: list[BallCount]
    total_count: int
    sum: int
    evens: int
    highs: int
    shape_ok: bool
    frequent_pairs: list[PairCount]
    extra_count: int | None
    extra_expected: float | None
    history: PlayHistory | None


class PlayOut(BaseModel):
    balls: list[BallOut]
    extra: int | None
    text: str  # lista para copiar
    popularity_score: int
    popularity_level: str
    popularity_reasons: list[str]
    stats: PlayStats | None = None


class GenerateOut(BaseModel):
    game: str
    mode: str
    seed: int
    plays: list[PlayOut]
    odds: Odds
    notice: str


def _text(ticket: Ticket) -> str:
    main = " - ".join(f"{n} {c}" if c else f"{n:02d}" for n, c in ticket.balls())
    return main + (f" | superbalota {ticket.extra:02d}" if ticket.extra is not None else "")


@lru_cache(maxsize=8)
def _prizes(code: str, mtime: float) -> tuple[dict, dict]:
    rows = read_prizes_csv(get_settings().raw_data_dir / f"{code}_premios.csv", code)
    by_draw: dict[int, dict] = defaultdict(dict)
    per_cat: dict[str, list[int]] = defaultdict(list)
    for r in rows:
        by_draw[r.draw_number][r.category] = r
        if r.winners:
            per_cat[r.category].append(r.prize_per_winner)
    return dict(by_draw), {c: sum(v) / len(v) for c, v in per_cat.items()}


def prize_tables(code: str) -> tuple[dict, dict]:
    path = get_settings().raw_data_dir / f"{code}_premios.csv"
    return _prizes(code, path.stat().st_mtime) if path.exists() else ({}, {})


def play_stats(ticket: Ticket, game: type[Game], history: list[DrawRecord], window: fq.Window) -> PlayStats:
    win = fq.apply_window(history, window)
    freq = fq.ball_frequency(win, game)
    balls = list(ticket.balls())
    nums = [b[0] for b in balls]
    shape = typical_shape(history, game)
    pairs = fq.combo_frequency(win, 2)
    top_pairs = {p for p, _ in pairs.most_common(30)}
    inside = []
    for a, b in combinations(sorted(balls, key=lambda x: (x[0], str(x[1]))), 2):
        if (a, b) in top_pairs:
            inside.append(PairCount(pair=f"{fq.ball_label(a)}-{fq.ball_label(b)}", count=pairs[(a, b)]))
    extra_count = extra_expected = None
    if game.extra_max and ticket.extra is not None:
        extra_count = fq.extra_frequency(win, game)[ticket.extra]
        extra_expected = len(win) / game.extra_max

    hist = None
    prizes, avg = prize_tables(game.code)
    if prizes:
        test = [r for r in history if r.draw_number in prizes]
        if test:
            r = play_ticket(game, ticket, test, prizes, avg)
            hist = PlayHistory(draws=r.draws, cost=r.cost, won=r.won, ret=r.ret, prize_draws=r.prize_draws,
                               best_hits=r.best, hits_3plus=sum(v for h, v in r.hits.items() if h >= 3),
                               date_from=test[0].draw_date.isoformat(), date_to=test[-1].draw_date.isoformat())
    return PlayStats(
        window_draws=len(win),
        expected_count=len(win) * game.main_count / game.pool_size(),
        counts=[BallCount(label=fq.ball_label(b), count=freq[b]) for b in sorted(balls, key=lambda x: (x[0], str(x[1])))],
        total_count=sum(freq[b] for b in balls),
        sum=sum(nums),
        evens=sum(n % 2 == 0 for n in nums),
        highs=sum(n > game.main_max / 2 for n in nums),
        shape_ok=shape.fits(nums, game),
        frequent_pairs=inside,
        extra_count=extra_count,
        extra_expected=extra_expected,
        history=hist,
    )


@router.post("", response_model=GenerateOut)
def generate(body: GenerateIn, session: Session = Depends(get_session)) -> GenerateOut:
    try:
        game = get_game(body.game)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from None
    history = records_from_db(session, game.code)
    if len(history) < 30:
        raise HTTPException(422, "no hay suficientes sorteos cargados")
    window = fq.parse_window(body.window)
    past = {frozenset(r.ticket.balls()) for r in history}
    seed = body.seed if body.seed is not None else secrets.randbelow(10_000_000)
    rng = random.Random(seed)

    tickets: list[Ticket] = []
    if body.mode == "historico":
        tickets = [p.ticket for p in historical_plays(history, game, body.n, rng, window)]
    else:
        seen: set[frozenset] = set()
        while len(tickets) < body.n:
            t = anti_popular(tuple(history), game, rng)
            if frozenset(t.balls()) not in seen:
                seen.add(frozenset(t.balls()))
                tickets.append(t)

    plays = []
    for t in tickets:
        p = popularity(t, game, past)
        plays.append(PlayOut(
            balls=[BallOut(number=n, color=c) for n, c in t.balls()], extra=t.extra, text=_text(t),
            popularity_score=p.score, popularity_level=p.level, popularity_reasons=p.reasons,
            stats=play_stats(t, game, history, window),
        ))
    return GenerateOut(game=game.code, mode=body.mode, seed=seed, plays=plays, odds=odds_of(game),
                       notice=NOTICES[body.mode])
