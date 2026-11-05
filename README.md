# LotoLab

Laboratorio estadístico de Baloto, Revancha, MiLoto y ColorLoto. **No predice**: analiza el
histórico y comprueba con backtesting si alguna estrategia popular le gana al azar.
Reglas del proyecto en [CLAUDE.md](CLAUDE.md).

## Estado

- [x] Fase 1 — Datos: histórico completo publicado (Baloto/Revancha 650 sorteos desde mayo
  2021, MiLoto 635 desde oct 2023, ColorLoto 231 desde ago 2024), validado; 1 hueco
  documentado en `data/raw/known_gaps.csv`
- [x] Fase 2 — Análisis: frecuencias, calientes/fríos, pares, chi-cuadrado corregido, rachas
  exactas, popularidad; `/games/{code}/stats` y `/draws`. Ver [conteo manual](docs/conteo_manual_fase2.md)
- [x] Fase 3 — Backtest: 5 estrategias × 3 ventanas × 4 juegos sobre el histórico completo
  (Baloto desde 2021). **Ninguna le gana al azar** → [resultados](docs/resultados_backtest.md)
- [x] Fase 6 — Analizador de jugadas: números más frecuentes, jugadas armadas con el histórico y
  cómo les habría ido con premios reales
- [x] Fase 5 — Valor esperado real de cada tiquete (tablas de premios oficiales), ventas
  estimadas, evidencia de que la gente juega fechas y análisis de potencia →
  [resultados](docs/valor_esperado.md)
- [x] Fase 4 — Web (inicio, estadísticas, backtest, generador), tarea post-sorteo, Docker,
  Render + Vercel + GitHub Actions. Falta publicarlo con tus cuentas: [guía](docs/despliegue.md)

## Empezar

Requiere [uv](https://docs.astral.sh/uv/) (instala Python 3.12 por su cuenta).

```bash
cd backend
uv sync
uv run pytest
uv run lotolab init
uv run lotolab scrape            # últimos ~400 días → data/raw/*.csv
uv run lotolab import
uv run lotolab validate
uv run uvicorn app.main:app --reload   # http://localhost:8000/docs
```

Frontend (Node 20+), con la API corriendo:

```bash
cd frontend
npm install
npm run dev                            # http://localhost:3000
```

## Datos

`data/raw/{juego}.csv` es la fuente canónica (ver formato en
`backend/app/ingest/importer_csv.py`). El scraper lee las páginas públicas de baloto.com
para uso académico, no comercial; ver la nota sobre términos de uso en CLAUDE.md.
