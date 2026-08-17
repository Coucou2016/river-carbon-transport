# CONTEXT 1/2 — Round 10: repo-level writing-quality + integrity review

**Date:** 2026-08-18
**Public repo:** https://github.com/Coucou2016/river-carbon-transport
**Commit at ask time:** see repo `main` HEAD (briefs pushed in the same commit batch)
**Dialog:** continuing the existing task dialog (Rounds 1–9 complete; see `docs/REVIEW_ROUNDS.md`)
**Executor:** Cursor (sole local implementer). ChatGPT = external text advisor only; browse GitHub Markdown, no file uploads.

## What changed since Round 9

The manuscript body was rewritten in a tighter WRR/EMS register ("Fraehr-style", below). The rewrite changed prose and structure only; every number, result, and conclusion is unchanged. The rewrite is now committed in `paper.md` / `paper.html` on `main` and ready for your review.

New repository documents since Round 9:

- `docs/RESEARCH_INTEGRITY_AUDIT.md` — truthfulness / self-computed-results / code-completeness / known-gaps audit.
- `docs/REVIEW_ROUNDS.md` — running ledger of every ChatGPT round with accept/reject decisions.

## Files to browse for THIS round (Round 10)

1. https://github.com/Coucou2016/river-carbon-transport/blob/main/paper.md — the full manuscript text (primary review target)
2. https://github.com/Coucou2016/river-carbon-transport/tree/main/docs/chatgpt/ — advisor briefs
3. https://github.com/Coucou2016/river-carbon-transport/blob/main/docs/RESEARCH_INTEGRITY_AUDIT.md
4. https://github.com/Coucou2016/river-carbon-transport/blob/main/docs/REVIEW_ROUNDS.md

## Style exemplar

Fraehr, N., Wang, Q. J., Wu, W., & Nathan, R. (2023). Development of a fast and accurate hybrid model for floodplain inundation simulations. Water Resources Research, 59, e2022WR033836. https://doi.org/10.1029/2022WR033836 — used as a rhythm/length/flow exemplar for a methods-heavy hydrology paper, NOT as a content model (topics differ).

## Frozen facts (must never be altered by any suggested rewrite)

- n = 120 samples, 2019-08-02 to 2019-08-11; reaches R001–R008 with sample counts 1, 3, 15, 24, 17, 1, 1, 58 (R001/R006/R007 schematic)
- Leave-one-reach-out transport-coupled C_aq RMSE: Baseline 0.0284; MLP 0.0573; RF 0.0745; k-correction 0.0244; sparse Pi 0.0506
- k-correction: median k_eff/k_emp about 3.35e-4; sample-summed model flux diagnostic 3.24 -> 0.031 mol m-2 d-1
- Filter mean |S_sgs|: 1.916 at dx about 838 m -> 1.000 at study-reach scale (7 cells, 6 sampled)
- Sparse law S*_z approx 1.059 + 1.536 Fr - 1.669 Slope - 2.179 h/W
- In-sample R2 approx 0.997 is appendix-only; F_CO2 is a model diagnostic, not a measured flux; cross-sections idealized
- Known gaps kept honest (待补充): authors, Gao DOI, Alk/N/P/PAR, width-sensitivity table, fold-level RMSE, C_eq appendix

## Round 10 questions

Q10.1 Read `paper.md` in full. As a WRR / Environmental Modelling & Software reviewer, does the manuscript still read like a "work summary", a "rebuttal letter", or an "AI-assembled draft"? Give a verdict per section (Key Points, Plain Language Summary, Abstract, Introduction, Methods 2.1–2.8, Results 3.1–3.6, Discussion 4.1–4.6, Conclusions, Data availability) and an overall verdict.

Q10.2 List the top 10 most AI-sounding or report-like passages with location (section + opening words). For each: quote the passage, say which tell it exhibits (e.g. stacked parallel "not X but Y" constructions, over-hedging, self-referential "we provide / we define" chains, formulaic transitions, em-dash steering, abstract-noun piles), and give a concrete human-sounding alternative or deletion.

Q10.3 Compare structure, section length, and paragraph flow of our manuscript against the Fraehr et al. (2023) exemplar (WRR e2022WR033836) and against Markovich et al. (2022) EMS 105498. Where are we longest/shortest relative to those papers, and which sections should be compressed or expanded? Be specific about paragraph count and approximate word targets.

Q10.4 Search the web for current guidance on detecting and removing AI-writing tells in academic prose (humanizer checklists, "AI-tell" lists, university writing-centre guidance) and for University of Manchester Academic Phrasebank guidance on hedging, transitions, and stance. Apply whatever you find to our manuscript: which specific tells from those checklists appear in our text, and what Phrasebank-style move vocabulary should replace our most formulaic transitions?

Q10.5 Integrity spot-check: does any sentence in `paper.md` sound like it could have been borrowed from a reference paper (i.e. phrasing that implies someone else's dataset or result)? Expected answer: none, because every number is self-computed — but please flag anything that reads as if it reports external data, so we can add a citation or reword.

Constraints for all your suggestions: keep all frozen numbers exactly; no em-dash steering; no bold in prose; no invented results; no claims beyond "practical equifinality of S_sgs and k under concentration-only East River observations".
