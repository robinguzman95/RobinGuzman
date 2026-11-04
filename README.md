# LotoLab

Laboratorio estadístico de Baloto, Revancha, MiLoto y ColorLoto. **No predice**: analiza el
histórico y comprueba con backtesting si alguna estrategia popular le gana al azar.
Reglas del proyecto en [CLAUDE.md](CLAUDE.md).

## Estado

- [x] Fase 1 — Datos: 684 sorteos (oct 2025 – nov 2026) de los cuatro juegos, validados;
  1 hueco documentado en `data/raw/known_gaps.csv`
- [ ] Fase 2 — Análisis
- [ ] Fase 3 — Backtest
- [ ] Fase 4 — Web y despliegue

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

## Datos

`data/raw/{juego}.csv` es la fuente canónica (ver formato en
`backend/app/ingest/importer_csv.py`). El scraper lee las páginas públicas de baloto.com
para uso académico, no comercial; ver la nota sobre términos de uso en CLAUDE.md.
