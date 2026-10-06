# Literature notes — river-network CO₂ closures (methods framing)

**Updated:** 2026-08-16 (Methods/Results ChatGPT pass)  
**Policy:** ChatGPT Pro = external literature/writing advisor (web search ON, text only). All DOIs **independently re-checked** by the executor.

## ChatGPT dialogs

| # | Purpose | URL | Web search |
|---|---------|-----|------------|
| 1 | Lit + journal + negative-result framing | https://chatgpt.com/c/6a815d47-94ec-83ea-90fc-f12041638002 | YES |
| 2 | **NEW** Methods/Results EMS critique + DOI check | https://chatgpt.com/c/6a818974-cd6c-83ea-8241-812dc9fd2598 | YES — UI “已搜索 21+ 个网站” |

Dialog 2 title in UI: **EMS论文审阅与改进**.

## ChatGPT framing accepted this pass (dialog 2)

1. Keep EMS methods/diagnostics + “failure as diagnosis”; do **not** pivot to AI accuracy win.
2. Novelty triad: filter definition + transport-coupled nested CV + practical equifinality (not “first East River CO₂ model”).
3. Soften causal wording: k-correction C gain **coincided with** flux collapse (not “only by”).
4. LES-analog firewall: coarse-graining analogy only; S_sgs = filter-induced residual.
5. Nested CV anti-leakage protocol must be mechanical; evaluate coupled C_aq.
6. Use **practical equifinality**, not formal structural non-identifiability.
7. Rename H1 to held-out reach generalization (not universal transferability theorem).

## ChatGPT suggestions rejected / deferred

| Item | Decision |
|------|----------|
| Any “AI improves accuracy” | **Rejected** |
| Formal structural non-identifiability claim | **Rejected** |
| “First LES / first AI subgrid river-C model” | **Rejected** |
| Treating sparse Π as automatically “interpretable” | **Rejected** (keep “compact / form-interpretable candidate”) |
| Rewriting equation purely for elegance without matching code | **Rejected** — lock to `src/03_baseline_transport.py` (A_s=L×W) |
| Expanding to CH₄ / CONUS / StreamPULSE coverage | **Rejected** |
| Post-hoc k-regularization presented as original success | **Rejected** (sensitivity only if ever added) |

## Independently verified citations

| Citation | Role | DOI / URL | Status |
|----------|------|-----------|--------|
| Saccardi & Winnick (2021) GBC | East River backbone | https://doi.org/10.1029/2021GB006972 | **Verified** |
| Raymond et al. (2012) L&O F&E | k₆₀₀ scaling | https://doi.org/10.1215/21573689-1597669 | **Verified** |
| Yuval & O’Gorman (2020) Nat Commun | Subgrid ML analogy | https://doi.org/10.1038/s41467-020-17142-3 | **Verified** |
| Battin et al. (2023) Nature | Broader C context | https://doi.org/10.1038/s41586-022-05500-8 | **Verified** |
| Gómez-Gener, Rocher-Ros et al. (2021) Nat Geosci | Flux / diel bias | https://doi.org/10.1038/s41561-021-00722-3 | **Verified** |
| Hotchkiss et al. (2015) Nat Geosci | CO₂ source partitioning | https://doi.org/10.1038/ngeo2507 | **Verified** (this pass) |
| Xie et al. (2022) Nat Commun | Dimensionless / sparse learning | https://doi.org/10.1038/s41467-022-35084-w | **Verified** (this pass) |
| Markovich, White & Knowling (2022) EMS | Structure exemplar | https://doi.org/10.1016/j.envsoft.2022.105498 | **Verified** |
| Bennett et al. (2013) EMS | Evaluation philosophy | https://doi.org/10.1016/j.envsoft.2012.09.011 | **Accepted Round 1** (DOI cited by ChatGPT; use as structure/philosophy) |
| Vilas et al. (2023) EMS | Discrepancy-as-diagnosis | https://doi.org/10.1016/j.envsoft.2023.105668 | **Accepted Round 1** |
| Gao et al. *The Innovation* draft | Inspiration only | Unpublished | **待补充** DOI |

## Locked project numbers (do not rewrite)

- Nested CV loo-reach: Baseline C_aq RMSE **0.0284**; Residual-AI MLP **0.0573** (worse); RF **0.0745**.
- k-correction: C RMSE **0.0244** with **median** k_eff/k_emp **≈3.4×10⁻⁴**; F_CO₂ total diagnostic **3.24 → ~0.03**.
- Filter-scale mean |S_sgs| **1.92 → 1.00** (mol m⁻² d⁻¹ scale; see filter table).
- In-sample Residual-AI R²≈0.997: **appendix only**.

## Units lock (code-aligned)

From `src/03_baseline_transport.py`: water-surface area A_s = L×W; areal fluxes in mol m⁻² d⁻¹; Q in m³ s⁻¹; C in mol m⁻³; k in m d⁻¹.
