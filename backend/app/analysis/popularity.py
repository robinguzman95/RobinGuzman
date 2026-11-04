"""Puntaje de popularidad de una jugada (0 = rara, 100 = la juega mucha gente).

Lo que sí se puede optimizar: la probabilidad de ganar es la misma para todas las jugadas, pero
si gana una jugada popular el premio se reparte entre más personas. Este puntaje estima cuán
probable es que otros hayan elegido lo mismo.

AVISO DE MÉTODO: los pesos son heurísticos. Se apoyan en patrones documentados del
comportamiento de apostadores en loterías de otros países (preferencia por fechas de
cumpleaños, secuencias, patrones en el tiquete, repetir ganadores anteriores), no en datos de
ventas de Baloto, que no son públicos. Sirven para ordenar jugadas, no como probabilidad.

La cuadrícula del tiquete (TICKET_COLUMNS) es una APROXIMACIÓN pendiente de confirmar con un
tiquete físico; solo afecta al componente "patrón visual".
"""

from collections import Counter
from dataclasses import dataclass, field

from app.games import Game, Ticket

# Columnas de la cuadrícula del tiquete por juego (aproximado, ver aviso).
TICKET_COLUMNS = {"baloto": 7, "revancha": 7, "miloto": 7}


@dataclass(frozen=True)
class PopularityScore:
    score: int
    level: str  # baja / media / alta
    reasons: list[str] = field(default_factory=list)


def _longest_consecutive(nums: list[int]) -> int:
    s = sorted(set(nums))
    best = cur = 1
    for a, b in zip(s, s[1:]):
        cur = cur + 1 if b == a + 1 else 1
        best = max(best, cur)
    return best


def _is_arithmetic(nums: list[int]) -> bool:
    s = sorted(nums)
    diffs = {b - a for a, b in zip(s, s[1:])}
    return len(diffs) == 1 and len(s) >= 3


def _grid_lines(nums: list[int], cols: int) -> list[str]:
    """Patrones visuales en una cuadrícula de ``cols`` columnas numerada por filas desde 1."""
    pos = [((n - 1) // cols, (n - 1) % cols) for n in nums]
    rows = {r for r, _ in pos}
    columns = {c for _, c in pos}
    out = []
    if len(rows) == 1:
        out.append("todos en una misma fila del tiquete")
    if len(columns) == 1:
        out.append("todos en una misma columna del tiquete")
    if len({r - c for r, c in pos}) == 1 or len({r + c for r, c in pos}) == 1:
        out.append("todos en una diagonal del tiquete")
    return out


def popularity(
    ticket: Ticket, game: type[Game], past_results: set[frozenset] | None = None
) -> PopularityScore:
    """``past_results``: resultados anteriores como frozenset de balotas (para detectar jugadas
    que repiten un ganador)."""
    nums = list(ticket.numbers)
    k = len(nums)
    points = 0
    reasons: list[str] = []

    def add(p: int, why: str) -> None:
        nonlocal points
        points += p
        reasons.append(f"+{p} {why}")

    # 1) Fechas: números ≤ 31 (días) y ≤ 12 (meses). Solo aporta si el bombo pasa de 31.
    if game.main_max > 31:
        le31 = sum(n <= 31 for n in nums)
        if le31 == k:
            add(25, "todos los números son ≤ 31 (parecen fechas)")
        elif le31 >= k - 1:
            add(10, f"{le31} de {k} números son ≤ 31 (fechas)")
    if game.main_max > 12 and sum(n <= 12 for n in nums) >= k - 1:
        add(10, "casi todos son ≤ 12 (meses)")

    # 2) Secuencias.
    run = _longest_consecutive(nums)
    if run >= 3:
        add(min(8 * (run - 1), 30), f"{run} números consecutivos")
    if _is_arithmetic(nums) and run < len(set(nums)):
        add(15, "progresión aritmética")

    # 3) Múltiplos de un mismo número (5, 10, 15...).
    for d in range(10, 1, -1):
        if all(n % d == 0 for n in nums):
            add(10, f"todos son múltiplos de {d}")
            break

    # 4) Misma terminación.
    endings = Counter(n % 10 for n in nums).most_common(1)[0][1]
    if endings >= 3:
        add(5 * (endings - 2), f"{endings} números con la misma terminación")

    # 5) Patrones en el tiquete (aproximado).
    cols = TICKET_COLUMNS.get(game.code)
    if cols and not game.colors:
        for why in _grid_lines(nums, cols):
            add(15, why + " (cuadrícula aproximada)")

    # 6) ColorLoto: patrones de color.
    if game.colors and ticket.colors:
        if len(set(ticket.colors)) == 1:
            add(20, "todas las balotas del mismo color")
        if len(set(nums)) == 1:
            add(15, "el mismo número en todos los colores")

    # 7) Repite un resultado anterior.
    if past_results and frozenset(ticket.balls()) in past_results:
        add(20, "repite una combinación que ya salió")

    score = min(points, 100)
    level = "baja" if score < 20 else "media" if score < 50 else "alta"
    return PopularityScore(score, level, reasons)
