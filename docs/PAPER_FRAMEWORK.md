# Paper framework — East River CO₂ subgrid closures (methods / diagnostics)

**Axes (nature-writing):** `task=manuscript`, `paper_type=methods`, `language=en` (with Chinese teaching report twin), `journal=generic` → target **Environmental Modelling & Software** (EMS). Not flagship *Nature*.

**Skill used:** `C:\Users\Administrator\.codex\skills\nature-writing\SKILL.md` (+ methods playbook). No pip install of “nature-skills”; Cursor/Codex skill set already present.

**ChatGPT advisor (web search ON):**  
1. Lit/journal: https://chatgpt.com/c/6a815d47-94ec-83ea-90fc-f12041638002  
2. Methods/Results (2026-08-16): https://chatgpt.com/c/6a818974-cd6c-83ea-8241-812dc9fd2598

---

## Chosen journal

**Primary (ChatGPT + accepted):** *Environmental Modelling & Software* — scope covers model evaluation, process identification, scale issues, and limitations of methods; fits a diagnostic negative result without forcing an “AI accuracy” story.  
**Alternate:** *Water Resources Research* (Methods) or *Global Biogeochemical Cycles* (East River audience; Saccardi & Winnick venue).  
**Avoid as lead:** “AI improves accuracy” ML venues.

## Template paper to imitate (structure)

**Primary structural exemplar (ChatGPT):** Markovich, White & Knowling (2022), *Environ. Model. Softw.* 156, 105498 — DOI https://doi.org/10.1016/j.envsoft.2022.105498 (verify before submission). Imitate **argument architecture**: controlled model-error problem → calibration vs prediction → parameter compensation diagnosis → implications for model use.  
**Domain Methods depth borrow:** Saccardi & Winnick (2021, GBC) for river-network CO₂ process writing, but **replace** their “improved prediction” lead with nested-CV falsification + equifinality.  
**Filter-scale borrow:** Yuval & O’Gorman (2020, Nat Commun) coarse-graining mindset.

**Results as three falsification tests:**  
H1 Transferability (Residual-AI vs Baseline) → fail; H2 Compensability (\(k\)-correction lowers C RMSE) → superficial pass; H3 Process consistency (flux/\(k\) plausibility) → fail.

Section order follows nature-writing **methods** playbook: Methods → Results → Introduction (retrospective) → Discussion → Conclusion → Abstract/Title last.

---

## Novelty statement (honest)

> We operationalize an LES-analog spatial filter for river-network CO₂ mass balance, evaluate residual and \(k\)-correction closures with **transport-coupled nested leave-one-reach-out CV**, and show **practical equifinality** of \(S_\mathrm{sgs}\) and \(k\) under concentration-only observations: Residual-AI does **not** beat Baseline on held-out \(C_\mathrm{aq}\) (RMSE 0.0573 vs 0.0284), while a modest \(k\)-correction C-RMSE gain **coincided with** a collapse of modelled evasion flux (not claimed as a uniquely proven causal pathway).

**Not claimed:** AI improves accuracy; continental CH₄; CONUS training.

---

## Section-by-section architecture

| Section | Job | Evidence |
|---------|-----|----------|
| **Title** | Multiscale filtering + identifiability of subgrid closures… | — |
| **Abstract** | Problem → method → nested-CV negative → equifinality → implication | Frozen metrics |
| **Significance / Highlights** | Protocol + identifiability, not RMSE medal | 3 bullets |
| **Introduction** | River CO₂ networks → unresolved subgrid → ML closures risk overfitting → need transport-coupled holdout | Verified lit |
| **Methods** | Data (HydroShare, USGS, NHD); 1D quasi-steady; Raymond \(k\); residual \(S_\mathrm{sgs}\); filter \(\Delta x\); nested CV; sparse Π | Code stages 01–15 |
| **Results** | (1) Nested CV accuracy failure (2) Filter-scale \(\|S_\mathrm{sgs}\|\) (3) Sparse Π form (4) \(k\)–flux collapse (5) Identifiability plots | Figs 1–7 + tables |
| **Discussion** | Practical equifinality; need independent flux/\(k\) constraints; appendix \(R^2\) warning | Engineering notes |
| **Conclusion** | Contribution = diagnostics | — |
| **Appendix** | In-sample \(R^2=0.997\) as overfit portrait | Fig A1 |

## Figure map (paper)

1 LES conceptual · 2 GIS network/samples · 3 Nested-CV RMSE · 4 Holdout scatter · 5 Identifiability · 6 Filter-scale · 7 Sparse Π · S1–S4 supporting · A1 in-sample

## Results lead order (frozen)

1. Residual-AI worse than Baseline on holdout \(C_\mathrm{aq}\)  
2. Filter-scale dependence of \(\|S_\mathrm{sgs}\|\)  
3. Sparse Π (interpretable, weak nested CV)  
4. \(k\)-correction: better C, collapsed \(F_{\mathrm{CO}_2}\)  
5. Integrated identifiability diagnosis
