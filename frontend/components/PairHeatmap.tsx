"use client";

import { useState } from "react";

const STEPS = ["--seq-100", "--seq-200", "--seq-300", "--seq-400", "--seq-500", "--seq-600", "--seq-700"];

/** Mapa de calor (triángulo inferior) de cuántas veces salieron juntas dos balotas.
 *  Secuencial de un solo tono; 0 = superficie. Tooltip al pasar el mouse o enfocar con teclado. */
export function PairHeatmap({ labels, pairs }: { labels: string[]; pairs: [string, string, number][] }) {
  const counts = new Map<string, number>();
  let max = 0;
  for (const [a, b, n] of pairs) {
    counts.set(`${a}|${b}`, n);
    counts.set(`${b}|${a}`, n);
    max = Math.max(max, n);
  }
  const [hover, setHover] = useState<{ a: string; b: string; n: number } | null>(null);
  const n = labels.length;
  const cell = 12;
  const pad = 34;
  const size = pad + n * cell;
  const step = (v: number) =>
    v === 0 || max === 0 ? null : STEPS[Math.min(STEPS.length - 1, Math.floor(((v - 1) / max) * STEPS.length))];
  const top = [...pairs].sort((x, y) => y[2] - x[2]).slice(0, 10);

  return (
    <figure className="space-y-2">
      <figcaption className="text-sm text-secondary">
        Parejas que salieron juntas (más oscuro = más veces; máximo {max}).{" "}
        <span aria-live="polite" className="font-semibold text-[color:var(--text-primary)]">
          {hover
            ? `${hover.a} y ${hover.b}: ${hover.n} ${hover.n === 1 ? "vez" : "veces"}`
            : "Pasa el cursor por una celda."}
        </span>
      </figcaption>
      <div className="flex items-center gap-2 text-xs text-muted" aria-hidden>
        <span>0</span>
        <span
          className="inline-block h-3 w-3 rounded-sm"
          style={{ background: "var(--surface-1)", border: "1px solid var(--grid)" }}
        />
        {STEPS.map((s) => (
          <span key={s} className="inline-block h-3 w-5 rounded-sm" style={{ background: `var(${s})` }} />
        ))}
        <span>{max} veces</span>
      </div>
      <div className="overflow-x-auto">
        <svg
          width={size}
          height={size}
          role="img"
          aria-label="Mapa de calor de parejas"
          onMouseLeave={() => setHover(null)}
        >
          {labels.map((l, i) =>
            i % (n > 30 ? 5 : 1) === 0 || i === n - 1 ? (
              <g key={l}>
                <text x={pad - 4} y={pad + i * cell + cell - 2} textAnchor="end" fontSize={9} fill="var(--text-muted)">
                  {l}
                </text>
                <text
                  x={pad + i * cell + cell / 2}
                  y={pad - 4}
                  textAnchor="start"
                  fontSize={9}
                  fill="var(--text-muted)"
                  transform={`rotate(-60 ${pad + i * cell + cell / 2} ${pad - 4})`}
                >
                  {l}
                </text>
              </g>
            ) : null,
          )}
          {labels.map((a, i) =>
            labels.slice(0, i).map((b, j) => {
              const v = counts.get(`${a}|${b}`) ?? 0;
              const s = step(v);
              return (
                <rect
                  key={`${i}-${j}`}
                  x={pad + j * cell}
                  y={pad + i * cell}
                  width={cell - 1}
                  height={cell - 1}
                  rx={2}
                  fill={s ? `var(${s})` : "var(--surface-1)"}
                  stroke="var(--grid)"
                  strokeWidth={s ? 0 : 0.5}
                  onMouseEnter={() => setHover({ a: b, b: a, n: v })}
                />
              );
            }),
          )}
        </svg>
      </div>
      <p className="sr-only">Las cifras completas están en la tabla de las 10 parejas más frecuentes.</p>
      <details className="text-sm" open={false}>
        <summary className="cursor-pointer text-secondary">Las 10 parejas más frecuentes</summary>
        <table className="data mt-2">
          <thead>
            <tr>
              <th>Pareja</th>
              <th>Veces</th>
            </tr>
          </thead>
          <tbody>
            {top.map(([a, b, v]) => (
              <tr key={`${a}-${b}`}>
                <td>
                  {a} y {b}
                </td>
                <td>{v}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  );
}
