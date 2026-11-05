"""Modelo de ML: no mira al futuro, sí aprende cuando hay patrón y no inventa cuando no lo hay."""

import random
from datetime import date, timedelta

import numpy as np
import pytest

from app.games import get_game
from app.ingest.records import DrawRecord
from app.ml.features import FEATURE_NAMES, feature_tensor, presence
from app.ml.model import predict_next, walk_forward

from tests.conftest import simulate_draws


def test_features_never_use_the_predicted_draw_or_later():
    recs = simulate_draws("miloto", 120, seed=1)
    p = presence(recs, get_game("miloto"))
    f = feature_tensor(p)
    assert f.shape == (121, 39, len(FEATURE_NAMES))
    altered = p.copy()
    altered[60:] = ~altered[60:]  # cambia todo desde el sorteo 60
    f2 = feature_tensor(altered)
    assert np.array_equal(f[:61], f2[:61])  # las variables para predecir t ≤ 60 no cambian
    assert not np.array_equal(f[61:], f2[61:])


def test_feature_values_by_hand():
    recs = [DrawRecord("miloto", i, date(2026, 1, i), (1, 2, 3, 4, 5) if i % 2 else (6, 7, 8, 9, 10))
            for i in range(1, 21)]
    p = presence(recs, get_game("miloto"))
    f = feature_tensor(p)
    t = 20  # predecir el sorteo 21 con los 20 anteriores
    col = {n: i for i, n in enumerate(FEATURE_NAMES)}
    assert f[t, 0, col["frec_10"]] == pytest.approx(0.5)  # el 1 salió en 5 de los últimos 10
    assert f[t, 0, col["salio_antes"]] == 0  # el sorteo 20 fue (6..10)
    assert f[t, 5, col["salio_antes"]] == 1
    assert f[t, 0, col["hueco"]] == pytest.approx(np.log1p(1))  # salió hace 1 sorteo (el 19)
    assert f[t, 20, col["hueco"]] == pytest.approx(np.log1p(20))  # el 21 nunca salió


@pytest.mark.parametrize("kind", ["gb", "logit"])
def test_no_signal_means_no_skill(kind):
    """Sorteos realmente aleatorios: el modelo no debe 'descubrir' nada."""
    recs = simulate_draws("miloto", 300, seed=3)
    ev = walk_forward(recs, get_game("miloto"), kind=kind, start=150)
    assert ev.delta_ci[0] < 0.002  # el IC no está claramente por encima de 0
    assert ev.skill < 0.01
    assert ev.base_p5 <= ev.avg_hits <= ev.base_p95 or ev.p_value > 0.01


def planted_draws(n: int, seed: int) -> list[DrawRecord]:
    """MiLoto con patrón plantado: una balota que salió en el sorteo anterior repite con
    probabilidad alta (el modelo debería aprenderlo con 'salio_antes')."""
    rng = random.Random(seed)
    out, prev = [], set(rng.sample(range(1, 40), 5))
    for i in range(n):
        keep = [x for x in prev if rng.random() < 0.5]
        rest = rng.sample([x for x in range(1, 40) if x not in keep], 5 - len(keep))
        cur = set(keep + rest)
        out.append(DrawRecord("miloto", i + 1, date(2020, 1, 1) + timedelta(days=i), tuple(sorted(cur))))
        prev = cur
    return out


@pytest.mark.parametrize("kind", ["gb", "logit"])
def test_learns_a_planted_pattern(kind):
    ev = walk_forward(planted_draws(300, seed=4), get_game("miloto"), kind=kind, start=150)
    assert ev.skill > 0.05 and ev.delta_ci[0] > 0
    assert ev.avg_hits > ev.base_p95 and ev.p_value < 0.01


def test_extra_ball_and_next_draw():
    recs = simulate_draws("baloto", 200, seed=6)
    game = get_game("baloto")
    ev = walk_forward(recs, game, kind="logit", unit="extra", start=120)
    assert ev.k == 1 and ev.b == 16 and ev.n_test == 80
    nxt = predict_next(recs, game, kind="gb")
    assert len(nxt.probabilities) == 43 and nxt.base == pytest.approx(5 / 43)
    assert all(0 < x < 1 for x in nxt.probabilities)
    nxt_x = predict_next(recs, game, kind="logit", unit="extra")
    assert len(nxt_x.probabilities) == 16 and set(nxt_x.importances) == set(FEATURE_NAMES)


def test_ml_endpoint_and_generator_mode():
    from app.games import Ticket
    from app.main import app
    from tests.test_api import make_client

    client = make_client(simulate_draws("baloto", 200, seed=10))
    try:
        body = client.get("/games/baloto/ml").json()
        main = body["units"]["main"]
        assert len(main["probabilities"]) == 43 and len(main["top"]) == 5
        assert main["base"] == pytest.approx(5 / 43)
        assert len(body["units"]["extra"]["probabilities"]) == 16
        assert "no predice mejor" in body["notice"]
        gen = client.post("/generate", json={"game": "baloto", "n": 4, "mode": "ml", "seed": 2}).json()
        assert gen["mode"] == "ml" and len(gen["plays"]) == 4
        top5 = sorted(int(x["label"]) for x in main["top"])
        first = gen["plays"][0]
        assert sorted(b["number"] for b in first["balls"]) == top5  # jugada 1 = las 5 más probables
        for p in gen["plays"]:
            assert get_game("baloto").validate(Ticket(tuple(b["number"] for b in p["balls"]), None, p["extra"])) == []
            assert len(p["ml_probabilities"]) == 5 and p["ml_extra_probability"] is not None
        assert client.get("/games/baloto/ml", params={"model": "x"}).status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_colorloto_units():
    recs = simulate_draws("colorloto", 150, seed=7)
    p = presence(recs, get_game("colorloto"))
    assert p.shape == (150, 42) and (p.sum(axis=1) == 6).all()
