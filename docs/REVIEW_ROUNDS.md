# Review rounds — Cursor ↔ ChatGPT (EMS manuscript maturation)

**Dialog:** https://chatgpt.com/c/6a818974-cd6c-83ea-8241-812dc9fd2598  
**Prior dialogs:** https://chatgpt.com/c/6a809d47-8f3c-83ea-af37-a6a1f643f726 , https://chatgpt.com/c/6a815d47-94ec-83ea-90fc-f12041638002  
**Public repo given to ChatGPT:** https://github.com/Coucou2016/river-carbon-transport (`main` @ `03ce613` at start; Round 7+ uses Markdown briefs under `docs/chatgpt/`)  
**Policy:** ChatGPT = external text advisor; no file uploads — prefer GitHub Markdown URLs. Local verification before every edit. Frozen metrics never contradicted.  
**Paper vs report:** Paper must not contain local paths / `.venv` / pipeline script filenames as process narrative; report may keep teaching-style process detail.

| Round | Focus | Status |
|------:|-------|--------|
| 1 | Repo-level architecture / novelty / EMS exemplars | Done |
| 2 | Abstract + Introduction | Done |
| 3 | Methods (equations, CV, units) | Done |
| 4 | Results + Discussion | Done |
| 5 | EMS referee simulation | Done — MAJOR REVISION |
| 6 | Title / keywords / cover letter / DOI checklist | Done |
| 7 | Paper↔report audit + GitHub Markdown briefs | Done (2026-08-17) |
| 8 | EMS Abstract/Intro/Discussion prose rewrite | Done |
| 9 | Data integrity + Methods consistency (no script paths) | Done |
| 10 | Repo-level style review (AI-tell + exemplar comparison) | Done (2026-08-18) |
| 11 | Abstract + Introduction rewrite | Done (2026-08-18) |
| 12 | Methods clarity + notation/units | Done (2026-08-18) |
| 13 | Results/Discussion prose + claims audit | Pending |
| 14 | Full referee pass + consistency sweep | Pending |
| 15 | Re-review of final text (if needed) | Pending |

**Round 7 context delivery:** https://github.com/Coucou2016/river-carbon-transport/tree/main/docs/chatgpt/  
Files: `00_TASK_BRIEF.md`, `01_PAPER_CURRENT.md`, `02_REPORT_VS_PAPER_AUDIT.md`, `03_DATA_INTEGRITY_CHECKLIST.md`, `04_QUESTIONS_FOR_CHATGPT.md`.  
**Round 10+ briefs:** `06_ROUND10_CONTEXT.md`, `07_ROUND10_PAPER_FULL.md` (commits `d867d84`, `33a6d40`); `08_ROUND11_ABS_INTRO.md` (Round 11); `09_ROUND12_METHODS.md` (commit `88e4f8f`); `10_ROUND13_RESULTS_DISCUSSION.md` (commit `cfd7441`).

---

## Round 10 — Repo-level style review (AI-tell audit + exemplar comparison)

**Sent:** Briefs 06/07 + `paper.md` URLs at commits `d867d84`/`33a6d40`; Q10.1–Q10.5 (section verdicts, top-10 AI tells, Fraehr/Markovich length comparison, Phrasebank/humanizer checklist application, borrowed-data integrity spot-check).

**ChatGPT browsed GitHub?** YES — confirmed reading the commit-pinned manuscript, both Round-10 briefs, and `docs/RESEARCH_INTEGRITY_AUDIT.md`. Web search used (Fraehr WRR exemplar, Markovich EMS exemplar, Purdue OWL, Manchester Academic Phrasebank, AI-tell literature).

**Verdict:** rewrite worked; manuscript is "submission-near but not final"; remaining issues are concentrated editorial scaffolding, not pervasive AI-ness.

**ACCEPTED (merged into `scripts/generate_paper.py`):**
- Removed PySINDy engineering-history residue (Methods 2.8 + Table 8 caption): state only that standardized LASSO was used.
- Deleted meta-narration: "The role of Eq. (1) in the design...", "The results follow an evidence ladder..." roadmap, "Two data boundaries...", "Two boundaries of the protocol..." checklist cadence; replaced with direct statements.
- Collapsed defensive boundary policing in 2.3 (single boundary sentence for the LES analogy) and 2.7 (one qualifier instead of rebuttal-style "not a formal proof").
- Replaced self-referential contribution triad ("The contribution is methodological...") in Abstract and Intro with direct statements of what the study establishes/tests.
- Merged Discussion 4.2+4.3 → "4.2 Process allocation and practical equifinality"; merged 4.4+4.5 → "4.3 What filtering and sparse representation reveal about the residual"; kept 4.1 and 4.6 (now 4.4). Six subsections → four.
- Rewrote Conclusions from three-item research-summary cadence into two compact synthesis paragraphs.
- Phrasebank-calibrated hedging: "does not distinguish" → "provides limited discrimination between"; "switches gas exchange almost off" → "gas exchange is reduced to nearly zero"; "is therefore driven by" → "is concentrated in"; "does not prove" patterns softened; KP3 now says "model-derived CO₂ flux diagnostic".
- PLS causal phrasing "only by reducing" → "while the modeled CO₂ release was reduced".
- Trimmed Abstract (~277 → ~250 words); moved WQP/StreamPULSE negatives out of Data availability (already in Methods 2.1 and Discussion limits).

**REJECTED:** none material. (Did not restructure Results 3.2/3.3 into one section: keeping them separate preserves the figure anchors; ChatGPT marked that split "defensible". Did not move the WQP/StreamPULSE statements out of Methods 2.1, because they document covariate constraints for the closures.)

**Integrity spot-check result:** no borrowed-data sentences found; provenance citations retained (Saccardi & Winnick tributary values, HydroShare/NHD inventories, USGS gage, Raymond k600 attribution). Softened the one causal claim about sparse tributary data "driving" the Residual-AI degradation to an association.

**Verification:** regenerate PASS; frozen numbers all present (0.0284×11, 0.0573×7, 0.0745×4, 0.0244×7, 0.0506×3, 3.35×3, 3.24×7, 0.031×5, 1.916×2, 1.000×8, sparse coefficients ×2 each, 0.997×3); base64 figures = 13; zero http in img/link/script; em-dash count = 0; PySINDy mentions = 0; no local paths.

---

## Round 11 — Abstract + Introduction rewrite (Fraehr rhythm)

**Sent:** Brief `08_ROUND11_ABS_INTRO.md` (current Abstract + Introduction text) plus Q11.1–Q11.3: full Abstract rewrite (~210–240 words, Fraehr rhythm problem → prior work → what this study does → frozen-number results → single implication), full 5-paragraph Introduction rewrite (650–800 words, ending with the testable question instead of a contribution list), and a formulaic-sentence audit table.

**ChatGPT browsed?** YES — re-browsed the Round-11 brief and web-searched style benchmarks (Fraehr WRR, AGU, ScienceDirect, Nature, ASLO, Purdue OWL). Confirmed reading via GitHub citation chips.

**ACCEPTED & MERGED into `scripts/generate_paper.py` (Abstract + both ABSTRACT/ABSTRACT_HTML strings + 5 Intro CONTENT paragraphs):**
- Abstract (225 words): prior-work gap inserted before implementation; negative Residual-AI result stated directly ("performed worse than the Baseline"); sparse-RMSE 0.0506 added; ends with one inference sentence ("These results indicate practical equifinality ... so lower concentration error alone is insufficient ...") instead of the contribution-list sentence. All frozen numbers retained exactly.
- Introduction (≈768 words, 5 paragraphs): (1) river-carbon context ending on the compensation risk; (2) Saccardi–Winnick + Raymond prior work with the explicit point that k-parameterization does not remove uncertainty in other balance terms; (3) Bennett/Vilas/Markovich posed as an evaluation problem with the test stated directly; (4) learned subgrid closures (Yuval, Gao in preparation) with a single strategic "not whether … but whether" contrast; (5) what the study does, all four boundaries stated as concrete sentences, ending with the testable question. All citations retained.
- ChatGPT's formulaic-sentence audit table (10 replacements) recorded verbatim above for traceability.

**Local verification of ChatGPT's factual additions before merging:**
- "solver uses observed C_aq as a fallback when an upstream state is unavailable" → verified in `src/03_baseline_transport.py` (`c_in` fallback branch).
- "coordinate-based fallback rather than a complete directed network topology" → consistent with existing Methods 2.3 disclosure (midpoint Y-then-X ordering fallback).
- Citations Hotchkiss/Gómez-Gener/Battin/Raymond/Saccardi/Bennett/Vilas/Markovich/Yuval/Gao all already in REFERENCES.

**REJECTED:** none material. (ChatGPT's proposed notation "(S_{sgs})" LaTeX-style brackets were adapted to the generator's plain `S_sgs` / HTML `S<sub>sgs</sub>` convention; "Residual-AI" terminology kept because it is the paper's established configuration name.)

**Verification:** regenerate PASS (HTML 4.71 MB, MD 41.7 KB); frozen numbers all present (0.0284×11, 0.0573×7, 0.0745×4, 0.0244×7, 0.0506×4, 3.35×3, 3.24×7, 0.031×5, 1.92×1, 1.00×10, 838×4); base64 figures = 13 in HTML (MD keeps file references by design); zero external http in md img/links and html img/link/script; no `D:`/`.venv`/`scripts/` narrative; em-dash count = 4 (table/appendix formatting, none in new prose); mean sentence length ≈ 23.3 words.

---

## Round 12 — Methods clarity + notation/units (code-verified merge)

**Sent:** Brief `09_ROUND12_METHODS.md` (Methods 2.1–2.8 verbatim + plain-text equations) with Q12.1–Q12.4: under-explanation audit, Eq. (1)/(4)/(2)/(5)/(6)+k600 unit check, paragraph-level clarity actions, and five likely reviewer questions. One scope note was sent first because the shared dialog had been polluted by an unrelated WRR review message from a separate task.

**ChatGPT browsed?** YES — browsed the public repo at commit `f99e66d` (GitHub citation chips) including `src/02_build_network.py`, `src/05_compute_residual_sgs.py`, `src/12_nested_cv_transport.py`, `src/13_filter_scale_sgs.py`, `src/15_dimensionless_sparse.py`, `src/utils.py`, and the config. Web search not needed this round.

**Two P0 implementation findings (code-verified, see integrity audit):**
1. The Residual-AI / sparse-Π training target in `src/05_compute_residual_sgs.py` adds an areal-flux term (mol m⁻² d⁻¹) to a concentration-difference term (mol m⁻³), so the computed target is not exactly Eq. (4) as written. The frozen results were generated with this target; fixing the target would change frozen numbers, which is out of scope. Prose now discloses the mismatch (Methods 2.4) and the integrity audit records it as a known limitation.
2. `Da` and `k·τ/h` in `src/05_compute_residual_sgs.py` multiply τ in seconds by k in m d⁻¹, so these two candidates are not strictly dimensionless. LASSO selection dropped both terms anyway; the retained law uses only Fr, slope, and h/W. Disclosed in Methods 2.8.

**ACCEPTED (merged into `scripts/generate_paper.py`, every claim first verified against `src/`):**
- 2.1: width proxy made quantitative (coordinate span / sample count, clipped 2–15 m; W = 5 m for single-sample reaches); Manning depth h = [Qn/(W·S^0.5)]^0.6, n = 0.035; u = Q/(Wh); flagged model-derived. Verified against `src/east_river_real_data.py` (manning_depth, clip bounds, lon-span width).
- 2.2: removed the capital-U/lowercase-u collision (bulk velocity u = Q/A_c); stated observed-vs-solved roles of C and diagnosed-vs-predicted roles of S_sgs; added Schmidt-number statement; corrected the C_eq sentence to "Henry's law with atmospheric pCO₂ and a constant Henry coefficient" (verified: `src/utils.py` co2_eq_concentration ignores temp_c).
- 2.3: filter operators stated explicitly (native, pairs, groups of four, whole reach); Y-then-X fallback ordering; Δx defined as the sample-weighted mean of attached cell lengths (Δx ≈ 838 m at native; 7 cells, 6 with samples at study-reach scale); added the per-date upstream C_in rule with fallback. Verified against `src/13_filter_scale_sgs.py` and `results/tables/filter_scale_metrics.csv`.
- 2.4: full predictor pool enumerated (hydraulics + T + DOC/DO/pH + dimensionless; wholly absent fields excluded; fold-median imputation); MLP 64/32/16, lr 0.001, early stopping, fold standardization, non-negative output; RF 200 trees / depth 12, unscaled; XGB 300/6/0.05 seed 42. Verified against `configs/east_river.yaml`, `src/ml_models.py`, `src/12_nested_cv_transport.py` (feature_columns, make_*).
- 2.4: k-correction target mechanics added (invert balance at observed C with S_sgs = 0 for k_need; g = ln(k_need/k_emp); k_eff = k_emp·exp(g)); plus the honest caveat that k_need is built from observations before the fold loop (verified: `invert_k_needed` runs before the fold loop and uses observed upstream concentrations).
- 2.4: training-target disclosure paragraph (see P0-1 above).
- 2.5: replaced generic "feature scaling" with the accurate fold mechanics: fold-median imputation; standardization only for MLP and LASSO; closure predicted for the full network, whole network re-solved, then held-out rows scored (verified in `grouped_holdout_predictions`).
- 2.7: Eq. (5) uses observed C_aq (verified: `src/14_identifiability_ksgs.py` builds S_implied from C_aq_obs).
- 2.8: rewritten with verified sparse mechanics: S* = S_sgs/(k_emp·C_eq); five candidates Fr, slope, h/W, log₁₀Re, log₁₀Da; per-fold scaler+LASSO refit (α = 0.05) for transport evaluation; frozen coefficients are a descriptive full-data refit, not a median fold law; Da-construction caveat (see P0-2 above). Verified in `src/15_dimensionless_sparse.py` (fit_sparse alpha=0.05, full-data refit for display).
- Notation: SPARSE_EQ rewritten to S* ≈ 1.059 + 1.536·Fr_z − 1.669·Slope_z − 2.179·(h/W)_z (subscript z = standardized predictors only, because the response is not z-scored in code); 3.5 prose aligned with the descriptive-refit interpretation.
- Equations renumbered sequentially in order of appearance: (1) mass balance, (2) area-normalized form, (3) F_CO₂, (4) residual diagnosis, (5) S_implied; all cross-references updated.

**REJECTED / deferred:**
- REJECTED: ChatGPT's proposal to rename the displayed law "median law" — verified the frozen coefficients come from a single full-data refit, not a median over folds; prose now says so instead.
- REJECTED: fixing the P0 code units now — would change frozen results (0.0573/0.0745/0.0506 and the sparse law), which is out of scope; disclosed in prose + audit instead.
- DEFERRED: the C_eq temperature-dependence appendix and a supplementary parameter table (kept as 待补充).

**Verification:** regenerate PASS (HTML 4.71 MB, MD 46.7 KB); frozen numbers all present (0.0284×11, 0.0573×7, 0.0745×4, 0.0244×7, 0.0506×4, 3.35×3, 3.24×7, 0.031×5, 1.916×2, 1.00×10, 838×5); base64 figures = 13 in HTML (MD keeps file references by design); zero external img/link/script http; no `D:`/`.venv`/`scripts/` narrative; em-dash count = 4 (tables only, none in prose); mean sentence length ≈ 24.7 words.

---

## Round 7 — Paper↔report + integrity (GitHub Markdown)

**Sent:** Pointed ChatGPT to `docs/chatgpt/*` + `paper.md` at commit `72b37f3` (no uploads). Questions 1–4.

**ChatGPT browsed GitHub?** **YES** — tree + all five briefs + `paper.md` + `PAPER_FRAMEWORK.md` + `REVIEW_ROUNDS.md` + commit `72b37f3` (multiple GitHub chips).

**ACCEPTED:** Strip all `src/*.py` / `scripts/*.py` process narrative from paper; move teaching five-part figure notes to report; synchronize title away from “physics-constrained ML”; prefer leave-one-reach-out over “nested CV”; tighten flux-diagnostic Highlights; keep novelty order protocol→filter→equifinality; WQP/StreamPULSE as resolved negatives not 待补充.

**REJECTED / deferred:** Topology rewrite; inventing width-sensitivity / fold RMSE; promoting R²; claiming process fidelity proved/disproved by F diagnostic.

**Local fixes:** `scripts/generate_paper.py` (no teach blocks; sanitize table leads; remove script citations; CN title aligned); `docs/PAPER_FRAMEWORK.md` (removed local skill path); `docs/chatgpt/00_TASK_BRIEF.md` (nested-CV wording).

---

## Round 8 — Abstract / Intro / Discussion prose

**Sent:** Questions 5–7; web search ON for Markovich/Bennett/Vilas.

**ChatGPT browsed?** YES (briefs + ScienceDirect exemplars).

**ACCEPTED & MERGED:** Full EN Abstract (~200 words); Chinese twin as non-submission companion; 5-paragraph Intro; Discussion 4.1–4.6; 3 Highlights. LES demoted; physics-constrained ML removed.

**REJECTED:** Any claim Residual-AI improves accuracy; F as observed flux; structural non-identifiability.

---

## Round 9 — Data integrity + Methods/Results consistency

**Sent:** Questions 8–10.

**ChatGPT browsed?** YES (`03` + `04` raw). Noted public `paper.md` not yet updated at ask time.

**ACCEPTED:** Methods wording for grouped CV / c_in / logical reaches / Y→X / width proxy / F diagnostic; Results lead H1→H2→H3→compensation→filter→sparse Π; WQP/StreamPULSE = resolved negative availability; Vilas reference title corrected to *TALKS…* (DOI 105668).

**DEFER:** Width-sensitivity table; fold RMSE; full C_eq appendix; Gao DOI.

**Local fixes:** Methods 2.5–2.6; Results lead; Data availability phrasing; Bennett+Vilas refs added; regenerate `paper.html`/`paper.md`.

---

## Round 1 — Repo-level review

**Sent (summary):** Public GitHub URL; ask to browse `docs/PAPER_FRAMEWORK.md`, `ENGINEERING_NOTES.md`, `LITERATURE_NOTES.md`, `paper.md`, `scripts/generate_paper.py`, `src/`; critique architecture, novelty, negative-result framing for EMS; request structural exemplars with DOIs; top-5 priorities. Web search ON.

**ChatGPT browsed GitHub?** **YES.** Confirmed latest public commit `03ce613` (2026-08-16). Cited files opened/read via GitHub: `docs/PAPER_FRAMEWORK.md`, `docs/ENGINEERING_NOTES.md`, `paper.md`, `src/12_nested_cv_transport.py`, `src/13_filter_scale_sgs.py`, baseline transport paths. Multiple GitHub citation chips in the reply.

**Key advice:**
1. Negative result is a genuine EMS contribution only if framed as **diagnostic protocol + what it reveals**, not “ML scored worse.”
2. Safer novelty hierarchy: **evaluation protocol → filter-induced residual → empirical compensation diagnosis**; demote “LES-analog” from headline into Methods.
3. Prefer “practical equifinality / closure compensation / identifiability limits” over bare “identifiability”; prefer “transport-coupled” over headline “physics-constrained ML.”
4. Structural exemplars: **Markovich et al. 2022** DOI `10.1016/j.envsoft.2022.105498` (confirmed); add **Bennett et al. 2013** `10.1016/j.envsoft.2012.09.011`; **Vilas et al. 2023** `10.1016/j.envsoft.2023.105668`.
5. Top blockers: (a) audit whether held-out `C_aq` can enter transport via `c_in` fallback; (b) filter Y→X midpoint ordering vs network topology; (c) terminology rewrite; (d) `paper.md` too thin vs prose in `generate_paper.py`; (e) report reach-level imbalance, not only pooled RMSE.
6. Do not use unpublished Gao *Innovation* draft as novelty boundary.

**Local verification:**
- `c_in` fallback to current-row observed `C_aq` when upstream missing: **CONFIRMED** (`src/03_baseline_transport.py` L82–86; similar pattern in `src/12` invert and `src/13`).
- Filter “along-reach chainage” with midpoint Y then X fallback: **CONFIRMED** (`src/13_filter_scale_sgs.py`).
- Outer leave-one-group-out + fold-specific imputation exists; explicit inner hyperparameter nest not found — clarify naming rather than discard protocol.
- Frozen metrics still: Baseline 0.0284; Residual-AI MLP 0.0573; RF 0.0745; k-corr 0.0244; F totals 3.24→0.031.

**ACCEPTED:** novelty hierarchy; terminology; Bennett/Vilas exemplars; Methods disclosure of `c_in` fallback and filter-ordering boundary; enrich `paper.md` / docs; emphasize R008 imbalance; keep Gao as 待补充 DOI only.

**REJECTED / deferred:** full network-topology filter rewrite this round (would change frozen Δx metrics); claim that outer LOO is scientifically invalid (clarify “outer leave-one-reach-out + fold scaling” instead); drastic cut of figure count in this pass.

**Changed locally (this round batch):** `docs/REVIEW_ROUNDS.md` (this file); updates to `docs/PAPER_FRAMEWORK.md`, `docs/ENGINEERING_NOTES.md`, `docs/LITERATURE_NOTES.md`, `scripts/generate_paper.py`, `paper.md` (see Round 2+ for Abstract/Intro text).

---

## Round 2 — Abstract + Introduction

**Sent (summary):** Confirmed Round-1 accept/reject decisions with local `c_in` / filter audits; pasted current Abstract + Intro skeleton; requested EN≤250-word rewrite + Chinese twin, Intro for EMS, 3 Highlights, claim audit. Web search ON.

**ChatGPT browsed GitHub this round?** Not re-required; Round 1 browse already used. Web search used for prior DOI context.

**Key advice:** Evaluation-gap-first Abstract (191 words) and Intro citing Bennett/Markovich/Vilas; demote LES-analog; disclose `c_in` fallback in Intro; Highlights triad; prohibit overclaims (structural non-identifiability, fully topology-aware filter, “nested CV” without inner loop, etc.). Prefer reach-held-out wording. Sparse table value 0.0506 OK as ≈0.051.

**ACCEPTED:** Full Abstract + Intro rewrite; Highlights; title terminology shift to practical equifinality / transport-coupled; claim prohibitions.

**REJECTED:** None material (all claim audits already in DO NOT CLAIM policy).

**Changed:** `scripts/generate_paper.py` (abstract/intro/highlights/methods disclosure note/Bennett+Vilas refs/title); docs framework/engineering already updated in Round 1 batch.

---

## Round 3 — Methods

**Sent (summary):** Governing equation, filter definition, closures, CV protocol, k600/cross-section, S_implied, sparse Π; ask equation block, CV paragraph, reproducibility gaps, unit checks, EMS subsection headings.

**Key advice:** Delete bare `(Q/A)`; use τ_d and q_A; distinguish A_s vs A_c; never equate k600 with k_emp; define F total as sample-summed diagnostic; rename CV away from nested; spell k600→k_CO2 via Sc; define median for k ratio; list P0/P1 reproducibility gaps; suggest 8 Methods subsections.

**Local verification:** `k_from_k600` uses `(Sc/600)**-0.5`; Raymond ln(k600) formula in `src/04_estimate_k.py`; model F uses predicted C (`src/03`); flux_obs proxy uses k_emp×(C_obs−C_eq) in `score_transport`.

**ACCEPTED:** Equation rewrite; CV naming; F-total label; Methods restructure 2.1–2.8; median k ratio; S_implied wording.

**REJECTED / deferred:** Full C_eq formula appendix rewrite (mark 待补充 until HydroShare path fully transcribed); full network-topology filter rewrite; inventing feature table numbers beyond code.

**Changed:** `scripts/generate_paper.py` Methods section.

---

## Round 4 — Results + Discussion

**Sent (summary):** Frozen results table + figure map; claim audit for H1–H3/filter/sparse/equifinality; equifinality wording; limitations paste; Markovich/Vilas Discussion structure; figure triage.

**Key advice:** H1 SUPPORT with scope qualifier; H2 NEED QUALIFIER (not “superficial”); H3 OVERCLAIM if phrased as flux prediction failure—use model-diagnostic collapse; equifinality = restricted three-level chain; paste Limitations; reorder Results 3.1–3.5 with concentration-vs-flux before filter; optionally demote Fig7/Fig4.

**ACCEPTED:** Claim wording; Limitations subsection; Discussion 4.1–4.6; Results lead reorder; keep A1 appendix-only.

**REJECTED:** Demoting Fig. 7 Sparse-Π (still answers Q3; keep main with “diagnostic not predictive” framing); demoting Fig. 4 (code already colors by reach).

**Changed:** `scripts/generate_paper.py` Results lead + Discussion.

---

## Round 5 — EMS referee simulation

**Sent (summary):** Ask for full referee report (recommendation, major/minor, mandatory text, what NOT to change). Web search ON; repo URL given.

**ChatGPT browsed GitHub again?** YES (multiple GitHub chips; audited Stage 02/03/11/12/13 and docs terminology drift).

**Verdict:** **MAJOR REVISION** — publishable EMS core; do not reject for ML failure; require network/width audit, fallback frequency/fold reporting, repo sync.

**ACCEPTED (this pass):** Disclose serial R001–R008 + width proxy into governing quantities; narrow filter claim; fix Raymond venue label in `src/04`; soften transferable-methodology conclusion; flux diagnostic language; keep negative result / no AI shopping / R² appendix-only.

**REJECTED / deferred:** Full topology rewrite; new flux campaign; changing frozen RMSE before width sensitivity table exists (mark 待补充); inventing fold-level RMSE without regenerating Stage 12 tables this round.

**Changed:** `scripts/generate_paper.py`; `src/04_estimate_k.py` docstring; `docs/COVER_LETTER_DRAFT.md`.

---

## Round 6 — Title / keywords / cover letter / DOI checklist

**Sent (summary):** Request 3 titles, keywords, ≤250-word EMS cover letter, DOI checklist for core refs.

**Key advice:** Prefer Title 1 (evaluation-first + “evidence for” equifinality); 8 keywords; cover letter ~190 words selling negative result; all 8 DOIs confirmed; Raymond venue = L&O F&E not Nat Geosci; Xie/Yuval are methodological analogies not river-CO₂ priors.

**ACCEPTED:** Title 1; keywords; cover letter text → `docs/COVER_LETTER_DRAFT.md`; DOI checklist.

**REJECTED:** None.

**Changed:** `scripts/generate_paper.py` title/keywords; `docs/COVER_LETTER_DRAFT.md`.
