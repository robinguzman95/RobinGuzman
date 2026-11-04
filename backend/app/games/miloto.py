"""MiLoto: 5 números de 1–39 sin repetir, cualquier orden."""

from app.games.base import Game


class MiLoto(Game):
    code = "miloto"
    name = "MiLoto"
    main_count = 5
    main_max = 39
    # lunes, martes, jueves y viernes.
    draw_weekdays = frozenset({0, 1, 3, 4})
