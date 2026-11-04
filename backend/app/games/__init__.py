"""Registro de juegos. Añadir un juego = crear su clase y agregarla a GAMES."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.games.base import Game, Ticket
from app.games.baloto import Baloto, Revancha
from app.games.colorloto import ColorLoto
from app.games.miloto import MiLoto

GAMES: dict[str, type[Game]] = {g.code: g for g in (Baloto, Revancha, MiLoto, ColorLoto)}


def get_game(code: str) -> type[Game]:
    try:
        return GAMES[code]
    except KeyError:
        raise ValueError(f"juego desconocido: {code!r}; opciones: {', '.join(GAMES)}") from None


def sync_games(session: Session) -> None:
    """Crea o actualiza las filas de la tabla games a partir del registro."""
    from app.models import GameRow

    existing = {row.code: row for row in session.scalars(select(GameRow))}
    for game in GAMES.values():
        row = existing.get(game.code) or GameRow(code=game.code)
        row.name = game.name
        row.main_count = game.main_count
        row.main_max = game.main_max
        row.extra_max = game.extra_max
        row.color_set = ",".join(game.colors) if game.colors else None
        session.add(row)
    session.commit()


__all__ = ["GAMES", "Game", "Ticket", "get_game", "sync_games"]
