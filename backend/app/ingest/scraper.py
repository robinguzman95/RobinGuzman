"""Descarga de resultados desde las páginas públicas de baloto.com.

Revisión de la fuente (2026-11-04):
- robots.txt solo prohíbe /api/ y /admin-baloto/; el histórico está en páginas HTML públicas
  renderizadas en el servidor y paginadas con ``?page=N`` (10 filas por página).
- Términos y condiciones (sección 13): los contenidos y bases de datos son del Operador
  Nacional de Juegos S.A.S.; se considera uso indebido su uso con fines comerciales sin
  autorización. Uso aquí: académico/portafolio, no comercial.

Buenas prácticas aplicadas: pausa entre peticiones, User-Agent identificable, caché local
del HTML (no se vuelve a pedir una página ya descargada salvo la primera, que cambia) y parada
temprana al alcanzar la fecha pedida. El resultado se escribe a data/raw/*.csv; la BD se carga
después con el importador, que es la única vía de entrada.
"""

import re
import time
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from app.ingest.records import DrawRecord

BASE_URL = "https://baloto.com"

# Página de histórico por "familia": Baloto y Revancha comparten página.
SOURCES = {
    "baloto": "/resultados",
    "miloto": "/miloto/resultados",
    "colorloto": "/colorloto/resultados",
}
FAMILY = {"baloto": "baloto", "revancha": "baloto", "miloto": "miloto", "colorloto": "colorloto"}

MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
    "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}
# Clases CSS de ColorLoto -> color oficial.
CSS_COLORS = {
    "balota-yellow": "amarillo", "balota-blue": "azul", "balota-red": "rojo",
    "balota-green": "verde", "balota-white": "blanco", "balota-black": "negro",
}


class ParseError(ValueError):
    pass


def parse_spanish_date(text: str) -> date:
    """'2 de Noviembre de 2026' -> date(2026, 11, 2)."""
    m = re.search(r"(\d{1,2})\s+de\s+([A-Za-zÁÉÍÓÚáéíóú]+)\s+de\s+(\d{4})", text)
    if not m:
        raise ParseError(f"fecha no reconocida: {text!r}")
    month_name = unicodedata.normalize("NFKD", m.group(2).lower()).encode("ascii", "ignore").decode()
    if month_name not in MONTHS:
        raise ParseError(f"mes no reconocido: {m.group(2)!r}")
    return date(int(m.group(3)), MONTHS[month_name], int(m.group(1)))


@dataclass
class Page:
    records: list[DrawRecord]
    total_pages: int


def _total_pages(soup: BeautifulSoup) -> int:
    m = re.search(r"P\S*gina\s+\d+\s+de\s+(\d+)", soup.get_text(" "))
    return int(m.group(1)) if m else 1


def _history_rows(soup: BeautifulSoup) -> list:
    """Filas del histórico: las que tienen enlace 'Ver detalle'."""
    return [a.find_parent("tr") for a in soup.find_all("a", string=re.compile("Ver detalle"))]


def _number_from_href(href: str, pattern: str) -> int:
    m = re.search(pattern, href)
    if not m:
        raise ParseError(f"no encontré el número de sorteo en {href!r}")
    return int(m.group(1))


def parse_baloto_page(html: str) -> Page:
    """Histórico de Baloto + Revancha (una fila por sorteo, con ícono del tipo)."""
    soup = BeautifulSoup(html, "html.parser")
    records = []
    for tr in _history_rows(soup):
        link = tr.find("a", string=re.compile("Ver detalle"))["href"]
        kind_match = re.search(r"/resultados-(baloto|revancha)/", link)
        if not kind_match:
            raise ParseError(f"tipo de sorteo desconocido en {link!r}")
        game = kind_match.group(1)
        number = _number_from_href(link, r"/resultados-(?:baloto|revancha)/(\d+)")
        cells = tr.find_all("td")
        draw_date = parse_spanish_date(cells[1].get_text(" ", strip=True))
        extra_span = cells[2].find("span")
        if extra_span is None:
            raise ParseError(f"sorteo {game} {number}: falta la superbalota")
        extra = int(extra_span.get_text(strip=True))
        extra_span.extract()
        numbers = tuple(int(x) for x in re.findall(r"\d+", cells[2].get_text(" ")))
        records.append(
            DrawRecord(game, number, draw_date, numbers, None, extra, None, BASE_URL + link)
        )
    return Page(records, _total_pages(soup))


def parse_miloto_page(html: str) -> Page:
    soup = BeautifulSoup(html, "html.parser")
    records = []
    for tr in _history_rows(soup):
        link = tr.find("a", string=re.compile("Ver detalle"))["href"]
        number = _number_from_href(link, r"/resultados-miloto/(\d+)")
        cells = tr.find_all("td")
        draw_date = parse_spanish_date(cells[0].get_text(" ", strip=True))
        numbers = tuple(int(s.get_text(strip=True)) for s in cells[1].find_all("span"))
        records.append(DrawRecord("miloto", number, draw_date, numbers, None, None, None, BASE_URL + link))
    return Page(records, _total_pages(soup))


def parse_colorloto_page(html: str) -> Page:
    soup = BeautifulSoup(html, "html.parser")
    records = []
    for tr in _history_rows(soup):
        link = tr.find("a", string=re.compile("Ver detalle"))["href"]
        number = _number_from_href(link, r"/colorloto/resultados/(\d+)")
        cells = tr.find_all("td")
        draw_date = parse_spanish_date(cells[0].get_text(" ", strip=True))
        nums, cols = [], []
        for ball in cells[1].select("div.balota-bg"):
            css = next((c for c in ball.get("class", []) if c in CSS_COLORS), None)
            if css is None:
                raise ParseError(f"ColorLoto {number}: color no reconocido {ball.get('class')}")
            nums.append(int(ball.get_text(strip=True)))
            cols.append(CSS_COLORS[css])
        records.append(
            DrawRecord("colorloto", number, draw_date, tuple(nums), tuple(cols), None, None, BASE_URL + link)
        )
    return Page(records, _total_pages(soup))


PARSERS = {"baloto": parse_baloto_page, "miloto": parse_miloto_page, "colorloto": parse_colorloto_page}


class Scraper:
    def __init__(
        self,
        cache_dir: Path,
        delay_seconds: float = 2.0,
        user_agent: str = "LotoLab/0.1",
        client: httpx.Client | None = None,
    ) -> None:
        self.cache_dir = cache_dir
        self.delay = delay_seconds
        self.client = client or httpx.Client(
            headers={"User-Agent": user_agent}, timeout=30, follow_redirects=True
        )
        self._last_request = 0.0

    def fetch(self, family: str, page: int) -> str:
        cache = self.cache_dir / family / f"page-{page:04d}.html"
        # La página 1 cambia tras cada sorteo; las demás también se desplazan, así que la
        # caché solo se usa dentro de un mismo día.
        if cache.exists() and date.fromtimestamp(cache.stat().st_mtime) == date.today():
            return cache.read_text(encoding="utf-8")
        wait = self.delay - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        resp = self.client.get(BASE_URL + SOURCES[family], params={"page": page})
        self._last_request = time.monotonic()
        resp.raise_for_status()
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(resp.text, encoding="utf-8")
        return resp.text

    def scrape(self, family: str, since: date, max_pages: int | None = None) -> list[DrawRecord]:
        """Recorre el histórico desde la página 1 hasta pasar la fecha ``since``."""
        parser = PARSERS[family]
        out: list[DrawRecord] = []
        page, total = 1, 1
        while page <= total and (max_pages is None or page <= max_pages):
            parsed = parser(self.fetch(family, page))
            total = parsed.total_pages
            if not parsed.records:
                break
            out += [r for r in parsed.records if r.draw_date >= since]
            if min(r.draw_date for r in parsed.records) < since:
                break
            page += 1
        return out
