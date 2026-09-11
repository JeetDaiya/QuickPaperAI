# Roadmap

Planned-but-not-built. Don't build any of this unless explicitly asked — it's here so an agent
doesn't reinvent it independently or assume it's already covered.

- **FCM push notifications** — the settings toggle and backend calls exist
  (`registerDeviceToken`, `getNotificationSettings`) but there's no actual browser
  registration/service-worker flow. See `docs/DEPLOYMENT.md` → "Known gap vs. the old client"
  for what the old client had that this one doesn't.
- **Deployment** — not deployed anywhere yet; not even in a git repo. See
  `docs/DEPLOYMENT.md`.
- **"Remove draft" UI action** — `removeDraft()` exists in `lib/drafts.ts` and is wired to
  Cancel Generation, but there's no explicit "dismiss this draft" button on the Dashboard's
  Recent Drafts list (matches the old client, which also never exposed one in its UI).
- **Templates nav item** — `AppShell` doesn't currently have a "Templates" link (the old
  client's sidebar mockups had one); no backend endpoint exists to support it, so it's not
  planned unless the backend grows one.
