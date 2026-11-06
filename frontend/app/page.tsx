import Link from "next/link";
import { connection } from "next/server";
import { Suspense } from "react";
import { Balls } from "@/components/Balls";
import { ApiDown } from "@/components/OddsNotice";
import { safe } from "@/lib/api";
import { getGames, getLastDraw, getOverview } from "@/lib/data";
import { dateEs, num } from "@/lib/format";
import { AUTHOR, NAV, REPO_URL, docUrl } from "@/lib/site";

const pct = (r: number, d = 0) => `${num(r * 100, d)} %`;

export default function Home() {
  return (
    <>
      <section className="hero">
        <div className="mx-auto grid max-w-6xl items-center gap-10 px-4 py-16 md:grid-cols-[1.15fr_1fr] md:py-20">
          <div className="space-y-6">
            <p className="eyebrow">Proyecto de ciencia de datos · Loterías de Colombia</p>
            <h1 className="text-4xl font-bold leading-tight tracking-tight md:text-5xl">
              ¿Se le puede ganar al azar en la lotería?
            </h1>
            <p className="max-w-xl text-lg text-secondary">
              LotoLab descarga el histórico oficial de Baloto, Revancha, MiLoto y ColorLoto y pone a prueba, con
              estadística, backtesting y machine learning, las estrategias que la gente usa para elegir sus números.
              Todo se evalúa como en la vida real: sin mirar al futuro.
            </p>
            <div className="flex flex-wrap gap-3">
              <a href="#hallazgos" className="btn">
                Ver los resultados
              </a>
              <Link href="/mi-jugada" className="btn-secondary">
                Revisar mi jugada
              </Link>
              <Link href="/proyecto" className="btn-secondary">
                Cómo se hizo
              </Link>
            </div>
          </div>
          <Suspense fallback={<KpiSkeleton />}>
            <Kpis />
          </Suspense>
        </div>
      </section>

      <div className="mx-auto max-w-6xl space-y-20 px-4 py-16">
        <Suspense fallback={null}>
          <Findings />
        </Suspense>
        <Pipeline />
        <Tools />
        <Suspense fallback={null}>
          <LatestDraws />
        </Suspense>
        <Stack />
        <Author />
      </div>
    </>
  );
}

// --- KPIs del encabezado ------------------------------------------------------------
async function Kpis() {
  await connection();
  const o = await safe(getOverview());
  if (!o) return <ApiDown />;
  const bal = o.expected_value?.baloto;
  const tiles = [
    { value: num(o.total_draws), label: "sorteos oficiales analizados", note: "4 juegos, desde 2021" },
    {
      value: o.backtest ? `${o.backtest.significant} de ${o.backtest.combinations}` : "—",
      label: "estrategias que le ganan al azar",
      note: "tras corregir por comparaciones múltiples",
    },
    {
      value: bal?.return_current != null ? pct(bal.return_current) : "—",
      label: "vuelve de cada peso jugado en Baloto",
      note: "valor esperado con premios reales",
    },
    {
      value: o.ml && Object.values(o.ml).every((g) => !Object.values(g).some((m) => m.beats_random)) ? "= azar" : "—",
      label: "lo que logra el modelo de ML",
      note: "gradient boosting y regresión logística",
    },
  ];
  return (
    <dl className="grid grid-cols-2 gap-3">
      {tiles.map((t) => (
        <div key={t.label} className="card p-5">
          <dd className="text-3xl font-bold tracking-tight">{t.value}</dd>
          <dt className="mt-1 text-sm font-medium">{t.label}</dt>
          <p className="mt-1 text-xs text-muted">{t.note}</p>
        </div>
      ))}
    </dl>
  );
}

function KpiSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-3" aria-busy="true">
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className="card h-32 animate-pulse p-5" />
      ))}
    </div>
  );
}

// --- Hallazgos ---------------------------------------------------------------------
async function Findings() {
  await connection();
  const o = await safe(getOverview());
  if (!o) return null;
  const bal = o.expected_value?.baloto;
  const mlb = o.ml?.baloto?.gb;
  const items = [
    {
      big: o.backtest ? `${o.backtest.significant}/${o.backtest.combinations}` : "—",
      title: "Ninguna estrategia popular funciona",
      text: `Números calientes, fríos, atrasados y anti-populares, en 3 ventanas y 4 juegos: ninguna combinación acierta más que jugadas al azar tras la corrección de Bonferroni. Sin corregir, ${o.backtest?.nominal === 1 ? "una parecía ganar" : `${o.backtest?.nominal ?? "—"} parecían ganar`}: justo lo que produce el azar al probar muchas cosas a la vez.`,
      href: "/backtest",
      cta: "Ver el backtest",
    },
    {
      big: mlb ? pct(mlb.skill, 2) : "—",
      title: "El machine learning tampoco",
      text: "Un gradient boosting entrenado con la historia de cada balota predice levemente peor que suponer que todas son iguales (sobreajuste). Como control, el mismo modelo sí descubre un patrón escondido en datos simulados: el problema no es el modelo, es que no hay patrón.",
      href: "/ml",
      cta: "Ver el modelo",
    },
    {
      big: bal?.return_current != null ? pct(bal.return_current) : "—",
      title: "Lo que devuelve un tiquete",
      text: `Con los premios reales pagados, la retención del 20 % y el reparto del premio mayor, de cada $${num(bal?.price ?? 6000)} jugados en Baloto vuelven en promedio ${bal?.return_current != null ? pct(bal.return_current) : "—"}. MiLoto es el juego que menos pierde.`,
      href: "/vale-la-pena",
      cta: "Ver el valor esperado",
    },
    {
      big: bal?.popularity_rho != null ? `ρ = ${num(bal.popularity_rho, 2)}` : "—",
      title: "La gente sí juega fechas",
      text: "Cuando los números ganadores son días del mes (≤ 31), hay hasta 28 % más ganadores de 3 y 4 aciertos de lo esperado. Es la huella, en datos reales, de cómo elige la gente sus números.",
      href: "/vale-la-pena",
      cta: "Ver el análisis",
    },
  ];
  return (
    <section id="hallazgos" className="scroll-mt-24 space-y-8">
      <SectionTitle eyebrow="Resultados" title="Lo que encontramos">
        Cuatro conclusiones, calculadas con los datos oficiales y actualizadas automáticamente después de cada sorteo.
      </SectionTitle>
      <div className="grid gap-4 md:grid-cols-2">
        {items.map((it) => (
          <article key={it.title} className="card flex flex-col gap-3 p-6">
            <p className="text-4xl font-bold tracking-tight" style={{ color: "var(--series-1)" }}>
              {it.big}
            </p>
            <h3 className="text-lg font-semibold">{it.title}</h3>
            <p className="text-secondary">{it.text}</p>
            <Link href={it.href} className="link mt-auto text-sm">
              {it.cta} →
            </Link>
          </article>
        ))}
      </div>
    </section>
  );
}

// --- Cómo funciona -----------------------------------------------------------------
const STEPS = [
  {
    n: "01",
    title: "Datos oficiales",
    text: "Scraper responsable de baloto.com, validación de huecos, duplicados y rangos, y actualización automática tras cada sorteo.",
  },
  {
    n: "02",
    title: "Estadística",
    text: "Chi-cuadrado corregido por extracción sin reposición, rachas con p-valor exacto y análisis de potencia.",
  },
  {
    n: "03",
    title: "Backtesting",
    text: "Cada estrategia solo ve el pasado; se compara con 10.000 jugadas al azar y se corrige por Bonferroni.",
  },
  {
    n: "04",
    title: "Machine learning",
    text: "Gradient boosting y regresión logística con validación walk-forward y pruebas automáticas contra fugas.",
  },
  {
    n: "05",
    title: "Producto web",
    text: "API en FastAPI y web en Next.js, desplegadas en la nube, con herramientas para revisar y generar jugadas.",
  },
];

function Pipeline() {
  return (
    <section className="space-y-8">
      <SectionTitle eyebrow="Metodología" title="Cómo funciona">
        Un flujo completo de ciencia de datos, desde la descarga hasta la web, con la misma regla en cada paso: nunca
        usar información del futuro.
      </SectionTitle>
      <ol className="grid gap-4 md:grid-cols-5">
        {STEPS.map((s) => (
          <li key={s.n} className="card space-y-2 p-5">
            <span className="text-sm font-semibold" style={{ color: "var(--series-1)" }}>
              {s.n}
            </span>
            <h3 className="font-semibold">{s.title}</h3>
            <p className="text-sm text-secondary">{s.text}</p>
          </li>
        ))}
      </ol>
      <Link href="/proyecto" className="link inline-block text-sm">
        Metodología completa, arquitectura y limitaciones →
      </Link>
    </section>
  );
}

// --- Herramientas ------------------------------------------------------------------
function Tools() {
  return (
    <section className="space-y-8">
      <SectionTitle eyebrow="Explora" title="Herramientas del laboratorio">
        Todas muestran la probabilidad real del juego junto a cada jugada.
      </SectionTitle>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {NAV.flatMap((g) => g.items).map((it) => (
          <Link key={it.href} href={it.href} className="card block space-y-1 p-5">
            <h3 className="font-semibold">{it.label}</h3>
            <p className="text-sm text-secondary">{it.description}</p>
          </Link>
        ))}
      </div>
    </section>
  );
}

// --- Últimos resultados ------------------------------------------------------------
async function LatestDraws() {
  await connection();
  const [o, games] = await Promise.all([safe(getOverview()), safe(getGames())]);
  if (!o || !games) return null;
  const last = await Promise.all(games.map((g) => safe(getLastDraw(g.code))));
  return (
    <section className="space-y-8">
      <SectionTitle eyebrow="En vivo" title="Últimos resultados">
        Se actualizan solos cada noche, después de los sorteos.
      </SectionTitle>
      <div className="grid gap-4 md:grid-cols-2">
        {games.map((g, i) => {
          const d = last[i]?.items[0];
          const info = o.games[g.code];
          return (
            <article key={g.code} className="card space-y-3 p-5">
              <div className="flex items-baseline justify-between gap-3">
                <h3 className="text-lg font-semibold">{g.name}</h3>
                <span className="text-xs text-muted">premio mayor: {g.odds.jackpot_odds}</span>
              </div>
              {d ? (
                <>
                  <Balls balls={d.balls} extra={d.extra} size="sm" />
                  <p className="text-xs text-muted">
                    Sorteo #{d.draw_number} · {dateEs(d.draw_date)} · {num(info?.draws ?? 0)} sorteos en el histórico
                  </p>
                </>
              ) : (
                <p className="text-secondary">Sin sorteos cargados.</p>
              )}
              <Link className="link text-sm" href={`/${g.code}`}>
                Estadísticas de {g.name} →
              </Link>
            </article>
          );
        })}
      </div>
    </section>
  );
}

// --- Tecnología y calidad ----------------------------------------------------------
const TECH = [
  "Python 3.12",
  "FastAPI",
  "SQLAlchemy + Alembic",
  "PostgreSQL",
  "pandas · NumPy · SciPy",
  "scikit-learn",
  "pytest",
  "Next.js 16 · TypeScript",
  "Recharts",
  "Docker",
  "Render · Vercel",
  "GitHub Actions",
];

function Stack() {
  const quality = [
    ["Pruebas automáticas", "Más de 180 pruebas, incluidas las que fallan si un modelo o estrategia mira el futuro."],
    ["Integración continua", "Cada cambio corre pruebas, tipos y compilación en GitHub Actions antes de publicarse."],
    ["Datos que se actualizan solos", "Una tarea programada trae cada sorteo nuevo y lo valida antes de cargarlo."],
    [
      "Honestidad por diseño",
      "Cada pantalla con jugadas muestra la probabilidad real; ningún resultado se presenta como predicción.",
    ],
  ];
  return (
    <section className="space-y-8">
      <SectionTitle eyebrow="Ingeniería" title="Tecnología y calidad" />
      <div className="flex flex-wrap gap-2">
        {TECH.map((t) => (
          <span key={t} className="chip">
            {t}
          </span>
        ))}
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {quality.map(([t, d]) => (
          <div key={t} className="card p-5">
            <h3 className="font-semibold">{t}</h3>
            <p className="mt-1 text-sm text-secondary">{d}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

// --- Autor -------------------------------------------------------------------------
function Author() {
  return (
    <section className="card flex flex-col items-start gap-4 p-8 md:flex-row md:items-center md:justify-between">
      <div className="space-y-1">
        <p className="eyebrow">Autor</p>
        <h2 className="text-2xl font-bold">{AUTHOR}</h2>
        <p className="text-secondary">Diseño, ingeniería de datos, análisis estadístico, modelos y desarrollo web.</p>
      </div>
      <div className="flex flex-wrap gap-3">
        <a href={REPO_URL} className="btn" rel="noopener noreferrer">
          Ver el código
        </a>
        <a href={docUrl("modelo_ml.md")} className="btn-secondary" rel="noopener noreferrer">
          Informe del modelo de ML
        </a>
      </div>
    </section>
  );
}

function SectionTitle({ eyebrow, title, children }: { eyebrow: string; title: string; children?: React.ReactNode }) {
  return (
    <div className="max-w-3xl space-y-2">
      <p className="eyebrow">{eyebrow}</p>
      <h2 className="text-3xl font-bold tracking-tight">{title}</h2>
      {children && <p className="text-secondary">{children}</p>}
    </div>
  );
}
