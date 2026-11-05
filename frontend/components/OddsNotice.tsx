import type { S } from "@/lib/api";

/** Aviso fijo con la probabilidad real (principio de honestidad del producto). */
export function OddsNotice({ odds, name, children }: { odds: S["Odds"]; name: string; children?: React.ReactNode }) {
  return (
    <aside className="card border-l-4 notice-border p-4 text-sm" role="note">
      <p className="font-semibold">
        Probabilidad real del premio mayor de {name}: <span className="whitespace-nowrap">{odds.jackpot_odds}</span>
      </p>
      <p className="mt-1 text-secondary">
        Ningún análisis ni estrategia cambia esta cifra.{children ? <> {children}</> : " Cada sorteo es independiente."}
      </p>
    </aside>
  );
}

export function Loading({ what }: { what: string }) {
  return (
    <div className="card p-6 text-secondary" role="status" aria-busy="true">
      Cargando {what}…
    </div>
  );
}

export function ApiDown() {
  return (
    <div className="card p-6 text-secondary" role="status">
      La API no responde en este momento (el servidor gratuito puede tardar un minuto en despertar). Recarga la página
      en unos segundos.
    </div>
  );
}
