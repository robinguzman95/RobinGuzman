"""Validación del histórico: duplicados, huecos, rangos, fechas y cobertura.

Trabaja sobre listas de DrawRecord, así sirve igual para un CSV que para la BD.
- *errores*: invalidan el dataset (duplicados en conflicto, rangos, orden de fechas).
- *advertencias*: merecen revisión pero pueden ser legítimas (día de sorteo inusual,
  huecos en la numeración, que pueden deberse a sorteos aún no descargados).
"""

import csv
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from app.games import get_game
from app.ingest.records import DrawRecord

WEEKDAYS_ES = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")


@dataclass
class ValidationReport:
    game: str
    total: int = 0
    first_date: date | None = None
    last_date: date | None = None
    missing_numbers: list[int] = field(default_factory=list)
    documented_gaps: list[int] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors and not self.missing_numbers

    @property
    def coverage_months(self) -> float:
        if not self.first_date or not self.last_date:
            return 0.0
        return (self.last_date - self.first_date).days / 30.4375

    def summary(self) -> str:
        lines = [
            f"[{self.game}] {self.total} sorteos"
            + (f", {self.first_date} → {self.last_date} ({self.coverage_months:.1f} meses)" if self.total else "")
        ]
        if self.missing_numbers:
            lines.append(f"  huecos: {len(self.missing_numbers)} sorteos faltantes, p. ej. {_preview(self.missing_numbers)}")
        if self.documented_gaps:
            lines.append(f"  huecos documentados (known_gaps.csv): {_preview(self.documented_gaps)}")
        lines += [f"  ERROR {e}" for e in self.errors]
        lines += [f"  aviso {w}" for w in self.warnings]
        lines.append("  OK" if self.ok else "  NO PASA")
        return "\n".join(lines)


def _preview(nums: list[int], k: int = 8) -> str:
    head = ", ".join(map(str, nums[:k]))
    return head + (" …" if len(nums) > k else "")


@dataclass(frozen=True)
class KnownGap:
    game: str
    draw_number: int
    reason: str


def read_known_gaps(path: Path) -> list[KnownGap]:
    """Sorteos que se sabe que faltan y por qué (data/raw/known_gaps.csv)."""
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return [
            KnownGap(row["game"].strip(), int(row["draw_number"]), row["reason"].strip())
            for row in csv.DictReader(fh)
        ]


def validate_records(
    game_code: str, records: list[DrawRecord], known_gaps: list[KnownGap] | None = None
) -> ValidationReport:
    """``known_gaps``: huecos explicados; se reportan aparte y no hacen fallar la validación."""
    game = get_game(game_code)
    rep = ValidationReport(game=game_code, total=len(records))
    if not records:
        rep.errors.append("no hay sorteos")
        return rep

    # 1) Rangos y reglas de la matriz.
    for r in records:
        for problem in game.validate(r.ticket):
            rep.errors.append(f"sorteo {r.draw_number}: {problem}")

    # 2) Duplicados por número de sorteo.
    counts = Counter(r.draw_number for r in records)
    for number, n in sorted(counts.items()):
        if n > 1:
            same = [r for r in records if r.draw_number == number]
            if all(same[0].same_result(o) for o in same[1:]):
                rep.warnings.append(f"sorteo {number} aparece {n} veces (idéntico)")
            else:
                rep.errors.append(f"sorteo {number} aparece {n} veces con resultados distintos")

    # 3) Mismo resultado repetido en otra fecha (señal de copia mal hecha).
    seen: dict[tuple, int] = {}
    for r in sorted(records, key=lambda x: x.draw_number):
        key = (tuple(sorted(r.ticket.balls(), key=str)), r.extra)
        if key in seen and seen[key] != r.draw_number:
            rep.warnings.append(f"sorteos {seen[key]} y {r.draw_number} tienen el mismo resultado")
        seen.setdefault(key, r.draw_number)

    unique = sorted({r.draw_number: r for r in records}.values(), key=lambda x: x.draw_number)
    rep.first_date = min(r.draw_date for r in unique)
    rep.last_date = max(r.draw_date for r in unique)

    # 4) Huecos en la numeración.
    numbers = [r.draw_number for r in unique]
    present = set(numbers)
    documented = {g.draw_number for g in known_gaps or [] if g.game == game_code}
    missing = [n for n in range(numbers[0], numbers[-1] + 1) if n not in present]
    rep.missing_numbers = [n for n in missing if n not in documented]
    rep.documented_gaps = [n for n in missing if n in documented]
    for n in sorted(documented & present):
        rep.warnings.append(f"sorteo {n} figura en known_gaps.csv pero ya está cargado: quítalo de ese archivo")

    # 5) Las fechas deben avanzar con el número de sorteo.
    for prev, cur in zip(unique, unique[1:]):
        if cur.draw_date < prev.draw_date:
            rep.errors.append(
                f"sorteo {cur.draw_number} ({cur.draw_date}) es anterior al {prev.draw_number} ({prev.draw_date})"
            )
        elif cur.draw_date == prev.draw_date:
            rep.errors.append(f"sorteos {prev.draw_number} y {cur.draw_number} tienen la misma fecha")

    # 6) Día de la semana (solo aviso: los calendarios cambian).
    if game.draw_weekdays:
        odd = Counter(WEEKDAYS_ES[r.draw_date.weekday()] for r in unique if r.draw_date.weekday() not in game.draw_weekdays)
        for day, n in odd.items():
            rep.warnings.append(f"{n} sorteo(s) en {day}, día no habitual para {game.name}")

    # 7) Fechas en el futuro.
    today = date.today()
    for r in unique:
        if r.draw_date > today:
            rep.errors.append(f"sorteo {r.draw_number} tiene fecha futura {r.draw_date}")
    return rep
