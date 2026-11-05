"""Motor de backtest con ventana móvil, sin mirar al futuro.

Para cada sorteo t del periodo de prueba:
1. la estrategia recibe SOLO los ``window`` sorteos inmediatamente anteriores a t (tupla
   inmutable); el motor verifica que todos tengan número de sorteo < t y falla si no;
2. genera una jugada, que se valida contra la matriz del juego;
3. se cuentan los aciertos contra t.

Luego se compara el promedio con la línea base Monte Carlo del mismo número de sorteos.
"""

import random
from collections import Counter
from dataclasses import dataclass
from datetime import date

from app.backtest.montecarlo import DEFAULT_SIMS, Baseline, baseline
from app.backtest.strategies import Strategy
from app.games import Game
from app.ingest.records import DrawRecord

ALPHA = 0.05
PRIMARY_WINDOW = 100  # ventana principal declarada ANTES de correr (ver CLAUDE.md)
SENSITIVITY_WINDOWS = (50, 200)


class LookAheadError(RuntimeError):
    """La historia entregada a la estrategia contiene el sorteo evaluado o uno posterior."""


@dataclass(frozen=True)
class DrawHit:
    draw_number: int
    draw_date: date
    hits: int
    extra_hit: bool | None


@dataclass(frozen=True)
class BacktestOutcome:
    game: str
    strategy: str
    window: int
    seed: int
    date_from: date
    date_to: date
    n_draws: int
    avg_hits: float
    hit_distribution: dict[int, int]  # aciertos -> número de sorteos
    extra_hit_rate: float | None
    baseline: Baseline
    p_value: float
    per_draw: list[DrawHit]

    def series(self) -> list[dict]:
        """Promedio acumulado de la estrategia frente a la banda p5–p95 del azar."""
        out, total, j = [], 0, 0
        cps = set(self.baseline.checkpoints)
        for i, d in enumerate(self.per_draw):
            total += d.hits
            if i in cps:
                out.append({
                    "draw_number": d.draw_number,
                    "draw_date": d.draw_date.isoformat(),
                    "strategy": total / (i + 1),
                    "p5": self.baseline.band_p5[j],
                    "p95": self.baseline.band_p95[j],
                })
                j += 1
        return out

    @property
    def above_p95(self) -> bool:
        return self.avg_hits > self.baseline.p95

    def verdict(self, alpha: float = ALPHA) -> str:
        if self.p_value < alpha and self.above_p95:
            return "le gana al azar (revisar: con datos aleatorios esto pasa 1 de cada 20 veces)"
        return "dentro de la banda aleatoria: no le gana al azar"


def _rng_for(seed: int, draw_number: int) -> random.Random:
    # Semilla por sorteo: reproducible y sin depender del orden en que se evalúa.
    return random.Random(seed * 1_000_003 + draw_number)


def run_backtest(
    records: list[DrawRecord],
    game: type[Game],
    strategy: Strategy,
    strategy_name: str,
    window: int = PRIMARY_WINDOW,
    date_from: date | None = None,
    date_to: date | None = None,
    seed: int = 0,
    sims: int = DEFAULT_SIMS,
) -> BacktestOutcome:
    if window < 1:
        raise ValueError("la ventana debe ser de al menos 1 sorteo")
    recs = sorted(records, key=lambda r: r.draw_number)
    targets = [
        i for i in range(window, len(recs))
        if (date_from is None or recs[i].draw_date >= date_from)
        and (date_to is None or recs[i].draw_date <= date_to)
    ]
    if not targets:
        raise ValueError(
            f"no hay sorteos para evaluar: {len(recs)} sorteos y ventana de {window}"
            " (cada sorteo evaluado necesita la ventana completa antes)"
        )

    per_draw: list[DrawHit] = []
    for i in targets:
        target = recs[i]
        history = tuple(recs[i - window: i])
        if any(h.draw_number >= target.draw_number for h in history):
            raise LookAheadError(f"la historia del sorteo {target.draw_number} incluye sorteos ≥ t")
        ticket = strategy(history, game, _rng_for(seed, target.draw_number))
        problems = game.validate(ticket)
        if problems:
            raise ValueError(f"{strategy_name} generó una jugada inválida para el sorteo "
                             f"{target.draw_number}: {'; '.join(problems)}")
        hits = len(set(ticket.balls()) & set(target.ticket.balls()))
        extra_hit = (ticket.extra == target.extra) if game.extra_max else None
        per_draw.append(DrawHit(target.draw_number, target.draw_date, hits, extra_hit))

    n = len(per_draw)
    avg = sum(d.hits for d in per_draw) / n
    dist_counts = Counter(d.hits for d in per_draw)
    dist = {k: dist_counts.get(k, 0) for k in range(game.main_count + 1)}
    extra_rate = sum(bool(d.extra_hit) for d in per_draw) / n if game.extra_max else None
    base = baseline(game, n, sims=sims, seed=seed)
    return BacktestOutcome(
        game=game.code, strategy=strategy_name, window=window, seed=seed,
        date_from=recs[targets[0]].draw_date, date_to=recs[targets[-1]].draw_date,
        n_draws=n, avg_hits=avg, hit_distribution=dist, extra_hit_rate=extra_rate,
        baseline=base, p_value=base.p_value(avg), per_draw=per_draw,
    )
