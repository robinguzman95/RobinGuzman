import type { components } from "./api-types";

export type S = components["schemas"];
export type GameOut = S["GameOut"];
export type StatsOut = S["StatsOut"];
export type DrawPage = S["DrawPage"];
export type BacktestOut = S["BacktestOut"];
export type SummaryOut = S["SummaryOut"];
export type GenerateOut = S["GenerateOut"];

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export const GAME_CODES = ["baloto", "revancha", "miloto", "colorloto"] as const;
export type GameCode = (typeof GAME_CODES)[number];

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {}
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

// Resumen de valor esperado (data/expected_value.json); la API lo sirve tal cual.
export type EVTax = { rate: number; threshold: number; uvt: number; note: string };
export type EVCategory = {
  category: string;
  probability: number;
  one_in: number;
  avg_prize: number;
  net_prize: number;
  contribution: number;
  draws_with_winners: number;
};
export type EVGame = {
  game: string;
  name: string;
  price: number;
  n_draws: number;
  date_from: string | null;
  date_to: string | null;
  odds: string;
  categories: EVCategory[];
  non_jackpot_ev: number;
  non_jackpot_return: number;
  sales_model: { a: number; b_per_million: number; r2: number; n: number };
  median_plays: number | null;
  sales_series?: {
    draw_number: number;
    draw_date: string | null;
    jackpot: number | null;
    plays: number;
    low: number;
    high: number;
  }[];
  current_jackpot: number | null;
  ev_current: number | null;
  return_current: number | null;
  ev_current_unpopular: number | null;
  curve?: { jackpot: number; plays: number; ev: number; return: number }[];
  break_even_jackpot: number | null;
  max_observed_jackpot: number | null;
  p_share_current: number | null;
  popularity: null | {
    categories: string[];
    spearman_rho: number;
    p_value: number;
    n_draws: number;
    groups: { low_numbers: number; draws: number; ratio: number }[];
  };
  power: {
    ball_bias: {
      n_draws: number;
      min_relative_bias: number;
      expected_count: number;
      biased_count: number;
      power: number;
    };
    backtest: null | {
      n_draws: number;
      comparisons: number;
      mean_hits: number;
      min_improvement: number;
      min_relative_improvement: number;
      power: number;
    };
  };
  tax?: EVTax;
  generated?: string;
};

// Analizador de jugadas (/games/{code}/picks).
export type PickBall = { number: number; color: string | null };
export type PickEval = {
  criterion: string;
  label: string;
  text: string;
  reason: string;
  balls: PickBall[];
  extra: number | null;
  won: number;
  cost: number;
  return: number;
  best_hits: number;
  hits_3plus: number;
  prize_draws: number;
  percentile_vs_random: number;
};
export type PicksOut = {
  game: string;
  name: string;
  window: string;
  n_draws: number;
  date_from: string;
  date_to: string;
  last_draw: number;
  odds: S["Odds"];
  notice: string;
  shape: { sum_low: number; sum_high: number; evens: number[]; highs: number[]; high_from: number };
  picks: { criterion: string; label: string; text: string; reason: string; balls: PickBall[]; extra: number | null }[];
  evaluation: null | {
    price: number;
    test_from: string;
    test_to: string;
    test_draws: number;
    built_until: string | null;
    hits_threshold: number;
    random: {
      sims: number;
      median_return: number;
      p5_return: number;
      p95_return: number;
      mean_hits_3plus: number;
      p95_hits_3plus: number;
    };
    out_of_sample: PickEval[];
    in_sample: PickEval[];
  };
};

export type Health = { status: string; games: Record<string, { last_draw_date: string | null; draws: number }> };

// La caché de servidor vive en lib/data.ts ("use cache"); aquí solo están las llamadas.
export const api = {
  games: () => request<GameOut[]>("/games"),
  health: () => request<Health>("/health"),
  draws: (code: string, pageSize = 1) => request<DrawPage>(`/games/${code}/draws?page_size=${pageSize}`),
  stats: (code: string, window: string) =>
    request<StatsOut>(`/games/${code}/stats?window=${encodeURIComponent(window)}`),
  summary: () => request<SummaryOut>("/backtest/summary"),
  picks: (code: string, window: string) =>
    request<PicksOut>(`/games/${code}/picks?window=${encodeURIComponent(window)}`),
  expectedValue: (code: string) => request<EVGame>(`/games/${code}/expected-value`),
  allExpectedValue: () => request<{ generated: string; tax: EVTax; games: Record<string, EVGame> }>("/expected-value"),
  backtest: (body: { game: string; strategy: string; window: number }) =>
    request<BacktestOut>("/backtest", { method: "POST", body: JSON.stringify(body) }),
  generate: (body: { game: string; n: number; mode: "historico" | "anti_popular"; window: "12m" | "100" | "all" }) =>
    request<GenerateOut>("/generate", { method: "POST", body: JSON.stringify(body) }),
};

/** Para páginas de servidor: si la API no responde, se muestra un aviso en vez de romper. */
export async function safe<T>(p: Promise<T>): Promise<T | null> {
  try {
    return await p;
  } catch {
    return null;
  }
}
