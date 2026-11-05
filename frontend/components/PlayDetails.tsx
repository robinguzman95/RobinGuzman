import type { S } from "@/lib/api";
import { dateEs, num } from "@/lib/format";

const money = (x: number) => `$${num(x)}`;
const pct = (r: number) => `${num(r * 100, 0)} %`;

/** Resumen de una jugada: probabilidad según el modelo, veces que salió cada balota, forma,
 *  parejas frecuentes, cuánto habría ganado el último año y popularidad. Lo usan el generador y
 *  "Revisar mi jugada". */
export function PlayDetails({
  play: p,
  extraName,
  show,
}: {
  play: S["PlayOut"];
  extraName: string | null;
  show: { ml?: boolean; stats?: boolean; popularity?: boolean };
}) {
  const s = p.stats;
  const h = s?.history;
  return (
    <>
      {show.ml && p.ml_probabilities && p.ml_base != null && (
        <p className="text-sm">
          <span className="font-semibold">Probabilidad según el modelo de ML</span> (azar: {num(p.ml_base * 100, 1)} %
          cada una):{" "}
          {p.balls
            .map(
              (b, j) => `${b.color ? `${b.number}-${b.color}` : b.number} (${num(p.ml_probabilities![j] * 100, 1)} %)`,
            )
            .join(", ")}
          {extraName && p.extra != null && p.ml_extra_probability != null && (
            <>
              {" "}
              · {extraName} {String(p.extra).padStart(2, "0")} ({num(p.ml_extra_probability * 100, 1)} %; azar 6,3 %)
            </>
          )}
          .
        </p>
      )}

      {show.stats && s && (
        <div className="grid gap-x-6 gap-y-2 text-sm md:grid-cols-2">
          <p>
            <span className="font-semibold">Veces que salió cada una</span> en {num(s.window_draws)} sorteos (lo normal:{" "}
            {num(s.expected_count, 1)}): {s.counts.map((c) => `${c.label} (${c.count})`).join(", ")}
            {extraName && p.extra != null && s.extra_count != null && s.extra_expected != null && (
              <>
                {" "}
                · {extraName} {String(p.extra).padStart(2, "0")} ({s.extra_count}; lo normal {num(s.extra_expected, 1)})
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
              <span className="font-semibold">Jugándola en cada sorteo del último año</span> ({h.draws} sorteos,{" "}
              {dateEs(h.date_from)} → {dateEs(h.date_to)}, {money(h.cost)}): habría ganado{" "}
              <strong>{money(h.won)}</strong> ({pct(h.ret)} de lo jugado) en {h.prize_draws} sorteos; mejor resultado{" "}
              {h.best_hits} aciertos; 3 o más aciertos {h.hits_3plus} {h.hits_3plus === 1 ? "vez" : "veces"}.
            </p>
          )}
        </div>
      )}

      {show.popularity && (
        <p className="text-sm text-secondary">
          <span className="font-semibold text-[color:var(--text-primary)]">Popularidad</span> {p.popularity_score}/100 (
          {p.popularity_level}): qué tanta gente suele jugar combinaciones así
          {p.popularity_reasons.length > 0 ? ` · ${p.popularity_reasons.join("; ")}` : ""}.
        </p>
      )}
    </>
  );
}
