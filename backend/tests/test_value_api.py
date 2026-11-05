import json

import pytest

from app.analysis.ev_report import build_summary, game_summary
from app.config import get_settings
from app.main import app

from tests.conftest import simulate_draws
from tests.test_api import make_client
from tests.test_expected import synthetic_rows

PRIZES = {"0+SB": 6000, "2+SB": 10_000, "3": 9_000, "3+SB": 40_000, "4": 100_000, "4+SB": 1_400_000,
          "5": 100_000_000}


@pytest.fixture
def summary_file(tmp_path, monkeypatch):
    draws = simulate_draws("baloto", 40, seed=3)
    rows = synthetic_rows("baloto", [120_000 + 5_000 * i for i in range(40)],
                          [int(4e9 + 5e8 * i) for i in range(40)], PRIZES)
    s = build_summary({"baloto": game_summary("baloto", rows, draws, backtest_draws=550)})
    path = tmp_path / "ev.json"
    path.write_text(json.dumps(s), encoding="utf-8")
    monkeypatch.setenv("LOTOLAB_EXPECTED_VALUE_PATH", str(path))
    get_settings.cache_clear()
    yield s
    get_settings.cache_clear()


def test_summary_shape(summary_file):
    g = summary_file["games"]["baloto"]
    assert g["price"] == 6000 and g["n_draws"] == 40
    assert 0 < g["non_jackpot_return"] < 1
    assert g["return_current"] < 1  # un tiquete pierde dinero en promedio
    assert g["ev_current_unpopular"] > g["ev_current"]
    assert g["power"]["backtest"]["n_draws"] == 550
    assert 0 < g["power"]["ball_bias"]["min_relative_bias"] < 5
    assert summary_file["tax"]["rate"] == 0.2


def test_value_endpoints(summary_file):
    client = make_client([])
    try:
        light = client.get("/expected-value").json()
        assert "curve" not in light["games"]["baloto"]
        full = client.get("/games/baloto/expected-value").json()
        assert len(full["curve"]) == 60
        q = client.get("/games/baloto/expected-value", params={"jackpot": 20e9}).json()["query"]
        q_unpop = client.get("/games/baloto/expected-value", params={"jackpot": 20e9, "popularity": 0.5}).json()["query"]
        assert q_unpop["ev"] > q["ev"] and q["return"] == pytest.approx(q["ev"] / 6000)
        assert client.get("/games/miloto/expected-value").status_code == 404
    finally:
        app.dependency_overrides.clear()
