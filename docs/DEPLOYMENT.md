# Deployment

Living document — reflects current deploy targets only. Update in place when something moves.

## Frontend
- **Vercel**: `https://quick-paper-ai-ruddy.vercel.app/`
- Auto-deploys on push to `main`. Root directory set to `client/` in the Vercel dashboard.
- Nitro output paths are pinned explicitly in `client/vite.config.ts`
  (`dir`, `publicDir`, `serverDir` → `.vercel/output/...`) — the TanStack config default
  doesn't match Vercel's Build Output API v3 layout, don't remove these overrides.

## Backend
- **Currently**: Railway — `https://quickpaperai-production.up.railway.app/`.
  Auto-builds root `Dockerfile` on push to `main`. Binds to Railway's `$PORT`.
  Uvicorn started with `--timeout-keep-alive 120` (generation can run past a minute; avoids
  socket drops on Railway's proxy). Playwright `wait_for_load_state` timeout set to 90s for the
  same reason.
- **In progress**: migrating backend hosting to Oracle Cloud (OCI) Always Free tier
  (Ampere A1, 2 OCPU / 12GB — Oracle halved this from 4/24 in June 2026, budget for the current
  smaller allowance). Target CI/CD: GitHub Actions builds on push to `main` → pushes image to
  GitHub Container Registry (`ghcr.io`) → SSH deploy step on the same workflow runs
  `docker compose pull && docker compose up -d` on the OCI VM → Caddy reverse-proxies to the
  app container by service name so no proxy reconfig is needed on redeploy. Not yet live —
  Railway is still the deployed backend until this is cut over.

## Worker
- ARQ worker: `arq src.paper.worker.settings.WorkerSettings`
- Needs its own `AsyncConnectionPool` sized independently from the web server's pool (see
  `docs/GOTCHAS.md` if pool sizing across processes ever gets revisited — Supabase's connection
  limit is the constraint, not the app).

## External services / env vars (categories, not values)
- Supabase: Postgres (chunks/users/generated_papers), Storage bucket (`question-papers`),
  service-role key (bypasses RLS — ownership checks are enforced in the app layer, see
  `docs/ARCHITECTURE.md` → Auth).
- Upstash Redis: OTP store, progress tracker, ARQ job queue, Pub/Sub for SSE.
- Gemini API (+ Groq as fallback chain).
- Firebase: Web push credentials (`quickpaperai-fc0db`), VAPID key — loaded via
  `VITE_FIREBASE_*` env vars client-side, never hardcoded.
- Mail: SMTP relay (Brevo/SendGrid) via `fastapi-mail`.

## Local run
```bash
source /home/jeet-daiya/Storage/Teddy/venv/bin/activate
python -m src.main            # API server
arq src.paper.worker.settings.WorkerSettings   # worker, separate terminal
python scripts/run_cli.py     # standalone CLI generator, no server needed
```