"""Frecuencias, calientes/fríos, combinaciones frecuentes y forma de las jugadas.

Unidad de conteo: la *balota*, un par (número, color). En juegos sin color el color es None.
En ColorLoto hay 42 balotas distintas; además se reportan los marginales por número y color.
"""

from collections import Counter
from dataclasses import dataclass
from datetime import timedelta
from itertools import combinations

from app.games import Game
from app.ingest.records import DrawRecord

Ball = tuple[int, str | None]


def all_balls(game: type[Game]) -> list[Ball]:
    colors = game.colors or (None,)
    return [(n, c) for c in colors for n in range(1, game.main_max + 1)]


def ball_label(ball: Ball) -> str:
    n, c = ball
    return f"{n}-{c}" if c else str(n)


# --- ventanas ----------------------------------------------------------------------
Window = int | str  # "all", "12m" (meses) o un entero = últimos N sorteos


def parse_window(raw: str | int | None) -> Window:
    if raw is None or raw == "":
        return "12m"
    if isinstance(raw, int):
        if raw <= 0:
            raise ValueError("la ventana debe ser positiva")
        return raw
    raw = raw.strip().lower()
    if raw == "all":
        return "all"
    if raw.endswith("m") and raw[:-1].isdigit() and int(raw[:-1]) > 0:
        return raw
    if raw.isdigit() and int(raw) > 0:
        return int(raw)
    raise ValueError(f"ventana inválida {raw!r}: use 'all', '<n>m' (meses) o un número de sorteos")


def apply_window(records: list[DrawRecord], window: Window) -> list[DrawRecord]:
    """Ordena por número de sorteo y recorta. Los meses se cuentan hacia atrás desde el último
    sorteo de la lista (no desde hoy), para que el resultado sea reproducible."""
    recs = sorted(records, key=lambda r: r.draw_number)
    if not recs or window == "all":
        return recs
    if isinstance(window, int):
        return recs[-window:]
    months = int(window[:-1])
    cutoff = recs[-1].draw_date - timedelta(days=round(months * 30.4375))
    return [r for r in recs if r.draw_date > cutoff]


# --- frecuencias -------------------------------------------------------------------
def ball_frequency(records: list[DrawRecord], game: type[Game]) -> dict[Ball, int]:
    """Veces que salió cada balota principal (incluye las que no salieron, con 0)."""
    counts = Counter(b for r in records for b in r.ticket.balls())
    return {b: counts.get(b, 0) for b in all_balls(game)}


def number_frequency(records: list[DrawRecord], game: type[Game]) -> dict[int, int]:
    """Marginal por número (en ColorLoto suma todos los colores)."""
    counts = Counter(n for r in records for n in r.numbers)
    return {n: counts.get(n, 0) for n in range(1, game.main_max + 1)}


def color_frequency(records: list[DrawRecord], game: type[Game]) -> dict[str, int] | None:
    if not game.colors:
        return None
    counts = Counter(c for r in records for c in (r.colors or ()))
    return {c: counts.get(c, 0) for c in game.colors}


def extra_frequency(records: list[DrawRecord], game: type[Game]) -> dict[int, int] | None:
    if game.extra_max is None:
        return None
    counts = Counter(r.extra for r in records)
    return {n: counts.get(n, 0) for n in range(1, game.extra_max + 1)}


# --- calientes y fríos -------------------------------------------------------------
@dataclass(frozen=True)
class BallStat:
    ball: Ball
    count: int
    draws_since: int | None  # 0 = salió en el último sorteo; None = no salió en la ventana
    days_since: int | None

    @property
    def label(self) -> str:
        return ball_label(self.ball)


def ball_stats(records: list[DrawRecord], game: type[Game]) -> list[BallStat]:
    recs = sorted(records, key=lambda r: r.draw_number)
    freq = ball_frequency(recs, game)
    last_idx: dict[Ball, int] = {}
    for i, r in enumerate(recs):
        for b in r.ticket.balls():
            last_idx[b] = i
    out = []
    for b in all_balls(game):
        i = last_idx.get(b)
        if i is None:
            out.append(BallStat(b, freq[b], None, None))
        else:
            out.append(BallStat(b, freq[b], len(recs) - 1 - i, (recs[-1].draw_date - recs[i].draw_date).days))
    return out


def _since_key(s: BallStat) -> int:
    return s.draws_since if s.draws_since is not None else 10**9


def hot_cold(records: list[DrawRecord], game: type[Game], n: int = 10) -> tuple[list[BallStat], list[BallStat]]:
    """Top n y bottom n por frecuencia. Empates: calientes = salió más reciente; fríos = lleva
    más sin salir; después, número menor. El orden es determinista."""
    stats = ball_stats(records, game)
    hot = sorted(stats, key=lambda s: (-s.count, _since_key(s), s.ball[0], str(s.ball[1])))[:n]
    cold = sorted(stats, key=lambda s: (s.count, -_since_key(s), s.ball[0], str(s.ball[1])))[:n]
    return hot, cold


def overdue(records: list[DrawRecord], game: type[Game], n: int = 10) -> list[BallStat]:
    """Las n balotas que llevan más sorteos sin salir."""
    stats = ball_stats(records, game)
    return sorted(stats, key=lambda s: (-_since_key(s), s.count, s.ball[0], str(s.ball[1])))[:n]


# --- combinaciones frecuentes ------------------------------------------------------
def combo_frequency(records: list[DrawRecord], k: int) -> Counter[tuple[Ball, ...]]:
    """Cuántas veces salieron juntas cada combinación de k balotas."""
    counts: Counter[tuple[Ball, ...]] = Counter()
    for r in records:
        balls = sorted(r.ticket.balls(), key=lambda b: (b[0], str(b[1])))
        counts.update(combinations(balls, k))
    return counts


def top_combos(records: list[DrawRecord], k: int, top: int = 10) -> list[tuple[tuple[Ball, ...], int]]:
    counts = combo_frequency(records, k)
    return sorted(counts.items(), key=lambda kv: (-kv[1], [(b[0], str(b[1])) for b in kv[0]]))[:top]


# --- forma de las jugadas ----------------------------------------------------------
@dataclass(frozen=True)
class ShapeStats:
    sum_min: int
    sum_max: int
    sum_mean: float
    sums: dict[int, int]  # suma -> veces
    even_counts: dict[int, int]  # cuántos pares tenía el sorteo -> veces
    high_counts: dict[int, int]  # cuántos altos (> main_max/2) -> veces


def shape_stats(records: list[DrawRecord], game: type[Game]) -> ShapeStats | None:
    if not records:
        return None
    sums = [sum(r.numbers) for r in records]
    k = game.main_count
    evens = Counter(sum(1 for n in r.numbers if n % 2 == 0) for r in records)
    highs = Counter(sum(1 for n in r.numbers if n > game.main_max / 2) for r in records)
    return ShapeStats(
        sum_min=min(sums),
        sum_max=max(sums),
        sum_mean=sum(sums) / len(sums),
        sums=dict(sorted(Counter(sums).items())),
        even_counts={i: evens.get(i, 0) for i in range(k + 1)},
        high_counts={i: highs.get(i, 0) for i in range(k + 1)},
    )
