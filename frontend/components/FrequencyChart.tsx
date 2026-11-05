"use client";

import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { num } from "@/lib/format";

type Row = { label: string; count: number };

/** Barras de frecuencia: una sola serie (slot 1) y una línea de referencia con lo esperado por azar. */
export function FrequencyChart({ rows, expected, title }: { rows: Row[]; expected: number; title: string }) {
  const dense = rows.length > 20;
  return (
    <figure className="space-y-2">
      <figcaption className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-secondary">
        <span>{title}</span>
        <span className="flex items-center gap-2">
          <span aria-hidden className="inline-block h-0.5 w-5" style={{ background: "var(--text-secondary)" }} />
          esperado por azar: {num(expected, 1)}
        </span>
      </figcaption>
      <div className={`${dense ? "h-80" : "h-72"} w-full`}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ top: 16, right: 8, bottom: 8, left: 0 }} barCategoryGap={2}>
            <CartesianGrid vertical={false} stroke="var(--grid)" />
            <XAxis
              dataKey="label"
              tick={{ fill: "var(--text-muted)", fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: "var(--axis)" }}
              interval={dense ? "preserveStartEnd" : 0}
              minTickGap={2}
              angle={dense ? -90 : 0}
              textAnchor={dense ? "end" : "middle"}
              height={dense ? Math.max(30, 7 * Math.max(...rows.map((r) => r.label.length))) : 24}
            />
            <YAxis
              allowDecimals={false}
              tick={{ fill: "var(--text-muted)", fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              width={32}
            />
            <Tooltip
              cursor={{ fill: "var(--band-fill)" }}
              contentStyle={{
                background: "var(--surface-1)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                color: "var(--text-primary)",
              }}
              formatter={(v) => [`${v} veces`, "salió"]}
              labelFormatter={(l) => `Balota ${l}`}
            />
            <Bar dataKey="count" fill="var(--series-1)" radius={[4, 4, 0, 0]} isAnimationActive={false} />
            <ReferenceLine y={expected} stroke="var(--text-secondary)" strokeWidth={1.5} ifOverflow="extendDomain" />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <details className="text-sm">
        <summary className="cursor-pointer text-secondary">Ver como tabla</summary>
        <div className="mt-2 max-h-64 overflow-auto">
          <table className="data">
            <thead>
              <tr>
                <th>Balota</th>
                <th>Veces</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.label}>
                  <td>{r.label}</td>
                  <td>{r.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  );
}
