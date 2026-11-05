from datetime import date

import httpx
import pytest

from app.api.ingest import get_scraper
from app.config import Settings, get_settings
from app.ingest.scraper import Scraper, parse_baloto_page, parse_colorloto_page, parse_miloto_page
from app.main import app

from tests.conftest import FIXTURES, simulate_draws
from tests.test_api import make_client


def fixture_html(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


PAGES = {"/resultados": "baloto_page1.html", "/miloto/resultados": "miloto_page1.html",
         "/colorloto/resultados": "colorloto_page1.html"}


def mock_scraper(tmp_path, calls: list) -> Scraper:
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.url.path, request.url.params.get("page")))
        if request.url.params.get("page") == "1":
            return httpx.Response(200, text=fixture_html(PAGES[request.url.path]))
        return httpx.Response(200, text="<html><body>sin filas</body></html>")

    return Scraper(tmp_path, delay_seconds=0, client=httpx.Client(transport=httpx.MockTransport(handler)),
                   use_cache=False)


@pytest.fixture
def token(monkeypatch):
    monkeypatch.setenv("LOTOLAB_INGEST_TOKEN", "secreto-de-prueba")
    get_settings.cache_clear()
    yield "secreto-de-prueba"
    get_settings.cache_clear()


def known_old_draws():
    """Lo que 'ya estaba' en la BD: los sorteos de las fixtures menos los 2 más recientes de cada juego."""
    recs = []
    for parser, name in [(parse_baloto_page, "baloto_page1.html"), (parse_miloto_page, "miloto_page1.html"),
                         (parse_colorloto_page, "colorloto_page1.html")]:
        page = parser(fixture_html(name)).records
        for game in {r.game for r in page}:
            recs += sorted((r for r in page if r.game == game), key=lambda r: r.draw_number)[:-2]
    return recs


# --- /ingest/run ---------------------------------------------------------------------
def test_ingest_requires_configured_token(monkeypatch):
    monkeypatch.delenv("LOTOLAB_INGEST_TOKEN", raising=False)
    get_settings.cache_clear()
    client = make_client([])
    try:
        assert client.post("/ingest/run").status_code == 503
    finally:
        app.dependency_overrides.clear()


def test_ingest_rejects_wrong_token(token):
    client = make_client([])
    try:
        assert client.post("/ingest/run").status_code == 401
        assert client.post("/ingest/run", headers={"X-Ingest-Token": "otro"}).status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_ingest_adds_only_new_draws_and_is_idempotent(token, tmp_path):
    calls: list = []
    client = make_client(known_old_draws())
    app.dependency_overrides[get_scraper] = lambda: mock_scraper(tmp_path, calls)
    try:
        body = client.post("/ingest/run", headers={"X-Ingest-Token": token}).json()
        assert body["inserted"] == {"baloto": 2, "revancha": 2, "miloto": 2, "colorloto": 2}
        assert body["conflicts"] == [] and body["rejected"] == []
        assert body["last_draw"]["baloto"] == "2026-11-02"
        assert body["last_draw"]["miloto"] == "2026-11-03"
        # Segunda corrida: nada nuevo.
        again = client.post("/ingest/run", headers={"X-Ingest-Token": token}).json()
        assert set(again["inserted"].values()) == {0}
        # Una sola página por familia y por corrida (la página 2 vacía corta el recorrido).
        assert all(page in ("1", "2") for _, page in calls)
    finally:
        app.dependency_overrides.clear()


# --- /generate -----------------------------------------------------------------------
@pytest.mark.parametrize("code", ["baloto", "miloto", "colorloto"])
def test_generate(code):
    from app.games import Ticket, get_game

    client = make_client(simulate_draws(code, 40, seed=5))
    try:
        req = {"game": code, "n": 5, "seed": 123, "mode": "anti_popular"}
        body = client.post("/generate", json=req).json()
        game = get_game(code)
        assert len(body["plays"]) == 5
        assert body["odds"]["jackpot_odds"] == game.odds_text()
        assert "Ninguna jugada tiene más probabilidad" in body["notice"]
        keys = set()
        for p in body["plays"]:
            nums = tuple(b["number"] for b in p["balls"])
            cols = tuple(b["color"] for b in p["balls"]) if game.colors else None
            assert game.validate(Ticket(nums, cols, p["extra"])) == []
            assert p["popularity_score"] <= 10 and p["text"]
            keys.add((nums, cols))
        assert len(keys) == 5  # sin jugadas repetidas
        # Misma semilla, mismas jugadas.
        assert client.post("/generate", json=req).json() == body
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("code", ["baloto", "miloto", "colorloto"])
def test_generate_historical(code):
    """Modo por defecto: jugadas con las balotas más frecuentes y sus estadísticas."""
    from app.analysis import frequency as fq
    from app.games import Ticket, get_game

    draws = simulate_draws(code, 200, seed=9)
    client = make_client(draws)
    try:
        body = client.post("/generate", json={"game": code, "n": 5, "seed": 1}).json()
        game = get_game(code)
        assert body["mode"] == "historico" and len(body["plays"]) == 5
        win = fq.apply_window(draws, "12m")
        freq = fq.ball_frequency(win, game)
        top15 = {fq.ball_label(b) for b in sorted(freq, key=lambda b: (-freq[b], b[0], str(b[1])))[:15]}
        keys = set()
        for p in body["plays"]:
            nums = tuple(b["number"] for b in p["balls"])
            cols = tuple(b["color"] for b in p["balls"]) if game.colors else None
            assert game.validate(Ticket(nums, cols, p["extra"])) == []
            s = p["stats"]
            assert {c["label"] for c in s["counts"]} <= top15  # solo balotas calientes
            assert s["total_count"] == sum(c["count"] for c in s["counts"])
            assert s["window_draws"] == len(win)
            keys.add(nums + (cols or ()))
        assert len(keys) == 5
        # Jugadas variadas: dos jugadas comparten como mucho K-2 balotas.
        sets = [set(zip(*(lambda p: ([b["number"] for b in p["balls"]], [b["color"] for b in p["balls"]]))(p)))
                for p in body["plays"]]
        assert all(len(a & b) <= game.main_count - 2 for i, a in enumerate(sets) for b in sets[i + 1:])
        assert client.post("/generate", json={"game": code, "n": 5, "seed": 1}).json() == body
    finally:
        app.dependency_overrides.clear()


def test_generate_validation():
    client = make_client([])
    try:
        assert client.post("/generate", json={"game": "chance"}).status_code == 404
        assert client.post("/generate", json={"game": "baloto", "n": 11}).status_code == 422
    finally:
        app.dependency_overrides.clear()


# --- backtest con serie y resumen ----------------------------------------------------
def test_backtest_series_and_cache():
    client = make_client(simulate_draws("baloto", 260, seed=9))
    try:
        body = client.post("/backtest", json={"game": "baloto", "strategy": "random", "window": 100}).json()
        series = body["series"]
        assert 10 <= len(series) <= 60
        assert series[-1]["strategy"] == pytest.approx(body["avg_hits"])
        assert all(p["p5"] <= p["p95"] for p in series)
        # La banda se estrecha al acumular sorteos.
        assert series[-1]["p95"] - series[-1]["p5"] < series[1]["p95"] - series[1]["p5"]
        # Corrida idéntica -> misma fila, no una nueva.
        again = client.post("/backtest", json={"game": "baloto", "strategy": "random", "window": 100}).json()
        assert again["id"] == body["id"]
    finally:
        app.dependency_overrides.clear()


def test_backtest_summary_served_from_file(tmp_path, monkeypatch):
    from app.backtest.report import run_all, to_summary
    import json

    rows, alpha_b, notes = run_all({"miloto": simulate_draws("miloto", 160, seed=3)}, ["random"], windows=(100,),
                                   sims=500)
    path = tmp_path / "summary.json"
    path.write_text(json.dumps(to_summary(rows, alpha_b, notes, generated=date(2026, 11, 4))), encoding="utf-8")
    monkeypatch.setenv("LOTOLAB_BACKTEST_SUMMARY_PATH", str(path))
    get_settings.cache_clear()
    client = make_client([])
    try:
        body = client.get("/backtest/summary").json()
        assert body["combinations"] == 1 and body["rows"][0]["primary"]
        monkeypatch.setenv("LOTOLAB_BACKTEST_SUMMARY_PATH", str(tmp_path / "no.json"))
        get_settings.cache_clear()
        assert client.get("/backtest/summary").status_code == 404
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


# --- pair_counts y configuración -----------------------------------------------------
def test_pair_counts_match_manual_count():
    from app.config import REPO_ROOT
    from app.ingest.importer_csv import read_csv
    from tests.test_frequency import BALOTO_PAIRS_TWICE

    client = make_client(read_csv(REPO_ROOT / "data" / "raw" / "baloto.csv", "baloto").records)
    try:
        body = client.get("/games/baloto/stats", params={"window": "10"}).json()
        twice = {(int(a), int(b)) for a, b, n in body["pair_counts"] if n == 2}
        assert twice == BALOTO_PAIRS_TWICE
        assert sum(n for _, _, n in body["pair_counts"]) == 10 * 10  # C(5,2) = 10 pares por sorteo
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("raw", ["postgres://u:p@h:5432/db", "postgresql://u:p@h:5432/db"])
def test_database_url_normalized(raw):
    assert Settings(database_url=raw).database_url == "postgresql+psycopg://u:p@h:5432/db"


def test_sqlite_url_untouched_and_cors_list():
    s = Settings(database_url="sqlite:///x.db", cors_origins="https://a.app, http://localhost:3000")
    assert s.database_url == "sqlite:///x.db"
    assert s.cors_origin_list == ["https://a.app", "http://localhost:3000"]
