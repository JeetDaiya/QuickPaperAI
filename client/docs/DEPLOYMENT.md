# Deployment

Living document — reflects current deploy targets only. Update in place when something moves.

## Current status: deployed on Vercel

Live on Vercel as a static Vite SPA build (framework preset "Vite", build `vite build` /
`npm run build`, output `dist`). `vercel.json` at the repo root adds a catch-all rewrite
(`/(.*) -> /index.html`) — without it, Vercel serves by literal path, so a hard refresh (or a
deep link) on any client-side route like `/generate/<threadId>` 404s instead of reaching the
SPA's router. Don't remove that rewrite.

## What replacing it actually needs

This app is a **plain static Vite SPA** — no server, no API routes, no SSR — which makes it a
simpler deploy target than what it would replace, but the Vercel project config differs:

- **Framework preset**: must be set to "Vite" (build command `vite build` / `npm run build`,
  output directory `dist`). The old client's Nitro `preset: "vercel"` config
  (`client/vite.config.ts`) and its Build Output API v3 directory structure don't apply here —
  don't try to carry that config over.
- **Env var**: `VITE_API_BASE_URL` must point at the backend
  (`https://80-225-247-83.sslip.io/` as of the backend's current deploy, or whatever domain it
  moves to) — same variable name and purpose as the old client used. It is **required** for a
  production build: `http.ts` throws at startup if it's missing, so a deploy that forgets to set
  it fails loudly instead of shipping a bundle calling `localhost:8000`. `.env.example` is the
  tracked list of every variable this app reads; `.env` itself is gitignored.
- **Backend CORS**: the backend's `ALLOWED_ORIGINS` env var must include whatever origin this
  app ends up served from. No frontend-side config needed for this, just a backend env var
  update if the origin is new.
- Two ways to actually cut over — swap this app's contents into `QuickPaperAI/client/` in the
  existing repo (keeps the same Vercel project/URL/auto-deploy pipeline, just needs the
  Framework preset change above), or stand up a fresh Vercel project pointing at this repo and
  migrate the custom domain once it's verified. Neither has been done — this is a note for
  whoever does it, not a description of anything that's happened.

## Known gap vs. the old client

The old client has real browser push-notification wiring: `useFCMNotification`, `firebase.ts`,
a `firebase-messaging-sw.js` service worker, `VITE_FIREBASE_*` env vars. This app has the
**settings UI and backend calls** (`registerDeviceToken`, `getNotificationSettings`,
`updateNotificationSettings`) but not the actual FCM registration/service-worker flow — toggling
"Notify me" saves the preference but never registers a device to actually receive a push. Decide
whether this blocks a full cutover, or port it over separately, before relying on it.

## Local run
```bash
npm install
cp .env.example .env    # then set VITE_API_BASE_URL
npm run dev             # this app, must land on port 5173/8080/3000/8000 (see GOTCHAS)

# in ../QuickPaperAI, separately:
source /home/jeet-daiya/Storage/Teddy/venv/bin/activate
uvicorn src.app:app                              # API server
arq src.paper.worker.settings.WorkerSettings     # worker — required for generation to progress
                                                  # past "generating"; /api/resume and
                                                  # /api/generate just enqueue jobs
```
