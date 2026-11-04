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

## Análisis (Fase 2)

- `app/analysis/` son funciones puras sobre `list[DrawRecord]`; el backtest las reutiliza
  pasándoles solo la historia anterior a cada sorteo. Nada en `analysis/` consulta la BD.
- Unidad de conteo: la balota (número, color); en juegos sin color, color = None.
- Chi-cuadrado: siempre con la corrección por extracción sin reposición c = (N−K)/(N−1).
- Rachas: p-valor exacto (la normal da falsos positivos con balotas poco frecuentes) y
  Bonferroni sobre todas las balotas.
- El puntaje de popularidad es heurístico y la cuadrícula del tiquete es aproximada: decirlo
  siempre que se muestre.

## Datos

- La vía canónica de entrada a la BD es el **CSV** en `data/raw/{juego}.csv`. El scraper solo
  escribe esos CSV; nunca inserta directo en la BD.
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
