import random
from datetime import date, timedelta

import pytest

from app.analysis.stat_tests import (
    chi_square_equal_groups,
    runs_by_ball,
    runs_test,
    uniformity_tests,
    verdict,
)
from app.games import get_game
from app.ingest.records import DrawRecord


def simulate(code: str, n: int, rng: random.Random, weights: dict[int, float] | None = None) -> list[DrawRecord]:
    """Sorteos simulados sin reposición; ``weights`` planta un sesgo en algunos números."""
    game = get_game(code)
    out = []
    for i in range(n):
        pool = list(range(1, game.main_max + 1))
        if weights:
            picks: list[int] = []
            while len(picks) < game.main_count:
                w = [weights.get(x, 1.0) for x in pool]
                x = rng.choices(pool, w)[0]
                picks.append(x)
                pool.remove(x)
        else:
            picks = rng.sample(pool, game.main_count)
        extra = rng.randint(1, game.extra_max) if game.extra_max else None
        out.append(DrawRecord(code, i + 1, date(2020, 1, 1) + timedelta(days=i), tuple(picks), None, extra))
    return out


def test_verdict_text():
    assert verdict(0.5) == "compatible con el azar"
    assert verdict(0.01).startswith("desviación significativa")
    assert verdict(None) == "sin datos suficientes"


def test_correction_factor():
    # Baloto: N=43, K=5 -> c = 38/42. Superbalota (K=1) -> sin corrección.
    res = chi_square_equal_groups([5] * 43, 43, 43, 5, "x")
    assert res.correction == pytest.approx(38 / 42)
    assert res.statistic == 0 and res.p_value == pytest.approx(1.0)
    assert chi_square_equal_groups([10] * 16, 160, 16, 1, "sb").correction == 1.0


@pytest.mark.parametrize("code", ["baloto", "miloto"])
def test_false_positive_rate_is_about_5_percent(code):
    """Con sorteos realmente aleatorios la prueba corregida rechaza ~5% de las veces.
    (Sin la corrección rechazaría bastante menos: sería conservadora.)"""
    rng = random.Random(2026)
    game = get_game(code)
    reps = 400
    rejections = sum(
        uniformity_tests(simulate(code, 200, rng), game)[0].p_value < 0.05 for _ in range(reps)
    )
    assert 0.025 <= rejections / reps <= 0.085


def test_detects_planted_bias():
    rng = random.Random(7)
    recs = simulate("miloto", 600, rng, weights={7: 2.0, 13: 2.0})
    main = uniformity_tests(recs, get_game("miloto"))[0]
    assert main.p_value < 0.001
    assert main.verdict.startswith("desviación significativa")


def test_small_sample_is_flagged_not_concluded():
    recs = simulate("baloto", 10, random.Random(1))
    main = uniformity_tests(recs, get_game("baloto"))[0]
    assert not main.reliable and "no concluyente" in main.verdict


def test_tests_per_game():
    rng = random.Random(3)
    assert [t.label for t in uniformity_tests(simulate("baloto", 50, rng), get_game("baloto"))] == ["números", "superbalota"]
    assert [t.label for t in uniformity_tests(simulate("miloto", 50, rng), get_game("miloto"))] == ["números"]


def test_runs_test_known_values():
    alternating = [True, False] * 20
    res = runs_test(alternating)
    assert res.runs == 40 and res.z > 0 and res.p_value < 0.001
    clumped = [True] * 20 + [False] * 20
    assert runs_test(clumped).runs == 2 and runs_test(clumped).z < 0
    assert runs_test([True] * 10) is None


def test_runs_pmf_is_a_distribution():
    from app.analysis.stat_tests import runs_pmf

    pmf = runs_pmf(17, 96)
    assert sum(pmf.values()) == pytest.approx(1.0)
    assert min(pmf) == 2 and max(pmf) == 2 * 17 + 1
    # Caso pequeño a mano: 2 éxitos y 2 fracasos -> 6 permutaciones; rachas 2:2, 3:2, 4:2.
    assert runs_pmf(2, 2) == pytest.approx({2: 1 / 3, 3: 1 / 3, 4: 1 / 3})


def test_runs_exact_on_real_colorloto_7_blanco():
    """Caso real que motivó el p-valor exacto: 17 apariciones en 113 sorteos y 21 rachas.
    La normal daba 0,0009 (falso positivo tras Bonferroni 0,05/42); el exacto da ~0,0055."""
    positions = {7, 10, 11, 12, 31, 35, 36, 43, 45, 73, 74, 75, 76, 77, 90, 97, 106}
    seq = [i in positions for i in range(113)]
    res = runs_test(seq)
    assert res.runs == 21
    assert res.p_value == pytest.approx(0.0055, abs=0.0005)
    assert res.p_value > 0.05 / 42


def test_runs_by_ball_random_data_is_compatible():
    recs = simulate("miloto", 300, random.Random(11))
    summary = runs_by_ball(recs, get_game("miloto"))
    assert summary.tested == 39
    assert summary.alpha_bonferroni == pytest.approx(0.05 / 39)
    assert summary.significant_bonferroni == []
    assert summary.verdict == "compatible con el azar"
