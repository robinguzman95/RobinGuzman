"""Lectura/escritura de los CSV de data/raw y carga a la base de datos.

Formato de ``data/raw/{juego}.csv`` (una fila por sorteo, fecha ISO):

    draw_number,draw_date,n1..nK[,c1..cK][,superbalota],jackpot_cop,source_url

- ``c1..cK`` solo en juegos con color (ColorLoto); ``superbalota`` solo en Baloto/Revancha.
- ``jackpot_cop`` y ``source_url`` pueden ir vacíos.
"""

import csv
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.games import Game, get_game
from app.ingest.records import DrawRecord


def csv_columns(game: type[Game]) -> list[str]:
    cols = ["draw_number", "draw_date"]
    cols += [f"n{i}" for i in range(1, game.main_count + 1)]
    if game.colors:
        cols += [f"c{i}" for i in range(1, game.main_count + 1)]
    if game.extra_max is not None:
        cols.append("superbalota")
    return cols + ["jackpot_cop", "source_url"]


@dataclass
class ReadResult:
    records: list[DrawRecord] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def read_csv(path: Path, game_code: str) -> ReadResult:
    """Lee el CSV. Las filas mal formadas o inválidas se reportan, no se cargan."""
    game = get_game(game_code)
    result = ReadResult()
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        missing = set(csv_columns(game)) - set(reader.fieldnames or [])
        if missing:
            result.errors.append(f"{path.name}: faltan columnas {sorted(missing)}")
            return result
        for line, row in enumerate(reader, start=2):
            try:
                rec = _row_to_record(row, game)
            except (ValueError, KeyError) as exc:
                result.errors.append(f"{path.name}:{line}: {exc}")
                continue
            problems = game.validate(rec.ticket)
            if problems:
                result.errors.append(f"{path.name}:{line}: sorteo {rec.draw_number}: {'; '.join(problems)}")
                continue
            result.records.append(rec)
    return result


def _row_to_record(row: dict[str, str], game: type[Game]) -> DrawRecord:
    k = game.main_count
    numbers = tuple(int(row[f"n{i}"]) for i in range(1, k + 1))
    colors = tuple(row[f"c{i}"].strip().lower() for i in range(1, k + 1)) if game.colors else None
    extra = int(row["superbalota"]) if game.extra_max is not None else None
    jackpot = row.get("jackpot_cop", "").strip()
    return DrawRecord(
        game=game.code,
        draw_number=int(row["draw_number"]),
        draw_date=date.fromisoformat(row["draw_date"].strip()),
        numbers=numbers,
        colors=colors,
        extra=extra,
        jackpot_cop=int(jackpot) if jackpot else None,
        source_url=(row.get("source_url") or "").strip() or None,
    )


def write_csv(path: Path, game_code: str, records: list[DrawRecord]) -> int:
    """Fusiona ``records`` con el CSV existente (clave: draw_number) y lo reescribe ordenado.

    Si un sorteo ya existe con otro resultado, se lanza ValueError: nunca se pisa en silencio.
    Devuelve cuántos sorteos nuevos se añadieron.
    """
    game = get_game(game_code)
    existing: dict[int, DrawRecord] = {}
    if path.exists():
        read = read_csv(path, game_code)
        if read.errors:
            raise ValueError("el CSV existente tiene errores:\n" + "\n".join(read.errors))
        existing = {r.draw_number: r for r in read.records}

    added = 0
    for rec in records:
        old = existing.get(rec.draw_number)
        if old is None:
            existing[rec.draw_number] = rec
            added += 1
        elif not old.same_result(rec):
            raise ValueError(f"{game_code} sorteo {rec.draw_number}: el CSV y la fuente no coinciden")

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(csv_columns(game))
        for rec in sorted(existing.values(), key=lambda r: r.draw_number):
            row: list[object] = [rec.draw_number, rec.draw_date.isoformat(), *rec.numbers]
            if game.colors:
                row += list(rec.colors or ())
            if game.extra_max is not None:
                row.append(rec.extra)
            row += [rec.jackpot_cop or "", rec.source_url or ""]
            writer.writerow(row)
    return added


@dataclass
class LoadResult:
    inserted: int = 0
    unchanged: int = 0
    conflicts: list[str] = field(default_factory=list)


def load_records(session: Session, records: list[DrawRecord]) -> LoadResult:
    """Inserta sorteos nuevos. Los ya cargados se ignoran si coinciden y se reportan si no."""
    from app.ingest.records import records_from_db
    from app.models import Draw, DrawBall, GameRow

    result = LoadResult()
    by_game: dict[str, list[DrawRecord]] = {}
    for rec in records:
        by_game.setdefault(rec.game, []).append(rec)

    for code, recs in by_game.items():
        game_row = session.scalar(select(GameRow).where(GameRow.code == code))
        if game_row is None:
            raise ValueError(f"el juego {code!r} no está en la tabla games; corre `lotolab init`")
        in_db = {r.draw_number: r for r in records_from_db(session, code)}
        seen: dict[int, DrawRecord] = {}
        for rec in recs:
            prior = in_db.get(rec.draw_number) or seen.get(rec.draw_number)
            if prior is not None:
                if prior.same_result(rec):
                    result.unchanged += 1
                else:
                    result.conflicts.append(f"{code} sorteo {rec.draw_number}: resultado distinto al ya cargado")
                continue
            seen[rec.draw_number] = rec
            draw = Draw(
                game_id=game_row.id,
                draw_number=rec.draw_number,
                draw_date=rec.draw_date,
                jackpot_cop=rec.jackpot_cop,
                source_url=rec.source_url,
            )
            for pos, (number, color) in enumerate(rec.ticket.balls(), start=1):
                draw.balls.append(DrawBall(position=pos, number=number, color=color, is_extra=False))
            if rec.extra is not None:
                draw.balls.append(
                    DrawBall(position=len(rec.numbers) + 1, number=rec.extra, color=None, is_extra=True)
                )
            session.add(draw)
            result.inserted += 1
    session.commit()
    return result


def discover_csvs(raw_dir: Path) -> dict[str, Path]:
    """{código de juego: ruta} para cada data/raw/{código}.csv que exista."""
    from app.games import GAMES

    return {code: raw_dir / f"{code}.csv" for code in GAMES if (raw_dir / f"{code}.csv").exists()}
