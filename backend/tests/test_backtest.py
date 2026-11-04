"""Criterios de salida de la Fase 3:
1. una prueba demuestra que el motor nunca ve el sorteo evaluado;
2. la estrategia ``random`` cae en la media aleatoria.
"""

import random

import pytest

from app.backtest.engine import run_backtest
from app.backtest.montecarlo import baseline, theoretical_mean
from app.backtest.strategies import STRATEGIES, get_strategy
from app.games import Ticket, get_game

from tests.conftest import simulate_draws

BALOTO = get_game("baloto")
SIMS = 2_000  # suficiente para las pruebas; producción usa 10.000


# --- 1. sin mirar al futuro --------------------------------------------------------
def test_strategy_only_sees_strictly_previous_draws():
    recs = simulate_draws("baloto", 80, seed=1)
    seen = []

    def spy(history, game, rng):
        seen.append(tuple(h.draw_number for h in history))
        return Ticket((1, 2, 3, 4, 5), extra=1)

    out = run_backtest(recs, BALOTO, spy, "spy", window=20, sims=SIMS)
    assert len(seen) == out.n_draws == 60
    for numbers, evaluated in zip(seen, out.per_draw):
        t = evaluated.draw_number
        assert max(numbers) < t, "la estrategia vio el sorteo evaluado o uno posterior"
        # Ventana exacta: los 20 sorteos inmediatamente anteriores, en orden.
        assert numbers == tuple(range(t - 20, t))


def test_history_is_immutable():
    recs = simulate_draws("miloto", 30, seed=2)

    def mutator(history, game, rng):
        with pytest.raises((TypeError, AttributeError)):
            history.append(recs[-1])  # type: ignore[attr-defined]
        return Ticket((1, 2, 3, 4, 5))

    run_backtest(recs, get_game("miloto"), mutator, "mutator", window=10, sims=SIMS)


def test_oracle_cannot_cheat():
    """'Oráculo' que copia el sorteo más reciente que recibe. Si el motor filtrara el sorteo
    evaluado, acertaría 5 de 5 siempre; sin fuga, acierta como el azar (~0,58)."""
    recs = simulate_draws("baloto", 300, seed=3)

    def oracle(history, game, rng):
        last = history[-1]
        return Ticket(last.numbers, extra=last.extra)

    out = run_backtest(recs, BALOTO, oracle, "oracle", window=10, sims=SIMS)
    assert out.avg_hits < 1.0
    assert out.baseline.p5 <= out.avg_hits <= out.baseline.p95 or out.p_value > 0.001


def test_results_do_not_depend_on_future_draws():
    """Cambiar los sorteos posteriores a t no puede cambiar la jugada para t."""
    from dataclasses import replace

    recs = simulate_draws("miloto", 120, seed=4)
    other = simulate_draws("miloto", 120, seed=99)
    altered = recs[:100] + [replace(r, numbers=o.numbers) for r, o in zip(recs[100:], other[100:])]
    assert altered[100:] != recs[100:]
    game = get_game("miloto")
    for name in STRATEGIES:
        a = run_backtest(recs, game, get_strategy(name), name, window=50, sims=SIMS)
        b = run_backtest(altered, game, get_strategy(name), name, window=50, sims=SIMS)
        # Los sorteos evaluados 51..100 solo dependen de sorteos <= 100, que no cambiaron.
        assert a.per_draw[:50] == b.per_draw[:50], name
        assert a.per_draw[50:] != b.per_draw[50:] or name == "random"


# --- 2. la línea base --------------------------------------------------------------
@pytest.mark.parametrize("code", ["baloto", "miloto", "colorloto"])
def test_baseline_matches_theory(code):
    game = get_game(code)
    base = baseline(game, 200, sims=SIMS, seed=5)
    assert base.mean == pytest.approx(theoretical_mean(game), abs=0.01)
    assert base.p5 < base.mean < base.p95


def test_theoretical_means():
    assert theoretical_mean(BALOTO) == pytest.approx(25 / 43)
    assert theoretical_mean(get_game("colorloto")) == pytest.approx(36 / 42)


def test_random_strategy_falls_in_random_band():
    """En 40 historiales aleatorios, ``random`` queda dentro de p5–p95 ~90% de las veces y su
    media general se acerca a K²/N."""
    inside, avgs = 0, []
    for seed in range(40):
        recs = simulate_draws("baloto", 150, seed=100 + seed)
        out = run_backtest(recs, BALOTO, get_strategy("random"), "random", window=50, seed=seed, sims=SIMS)
        inside += out.baseline.p5 <= out.avg_hits <= out.baseline.p95
        avgs.append(out.avg_hits)
    assert inside >= 32  # esperado 36; margen para la variación
    assert sum(avgs) / len(avgs) == pytest.approx(25 / 43, abs=0.03)


def test_p_value_direction():
    base = baseline(BALOTO, 100, sims=SIMS, seed=6)
    assert base.p_value(5.0) == pytest.approx(1 / (SIMS + 1))
    assert base.p_value(0.0) == pytest.approx(1.0)
    # Los promedios son discretos (pasos de 1/100): P(>= p95) incluye los empates en p95,
    # así que el primer valor por encima de p95 es el que queda por debajo de 0,05.
    assert base.p_value(base.p95 + 0.01) <= 0.05
    assert base.p_value(base.p95) > 0.05


# --- estrategias -------------------------------------------------------------------
@pytest.mark.parametrize("code", ["baloto", "miloto", "colorloto"])
@pytest.mark.parametrize("name", list(STRATEGIES))
def test_every_strategy_returns_valid_deterministic_tickets(code, name):
    game = get_game(code)
    history = tuple(simulate_draws(code, 60, seed=7))
    strat = get_strategy(name)
    a = strat(history, game, random.Random(1))
    b = strat(history, game, random.Random(1))
    assert game.validate(a) == [], (name, a)
    assert a == b


def test_hot_and_cold_pick_extremes():
    from app.ingest.records import DrawRecord
    from datetime import date

    hist = tuple(
        # El último (i=10) es (1,2,3,4,5): desempata 5 sobre 6 por recencia.
        DrawRecord("miloto", i, date(2026, 1, 1), (1, 2, 3, 4, 5) if i % 2 == 0 else (1, 2, 3, 4, 6))
        for i in range(1, 11)
    )
    game = get_game("miloto")
    assert get_strategy("hot")(hist, game, random.Random(0)).numbers == (1, 2, 3, 4, 5)
    cold = get_strategy("cold")(hist, game, random.Random(0)).numbers
    assert set(cold).isdisjoint({1, 2, 3, 4, 5, 6})


def test_anti_popular_has_low_score():
    from app.analysis.popularity import popularity

    game = get_game("baloto")
    hist = tuple(simulate_draws("baloto", 30, seed=8))
    for s in range(20):
        t = get_strategy("anti_popular")(hist, game, random.Random(s))
        assert popularity(t, game).score <= 10


def test_errors():
    recs = simulate_draws("baloto", 30)
    with pytest.raises(ValueError, match="no hay sorteos"):
        run_backtest(recs, BALOTO, get_strategy("random"), "random", window=50, sims=SIMS)
    with pytest.raises(ValueError, match="estrategia desconocida"):
        get_strategy("martingala")
