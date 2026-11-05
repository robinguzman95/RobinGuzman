import Link from "next/link";
import { connection } from "next/server";
import { Suspense } from "react";
import { Balls } from "@/components/Balls";
import { CopyButton } from "@/components/CopyButton";
import { ApiDown, Loading, OddsNotice } from "@/components/OddsNotice";
import { safe, type PickEval, type PicksOut } from "@/lib/api";
import { getPicks } from "@/lib/data";
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
];

const money = (x: number) => `$${num(x)}`;
const pct = (r: number) => `${num(r * 100, 0)} %`;

type Props = { searchParams: Promise<{ juego?: string; ventana?: string }> };

export default function AnalizadorPage(props: Props) {
  return (
    <div className="space-y-8">
      <header className="space-y-3">
        <h1 className="text-3xl font-bold">Analizador de jugadas</h1>
        <p className="max-w-3xl text-secondary">
          Jugadas armadas con lo que más ha salido: los números calientes, los que se repiten en todas las épocas, los
          que además tienen la forma típica de un resultado ganador, la pareja más repetida y los que llevan más tiempo
          sin salir. Abajo verás, con los premios reales que pagó Baloto, cómo les habría ido.
        </p>
      </header>
      <Suspense fallback={<Loading what="el análisis" />}>
        <Content {...props} />
      </Suspense>
    </div>
  );
}

async function Content({ searchParams }: Props) {
  await connection();
  const { juego = "baloto", ventana = "12m" } = await searchParams;
  const code = GAMES.some((g) => g.code === juego) ? juego : "baloto";
  const w = WINDOWS.some((x) => x.value === ventana) ? ventana : "12m";
  const data = await safe(getPicks(code, w));
  if (!data) return <ApiDown />;

  return (
    <>
      <nav className="flex flex-wrap gap-2 text-sm" aria-label="juego">
        {GAMES.map((g) => (
          <Link
            key={g.code}
            href={`/analizador?juego=${g.code}&ventana=${w}`}
            aria-current={g.code === code ? "page" : undefined}
            className={`btn-ghost ${g.code === code ? "font-semibold" : "text-secondary"}`}
          >
            {g.name}
          </Link>
        ))}
      </nav>
      <nav className="flex flex-wrap gap-2 text-sm" aria-label="ventana de tiempo">
        {WINDOWS.map((x) => (
          <Link
            key={x.value}
            href={`/analizador?juego=${code}&ventana=${x.value}`}
            aria-current={x.value === w ? "true" : undefined}
            className={`btn-ghost ${x.value === w ? "font-semibold" : "text-secondary"}`}
          >
            {x.label}
          </Link>
        ))}
      </nav>

      <OddsNotice odds={data.odds} name={data.name}>
        {data.notice}
      </OddsNotice>

      <Suggestions data={data} />
      {data.evaluation && <Evaluation data={data} />}

      <p className="text-sm text-secondary">
        ¿Quieres ver todas las frecuencias, las parejas y las pruebas estadísticas?{" "}
        <Link className="link" href={`/${code}?window=${w}`}>
          Estadísticas de {data.name} →
        </Link>
      </p>
    </>
  );
}

function Suggestions({ data }: { data: PicksOut }) {
  // Agrupa criterios que llevan a la misma jugada.
  const groups = new Map<string, PicksOut["picks"]>();
  for (const p of data.picks) groups.set(p.text, [...(groups.get(p.text) ?? []), p]);
  const s = data.shape;
  return (
    <section className="space-y-3">
      <h2 className="text-xl font-semibold">Jugadas para el próximo sorteo</h2>
      <p className="text-sm text-secondary">
        Armadas con {num(data.n_draws)} sorteos ({dateEs(data.date_from)} → {dateEs(data.date_to)}, último #
        {data.last_draw}). Forma típica de un resultado: suma entre {s.sum_low} y {s.sum_high}, {s.evens.join(" o ")}{" "}
        números pares y {s.highs.join(" o ")} números de {s.high_from} en adelante.
      </p>
      <ol className="space-y-3">
        {[...groups.entries()].map(([text, ps]) => (
          <li key={text} className="card space-y-3 p-4">
            <div className="flex flex-wrap items-center gap-3">
              <h3 className="font-semibold">{ps.map((p) => p.label).join(" · ")}</h3>
              {ps.length > 1 && <span className="text-xs text-muted">({ps.length} criterios coinciden)</span>}
            </div>
            <div className="flex flex-wrap items-center gap-4">
              <Balls balls={ps[0].balls} extra={ps[0].extra} />
              <CopyButton text={text} />
            </div>
            <ul className="space-y-1 text-sm text-secondary">
              {ps.map((p) => (
                <li key={p.criterion}>{p.reason}</li>
              ))}
            </ul>
          </li>
        ))}
      </ol>
    </section>
  );
}

function Evaluation({ data }: { data: PicksOut }) {
  const e = data.evaluation!;
  const byCrit = new Map(e.in_sample.map((x) => [x.criterion, x]));
  const t = e.hits_threshold;
  return (
    <section className="card space-y-4 p-5">
      <h2 className="text-xl font-semibold">¿Cómo les habría ido? Prueba con premios reales</h2>
      <p className="text-secondary">
        Cada jugada se juega en los {e.test_draws} sorteos del último año ({dateEs(e.test_from)} → {dateEs(e.test_to)}),
        a {money(e.price)} cada uno ({money(e.price * e.test_draws)} en total), y se suma lo que habría pagado{" "}
        {data.name} (premios antes de impuestos). Como referencia, {num(e.random.sims)} jugadas al azar recuperan entre{" "}
        {pct(e.random.p5_return)} y {pct(e.random.p95_return)} (la mitad, menos de {pct(e.random.median_return)}) y
        logran {t} o más aciertos {num(e.random.mean_hits_3plus, 1)} veces en promedio.
      </p>

      <div className="overflow-x-auto">
        <table className="data">
          <thead>
            <tr>
              <th rowSpan={2}>Criterio</th>
              <th colSpan={4}>Armada con lo que se sabía antes (prueba justa)</th>
              <th colSpan={2}>Armada mirando el mismo año (optimista)</th>
            </tr>
            <tr>
              <th>Jugada</th>
              <th>Recuperó</th>
              <th>{t}+ aciertos</th>
              <th>Mejor que el azar</th>
              <th>Recuperó</th>
              <th>Mejor que el azar</th>
            </tr>
          </thead>
          <tbody>
            {e.out_of_sample.map((o: PickEval) => {
              const i = byCrit.get(o.criterion);
              return (
                <tr key={o.criterion}>
                  <td>{o.label}</td>
                  <td className="whitespace-nowrap">{o.text}</td>
                  <td>
                    {money(o.won)} ({pct(o.return)})
                  </td>
                  <td>{o.hits_3plus} veces</td>
                  <td>{pct(o.percentile_vs_random)} de las jugadas</td>
                  <td>{i ? `${money(i.won)} (${pct(i.return)})` : "—"}</td>
                  <td>{i ? `${pct(i.percentile_vs_random)} de las jugadas` : "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="space-y-2 text-sm text-secondary">
        <p>
          <strong>Cómo leerlo:</strong> la columna de la derecha arma la jugada sabiendo qué salió durante el año, por
          eso casi siempre se ve muy bien. La prueba justa es la de la izquierda: la jugada que habrías elegido con los
          datos de antes ({e.built_until ? `hasta ${dateEs(e.built_until)}` : "antes del periodo"}), jugada en los
          sorteos que vinieron después.
        </p>
        <p>
          Si un criterio realmente anticipara resultados, en la prueba justa quedaría por encima de casi todas las
          jugadas al azar en todos los juegos. Lo que se ve es que los números calientes de un año no se repiten al
          siguiente: unas veces quedan arriba y otras abajo, como cualquier jugada. La probabilidad del premio mayor es{" "}
          {data.odds.jackpot_odds} con cualquiera de ellas.
        </p>
      </div>
    </section>
  );
}
