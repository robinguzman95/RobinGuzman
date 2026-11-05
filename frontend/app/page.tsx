import Link from "next/link";
import { connection } from "next/server";
import { Suspense } from "react";
import { Balls } from "@/components/Balls";
import { ApiDown, Loading } from "@/components/OddsNotice";
import { safe } from "@/lib/api";
import { getGames, getHealth, getLastDraw } from "@/lib/data";
import { dateEs, GAME_BLURB, num } from "@/lib/format";

export default function Home() {
  return (
    <div className="space-y-8">
      <section className="space-y-3">
        <h1 className="text-3xl font-bold">¿Alguna estrategia le gana al azar?</h1>
        <p className="max-w-3xl text-secondary">
          LotoLab analiza el histórico de los juegos de Baloto y somete a prueba las estrategias populares — números
          calientes, fríos o atrasados — contra jugadas al azar. Spoiler honesto: cada sorteo es independiente, así que{" "}
          <strong>ninguna</strong> estrategia mejora la probabilidad. Aquí lo puedes comprobar con los datos.
        </p>
        <p>
          <Link className="link" href="/backtest">
            Ver el resultado del backtest →
          </Link>
        </p>
      </section>
      <Suspense fallback={<Loading what="los juegos" />}>
        <GameCards />
      </Suspense>
    </div>
  );
}

async function GameCards() {
  await connection(); // datos de la API en tiempo de petición (con caché de 1 min en lib/data)
  const [games, health] = await Promise.all([safe(getGames()), safe(getHealth())]);
  if (!games || !health) return <ApiDown />;
  const last = await Promise.all(games.map((g) => safe(getLastDraw(g.code))));
  return (
    <section aria-label="juegos" className="grid gap-4 sm:grid-cols-2">
      {games.map((g, i) => {
        const d = last[i]?.items[0];
        const h = health.games[g.code];
        return (
          <article key={g.code} className="card flex flex-col gap-3 p-5">
            <header>
              <h2 className="text-xl font-semibold">{g.name}</h2>
              <p className="text-sm text-secondary">{GAME_BLURB[g.code]}</p>
            </header>
            {d ? (
              <div className="space-y-2">
                <p className="text-sm text-muted">
                  Último sorteo #{d.draw_number} · {dateEs(d.draw_date)}
                </p>
                <Balls balls={d.balls} extra={d.extra} />
              </div>
            ) : (
              <p className="text-secondary">Sin sorteos cargados.</p>
            )}
            <dl className="mt-auto grid grid-cols-2 gap-2 text-sm">
              <div>
                <dt className="text-muted">Premio mayor</dt>
                <dd className="font-semibold">{g.odds.jackpot_odds}</dd>
              </div>
              <div>
                <dt className="text-muted">Histórico</dt>
                <dd>
                  {num(h?.draws ?? 0)} sorteos · act. {dateEs(h?.last_draw_date)}
                </dd>
              </div>
            </dl>
            <Link className="link text-sm" href={`/${g.code}`}>
              Estadísticas de {g.name} →
            </Link>
          </article>
        );
      })}
    </section>
  );
}
