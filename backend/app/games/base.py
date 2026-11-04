"""Clase base de los juegos: matriz, validación y probabilidad real del premio mayor.

Un juego se describe por:
- ``main_count`` balotas principales con número en ``1..main_max``;
- opcionalmente un color por balota (``colors``); entonces cada balota es un par
  (número, color) y el bombo tiene ``main_max * len(colors)`` balotas distintas;
- opcionalmente una balota extra en ``1..extra_max`` (la superbalota de Baloto).

Las balotas principales se extraen sin reposición y el orden no importa, así que el
número de jugadas posibles es ``C(pool, main_count) * (extra_max or 1)``.
"""

from dataclasses import dataclass
from fractions import Fraction
from math import comb
from typing import ClassVar


@dataclass(frozen=True)
class Ticket:
    """Una jugada o el resultado de un sorteo."""

    numbers: tuple[int, ...]
    colors: tuple[str, ...] | None = None
    extra: int | None = None

    def balls(self) -> tuple[tuple[int, str | None], ...]:
        """Balotas principales como pares (número, color)."""
        colors = self.colors or (None,) * len(self.numbers)
        return tuple(zip(self.numbers, colors, strict=True))


class Game:
    code: ClassVar[str]
    name: ClassVar[str]
    main_count: ClassVar[int]
    main_max: ClassVar[int]
    extra_max: ClassVar[int | None] = None
    colors: ClassVar[tuple[str, ...] | None] = None
    # 0 = lunes ... 6 = domingo. Los calendarios cambian: el validador solo advierte.
    draw_weekdays: ClassVar[frozenset[int]] = frozenset()

    # --- matriz y probabilidades -------------------------------------------------
    @classmethod
    def pool_size(cls) -> int:
        return cls.main_max * (len(cls.colors) if cls.colors else 1)

    @classmethod
    def combinations(cls) -> int:
        """Número de jugadas distintas posibles."""
        return comb(cls.pool_size(), cls.main_count) * (cls.extra_max or 1)

    @classmethod
    def jackpot_odds(cls) -> Fraction:
        """Probabilidad exacta de acertar el premio mayor con una jugada."""
        return Fraction(1, cls.combinations())

    @classmethod
    def odds_text(cls) -> str:
        """'1 en 15.401.568' (separador de miles colombiano)."""
        return "1 en " + f"{cls.combinations():,}".replace(",", ".")

    # --- validación --------------------------------------------------------------
    @classmethod
    def validate(cls, ticket: Ticket) -> list[str]:
        """Devuelve la lista de errores; vacía si la jugada es válida."""
        errors: list[str] = []
        if len(ticket.numbers) != cls.main_count:
            errors.append(f"se esperaban {cls.main_count} números, llegaron {len(ticket.numbers)}")
        for n in ticket.numbers:
            if not 1 <= n <= cls.main_max:
                errors.append(f"número {n} fuera de rango 1–{cls.main_max}")

        if cls.colors:
            if ticket.colors is None or len(ticket.colors) != len(ticket.numbers):
                errors.append("cada balota necesita un color")
            else:
                for c in ticket.colors:
                    if c not in cls.colors:
                        errors.append(f"color desconocido: {c!r}")
        elif ticket.colors is not None:
            errors.append(f"{cls.name} no usa colores")

        if not errors:
            balls = ticket.balls()
            if len(set(balls)) != len(balls):
                what = "pares número-color" if cls.colors else "números"
                errors.append(f"hay {what} repetidos")

        if cls.extra_max is not None:
            if ticket.extra is None:
                errors.append("falta la balota extra")
            elif not 1 <= ticket.extra <= cls.extra_max:
                errors.append(f"balota extra {ticket.extra} fuera de rango 1–{cls.extra_max}")
        elif ticket.extra is not None:
            errors.append(f"{cls.name} no tiene balota extra")
        return errors

    @classmethod
    def is_valid(cls, ticket: Ticket) -> bool:
        return not cls.validate(ticket)
