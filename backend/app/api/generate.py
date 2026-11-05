"""POST /generate: jugadas anti-populares con la probabilidad real."""

import random
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.analysis.popularity import popularity
from app.api.games import odds_of
from app.api.schemas import BallOut, Odds
from app.backtest.strategies import anti_popular
from app.db import get_session
from app.games import get_game
from app.ingest.records import records_from_db

router = APIRouter(prefix="/generate", tags=["generador"])

NOTICE = (
    "Ninguna jugada tiene más probabilidad de ganar que otra. Estas jugadas solo evitan patrones "
    "que mucha gente juega (fechas, secuencias, figuras), para que, si ganan, el premio se reparta "
    "entre menos personas."
)


class GenerateIn(BaseModel):
    game: str
    n: int = Field(5, ge=1, le=10)
    seed: int | None = Field(None, ge=0, description="opcional, para reproducir las mismas jugadas")


class PlayOut(BaseModel):
    balls: list[BallOut]
    extra: int | None
    text: str  # lista para copiar
    popularity_score: int
    popularity_level: str
    popularity_reasons: list[str]


class GenerateOut(BaseModel):
    game: str
    seed: int
    plays: list[PlayOut]
    odds: Odds
    notice: str


def _text(ticket, game) -> str:
    main = " - ".join(f"{n} {c}" if c else f"{n:02d}" for n, c in ticket.balls())
    return main + (f" | superbalota {ticket.extra:02d}" if ticket.extra is not None else "")


@router.post("", response_model=GenerateOut)
def generate(body: GenerateIn, session: Session = Depends(get_session)) -> GenerateOut:
    try:
        game = get_game(body.game)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from None
    history = tuple(records_from_db(session, game.code))
    past = {frozenset(r.ticket.balls()) for r in history}
    seed = body.seed if body.seed is not None else secrets.randbelow(10_000_000)
    rng = random.Random(seed)
    plays, seen = [], set()
    while len(plays) < body.n:
        t = anti_popular(history, game, rng)
        key = frozenset(t.balls())
        if key in seen:
            continue
        seen.add(key)
        p = popularity(t, game, past)
        plays.append(PlayOut(
            balls=[BallOut(number=n, color=c) for n, c in t.balls()], extra=t.extra, text=_text(t, game),
            popularity_score=p.score, popularity_level=p.level, popularity_reasons=p.reasons,
        ))
    return GenerateOut(game=game.code, seed=seed, plays=plays, odds=odds_of(game), notice=NOTICE)
