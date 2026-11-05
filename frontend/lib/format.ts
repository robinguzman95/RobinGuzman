const nf = (d: number) => new Intl.NumberFormat("es-CO", { minimumFractionDigits: d, maximumFractionDigits: d });

export const num = (x: number, d = 0) => nf(d).format(x);

export function pValue(p: number | null | undefined): string {
  if (p === null || p === undefined) return "—";
  if (p < 0.001) return "< 0,001";
  return num(p, 3);
}

export function dateEs(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [y, m, d] = iso.split("-").map(Number);
  return new Intl.DateTimeFormat("es-CO", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }).format(
    new Date(Date.UTC(y, m - 1, d)),
  );
}

export const STRATEGY_LABEL: Record<string, string> = {
  random: "Al azar (línea base)",
  hot: "Calientes (más frecuentes)",
  cold: "Fríos (menos frecuentes)",
  overdue: "Atrasados (más tiempo sin salir)",
  anti_popular: "Anti-populares",
};

export const GAME_BLURB: Record<string, string> = {
  baloto: "5 números del 1 al 43 + superbalota del 1 al 16",
  revancha: "La misma jugada de Baloto, en un sorteo aparte",
  miloto: "5 números del 1 al 39, en cualquier orden",
  colorloto: "6 balotas, cada una con número del 1 al 7 y un color",
};
