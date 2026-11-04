"""Esquemas de respuesta. Toda respuesta de un juego incluye su probabilidad real."""

from datetime import date

from pydantic import BaseModel


class Odds(BaseModel):
    combinations: int
    jackpot_odds: str  # "1 en 15.401.568"
    jackpot_probability: float


class GameOut(BaseModel):
    code: str
    name: str
    main_count: int
    main_max: int
    extra_max: int | None
    colors: list[str] | None
    odds: Odds


class BallOut(BaseModel):
    number: int
    color: str | None = None


class DrawOut(BaseModel):
    draw_number: int
    draw_date: date
    balls: list[BallOut]
    extra: int | None
    source_url: str | None


class DrawPage(BaseModel):
    game: str
    page: int
    page_size: int
    total: int
    items: list[DrawOut]


class BallStatOut(BaseModel):
    label: str
    number: int
    color: str | None
    count: int
    draws_since: int | None
    days_since: int | None


class ComboOut(BaseModel):
    balls: list[str]
    count: int


class ShapeOut(BaseModel):
    sum_min: int
    sum_max: int
    sum_mean: float
    even_counts: dict[int, int]
    high_counts: dict[int, int]


class ChiSquareOut(BaseModel):
    label: str
    statistic: float
    dof: int
    p_value: float | None
    expected_per_cell: float
    correction: float
    reliable: bool
    verdict: str


class RunsOut(BaseModel):
    tested: int
    alpha_bonferroni: float
    significant_raw: int
    significant_bonferroni: list[str]
    min_p_value: float | None
    verdict: str


class StatsOut(BaseModel):
    game: str
    window: str
    n_draws: int
    date_from: date | None
    date_to: date | None
    odds: Odds
    disclaimer: str
    frequency: dict[str, int]
    number_frequency: dict[int, int] | None  # solo ColorLoto (marginal por número)
    color_frequency: dict[str, int] | None
    extra_frequency: dict[int, int] | None
    hot: list[BallStatOut]
    cold: list[BallStatOut]
    overdue: list[BallStatOut]
    top_pairs: list[ComboOut]
    top_triples: list[ComboOut]
    shape: ShapeOut | None
    uniformity: list[ChiSquareOut]
    runs: RunsOut
