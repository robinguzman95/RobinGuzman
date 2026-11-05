"""Analizador de jugadas: jugadas armadas desde el histórico y cómo les habría ido.

Criterios (todos usan SOLO los sorteos que se le pasan como historia):
- calientes: las K balotas que más salieron en la ventana.
- consistentes: las que están arriba en las tres ventanas a la vez (12 meses, 100 sorteos, todo).
- forma típica: de las 15 más calientes, la combinación con más salidas cuya suma, cantidad de
  pares y cantidad de altos está dentro de lo habitual en los resultados históricos.
- pareja: la pareja que más salió junta, completada con calientes de forma típica.
- atrasados: las que llevan más sorteos sin salir ("ya les toca").
La balota extra (superbalota) es siempre la más frecuente de la ventana.

Evaluación con premios reales: se juega la misma jugada en cada sorteo del periodo de prueba y se
suma lo que habría pagado baloto.com (premio por ganador de la categoría acertada; si en la
categoría nadie ganó, el promedio del periodo; el premio mayor sin ganadores = el acumulado).
Dos versiones:
- dentro de la muestra: jugada armada con el mismo periodo en que se evalúa (optimista: ya se
  sabe qué salió);
- fuera de la muestra: armada con lo que se sabía antes del periodo (la prueba justa).
"""

import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from itertools import combinations

import numpy as np

from app.analysis import frequency as fq
from app.analysis.expected import JACKPOT_CATEGORY, PRICES
from app.games import Game, Ticket
from app.ingest.prizes import PrizeRow
from app.ingest.records import DrawRecord

Ball = fq.Ball
CRITERIA = {
    "calientes": "Las que más salieron",
    "consistentes": "Calientes en las tres ventanas",
    "forma": "Calientes con forma típica",
    "pareja": "La pareja más repetida + calientes",
    "atrasados": "Las que llevan más tiempo sin salir",
}


@dataclass(frozen=True)
class Shape:
    sum_low: int
    sum_high: int
    evens: tuple[int, ...]
    highs: tuple[int, ...]

    def fits(self, numbers: list[int], game: type[Game]) -> bool:
        return (self.sum_low <= sum(numbers) <= self.sum_high
                and sum(n % 2 == 0 for n in numbers) in self.evens
                and sum(n > game.main_max / 2 for n in numbers) in self.highs)


def typical_shape(history: list[DrawRecord], game: type[Game]) -> Shape:
    """Rango central (50 %) de la suma y los dos valores más comunes de pares y de altos."""
    sums = [sum(r.numbers) for r in history]
    ev = Counter(sum(n % 2 == 0 for n in r.numbers) for r in history)
    hi = Counter(sum(n > game.main_max / 2 for n in r.numbers) for r in history)
    return Shape(int(np.percentile(sums, 25)), int(np.percentile(sums, 75)),
                 tuple(sorted(k for k, _ in ev.most_common(2))), tuple(sorted(k for k, _ in hi.most_common(2))))


@dataclass(frozen=True)
class Pick:
    criterion: str
    label: str
    balls: tuple[Ball, ...]
    extra: int | None
    reason: str

    @property
    def ticket(self) -> Ticket:
        b = sorted(self.balls, key=lambda x: (x[0], str(x[1])))
        return Ticket(tuple(n for n, _ in b), tuple(c for _, c in b) if b and b[0][1] else None, self.extra)

    @property
    def text(self) -> str:
        main = " - ".join(f"{n} {c}" if c else f"{n:02d}" for n, c in sorted(self.balls, key=lambda x: (x[0], str(x[1]))))
        return main + (f" | superbalota {self.extra:02d}" if self.extra is not None else "")


def _key(b: Ball) -> tuple:
    return (b[0], str(b[1]))


def build_picks(history: list[DrawRecord], game: type[Game], window: fq.Window = "12m") -> list[Pick]:
    hist = sorted(history, key=lambda r: r.draw_number)
    win = fq.apply_window(hist, window)
    k = game.main_count
    freq = fq.ball_frequency(win, game)
    rank = sorted(freq, key=lambda b: (-freq[b], _key(b)))
    extra = None
    if game.extra_max:
        ef = fq.extra_frequency(win, game)
        extra = min(ef, key=lambda n: (-ef[n], n))
    shape = typical_shape(hist, game)
    n_win = len(win)

    def why(balls) -> str:
        return ", ".join(f"{fq.ball_label(b)} ({freq[b]})" for b in sorted(balls, key=_key))

    picks = [Pick("calientes", CRITERIA["calientes"], tuple(rank[:k]), extra,
                  f"Veces que salió cada una en {n_win} sorteos: {why(rank[:k])}.")]

    # Consistentes: suma de posiciones en las tres ventanas.
    def positions(recs):
        f = fq.ball_frequency(recs, game)
        order = sorted(f, key=lambda b: (-f[b], _key(b)))
        return {b: i for i, b in enumerate(order)}
    p12, p100, pall = positions(fq.apply_window(hist, "12m")), positions(fq.apply_window(hist, 100)), positions(hist)
    cons = sorted(fq.all_balls(game), key=lambda b: (p12[b] + p100[b] + pall[b], _key(b)))[:k]
    picks.append(Pick("consistentes", CRITERIA["consistentes"], tuple(cons), extra,
                      "Puestos en el ranking (12 meses / 100 sorteos / todo): "
                      + ", ".join(f"{fq.ball_label(b)} ({p12[b] + 1}/{p100[b] + 1}/{pall[b] + 1})"
                                  for b in sorted(cons, key=_key)) + "."))

    # Forma típica entre las 15 más calientes.
    pool = rank[:15]
    fitting = [c for c in combinations(pool, k) if shape.fits([b[0] for b in c], game)]
    best = max(fitting, key=lambda c: (sum(freq[b] for b in c), [-_key(b)[0] for b in c])) if fitting else tuple(rank[:k])
    nums = [b[0] for b in best]
    picks.append(Pick("forma", CRITERIA["forma"], tuple(best), extra,
                      f"Suma {sum(nums)} (lo habitual: {shape.sum_low}–{shape.sum_high}), "
                      f"{sum(n % 2 == 0 for n in nums)} pares, {sum(n > game.main_max / 2 for n in nums)} altos. "
                      f"Salidas: {why(best)}."))

    # Pareja más repetida + calientes que completen forma típica.
    (a, b), times = fq.top_combos(win, 2, 1)[0]
    base = [a, b]
    rest = [x for x in rank if x not in base]
    fill = next((list(c) for c in combinations(rest[:12], k - 2) if shape.fits([y[0] for y in base + list(c)], game)),
                rest[:k - 2])
    picks.append(Pick("pareja", CRITERIA["pareja"], tuple(base + fill), extra,
                      f"{fq.ball_label(a)} y {fq.ball_label(b)} salieron juntas {times} veces; "
                      f"se completan con {', '.join(fq.ball_label(x) for x in sorted(fill, key=_key))}."))

    # Atrasados.
    od = fq.overdue(win, game, n=k)
    od_extra = None
    if game.extra_max:
        last = {r.extra: i for i, r in enumerate(win)}
        od_extra = min(range(1, game.extra_max + 1), key=lambda n: (last.get(n, -1), n))
    picks.append(Pick("atrasados", CRITERIA["atrasados"], tuple(s.ball for s in od), od_extra,
                      "Sorteos sin salir: " + ", ".join(
                          f"{s.label} ({'no salió' if s.draws_since is None else s.draws_since})" for s in od) + "."))
    return picks


# --- evaluación con premios reales -------------------------------------------------
def category_for(game: type[Game], ticket: Ticket, draw: DrawRecord) -> list[str]:
    """Categorías de premio que gana `ticket` en `draw` (puede ser más de una en ColorLoto)."""
    hits = len(set(ticket.balls()) & set(draw.ticket.balls()))
    code = game.code
    if code in ("baloto", "revancha"):
        s = ticket.extra == draw.extra
        if hits >= 3:
            return [f"{hits}+SB" if s else str(hits)]
        if hits == 2 and s:
            return ["2+SB"]
        return ["0+SB"] if s else []
    if code == "miloto":
        return [str(hits)] if hits >= 2 else []
    if code == "colorloto":
        out = [str(hits)] if hits >= 3 else []
        if hits < 6:
            if sorted(ticket.numbers) == sorted(draw.numbers):
                out.append("6N")
            if sorted(ticket.colors or ()) == sorted(draw.colors or ()):
                out.append("6C")
        return out
    raise ValueError(code)


@dataclass
class PlayResult:
    draws: int
    cost: int
    won: int
    hits: dict[int, int] = field(default_factory=dict)  # aciertos principales -> veces
    prize_draws: int = 0  # sorteos en que ganó algo
    best: int = 0

    @property
    def ret(self) -> float:
        return self.won / self.cost if self.cost else 0.0


def play_ticket(game: type[Game], ticket: Ticket, test: list[DrawRecord],
                prizes: dict[int, dict[str, PrizeRow]], avg_prize: dict[str, float]) -> PlayResult:
    price = PRICES[game.code]
    res = PlayResult(0, 0, 0, defaultdict(int))
    jackpot = JACKPOT_CATEGORY[game.code]
    tb = set(ticket.balls())
    for d in test:
        if d.draw_number not in prizes:
            continue
        res.draws += 1
        res.cost += price
        h = len(tb & set(d.ticket.balls()))
        res.hits[h] += 1
        res.best = max(res.best, h)
        cats = category_for(game, ticket, d)
        pay = 0
        for c in cats:
            row = prizes[d.draw_number].get(c)
            if row is None:
                continue
            if row.winners:
                v = row.prize_per_winner
            elif c == jackpot:
                v = row.jackpot_cop or 0
            else:
                v = avg_prize.get(c, 0)
            pay = max(pay, int(v))
        if pay:
            res.prize_draws += 1
            res.won += pay
    res.hits = dict(sorted(res.hits.items()))
    return res


def _random_ticket(game: type[Game], rng: random.Random) -> Ticket:
    balls = sorted(rng.sample(fq.all_balls(game), game.main_count), key=_key)
    return Ticket(tuple(b[0] for b in balls), tuple(b[1] for b in balls) if game.colors else None,
                  rng.randint(1, game.extra_max) if game.extra_max else None)


def evaluate(game: type[Game], records: list[DrawRecord], prize_rows: list[PrizeRow],
             sims: int = 3000, seed: int = 7) -> dict:
    recs = sorted(records, key=lambda r: r.draw_number)
    prizes: dict[int, dict[str, PrizeRow]] = defaultdict(dict)
    per_cat: dict[str, list[int]] = defaultdict(list)
    for p in prize_rows:
        prizes[p.draw_number][p.category] = p
        if p.winners:
            per_cat[p.category].append(p.prize_per_winner)
    avg_prize = {c: float(np.mean(v)) for c, v in per_cat.items()}
    test = [r for r in recs if r.draw_number in prizes]
    start = test[0].draw_date
    before = [r for r in recs if r.draw_date < start]
    threshold = 3

    rng = random.Random(seed)
    rnd = [play_ticket(game, _random_ticket(game, rng), test, prizes, avg_prize) for _ in range(sims)]
    rets = np.array([r.ret for r in rnd])
    threes = np.array([sum(v for h, v in r.hits.items() if h >= threshold) for r in rnd])

    def describe(p: Pick, r: PlayResult) -> dict:
        three = sum(v for h, v in r.hits.items() if h >= threshold)
        return {"criterion": p.criterion, "label": p.label, "text": p.text, "reason": p.reason,
                "balls": [{"number": b[0], "color": b[1]} for b in sorted(p.balls, key=_key)], "extra": p.extra,
                "won": r.won, "cost": r.cost, "return": r.ret, "best_hits": r.best, "hits_3plus": three,
                "prize_draws": r.prize_draws, "hits": r.hits,
                "percentile_vs_random": float((rets < r.ret).mean())}

    out_sample = [describe(p, play_ticket(game, p.ticket, test, prizes, avg_prize))
                  for p in build_picks(before, game)] if len(before) >= 30 else []
    in_sample = [describe(p, play_ticket(game, p.ticket, test, prizes, avg_prize)) for p in build_picks(test, game, "all")]
    return {
        "game": game.code,
        "price": PRICES[game.code],
        "test_from": test[0].draw_date.isoformat(),
        "test_to": test[-1].draw_date.isoformat(),
        "test_draws": len(test),
        "built_until": before[-1].draw_date.isoformat() if before else None,
        "hits_threshold": threshold,
        "random": {"sims": sims, "median_return": float(np.median(rets)), "p5_return": float(np.percentile(rets, 5)),
                   "p95_return": float(np.percentile(rets, 95)), "mean_hits_3plus": float(threes.mean()),
                   "p95_hits_3plus": float(np.percentile(threes, 95))},
        "out_of_sample": out_sample,
        "in_sample": in_sample,
    }
