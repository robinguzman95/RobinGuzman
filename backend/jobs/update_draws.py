"""Tarea programada post-sorteo: trae los sorteos nuevos y los carga en la BD.

En producción la BD es la fuente de verdad (el disco del contenedor es efímero), así que esta
tarea carga directo con el mismo validador e importador que usan los CSV. Para respaldar en el
repo: ``uv run lotolab export-csv``.

Uso: ``uv run python -m jobs.update_draws`` o ``POST /ingest/run`` (con token).
"""

from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.config import get_settings
from app.games import GAMES, get_game
from app.ingest.importer_csv import load_records
from app.ingest.records import DrawRecord, records_from_db
from app.ingest.scraper import FAMILY, Scraper
from app.ingest.validate import read_known_gaps, validate_records

LOOKBACK_DAYS = 7  # vuelve a revisar la última semana por si un sorteo se publicó tarde


@dataclass
class UpdateSummary:
    inserted: dict[str, int] = field(default_factory=dict)
    rejected: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    validation: dict[str, str] = field(default_factory=dict)
    last_draw: dict[str, str | None] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.rejected and not self.conflicts and all(v == "OK" for v in self.validation.values())


def run_update(session: Session, scraper: Scraper, today: date | None = None) -> UpdateSummary:
    today = today or date.today()
    summary = UpdateSummary()
    existing = {code: records_from_db(session, code) for code in GAMES}

    for family in sorted(set(FAMILY.values())):
        codes = [c for c, f in FAMILY.items() if f == family]
        last = max((r.draw_date for c in codes for r in existing[c]), default=today - timedelta(days=30))
        scraped = scraper.scrape(family, since=last - timedelta(days=LOOKBACK_DAYS))
        valid: list[DrawRecord] = []
        for rec in scraped:
            problems = get_game(rec.game).validate(rec.ticket)
            if problems:
                summary.rejected.append(f"{rec.game} {rec.draw_number}: {'; '.join(problems)}")
            else:
                valid.append(rec)
        before = {c: len(existing[c]) for c in codes}
        loaded = load_records(session, valid)
        summary.conflicts += loaded.conflicts
        for c in codes:
            summary.inserted[c] = len(records_from_db(session, c)) - before[c]

    gaps = read_known_gaps(get_settings().raw_data_dir / "known_gaps.csv")
    for code in GAMES:
        recs = records_from_db(session, code)
        rep = validate_records(code, recs, gaps)
        summary.validation[code] = "OK" if rep.ok else "; ".join(
            rep.errors[:3] + ([f"huecos {rep.missing_numbers[:5]}"] if rep.missing_numbers else []))
        summary.last_draw[code] = max((r.draw_date for r in recs), default=None).isoformat() if recs else None
    return summary


def main() -> int:
    from app.db import get_sessionmaker

    s = get_settings()
    scraper = Scraper(s.cache_dir, s.scraper_delay_seconds, s.scraper_user_agent, use_cache=False)
    with get_sessionmaker()() as session:
        summary = run_update(session, scraper)
    print(summary)
    return 0 if summary.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
