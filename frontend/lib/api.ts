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

export type Health = { status: string; games: Record<string, { last_draw_date: string | null; draws: number }> };

// La caché de servidor vive en lib/data.ts ("use cache"); aquí solo están las llamadas.
export const api = {
  games: () => request<GameOut[]>("/games"),
  health: () => request<Health>("/health"),
  draws: (code: string, pageSize = 1) => request<DrawPage>(`/games/${code}/draws?page_size=${pageSize}`),
  stats: (code: string, window: string) =>
    request<StatsOut>(`/games/${code}/stats?window=${encodeURIComponent(window)}`),
  summary: () => request<SummaryOut>("/backtest/summary"),
  backtest: (body: { game: string; strategy: string; window: number }) =>
    request<BacktestOut>("/backtest", { method: "POST", body: JSON.stringify(body) }),
  generate: (body: { game: string; n: number }) =>
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
