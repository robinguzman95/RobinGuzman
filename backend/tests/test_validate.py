from dataclasses import replace
from datetime import date

from app.ingest.records import DrawRecord
from app.ingest.validate import read_known_gaps, validate_records

from tests.conftest import miloto_series


def test_clean_series_passes():
    recs = miloto_series(220)
    rep = validate_records("miloto", recs)
    assert rep.ok, rep.summary()
    assert rep.warnings == []
    assert rep.coverage_months > 12


def test_detects_gaps():
    recs = miloto_series(20)
    del recs[5:8]
    rep = validate_records("miloto", recs)
    assert rep.missing_numbers == [105, 106, 107]
    assert not rep.ok


def test_documented_gap_does_not_fail(tmp_path):
    recs = miloto_series(20)
    del recs[5]  # sorteo 105
    path = tmp_path / "known_gaps.csv"
    path.write_text(
        "game,draw_number,expected_date,reason,checked_on\n"
        "miloto,105,2025-01-13,sin fuente,2026-11-04\n"
        "colorloto,105,2025-01-13,otro juego,2026-11-04\n",
        encoding="utf-8",
    )
    gaps = read_known_gaps(path)
    rep = validate_records("miloto", recs, gaps)
    assert rep.ok
    assert (rep.missing_numbers, rep.documented_gaps) == ([], [105])
    # Un hueco documentado no tapa otros huecos.
    del recs[8]
    assert validate_records("miloto", recs, gaps).missing_numbers == [109]


def test_documented_gap_already_loaded_warns(tmp_path):
    from app.ingest.validate import KnownGap

    rep = validate_records("miloto", miloto_series(5), [KnownGap("miloto", 102, "x")])
    assert rep.ok and any("known_gaps.csv" in w for w in rep.warnings)


def test_missing_known_gaps_file_is_empty(tmp_path):
    assert read_known_gaps(tmp_path / "no.csv") == []


def test_identical_duplicate_is_warning_conflicting_is_error():
    recs = miloto_series(5)
    rep = validate_records("miloto", recs + [recs[2]])
    assert rep.ok and any("idéntico" in w for w in rep.warnings)

    conflicting = replace(recs[2], numbers=(30, 31, 32, 33, 34))
    rep = validate_records("miloto", recs + [conflicting])
    assert any("resultados distintos" in e for e in rep.errors)


def test_detects_out_of_range_and_date_order():
    recs = miloto_series(5)
    recs[1] = replace(recs[1], numbers=(1, 2, 3, 4, 40))
    recs[3] = replace(recs[3], draw_date=date(2024, 1, 1))
    rep = validate_records("miloto", recs)
    assert any("fuera de rango" in e for e in rep.errors)
    assert any("es anterior al" in e for e in rep.errors)


def test_unusual_weekday_is_only_a_warning():
    recs = miloto_series(5)
    recs[-1] = replace(recs[-1], draw_date=date(2025, 1, 19))  # domingo
    rep = validate_records("miloto", recs)
    assert rep.ok
    assert any("domingo" in w for w in rep.warnings)


def test_future_date_is_error():
    rec = DrawRecord("miloto", 1, date(2999, 1, 1), (1, 2, 3, 4, 5))
    assert any("futura" in e for e in validate_records("miloto", [rec]).errors)


def test_empty_is_not_ok():
    assert not validate_records("baloto", []).ok
