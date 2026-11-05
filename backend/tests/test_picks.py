from datetime import date

import pytest

from app.analysis.picks import CRITERIA, build_picks, category_for, evaluate, play_ticket, typical_shape
from app.games import Ticket, get_game
from app.ingest.prizes import PrizeRow
from app.ingest.records import DrawRecord
from app.main import app

from tests.conftest import simulate_draws
from tests.test_api import make_client


@pytest.mark.parametrize("code", ["baloto", "miloto", "colorloto"])
def test_picks_are_valid_and_deterministic(code):
    game = get_game(code)
    hist = simulate_draws(code, 200, seed=1)
    a = build_picks(hist, game)
    b = build_picks(hist, game)
    assert [p.criterion for p in a] == list(CRITERIA)
    assert [p.text for p in a] == [p.text for p in b]
    for p in a:
        assert game.validate(p.ticket) == [], (p.criterion, p.text)
        assert p.reason


def test_hot_pick_uses_most_frequent_and_only_history():
    hist = [DrawRecord("miloto", i, date(2026, 1, 1), (1, 2, 3, 4, 5) if i % 2 else (1, 2, 3, 4, 6)) for i in range(1, 41)]
    hot = build_picks(hist, get_game("miloto"), "all")[0]
    assert sorted(n for n, _ in hot.balls)[:4] == [1, 2, 3, 4]
    # Un sorteo posterior no debe cambiar una jugada armada antes de él.
    more = hist + [DrawRecord("miloto", 41, date(2026, 2, 1), (30, 31, 32, 33, 34))]
    assert build_picks(hist, get_game("miloto"), 40)[0].text == build_picks(more[:-1], get_game("miloto"), 40)[0].text


def test_shape_from_history():
    hist = simulate_draws("baloto", 300, seed=2)
    s = typical_shape(hist, get_game("baloto"))
    assert 70 < s.sum_low < s.sum_high < 150
    assert set(s.evens) <= {1, 2, 3, 4} and len(s.highs) == 2


def test_categories_per_game():
    b = get_game("baloto")
    draw = DrawRecord("baloto", 1, date(2026, 1, 1), (1, 2, 3, 4, 5), None, 7)
    assert category_for(b, Ticket((1, 2, 3, 4, 5), extra=7), draw) == ["5+SB"]
    assert category_for(b, Ticket((1, 2, 3, 40, 41), extra=1), draw) == ["3"]
    assert category_for(b, Ticket((1, 2, 30, 40, 41), extra=7), draw) == ["2+SB"]
    assert category_for(b, Ticket((1, 20, 30, 40, 41), extra=7), draw) == ["0+SB"]
    assert category_for(b, Ticket((1, 2, 30, 40, 41), extra=1), draw) == []
    m = get_game("miloto")
    assert category_for(m, Ticket((1, 2, 30, 31, 32)), DrawRecord("miloto", 1, date(2026, 1, 1), (1, 2, 3, 4, 5))) == ["2"]
    c = get_game("colorloto")
    d = DrawRecord("colorloto", 1, date(2026, 1, 1), (1, 2, 3, 4, 5, 6), ("rojo",) * 3 + ("azul",) * 3)
    same_numbers = Ticket((1, 2, 3, 4, 5, 6), ("azul",) * 3 + ("rojo",) * 3)
    assert "6N" in category_for(c, same_numbers, d) and "6C" in category_for(c, same_numbers, d)


def test_play_ticket_pays_real_prizes():
    g = get_game("miloto")
    draws = [DrawRecord("miloto", i, date(2026, 1, i), (1, 2, 3, 4, 5)) for i in (1, 2, 3)]
    prizes = {
        1: {"3": PrizeRow("miloto", 1, None, "3", 100, 40_000, 0)},
        2: {"3": PrizeRow("miloto", 2, None, "3", 0, 0, 0)},  # nadie ganó: se usa el promedio
        3: {"2": PrizeRow("miloto", 3, None, "2", 10, 4_000, 0)},
    }
    t = Ticket((1, 2, 3, 30, 31))
    r = play_ticket(g, t, draws[:2], prizes, {"3": 50_000})
    assert (r.draws, r.cost, r.won, r.prize_draws, r.best) == (2, 8_000, 90_000, 2, 3)
    assert r.hits == {3: 2}


def test_evaluate_builds_out_of_sample_before_test_period():
    code = "miloto"
    recs = simulate_draws(code, 120, seed=5)
    test = recs[80:]
    rows = [PrizeRow(code, r.draw_number, None, cat, 5, pz, 0)
            for r in test for cat, pz in (("2", 4000), ("3", 40_000), ("4", 1_000_000), ("5", 0))]
    ev = evaluate(get_game(code), recs, rows, sims=200)
    assert ev["test_draws"] == 40 and ev["built_until"] < ev["test_from"]
    assert len(ev["out_of_sample"]) == len(CRITERIA) == len(ev["in_sample"])
    for x in ev["out_of_sample"]:
        assert x["cost"] == 40 * 4000 and 0 <= x["percentile_vs_random"] <= 1
    assert ev["random"]["p5_return"] <= ev["random"]["median_return"] <= ev["random"]["p95_return"]


def test_picks_endpoint():
    client = make_client(simulate_draws("baloto", 120, seed=8))
    try:
        body = client.get("/games/baloto/picks", params={"window": "100"}).json()
        assert body["n_draws"] == 100 and len(body["picks"]) == len(CRITERIA)
        assert body["odds"]["jackpot_odds"] == "1 en 15.401.568"
        assert "No tienen más probabilidad" in body["notice"]
        assert all(p["extra"] is not None for p in body["picks"])
        assert client.get("/games/chance/picks").status_code == 404
    finally:
        app.dependency_overrides.clear()
