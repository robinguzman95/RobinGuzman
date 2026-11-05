# LotoLab — reglas del proyecto

Laboratorio estadístico web para Baloto, Revancha, MiLoto y ColorLoto (Colombia).

## Principio de honestidad (no negociable)

- Los sorteos son independientes. La app **no predice** ni promete mejorar probabilidades.
- Toda pantalla o respuesta que recomiende jugadas muestra la **probabilidad real** del juego,
  calculada por `Game.jackpot_odds()`; nunca se escribe a mano.
- Una estrategia solo "funciona" si su promedio de aciertos supera el percentil 95 de 10.000
  jugadas aleatorias (Monte Carlo). Si no, se dice en pantalla. Se corrige por comparaciones
  múltiples (Bonferroni).
- El generador solo optimiza lo optimizable: evitar combinaciones populares para no repartir premio.

## Matrices (fuente: baloto.com, revisado 2026-11-04)

| Juego | Matriz | Sorteos | Premio mayor |
|---|---|---|---|
| Baloto | 5 de 1–43 sin repetir + superbalota 1–16 | lun, mié, sáb | 1 en 15.401.568 = C(43,5)·16 |
| Revancha | misma jugada que Baloto, sorteo aparte | lun, mié, sáb | 1 en 15.401.568 |
| MiLoto | 5 de 1–39 sin repetir, cualquier orden | lun, mar, jue, vie | 1 en 575.757 = C(39,5) |
| ColorLoto | 6 balotas número 1–7 + color (amarillo, azul, rojo, verde, blanco, negro); no se repite el mismo par número-color | lun, jue | 1 en 5.245.786 = C(42,6) |

Los días de sorteo cambian (Baloto pasó de mié/sáb a lun/mié/sáb): el validador los trata
como **advertencia**, no como error.

## Reglas del backtest (Fase 3)

- Ventana móvil: para el sorteo t solo se usan sorteos con fecha/número **< t**. Debe existir un
  test que falle si se filtra información del futuro.
- Las estrategias son funciones puras: `historial -> jugada`. Sin estado global ni aleatoriedad
  sin semilla explícita.
- Se reporta: aciertos promedio, distribución de aciertos, p5/media/p95 de la línea base y p-valor.
- La ventana principal se declara antes de correr; las demás son análisis de sensibilidad.
  **Declarada: 100 sorteos** (`PRIMARY_WINDOW` en `backtest/engine.py`); sensibilidad: 50 y 200.
  No cambiarla después de ver resultados.
- El motor entrega la historia como tupla y verifica que todo sorteo tenga número < t
  (`LookAheadError`). `tests/test_backtest.py` tiene la prueba espía, el "oráculo" y la de
  independencia de sorteos futuros: deben seguir pasando.
- Línea base: aciertos hipergeométricos H(N, K, K) simulados con numpy (equivale a jugadas al
  azar contra los mismos sorteos); media teórica K²/N. p-valor de una cola con +1.
- "Le gana al azar" solo si promedio > p95 **y** p < α/m (Bonferroni sobre todas las
  combinaciones corridas juntas, `lotolab backtest-all`). Una corrida suelta de la API lo dice.

## Análisis (Fase 2)

- `app/analysis/` son funciones puras sobre `list[DrawRecord]`; el backtest las reutiliza
  pasándoles solo la historia anterior a cada sorteo. Nada en `analysis/` consulta la BD.
- Unidad de conteo: la balota (número, color); en juegos sin color, color = None.
- Chi-cuadrado: siempre con la corrección por extracción sin reposición c = (N−K)/(N−1).
- Rachas: p-valor exacto (la normal da falsos positivos con balotas poco frecuentes) y
  Bonferroni sobre todas las balotas.
- El puntaje de popularidad es heurístico y la cuadrícula del tiquete es aproximada: decirlo
  siempre que se muestre.

## Web y despliegue (Fase 4)

- Frontend en `frontend/`: **Next.js 16 con Cache Components** (`cacheComponents: true`). No usar
  `export const revalidate/dynamic`: los datos de servidor se cachean con `"use cache"` +
  `cacheLife` en `lib/data.ts`, y el contenido que depende de la API va en `<Suspense>` con
  `await connection()` (el build no necesita la API). Leer `frontend/node_modules/next/dist/docs/`
  antes de usar APIs de Next: difieren de versiones anteriores.
- Tipos de la API generados: `npm run types` (OpenAPI → `lib/api-types.ts`). Regenerar tras cambiar
  esquemas del backend.
- Gráficas: serie única = azul `--series-1`; banda del azar = gris; mapa de calor = rampa
  secuencial azul. Toda gráfica tiene vista de tabla. Toda pantalla con jugadas muestra la
  probabilidad real (`OddsNotice`).
- API pública: `POST /backtest` solo acepta ventanas 50/100/200 y semilla 0–20, y reutiliza
  corridas idénticas (cada corrida distinta se guarda). `POST /ingest/run` exige
  `X-Ingest-Token`.
- Despliegue: Vercel (frontend) + Render (`render.yaml`, `backend/Dockerfile`) + cron en
  `.github/workflows/update-draws.yml`. Guía: `docs/despliegue.md`.

## Valor esperado y potencia (Fase 5)

- Tablas de premios: `lotolab scrape-prizes` (páginas de detalle, último año, caché permanente) →
  `data/raw/{juego}_premios.csv`. Luego `lotolab expected-value` → `data/expected_value.json`, que
  sirve la API (`/expected-value`, `/games/{code}/expected-value?jackpot=&popularity=`).
- Probabilidades por categoría exactas por combinatoria (`analysis/expected.py`); ColorLoto "6N" y
  "6C" por Monte Carlo con semilla fija. En Baloto/Revancha la fila "0 + SB" agrupa 0 y 1 aciertos
  con superbalota (ambos devuelven el valor de la jugada).
- Ventas estimadas = ganadores de una categoría "contador" / su probabilidad. VE del premio mayor
  con reparto Poisson: E[1/(1+K)] = (1 − e^{−λ})/λ. Retención 20 % > 48 UVT (2026): revisar cada año.
- Potencia (`analysis/power.py`): chi-cuadrado no central para el sesgo mínimo detectable y
  Δ = (z_{1−α/m} + z_{potencia})·σ/√n para el backtest; ambas validadas por simulación en tests.
- Precios por jugada en `PRICES`: actualizarlos si baloto.com los cambia.

## Analizador de jugadas (Fase 6)

- `analysis/picks.py`: jugadas armadas desde el histórico (calientes, consistentes en 3 ventanas,
  forma típica, pareja más repetida, atrasados). `GET /games/{code}/picks?window=` las arma en vivo
  desde la BD. `lotolab picks` evalúa cada criterio con los premios reales del último año →
  `data/picks_eval.json` (fuera de muestra = armada con datos anteriores; dentro = optimista).
- Mostrar siempre las dos columnas y la probabilidad real: la página no debe sugerir que una
  jugada tiene más probabilidad de acertar.

## Datos

- En **local**, la vía canónica de entrada a la BD es el **CSV** en `data/raw/{juego}.csv`: el
  comando `scrape` solo escribe CSV y `import` los carga.
- En **producción** la BD es la fuente (el disco del contenedor es efímero): `jobs/update_draws.py`
  (vía `POST /ingest/run` o el cron de GitHub Actions) valida y carga con el mismo importador, sin
  CSV intermedio. `lotolab export-csv` respalda la BD en `data/raw/`. Al arrancar, el contenedor
  siembra la BD desde los CSV del repo (idempotente).
- Scraper: solo páginas públicas de `baloto.com` (robots.txt prohíbe `/api/`), con pausa entre
  peticiones y User-Agent identificable. Los términos de baloto.com reservan sus bases de datos y
  prohíben el uso **comercial** sin autorización: este proyecto es académico/portafolio. Si algún
  día se comercializa o se publica el dataset, pedir autorización al Operador Nacional de Juegos.
- Una fila por balota en `draw_balls`; frecuencias = `GROUP BY`.
- baloto.com no publica algunos sorteos (p. ej. julio de 2026). Se completan a mano solo si
  **dos medios independientes** coinciden en las balotas (cotejar por fecha: la prensa se
  equivoca en el número de sorteo), con ambas URL en `source_url`. Si no hay dos fuentes, el
  sorteo **no se inventa**: se registra en `data/raw/known_gaps.csv` con el motivo, y el
  validador lo reporta como hueco documentado en lugar de error.

## Stack y comandos

Backend en `backend/` con `uv` y Python 3.12 (FastAPI, SQLAlchemy 2 + Alembic, pandas/numpy/scipy,
pytest). SQLite en desarrollo, PostgreSQL en producción. Frontend Next.js + TypeScript + Recharts
(Fase 4). Docker Compose en la Fase 4.

```bash
cd backend
uv sync                                   # instalar dependencias
uv run pytest                             # pruebas
uv run lotolab init                       # migraciones + tabla games
uv run lotolab scrape --game baloto --since 2025-11-01   # descarga a data/raw/*.csv
uv run lotolab import                     # carga data/raw/*.csv
uv run lotolab validate                   # huecos, duplicados, rangos, cobertura
uv run alembic revision --autogenerate -m "..."          # nueva migración
```

## Convenciones

- Cada juego es una clase en `backend/app/games/` que hereda de `Game`; añadir un juego no toca
  el motor. Registro en `app/games/__init__.py`.
- Código en inglés; textos para el usuario y documentación en español.
- Ritual por fase: plan → implementación → `pytest` en verde → code-review → commit.
- No hacer commit de `data/*.db` ni de la caché HTML del scraper.
