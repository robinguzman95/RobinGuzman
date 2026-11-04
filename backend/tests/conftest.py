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


def simulate_draws(code: str, n: int, seed: int = 0) -> list[DrawRecord]:
    """n sorteos aleatorios válidos de cualquier juego (incluye colores y superbalota)."""
    from app.analysis.frequency import all_balls
    from app.games import get_game

    game = get_game(code)
    rng = random.Random(seed)
    out = []
    for i in range(n):
        balls = sorted(rng.sample(all_balls(game), game.main_count), key=lambda b: (b[0], str(b[1])))
        out.append(DrawRecord(
            code, i + 1, date(2020, 1, 1) + timedelta(days=i),
            tuple(b[0] for b in balls),
            tuple(b[1] for b in balls) if game.colors else None,
            rng.randint(1, game.extra_max) if game.extra_max else None,
        ))
    return out


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
