"""Valor esperado de un tiquete y estimación de ventas a partir de las tablas de premios.

Modelo
------
VE(J) = Σ_c P(c) · premio_neto_c  +  P(mayor) · J_neto · E[1 / (1 + K)]

- P(c): probabilidad exacta de cada categoría (combinatoria; ColorLoto "6N"/"6C" por Monte
  Carlo, porque dependen de la composición del tiquete).
- premio_neto_c: premio promedio por ganador en los sorteos del periodo (los premios son
  parimutuales: varían con las ventas y el número de ganadores), menos la retención.
- K: cuántas otras personas también aciertan el premio mayor. Si se venden N jugadas al azar,
  K ~ Poisson(λ), λ = N · P(mayor), y E[1/(1+K)] = (1 − e^{−λ}) / λ.
- N depende del acumulado (la gente compra más cuando el premio es grande): se ajusta una
  recta N(J) con los sorteos del periodo.

Ventas estimadas por sorteo: N̂ = ganadores_c / P(c) usando una categoría "contador". En
Baloto y Revancha la categoría "0+SB" (0 o 1 aciertos + superbalota) cubre casi todos los
tiquetes sin importar qué números salieron, así que es casi inmune a la popularidad de los
números ganadores. En MiLoto y ColorLoto se usa el estimador agrupado Σ ganadores / Σ P(c).

Impuestos (Colombia, 2026): retención del 20 % sobre premios de loterías superiores a 48 UVT
(UVT 2026 = $52.374 → umbral $2.513.952). Hay un proyecto de ley para subirla al 30 % (no
vigente). El modelo aplica el 20 % al premio por ganador cuando supera el umbral.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from functools import lru_cache
from math import comb, exp

import numpy as np

from app.games import Game, get_game
from app.ingest.prizes import PrizeRow

UVT_2026 = 52_374
TAX_THRESHOLD = 48 * UVT_2026
TAX_RATE = 0.20

# Precio por jugada, IVA incluido (baloto.com, nov-2026). Revancha es un adicional a Baloto.
PRICES = {"baloto": 6_000, "revancha": 3_000, "miloto": 4_000, "colorloto": 5_000}
JACKPOT_CATEGORY = {"baloto": "5+SB", "revancha": "5+SB", "miloto": "5", "colorloto": "6"}
COUNTER_CATEGORY = {"baloto": "0+SB", "revancha": "0+SB"}  # para estimar ventas


def _hyper(n: int, k: int, hits: int) -> float:
    """P(exactamente `hits` aciertos) eligiendo k de n con k ganadoras."""
    return comb(k, hits) * comb(n - k, k - hits) / comb(n, k)


@lru_cache
def _colorloto_special(sims: int = 2_000_000, seed: int = 2026) -> tuple[float, float]:
    """P("6N") y P("6C") por Monte Carlo: tiquete y sorteo = 6 balotas distintas de 42.
    Balota b ∈ 0..41 -> número b % 7, color b // 7. Se compara el multiconjunto de números
    (o de colores) sin importar el orden."""
    rng = np.random.default_rng(seed)
    out_n = out_c = 0
    chunk = 200_000
    for _ in range(sims // chunk):
        t = np.argsort(rng.random((chunk, 42)), axis=1)[:, :6]
        d = np.argsort(rng.random((chunk, 42)), axis=1)[:, :6]
        tn, dn = np.sort(t % 7, axis=1), np.sort(d % 7, axis=1)
        tc, dc = np.sort(t // 7, axis=1), np.sort(d // 7, axis=1)
        out_n += int(np.all(tn == dn, axis=1).sum())
        out_c += int(np.all(tc == dc, axis=1).sum())
    return out_n / sims, out_c / sims


@lru_cache
def category_probabilities(code: str) -> dict[str, float]:
    """Probabilidad de que UNA jugada caiga en cada categoría de premio."""
    game = get_game(code)
    if code in ("baloto", "revancha"):
        n, k, sb = game.main_max, game.main_count, 1 / game.extra_max
        p = {h: _hyper(n, k, h) for h in range(k + 1)}
        out = {}
        for h in (5, 4, 3):
            out[f"{h}+SB"] = p[h] * sb
            out[f"{h}"] = p[h] * (1 - sb)
        out["2+SB"] = p[2] * sb
        out["0+SB"] = (p[0] + p[1]) * sb  # la tabla agrupa 0 y 1 aciertos con superbalota
        return out
    if code == "miloto":
        return {str(h): _hyper(game.main_max, game.main_count, h) for h in (5, 4, 3, 2)}
    if code == "colorloto":
        out = {str(h): _hyper(42, 6, h) for h in (6, 5, 4, 3)}
        out["6N"], out["6C"] = _colorloto_special()
        return out
    raise ValueError(code)


def net_prize(gross: float) -> float:
    return gross * (1 - TAX_RATE) if gross > TAX_THRESHOLD else gross


# --- ventas -------------------------------------------------------------------------
@dataclass(frozen=True)
class DrawSales:
    draw_number: int
    jackpot: int | None
    plays: float  # jugadas estimadas
    plays_low: float  # IC 95 % (Poisson sobre los ganadores del contador)
    plays_high: float


def estimate_sales(rows: list[PrizeRow], code: str) -> list[DrawSales]:
    probs = category_probabilities(code)
    jackpot_cat = JACKPOT_CATEGORY[code]
    by_draw: dict[int, list[PrizeRow]] = defaultdict(list)
    for r in rows:
        by_draw[r.draw_number].append(r)
    out = []
    for n, rs in sorted(by_draw.items()):
        counter = COUNTER_CATEGORY.get(code)
        cats = [r for r in rs if (r.category == counter if counter else r.category != jackpot_cat)]
        w = sum(r.winners for r in cats)
        p = sum(probs[r.category] for r in cats if r.category in probs)
        if w == 0 or p == 0:
            continue
        se = w ** 0.5
        out.append(DrawSales(n, rs[0].jackpot_cop, w / p, max(w - 1.96 * se, 0) / p, (w + 1.96 * se) / p))
    return out


@dataclass(frozen=True)
class SalesModel:
    """N(J) = a + b · J  (J en millones de pesos)."""

    a: float
    b: float
    r2: float
    n: int

    def plays(self, jackpot: float) -> float:
        return max(self.a + self.b * jackpot / 1e6, 1.0)


def fit_sales_model(sales: list[DrawSales]) -> SalesModel:
    pts = [(s.jackpot / 1e6, s.plays) for s in sales if s.jackpot]
    x = np.array([p[0] for p in pts])
    y = np.array([p[1] for p in pts])
    if len(pts) < 3 or np.ptp(x) == 0:
        return SalesModel(float(y.mean()) if len(y) else 0.0, 0.0, 0.0, len(pts))
    b, a = np.polyfit(x, y, 1)
    pred = a + b * x
    r2 = 1 - float(((y - pred) ** 2).sum()) / float(((y - y.mean()) ** 2).sum())
    return SalesModel(float(a), float(b), r2, len(pts))


# --- ¿la gente juega números populares? ---------------------------------------------
@dataclass(frozen=True)
class PopularityGroup:
    low_numbers: int  # cuántos de los números ganadores eran ≤ 31 ("fechas")
    draws: int
    ratio: float  # ganadores reales / esperados si todos jugaran al azar (promedio)


@dataclass(frozen=True)
class PopularityEffect:
    categories: list[str]
    groups: list[PopularityGroup]
    spearman_rho: float | None
    p_value: float | None
    n_draws: int


def popularity_effect(rows: list[PrizeRow], draws: dict[int, tuple[int, ...]], code: str) -> PopularityEffect | None:
    """Solo Baloto/Revancha (tienen un contador casi inmune a la popularidad). Para cada sorteo:
    ratio = ganadores de 3–4 aciertos / (ventas estimadas × P). Si la gente elige fechas, cuando
    salen muchos números ≤ 31 hay más ganadores de los esperados (ratio > 1)."""
    if code not in COUNTER_CATEGORY:
        return None
    from scipy import stats

    probs = category_probabilities(code)
    cats = ["4", "3+SB", "3"]
    sales = {s.draw_number: s.plays for s in estimate_sales(rows, code)}
    by_draw: dict[int, dict[str, int]] = defaultdict(dict)
    for r in rows:
        by_draw[r.draw_number][r.category] = r.winners
    xs, ys = [], []
    for n, w in by_draw.items():
        if n not in sales or n not in draws:
            continue
        expected = sales[n] * sum(probs[c] for c in cats)
        if expected <= 0:
            continue
        xs.append(sum(1 for x in draws[n] if x <= 31))
        ys.append(sum(w.get(c, 0) for c in cats) / expected)
    if len(xs) < 10:
        return None
    rho, p = stats.spearmanr(xs, ys)
    groups = []
    for k in sorted(set(xs)):
        vals = [y for x, y in zip(xs, ys) if x == k]
        groups.append(PopularityGroup(k, len(vals), float(np.mean(vals))))
    return PopularityEffect(cats, groups, float(rho), float(p), len(xs))


# --- valor esperado -----------------------------------------------------------------
@dataclass(frozen=True)
class CategoryEV:
    category: str
    probability: float
    one_in: float
    avg_prize: float  # bruto, promedio por ganador cuando hubo ganadores
    net_prize: float
    contribution: float  # P · premio neto, en pesos por jugada
    draws_with_winners: int


@dataclass
class EVResult:
    game: str
    price: int
    categories: list[CategoryEV]
    non_jackpot_ev: float
    sales: SalesModel
    current_jackpot: int | None
    curve: list[dict] = field(default_factory=list)  # {jackpot, plays, ev, return}
    break_even_jackpot: float | None = None
    n_draws: int = 0

    def ev(self, jackpot: float, popularity: float = 1.0) -> float:
        """VE con un acumulado dado. ``popularity`` escala cuántos otros eligen tu misma
        combinación (1 = jugada promedio; < 1 = menos popular)."""
        p_j = category_probabilities(self.game)[JACKPOT_CATEGORY[self.game]]
        lam = popularity * self.sales.plays(jackpot) * p_j
        share = (1 - exp(-lam)) / lam if lam > 0 else 1.0
        return self.non_jackpot_ev + p_j * net_prize(jackpot) * share


def expected_value(rows: list[PrizeRow], code: str, points: int = 60, max_jackpot: float | None = None) -> EVResult:
    probs = category_probabilities(code)
    jackpot_cat = JACKPOT_CATEGORY[code]
    per_cat: dict[str, list[int]] = defaultdict(list)
    for r in rows:
        if r.winners > 0 and r.category != jackpot_cat:
            per_cat[r.category].append(r.prize_per_winner)

    cats = []
    for cat, p in probs.items():
        if cat == jackpot_cat:
            continue
        prizes = per_cat.get(cat, [])
        avg = float(np.mean(prizes)) if prizes else 0.0
        net = net_prize(avg)
        cats.append(CategoryEV(cat, p, 1 / p, avg, net, p * net, len(prizes)))
    cats.append(CategoryEV(jackpot_cat, probs[jackpot_cat], 1 / probs[jackpot_cat], 0.0, 0.0, 0.0,
                           len({r.draw_number for r in rows if r.category == jackpot_cat and r.winners > 0})))

    sales = fit_sales_model(estimate_sales(rows, code))
    draws = sorted({r.draw_number: r for r in rows}.values(), key=lambda r: r.draw_number)
    current = draws[-1].jackpot_cop if draws else None
    res = EVResult(code, PRICES[code], cats, sum(c.contribution for c in cats), sales, current,
                   n_draws=len(draws))

    jackpots = [r.jackpot_cop for r in draws if r.jackpot_cop]
    hi = max_jackpot or max(max(jackpots, default=1e9) * 2.5, 1e9)
    for j in np.linspace(min(jackpots, default=1e8), hi, points):
        ev = res.ev(float(j))
        res.curve.append({"jackpot": float(j), "plays": res.sales.plays(float(j)), "ev": ev,
                          "return": ev / res.price})
    # Acumulado de equilibrio (VE = precio), si existe en un rango razonable.
    lo_j, hi_j = 0.0, 1e13
    if res.ev(hi_j) >= res.price:
        for _ in range(100):
            mid = (lo_j + hi_j) / 2
            lo_j, hi_j = (mid, hi_j) if res.ev(mid) < res.price else (lo_j, mid)
        res.break_even_jackpot = hi_j
    return res
