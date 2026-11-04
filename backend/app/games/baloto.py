"""Baloto y Revancha: 5 números de 1–43 sin repetir + superbalota 1–16."""

from app.games.base import Game


class Baloto(Game):
    code = "baloto"
    name = "Baloto"
    main_count = 5
    main_max = 43
    extra_max = 16
    # baloto.com, nov-2026: lunes, miércoles y sábado.
    draw_weekdays = frozenset({0, 2, 5})


class Revancha(Baloto):
    """Misma jugada que Baloto, sorteo independiente."""

    code = "revancha"
    name = "Revancha"
