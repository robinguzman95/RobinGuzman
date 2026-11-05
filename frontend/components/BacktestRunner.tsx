"use client";

import { useEffect, useState } from "react";
import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, type BacktestOut } from "@/lib/api";
import { dateEs, num, pValue, STRATEGY_LABEL } from "@/lib/format";

const GAMES = [
  { code: "baloto", name: "Baloto" },
  { code: "revancha", name: "Revancha" },
  { code: "miloto", name: "MiLoto" },
  { code: "colorloto", name: "ColorLoto" },
];
const WINDOWS = [50, 100, 200];

export function BacktestRunner({ primaryWindow }: { primaryWindow: number }) {
  const [game, setGame] = useState("baloto");
  const [strategy, setStrategy] = useState("hot");
  const [window, setWindow] = useState(primaryWindow);
  // El resultado guarda la clave de la petición que lo produjo: "cargando" = la clave actual aún
  // no tiene respuesta. Mientras tanto se mantiene el resultado anterior atenuado (sin saltos).
  const key = `${game}|${strategy}|${window}`;
  const [state, setState] = useState<{ key: string; result?: BacktestOut; error?: string } | null>(null);

  useEffect(() => {
    let alive = true;
    api
      .backtest({ game, strategy, window })
      .then((r) => alive && setState({ key, result: r }))
      .catch((e: Error) => alive && setState((prev) => ({ key, result: prev?.result, error: e.message })));
    return () => {
      alive = false;
    };
  }, [key, game, strategy, window]);

  const loading = state?.key !== key;
  const result = state?.result ?? null;
  const error = !loading ? (state?.error ?? null) : null;

  return (
    <section className="card space-y-4 p-5">
      <h2 className="text-xl font-semibold">Pruébalo tú</h2>
      <div className="flex flex-wrap gap-3 text-sm">
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
          Estrategia
          <select className="field" value={strategy} onChange={(e) => setStrategy(e.target.value)}>
            {Object.entries(STRATEGY_LABEL).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          Ventana (sorteos de historia)
          <select className="field" value={window} onChange={(e) => setWindow(Number(e.target.value))}>
            {WINDOWS.map((w) => (
              <option key={w} value={w}>
                {w}
                {w === primaryWindow ? " (principal)" : ""}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error && (
        <p role="alert" className="text-sm" style={{ color: "var(--serious)" }}>
          ⚠ {error}
        </p>
      )}

      <div style={{ opacity: loading ? 0.5 : 1 }} aria-busy={loading}>
        {result ? (
          <Result r={result} />
        ) : (
          !error && (
            <p className="text-secondary">
              Calculando 10.000 simulaciones… (la primera vez puede tardar unos segundos)
            </p>
          )
        )}
      </div>
    </section>
  );
}

function Result({ r }: { r: BacktestOut }) {
  const data = r.series.map((p) => ({ ...p, band: [p.p5, p.p95] as [number, number] }));
  const beats = r.beats_random;
  return (
    <div className="space-y-4">
      <p className="text-lg">
        <span className="font-semibold" style={{ color: beats ? "var(--serious)" : "var(--good)" }}>
          <span aria-hidden>{beats ? "⚠ " : "✓ "}</span>
          {beats ? "Por encima del azar en esta corrida" : "Dentro de la banda del azar"}
        </span>
        <span className="text-secondary">
          {" "}
          — {num(r.avg_hits, 3)} aciertos por sorteo frente a {num(r.baseline_mean, 3)} de una jugada al azar (90% de
          las jugadas al azar: {num(r.baseline_p5, 3)}–{num(r.baseline_p95, 3)}). p = {pValue(r.p_value)}.
        </span>
      </p>
      {beats && (
        <p className="text-sm text-secondary">
          Una sola corrida “gana” por suerte 1 de cada 20 veces. En el reporte de abajo, con las 60 combinaciones y la
          corrección de Bonferroni, ninguna estrategia supera al azar.
        </p>
      )}

      <figure className="space-y-2">
        <figcaption className="text-sm text-secondary">
          Promedio acumulado de aciertos de la estrategia, sorteo a sorteo ({r.n_draws} sorteos evaluados,{" "}
          {dateEs(r.date_from)} → {dateEs(r.date_to)}).
        </figcaption>
        <ul className="flex flex-wrap gap-4 text-sm" aria-label="leyenda">
          <li className="flex items-center gap-2">
            <span className="inline-block h-0.5 w-6" style={{ background: "var(--series-1)" }} />
            {STRATEGY_LABEL[r.strategy] ?? r.strategy}
          </li>
          <li className="flex items-center gap-2">
            <span
              className="inline-block h-3 w-6 rounded-sm"
              style={{ background: "var(--band-fill)", border: "1px solid var(--band)" }}
            />
            90% de las jugadas al azar (p5–p95)
          </li>
        </ul>
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 8, right: 12, bottom: 8, left: 0 }}>
              <CartesianGrid vertical={false} stroke="var(--grid)" />
              <XAxis
                dataKey="draw_date"
                tickFormatter={(d: string) => dateEs(d)}
                tick={{ fill: "var(--text-muted)", fontSize: 11 }}
                tickLine={false}
                axisLine={{ stroke: "var(--axis)" }}
                minTickGap={40}
              />
              <YAxis
                tick={{ fill: "var(--text-muted)", fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                width={40}
                tickFormatter={(v: number) => num(v, 2)}
                domain={["auto", "auto"]}
              />
              <Tooltip
                contentStyle={{
                  background: "var(--surface-1)",
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  color: "var(--text-primary)",
                }}
                labelFormatter={(d) => `Hasta el ${dateEs(String(d))}`}
                formatter={(v, name) =>
                  name === "band"
                    ? [`${num((v as number[])[0], 3)}–${num((v as number[])[1], 3)}`, "azar (p5–p95)"]
                    : [num(v as number, 3), "estrategia"]
                }
              />
              <Area
                dataKey="band"
                stroke="var(--band)"
                strokeWidth={1}
                fill="var(--band-fill)"
                isAnimationActive={false}
              />
              <Line dataKey="strategy" stroke="var(--series-1)" strokeWidth={2} dot={false} isAnimationActive={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </figure>

      <details className="text-sm">
        <summary className="cursor-pointer text-secondary">Distribución de aciertos (tabla)</summary>
        <table className="data mt-2 max-w-sm">
          <thead>
            <tr>
              <th>Aciertos</th>
              <th>Sorteos</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(r.hit_distribution).map(([k, v]) => (
              <tr key={k}>
                <td>{k}</td>
                <td>{v}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
      <p className="text-sm text-secondary">Premio mayor: {r.odds.jackpot_odds}, con o sin estrategia.</p>
    </div>
  );
}
