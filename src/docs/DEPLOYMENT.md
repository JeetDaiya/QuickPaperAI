# Deployment

Living document — reflects current deploy targets only. Update in place when something moves.

## Frontend
- **Vercel**: `https://quick-paper-ai-ruddy.vercel.app/`
- Auto-deploys on push to `main`. Root directory set to `client/` in the Vercel dashboard.
- Nitro output paths are pinned explicitly in `client/vite.config.ts`
  (`dir`, `publicDir`, `serverDir` → `.vercel/output/...`) — the TanStack config default
  doesn't match Vercel's Build Output API v3 layout, don't remove these overrides.

## Backend
- **Currently**: Oracle Cloud (OCI) Always Free tier — `https://80-225-247-83.sslip.io/`
  (Ampere A1, Ubuntu 24.04, 2 OCPU / 12GB RAM, 4GB swap). sslip.io is a wildcard-DNS service
  that resolves `<ip-with-dashes>.sslip.io` to that IP with zero registration — swap to a real
  domain later by changing the `Caddyfile` site block and `VITE_API_BASE_URL`, nothing else.
  CI/CD: `.github/workflows/deploy.yml` — on push to `main`, GitHub Actions builds an
  `linux/arm64` image (QEMU + Buildx, since hosted runners are amd64 and the VM is ARM) →
  pushes to GitHub Container Registry (`ghcr.io/jeetdaiya/quickpaperai`) → copies
  `docker-compose.yml`/`Caddyfile` to the VM via `scp` → `docker compose pull && up -d` over
  SSH. Caddy reverse-proxies to the `app` container by service name and auto-provisions/renews
  the Let's Encrypt cert — no manual TLS handling.
  `.env` and `firebase-credentials.json` are gitignored and live only on the VM
  (`~/app/`, `chmod 600`), bind-mounted into the `app`/`worker` containers via
  `docker-compose.yml` — never pushed through git or CI.
- **Previously**: Railway — `https://quickpaperai-production.up.railway.app/`. Kept warm as a
  fallback for now; decommission once OCI has proven stable under real usage.
  Uvicorn was started with `--timeout-keep-alive 120` there (generation can run past a minute;
  avoids socket drops on Railway's proxy) — same flag carried over to the OCI Dockerfile CMD.

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