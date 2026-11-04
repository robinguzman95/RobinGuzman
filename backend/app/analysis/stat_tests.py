"""Pruebas de hipótesis: uniformidad (chi-cuadrado) y aleatoriedad temporal (rachas).

Chi-cuadrado corregido por extracción sin reposición
----------------------------------------------------
En cada sorteo salen K balotas *distintas* de un bombo de N. La cuenta de cada balota no es
multinomial: dentro de un sorteo las balotas se excluyen entre sí. Para el vector indicador de un
K-subconjunto, Var(X_i) = p(1-p) y Cov(X_i, X_j) = -p(1-p)/(N-1), con p = K/N. Sumado sobre n
sorteos y estandarizado como en el estadístico de Pearson, eso da

    X² = Σ (O - E)² / E  ~  c · χ²(G - 1),   c = (N - K) / (N - 1)

para cualquier agrupación de las N balotas en G grupos del mismo tamaño (balotas sueltas,
números, colores). Por eso reportamos X²/c, que sí sigue χ²(G-1). Sin la corrección la prueba
sería conservadora (p-valores inflados), p. ej. en Baloto c = 38/42.
Con K = 1 (la superbalota) c = 1 y es la prueba clásica.
"""

from dataclasses import dataclass
from math import comb, sqrt

from scipy import stats

from app.analysis.frequency import ball_frequency, color_frequency, extra_frequency, number_frequency
from app.games import Game
from app.ingest.records import DrawRecord

ALPHA = 0.05
MIN_EXPECTED = 5.0


def verdict(p_value: float | None, alpha: float = ALPHA) -> str:
    if p_value is None:
        return "sin datos suficientes"
    if p_value >= alpha:
        return "compatible con el azar"
    return "desviación significativa: revisar datos antes de concluir nada"


@dataclass(frozen=True)
class ChiSquareResult:
    label: str
    statistic: float  # ya corregido
    dof: int
    p_value: float | None
    n_draws: int
    expected_per_cell: float
    correction: float
    reliable: bool  # esperado por celda >= 5
    verdict: str


def chi_square_equal_groups(
    observed: list[int], n_draws: int, pool: int, per_draw: int, label: str
) -> ChiSquareResult:
    """``observed``: cuentas por grupo (todos los grupos del mismo tamaño ``pool/len(observed)``)."""
    g = len(observed)
    total = sum(observed)
    if n_draws == 0 or total == 0 or g < 2:
        return ChiSquareResult(label, 0.0, max(g - 1, 0), None, n_draws, 0.0, 1.0, False, verdict(None))
    expected = total / g
    c = (pool - per_draw) / (pool - 1) if per_draw > 1 else 1.0
    raw = sum((o - expected) ** 2 / expected for o in observed)
    stat = raw / c
    p = float(stats.chi2.sf(stat, g - 1))
    reliable = expected >= MIN_EXPECTED
    v = verdict(p) if reliable else "pocos datos (esperado < 5 por celda): no concluyente"
    return ChiSquareResult(label, stat, g - 1, p, n_draws, expected, c, reliable, v)


def uniformity_tests(records: list[DrawRecord], game: type[Game]) -> list[ChiSquareResult]:
    """Pruebas de uniformidad que aplican al juego."""
    n = len(records)
    pool, k = game.pool_size(), game.main_count
    out = [
        chi_square_equal_groups(list(ball_frequency(records, game).values()), n, pool, k,
                                "balotas" if game.colors else "números"),
    ]
    if game.colors:
        out.append(chi_square_equal_groups(list(number_frequency(records, game).values()), n, pool, k, "números"))
        out.append(chi_square_equal_groups(list(color_frequency(records, game).values()), n, pool, k, "colores"))
    if game.extra_max:
        out.append(chi_square_equal_groups(list(extra_frequency(records, game).values()), n, game.extra_max, 1,
                                           "superbalota"))
    return out


# --- rachas (Wald–Wolfowitz) -------------------------------------------------------
@dataclass(frozen=True)
class RunsResult:
    runs: int
    expected_runs: float
    z: float
    p_value: float


def runs_pmf(n1: int, n2: int) -> dict[int, float]:
    """Distribución exacta del número de rachas con n1 éxitos y n2 fracasos (todas las
    permutaciones equiprobables)."""
    total = comb(n1 + n2, n1)
    pmf: dict[int, float] = {}
    for r in range(2, n1 + n2 + 1):
        k, odd = divmod(r, 2)
        if odd:
            ways = comb(n1 - 1, k) * comb(n2 - 1, k - 1) + comb(n1 - 1, k - 1) * comb(n2 - 1, k)
        else:
            ways = 2 * comb(n1 - 1, k - 1) * comb(n2 - 1, k - 1)
        if ways:
            pmf[r] = ways / total
    return pmf


def runs_test(sequence: list[bool]) -> RunsResult | None:
    """Prueba de rachas de Wald–Wolfowitz, dos colas, con p-valor EXACTO.

    Aquí casi siempre una de las dos clases es pequeña (una balota sale en ~1 de cada 7 a 9
    sorteos), y ahí la aproximación normal exagera la significancia. Ejemplo real: 7-blanco en
    ColorLoto daba p = 0,0009 con la normal y p = 0,0055 exacto. ``z`` se reporta solo como
    referencia. None si la secuencia es constante.
    """
    n1 = sum(sequence)
    n2 = len(sequence) - n1
    if n1 == 0 or n2 == 0:
        return None
    n = n1 + n2
    runs = 1 + sum(1 for a, b in zip(sequence, sequence[1:]) if a != b)
    mu = 1 + 2 * n1 * n2 / n
    var = 2 * n1 * n2 * (2 * n1 * n2 - n) / (n**2 * (n - 1))
    z = (runs - mu) / sqrt(var) if var > 0 else 0.0
    pmf = runs_pmf(n1, n2)
    low = sum(p for r, p in pmf.items() if r <= runs)
    high = sum(p for r, p in pmf.items() if r >= runs)
    return RunsResult(runs, mu, z, min(1.0, 2 * min(low, high)))


@dataclass(frozen=True)
class RunsSummary:
    tested: int
    alpha_bonferroni: float
    significant_raw: int  # p < 0.05 sin corregir (se esperan ~5% por azar)
    significant_bonferroni: list[str]  # balotas que pasan la corrección
    min_p_value: float | None
    verdict: str


def runs_by_ball(records: list[DrawRecord], game: type[Game], alpha: float = ALPHA) -> RunsSummary:
    """Para cada balota, la secuencia sale/no sale a lo largo de los sorteos. Muchas pruebas a la
    vez: se corrige con Bonferroni (alpha / número de pruebas)."""
    from app.analysis.frequency import all_balls, ball_label

    recs = sorted(records, key=lambda r: r.draw_number)
    present = [set(r.ticket.balls()) for r in recs]
    results = {}
    for ball in all_balls(game):
        res = runs_test([ball in s for s in present])
        if res is not None:
            results[ball] = res
    m = len(results)
    if m == 0:
        return RunsSummary(0, alpha, 0, [], None, verdict(None))
    alpha_b = alpha / m
    sig = [ball_label(b) for b, r in results.items() if r.p_value < alpha_b]
    min_p = min(r.p_value for r in results.values())
    v = "compatible con el azar" if not sig else f"{len(sig)} balota(s) con rachas atípicas: revisar"
    return RunsSummary(m, alpha_b, sum(r.p_value < alpha for r in results.values()), sig, min_p, v)
