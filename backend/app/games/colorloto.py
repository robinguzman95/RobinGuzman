"""ColorLoto: 6 balotas, cada una con número 1–7 y uno de 6 colores.

Regla oficial (baloto.com/colorloto, revisado 2026-11-04): se pueden repetir colores con
números distintos y números con colores distintos, pero "no puedes repetir combinaciones
iguales de número y color". Por tanto el bombo tiene 7 x 6 = 42 balotas distintas y el
premio mayor (6 aciertos de número y color, en cualquier orden) es 1 en C(42, 6) = 5.245.786.
"""

from app.games.base import Game

COLORS = ("amarillo", "azul", "rojo", "verde", "blanco", "negro")


class ColorLoto(Game):
    code = "colorloto"
    name = "ColorLoto"
    main_count = 6
    main_max = 7
    colors = COLORS
    # lunes y jueves.
    draw_weekdays = frozenset({0, 3})
