from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import REPO_ROOT
from app.db import get_session
from app.games import sync_games
from app.ingest.importer_csv import load_records, read_csv
from app.ingest.records import DrawRecord
from app.main import app
from app.models import Base


def make_client(records: list[DrawRecord]) -> TestClient:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        sync_games(s)
        load_records(s, records)

    def override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override
    return TestClient(app)


@pytest.fixture
def client():
    yield make_client([DrawRecord("miloto", 635, date(2026, 11, 3), (8, 13, 20, 24, 25))])
    app.dependency_overrides.clear()


@pytest.fixture
def real_client():
    """BD con el histórico real de data/raw (Baloto y ColorLoto)."""
    recs = []
    for code in ("baloto", "colorloto"):
        read = read_csv(REPO_ROOT / "data" / "raw" / f"{code}.csv", code)
        recs += read.records
    yield make_client(recs)
    app.dependency_overrides.clear()


def test_games_show_real_odds(client):
    by_code = {g["code"]: g for g in client.get("/games").json()}
    assert by_code["baloto"]["odds"]["jackpot_odds"] == "1 en 15.401.568"
    assert by_code["colorloto"]["odds"]["combinations"] == 5_245_786


def test_health_reports_last_draw(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["games"]["miloto"] == {"last_draw_date": "2026-11-03", "draws": 1}
    assert body["games"]["baloto"]["draws"] == 0


def test_draws_paginated_and_filtered(real_client):
    body = real_client.get("/games/baloto/draws", params={"page_size": 3}).json()
    assert body["total"] == 171 and len(body["items"]) == 3
    assert body["items"][0]["draw_number"] == 2730
    assert [b["number"] for b in body["items"][0]["balls"]] == [18, 19, 20, 31, 43]
    assert body["items"][0]["extra"] == 14
    ranged = real_client.get("/games/baloto/draws", params={"from": "2026-10-12", "to": "2026-11-02"}).json()
    assert ranged["total"] == 10


def test_stats_last_10_matches_manual_count(real_client):
    body = real_client.get("/games/baloto/stats", params={"window": "10"}).json()
    assert body["n_draws"] == 10
    assert body["odds"]["jackpot_odds"] == "1 en 15.401.568"
    assert "no predice" in body["disclaimer"]
    assert body["frequency"]["6"] == 4 and body["frequency"]["1"] == 0
    assert [h["number"] for h in body["hot"][:3]] == [19, 29, 6]
    assert [t["label"] for t in body["uniformity"]] == ["números", "superbalota"]


def test_stats_colorloto_has_marginals(real_client):
    body = real_client.get("/games/colorloto/stats", params={"window": "all"}).json()
    assert len(body["frequency"]) == 42
    assert set(body["color_frequency"]) == {"amarillo", "azul", "rojo", "verde", "blanco", "negro"}
    assert sum(body["color_frequency"].values()) == 6 * body["n_draws"]
    assert [t["label"] for t in body["uniformity"]] == ["balotas", "números", "colores"]


def test_stats_errors(client):
    assert client.get("/games/chance/stats").status_code == 404
    assert client.get("/games/baloto/stats", params={"window": "abc"}).status_code == 422
