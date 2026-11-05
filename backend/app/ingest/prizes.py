"""Tablas de premios de cada sorteo (páginas de detalle de baloto.com).

Cada página de detalle publica: el acumulado del sorteo y, por categoría de aciertos, el
premio total, el número de ganadores y el premio por ganador. Con eso se calcula el valor
esperado real de un tiquete y se estima cuántas jugadas se vendieron (ver analysis/expected.py).

Categorías normalizadas:
- Baloto / Revancha: "5+SB", "5", "4+SB", "4", "3+SB", "3", "2+SB", "1+SB", "0+SB"
- MiLoto: "5", "4", "3", "2"
- ColorLoto: "6", "5", "4", "3" (número y color), "6N" (6 números sin importar color),
  "6C" (6 colores sin importar número)

Las páginas de detalle no cambian una vez publicadas: se guardan en caché sin vencimiento.
"""

import csv
import re
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from app.ingest.scraper import BASE_URL

DETAIL_PATHS = {
    "baloto": "/resultados-baloto/{n}",
    "revancha": "/resultados-revancha/{n}",
    "miloto": "/miloto/resultados-miloto/{n}/",
    "colorloto": "/colorloto/resultados/{n}",
}

CSV_COLUMNS = ["draw_number", "jackpot_cop", "category", "winners", "prize_per_winner", "total_prize"]


@dataclass(frozen=True)
class PrizeRow:
    game: str
    draw_number: int
    jackpot_cop: int | None  # "ACUMULADO DEL SORTEO" (premio mayor en juego en ese sorteo)
    category: str
    winners: int
    prize_per_winner: int
    total_prize: int


class NotADetailPage(ValueError):
    """baloto.com redirige al listado cuando no tiene el detalle de un sorteo."""


def _money(s: str) -> int:
    return int(s.replace(".", "").replace(",", ""))


def _text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "nav", "footer", "header"]):
        t.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" "))


def _jackpot(text: str) -> int | None:
    m = re.search(r"ACUMULADO DEL SORTEO:\s*\$\s*([\d.]+)\s*MILLONES", text, re.I)
    return _money(m.group(1)) * 1_000_000 if m else None


def _draw_number(text: str) -> int | None:
    m = re.search(r"SORTEO\s*#?\s*([\d.]+)", text, re.I)
    return _money(m.group(1)) if m else None


def parse_detail(html: str, game: str, expected_number: int) -> list[PrizeRow]:
    text = _text(html)
    number = _draw_number(text)
    if number != expected_number:
        raise NotADetailPage(f"{game} {expected_number}: la página corresponde al sorteo {number}")
    jackpot = _jackpot(text)
    rows: list[tuple[str, int, int, int]] = []  # (categoría, total, ganadores, por ganador)

    if game in ("baloto", "revancha"):
        for m in re.finditer(r"(\d) ?(\+ ?SB)? \$([\d.]+) ([\d.]+) \$([\d.]+)", text):
            cat = m.group(1) + ("+SB" if m.group(2) else "")
            rows.append((cat, _money(m.group(3)), _money(m.group(4)), _money(m.group(5))))
    elif game == "miloto":
        pat = r"Aciertos (\d) Premio total \$([\d.]+) Premio por ganador \$([\d.]+) Ganadores ([\d.]+)"
        for m in re.finditer(pat, text, re.I):
            rows.append((m.group(1), _money(m.group(2)), _money(m.group(4)), _money(m.group(3))))
    elif game == "colorloto":
        pat = r"ACIERTOS (6 N\S*MEROS|6 COLORES|\d) \$([\d.]+) ([\d.]+) \$([\d.]+)"
        for m in re.finditer(pat, text, re.I):
            raw = m.group(1).upper()
            cat = "6N" if "N" in raw else "6C" if "COLOR" in raw else raw
            rows.append((cat, _money(m.group(2)), _money(m.group(3)), _money(m.group(4))))
    else:
        raise ValueError(f"juego desconocido {game!r}")

    if not rows:
        raise NotADetailPage(f"{game} {expected_number}: no encontré la tabla de premios")
    seen = set()
    out = []
    for cat, total, winners, per in rows:
        if cat in seen:  # la tabla aparece una sola vez; ignora repeticiones del texto
            continue
        seen.add(cat)
        out.append(PrizeRow(game, expected_number, jackpot, cat, winners, per, total))
    return out


class PrizeScraper:
    def __init__(self, cache_dir: Path, delay_seconds: float = 2.0, user_agent: str = "LotoLab/0.1",
                 client: httpx.Client | None = None) -> None:
        self.cache_dir = cache_dir
        self.delay = delay_seconds
        self.client = client or httpx.Client(headers={"User-Agent": user_agent}, timeout=30, follow_redirects=True)
        self._last = 0.0

    def fetch(self, game: str, number: int) -> str:
        cache = self.cache_dir / "detail" / game / f"{number}.html"
        if cache.exists():
            return cache.read_text(encoding="utf-8")
        wait = self.delay - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        resp = self.client.get(BASE_URL + DETAIL_PATHS[game].format(n=number))
        self._last = time.monotonic()
        resp.raise_for_status()
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(resp.text, encoding="utf-8")
        return resp.text

    def scrape(self, game: str, numbers: list[int]) -> tuple[list[PrizeRow], list[str]]:
        rows, missing = [], []
        for n in numbers:
            try:
                rows += parse_detail(self.fetch(game, n), game, n)
            except NotADetailPage as exc:
                missing.append(str(exc))
        return rows, missing


def read_prizes_csv(path: Path, game: str) -> list[PrizeRow]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return [
            PrizeRow(game, int(r["draw_number"]), int(r["jackpot_cop"]) if r["jackpot_cop"] else None,
                     r["category"], int(r["winners"]), int(r["prize_per_winner"]), int(r["total_prize"]))
            for r in csv.DictReader(fh)
        ]


def write_prizes_csv(path: Path, game: str, rows: list[PrizeRow]) -> int:
    """Fusiona por (sorteo, categoría) y reescribe ordenado. Devuelve filas nuevas."""
    merged = {(r.draw_number, r.category): r for r in read_prizes_csv(path, game)}
    before = len(merged)
    for r in rows:
        merged[(r.draw_number, r.category)] = r
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(CSV_COLUMNS)
        for r in sorted(merged.values(), key=lambda r: (r.draw_number, r.category)):
            w.writerow([r.draw_number, r.jackpot_cop or "", r.category, r.winners, r.prize_per_winner, r.total_prize])
    return len(merged) - before
