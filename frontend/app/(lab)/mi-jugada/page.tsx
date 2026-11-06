"use client";

import { useState } from "react";
import { Balls } from "@/components/Balls";
import { OddsNotice } from "@/components/OddsNotice";
import { PlayDetails } from "@/components/PlayDetails";
import { api, type S } from "@/lib/api";
import { dateEs, num } from "@/lib/format";

const GAMES = {
  baloto: { name: "Baloto", k: 5, max: 43, extra: 16, colors: null },
  revancha: { name: "Revancha", k: 5, max: 43, extra: 16, colors: null },
  miloto: { name: "MiLoto", k: 5, max: 39, extra: null, colors: null },
  colorloto: {
    name: "ColorLoto",
    k: 6,
    max: 7,
    extra: null,
    colors: ["amarillo", "azul", "rojo", "verde", "blanco", "negro"],
  },
} as const;
type Code = keyof typeof GAMES;
const WINDOWS = [
  { value: "12m", label: "Últimos 12 meses" },
  { value: "100", label: "Últimos 100 sorteos" },
  { value: "all", label: "Todo el histórico" },
] as const;
type Window = (typeof WINDOWS)[number]["value"];

const empty = (code: Code) => Array.from({ length: GAMES[code].k }, () => ({ number: "", color: "" }));

export default function MiJugadaPage() {
  const [code, setCode] = useState<Code>("baloto");
  const [balls, setBalls] = useState(empty("baloto"));
  const [extra, setExtra] = useState("");
  const [window, setWindow] = useState<Window>("12m");
  const [out, setOut] = useState<S["AnalyzeOut"] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const g = GAMES[code];

  function changeGame(c: Code) {
    setCode(c);
    setBalls(empty(c));
    setExtra("");
    setOut(null);
    setError(null);
  }

  async function run() {
    setError(null);
    if (balls.some((b) => b.number === "") || (g.extra && extra === "") || (g.colors && balls.some((b) => !b.color))) {
      setError(`Completa los ${g.k} números${g.colors ? " con su color" : ""}${g.extra ? " y la superbalota" : ""}.`);
      return;
    }
    setLoading(true);
    try {
      setOut(
        await api.analyze({
          game: code,
          balls: balls.map((b) => ({ number: Number(b.number), color: g.colors ? b.color : null })),
          extra: g.extra ? Number(extra) : null,
          window,
        }),
      );
    } catch (e) {
      setOut(null);
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <header className="space-y-3">
        <p className="eyebrow">Herramientas · Mi jugada</p>
        <h1 className="text-3xl font-bold tracking-tight md:text-4xl">Revisar mi jugada</h1>
        <p className="max-w-3xl text-secondary">
          Escribe los números que piensas jugar y te mostramos su resumen: cuántas veces ha salido cada uno, la
          probabilidad según el modelo de machine learning, la forma de la jugada, sus parejas frecuentes, qué tan
          popular es, cuánto habría ganado el último año y si alguna vez salió.
        </p>
      </header>

      <form
        className="card space-y-4 p-5 text-sm"
        onSubmit={(e) => {
          e.preventDefault();
          run();
        }}
      >
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1">
            Juego
            <select className="field" value={code} onChange={(e) => changeGame(e.target.value as Code)}>
              {(Object.keys(GAMES) as Code[]).map((c) => (
                <option key={c} value={c}>
                  {GAMES[c].name}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1">
            Comparar con
            <select className="field" value={window} onChange={(e) => setWindow(e.target.value as Window)}>
              {WINDOWS.map((w) => (
                <option key={w.value} value={w.value}>
                  {w.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <fieldset className="space-y-2">
          <legend className="font-semibold">
            Tus {g.k} números (del 1 al {g.max}
            {g.colors ? ", cada uno con su color" : ", sin repetir"})
          </legend>
          <div className="flex flex-wrap gap-3">
            {balls.map((b, i) => (
              <div key={i} className="flex flex-col gap-1">
                <input
                  aria-label={`Número ${i + 1}`}
                  className="field w-20 text-center text-base"
                  type="number"
                  inputMode="numeric"
                  min={1}
                  max={g.max}
                  value={b.number}
                  onChange={(e) =>
                    setBalls(balls.map((x, j) => (j === i ? { ...x, number: e.target.value.slice(0, 2) } : x)))
                  }
                />
                {g.colors && (
                  <select
                    aria-label={`Color del número ${i + 1}`}
                    className="field w-20"
                    value={b.color}
                    onChange={(e) => setBalls(balls.map((x, j) => (j === i ? { ...x, color: e.target.value } : x)))}
                  >
                    <option value="">color</option>
                    {g.colors.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                )}
              </div>
            ))}
            {g.extra && (
              <label className="flex flex-col gap-1">
                <span className="sr-only">Superbalota</span>
                <input
                  aria-label="Superbalota"
                  className="field w-20 text-center text-base"
                  style={{ background: "var(--text-primary)", color: "var(--surface-1)" }}
                  type="number"
                  inputMode="numeric"
                  min={1}
                  max={g.extra}
                  placeholder="SB"
                  value={extra}
                  onChange={(e) => setExtra(e.target.value.slice(0, 2))}
                />
                <span className="text-xs text-muted">superbalota (1–{g.extra})</span>
              </label>
            )}
          </div>
        </fieldset>

        <button className="btn" type="submit" disabled={loading}>
          {loading ? "Analizando…" : "Analizar mi jugada"}
        </button>
      </form>

      {error && (
        <p role="alert" style={{ color: "var(--serious)" }}>
          ⚠ {error}
        </p>
      )}

      {out && <Result out={out} extraName={g.extra ? "superbalota" : null} />}
    </div>
  );
}

function Result({ out, extraName }: { out: S["AnalyzeOut"]; extraName: string | null }) {
  const p = out.play;
  const h = out.all_history;
  const best = h.best[0];
  return (
    <div className="space-y-4">
      <OddsNotice odds={out.odds} name={out.name}>
        {out.notice}
      </OddsNotice>
      <section className="card space-y-3 p-4">
        <div className="flex flex-wrap items-center gap-4">
          <span className="text-sm font-semibold text-muted">Tu jugada</span>
          <Balls balls={p.balls} extra={p.extra} />
        </div>
        <PlayDetails play={p} extraName={extraName} show={{ ml: true, stats: true, popularity: true }} />
        <div className="space-y-2 text-sm">
          <p>
            <span className="font-semibold">En todo el histórico</span> ({num(h.draws)} sorteos, {dateEs(h.date_from)} →{" "}
            {dateEs(h.date_to)}):{" "}
            {h.exact_matches.length > 0 ? (
              <strong>
                esta combinación exacta ya salió{" "}
                {h.exact_matches.map((m) => `en el sorteo #${m.draw_number} (${dateEs(m.draw_date)})`).join(", ")}
              </strong>
            ) : (
              "esta combinación exacta nunca ha salido"
            )}
            .{" "}
            {best && (
              <>
                Su mejor resultado fue <strong>{best.hits} aciertos</strong>
                {best.extra_hit ? " con superbalota" : ""} en el sorteo #{best.draw_number} ({dateEs(best.draw_date)}).
              </>
            )}
          </p>
          <table className="data max-w-md">
            <thead>
              <tr>
                <th>Aciertos</th>
                <th>Veces en el histórico</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(h.hits)
                .sort((a, b) => Number(b[0]) - Number(a[0]))
                .map(([k, v]) => (
                  <tr key={k}>
                    <td>{k}</td>
                    <td>{num(v)}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </section>
      <p className="text-xs text-muted">
        «Cuánto habría ganado» usa los premios reales que pagó {out.name} en cada sorteo del último año (antes de
        impuestos). El modelo de ML, probado sin mirar al futuro, no predice mejor que el azar. El puntaje de
        popularidad es una estimación heurística.
      </p>
    </div>
  );
}
