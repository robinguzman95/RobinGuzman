"""Representación en memoria de un sorteo, común a CSV, scraper, validador y BD."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.games import Ticket


@dataclass(frozen=True)
class DrawRecord:
    game: str
    draw_number: int
    draw_date: date
    numbers: tuple[int, ...]
    colors: tuple[str, ...] | None = None
    extra: int | None = None
    jackpot_cop: int | None = None
    source_url: str | None = None

    @property
    def ticket(self) -> Ticket:
        return Ticket(self.numbers, self.colors, self.extra)

    def same_result(self, other: "DrawRecord") -> bool:
        """Mismo resultado, sin importar el orden de las balotas."""
        return (
            self.draw_date == other.draw_date
            and sorted(self.ticket.balls(), key=str) == sorted(other.ticket.balls(), key=str)
            and self.extra == other.extra
        )


def records_from_db(session: Session, game_code: str) -> list[DrawRecord]:
    from app.models import Draw, GameRow

    stmt = (
        select(Draw)
        .join(GameRow)
        .where(GameRow.code == game_code)
        .options(selectinload(Draw.balls))
        .order_by(Draw.draw_number)
    )
    out = []
    for d in session.scalars(stmt):
        main = [b for b in d.balls if not b.is_extra]
        extra = next((b.number for b in d.balls if b.is_extra), None)
        colors = tuple(b.color for b in main) if main and main[0].color else None
        out.append(
            DrawRecord(
                game=game_code,
                draw_number=d.draw_number,
                draw_date=d.draw_date,
                numbers=tuple(b.number for b in main),
                colors=colors,
                extra=extra,
                jackpot_cop=d.jackpot_cop,
                source_url=d.source_url,
            )
        )
    return out
