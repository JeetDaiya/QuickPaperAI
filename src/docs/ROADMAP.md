# Roadmap

Planned but not built. Don't implement any of this unless explicitly asked — it's here so an
agent doesn't mistake "there's a TODO for this" for "this is expected to exist."

- **Collaborative review / co-authorship**: shareable draft links with `view`/`comment`/`edit`
  permissions; `paper_shares` + `draft_comments` tables.
- **Preset templates**: save a subject/standard/chapters/difficulty config for reuse across
  semesters.
- **Searchable question bank / favorites**: let teachers star generated questions into a
  personal bank, searchable and reusable in future papers.
- **Fully decouple `DocumentCompiler` at the graph-runner level**: currently injected via
  `GraphConfig`, but `pdf_node` still knows a bit too much about compilation specifics; push
  that down into `src/paper/compilers/adapters/`.