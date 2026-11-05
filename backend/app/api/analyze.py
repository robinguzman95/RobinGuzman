"""POST /analyze: el usuario escribe su jugada y recibe el mismo resumen que el generador.

Además de lo del generador (veces que salió cada balota, forma, parejas frecuentes, probabilidad
según el modelo de ML, popularidad y cuánto habría ganado el último año), agrega lo que solo tiene
sentido para una jugada propia: si esa combinación exacta ya salió y su mejor resultado en todo el
histórico.
"""

from collections import Counter
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.analysis import frequency as fq
from app.api.games import odds_of
from app.api.generate import PlayOut, build_play
from app.api.schemas import BallOut, Odds
from app.db import get_session
from app.games import Ticket, get_game
from app.ingest.records import records_from_db

router = APIRouter(prefix="/analyze", tags=["mi jugada"])

NOTICE = (
    "Este es el resumen de tu jugada con los datos reales. Ninguna jugada tiene más probabilidad de "
    "ganar que otra: cada sorteo es independiente."
)


class AnalyzeIn(BaseModel):
    game: str
    balls: list[BallOut] = Field(min_length=1, max_length=6)
    extra: int | None = None
    window: Literal["12m", "100", "all"] = "12m"


class DrawRef(BaseModel):
    draw_number: int
    draw_date: str
    hits: int
    extra_hit: bool | None


class AllHistory(BaseModel):
    draws: int
    date_from: str
    date_to: str
    hits: dict[int, int]  # aciertos -> veces en todo el histórico
    exact_matches: list[DrawRef]  # sorteos en que salió exactamente esta combinación
    best: list[DrawRef]  # sorteos con más aciertos (hasta 5)


class AnalyzeOut(BaseModel):
    game: str
    name: str
    play: PlayOut
    all_history: AllHistory
    odds: Odds
    notice: str


@router.post("", response_model=AnalyzeOut)
def analyze(body: AnalyzeIn, session: Session = Depends(get_session)) -> AnalyzeOut:
    try:
        game = get_game(body.game)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from None
    if game.colors and any(b.color is None for b in body.balls):
        raise HTTPException(422, "en ColorLoto cada balota necesita su color")
    ordered = sorted(body.balls, key=lambda b: (b.number, str(b.color)))  # el orden no importa
    colors = tuple(b.color for b in ordered) if game.colors else None
    ticket = Ticket(tuple(b.number for b in ordered), colors, body.extra)
    problems = game.validate(ticket)
    if problems:
        raise HTTPException(422, "jugada inválida: " + "; ".join(problems))
    history = records_from_db(session, game.code)
    if len(history) < 30:
        raise HTTPException(422, "no hay suficientes sorteos cargados")
    window = fq.parse_window(body.window)
    past = {frozenset(r.ticket.balls()) for r in history}

    ml_main = ml_extra = None
    if len(history) >= 150:
        from app.api.ml import next_draw

        ml_main = next_draw(game, history, "gb", "main")
        ml_extra = next_draw(game, history, "gb", "extra") if game.extra_max else None
    play = build_play(ticket, game, history, window, past, ml_main, ml_extra)

    mine = set(ticket.balls())
    refs = []
    for r in history:
        h = len(mine & set(r.ticket.balls()))
        refs.append(DrawRef(draw_number=r.draw_number, draw_date=r.draw_date.isoformat(), hits=h,
                            extra_hit=(ticket.extra == r.extra) if game.extra_max else None))
    exact = [x for x in refs if x.hits == game.main_count]
    best = sorted(refs, key=lambda x: (-x.hits, -int(bool(x.extra_hit)), -x.draw_number))[:5]
    hits = dict(sorted(Counter(x.hits for x in refs).items()))
    dates = sorted(r.draw_date for r in history)
    return AnalyzeOut(
        game=game.code, name=game.name, play=play,
        all_history=AllHistory(draws=len(history), date_from=dates[0].isoformat(), date_to=dates[-1].isoformat(),
                               hits=hits, exact_matches=exact, best=best),
        odds=odds_of(game), notice=NOTICE,
    )
