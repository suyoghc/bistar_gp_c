# Round-1 review — Codex gpt-5.6-sol xhigh, fresh session, repo access

REVISE

1. [severity S2] [docs/paper-sie-jmp/02-machinery.md:39] \(\bar G(\phi)\) “averages \(G\) across data patterns” — the referenced implementation evaluates \(G\) once against a moment-matched `avg_gp`, which generally differs from \(E_\psi[G(\psi,\phi)]\), including under `pw_kl_vcal` — define the implemented estimand as \(G(\bar\psi,\phi)\), or explicitly identify moment matching as an approximation to the theoretical average.

2. [severity S2] [docs/paper-sie-jmp/02-machinery.md:65] pooled soft transfer recovers hard best-match assignment as \(\tau\) approaches zero — pooled aggregation is dominated by the globally smallest absolute divergences, not each draw’s winner; Case A directly demonstrates this distinction — restrict the hard-assignment limit to row-min and expected-posterior aggregation under unique per-draw winners, and state the pooled limit separately.

3. [severity S3] [docs/paper-sie-jmp/02-machinery.md:34] the projection equivalence is presented as an empirical mechanism check — `experiments/mechanism_figure_poster.py` is absent from the branch and all four case branches, its local version does not invoke `projection_metric_check()` from its entry point, and no result artifact exists — recast this as the algebraic equivalence that holds when each pattern has constant variance across locations, and remove the unsupported check citation.

4. [severity S3] [docs/paper-sie-jmp/08-discussion.md:26] neither LOO nor the table path “credits” the satisfied constraint — Case C’s LOO point estimate has a constrained-favoring direction but is inferentially inconclusive, while its negligible excluded-mass diagnostic is only a local full-data Gaussian approximation, not a fold-posterior result — say neither method provides a reliable or automatic restriction preference in this example and preserve the diagnostic’s stated limitation.

5. [severity S3] [docs/paper-sie-jmp/08-discussion.md:116] Case D leaves an F1-versus-F2 mechanism ambiguity — the case explicitly leaves four sources unresolved: F1, F2, metric behavior, and sampling noise — add the latter two so the synthesis does not narrow the case’s causal non-identifiability.