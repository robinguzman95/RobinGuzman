"""Línea de comandos: ``uv run lotolab {init,scrape,import,validate}``."""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

from app.config import get_settings


def _migrate(url: str) -> None:
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url)
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "head")


def cmd_init(_args: argparse.Namespace) -> int:
    from app.db import get_sessionmaker
    from app.games import sync_games

    settings = get_settings()
    if settings.database_url.startswith("sqlite:///"):
        Path(settings.database_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    _migrate(settings.database_url)
    with get_sessionmaker()() as session:
        sync_games(session)
    print(f"BD lista: {settings.database_url}")
    return 0


def cmd_scrape(args: argparse.Namespace) -> int:
    from app.ingest.importer_csv import write_csv
    from app.ingest.scraper import FAMILY, Scraper

    settings = get_settings()
    since = date.fromisoformat(args.since) if args.since else date.today() - timedelta(days=400)
    families = sorted({FAMILY[g] for g in args.game}) if args.game else ["baloto", "miloto", "colorloto"]
    scraper = Scraper(settings.cache_dir, settings.scraper_delay_seconds, settings.scraper_user_agent)
    for family in families:
        records = scraper.scrape(family, since, args.max_pages)
        for code in sorted({r.game for r in records}):
            recs = [r for r in records if r.game == code]
            path = settings.raw_data_dir / f"{code}.csv"
            added = write_csv(path, code, recs)
            print(f"{code}: {len(recs)} sorteos leídos desde {since}, {added} nuevos → {path}")
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    from app.db import get_sessionmaker
    from app.ingest.importer_csv import discover_csvs, load_records, read_csv

    settings = get_settings()
    csvs = discover_csvs(settings.raw_data_dir)
    if args.game:
        csvs = {k: v for k, v in csvs.items() if k in args.game}
    if not csvs:
        print(f"no hay CSV en {settings.raw_data_dir}")
        return 1
    status = 0
    with get_sessionmaker()() as session:
        for code, path in csvs.items():
            read = read_csv(path, code)
            for e in read.errors:
                print("  ERROR", e)
            loaded = load_records(session, read.records)
            for c in loaded.conflicts:
                print("  CONFLICTO", c)
            print(f"{code}: {loaded.inserted} nuevos, {loaded.unchanged} ya estaban, {len(read.errors)} filas rechazadas")
            status |= bool(read.errors or loaded.conflicts)
    return status


def cmd_validate(args: argparse.Namespace) -> int:
    from app.db import get_sessionmaker
    from app.games import GAMES
    from app.ingest.records import records_from_db
    from app.ingest.validate import read_known_gaps, validate_records

    codes = args.game or list(GAMES)
    gaps = read_known_gaps(get_settings().raw_data_dir / "known_gaps.csv")
    status = 0
    with get_sessionmaker()() as session:
        for code in codes:
            rep = validate_records(code, records_from_db(session, code), gaps)
            print(rep.summary())
            if not rep.ok or rep.coverage_months < args.min_months:
                status = 1
                if rep.total and rep.coverage_months < args.min_months:
                    print(f"  cobertura menor a {args.min_months} meses")
    return status


def _records_by_game(codes: list[str]) -> dict:
    from app.db import get_sessionmaker
    from app.ingest.records import records_from_db

    with get_sessionmaker()() as session:
        return {code: records_from_db(session, code) for code in codes}


def cmd_backtest(args: argparse.Namespace) -> int:
    from app.backtest.engine import run_backtest
    from app.backtest.strategies import get_strategy
    from app.games import get_game

    game = get_game(args.game)
    recs = _records_by_game([game.code])[game.code]
    o = run_backtest(recs, game, get_strategy(args.strategy), args.strategy, window=args.window, seed=args.seed)
    print(f"{game.name} · {o.strategy} · ventana {o.window} · {o.n_draws} sorteos ({o.date_from} → {o.date_to})")
    print(f"  aciertos/sorteo {o.avg_hits:.3f}  ·  azar {o.baseline.mean:.3f} [p5 {o.baseline.p5:.3f} – p95 {o.baseline.p95:.3f}]")
    print(f"  distribución {o.hit_distribution}  ·  p-valor {o.p_value:.3f}")
    print(f"  → {o.verdict()}  ·  premio mayor: {game.odds_text()}")
    return 0


def cmd_backtest_all(args: argparse.Namespace) -> int:
    from app.backtest.report import render_markdown, run_all
    from app.config import REPO_ROOT
    from app.games import GAMES

    codes = args.game or list(GAMES)
    rows, alpha_b, notes = run_all(_records_by_game(codes), args.strategy, seed=args.seed)
    md = render_markdown(rows, alpha_b, notes)
    out = Path(args.out) if args.out else REPO_ROOT / "docs" / "resultados_backtest.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    winners = sum(r.significant_bonferroni for r in rows)
    print(f"{len(rows)} combinaciones, α corregido {alpha_b:.5f}, {winners} superan al azar → {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    from app.games import GAMES

    p = argparse.ArgumentParser(prog="lotolab", description="Ingesta de datos de LotoLab")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="aplica migraciones y registra los juegos").set_defaults(func=cmd_init)

    s = sub.add_parser("scrape", help="descarga resultados de baloto.com a data/raw/*.csv")
    s.add_argument("--game", action="append", choices=list(GAMES))
    s.add_argument("--since", help="fecha ISO; por defecto, hace 400 días")
    s.add_argument("--max-pages", type=int)
    s.set_defaults(func=cmd_scrape)

    i = sub.add_parser("import", help="carga data/raw/*.csv en la BD")
    i.add_argument("--game", action="append", choices=list(GAMES))
    i.set_defaults(func=cmd_import)

    v = sub.add_parser("validate", help="revisa huecos, duplicados, rangos y cobertura")
    v.add_argument("--game", action="append", choices=list(GAMES))
    v.add_argument("--min-months", type=float, default=12.0)
    v.set_defaults(func=cmd_validate)

    from app.backtest.engine import PRIMARY_WINDOW
    from app.backtest.strategies import STRATEGIES

    b = sub.add_parser("backtest", help="una corrida de backtest frente al azar")
    b.add_argument("--game", required=True, choices=list(GAMES))
    b.add_argument("--strategy", required=True, choices=list(STRATEGIES))
    b.add_argument("--window", type=int, default=PRIMARY_WINDOW)
    b.add_argument("--seed", type=int, default=0)
    b.set_defaults(func=cmd_backtest)

    ba = sub.add_parser("backtest-all", help="todas las combinaciones con Bonferroni → docs/resultados_backtest.md")
    ba.add_argument("--game", action="append", choices=list(GAMES))
    ba.add_argument("--strategy", action="append", choices=list(STRATEGIES))
    ba.add_argument("--seed", type=int, default=0)
    ba.add_argument("--out")
    ba.set_defaults(func=cmd_backtest_all)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
