"""Las fixtures son páginas reales de baloto.com descargadas el 2026-11-04."""

from datetime import date

import httpx
import pytest

from app.games import get_game
from app.ingest.scraper import (
    ParseError,
    Scraper,
    parse_baloto_page,
    parse_colorloto_page,
    parse_miloto_page,
    parse_spanish_date,
)

from tests.conftest import FIXTURES


def html(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_spanish_dates():
    assert parse_spanish_date("2 de Noviembre de 2026") == date(2026, 11, 2)
    assert parse_spanish_date(" 31 de octubre de 2026 ") == date(2026, 10, 31)
    with pytest.raises(ParseError):
        parse_spanish_date("31/10/2026")


def test_baloto_and_revancha():
    page = parse_baloto_page(html("baloto_page1.html"))
    assert page.total_pages == 130
    assert len(page.records) == 10
    first = page.records[0]
    assert (first.game, first.draw_number, first.draw_date) == ("baloto", 2730, date(2026, 11, 2))
    assert first.numbers == (18, 19, 20, 31, 43) and first.extra == 14
    second = page.records[1]
    assert second.game == "revancha" and second.numbers == (18, 30, 37, 39, 40)
    assert {r.game for r in page.records} == {"baloto", "revancha"}


def test_miloto():
    page = parse_miloto_page(html("miloto_page1.html"))
    first = page.records[0]
    assert (first.draw_number, first.draw_date, first.numbers) == (635, date(2026, 11, 3), (8, 13, 20, 24, 25))
    assert len(page.records) == 10


def test_colorloto():
    page = parse_colorloto_page(html("colorloto_page1.html"))
    assert page.total_pages == 23
    first = page.records[0]
    assert first.draw_number == 232 and first.draw_date == date(2026, 11, 2)
    assert first.numbers == (5, 6, 7, 2, 3, 6)
    assert first.colors == ("amarillo", "amarillo", "amarillo", "azul", "rojo", "rojo")


@pytest.mark.parametrize(
    "parser, fixture",
    [
        (parse_baloto_page, "baloto_page1.html"),
        (parse_miloto_page, "miloto_page1.html"),
        (parse_colorloto_page, "colorloto_page1.html"),
    ],
)
def test_every_parsed_draw_is_valid(parser, fixture):
    for rec in parser(html(fixture)).records:
        assert get_game(rec.game).validate(rec.ticket) == [], rec


def test_scrape_stops_at_since(tmp_path):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.params.get("page"))
        return httpx.Response(200, text=html("miloto_page1.html"))

    client = httpx.Client(transport=httpx.MockTransport(handler))
    scraper = Scraper(tmp_path, delay_seconds=0, client=client)
    recs = scraper.scrape("miloto", since=date(2026, 10, 27))
    assert calls == ["1"]  # la página ya llega a fechas anteriores a since: no pide más
    assert min(r.draw_date for r in recs) >= date(2026, 10, 27)
    assert [r.draw_number for r in recs][:1] == [635]
