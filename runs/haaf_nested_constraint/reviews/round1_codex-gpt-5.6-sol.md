# Round-1 review — Codex gpt-5.6-sol xhigh, fresh session, repo access

REVISE

1. [severity S2] [experiments/haaf_nested_constraint.py:38] The canonical run has complete declared dependencies — `arviz` is imported unconditionally but absent from both `requirements.txt` and `pyproject.toml`, contrary to the work order, so a clean installation cannot run the experiment — add a compatible `arviz` dependency to both dependency manifests.

2. [severity S3] [docs/paper-sie-jmp/05-case-C-nested-constraints.md:58] `kl_forward` is appendix-only — the main Case C section reports its numerical result, violating W1 — remove this sentence from the main section and retain the result only in the run artifact or an existing appendix.

3. [severity S3] [docs/paper-sie-jmp/05-case-C-nested-constraints.md:22] Both fits use the same starts — the constrained optimization additionally receives every free-fit solution as an extra start at `experiments/haaf_nested_constraint.py:251`, while the free optimization initially uses only the four base starts — describe the shared base starts and asymmetric warm-start/candidate pooling accurately here and in `Notes/DECISIONS.md:5921`.