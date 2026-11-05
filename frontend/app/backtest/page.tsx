import { connection } from "next/server";
import { Suspense } from "react";
import { BacktestRunner } from "@/components/BacktestRunner";
import { ApiDown, Loading } from "@/components/OddsNotice";
import { safe } from "@/lib/api";
import { getSummary } from "@/lib/data";
import { dateEs, num, pValue, STRATEGY_LABEL } from "@/lib/format";

const NAMES: Record<string, string> = {
  baloto: "Baloto",
  revancha: "Revancha",
  miloto: "MiLoto",
  colorloto: "ColorLoto",
};

export default function BacktestPage() {
  return (
    <Suspense fallback={<Loading what="el backtest" />}>
      <BacktestContent />
    </Suspense>
  );
}

async function BacktestContent() {
  await connection();
  const summary = await safe(getSummary());
  if (!summary) return <ApiDown />;
  const winners = summary.rows.filter((r) => r.significant_bonferroni);
  const nominal = summary.rows.filter((r) => r.above_p95 && r.p_value < summary.alpha);
  const primary = summary.rows.filter((r) => r.primary);

  return (
    <div className="space-y-8">
      <header className="space-y-3">
        <h1 className="text-3xl font-bold">Backtest: ¿alguna estrategia le gana al azar?</h1>
        <p className="max-w-3xl text-secondary">
          Para cada sorteo, la estrategia solo ve los sorteos anteriores (nunca el que se evalúa). Sus aciertos se
          comparan con 10.000 jugadas al azar sobre los mismos sorteos. Si una estrategia sirviera, su línea quedaría
          por encima de la banda gris.
        </p>
      </header>

      <section className="card space-y-2 p-5" aria-label="veredicto">
        <p className="text-2xl font-semibold" style={{ color: winners.length ? "var(--serious)" : "var(--good)" }}>
          <span aria-hidden>{winners.length ? "⚠ " : "✓ "}</span>
          {winners.length
            ? `${winners.length} combinación(es) superan al azar tras la corrección`
            : "Ninguna estrategia le gana al azar"}
        </p>
        <p className="text-secondary">
          {summary.combinations} combinaciones (5 estrategias × 3 ventanas × 4 juegos), corrección de Bonferroni: α =
          0,05 / {summary.combinations} = {num(summary.alpha_bonferroni, 5)}. Sin corregir,{" "}
          {nominal.length === 1 ? "1 combinación queda" : `${nominal.length} combinaciones quedan`} “por encima”, y por
          puro azar se esperaban unas {num(summary.alpha * summary.combinations, 0)}: probar muchas estrategias a la vez
          hace que alguna parezca ganar por suerte. Actualizado el {dateEs(summary.generated)}.
        </p>
      </section>

      <BacktestRunner primaryWindow={summary.primary_window} />

      <section className="card space-y-3 p-5">
        <h2 className="text-xl font-semibold">Ventana principal ({summary.primary_window} sorteos)</h2>
        <div className="overflow-x-auto">
          <table className="data">
            <thead>
              <tr>
                <th>Juego</th>
                <th>Estrategia</th>
                <th>Sorteos</th>
                <th>Aciertos/sorteo</th>
                <th>Azar p5–p95</th>
                <th>p-valor</th>
                <th>Resultado</th>
              </tr>
            </thead>
            <tbody>
              {primary.map((r) => (
                <tr key={`${r.game}-${r.strategy}`}>
                  <td>{NAMES[r.game]}</td>
                  <td>{STRATEGY_LABEL[r.strategy] ?? r.strategy}</td>
                  <td>{r.n_draws}</td>
                  <td>{num(r.avg_hits, 3)}</td>
                  <td>
                    {num(r.baseline_p5, 3)}–{num(r.baseline_p95, 3)}
                  </td>
                  <td>{pValue(r.p_value)}</td>
                  <td>
                    {r.significant_bonferroni
                      ? "le gana al azar"
                      : r.above_p95 && r.p_value < summary.alpha
                        ? "sobre p95, no significativo tras Bonferroni"
                        : "dentro de la banda"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-sm text-secondary">
          Las ventanas de 50 y 200 sorteos son análisis de sensibilidad; la de {summary.primary_window} se declaró antes
          de ver los resultados.
        </p>
      </section>
    </div>
  );
}
