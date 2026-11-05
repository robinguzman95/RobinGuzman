import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { FrequencyChart } from "@/components/FrequencyChart";
import { ApiDown, Loading, OddsNotice } from "@/components/OddsNotice";
import { PairHeatmap } from "@/components/PairHeatmap";
import { GAME_CODES, safe, type GameCode, type S } from "@/lib/api";
import { getGames, getStats } from "@/lib/data";
import { dateEs, num, pValue } from "@/lib/format";

const WINDOWS = [
  { value: "12m", label: "Últimos 12 meses" },
  { value: "100", label: "Últimos 100 sorteos" },
  { value: "all", label: "Todo el histórico" },
];

type Props = { params: Promise<{ game: string }>; searchParams: Promise<{ window?: string }> };

export default function GamePage(props: Props) {
  return (
    <Suspense fallback={<Loading what="las estadísticas" />}>
      <GameContent {...props} />
    </Suspense>
  );
}

async function GameContent({ params, searchParams }: Props) {
  const { game } = await params;
  if (!GAME_CODES.includes(game as GameCode)) notFound();
  const { window = "12m" } = await searchParams;
  const w = WINDOWS.some((x) => x.value === window) ? window : "12m";
  const [s, games] = await Promise.all([safe(getStats(game, w)), safe(getGames())]);
  const g = games?.find((x) => x.code === game);
  if (!s || !g) return <ApiDown />;

  const k = g.main_count;
  const pool = g.main_max * (g.colors?.length ?? 1);
  const rows = Object.entries(s.frequency).map(([label, count]) => ({ label, count }));

  return (
    <div className="space-y-8">
      <header className="space-y-3">
        <nav className="flex flex-wrap gap-2 text-sm" aria-label="juego">
          {GAME_CODES.map((c) => (
            <Link
              key={c}
              href={`/${c}?window=${w}`}
              aria-current={c === game ? "page" : undefined}
              className={`btn-ghost ${c === game ? "font-semibold" : "text-secondary"}`}
            >
              {c === "colorloto" ? "ColorLoto" : c === "miloto" ? "MiLoto" : c[0].toUpperCase() + c.slice(1)}
            </Link>
          ))}
        </nav>
        <h1 className="text-3xl font-bold">Estadísticas de {g.name}</h1>
        <p className="text-secondary">
          {num(s.n_draws)} sorteos · {dateEs(s.date_from)} → {dateEs(s.date_to)}
        </p>
        <nav className="flex flex-wrap gap-2 text-sm" aria-label="ventana de tiempo">
          {WINDOWS.map((x) => (
            <Link
              key={x.value}
              href={`/${game}?window=${x.value}`}
              aria-current={x.value === w ? "true" : undefined}
              className={`btn-ghost ${x.value === w ? "font-semibold" : "text-secondary"}`}
            >
              {x.label}
            </Link>
          ))}
        </nav>
      </header>

      <OddsNotice odds={s.odds} name={g.name}>
        {s.disclaimer}
      </OddsNotice>

      <section className="card space-y-4 p-5">
        <h2 className="text-xl font-semibold">¿Salen todas las balotas por igual?</h2>
        <p className="text-sm text-secondary">
          Un p-valor alto significa que las diferencias entre balotas son del tamaño que produce el azar; solo un
          p-valor muy bajo indicaría algo raro.
        </p>
        <ul className="space-y-3">
          {s.uniformity.map((t) => (
            <Verdict key={t.label} t={t} />
          ))}
          <li className="text-sm">
            <span className="font-semibold">Rachas</span> (¿hay balotas que salen “en bloque”?):{" "}
            <VerdictText text={s.runs.verdict} /> — {s.runs.tested} pruebas con corrección de Bonferroni (α ={" "}
            {pValue(s.runs.alpha_bonferroni)}).
            {s.runs.significant_bonferroni.length > 0 && (
              <> Balotas a revisar: {s.runs.significant_bonferroni.join(", ")}.</>
            )}
          </li>
        </ul>
      </section>

      <section className="card space-y-4 p-5">
        <h2 className="text-xl font-semibold">Frecuencia por balota</h2>
        <FrequencyChart
          rows={rows}
          expected={(s.n_draws * k) / pool}
          title={g.colors ? "Veces que salió cada par número-color" : "Veces que salió cada número"}
        />
        {s.number_frequency && (
          <FrequencyChart
            rows={Object.entries(s.number_frequency).map(([label, count]) => ({ label, count }))}
            expected={(s.n_draws * k) / g.main_max}
            title="Por número (sumando todos los colores)"
          />
        )}
        {s.color_frequency && g.colors && (
          <FrequencyChart
            rows={Object.entries(s.color_frequency).map(([label, count]) => ({ label, count }))}
            expected={(s.n_draws * k) / g.colors.length}
            title="Por color (sumando todos los números)"
          />
        )}
        {s.extra_frequency && g.extra_max && (
          <FrequencyChart
            rows={Object.entries(s.extra_frequency).map(([label, count]) => ({ label, count }))}
            expected={s.n_draws / g.extra_max}
            title="Superbalota"
          />
        )}
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <StatTable title="Calientes" note="más veces en la ventana" rows={s.hot} />
        <StatTable title="Fríos" note="menos veces en la ventana" rows={s.cold} />
        <StatTable title="Atrasados" note="más sorteos sin salir" rows={s.overdue} />
      </section>
      <p className="text-sm text-secondary">
        Que un número esté “caliente” o “atrasado” no cambia su probabilidad en el próximo sorteo. El{" "}
        <Link className="link" href="/backtest">
          backtest
        </Link>{" "}
        lo comprueba con datos.
      </p>

      <section className="card space-y-4 p-5">
        <h2 className="text-xl font-semibold">Parejas frecuentes</h2>
        <PairHeatmap labels={Object.keys(s.frequency)} pairs={s.pair_counts as [string, string, number][]} />
      </section>

      {s.shape && (
        <section className="card space-y-2 p-5 text-sm">
          <h2 className="text-xl font-semibold">Forma de las combinaciones</h2>
          <p>
            Suma de los números: mínimo {s.shape.sum_min}, máximo {s.shape.sum_max}, promedio {num(s.shape.sum_mean, 1)}
            .
          </p>
          <ShapeTable title="Cantidad de números pares por sorteo" counts={s.shape.even_counts} />
          <ShapeTable
            title={`Cantidad de números altos (> ${g.main_max / 2}) por sorteo`}
            counts={s.shape.high_counts}
          />
        </section>
      )}
    </div>
  );
}

function VerdictText({ text }: { text: string }) {
  const ok = text.startsWith("compatible");
  return (
    <span className="font-semibold" style={{ color: ok ? "var(--good)" : "var(--serious)" }}>
      <span aria-hidden>{ok ? "✓ " : "⚠ "}</span>
      {text}
    </span>
  );
}

function Verdict({ t }: { t: S["ChiSquareOut"] }) {
  return (
    <li className="text-sm">
      <span className="font-semibold capitalize">{t.label}</span>: <VerdictText text={t.verdict} />
      <span className="text-secondary">
        {" "}
        — chi-cuadrado {num(t.statistic, 1)} con {t.dof} grados de libertad, p = {pValue(t.p_value)}.
      </span>
    </li>
  );
}

function StatTable({ title, note, rows }: { title: string; note: string; rows: S["BallStatOut"][] }) {
  return (
    <section className="card p-4">
      <h3 className="font-semibold">{title}</h3>
      <p className="text-xs text-muted">{note}</p>
      <table className="data mt-2">
        <thead>
          <tr>
            <th>Balota</th>
            <th>Veces</th>
            <th>Hace</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.label}>
              <td>{r.label}</td>
              <td>{r.count}</td>
              <td>{since(r)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function since(r: S["BallStatOut"]): string {
  if (r.draws_since === null || r.days_since === null) return "no salió";
  if (r.draws_since === 0) return "último sorteo";
  return `${r.draws_since} ${r.draws_since === 1 ? "sorteo" : "sorteos"} (${r.days_since} d)`;
}

function ShapeTable({ title, counts }: { title: string; counts: Record<string, number> }) {
  return (
    <div>
      <p className="mt-2 text-secondary">{title}</p>
      <table className="data max-w-md">
        <thead>
          <tr>
            {Object.keys(counts).map((k) => (
              <th key={k}>{k}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          <tr>
            {Object.values(counts).map((v, i) => (
              <td key={i}>{v}</td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  );
}
