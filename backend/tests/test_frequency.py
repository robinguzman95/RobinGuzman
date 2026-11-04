"""Criterio de salida de la Fase 2: los números cuadran con un conteo manual de 10 sorteos.

Los valores esperados están escritos A MANO a partir de los sorteos reales (ver
docs/conteo_manual_fase2.md); no se calculan con el código que se está probando.
"""

from datetime import date

import pytest

from app.analysis import frequency as fq
from app.config import REPO_ROOT
from app.games import get_game
from app.ingest.importer_csv import read_csv
from app.ingest.records import DrawRecord

RAW = REPO_ROOT / "data" / "raw"


def last10(code: str) -> list[DrawRecord]:
    read = read_csv(RAW / f"{code}.csv", code)
    assert read.errors == []
    return fq.apply_window(read.records, 10)


# Baloto 2721–2730 (12 oct – 2 nov 2026), contado a mano.
BALOTO_MANUAL = {
    4: 1, 5: 1, 6: 4, 7: 1, 8: 1, 9: 1, 10: 1, 11: 2, 12: 1, 13: 2, 15: 1, 17: 1, 18: 1,
    19: 4, 20: 2, 21: 1, 23: 1, 25: 3, 26: 1, 28: 2, 29: 4, 30: 2, 31: 1, 33: 2, 35: 1,
    36: 1, 38: 1, 39: 1, 40: 1, 41: 2, 43: 2,
}
BALOTO_SUPERBALOTA_MANUAL = {3: 1, 4: 1, 7: 1, 8: 1, 9: 1, 12: 2, 14: 1, 16: 2}
# Pares que salieron juntos dos veces (ningún par salió tres veces).
BALOTO_PAIRS_TWICE = {(6, 19), (6, 28), (11, 29), (13, 41), (19, 20), (25, 33)}

# MiLoto 626–635 (19 oct – 3 nov 2026), contado a mano.
MILOTO_MANUAL = {
    1: 3, 4: 1, 5: 1, 6: 1, 8: 2, 10: 2, 11: 2, 12: 3, 13: 2, 14: 4, 15: 1, 16: 1, 18: 2,
    19: 1, 20: 1, 21: 1, 23: 2, 24: 1, 25: 1, 26: 2, 27: 2, 28: 2, 29: 1, 33: 1, 34: 3,
    35: 2, 36: 2, 37: 3,
}


class TestManualCount:
    def test_baloto_window_is_the_expected_draws(self):
        recs = last10("baloto")
        assert [r.draw_number for r in recs] == list(range(2721, 2731))

    def test_baloto_numbers(self):
        freq = fq.number_frequency(last10("baloto"), get_game("baloto"))
        expected = {n: BALOTO_MANUAL.get(n, 0) for n in range(1, 44)}
        assert freq == expected
        assert sum(freq.values()) == 50

    def test_baloto_superbalota(self):
        freq = fq.extra_frequency(last10("baloto"), get_game("baloto"))
        assert freq == {n: BALOTO_SUPERBALOTA_MANUAL.get(n, 0) for n in range(1, 17)}

    def test_baloto_pairs(self):
        counts = fq.combo_frequency(last10("baloto"), 2)
        twice = {tuple(n for n, _ in combo) for combo, c in counts.items() if c == 2}
        assert twice == BALOTO_PAIRS_TWICE
        assert max(counts.values()) == 2
        assert max(fq.combo_frequency(last10("baloto"), 3).values()) == 1

    def test_baloto_hot_and_overdue(self):
        game = get_game("baloto")
        hot, cold = fq.hot_cold(last10("baloto"), game, n=4)
        # 6, 19 y 29 salieron 4 veces; desempate por recencia: 19 (último sorteo), 29 (hace 1), 6 (hace 5).
        assert [s.ball[0] for s in hot] == [19, 29, 6, 25]
        assert [s.count for s in hot] == [4, 4, 4, 3]
        assert hot[0].draws_since == 0 and hot[2].draws_since == 5
        # Fríos: los 12 que no salieron (1, 2, 3, 14, 16, 22, 24, 27, 32, 34, 37, 42).
        assert all(s.count == 0 and s.draws_since is None for s in cold)

    def test_baloto_shape_of_last_draw(self):
        last = last10("baloto")[-1:]  # 18, 19, 20, 31, 43
        shape = fq.shape_stats(last, get_game("baloto"))
        assert shape.sum_min == shape.sum_max == 131
        assert shape.even_counts[2] == 1  # 18 y 20
        assert shape.high_counts[2] == 1  # 31 y 43 (> 21.5)

    def test_miloto_numbers(self):
        recs = last10("miloto")
        assert [r.draw_number for r in recs] == list(range(626, 636))
        freq = fq.number_frequency(recs, get_game("miloto"))
        assert freq == {n: MILOTO_MANUAL.get(n, 0) for n in range(1, 40)}


class TestWindows:
    @pytest.mark.parametrize("raw, parsed", [(None, "12m"), ("all", "all"), ("6m", "6m"), ("50", 50), (20, 20)])
    def test_parse(self, raw, parsed):
        assert fq.parse_window(raw) == parsed

    @pytest.mark.parametrize("raw", ["0", "-3", "abc", "0m", "12x"])
    def test_parse_rejects(self, raw):
        with pytest.raises(ValueError):
            fq.parse_window(raw)

    def test_months_counted_from_last_draw(self):
        recs = [DrawRecord("miloto", i, date(2025, 1, 1 + i), (1, 2, 3, 4, 5)) for i in range(20)]
        recs.append(DrawRecord("miloto", 100, date(2026, 6, 1), (1, 2, 3, 4, 5)))
        assert [r.draw_number for r in fq.apply_window(recs, "1m")] == [100]
        assert len(fq.apply_window(recs, "all")) == 21


class TestColorLoto:
    REC = DrawRecord("colorloto", 1, date(2026, 1, 1), (5, 5, 7, 2, 3, 6),
                     ("amarillo", "azul", "amarillo", "azul", "rojo", "rojo"))

    def test_ball_number_and_color_marginals(self):
        game = get_game("colorloto")
        balls = fq.ball_frequency([self.REC], game)
        assert len(balls) == 42 and sum(balls.values()) == 6
        assert balls[(5, "amarillo")] == 1 and balls[(5, "verde")] == 0
        assert fq.number_frequency([self.REC], game)[5] == 2
        assert fq.color_frequency([self.REC], game) == {
            "amarillo": 2, "azul": 2, "rojo": 2, "verde": 0, "blanco": 0, "negro": 0}

    def test_labels(self):
        assert fq.ball_label((3, "rojo")) == "3-rojo"
        assert fq.ball_label((3, None)) == "3"
