// Lecturas de la API para componentes de servidor, cacheadas con Cache Components (Next 16):
// "use cache" + cacheLife("minutes") = se sirve desde caché y se revalida cada minuto.
// Si la API falla, la función lanza y el error NO queda en caché; la página muestra un aviso.
import { cacheLife } from "next/cache";
import { api } from "./api";

export async function getGames() {
  "use cache";
  cacheLife("minutes");
  return api.games();
}

export async function getHealth() {
  "use cache";
  cacheLife("minutes");
  return api.health();
}

export async function getLastDraw(code: string) {
  "use cache";
  cacheLife("minutes");
  return api.draws(code, 1);
}

export async function getStats(code: string, window: string) {
  "use cache";
  cacheLife("minutes");
  return api.stats(code, window);
}

export async function getExpectedValue(code: string) {
  "use cache";
  cacheLife("hours");
  return api.expectedValue(code);
}

export async function getAllExpectedValue() {
  "use cache";
  cacheLife("hours");
  return api.allExpectedValue();
}

export async function getSummary() {
  "use cache";
  cacheLife("minutes");
  return api.summary();
}
