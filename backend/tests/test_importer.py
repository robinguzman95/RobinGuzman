from datetime import date

import pytest
from sqlalchemy import func, select

from app.ingest.importer_csv import csv_columns, load_records, read_csv, write_csv
from app.ingest.records import DrawRecord, records_from_db
from app.games import get_game
from app.models import DrawBall

BALOTO = DrawRecord("baloto", 2730, date(2026, 11, 2), (18, 19, 20, 31, 43), None, 14, 18_800_000_000, "u")
COLOR = DrawRecord(
    "colorloto", 232, date(2026, 11, 2), (5, 6, 7, 2, 3, 6),
    ("amarillo", "amarillo", "amarillo", "azul", "rojo", "rojo"),
)


def test_columns_per_game():
    assert csv_columns(get_game("baloto"))[-3:] == ["superbalota", "jackpot_cop", "source_url"]
    assert "c6" in csv_columns(get_game("colorloto"))
    assert "superbalota" not in csv_columns(get_game("miloto"))


@pytest.mark.parametrize("rec", [BALOTO, COLOR])
def test_roundtrip(tmp_path, rec):
    path = tmp_path / f"{rec.game}.csv"
    assert write_csv(path, rec.game, [rec]) == 1
    assert write_csv(path, rec.game, [rec]) == 0  # idempotente
    read = read_csv(path, rec.game)
    assert read.errors == []
    assert read.records == [rec]


def test_write_refuses_to_overwrite_different_result(tmp_path):
    path = tmp_path / "baloto.csv"
    write_csv(path, "baloto", [BALOTO])
    changed = DrawRecord("baloto", 2730, BALOTO.draw_date, (1, 2, 3, 4, 5), None, 1)
    with pytest.raises(ValueError, match="no coinciden"):
        write_csv(path, "baloto", [changed])


def test_read_rejects_bad_rows(tmp_path):
    path = tmp_path / "miloto.csv"
    path.write_text(
        "draw_number,draw_date,n1,n2,n3,n4,n5,jackpot_cop,source_url\n"
        "1,2026-01-05,1,2,3,4,5,,\n"
        "2,2026-01-06,1,2,3,4,40,,\n"  # fuera de rango
        "3,no-es-fecha,1,2,3,4,5,,\n"
        "4,2026-01-08,1,1,3,4,5,,\n",  # repetido
        encoding="utf-8",
    )
    read = read_csv(path, "miloto")
    assert [r.draw_number for r in read.records] == [1]
    assert len(read.errors) == 3
    assert ":3:" in read.errors[0] and "fuera de rango" in read.errors[0]


def test_read_reports_missing_columns(tmp_path):
    path = tmp_path / "baloto.csv"
    path.write_text("draw_number,draw_date,n1\n", encoding="utf-8")
    assert "faltan columnas" in read_csv(path, "baloto").errors[0]


def test_load_one_row_per_ball(session):
    res = load_records(session, [BALOTO, COLOR])
    assert res.inserted == 2 and res.conflicts == []
    assert session.scalar(select(func.count(DrawBall.id))) == 6 + 6
    extra = session.scalars(select(DrawBall).where(DrawBall.is_extra)).all()
    assert [b.number for b in extra] == [14]
    assert records_from_db(session, "baloto") == [BALOTO]
    assert records_from_db(session, "colorloto") == [COLOR]


def test_load_is_idempotent_and_reports_conflicts(session):
    load_records(session, [BALOTO])
    res = load_records(session, [BALOTO])
    assert (res.inserted, res.unchanged) == (0, 1)
    changed = DrawRecord("baloto", 2730, BALOTO.draw_date, (1, 2, 3, 4, 5), None, 1)
    res = load_records(session, [changed])
    assert res.inserted == 0 and len(res.conflicts) == 1


def test_same_number_in_two_games_is_fine(session):
    revancha = DrawRecord("revancha", 2730, BALOTO.draw_date, (18, 30, 37, 39, 40), None, 14)
    assert load_records(session, [BALOTO, revancha]).inserted == 2
