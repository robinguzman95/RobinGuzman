"""Análisis de potencia: ¿qué tan grande tendría que ser un efecto para que lo viéramos?

"No encontramos sesgo" solo es informativo si los datos podían encontrarlo. Aquí se calcula el
efecto mínimo detectable con probabilidad ``power`` (80 % por defecto) dados los sorteos que
hay. Ambos cálculos se validan por simulación en tests/test_power.py.

1) Sesgo de una balota (prueba chi-cuadrado de uniformidad, con la misma corrección por
   extracción sin reposición de stat_tests.py). Alternativa: una balota sale con probabilidad
   (1 + δ) veces la normal y las demás se reducen en proporción. Bajo esa alternativa el
   estadístico corregido sigue aproximadamente una chi-cuadrado no central con
   gl = G − 1 y λ = n·K·Σ (q₁ − q₀)² / q₀ / c.

2) Ventaja de una estrategia en el backtest. Los aciertos por sorteo de cualquier jugada que
   solo usa el pasado son hipergeométricos H(N, K, K), con media K²/N y varianza
   σ² = K·(K/N)·(1 − K/N)·(N − K)/(N − 1). Para detectar una mejora Δ en el promedio de n
   sorteos con una prueba de una cola a nivel α/m (Bonferroni sobre m combinaciones):
   Δ = (z_{1−α/m} + z_{power}) · σ / √n.
"""

from dataclasses import dataclass
from math import sqrt

from scipy import optimize, stats

from app.games import Game

ALPHA = 0.05


@dataclass(frozen=True)
class BallBiasPower:
    n_draws: int
    groups: int
    min_relative_bias: float  # δ: la balota sale (1 + δ) veces lo normal
    expected_count: float  # veces que sale una balota normal en n sorteos
    biased_count: float  # veces que saldría la balota sesgada
    power: float
    alpha: float


def _ball_noncentrality(game: type[Game], n_draws: int, delta: float) -> tuple[float, int]:
    g = game.pool_size()
    k = game.main_count
    q0 = 1 / g
    q_biased = q0 * (1 + delta)
    q_rest = (1 - q_biased) / (g - 1)
    c = (g - k) / (g - 1) if k > 1 else 1.0
    lam = n_draws * k * ((q_biased - q0) ** 2 / q0 + (g - 1) * (q_rest - q0) ** 2 / q0) / c
    return lam, g - 1


def ball_bias_power(game: type[Game], n_draws: int, delta: float, alpha: float = ALPHA) -> float:
    lam, df = _ball_noncentrality(game, n_draws, delta)
    crit = stats.chi2.isf(alpha, df)
    return float(stats.ncx2.sf(crit, df, lam))


def min_detectable_ball_bias(game: type[Game], n_draws: int, power: float = 0.8,
                             alpha: float = ALPHA) -> BallBiasPower:
    g = game.pool_size()
    hi = 1.0
    while ball_bias_power(game, n_draws, hi, alpha) < power and hi < g - 1:
        hi *= 2
    hi = min(hi, g - 1.001)
    delta = optimize.brentq(lambda d: ball_bias_power(game, n_draws, d, alpha) - power, 1e-6, hi)
    expected = n_draws * game.main_count / g
    return BallBiasPower(n_draws, g, delta, expected, expected * (1 + delta), power, alpha)


@dataclass(frozen=True)
class BacktestPower:
    n_draws: int
    comparisons: int
    mean_hits: float  # K²/N
    sd_hits: float  # σ por sorteo
    min_improvement: float  # Δ absoluto en aciertos por sorteo
    min_relative_improvement: float  # Δ / media
    power: float
    alpha: float


def hits_sd(game: type[Game]) -> float:
    n, k = game.pool_size(), game.main_count
    p = k / n
    return sqrt(k * p * (1 - p) * (n - k) / (n - 1))


def min_detectable_improvement(game: type[Game], n_draws: int, comparisons: int = 60, power: float = 0.8,
                               alpha: float = ALPHA) -> BacktestPower:
    mean = game.main_count ** 2 / game.pool_size()
    sd = hits_sd(game)
    z = stats.norm.isf(alpha / comparisons) + stats.norm.ppf(power)
    delta = z * sd / sqrt(n_draws)
    return BacktestPower(n_draws, comparisons, mean, sd, delta, delta / mean, power, alpha)
