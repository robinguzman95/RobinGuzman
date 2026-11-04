"""Corrida de todas las combinaciones (juego × estrategia × ventana) con Bonferroni y
reporte en Markdown: el producto central del laboratorio."""

from dataclasses import dataclass
from datetime import date

from app.backtest.engine import ALPHA, PRIMARY_WINDOW, SENSITIVITY_WINDOWS, BacktestOutcome, run_backtest
from app.backtest.montecarlo import DEFAULT_SIMS
from app.backtest.strategies import STRATEGIES, get_strategy
from app.games import get_game
from app.ingest.records import DrawRecord


@dataclass(frozen=True)
class Row:
    outcome: BacktestOutcome
    primary: bool
    significant_bonferroni: bool


def run_all(
    records_by_game: dict[str, list[DrawRecord]],
    strategies: list[str] | None = None,
    windows: tuple[int, ...] = (PRIMARY_WINDOW, *SENSITIVITY_WINDOWS),
    sims: int = DEFAULT_SIMS,
    seed: int = 0,
) -> tuple[list[Row], float, list[str]]:
    """Devuelve (filas, alpha corregido, avisos). Las combinaciones que no caben (ventana más
    larga que la historia) se omiten con un aviso y no cuentan para Bonferroni."""
    names = strategies or list(STRATEGIES)
    outcomes: list[BacktestOutcome] = []
    notes: list[str] = []
    for code, recs in records_by_game.items():
        game = get_game(code)
        for w in windows:
            if len(recs) <= w:
                notes.append(f"{game.name}: ventana {w} omitida ({len(recs)} sorteos)")
                continue
            for name in names:
                outcomes.append(run_backtest(recs, game, get_strategy(name), name, window=w, seed=seed, sims=sims))
    m = max(len(outcomes), 1)
    alpha_b = ALPHA / m
    rows = [Row(o, o.window == PRIMARY_WINDOW, o.p_value < alpha_b and o.above_p95) for o in outcomes]
    return rows, alpha_b, notes


def _fmt(x: float, d: int = 3) -> str:
    return f"{x:.{d}f}".replace(".", ",")


def render_markdown(rows: list[Row], alpha_b: float, notes: list[str], generated: date | None = None) -> str:
    generated = generated or date.today()
    winners = [r for r in rows if r.significant_bonferroni]
    lines = [
        "# Resultados del backtest",
        "",
        f"Generado el {generated.isoformat()} con `uv run lotolab backtest-all`.",
        "",
        "**Pregunta:** ¿alguna estrategia popular acierta más que una jugada al azar?",
        "",
        "**Método:** ventana móvil sin mirar al futuro (para el sorteo t solo se usan sorteos "
        "anteriores a t); línea base de 10.000 jugadas aleatorias (Monte Carlo hipergeométrico) "
        f"sobre los mismos sorteos; p-valor de una cola; ventana principal **{PRIMARY_WINDOW}** "
        f"sorteos, declarada antes de correr; {', '.join(map(str, SENSITIVITY_WINDOWS))} son de "
        f"sensibilidad. Corrección de Bonferroni sobre las {len(rows)} combinaciones: "
        f"α = 0,05 / {len(rows)} = {_fmt(alpha_b, 5)}.",
        "",
        "## Veredicto",
        "",
    ]
    if winners:
        lines.append(f"**{len(winners)} combinación(es) superan al azar tras la corrección.** Antes de creerlo, "
                     "revisar datos y repetir con otra semilla: con muchas pruebas, algún falso positivo es posible.")
    else:
        lines.append("**Ninguna estrategia le gana al azar.** Tras la corrección por comparaciones múltiples, "
                     "ninguna combinación acierta más de lo que produciría jugar al azar, como se espera si los "
                     "sorteos son independientes.")
    nominal = [r for r in rows if r.outcome.p_value < ALPHA and r.outcome.above_p95]
    lines += [
        "",
        f"Sin corregir (p < 0,05 y sobre p95) salen {len(nominal)} de {len(rows)} combinaciones; solo por azar "
        f"se esperan unas {_fmt(ALPHA * len(rows), 1)}. Por eso hace falta Bonferroni: al probar muchas "
        "estrategias a la vez, alguna \"gana\" por suerte."
        + ("" if not nominal else " Casos: " + "; ".join(
            f"{get_game(r.outcome.game).name} · {r.outcome.strategy} · ventana {r.outcome.window} "
            f"(p = {_fmt(r.outcome.p_value)})" for r in nominal) + "."),
    ]
    lines += ["", "## Ventana principal", ""]
    lines += _table([r for r in rows if r.primary])
    lines += ["", "## Sensibilidad (otras ventanas)", ""]
    lines += _table([r for r in rows if not r.primary])
    if notes:
        lines += ["", "## Avisos", ""] + [f"- {n}" for n in notes]
    lines += [
        "",
        "## Cómo leer la tabla",
        "",
        "- **Aciertos/sorteo:** promedio de números principales acertados por sorteo evaluado.",
        "- **Banda p5–p95:** el 90% central de los promedios de 10.000 jugadas aleatorias en el mismo periodo.",
        "- **p-valor:** proporción de jugadas aleatorias que igualan o superan a la estrategia.",
        "- La probabilidad real del premio mayor no cambia con ninguna estrategia.",
        "",
    ]
    return "\n".join(lines)


def _table(rows: list[Row]) -> list[str]:
    if not rows:
        return ["(sin combinaciones)"]
    out = [
        "| Juego | Estrategia | Ventana | Sorteos evaluados | Aciertos/sorteo | Banda azar p5–p95 | p-valor | Resultado | Prob. premio mayor |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        o = r.outcome
        game = get_game(o.game)
        if r.significant_bonferroni:
            res = "**le gana al azar**"
        elif o.above_p95 and o.p_value < ALPHA:
            res = "sobre p95, pero no significativo tras Bonferroni"
        else:
            res = "dentro de la banda"
        out.append(
            f"| {game.name} | {o.strategy} | {o.window} | {o.n_draws} ({o.date_from} → {o.date_to}) | "
            f"{_fmt(o.avg_hits)} | {_fmt(o.baseline.p5)}–{_fmt(o.baseline.p95)} | {_fmt(o.p_value)} | "
            f"{res} | {game.odds_text()} |"
        )
    return out
