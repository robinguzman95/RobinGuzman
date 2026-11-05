"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { num } from "@/lib/format";

type Point = { jackpot: number; ev: number; return: number };

const billions = (j: number) => `$${num(j / 1e9, j < 1e10 ? 1 : 0)} mil M`;
const pct = (r: number) => `${num(r * 100, 0)} %`;

/** Retorno esperado (VE / precio) según el acumulado. La línea de 100 % es "recuperar lo jugado". */
export function EVChart({
  curve,
  price,
  current,
  currentReturn,
  maxObserved,
}: {
  curve: Point[];
  price: number;
  current: number | null;
  currentReturn: number | null;
  maxObserved: number | null;
}) {
  const maxR = Math.max(1.05, ...curve.map((c) => c.return));
  return (
    <figure className="space-y-2">
      <figcaption className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-secondary">
        <span className="flex items-center gap-2">
          <span aria-hidden className="inline-block h-0.5 w-5" style={{ background: "var(--series-1)" }} />
          de cada ${num(price)} jugados, cuánto vuelve en promedio
        </span>
        <span className="flex items-center gap-2">
          <span aria-hidden className="inline-block h-0.5 w-5" style={{ background: "var(--text-secondary)" }} />
          100 % = recuperar lo jugado
        </span>
      </figcaption>
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={curve} margin={{ top: 12, right: 16, bottom: 8, left: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--grid)" />
            <XAxis
              dataKey="jackpot"
              type="number"
              domain={["dataMin", "dataMax"]}
              tickFormatter={billions}
              tick={{ fill: "var(--text-muted)", fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: "var(--axis)" }}
              minTickGap={30}
            />
            <YAxis
              dataKey="return"
              domain={[0, Math.ceil(maxR * 10) / 10]}
              tickFormatter={pct}
              tick={{ fill: "var(--text-muted)", fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              width={44}
            />
            <Tooltip
              contentStyle={{
                background: "var(--surface-1)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                color: "var(--text-primary)",
              }}
              labelFormatter={(j) => `Acumulado ${billions(Number(j))}`}
              formatter={(v, _n, item) => [
                `${pct(Number(v))} ($${num((item.payload as Point).ev)} de $${num(price)})`,
                "vuelve en promedio",
              ]}
            />
            <ReferenceLine y={1} stroke="var(--text-secondary)" strokeWidth={1.5} />
            {maxObserved !== null && (
              <ReferenceLine
                x={maxObserved}
                stroke="var(--axis)"
                strokeWidth={1.5}
                label={{
                  value: "mayor acumulado visto → extrapolación",
                  position: "insideTopLeft",
                  fill: "var(--text-muted)",
                  fontSize: 11,
                }}
              />
            )}
            <Line dataKey="return" stroke="var(--series-1)" strokeWidth={2} dot={false} isAnimationActive={false} />
            {current !== null && currentReturn !== null && (
              <ReferenceDot
                x={current}
                y={currentReturn}
                r={5}
                fill="var(--series-1)"
                stroke="var(--surface-1)"
                strokeWidth={2}
                label={{ value: "hoy", position: "top", fill: "var(--text-primary)", fontSize: 12 }}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <details className="text-sm">
        <summary className="cursor-pointer text-secondary">Ver como tabla</summary>
        <div className="mt-2 max-h-64 overflow-auto">
          <table className="data">
            <thead>
              <tr>
                <th>Acumulado</th>
                <th>Vuelve en promedio</th>
                <th>Retorno</th>
              </tr>
            </thead>
            <tbody>
              {curve
                .filter((_, i) => i % 5 === 0)
                .map((c) => (
                  <tr key={c.jackpot}>
                    <td>{billions(c.jackpot)}</td>
                    <td>${num(c.ev)}</td>
                    <td>{pct(c.return)}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  );
}
