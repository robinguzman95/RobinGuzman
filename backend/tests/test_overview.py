from app.main import app

from tests.conftest import simulate_draws
from tests.test_api import make_client


def test_overview_with_real_summaries():
    """Usa los resúmenes reales de data/ (backtest, valor esperado, ML) y una BD simulada."""
    client = make_client(simulate_draws("baloto", 50, seed=1) + simulate_draws("miloto", 30, seed=2))
    try:
        body = client.get("/overview").json()
        assert body["total_draws"] == 80
        assert body["games"]["baloto"]["draws"] == 50 and body["games"]["colorloto"]["draws"] == 0
        assert body["games"]["baloto"]["odds"] == "1 en 15.401.568"
        bt = body["backtest"]
        assert bt["combinations"] == 60 and bt["significant"] == 0
        assert 0 < body["expected_value"]["baloto"]["return_current"] < 1
        assert set(body["ml"]["baloto"]) == {"gb", "logit"}
        assert body["ml"]["baloto"]["gb"]["beats_random"] is False
    finally:
        app.dependency_overrides.clear()
