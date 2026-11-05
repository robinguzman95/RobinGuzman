"""Arma el resumen de valor esperado y potencia que sirve la API (data/expected_value.json).

Se genera en local con `uv run lotolab expected-value` a partir de data/raw/*_premios.csv y del
histórico de sorteos, igual que el resumen del backtest.
"""

from datetime import date
from math import exp
from statistics import median

from app.analysis.expected import (
    TAX_RATE,
    TAX_THRESHOLD,
    UVT_2026,
    estimate_sales,
    expected_value,
    popularity_effect,
)
from app.analysis.power import min_detectable_ball_bias, min_detectable_improvement
from app.games import get_game
from app.ingest.prizes import PrizeRow
from app.ingest.records import DrawRecord


def game_summary(code: str, prizes: list[PrizeRow], draws: list[DrawRecord], backtest_draws: int | None) -> dict:
    game = get_game(code)
    res = expected_value(prizes, code)
    sales = estimate_sales(prizes, code)
    by_number = {d.draw_number: d for d in draws}
    pop = popularity_effect(prizes, {n: d.numbers for n, d in by_number.items()}, code)
    prize_draws = sorted({r.draw_number for r in prizes})
    dates = [by_number[n].draw_date for n in prize_draws if n in by_number]

    ball = min_detectable_ball_bias(game, len(draws))
    jackpots = [r.jackpot_cop for r in prizes if r.jackpot_cop]
    p_j = res.categories[-1].probability
    lam_now = res.sales.plays(res.current_jackpot) * p_j if res.current_jackpot else None
    bt = min_detectable_improvement(game, backtest_draws) if backtest_draws else None
    current = res.current_jackpot
    return {
        "game": code,
        "name": game.name,
        "price": res.price,
        "n_draws": res.n_draws,
        "date_from": min(dates).isoformat() if dates else None,
        "date_to": max(dates).isoformat() if dates else None,
        "odds": game.odds_text(),
        "categories": [
            {"category": c.category, "probability": c.probability, "one_in": c.one_in, "avg_prize": c.avg_prize,
             "net_prize": c.net_prize, "contribution": c.contribution, "draws_with_winners": c.draws_with_winners}
            for c in res.categories
        ],
        "non_jackpot_ev": res.non_jackpot_ev,
        "non_jackpot_return": res.non_jackpot_ev / res.price,
        "sales_model": {"a": res.sales.a, "b_per_million": res.sales.b, "r2": res.sales.r2, "n": res.sales.n},
        "median_plays": median([s.plays for s in sales]) if sales else None,
        "sales_series": [
            {"draw_number": s.draw_number, "draw_date": by_number[s.draw_number].draw_date.isoformat()
             if s.draw_number in by_number else None, "jackpot": s.jackpot, "plays": s.plays,
             "low": s.plays_low, "high": s.plays_high}
            for s in sales
        ],
        "current_jackpot": current,
        "ev_current": res.ev(current) if current else None,
        "return_current": res.ev(current) / res.price if current else None,
        "ev_current_unpopular": res.ev(current, popularity=0.5) if current else None,
        "curve": res.curve,
        "break_even_jackpot": res.break_even_jackpot,
        "max_observed_jackpot": max(jackpots) if jackpots else None,
        # Si acertaras el premio mayor hoy: probabilidad de que al menos otra jugada también lo acierte.
        "p_share_current": (1 - exp(-lam_now)) if lam_now else None,
        "popularity": None if pop is None else {
            "categories": pop.categories, "spearman_rho": pop.spearman_rho, "p_value": pop.p_value,
            "n_draws": pop.n_draws,
            "groups": [{"low_numbers": g.low_numbers, "draws": g.draws, "ratio": g.ratio} for g in pop.groups],
        },
        "power": {
            "ball_bias": {"n_draws": ball.n_draws, "min_relative_bias": ball.min_relative_bias,
                          "expected_count": ball.expected_count, "biased_count": ball.biased_count,
                          "power": ball.power, "alpha": ball.alpha},
            "backtest": None if bt is None else {
                "n_draws": bt.n_draws, "comparisons": bt.comparisons, "mean_hits": bt.mean_hits,
                "sd_hits": bt.sd_hits, "min_improvement": bt.min_improvement,
                "min_relative_improvement": bt.min_relative_improvement, "power": bt.power, "alpha": bt.alpha},
        },
    }


def build_summary(per_game: dict[str, dict]) -> dict:
    return {
        "generated": date.today().isoformat(),
        "tax": {"rate": TAX_RATE, "threshold": TAX_THRESHOLD, "uvt": UVT_2026,
                "note": "Retención del 20 % sobre premios de loterías > 48 UVT (2026). Proyecto de ley "
                        "para subirla al 30 %, no vigente."},
        "games": per_game,
    }
