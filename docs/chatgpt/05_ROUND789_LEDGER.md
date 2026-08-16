# Round 7–9 accept/reject ledger (Cursor)

**Dialog:** https://chatgpt.com/c/6a818974-cd6c-83ea-8241-812dc9fd2598  
**Briefs pushed first at:** `72b37f3`  
**Paper regeneration this batch:** after Round 8–9 merges into `scripts/generate_paper.py`

## Accepted (implemented)

- Paper↔report separation: no pipeline `.py` narrative; no teaching fig-analysis in paper
- EMS Abstract / Intro / Discussion prose (Round 8)
- Highlights tightened for model-derived flux diagnostic
- Grouped CV naming; c_in as partial boundary conditioning
- Results lead H1→H2→H3→compensation→filter→sparse
- WQP/StreamPULSE as resolved negative availability
- Vilas 2023 title corrected to TALKS framework (DOI 105668)
- Bennett + Vilas added to reference list
- Local skill path removed from public `PAPER_FRAMEWORK.md`

## Rejected / deferred

- Topology-aware filter rewrite (would change frozen Δx)
- Invented width-sensitivity or fold RMSE tables
- Treating F_CO2 as validated flux
- Claiming Residual-AI improves accuracy
- Promoting in-sample R²
- Round 10 full referee re-pass deferred (Round 5 + R7–9 sufficient this turn)

## Frozen metrics (unchanged)

Baseline 0.0284; Residual-AI MLP 0.0573; RF 0.0745; k-corr 0.0244; F ~3.24→~0.03; sparse ≈0.051; filter 1.92→1.00; R²≈0.997 appendix only.
