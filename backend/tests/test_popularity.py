import pytest

from app.analysis.popularity import popularity
from app.games import Ticket, get_game

BALOTO = get_game("baloto")


def score(nums, extra=1, **kw):
    return popularity(Ticket(tuple(nums), extra=extra), BALOTO, **kw)


def test_birthdays_are_popular():
    s = score([3, 7, 12, 19, 28])
    assert s.score >= 25 and any("fechas" in r for r in s.reasons)


def test_spread_ticket_is_low():
    s = score([4, 18, 33, 37, 42])
    assert s.level == "baja", s.reasons


def test_sequence_scores_high():
    s = score([1, 2, 3, 4, 5])
    assert s.level == "alta"
    assert any("consecutivos" in r for r in s.reasons)


@pytest.mark.parametrize(
    "nums, fragment",
    [
        ([5, 10, 15, 20, 25], "múltiplos de 5"),
        ([2, 12, 22, 32, 42], "misma terminación"),
        ([3, 13, 23, 33, 43], "progresión aritmética"),
        ([36, 37, 38, 39, 40], "misma fila"),
    ],
)
def test_patterns(nums, fragment):
    assert any(fragment in r for r in score(nums).reasons), score(nums).reasons


def test_repeating_a_past_winner():
    past = {frozenset(Ticket((18, 19, 20, 31, 43)).balls())}
    s = score([18, 19, 20, 31, 43], past_results=past)
    assert any("ya salió" in r for r in s.reasons)


def test_colorloto_patterns():
    game = get_game("colorloto")
    same_color = popularity(Ticket((1, 2, 3, 4, 5, 6), ("rojo",) * 6), game)
    assert any("mismo color" in r for r in same_color.reasons)
    same_number = popularity(Ticket((7,) * 6, ("amarillo", "azul", "rojo", "verde", "blanco", "negro")), game)
    assert any("mismo número" in r for r in same_number.reasons)


def test_score_is_capped():
    s = score([1, 2, 3, 4, 5], past_results={frozenset(Ticket((1, 2, 3, 4, 5)).balls())})
    assert s.score <= 100
