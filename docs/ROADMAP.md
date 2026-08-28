# Roadmap

Planned but not built. Don't implement any of this unless explicitly asked — it's here so an
agent doesn't mistake "there's a TODO for this" for "this is expected to exist."

- **Collaborative review / co-authorship**: shareable draft links with `view`/`comment`/`edit`
  permissions; `paper_shares` + `draft_comments` tables.
- **Preset templates**: save a subject/standard/chapters/difficulty config for reuse across
  semesters.
- **Searchable question bank / favorites**: let teachers star generated questions into a
  personal bank, searchable and reusable in future papers.
- **REST error contract migration**: replace the `{"status": "failed"}` + HTTP 200 pattern with
  real `HTTPException(status_code=...)` responses; update the frontend TanStack Query layer to
  handle rejected promises centrally. (This is the same pattern flagged as a finding in the
  security/architecture audit — same fix either way.)
- **Fully decouple `DocumentCompiler` at the graph-runner level**: currently injected via
  `GraphConfig`, but `pdf_node` still knows a bit too much about compilation specifics; push
  that down into `src/paper/compilers/adapters/`.
- **Exception handling refactor in `SupabaseDatabase` adapters** (`src/db/adapters/supabase_db.py`):
  several methods (`get_fcm_token`, `get_notification_perms`, `update_notification_perms`,
  `save_fcm_token`, etc.) catch `Exception`, `print()` it, and return `False`/empty data instead
  of raising — routes then return `200 OK` with silently missing data. Caught in production when
  a wrong column name (`user_id` vs `id`) went unnoticed until logs were checked manually; a
  proper error contract would have surfaced it immediately. Same underlying issue as the "REST
  error contract migration" item above — worth doing together.