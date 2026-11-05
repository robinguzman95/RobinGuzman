"use client";

import Link from "next/link";
import { useState } from "react";
import { Balls } from "@/components/Balls";
import { OddsNotice } from "@/components/OddsNotice";
import { api, type GenerateOut } from "@/lib/api";
import { dateEs, num } from "@/lib/format";

const GAMES = [
  { code: "baloto", name: "Baloto" },
  { code: "revancha", name: "Revancha" },
  { code: "miloto", name: "MiLoto" },
  { code: "colorloto", name: "ColorLoto" },
];
const WINDOWS = [
  { value: "12m", label: "Últimos 12 meses" },
  { value: "100", label: "Últimos 100 sorteos" },
  { value: "all", label: "Todo el histórico" },
] as const;
type Mode = "historico" | "anti_popular";
type Window = (typeof WINDOWS)[number]["value"];

const money = (x: number) => `$${num(x)}`;
const pct = (r: number) => `${num(r * 100, 0)} %`;

export default function GeneratorPage() {
  const [game, setGame] = useState("baloto");
  const [n, setN] = useState(5);
  const [mode, setMode] = useState<Mode>("historico");
  const [window, setWindow] = useState<Window>("12m");
  const [out, setOut] = useState<GenerateOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState<number | null>(null);
  const name = GAMES.find((g) => g.code === game)?.name ?? game;
  const extraName = game === "baloto" || game === "revancha" ? "superbalota" : null;

  async function run() {
    setLoading(true);
    setError(null);
    try {
      setOut(await api.generate({ game, n, mode, window }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function copy(text: string, i: number) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(i);
      setTimeout(() => setCopied(null), 1500);
    } catch {
      setError("No se pudo copiar; selecciona el texto a mano.");
    }
  }

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-3xl font-bold">Generador de jugadas</h1>
        <p className="max-w-3xl text-secondary">
          Genera jugadas con las balotas que <strong>más han salido</strong> (calientes, con la forma típica de un
          resultado y las parejas más repetidas) y mira, para cada una, cuántas veces salió cada número y cuánto habría
          ganado jugándola en cada sorteo del último año. También puedes generar jugadas anti-populares, que evitan los
          números que juega mucha gente.
        </p>
      </header>

      {out ? (
        <OddsNotice odds={out.odds} name={name}>
          {out.notice}
        </OddsNotice>
      ) : (
        <aside className="card border-l-4 notice-border p-4 text-sm" role="note">
          Ninguna jugada tiene más probabilidad de ganar que otra. Al generar verás la probabilidad real del juego.
        </aside>
      )}

      <form
        className="card flex flex-wrap items-end gap-3 p-5 text-sm"
        onSubmit={(e) => {
          e.preventDefault();
          run();
        }}
      >
        <label className="flex flex-col gap-1">
          Juego
          <select className="field" value={game} onChange={(e) => setGame(e.target.value)}>
            {GAMES.map((g) => (
              <option key={g.code} value={g.code}>
                {g.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          Tipo de jugada
          <select className="field" value={mode} onChange={(e) => setMode(e.target.value as Mode)}>
            <option value="historico">Lo que más ha salido</option>
            <option value="anti_popular">Anti-populares</option>
          </select>
        </label>
        {mode === "historico" && (
          <label className="flex flex-col gap-1">
            Periodo
            <select className="field" value={window} onChange={(e) => setWindow(e.target.value as Window)}>
              {WINDOWS.map((w) => (
                <option key={w.value} value={w.value}>
                  {w.label}
                </option>
              ))}
            </select>
          </label>
        )}
        <label className="flex flex-col gap-1">
          Jugadas
          <input
            className="field w-20"
            type="number"
            min={1}
            max={10}
            value={n}
            onChange={(e) => setN(Math.max(1, Math.min(10, Number(e.target.value) || 1)))}
          />
        </label>
        <button className="btn" type="submit" disabled={loading}>
          {loading ? "Generando…" : "Generar"}
        </button>
      </form>

      {error && (
        <p role="alert" style={{ color: "var(--serious)" }}>
          ⚠ {error}
        </p>
      )}

      {out && (
        <ol className="space-y-3">
          {out.plays.map((p, i) => {
            const s = p.stats;
            const h = s?.history;
            return (
              <li key={i} className="card space-y-3 p-4">
                <div className="flex flex-wrap items-center gap-4">
                  <span className="text-sm font-semibold text-muted">Jugada {i + 1}</span>
                  <Balls balls={p.balls} extra={p.extra} />
                  <button type="button" className="btn-ghost ml-auto text-sm" onClick={() => copy(p.text, i)}>
                    {copied === i ? "¡Copiado!" : "Copiar"}
                  </button>
                  <span className="sr-only">{p.text}</span>
                </div>

                {s && out.mode === "historico" && (
                  <div className="grid gap-x-6 gap-y-2 text-sm md:grid-cols-2">
                    <p>
                      <span className="font-semibold">Veces que salió cada una</span> en {num(s.window_draws)} sorteos
                      (lo normal: {num(s.expected_count, 1)}):{" "}
                      {s.counts.map((c) => `${c.label} (${c.count})`).join(", ")}
                      {extraName && p.extra != null && s.extra_count != null && s.extra_expected != null && (
                        <>
                          {" "}
                          · {extraName} {String(p.extra).padStart(2, "0")} ({s.extra_count}; lo normal{" "}
                          {num(s.extra_expected, 1)})
                        </>
                      )}
                      .
                    </p>
                    <p>
                      <span className="font-semibold">Forma:</span> suma {s.sum}, {s.evens} pares, {s.highs} altos
                      {s.shape_ok ? " (típica de un resultado ganador)" : " (fuera de lo habitual)"}.
                      {s.frequent_pairs.length > 0 && (
                        <>
                          {" "}
                          <span className="font-semibold">Parejas frecuentes:</span>{" "}
                          {s.frequent_pairs.map((x) => `${x.pair} (${x.count} veces juntas)`).join(", ")}.
                        </>
                      )}
                    </p>
                    {h && (
                      <p className="md:col-span-2">
                        <span className="font-semibold">Jugándola en cada sorteo del último año</span> ({h.draws}{" "}
                        sorteos, {dateEs(h.date_from)} → {dateEs(h.date_to)}, {money(h.cost)}): habría ganado{" "}
                        <strong>{money(h.won)}</strong> ({pct(h.ret)} de lo jugado) en {h.prize_draws} sorteos; mejor
                        resultado {h.best_hits} aciertos; 3 o más aciertos {h.hits_3plus}{" "}
                        {h.hits_3plus === 1 ? "vez" : "veces"}.
                      </p>
                    )}
                  </div>
                )}

                {out.mode === "anti_popular" && (
                  <div className="text-sm text-secondary">
                    Popularidad {p.popularity_score}/100 ({p.popularity_level})
                    {p.popularity_reasons.length > 0 && <span> · {p.popularity_reasons.join("; ")}</span>}
                  </div>
                )}
              </li>
            );
          })}
        </ol>
      )}
      {out?.mode === "historico" && (
        <p className="text-xs text-muted">
          El resultado del último año se calcula con los premios que pagó {name} en cada sorteo (antes de impuestos).
          Ese resultado mira hacia atrás: las balotas se eligieron sabiendo qué salió, por eso suele verse mejor que lo
          que se puede esperar hacia adelante. En el{" "}
          <Link className="link" href="/analizador">
            Analizador
          </Link>{" "}
          está la prueba justa.
        </p>
      )}
      {out?.mode === "anti_popular" && (
        <p className="text-xs text-muted">
          El puntaje de popularidad es una estimación heurística (no hay datos públicos de lo que juega la gente) y la
          cuadrícula del tiquete es aproximada.
        </p>
      )}
    </div>
  );
}
