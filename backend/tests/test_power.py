"""Las fórmulas de potencia se validan contra simulación: el efecto mínimo detectable debe
detectarse ~80 % de las veces."""

import random

import numpy as np
import pytest

from app.analysis.power import ball_bias_power, min_detectable_ball_bias, min_detectable_improvement
from app.analysis.stat_tests import uniformity_tests
from app.games import get_game
from app.ingest.records import DrawRecord
from datetime import date


def biased_draws(n: int, delta: float, rng: random.Random) -> list[DrawRecord]:
    """MiLoto donde el número 7 pesa (1 + δ') en cada extracción, con δ' calibrado para que su
    frecuencia final sea ~(1 + δ) veces la normal."""
    out = []
    for i in range(n):
        pool = list(range(1, 40))
        picks = []
        while len(picks) < 5:
            w = [(1 + delta * 1.12) if x == 7 else 1.0 for x in pool]
            x = rng.choices(pool, w)[0]
            picks.append(x)
            pool.remove(x)
        out.append(DrawRecord("miloto", i + 1, date(2020, 1, 1), tuple(picks)))
    return out


def test_power_increases_with_bias_and_draws():
    g = get_game("miloto")
    assert ball_bias_power(g, 600, 0.0) == pytest.approx(0.05, abs=1e-6)
    assert ball_bias_power(g, 600, 0.3) < ball_bias_power(g, 600, 0.6)
    assert ball_bias_power(g, 300, 0.5) < ball_bias_power(g, 1200, 0.5)


def test_min_detectable_bias_is_detected_about_80_percent():
    g = get_game("miloto")
    n = 600
    mdb = min_detectable_ball_bias(g, n)
    assert 0.2 < mdb.min_relative_bias < 1.0
    rng = random.Random(11)
    reps = 150
    hits = 0
    for _ in range(reps):
        recs = biased_draws(n, mdb.min_relative_bias, rng)
        counts = [sum(7 in r.numbers for r in recs)]
        hits += uniformity_tests(recs, g)[0].p_value < 0.05
    assert 0.65 <= hits / reps <= 0.93, (hits / reps, mdb.min_relative_bias)


def test_backtest_min_improvement_detected_about_80_percent():
    g = get_game("baloto")
    n, m = 550, 60
    bp = min_detectable_improvement(g, n, comparisons=m)
    assert bp.mean_hits == pytest.approx(25 / 43)
    rng = np.random.default_rng(5)
    # Simula promedios bajo H0 (para el umbral) y bajo H1 = H0 + Δ.
    sims = 40_000
    null = rng.hypergeometric(5, 38, 5, size=(sims, n)).mean(axis=1)
    threshold = np.quantile(null, 1 - 0.05 / m)
    alt = null[:4000] + bp.min_improvement
    detected = float((alt > threshold).mean())
    assert 0.7 <= detected <= 0.9, detected


def test_more_draws_detect_smaller_improvements():
    g = get_game("baloto")
    assert min_detectable_improvement(g, 2000).min_improvement < min_detectable_improvement(g, 500).min_improvement
