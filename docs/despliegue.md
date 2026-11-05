# Despliegue de LotoLab

Arquitectura: **frontend en Vercel** → **API en Render** (Docker) → **PostgreSQL en Render**, y
**GitHub Actions** dispara la actualización tras cada sorteo. Todo en planes gratuitos; verifica
los precios vigentes antes de empezar.

```
Navegador ──► Vercel (Next.js) ──► Render: lotolab-api (FastAPI) ──► Render: lotolab-db (Postgres)
                                          ▲
GitHub Actions (cron 00:30 y 08:00 Bogotá) ┘  POST /ingest/run con token
```

Solo tú puedes crear las cuentas e ingresar credenciales. Estos pasos toman unos 30 minutos.

## 0. Antes de empezar

1. `main` ya contiene las cuatro fases. Si haces cambios en otra rama, fusiónalos antes de publicar
   (`git switch main` y `git merge --ff-only <rama>`).
2. Genera el token de ingesta (guárdalo en tu gestor de contraseñas; no lo subas al repo):
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

## 1. GitHub

1. Crea un repositorio vacío en github.com (p. ej. `lotolab`). Público sirve como portafolio; no
   contiene secretos. Contiene los CSV de resultados en `data/raw/`: si prefieres no publicar el
   dataset (ver nota de términos en `CLAUDE.md`), créalo **privado**: Vercel y Render funcionan igual.
2. Súbelo:
   ```bash
   git remote add origin https://github.com/<tu-usuario>/lotolab.git
   git push -u origin main
   ```
3. En **Settings → Secrets and variables → Actions**:
   - *Secrets* → `INGEST_TOKEN` = el token del paso 0.
   - *Variables* → `API_URL` = la URL de Render (la tendrás en el paso 2; vuelve a ponerla).

## 2. Render (API + base de datos)

1. Crea una cuenta en render.com con tu GitHub.
2. **New → Blueprint** → elige el repo. Render lee `render.yaml` y propone `lotolab-api` (Docker) y
   `lotolab-db` (PostgreSQL).
3. Te pedirá las variables marcadas `sync: false`:
   - `LOTOLAB_INGEST_TOKEN` = el mismo token.
   - `LOTOLAB_CORS_ORIGINS` = la URL de Vercel (paso 3). Si aún no la tienes, pon
     `http://localhost:3000` y la cambias después.
4. Espera el primer deploy (5–10 min). Al arrancar, el contenedor corre `lotolab init` (tablas) y
   `lotolab import` (siembra la BD con `data/raw/*.csv`; las siguientes veces no hace nada).
5. Comprueba `https://<tu-api>.onrender.com/health`: debe listar los cuatro juegos con sus sorteos.

> **Postgres gratis de Render:** si sigue expirando a los 30 días, crea una base gratis en
> neon.tech y pon su cadena de conexión en `LOTOLAB_DATABASE_URL` del servicio. El código acepta
> `postgres://` y `postgresql://`.
>
> **Arranque en frío:** el plan gratis duerme el servicio tras 15 min sin uso; la primera visita
> tarda ~1 minuto. La web muestra un aviso en lugar de romperse.

## 3. Vercel (frontend)

1. Crea una cuenta en vercel.com con tu GitHub → **Add New → Project** → el repo.
2. **Root Directory**: `frontend`.
3. **Environment Variables**: `NEXT_PUBLIC_API_URL` = `https://<tu-api>.onrender.com`.
4. Deploy. Copia la URL (p. ej. `https://lotolab.vercel.app`) y ponla en
   `LOTOLAB_CORS_ORIGINS` de Render (paso 2.3); Render se redespliega solo.

## 4. Actualización automática (condición de salida de la Fase 4)

1. En GitHub → **Actions → Actualizar sorteos → Run workflow**. Debe terminar en verde con
   `"ok": true`.
2. Tras el siguiente sorteo real, el cron de las 00:30 (hora de Bogotá) lo trae solo. Verifícalo:
   `/health` muestra el nuevo `last_draw_date` y la web enseña el sorteo en la portada.
3. Si un día falla (baloto.com caído o publicó tarde), el reintento de las 08:00 lo recoge; si
   ambos fallan, GitHub te avisa por correo.

## 5. Mantenimiento

- **Respaldo de datos al repo** (opcional, cada tanto), con la URL de Postgres de Render en tu PC:
  ```bash
  cd backend
  LOTOLAB_DATABASE_URL="<cadena externa de Render>" uv run lotolab export-csv
  ```
  y haz commit de `data/raw/*.csv`.
- **Reporte del backtest** con datos nuevos: `uv run lotolab backtest-all` en local (genera
  `docs/resultados_backtest.md` y `data/backtest_summary.json`), commit y push: Render lo publica.
- **Huecos** que baloto.com no publique: completar con dos fuentes o documentar en
  `data/raw/known_gaps.csv` (ver `CLAUDE.md`), y hacer push.

## Uso responsable de la fuente

Proyecto académico, no comercial. La web cita a baloto.com como fuente, no muestra publicidad ni
cobra, y la tarea consulta las páginas públicas una o dos veces al día con un User-Agent
identificable. Si algún día se comercializa, pedir autorización al Operador Nacional de Juegos.
