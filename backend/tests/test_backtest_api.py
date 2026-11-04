from datetime import date

import pytest

from app.backtest.report import render_markdown, run_all
from app.main import app

from tests.conftest import simulate_draws
from tests.test_api import make_client


@pytest.fixture
def client():
    yield make_client(simulate_draws("miloto", 160, seed=21))
    app.dependency_overrides.clear()


def test_create_and_fetch_backtest(client):
    resp = client.post("/backtest", json={"game": "miloto", "strategy": "hot", "window": 100})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["n_draws"] == 60 and body["is_primary_window"]
    assert sum(body["hit_distribution"].values()) == 60
    assert body["baseline_p5"] < body["baseline_mean"] < body["baseline_p95"]
    assert body["odds"]["jackpot_odds"] == "1 en 575.757"
    again = client.get(f"/backtest/{body['id']}").json()
    assert again == body


def test_backtest_errors(client):
    assert client.post("/backtest", json={"game": "miloto", "strategy": "martingala"}).status_code == 404
    assert client.post("/backtest", json={"game": "chance", "strategy": "hot"}).status_code == 404
    too_big = client.post("/backtest", json={"game": "miloto", "strategy": "hot", "window": 500})
    assert too_big.status_code == 422 and "no hay sorteos" in too_big.json()["detail"]
    assert client.get("/backtest/999").status_code == 404


def test_run_all_applies_bonferroni_and_skips_windows():
    recs = {"miloto": simulate_draws("miloto", 180, seed=22)}
    rows, alpha_b, notes = run_all(recs, ["random", "hot"], windows=(100, 50, 200), sims=1000)
    assert len(rows) == 4  # ventana 200 no cabe en 180 sorteos
    assert alpha_b == pytest.approx(0.05 / 4)
    assert any("ventana 200 omitida" in n for n in notes)
    md = render_markdown(rows, alpha_b, notes, generated=date(2026, 11, 4))
    assert "Ninguna estrategia le gana al azar" in md or "superan al azar" in md
    assert "1 en 575.757" in md
    assert md.count("| MiLoto |") == 4
