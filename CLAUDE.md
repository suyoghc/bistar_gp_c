# bistar_gp_c — Claude Conventions

## Project

BI* and BMS* with Gaussian Processes (Chandramouli & Shiffrin, 2016, 2020). GP-backed Bayesian bias mitigation and model comparison.

## kb/ — Knowledge Base

Three-layer vault: `Raw/` (source material) → `Digests/` (analysis) → `Wiki/` (compiled articles).

```
kb/
├── Raw/papers/{arxiv,doi,important,sep}   PDFs, abstracts, metadata stubs
├── Raw/searches/                          Research search results
├── Raw/Claude Chat Artifacts/             54 parsed chat transcripts
├── Raw/WANTED.md                          Papers needing acquisition
├── Digests/Decisions/                     Per-transcript decision JSONs
├── Digests/Clippings/                     Per-paper-group summaries
├── Digests/GAPS.md                        Citation gaps
├── Wiki/                                  Compiled concept articles
└── pipeline/decision_pipeline.py          Extraction pipeline
```

### Frontmatter (keep light)

```yaml
# Raw files
title: "Paper title"
authors: ["Author A", "Author B"]
year: 2007
source_url: "https://..."
fetched: 2026-04-14
type: arxiv | doi | stub
status: unread | skimmed | extracted | synthesized | needs-pdf

# Wiki files
title: "Article title"
tags: [tag-a, tag-b]
sources: ["[[source1]]", "[[source2]]"]
last_updated: 2026-04-14
status: synthesized | generated
```

### Pipeline — Decision Extraction

`kb/pipeline/decision_pipeline.py` extracts decisions from transcripts, git history, and code:

```bash
python decision_pipeline.py scan                    # rank sources (free)
python decision_pipeline.py extract --top 10        # extract via claude CLI
python decision_pipeline.py extract --model opus    # use Opus for quality
python decision_pipeline.py fetch                   # populate Raw/papers/ from arXiv
python decision_pipeline.py wiki                    # generate Decision Provenance wiki
```

## Scripts — LLM Calls

All scripts call Claude via `subprocess.run(["claude", "-p", prompt])`. This uses the Claude Code Max subscription with no API key required. Do not add `import anthropic` to scripts.

```python
import subprocess

result = subprocess.run(
    ["claude", "-p", prompt, "--output-format", "json", "--model", "sonnet"],
    input=stdin_content,   # pipe long content via stdin
    capture_output=True, text=True, timeout=300
)
```

## Operations — read the skill file before executing

- **Ingest**: `.claude/skills/ingest.md` — add papers from WANTED.md to Raw/, update Wiki
- **Lint**: `.claude/skills/lint.md` — check for contradictions, orphans, gaps
- **Evidence tiers & citations**: `.claude/skills/evidence-tiers.md` — inline footnote format

## Paper Writing Resources

The user is preparing a journal paper on BI*/BMS*-GP. Before synthesizing any argument about design decisions, check these in order:

1. `kb/Wiki/Paper Writing Guide.md` — maps synthesis articles to paper outline v8 sections
2. `kb/Wiki/Metric Choice Justification.md` — KL to pw_nll to MLL-weighted aggregation, 6-part argument
3. `kb/Wiki/Vehtari-Gelman-Gabry Connection.md` — equation-level mapping to elpd/PSIS-LOO
4. `kb/Wiki/Criticisms of Pointwise Predictive Methods.md` — which LOO criticisms transfer to BMS*-GP
5. `kb/Wiki/Decision Provenance.md` — 244 decisions with full literature chains

These are pre-built for direct drop-in to the paper. Elaborate on them rather than starting fresh.

## Cross-Vault

kb/ structural conventions (ingest workflow, lint, evidence tiers) are documented in:
`OBS_ResearchDB/DECISIONS.md` (entries D7, D8, D11, D12, D18, D19).
That vault is the canonical home for cross-project kb/ organization decisions.

## Notes/ — Decision Log & Session Tracking

Convention adopted from `antagonistic_collab/Notes/`. Keep a lightweight paper trail so
design rationale survives across sessions. At the start of significant work, read recent
`Notes/DECISIONS.md` entries and `Notes/SCRATCHPAD.md` for context.

- **`Notes/DECISIONS.md`** — the decision log. When a non-trivial design or modeling choice is
  made, log it: numbered entries (`D1`, `D2`, …) with the date, `**Problem:**`, `**Decision:**`,
  `**Alternatives considered:**`, and optionally `**Result:**` / `**Status:**`. Include commit
  hashes, `file:line`, flags, and numbers so entries are self-contained — the log is the source
  text for commit messages. Update DECISIONS.md **in the same commit** that introduces the change,
  while context is fresh; do not defer to session end. Mark unresolved forks `(OPEN)` and update
  the entry when they close rather than adding a duplicate.
- **`Notes/SCRATCHPAD.md`** — working notes: current plan, open questions, in-progress state,
  active branches/PRs. Clean out completed items.
- **`Notes/CHATLOG.md`** — at the end of a session, append a dated summary: what was done, what
  was committed, and key discussion points.

Longer design specs live as dated docs under `docs/` (e.g. `docs/plan-zmx-laplace.md`);
`DECISIONS.md` links to them rather than duplicating their content.
