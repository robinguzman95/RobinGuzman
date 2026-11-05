import Link from "next/link";
import { connection } from "next/server";
import { Suspense } from "react";
import { ApiDown, Loading, OddsNotice } from "@/components/OddsNotice";
import { ProbabilityChart } from "@/components/ProbabilityChart";
import { safe, type MLOut, type MLUnitEval } from "@/lib/api";
import { getML } from "@/lib/data";
import { dateEs, num, pValue } from "@/lib/format";

const GAMES = [
  { code: "baloto", name: "Baloto" },
  { code: "revancha", name: "Revancha" },
  { code: "miloto", name: "MiLoto" },
  { code: "colorloto", name: "ColorLoto" },
];
const MODELS = [
  { code: "gb", name: "Gradient boosting (tipo LightGBM)" },
  { code: "logit", name: "Regresión logística" },
];

const pct = (x: number, d = 1) => `${num(x * 100, d)} %`;
type Props = { searchParams: Promise<{ juego?: string; modelo?: string }> };

export default function MLPage(props: Props) {
  return (
    <div className="space-y-8">
      <header className="space-y-3">
        <h1 className="text-3xl font-bold">Modelo de machine learning</h1>
        <p className="max-w-3xl text-secondary">
          Un modelo aprende, con la historia de cada balota (cuánto salió en los últimos 10, 25, 50 y 100 sorteos, hace
          cuánto no sale y si salió en el sorteo anterior), qué tan probable es que salga en el próximo. Luego se pone a
          prueba como en la vida real: se entrena solo con el pasado y se le pide adivinar los sorteos que vienen.
        </p>
      </header>
      <Suspense fallback={<Loading what="el modelo (entrenarlo puede tardar unos segundos)" />}>
        <Content {...props} />
      </Suspense>
    </div>
  );
}

async function Content({ searchParams }: Props) {
  await connection();
  const { juego = "baloto", modelo = "gb" } = await searchParams;
  const code = GAMES.some((g) => g.code === juego) ? juego : "baloto";
  const model = MODELS.some((m) => m.code === modelo) ? modelo : "gb";
  const d = await safe(getML(code, model));
  if (!d) return <ApiDown />;
  const main = d.units.main;
  const extra = d.units.extra;

  return (
    <>
      <nav className="flex flex-wrap gap-2 text-sm" aria-label="juego">
        {GAMES.map((g) => (
          <Link
            key={g.code}
            href={`/ml?juego=${g.code}&modelo=${model}`}
            aria-current={g.code === code ? "page" : undefined}
            className={`btn-ghost ${g.code === code ? "font-semibold" : "text-secondary"}`}
          >
            {g.name}
          </Link>
        ))}
      </nav>
      <nav className="flex flex-wrap gap-2 text-sm" aria-label="modelo">
        {MODELS.map((m) => (
          <Link
            key={m.code}
            href={`/ml?juego=${code}&modelo=${m.code}`}
            aria-current={m.code === model ? "true" : undefined}
            className={`btn-ghost ${m.code === model ? "font-semibold" : "text-secondary"}`}
          >
            {m.name}
          </Link>
        ))}
      </nav>

      <OddsNotice odds={d.odds} name={d.name}>
        {d.notice}
      </OddsNotice>

      <section className="card space-y-4 p-5">
        <h2 className="text-xl font-semibold">Probabilidades para el próximo sorteo</h2>
        <p className="text-secondary">
          Entrenado con todos los sorteos hasta el #{d.last_draw}. Las {main.top.length} balotas con más probabilidad
          según el modelo: <strong>{main.top.map((t) => `${t.label} (${pct(t.probability)})`).join(", ")}</strong>
          {extra && (
            <>
              {" "}
              · superbalota: <strong>{extra.top.map((t) => `${t.label} (${pct(t.probability)})`).join(", ")}</strong>
            </>
          )}
          . Por puro azar cada balota tiene {pct(main.base)}
          {extra ? ` y cada superbalota ${pct(extra.base)}` : ""}: fíjate qué tan cerca de esa línea quedan las barras.
        </p>
        <ProbabilityChart rows={main.probabilities} base={main.base} title={d.model_name} />
        {extra && <ProbabilityChart rows={extra.probabilities} base={extra.base} title="Superbalota" />}
        <p className="text-sm">
          ¿Quieres jugadas con estas balotas?{" "}
          <Link className="link" href="/generador">
            Genéralas en el Generador → modo «Modelo de ML»
          </Link>
        </p>
      </section>

      {d.evaluation && <Evaluation d={d} />}
    </>
  );
}

function verdict(e: MLUnitEval) {
  // Según el IC 95 % de la mejora en log-loss: todo > 0 = mejor; todo < 0 = peor; si incluye 0, igual.
  if (e.delta_ci[0] > 0) return "predice mejor que el azar";
  if (e.delta_ci[1] < 0) return "predice peor que el azar";
  return "igual que el azar";
}

function Evaluation({ d }: { d: MLOut }) {
  const ev = d.evaluation!;
  const rows: { unit: string; e: MLUnitEval; name: string }[] = [];
  for (const [unit, kinds] of Object.entries(ev.units)) {
    for (const m of MODELS) if (kinds[m.code]) rows.push({ unit, e: kinds[m.code], name: m.name });
  }
  return (
    <section className="card space-y-4 p-5">
      <h2 className="text-xl font-semibold">¿Funciona? Prueba sin mirar al futuro</h2>
      <p className="text-secondary">
        Se usaron {num(ev.test_draws)} sorteos de prueba ({dateEs(ev.test_from)} → {dateEs(ev.test_to)}). Cada 25
        sorteos el modelo se reentrena solo con los anteriores y adivina los 25 siguientes. Se mide de dos formas: si
        sus probabilidades son más acertadas que decir «todas tienen la misma» (puntaje de habilidad, &gt; 0 = mejor), y
        cuántas balotas acierta jugando sus favoritas.
      </p>
      <div className="overflow-x-auto">
        <table className="data">
          <thead>
            <tr>
              <th>Qué predice</th>
              <th>Modelo</th>
              <th>Habilidad</th>
              <th>IC 95 %</th>
              <th>Aciertos por sorteo</th>
              <th>Azar (90 %)</th>
              <th>p-valor</th>
              <th>Resultado</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(({ unit, e, name }) => (
              <tr key={`${unit}-${e.kind}`}>
                <td>{unit === "main" ? "Balotas" : "Superbalota"}</td>
                <td>{name}</td>
                <td>{pct(e.skill, 2)}</td>
                <td>
                  {num(e.delta_ci[0], 4)} a {num(e.delta_ci[1], 4)}
                </td>
                <td>{num(e.avg_hits, 3)}</td>
                <td>
                  {num(e.base_p5, 3)}–{num(e.base_p95, 3)}
                </td>
                <td>{pValue(e.p_value)}</td>
                <td>{verdict(e)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="space-y-2 text-sm text-secondary">
        <p>
          <strong>Cómo leerlo:</strong> si el modelo hubiera encontrado algo, la habilidad sería positiva con un
          intervalo (IC) completamente por encima de 0, y los aciertos estarían por encima de la banda del azar. El
          gradient boosting, el más sofisticado, sale incluso un poco <em>peor</em> que el azar: aprende coincidencias
          del pasado que no se repiten (sobreajuste).
        </p>
        <p>
          <strong>¿Y si el modelo simplemente no sirve?</strong> Lo probamos: en sorteos simulados con un patrón
          escondido (balotas que tienden a repetir), los mismos modelos lo descubren y superan con claridad la banda del
          azar. Es decir, el modelo funciona; lo que no hay en los sorteos reales es un patrón que aprender.
        </p>
      </div>
    </section>
  );
}
