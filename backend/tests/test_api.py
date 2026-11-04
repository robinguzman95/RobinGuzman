from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session

from app.db import get_session
from app.games import sync_games
from app.ingest.importer_csv import load_records
from app.ingest.records import DrawRecord
from app.main import app
from app.models import Base
from sqlalchemy import create_engine


@pytest.fixture
def client():
    yield make_client()
    app.dependency_overrides.clear()


def make_client() -> TestClient:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        sync_games(s)
        load_records(s, [DrawRecord("miloto", 635, date(2026, 11, 3), (8, 13, 20, 24, 25))])

    def override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override
    return TestClient(app)


def test_games_show_real_odds(client):
    body = client.get("/games").json()
    by_code = {g["code"]: g for g in body}
    assert by_code["baloto"]["jackpot_odds"] == "1 en 15.401.568"
    assert by_code["colorloto"]["combinations"] == 5_245_786


def test_health_reports_last_draw(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["games"]["miloto"] == {"last_draw_date": "2026-11-03", "draws": 1}
    assert body["games"]["baloto"]["draws"] == 0
