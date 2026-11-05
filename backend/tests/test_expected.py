from math import comb, exp

import httpx
import pytest

from app.analysis.expected import (
    JACKPOT_CATEGORY,
    TAX_THRESHOLD,
    PRICES,
    category_probabilities,
    estimate_sales,
    expected_value,
    net_prize,
    popularity_effect,
)
from app.ingest.prizes import NotADetailPage, PrizeRow, PrizeScraper, parse_detail, read_prizes_csv, write_prizes_csv

from tests.conftest import FIXTURES


def detail(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8", errors="replace")


# --- parser de tablas de premios (páginas reales) ------------------------------------
def test_parse_baloto_detail():
    rows = parse_detail(detail("detail_baloto_2730.html"), "baloto", 2730)
    by = {r.category: r for r in rows}
    assert rows[0].jackpot_cop == 18_400_000_000
    assert (by["0+SB"].winners, by["0+SB"].prize_per_winner) == (6138, 6000)
    assert (by["4"].winners, by["4"].prize_per_winner, by["4"].total_prize) == (30, 103_100, 3_093_000)
    assert by["5+SB"].winners == 0
    assert set(by) == {"5+SB", "5", "4+SB", "4", "3+SB", "3", "2+SB", "0+SB"}


def test_parse_other_games():
    m = {r.category: r for r in parse_detail(detail("detail_miloto_635.html"), "miloto", 635)}
    assert (m["2"].winners, m["2"].prize_per_winner) == (12_924, 4_000)
    assert m["4"].prize_per_winner == 987_100
    c = {r.category: r for r in parse_detail(detail("detail_colorloto_232.html"), "colorloto", 232)}
    assert (c["6C"].winners, c["6C"].prize_per_winner) == (10, 214_350)
    assert (c["6N"].winners, c["3"].winners) == (47, 397)
    r = {r.category: r for r in parse_detail(detail("detail_revancha_2730.html"), "revancha", 2730)}
    assert r["0+SB"].prize_per_winner == 3_000 and r["0+SB"].winners == 5829


def test_redirect_to_listing_is_detected():
    with pytest.raises(NotADetailPage):
        parse_detail(detail("detail_baloto_2730.html"), "baloto", 2685)


def test_prize_scraper_caches_and_reports_missing(tmp_path):
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req.url.path)
        return httpx.Response(200, text=detail("detail_miloto_635.html"))

    s = PrizeScraper(tmp_path, delay_seconds=0, client=httpx.Client(transport=httpx.MockTransport(handler)))
    rows, missing = s.scrape("miloto", [635, 634])
    assert {r.draw_number for r in rows} == {635} and len(missing) == 1  # 634 devuelve otra página
    s.scrape("miloto", [635])
    assert calls.count("/miloto/resultados-miloto/635/") == 1  # segunda vez desde caché


def test_prizes_csv_roundtrip(tmp_path):
    rows = parse_detail(detail("detail_baloto_2730.html"), "baloto", 2730)
    path = tmp_path / "baloto_premios.csv"
    assert write_prizes_csv(path, "baloto", rows) == len(rows)
    assert write_prizes_csv(path, "baloto", rows) == 0
    assert sorted(read_prizes_csv(path, "baloto"), key=lambda r: r.category) == sorted(rows, key=lambda r: r.category)


# --- probabilidades -----------------------------------------------------------------
def test_baloto_probabilities_add_up():
    p = category_probabilities("baloto")
    assert p["5+SB"] == pytest.approx(1 / 15_401_568)
    assert p["3"] == pytest.approx(comb(5, 3) * comb(38, 2) / comb(43, 5) * 15 / 16)
    assert p["0+SB"] == pytest.approx((comb(38, 5) + 5 * comb(38, 4)) / comb(43, 5) / 16)
    # Las categorías con superbalota cubren todas las jugadas que la aciertan: suman 1/16.
    with_sb = sum(v for k, v in p.items() if k.endswith("+SB"))
    assert with_sb == pytest.approx(1 / 16)


def test_miloto_and_colorloto_probabilities():
    m = category_probabilities("miloto")
    assert m["5"] == pytest.approx(1 / 575_757)
    assert sum(m.values()) < 1
    c = category_probabilities("colorloto")
    assert c["6"] == pytest.approx(1 / 5_245_786)
    # 6 números sin importar color: más probable que el premio mayor, mucho menos que 3 aciertos.
    assert c["6"] < c["6N"] < c["3"] and c["6"] < c["6C"] < c["3"]


def test_net_prize_applies_tax_above_threshold():
    assert net_prize(100_000) == 100_000
    assert net_prize(TAX_THRESHOLD + 1) == pytest.approx((TAX_THRESHOLD + 1) * 0.8)


# --- ventas y valor esperado con datos sintéticos -------------------------------------
def synthetic_rows(code: str, plays: list[int], jackpots: list[int], prize: dict[str, int]) -> list[PrizeRow]:
    """Ganadores = ventas × probabilidad (valor esperado exacto, sin ruido)."""
    p = category_probabilities(code)
    rows = []
    for i, (n, j) in enumerate(zip(plays, jackpots), start=1):
        for cat, pc in p.items():
            # Al menos 1 ganador en categorías no mayores, para que haya premio observado.
            w = max(1, round(n * pc)) if cat != JACKPOT_CATEGORY[code] else 0
            rows.append(PrizeRow(code, i, j, cat, w, prize.get(cat, 0) if w else 0, w * prize.get(cat, 0)))
    return rows


def test_sales_estimate_recovers_known_sales():
    rows = synthetic_rows("baloto", [100_000, 200_000, 400_000], [5e9, 10e9, 20e9], {"0+SB": 6000})
    est = [s.plays for s in estimate_sales(rows, "baloto")]
    assert est == pytest.approx([100_000, 200_000, 400_000], rel=0.01)
    lo_hi = estimate_sales(rows, "baloto")[0]
    assert lo_hi.plays_low < lo_hi.plays < lo_hi.plays_high


def test_expected_value_formula():
    prizes = {"0+SB": 6000, "2+SB": 10_000, "3": 9_000, "3+SB": 40_000, "4": 100_000, "4+SB": 1_400_000,
              "5": 100_000_000}
    plays = [100_000 + 10_000 * i for i in range(10)]
    jackpots = [int(4e9 + 1e9 * i) for i in range(10)]
    rows = synthetic_rows("baloto", plays, jackpots, prizes)
    res = expected_value(rows, "baloto")
    p = category_probabilities("baloto")
    manual = sum(p[c] * net_prize(v) for c, v in prizes.items())
    assert res.non_jackpot_ev == pytest.approx(manual, rel=1e-3)
    # Ventas: recta exacta N = 60.000 + 10 por millón de acumulado.
    assert res.sales.b == pytest.approx(10, rel=1e-3) and res.sales.a == pytest.approx(60_000, rel=1e-3)
    # VE con acumulado J: fórmula Poisson.
    j = 20e9
    lam = res.sales.plays(j) * p["5+SB"]
    assert res.ev(j) == pytest.approx(manual + p["5+SB"] * j * 0.8 * (1 - exp(-lam)) / lam, rel=1e-6)
    # Menos popular -> menos gente con quien repartir -> VE mayor.
    assert res.ev(j, popularity=0.5) > res.ev(j) > res.ev(j, popularity=2)
    assert res.price == PRICES["baloto"]
    assert res.curve and all(c["return"] == pytest.approx(c["ev"] / 6000) for c in res.curve)


def test_popularity_effect_detects_planted_bias():
    """Sorteos sintéticos donde, si salen muchos números ≤ 31, hay 30 % más ganadores de 3–4."""
    import random

    rng = random.Random(4)
    p = category_probabilities("baloto")
    rows, draws = [], {}
    for n in range(1, 151):
        nums = tuple(sorted(rng.sample(range(1, 44), 5)))
        draws[n] = nums
        low = sum(x <= 31 for x in nums)
        boost = 1 + 0.1 * max(low - 2, 0)
        plays = 150_000
        for cat, pc in p.items():
            w = plays * pc * (boost if cat in ("4", "3+SB", "3") else 1)
            rows.append(PrizeRow("baloto", n, int(5e9), cat, int(round(w)), 1, 1))
    eff = popularity_effect(rows, draws, "baloto")
    assert eff.spearman_rho > 0.5 and eff.p_value < 0.001
    assert eff.groups[-1].ratio > eff.groups[0].ratio
    assert popularity_effect(rows, draws, "miloto") is None
