# Dapagliflozin CKD economic and synthetic causal methods

## Scope and status

A completed computational scenario analysis of dapagliflozin 10mg daily plus standard care versus standard care without an SGLT2 inhibitor. Reference horizon 10 years; lifetime to age 100 is an exploratory sensitivity, not a clinically validated forecast. The hypothetical target is T2D with albuminuric CKD, eGFR25–75 and UACR200–5000, no baseline KRT. Stage-only public inputs do not preserve individual lab trajectories or validate transport to this population. CKD with T2D is not automatically proven diabetic nephropathy.

The economic contrast does not imply withholding SGLT2 inhibitors is optimal contemporary care. The synthetic active-comparator module has a different estimand and supplies no clinical treatment effects to the economic model.

## Evidence and scenario separation

Original CMS price rows and CKJ supplement S3/S4 probabilities/SEs remain unchanged in their evidence JSON files. `scenario.json` defines every operational setting and explicitly marks mortality, initial mix, inflation, cost allocation, eligibility, uptake and transport assumptions. [Sources](SOURCES.md) contains sources and applicability decisions.

The reference economic result is conditional, not an approved clinical base case. Its restricted cost perspective includes a constructed background medical-spending proxy and incremental drug cost, omitting common background pharmacy costs; it is neither full US healthcare-sector cost nor actual Medicare Advantage net liability. No simulated individual-level information is taken from real patients.

## Monthly economic state model

States: G1, G2, G3a, G3b, G4, G5 before KRT, dialysis, transplant and death. Initial probabilities are `[0,.10,.30,.45,.15,0,0,0]`, an assumed composition rather than an extracted trial distribution. Baseline G2 means eligible eGFR60–75 and G4 means 25–29. Subsequent stage states are broader. G1 remains reachable and does not mean CKD is cured.

Renal matrices exclude mortality and contain rounded rows. Reference correction divides each row by its sum; a diagonal-residual alternative is tested. Four initial monthly cycles use the printed early matrix; subsequent cycles use late inputs. Five early cycles form a boundary sensitivity. Death is absorbing. In each cycle, assumed stage-specific annual hazards at age 65 are multiplied by `2 ** ((age-65)/10)` and converted by `1-exp(-hazard/12)`. Apply death once, then the renal matrix conditional on survival. No composite or all-cause mortality HR is multiplied into the matrix.

For row-vector alive occupancy `v`, death probability `q` and renal matrix `R`:

```text
next_alive = (v * (1-q)) @ R
new_deaths = v @ q
reward_occupancy = (v + next_alive) / 2
monthly_QALY = reward_occupancy @ utility / 12
monthly_cost = reward_occupancy @ annual_background_cost / 12 + drug_exposure_cost
discount_factor(t) = (1 + annual_discount) ** (-(t + 0.5)/12)
```

Per-person costs and QALYs use 3% discounting. Life-years are also reported discounted. Drug is charged for pre-KRT exposure at 365/12 tablets per cycle; all costs are in a declared 2026-price scenario. KRT ends exposure permanently. The reference maintains the published arm contrast while charging full daily exposure; it is not an estimate of observed trial adherence. Additional discontinuation scenarios remove a fraction at each cycle end and use comparator transitions thereafter. These are hypothetical policy deviations, not independently fitted on-treatment effects. Costs and transitions change together; no separate adherence multiplier is silently applied to the ITT contrast.

A common utility shift and mortality/cost multipliers are scenario settings. No separate HF benefit is counted. The average state-cost proxy already contains event care; separate hospitalization savings would double count it. Transplant uses one prevalent average state, with no added incident procedure cost; first-year versus maintenance heterogeneity remains a limitation. Treatment-burden sensitivity adds hypothetical 250 USD/year and 0.01 QALY/year penalties, not observed adverse-event estimates.

## Economic uncertainty

Outputs: discounted costs, life-years, QALYs, incremental costs/QALYs, ICER when appropriate, dominance classification, and net monetary benefit `WTP*delta_QALY-delta_cost`. The 100,000 USD/QALY benchmark is illustrative. The drug-price threshold solves NMB=0 with exposure and clinical transitions held fixed. Small/zero or negative QALY increments do not produce a misleading headline ratio.

Thirty-two deterministic settings include 3/5/10 year and age 100 horizons, discount 0/5%, price, mortality, medical cost, inflation, utility, source-effect retention 0/50/100%, slow renal movements,30 month effect cessation, treatment cessation, additional dropout, early phase boundary, rounding and age/stage composition. Stage composition scenarios are not validated subgroup treatment effects.

The 1,000-draw scenario PSA uses seed 20261011: shared lognormal cost multiplier CV 20%, shared lognormal mortality multiplier CV 30% (means 1), a common normal utility shift SD 0.03 clipped to 0–1, drug price Uniform 0.5–1.5 times reference, and retention Uniform 0–1 of the published arm-matrix contrast. Conditional on other inputs these draws are independent; shared shifts impose perfect within-domain correlation across stages. These are chosen uncertainty distributions, not empirical posteriors. Source matrices remain fixed; marginal rounded SEs cannot recover their joint covariance. The acceptability curve reports the fraction of these draws with positive NMB and binomial Monte Carlo SE.

## Three-year budget

The fixed plan size is 100,000 total members. Initial eligible cohort 1,000 with 20% existing users;20new eligible members enter monthly from month two. These are design assumptions, not NHANES prevalence estimates. Existing members start at 65; new entrants enter at 65. Current targets 20/20/20% and expanded targets 30/45/60% refer to pre-KRT treatment shares. Only never-treated G2–G4 members can start; the G4 eligible fraction is assumed 1/3 because eGFR25–29 cannot be recovered from the broad stage. Retain unreachable-target information in monthly outputs. Additional stops 10%/year are permanent, plan exits 5%/year, both converted to monthly conditional probabilities. Death precedes surviving-member exit, avoiding double counting.

All BIA groups, including new starts, use late renal matrices as a prevalent-population steady-response approximation. Early dynamics are modeled in CEA only. This preserves the zero-effect counterfactual when treatment targets differ; a zero arm contrast cannot generate medical savings merely by assigning a different phase. Drug and medical payment shares are explicit settings, reference 100%. They do not represent verified plan liability.

Apply uptake at cycle start, mortality/renal movements/exits during the cycle, additional stops at cycle end; use midpoint exposure and costs. Report fractional expected people, distinct new starts (no restarts), treatment-months, entrants, deaths, exits, eligible populations, drug/medical totals and incremental budgets. PMPM denominator is 100,000*12 per year. A cost-per-additional-treated-year measure uses incremental exposure, not an incorrectly summed headcount. No budget discounting; hold 2026 price constant as a stated scenario, despite known separate 2027 MFP rows. Fourteen budget settings cover uptake, prices, population, entry/exit, discontinuation, eligibility and payment allocation.

## Synthetic target trial and SQL

Artificial new users of dapagliflozin versus sitagliptin are indexed at study day 0. The outcome is 12 month cumulative incidence of KRT before competing death under treatment initiation. No real comparative effect is assumed; the generator sets all hazards. Treatment labels illustrate an active-comparator design, not a clinical prescribing recommendation. Use a 365 day observable baseline, two T2D diagnosis dates, no either-drug fills during baseline, age 18+, no prior KRT/transplant, recent eGFR25–75/UACR200–5000 and an older abnormal albuminuria result at least 90 days apart. Do not require future survival or enrollment. Twenty decoys exercise missing baseline, T2D, eligibility, prior use and prior KRT exclusions.

Five tables are enrollment, diagnoses, labs, fills and events. Labs are simulated linked clinical data, not assumed to exist in claims alone. Codes are intentionally simple strings; production ICD/NDC algorithms would require independent phenotype validation. Prescriptions carry 30 day supplies; index fill exists at time zero before immediate first-cycle disenrollment. Follow-up records stop at event, death, disenrollment or 365 day study end. Month boundaries are mapped to rounded 365/12 day intervals. No post-index selection on drug adherence; treatment-initiation effects include subsequent observed follow-up.

Baseline binary older age, severe CKD and HF have probabilities 0.35,0.40,0.25. Hidden U has probability 0.30. Treatment probability is logistic(-0.8+1.3*severe+0.5*older+0.8*HF), adding 1.5*U in the hidden-confounding scenario. Monthly renal hazard is exp(-4.8+0.7*severe+0.25*older+0.4*HF+log(0.75)*A), with 0.9*U added in that scenario. Death hazard is exp(-5.2+0.5*older+0.5*HF+0.4*severe+log(0.95)*A), adding 0.4*U when hidden. Joint event probability 1-exp(-(renal+death)); allocate causes proportionally to hazards. Censoring precedes cycle events with logistic(-3.4+0.8*severe+0.5*older+0.4*HF+0.2*A) in the informative/hidden scenarios. In the positivity failure setting A=severe deterministically.

Known truth for each individual's 12 month renal risk is `renal/(renal+death)*(1-exp(-12*(renal+death)))`; average both potential risks over the same baseline cohort. The ATE target is that finite-baseline-cohort average risk difference. The hidden variable influences truth but is never given to the analysis cohort.

Estimate propensity nonparametrically within eight measured baseline strata. IPTW weights are 1/e or 1/(1-e); report effective sample sizes, max weight, overlap and standardized mean differences using the original pooled standard deviation. Estimate constant monthly censoring probability within treatment-stratum cells from censor counts divided by observed start-of-month opportunities. Renal-event weights also contain `1/(1-q)^event_month`. The arm-specific risk is the weighted event sum divided by total baseline treatment weights. Competing deaths contribute zero renal events, not censoring. The estimator is not forcibly clipped to 0–1.

Primary demonstration n 4,000 with 300 bootstrap resamples; four settings each have 200 replicates of n 2,500 with 100 bootstrap resamples. Resample people and refit both nuisance estimates. Report normal 95% bootstrap-SE intervals, bias, RMSE, interval coverage and Monte Carlo SE. A replicate with an empty treatment cell is not identified. If more than 5% bootstrap resamples are unidentified, suppress its interval and report interval failure rate; coverage is conditional on valid intervals, not silently counted over all runs. No arbitrary propensity clipping repairs structural nonidentification. Interval behavior in simulations is a finding, not a guarantee.

## Verification and interpretation

Tests cover source fingerprints/rounding, mass conservation, absorbing death, closed-form survival and identity cases, zero-effect cost decomposition, discounting, dropout, zero-treatment/identical-strategy budgets, independent annual population accounting, SQL reconstruction, early loss retention, reproducibility, balance, no-overlap detection and large-sample known-truth recovery. Independently recompute discounted costs from saved traces. A computational reference checks repeatability; changing it requires reviewing inputs, not silently accepting drift.

Clinical validation has not been established. The trial composite cannot be reconstructed from stage-only aggregates, and mortality/transport are not fitted to T2D outcomes. External risk-group costs and different trial endpoints are contextual references only. Research-grade application needs a compatible mortality/transition model, US utilities, verified payer cost allocations, event costs without overlap, and endpoint-aligned clinical calibration. These evidence requirements cannot be satisfied merely by running more tests.
