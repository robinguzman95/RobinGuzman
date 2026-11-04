import random
from datetime import date, timedelta
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.db import make_engine
from app.games import sync_games
from app.ingest.records import DrawRecord
from app.models import Base

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def session() -> Session:
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        sync_games(s)
        yield s


def miloto_series(n: int, start_number: int = 100, start: date = date(2025, 1, 6)) -> list[DrawRecord]:
    """n sorteos válidos de MiLoto en días de sorteo (lun, mar, jue, vie)."""
    out, d, num = [], start, start_number
    while len(out) < n:
        if d.weekday() in (0, 1, 3, 4):
            numbers = tuple(sorted(random.Random(num).sample(range(1, 40), 5)))
            out.append(DrawRecord("miloto", num, d, numbers))
            num += 1
        d += timedelta(days=1)
    return out
