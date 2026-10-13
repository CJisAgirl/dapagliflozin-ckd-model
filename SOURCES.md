# Evidence and Parameter Sources

The project preserves published inputs separately from the operational scenario settings. Model outputs are conditional on those settings; source citations do not establish that every parameter applies to the target population.

## Clinical evidence

| Source | Role | Applicability |
| --- | --- | --- |
| [DAPA-CKD trial](https://pubmed.ncbi.nlm.nih.gov/32970396/) | Clinical question, eligibility and outcome framework | Mixed diabetes status; not a complete state-transition or mortality model |
| [Prespecified diabetes subgroup](https://pubmed.ncbi.nlm.nih.gov/33338413/) | Reference for the diabetes population | A composite hazard ratio does not identify every stage transition or absolute mortality risk |
| [McEwan et al., Clinical Kidney Journal](https://doi.org/10.1093/ckj/sfae025) | Published monthly renal transitions and health-state utilities | Supplement S3/S4 high-albuminuria matrices are not separately T2D-specific; utilities use an external UK tariff |

The original supplement is attributed to McEwan and colleagues, published under CC BY 4.0. The [transition register](parameters/ckd-transitions-source.json) preserves printed means and standard errors, source identification and fingerprint. The [extractor](scripts/extract_ckd_transitions.py) verifies the source before parsing. Runtime normalization of rounded rows and an alternative rounding scenario are separate from the source evidence. Death is not embedded in these renal matrices.

## US price and spending references

| Source | Role | Applicability |
| --- | --- | --- |
| [CMS negotiated prices](https://www.cms.gov/initiatives/medicare-prescription-drug-affordability/overview/medicare-drug-price-negotiation-program/selected-drugs-negotiated-prices) | Product-specific drug-price scenario | Select the product, unit and effective year; maximum fair price is not observed net payer liability or patient out-of-pocket spending |
| [Farxiga label](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=72ad22ae-efe6-4cd6-a302-98aaee423d69) | Product identity and dosing reference | A label does not supply an observed plan population or adherence model |
| [USRDS CKD spending, Table 6.3](https://usrds-adr.niddk.nih.gov/2025/chronic-kidney-disease/6-healthcare-expenditures-for-persons-with-ckd#table-6-3-section) | Stage-group spending for older Medicare FFS beneficiaries with diabetes | Diabetes is not restricted to T2D; combined stage groups must be mapped to model states |
| [USRDS transplant spending, Figure 9.11d](https://usrds-adr.niddk.nih.gov/2025/end-stage-renal-disease/9-healthcare-expenditures-for-persons-with-esrd#figure-9-11d-section) | Annual prevalent transplant spending | Not first-year transplant cost or a diabetes-specific estimate |

The USRDS edition is 2025; the spending observations used are from 2023. [Cost-source notes](parameters/us-cost-source.json) record manually transcribed values and transformations. CMS product/date selection is independently reproducible with the [price extractor](scripts/extract_cms_price.py); its [evidence register](parameters/cms-price-evidence.json) retains the raw source row and fingerprint.

## Assumptions that remain in the model

The [scenario register](parameters/scenario.json) contains the complete numerical settings and their explanations. Stage-specific mortality and age progression, initial age/stage composition, dialysis spending, pharmacy subtraction, inflation, treatment persistence, uptake and plan membership are scenario assumptions. Utilities and renal transitions are transferred from external populations. Their applicability to the hypothetical T2D population is an assumption examined through scenario analysis.

The restricted cost perspective combines a background medical-spending proxy with incremental study-drug cost. It does not estimate comprehensive healthcare-sector costs or actual insurer net liability. An assumed pharmacy share is removed from source totals; common background pharmacy costs are omitted. The transplant state uses a prevalent average, and there are no separate hospitalisation-for-heart-failure savings or observed adverse-event effects. These restrictions avoid asserting event benefits that have not been modelled.

Probability-based scenarios use selected distributions rather than a recovered joint trial parameter distribution. Renal-matrix covariance cannot be inferred from rounded marginal standard errors. Long-term extrapolation and transfer to the target population remain structural uncertainties.

## Relationship to other economic work

US economic evaluation of dapagliflozin is established, including [Abegaz et al.](https://doi.org/10.1007/s40261-022-01160-8). [Chang et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC11293758/) examine commercial-payer cost offsets, and [Li et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC11932809/) compare diabetes drug value-based prices with negotiated prices. This project combines transparent source selection, executable CEA/BIA scenarios and a separate causal-method experiment; it does not claim to be the first evaluation or to reproduce those authors' results.

## Synthetic data

The longitudinal records are generated within the project. The generation mechanism supplies a known counterfactual risk for method evaluation; estimation uses only simulated observed variables. No CMS, Optum or MarketScan patient records are used. Simplified diagnosis and prescription labels are not production ICD/NDC definitions. Synthetic treatment effects are never imported into the economic model.

See [methods](METHODS.md) for estimands and equations, [validation](results/validation.json) for computational checks, and the [run manifest](results/run-manifest.json) for input and code fingerprints.
