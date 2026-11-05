from datetime import timedelta

import pytest

from app.ingest.records import DrawRecord
from app.main import app

from tests.conftest import simulate_draws
from tests.test_api import make_client


@pytest.fixture
def client():
    draws = simulate_draws("baloto", 160, seed=12)
    # Un sorteo conocido para comprobar "ya salió" y "mejor resultado".
    draws.append(DrawRecord("baloto", 161, draws[-1].draw_date + timedelta(days=1), (3, 11, 15, 28, 40), None, 7))
    yield make_client(draws)
    app.dependency_overrides.clear()


def balls(*nums):
    return [{"number": n} for n in nums]


def test_analyze_my_play(client):
    body = client.post("/analyze", json={"game": "baloto", "balls": balls(3, 11, 15, 28, 40), "extra": 7}).json()
    play = body["play"]
    assert play["text"] == "03 - 11 - 15 - 28 - 40 | superbalota 07"
    assert len(play["stats"]["counts"]) == 5 and play["stats"]["window_draws"] > 0
    assert len(play["ml_probabilities"]) == 5 and play["ml_extra_probability"] is not None
    assert 0 <= play["popularity_score"] <= 100
    h = body["all_history"]
    assert h["draws"] == 161 and sum(h["hits"].values()) == 161
    assert [m["draw_number"] for m in h["exact_matches"]] == [161]
    assert h["best"][0]["hits"] == 5 and h["best"][0]["extra_hit"] is True
    assert body["odds"]["jackpot_odds"] == "1 en 15.401.568"


def test_order_does_not_matter(client):
    a = client.post("/analyze", json={"game": "baloto", "balls": balls(40, 3, 28, 11, 15), "extra": 7}).json()
    assert a["play"]["text"] == "03 - 11 - 15 - 28 - 40 | superbalota 07"


@pytest.mark.parametrize(
    "payload, fragment",
    [
        ({"game": "baloto", "balls": balls(1, 2, 3, 4), "extra": 1}, "se esperaban 5"),
        ({"game": "baloto", "balls": balls(1, 2, 3, 4, 44), "extra": 1}, "fuera de rango"),
        ({"game": "baloto", "balls": balls(1, 1, 3, 4, 5), "extra": 1}, "repetidos"),
        ({"game": "baloto", "balls": balls(1, 2, 3, 4, 5)}, "falta la balota extra"),
    ],
)
def test_invalid_plays_explain_why(client, payload, fragment):
    r = client.post("/analyze", json=payload)
    assert r.status_code == 422 and fragment in r.json()["detail"]


def test_colorloto_needs_colors():
    c = make_client(simulate_draws("colorloto", 60, seed=3))
    try:
        r = c.post("/analyze", json={"game": "colorloto", "balls": balls(1, 2, 3, 4, 5, 6)})
        assert r.status_code == 422 and "color" in r.json()["detail"]
        ok = c.post("/analyze", json={"game": "colorloto", "balls": [
            {"number": n, "color": col} for n, col in [(1, "rojo"), (2, "rojo"), (3, "azul"), (4, "verde"),
                                                       (5, "blanco"), (6, "negro")]]})
        assert ok.status_code == 200 and ok.json()["play"]["ml_probabilities"] is None  # < 150 sorteos
    finally:
        app.dependency_overrides.clear()
