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
| 10 | Optional EMS referee pass on revised excerpts | Deferred (time); Round 5 + R7–9 cover referee risks |

**Round 7 context delivery:** https://github.com/Coucou2016/river-carbon-transport/tree/main/docs/chatgpt/  
Files: `00_TASK_BRIEF.md`, `01_PAPER_CURRENT.md`, `02_REPORT_VS_PAPER_AUDIT.md`, `03_DATA_INTEGRITY_CHECKLIST.md`, `04_QUESTIONS_FOR_CHATGPT.md`.

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
