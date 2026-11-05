"use client";

import { useState } from "react";
import { Balls } from "@/components/Balls";
import { OddsNotice } from "@/components/OddsNotice";
import { api, type GenerateOut } from "@/lib/api";

const GAMES = [
  { code: "baloto", name: "Baloto" },
  { code: "revancha", name: "Revancha" },
  { code: "miloto", name: "MiLoto" },
  { code: "colorloto", name: "ColorLoto" },
];

export default function GeneratorPage() {
  const [game, setGame] = useState("baloto");
  const [n, setN] = useState(5);
  const [out, setOut] = useState<GenerateOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState<number | null>(null);
  const name = GAMES.find((g) => g.code === game)?.name ?? game;

  async function run() {
    setLoading(true);
    setError(null);
    try {
      setOut(await api.generate({ game, n }));
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
        <h1 className="text-3xl font-bold">Generador de jugadas anti-populares</h1>
        <p className="max-w-3xl text-secondary">
          Lo único que sí se puede optimizar: evitar jugadas que mucha gente elige (fechas, secuencias, figuras en el
          tiquete, resultados anteriores). Así, si ganas, compartes el premio con menos personas. La probabilidad de
          ganar es exactamente la misma.
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
          {out.plays.map((p, i) => (
            <li key={i} className="card flex flex-wrap items-center gap-4 p-4">
              <Balls balls={p.balls} extra={p.extra} />
              <div className="text-sm text-secondary">
                Popularidad {p.popularity_score}/100 ({p.popularity_level})
                {p.popularity_reasons.length > 0 && <span> · {p.popularity_reasons.join("; ")}</span>}
              </div>
              <button type="button" className="btn-ghost ml-auto text-sm" onClick={() => copy(p.text, i)}>
                {copied === i ? "¡Copiado!" : "Copiar"}
              </button>
              <span className="sr-only">{p.text}</span>
            </li>
          ))}
        </ol>
      )}
      {out && (
        <p className="text-xs text-muted">
          El puntaje de popularidad es una estimación heurística (no hay datos públicos de lo que juega la gente) y la
          cuadrícula del tiquete es aproximada.
        </p>
      )}
    </div>
  );
}
