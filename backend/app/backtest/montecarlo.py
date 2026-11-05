"""Línea base aleatoria por Monte Carlo.

Si los sorteos son aleatorios, una jugada que solo usa información del pasado acierta, en cada
sorteo, como una jugada al azar: el número de aciertos sigue una hipergeométrica
H(N, K, K) (bombo de N balotas, K ganadoras, K elegidas), sin importar cuál fue el resultado.
Por eso simulamos directamente aciertos hipergeométricos: es exactamente equivalente a jugar
10.000 jugadas aleatorias contra los mismos sorteos, y mucho más rápido.

Media teórica por sorteo: K·K/N (Baloto 25/43 ≈ 0,581; MiLoto 25/39; ColorLoto 36/42).
"""

from dataclasses import dataclass

import numpy as np

from app.games import Game

DEFAULT_SIMS = 10_000


SERIES_POINTS = 60


def checkpoints(n_draws: int, points: int = SERIES_POINTS) -> list[int]:
    """Índices (0-based) del periodo donde se mide el promedio acumulado; siempre incluye el último."""
    return sorted({int(round(x)) for x in np.linspace(0, n_draws - 1, min(points, n_draws))})


@dataclass(frozen=True)
class Baseline:
    sims: int
    n_draws: int
    mean: float
    p5: float
    p95: float
    theoretical_mean: float
    means: np.ndarray  # promedio de aciertos de cada simulación (para el p-valor)
    # Banda del promedio ACUMULADO en ``checkpoints`` (para la gráfica de la Fase 4).
    checkpoints: tuple[int, ...] = ()
    band_p5: tuple[float, ...] = ()
    band_p95: tuple[float, ...] = ()

    def p_value(self, strategy_mean: float) -> float:
        """Una cola: P(azar >= estrategia), con corrección +1 para no reportar p = 0."""
        return float((1 + np.sum(self.means >= strategy_mean - 1e-12)) / (self.sims + 1))


def theoretical_mean(game: type[Game]) -> float:
    k = game.main_count
    return k * k / game.pool_size()


def baseline(game: type[Game], n_draws: int, sims: int = DEFAULT_SIMS, seed: int = 0) -> Baseline:
    if n_draws <= 0:
        raise ValueError("el periodo de prueba no tiene sorteos")
    rng = np.random.default_rng(seed)
    k, n = game.main_count, game.pool_size()
    hits = rng.hypergeometric(ngood=k, nbad=n - k, nsample=k, size=(sims, n_draws)).astype(np.int8)
    means = hits.mean(axis=1)
    idx = checkpoints(n_draws)
    cum = np.cumsum(hits, axis=1, dtype=np.int32)[:, idx] / (np.asarray(idx) + 1)
    return Baseline(
        checkpoints=tuple(idx),
        band_p5=tuple(float(x) for x in np.percentile(cum, 5, axis=0)),
        band_p95=tuple(float(x) for x in np.percentile(cum, 95, axis=0)),
        sims=sims,
        n_draws=n_draws,
        mean=float(means.mean()),
        p5=float(np.percentile(means, 5)),
        p95=float(np.percentile(means, 95)),
        theoretical_mean=theoretical_mean(game),
        means=means,
    )
