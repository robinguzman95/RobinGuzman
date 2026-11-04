from fractions import Fraction
from math import comb

import pytest

from app.games import GAMES, Ticket, get_game
from app.games.baloto import Baloto, Revancha
from app.games.colorloto import ColorLoto
from app.games.miloto import MiLoto


class TestOdds:
    def test_baloto(self):
        assert Baloto.combinations() == 15_401_568 == comb(43, 5) * 16
        assert Baloto.jackpot_odds() == Fraction(1, 15_401_568)
        assert Baloto.odds_text() == "1 en 15.401.568"

    def test_revancha_same_matrix_as_baloto(self):
        assert Revancha.combinations() == Baloto.combinations()
        assert Revancha.code != Baloto.code

    def test_miloto(self):
        assert MiLoto.combinations() == 575_757 == comb(39, 5)
        assert MiLoto.odds_text() == "1 en 575.757"

    def test_colorloto(self):
        # 7 números x 6 colores = 42 balotas distintas; se sacan 6 sin reposición.
        assert ColorLoto.pool_size() == 42
        assert ColorLoto.combinations() == 5_245_786 == comb(42, 6)

    def test_registry(self):
        assert set(GAMES) == {"baloto", "revancha", "miloto", "colorloto"}
        with pytest.raises(ValueError, match="desconocido"):
            get_game("chance")


class TestValidation:
    def test_valid_baloto(self):
        assert Baloto.validate(Ticket((1, 2, 3, 4, 43), extra=16)) == []

    @pytest.mark.parametrize(
        "ticket, fragment",
        [
            (Ticket((1, 2, 3, 4), extra=1), "se esperaban 5"),
            (Ticket((1, 2, 3, 4, 44), extra=1), "fuera de rango"),
            (Ticket((0, 2, 3, 4, 5), extra=1), "fuera de rango"),
            (Ticket((1, 1, 3, 4, 5), extra=1), "repetidos"),
            (Ticket((1, 2, 3, 4, 5)), "falta la balota extra"),
            (Ticket((1, 2, 3, 4, 5), extra=17), "extra 17 fuera de rango"),
        ],
    )
    def test_invalid_baloto(self, ticket, fragment):
        assert any(fragment in e for e in Baloto.validate(ticket))

    def test_miloto_rejects_extra(self):
        assert MiLoto.validate(Ticket((1, 2, 3, 4, 39))) == []
        assert MiLoto.validate(Ticket((1, 2, 3, 4, 40)))
        assert any("no tiene balota extra" in e for e in MiLoto.validate(Ticket((1, 2, 3, 4, 5), extra=3)))

    def test_colorloto_rules(self):
        # Mismo número con distinto color y mismo color con distinto número: válido.
        ok = Ticket((5, 5, 7, 2, 3, 6), ("amarillo", "azul", "amarillo", "azul", "rojo", "rojo"))
        assert ColorLoto.validate(ok) == []
        # El mismo par número-color dos veces: inválido.
        dup = Ticket((5, 5, 7, 2, 3, 6), ("amarillo", "amarillo", "amarillo", "azul", "rojo", "rojo"))
        assert any("pares número-color repetidos" in e for e in ColorLoto.validate(dup))

    def test_colorloto_needs_known_colors(self):
        assert ColorLoto.validate(Ticket((1, 2, 3, 4, 5, 6)))
        bad = Ticket((1, 2, 3, 4, 5, 6), ("morado",) * 6)
        assert any("color desconocido" in e for e in ColorLoto.validate(bad))
        assert any("fuera de rango 1–7" in e for e in ColorLoto.validate(Ticket((8, 2, 3, 4, 5, 6), ("rojo",) * 6)))

    def test_number_games_reject_colors(self):
        assert any("no usa colores" in e for e in MiLoto.validate(Ticket((1, 2, 3, 4, 5), ("rojo",) * 5)))
