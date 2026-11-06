import type { Metadata } from "next";
import Link from "next/link";
import { connection } from "next/server";
import { Suspense } from "react";
import { PageHeader } from "@/components/PageHeader";
import { safe } from "@/lib/api";
import { getOverview } from "@/lib/data";
import { dateEs, num } from "@/lib/format";
import { AUTHOR, REPO_URL, docUrl } from "@/lib/site";

export const metadata: Metadata = {
  title: "El proyecto",
  description: "Pregunta, datos, metodología, validación, resultados, limitaciones y arquitectura de LotoLab.",
};

const pct = (r: number, d = 0) => `${num(r * 100, d)} %`;

export default function ProyectoPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-12">
      <div className="grid gap-12 lg:grid-cols-[14rem_1fr]">
        <nav aria-label="contenido" className="hidden lg:block">
          <ol className="sticky top-24 space-y-2 text-sm text-secondary">
            {[
              ["resumen", "Resumen"],
              ["pregunta", "La pregunta"],
              ["datos", "Datos"],
              ["metodos", "Métodos"],
              ["validacion", "Validación"],
              ["resultados", "Resultados"],
              ["limitaciones", "Limitaciones"],
              ["arquitectura", "Arquitectura"],
              ["autor", "Autor y enlaces"],
            ].map(([id, label]) => (
              <li key={id}>
                <a href={`#${id}`} className="hover:underline">
                  {label}
                </a>
              </li>
            ))}
          </ol>
        </nav>

        <article className="prose-lab max-w-3xl space-y-4">
          <PageHeader eyebrow="El proyecto" title="LotoLab: ciencia de datos contra el azar">
            Un laboratorio que pone a prueba, con datos oficiales y métodos rigurosos, las creencias más comunes sobre
            cómo ganar la lotería.
          </PageHeader>

          <h2 id="resumen">Resumen</h2>
          <Suspense fallback={<p>Cargando cifras…</p>}>
            <Summary />
          </Suspense>

          <h2 id="pregunta">La pregunta</h2>
          <p>
            Mucha gente elige sus números con estrategias: los que «más salen», los que «ya les toca», los que llevan
            tiempo sin aparecer. La pregunta del proyecto es si alguna de esas estrategias — o un modelo de machine
            learning — acierta más que una jugada al azar cuando se evalúa con honestidad, es decir, usando solo
            información disponible antes de cada sorteo.
          </p>
          <p>
            El principio del producto es no prometer lo que no se puede cumplir: si los sorteos son justos, cada uno es
            independiente y nada del pasado cambia la probabilidad del próximo. Por eso cada pantalla que muestra
            jugadas muestra también la probabilidad real del juego.
          </p>

          <h2 id="datos">Datos</h2>
          <ul>
            <li>
              <strong>Fuente:</strong> páginas públicas de resultados de baloto.com (Operador Nacional de Juegos), con
              un scraper que respeta robots.txt, espera entre peticiones y se identifica. Uso académico, no comercial.
            </li>
            <li>
              <strong>Cobertura:</strong> Baloto y Revancha desde mayo de 2021, MiLoto desde octubre de 2023 y ColorLoto
              desde su lanzamiento en 2024, más las tablas de premios del último año.
            </li>
            <li>
              <strong>Calidad:</strong> un validador revisa números fuera de rango, duplicados, huecos en la numeración
              y fechas. Los sorteos que el sitio oficial no publica se completaron solo cuando dos medios independientes
              coincidían; el único que no se pudo confirmar quedó documentado, no inventado.
            </li>
            <li>
              <strong>Actualización:</strong> una tarea programada en GitHub Actions trae cada noche los sorteos nuevos
              y los valida antes de cargarlos en PostgreSQL.
            </li>
          </ul>

          <h2 id="metodos">Métodos</h2>
          <h3>Pruebas de aleatoriedad</h3>
          <p>
            Chi-cuadrado de uniformidad con una corrección exacta por extracción sin reposición (el estadístico se
            divide por (N−K)/(N−1), validado por simulación) y prueba de rachas de Wald–Wolfowitz con p-valor exacto,
            porque la aproximación normal producía falsos positivos con balotas poco frecuentes.
          </p>
          <h3>Backtesting</h3>
          <p>
            Cinco estrategias (calientes, fríos, atrasados, anti-populares y azar) en tres ventanas de historia, con un
            motor que solo entrega sorteos anteriores al evaluado. La línea base son 10.000 jugadas al azar sobre los
            mismos sorteos (Monte Carlo hipergeométrico), con corrección de Bonferroni por las 60 comparaciones. La
            ventana principal se declaró antes de ver resultados.
          </p>
          <h3>Valor esperado y análisis de potencia</h3>
          <p>
            Valor esperado de cada tiquete con las probabilidades exactas por categoría, los premios realmente pagados,
            la retención del 20 % y un modelo de Poisson para el reparto del premio mayor; las ventas por sorteo se
            estiman a partir del número de ganadores. El análisis de potencia calcula qué tan grande tendría que ser un
            sesgo para detectarlo (chi-cuadrado no central).
          </p>
          <h3>Machine learning</h3>
          <p>
            Gradient boosting (el mismo tipo de modelo que LightGBM, vía scikit-learn) y regresión logística que estiman
            la probabilidad de cada balota a partir de su historia reciente. Se evalúan con walk-forward:
            reentrenamiento cada 25 sorteos solo con el pasado, log-loss y Brier frente a la probabilidad uniforme e
            intervalos de confianza por bootstrap.
          </p>

          <h2 id="validacion">Validación: cómo sabemos que el «no» es confiable</h2>
          <ul>
            <li>
              <strong>Pruebas contra fugas de información.</strong> Hay pruebas automáticas que fallan si el backtest o
              el modelo usan el sorteo que intentan predecir. Una de ellas detectó y permitió corregir una fuga real
              durante el desarrollo.
            </li>
            <li>
              <strong>Control positivo.</strong> En sorteos simulados con un patrón escondido, el modelo de ML lo
              descubre y supera al azar con claridad; en sorteos simulados sin patrón no inventa nada.
            </li>
            <li>
              <strong>Potencia estadística.</strong> Con 650 sorteos, una balota que saliera un 57 % más de lo normal se
              detectaría el 80 % de las veces; una estrategia que acertara un 20 % más, también.
            </li>
            <li>
              <strong>Más de 180 pruebas automáticas</strong> e integración continua en cada cambio.
            </li>
          </ul>

          <h2 id="resultados">Resultados</h2>
          <Suspense fallback={<p>Cargando resultados…</p>}>
            <Results />
          </Suspense>

          <h2 id="limitaciones">Limitaciones</h2>
          <ul>
            <li>
              Con unos cientos de sorteos por juego no se pueden descartar sesgos pequeños (por debajo de ~50 %); para
              eso harían falta miles de sorteos.
            </li>
            <li>
              Las ventas por sorteo son estimaciones a partir de los ganadores, y el puntaje de popularidad de una
              jugada es heurístico (no hay datos públicos de lo que juega la gente).
            </li>
            <li>Los acumulados de equilibrio del valor esperado son extrapolaciones fuera del rango observado.</li>
            <li>Faltan algunos sorteos de julio de 2026 que el operador no publica; están documentados.</li>
          </ul>

          <h2 id="arquitectura">Arquitectura</h2>
          <Architecture />
          <p>
            Monorepo con backend en Python (FastAPI, SQLAlchemy y Alembic; pandas, NumPy, SciPy y scikit-learn para el
            análisis) y frontend en Next.js 16 con TypeScript y Recharts. La API corre en Docker sobre Render con
            PostgreSQL; la web, en Vercel. Los tipos de la API se generan automáticamente desde su especificación
            OpenAPI.
          </p>

          <h2 id="autor">Autor y enlaces</h2>
          <p>
            Proyecto desarrollado por <strong>{AUTHOR}</strong>: diseño del estudio, ingeniería de datos, estadística,
            modelos, API y web.
          </p>
          <div className="not-prose flex flex-wrap gap-3 pt-2">
            <a href={REPO_URL} className="btn" rel="noopener noreferrer">
              Código en GitHub
            </a>
            <a href={docUrl("resultados_backtest.md")} className="btn-secondary" rel="noopener noreferrer">
              Informe del backtest
            </a>
            <a href={docUrl("valor_esperado.md")} className="btn-secondary" rel="noopener noreferrer">
              Informe de valor esperado
            </a>
            <a href={docUrl("modelo_ml.md")} className="btn-secondary" rel="noopener noreferrer">
              Informe del modelo de ML
            </a>
          </div>
        </article>
      </div>
    </div>
  );
}

async function Summary() {
  await connection();
  const o = await safe(getOverview());
  const dates = o
    ? Object.values(o.games)
        .flatMap((g) => [g.date_from, g.date_to])
        .filter(Boolean)
        .sort()
    : [];
  return (
    <p>
      LotoLab analiza <strong>{o ? num(o.total_draws) : "más de 2.000"} sorteos oficiales</strong>
      {dates.length > 0 && (
        <>
          {" "}
          ({dateEs(dates[0])} → {dateEs(dates[dates.length - 1])})
        </>
      )}{" "}
      de cuatro loterías colombianas. Ninguna de las {o?.backtest?.combinations ?? 60} combinaciones de estrategia,
      ventana y juego supera al azar, el modelo de machine learning tampoco, y un tiquete de Baloto devuelve en promedio{" "}
      <strong>
        {o?.expected_value?.baloto?.return_current != null ? pct(o.expected_value.baloto.return_current) : "~26 %"}
      </strong>{" "}
      de lo que cuesta. El hallazgo, bien medido, es el producto: los datos confirman que las loterías son azar.
    </p>
  );
}

async function Results() {
  await connection();
  const o = await safe(getOverview());
  if (!o) return <p>La API no responde en este momento.</p>;
  const codes = Object.keys(o.games);
  return (
    <div className="not-prose overflow-x-auto">
      <table className="data">
        <thead>
          <tr>
            <th>Juego</th>
            <th>Sorteos</th>
            <th>Vuelve por peso jugado</th>
            <th>Modelo de ML (habilidad)</th>
            <th>Sesgo mínimo detectable</th>
            <th>Premio mayor</th>
          </tr>
        </thead>
        <tbody>
          {codes.map((c) => {
            const g = o.games[c];
            const ev = o.expected_value?.[c];
            const ml = o.ml?.[c]?.gb;
            return (
              <tr key={c}>
                <td>{g.name}</td>
                <td>{num(g.draws)}</td>
                <td>{ev?.return_current != null ? pct(ev.return_current) : "—"}</td>
                <td>{ml ? `${pct(ml.skill, 2)} (${ml.beats_random ? "mejor" : "no supera"} al azar)` : "—"}</td>
                <td>{ev ? `+${pct(ev.min_bias)}` : "—"}</td>
                <td>{g.odds}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="mt-3 text-sm text-secondary">
        Backtest: {o.backtest?.significant ?? 0} de {o.backtest?.combinations ?? 60} combinaciones superan al azar tras
        Bonferroni (α = {o.backtest ? num(o.backtest.alpha_bonferroni, 5) : "—"}). Detalle en{" "}
        <Link href="/backtest" className="link">
          Backtest
        </Link>
        ,{" "}
        <Link href="/ml" className="link">
          Modelo de ML
        </Link>{" "}
        y{" "}
        <Link href="/vale-la-pena" className="link">
          ¿Vale la pena?
        </Link>
        .
      </p>
    </div>
  );
}

function Architecture() {
  const boxes = [
    ["baloto.com", "resultados y premios públicos"],
    ["Ingesta", "scraper · validación · CSV"],
    ["PostgreSQL", "sorteos y corridas"],
    ["API FastAPI", "estadística · backtest · ML"],
    ["Web Next.js", "Vercel"],
  ];
  return (
    <figure className="not-prose space-y-2">
      <ol className="flex flex-col items-stretch gap-2 md:flex-row md:items-center">
        {boxes.map(([t, d], i) => (
          <li key={t} className="flex flex-1 items-center gap-2">
            <div className="card flex-1 p-3 text-center">
              <p className="font-semibold">{t}</p>
              <p className="text-xs text-muted">{d}</p>
            </div>
            {i < boxes.length - 1 && (
              <span aria-hidden className="text-muted md:inline">
                →
              </span>
            )}
          </li>
        ))}
      </ol>
      <figcaption className="text-xs text-muted">
        GitHub Actions dispara la ingesta cada noche y corre las pruebas en cada cambio. Docker empaqueta la API.
      </figcaption>
    </figure>
  );
}
