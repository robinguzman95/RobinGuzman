from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import func, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import pytest

from app.db import make_engine
from app.games import GAMES, sync_games
from app.models import Base, Draw, DrawBall, GameRow

BACKEND = Path(__file__).resolve().parents[1]


def test_migration_matches_models(tmp_path):
    url = f"sqlite:///{(tmp_path / 'm.db').as_posix()}"
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url)
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "head")

    engine = make_engine(url)
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
        assert diff == [], f"la migración no coincide con models.py: {diff}"
        tables = set(inspect(conn).get_table_names())
    assert {"games", "draws", "draw_balls", "backtest_runs", "backtest_results"} <= tables
    command.downgrade(cfg, "base")


def test_sync_games_is_idempotent(session: Session):
    sync_games(session)
    rows = session.scalars(select(GameRow)).all()
    assert len(rows) == len(GAMES)
    color = next(r for r in rows if r.code == "colorloto")
    assert color.color_set == "amarillo,azul,rojo,verde,blanco,negro"
    assert next(r for r in rows if r.code == "baloto").extra_max == 16


def test_unique_game_draw_number(session: Session):
    game = session.scalar(select(GameRow).where(GameRow.code == "miloto"))
    from datetime import date

    session.add(Draw(game_id=game.id, draw_number=1, draw_date=date(2026, 1, 1)))
    session.commit()
    session.add(Draw(game_id=game.id, draw_number=1, draw_date=date(2026, 1, 2)))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_deleting_draw_cascades_to_balls(session: Session):
    from datetime import date

    game = session.scalar(select(GameRow).where(GameRow.code == "miloto"))
    d = Draw(game_id=game.id, draw_number=7, draw_date=date(2026, 1, 1))
    d.balls = [DrawBall(position=i, number=i, is_extra=False) for i in range(1, 6)]
    session.add(d)
    session.commit()
    session.delete(d)
    session.commit()
    assert session.scalar(select(func.count(DrawBall.id))) == 0
