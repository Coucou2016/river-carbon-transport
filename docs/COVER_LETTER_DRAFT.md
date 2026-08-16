# EMS cover letter draft (Round 6 accepted)

**Target journal:** *Environmental Modelling & Software*

**Preferred English title (ChatGPT Round 6, accepted):**  
Transport-coupled evaluation of river-network CO₂ closures: Evidence for practical equifinality under concentration-only observations

**Alternate titles:**  
2. Diagnosing closure compensation in river-network CO₂ transport through spatial filtering and reach-held-out evaluation  
3. When concentration fit does not constrain process allocation: Practical closure equifinality in river-network CO₂ modelling

**Keywords:** River carbon cycling; environmental model evaluation; transport-coupled validation; spatial coarse-graining; subgrid residual; gas-transfer velocity; practical equifinality; grouped cross-validation

---

Dear Editor,

We submit our manuscript, "Transport-coupled evaluation of river-network CO₂ closures: Evidence for practical equifinality under concentration-only observations," for consideration in Environmental Modelling & Software.

The manuscript addresses an environmental-model evaluation problem rather than an algorithmic accuracy contest. Using public East River observations, we operationalize a spatially filtered residual for river-network CO₂ mass balance and evaluate alternative unresolved-process closures after coupling them back to the transport model under leave-one-reach-out grouped evaluation.

The principal result is deliberately negative. Learned residual closures do not outperform the process Baseline: held-out C_aq RMSE is 0.0573 for the MLP and 0.0745 for the random forest, compared with 0.0284 for the Baseline. A k-correction lowers concentration RMSE to 0.0244, but this coincides with a median k_eff/k_emp ≈ 3.35×10⁻⁴ and a reduction in the sample-summed model flux diagnostic from 3.24 to 0.031. We therefore do not claim that machine learning improves predictive accuracy or that the model flux is independently validated.

The contribution is methodological: an operable filtering definition, transport-coupled grouped evaluation, and an empirical diagnosis of practical closure compensation under concentration-dominated observations. The manuscript also states the limitations of its boundary conditioning, reach representation, sampling imbalance, hydraulic proxies, and spatial-filter implementation.

A public repository accompanies the study: https://github.com/Coucou2016/river-carbon-transport

Thank you for considering the manuscript.

**Authors / affiliations:** 待补充

---

## DOI checklist (Round 6 CONFIRMED)

| Citation | DOI |
|----------|-----|
| Markovich et al. 2022 | 10.1016/j.envsoft.2022.105498 |
| Bennett et al. 2013 | 10.1016/j.envsoft.2012.09.011 |
| Vilas et al. 2023 | 10.1016/j.envsoft.2023.105668 |
| Raymond et al. 2012 L&O F&E | 10.1215/21573689-1597669 |
| Saccardi & Winnick 2021 | 10.1029/2021GB006972 |
| Yuval & O'Gorman 2020 | 10.1038/s41467-020-17142-3 |
| Hotchkiss et al. 2015 | 10.1038/ngeo2507 |
| Xie et al. 2022 | 10.1038/s41467-022-35084-w |
