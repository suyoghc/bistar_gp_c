# Round-1 review — Gemini 3.1 Pro (package-only, thinkingLevel HIGH)

APPROVE

**1. Clean Verification: Prose numbers against JSON (Section 07.1)**
Every number reported in the text was verified against `runs/toy_debias_demo/results.json`. The rounding is exact across the board (e.g., `0.32299` rounds to `0.323`, `1.43039` rounds to `1.430`). Values such as the 71.9% RMSE reduction and the grid coverage (174 of 201 points) match the arithmetic of the JSON outputs. 

**2. Clean Verification: Exact mixture-interval construction**
The `mixture_central_interval` function robustly determines mixture bounds via CDF bisection on an equally-weighted Gaussian mixture (utilizing `ndtr`). The bounded search space initialized at $\pm 12 \sigma$ is deeply conservative, and the 100-iteration depth is sufficient for exact convergence. Avoiding a simplistic normal approximation appropriately preserves the fat tails resulting from hyperparameter uncertainty.

**3. Clean Verification: Law of Total Variance slope sd**
The `total_variance_sd` helper accurately implements the continuous decomposition $\text{Var}(X) = E[\text{Var}(X|Y)] + \text{Var}(E[X|Y])$ via `var_draws.mean() + mean_draws.var()`. Furthermore, reading the slope variance directly off the $k(x,x') = v x x'$ kernel component using `xg[var_idx] ** 2` safely limits evaluation to $|x| \geq 1.0$ to bypass zero-division instability. Checking max deviations (`max_rank_one_dev`) explicitly guarantees that reading the component covariance output respects the mathematical properties of `LinearKernel`. 

**4. Clean Verification: MAP-init and R-hat framing**
The text is scientifically honest regarding its initialization: "rank-normalized R-hat reported here measures mixing within the mode the optimizer selected and not agreement between dispersed starts." This appropriately limits diagnostic confidence to within-mode exploration, fully acknowledging the posterior's multi-basin geometry (D12) instead of presenting low R-hat as proof of global coverage.

**5. Clean Verification: RMSE comparison and scale references**
Section 07.1 properly anchors its findings: framing the 1.430 composite RMSE against the baseline 1.451 displacement drift, and juxtaposing the remaining 0.403 debiased discrepancy against the 0.690 signal RMS. It resists claiming perfect debiasing, framing it instead as removing "most of it" while plainly acknowledging that the residual is "not negligible."

**6. Clean Verification: Coverage caveat**
The text accurately characterizes the 0.866 nominal 0.95 interval coverage as "mild undercoverage." Importantly, the disclosure that "neighboring grid points share nearly the same posterior" rightly prevents the reader from mistaking 201 correlated pointwise grid checks for 201 independent calibration trials.

**7. Clean Verification: Band-width and uncertainty-floor reading**
Section 07.2 notes the debiased band width (1.836) is wider than the composite band (1.032). The script and text properly identify this as the consequence of anti-correlation between unidentifiable additive components: the data bounds the sum sharply, but assigns a persistent uncertainty floor to the unobserved parts. This provides airtight mathematical support for the expectation established in Section 8.5.

**8. Clean Verification: Style and scope constraints**
An audit of `docs/paper-sie-jmp/07-debias-bridge.md` confirms total compliance with hard constraints: 
- There are no arrow glyphs in prose.
- There are zero occurrences of "lives" or "sits".
- Em-dashes are excluded from the main prose. 
- The text strictly avoids "X is the Y" role-noun phrasing for modeling constructs (favoring careful language such as "treated as the truth candidate" or "identifying the linear component as bias is a modeling choice"). 
- No Mauna Loa data is cited or tested, leaving the preregistration boundary uncompromised.