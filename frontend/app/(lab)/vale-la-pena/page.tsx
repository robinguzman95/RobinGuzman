import Link from "next/link";
import { connection } from "next/server";
import { Suspense } from "react";
import { EVChart } from "@/components/EVChart";
import { ApiDown, Loading } from "@/components/OddsNotice";
import { safe, type EVGame } from "@/lib/api";
import { getAllExpectedValue, getExpectedValue } from "@/lib/data";
import { dateEs, num, pValue } from "@/lib/format";

const GAMES = [
  { code: "baloto", name: "Baloto" },
  { code: "revancha", name: "Revancha" },
  { code: "miloto", name: "MiLoto" },
  { code: "colorloto", name: "ColorLoto" },
];

const CATEGORY_LABEL: Record<string, string> = {
  "5+SB": "5 + superbalota (premio mayor)",
  "5": "5 aciertos",
  "4+SB": "4 + superbalota",
  "4": "4 aciertos",
  "3+SB": "3 + superbalota",
  "3": "3 aciertos",
  "2+SB": "2 + superbalota",
  "0+SB": "0 o 1 + superbalota",
  "2": "2 aciertos",
  "6": "6 número y color (premio mayor)",
  "6N": "6 números sin importar color",
  "6C": "6 colores sin importar número",
};

const money = (x: number) => `$${num(x)}`;
const pct = (r: number) => `${num(r * 100, 0)} %`;
const big = (j: number) => `$${num(j / 1e9, j < 1e10 ? 1 : 0)} mil millones`;

type Props = { searchParams: Promise<{ juego?: string }> };

export default function ValePage(props: Props) {
  return (
    <div className="space-y-8">
      <header className="space-y-3">
        <p className="eyebrow">Laboratorio · Valor esperado</p>
        <h1 className="text-3xl font-bold tracking-tight md:text-4xl">¿Vale la pena jugar?</h1>
        <p className="max-w-3xl text-secondary">
          El <strong>valor esperado</strong> es lo que devuelve en promedio un tiquete si se jugara muchísimas veces:
          cada premio multiplicado por su probabilidad, usando los premios reales pagados en el último año, la retención
          del 20 % sobre premios grandes y la probabilidad de tener que repartir el premio mayor.
        </p>
      </header>
      <Suspense fallback={<Loading what="el valor esperado" />}>
        <Content {...props} />
      </Suspense>
    </div>
  );
}

async function Content({ searchParams }: Props) {
  await connection();
  const { juego = "baloto" } = await searchParams;
  const code = GAMES.some((g) => g.code === juego) ? juego : "baloto";
  const [all, g] = await Promise.all([safe(getAllExpectedValue()), safe(getExpectedValue(code))]);
  if (!all || !g) return <ApiDown />;

  return (
    <>
      <section aria-label="resumen" className="grid gap-4 sm:grid-cols-2">
        {GAMES.filter((x) => all.games[x.code]).map((x) => {
          const s = all.games[x.code];
          return (
            <Link
              key={x.code}
              href={`/vale-la-pena?juego=${x.code}`}
              aria-current={x.code === code ? "true" : undefined}
              className={`card block p-5 ${x.code === code ? "ring-2 ring-[color:var(--series-1)]" : ""}`}
            >
              <h2 className="text-lg font-semibold">{x.name}</h2>
              <p className="mt-1 text-sm text-secondary">
                Con el acumulado actual, de cada {money(s.price)} jugados vuelven en promedio
              </p>
              <p className="text-3xl font-semibold">
                {s.ev_current != null ? money(s.ev_current) : "—"}
                <span className="ml-2 text-base font-normal text-secondary">
                  {s.return_current != null ? pct(s.return_current) : ""}
                </span>
              </p>
              <p className="mt-1 text-sm text-secondary">
                Pierdes en promedio {s.ev_current != null ? money(s.price - s.ev_current) : "—"} por jugada.
              </p>
            </Link>
          );
        })}
      </section>

      <Detail g={g} />

      <p className="text-xs text-muted">
        Fuente: tablas de premios publicadas por baloto.com, {g.n_draws} sorteos de {g.name} ({dateEs(g.date_from)} →{" "}
        {dateEs(g.date_to)}). {all.tax.note} Actualizado el {dateEs(all.generated)}.
      </p>
    </>
  );
}

const JACKPOT_CATEGORY: Record<string, string> = { baloto: "5+SB", revancha: "5+SB", miloto: "5", colorloto: "6" };

function Detail({ g }: { g: EVGame }) {
  const jackpot = g.categories.find((c) => c.category === JACKPOT_CATEGORY[g.game]);
  return (
    <>
      <section className="card space-y-4 p-5">
        <h2 className="text-xl font-semibold">{g.name}: retorno según el acumulado</h2>
        <p className="text-secondary">
          Sin contar el premio mayor, cada jugada devuelve en promedio <strong>{money(g.non_jackpot_ev)}</strong> (
          {pct(g.non_jackpot_return)} de {money(g.price)}). El resto depende del acumulado: cuanto más grande, más vale…
          pero también se venden más tiquetes y aumenta la probabilidad de repartirlo.{" "}
          {g.break_even_jackpot ? (
            <>
              El tiquete recuperaría su precio en promedio con un acumulado de{" "}
              <strong>{big(g.break_even_jackpot)}</strong>
              {g.max_observed_jackpot && g.break_even_jackpot > g.max_observed_jackpot && (
                <>
                  , muy por encima del mayor acumulado del último año ({big(g.max_observed_jackpot)}). Es una
                  extrapolación: supone que las ventas siguen creciendo con el premio como hasta ahora
                </>
              )}
              .
            </>
          ) : (
            <strong>Con ningún acumulado el tiquete recupera su precio en promedio</strong>
          )}
          {!g.break_even_jackpot && ": las ventas crecen con el premio y el reparto se come la diferencia."}
        </p>
        {g.curve && (
          <EVChart
            curve={g.curve}
            price={g.price}
            current={g.current_jackpot}
            currentReturn={g.return_current}
            maxObserved={g.max_observed_jackpot}
          />
        )}
        {g.current_jackpot && g.ev_current_unpopular != null && g.ev_current != null && g.p_share_current != null && (
          <p className="text-sm text-secondary">
            Si acertaras el premio mayor hoy ({big(g.current_jackpot)}), la probabilidad de que alguien más también lo
            acierte es de solo {num(g.p_share_current * 100, 1)} %. Por eso una jugada la mitad de popular (como las del
            generador) apenas sube el valor esperado: {money(g.ev_current_unpopular)} en lugar de {money(g.ev_current)}.
            Evitar jugadas populares importa sobre todo en sorteos con muchísimas ventas.
          </p>
        )}
      </section>

      <section className="card space-y-3 p-5">
        <h2 className="text-xl font-semibold">De dónde sale el valor esperado</h2>
        <div className="overflow-x-auto">
          <table className="data">
            <thead>
              <tr>
                <th>Categoría</th>
                <th>Probabilidad</th>
                <th>Premio promedio</th>
                <th>Aporta por jugada</th>
              </tr>
            </thead>
            <tbody>
              {g.categories.map((c) => (
                <tr key={c.category}>
                  <td>{CATEGORY_LABEL[c.category] ?? c.category}</td>
                  <td>1 en {num(c.one_in)}</td>
                  <td>{c.avg_prize ? money(c.avg_prize) : c === jackpot ? "el acumulado" : "sin ganadores"}</td>
                  <td>{c.contribution ? money(c.contribution) : c === jackpot ? "depende del acumulado" : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-sm text-secondary">
          Se venden unas <strong>{g.median_plays ? num(g.median_plays) : "—"}</strong> jugadas por sorteo (mediana
          estimada a partir de los ganadores de cada categoría).
          {g.sales_model.b_per_million > 0 &&
            ` Por cada $1.000 millones más de acumulado se venden unas ${num(g.sales_model.b_per_million * 1000)} jugadas más.`}
        </p>
      </section>

      {g.popularity && (
        <section className="card space-y-3 p-5">
          <h2 className="text-xl font-semibold">¿La gente juega fechas?</h2>
          <p className="text-secondary">
            Si todos jugaran al azar, los ganadores de 3 y 4 aciertos serían los esperados (proporción 1,0) sin importar
            qué números salieron. Cuando salen muchos números ≤ 31 (días del mes), la proporción{" "}
            {g.popularity.spearman_rho > 0 && g.popularity.p_value < 0.05 ? "sube" : "no cambia de forma clara"}{" "}
            (correlación de Spearman {num(g.popularity.spearman_rho, 2)}, p {g.popularity.p_value < 0.001 ? "" : "= "}
            {pValue(g.popularity.p_value)}, {g.popularity.n_draws} sorteos).
          </p>
          <table className="data max-w-md">
            <thead>
              <tr>
                <th>Números ≤ 31 en el resultado</th>
                <th>Sorteos</th>
                <th>Ganadores reales / esperados</th>
              </tr>
            </thead>
            <tbody>
              {g.popularity.groups.map((x) => (
                <tr key={x.low_numbers}>
                  <td>{x.low_numbers} de 5</td>
                  <td>{x.draws}</td>
                  <td>{num(x.ratio, 2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      <section className="card space-y-3 p-5">
        <h2 className="text-xl font-semibold">¿Qué tan seguros estamos de que no hay ventaja?</h2>
        <p className="text-secondary">
          Con {num(g.power.ball_bias.n_draws)} sorteos, si una balota saliera{" "}
          <strong>{pct(g.power.ball_bias.min_relative_bias)} más</strong> de lo normal (unas{" "}
          {num(g.power.ball_bias.biased_count, 0)} veces en lugar de {num(g.power.ball_bias.expected_count, 0)}), la
          prueba de uniformidad lo detectaría el {pct(g.power.ball_bias.power)} de las veces. No detectamos nada: un
          sesgo de ese tamaño es muy improbable.
        </p>
        {g.power.backtest && (
          <p className="text-secondary">
            En el backtest ({num(g.power.backtest.n_draws)} sorteos evaluados, {g.power.backtest.comparisons}{" "}
            comparaciones con Bonferroni), una estrategia que acertara{" "}
            <strong>{pct(g.power.backtest.min_relative_improvement)} más</strong> que el azar (
            {num(g.power.backtest.mean_hits + g.power.backtest.min_improvement, 3)} aciertos por sorteo en lugar de{" "}
            {num(g.power.backtest.mean_hits, 3)}) se habría detectado el {pct(g.power.backtest.power)} de las veces.
            Ninguna lo hizo.
          </p>
        )}
      </section>
    </>
  );
}
