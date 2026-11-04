"""Estrategias de juego como funciones puras: (historia, juego, rng) -> jugada.

- ``history`` es una tupla inmutable con los sorteos ANTERIORES al evaluado (el motor
  garantiza que no contiene el sorteo evaluado ni posteriores).
- ``rng`` es un random.Random con semilla: misma semilla, misma jugada. Ninguna estrategia
  usa el módulo random global.
- Toda jugada devuelta es válida para el juego (ColorLoto: pares número-color distintos).
"""

import random
from collections.abc import Callable

from app.analysis import frequency as fq
from app.analysis.popularity import popularity
from app.games import Game, Ticket
from app.ingest.records import DrawRecord

History = tuple[DrawRecord, ...]
Strategy = Callable[[History, type[Game], random.Random], Ticket]


def _ticket_from_balls(balls: list[fq.Ball], game: type[Game], extra: int | None) -> Ticket:
    balls = sorted(balls, key=lambda b: (b[0], str(b[1])))
    numbers = tuple(n for n, _ in balls)
    colors = tuple(c for _, c in balls) if game.colors else None
    return Ticket(numbers, colors, extra)


def _random_extra(game: type[Game], rng: random.Random) -> int | None:
    return rng.randint(1, game.extra_max) if game.extra_max else None


def _ranked_extra(history: History, game: type[Game], reverse: bool) -> int | None:
    """Superbalota más (reverse=True) o menos frecuente; empate -> número menor."""
    freq = fq.extra_frequency(list(history), game)
    if freq is None:
        return None
    return sorted(freq, key=lambda n: (-freq[n] if reverse else freq[n], n))[0]


def random_play(history: History, game: type[Game], rng: random.Random) -> Ticket:
    """Línea base: jugada uniforme al azar."""
    balls = rng.sample(fq.all_balls(game), game.main_count)
    return _ticket_from_balls(balls, game, _random_extra(game, rng))


def hot(history: History, game: type[Game], rng: random.Random) -> Ticket:
    """Las K balotas más frecuentes de la ventana."""
    top, _ = fq.hot_cold(list(history), game, n=game.main_count)
    return _ticket_from_balls([s.ball for s in top], game, _ranked_extra(history, game, reverse=True))


def cold(history: History, game: type[Game], rng: random.Random) -> Ticket:
    """Las K menos frecuentes ("ya les toca")."""
    _, bottom = fq.hot_cold(list(history), game, n=game.main_count)
    return _ticket_from_balls([s.ball for s in bottom], game, _ranked_extra(history, game, reverse=False))


def overdue(history: History, game: type[Game], rng: random.Random) -> Ticket:
    """Las K que llevan más sorteos sin salir."""
    stats = fq.overdue(list(history), game, n=game.main_count)
    extra = None
    if game.extra_max:
        last: dict[int, int] = {}
        for i, r in enumerate(sorted(history, key=lambda r: r.draw_number)):
            last[r.extra] = i
        extra = sorted(range(1, game.extra_max + 1), key=lambda n: (last.get(n, -1), n))[0]
    return _ticket_from_balls([s.ball for s in stats], game, extra)


ANTI_POPULAR_MAX_SCORE = 10
ANTI_POPULAR_TRIES = 200


def anti_popular(history: History, game: type[Game], rng: random.Random) -> Ticket:
    """Aleatoria, pero rechaza jugadas con puntaje de popularidad > 10. No intenta acertar más:
    busca que, si gana, el premio se reparta con menos gente."""
    past = {frozenset(r.ticket.balls()) for r in history}
    best: tuple[int, Ticket] | None = None
    for _ in range(ANTI_POPULAR_TRIES):
        t = random_play(history, game, rng)
        s = popularity(t, game, past).score
        if s <= ANTI_POPULAR_MAX_SCORE:
            return t
        if best is None or s < best[0]:
            best = (s, t)
    return best[1]


STRATEGIES: dict[str, Strategy] = {
    "random": random_play,
    "hot": hot,
    "cold": cold,
    "overdue": overdue,
    "anti_popular": anti_popular,
}


def get_strategy(name: str) -> Strategy:
    try:
        return STRATEGIES[name]
    except KeyError:
        raise ValueError(f"estrategia desconocida {name!r}; opciones: {', '.join(STRATEGIES)}") from None
