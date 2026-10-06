"""
SUPERSEDED — NOT FOR SUBMISSION — 2026-08-27

This document records a prior recalculation pass (2026-08-18 / 2026-08-24).
A subsequent independent audit (审查文档/审查文档_严格审稿与真实性证据审计_20260827.md)
found blocking defects that invalidate the numerical conclusions recorded here:

  P0-01  Shape_Length reused as per-sample control-volume length
  P0-02  upstream CSV strings parsed with list(str), so confluences never mix
  P0-03  flux totals sum overlapping sample areas across dates
  P0-04  filter-scale operator does not propagate mass on the cell DAG
  P0-05  pipeline / paper / figure directories are mutually inconsistent
  P0-06  k-correction infeasible handling contradicts the manuscript text

Do NOT cite the RMSE, flux, filter-scale, or equifinality numbers in this file
as submission-ready results. Use the 2026-08-27 audit as the active review
baseline until Phase 1–6 of that audit are closed and a new recalculation
manifest is written.
"""
