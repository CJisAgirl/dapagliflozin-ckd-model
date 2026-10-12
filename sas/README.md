# SAS economic replication

Base SAS code for an independent implementation of the reference cost-effectiveness calculation and a budget aggregation check. SAS/IML is not required. **Execution status: not yet run in SAS; agreement with Python has not been established.** Python input/export checks do not change that status.

## Scope

- Recalculate both treatment arms from the raw published renal matrices and the saved scenario parameters, including matrix rounding, monthly death, permanent treatment stops, half-cycle rewards and discounting.
- Recompute costs, QALYs, life-years, ICER, net monetary benefit and the conditional drug-price threshold. Check 20 reference CEA values against Python.
- Re-aggregate the saved Python monthly budget traces into 36 annual drug, medical, incremental-spending and PMPM values. This checks aggregation, not the underlying budget population dynamics.

The nine-state monthly CEA is implemented using DATA step arrays and loops. PROC SQL summarizes outcomes; PROC COMPARE checks numerical agreement. The synthetic causal estimators, scenario grid and PSA remain in Python. Scientific assumptions and clinical-validation limits in [Methods](../METHODS.md) continue to apply.

## Run in SAS Studio

On a Mac, the free [SAS OnDemand for Academics](https://www.sas.com/en_us/software/on-demand-for-academics.html) learning environment provides SAS Studio in a browser. Register or sign in and launch SAS Studio; no local SAS installation is needed.

1. Download or clone this repository. Upload `sas/replicate_economics.sas` and `sas/reference_inputs.sas` to a `sas` folder under your project directory on the SAS server. The saved inputs contain public parameters and aggregate reference results only.
2. Open `replicate_economics.sas`. Change its first `%let project=...;` setting to the project directory on that server, not the Mac directory. For example, if the code is at `/home/your-user/dapagliflozin-ckd-model/sas/replicate_economics.sas`, use `/home/your-user/dapagliflozin-ckd-model`.
3. Run the entire program. It creates `sas/output/`. Save the complete SAS log and review errors or invalid-value diagnostics. A successful comparison ends with `NOTE: CKD_SAS_REFERENCE_CHECKS_PASSED`.
4. Download `cea.csv`, `budget.csv` and `run.csv` from the SAS output folder to your local `sas/output/`. Save the SAS log there as `sas.log`. Audit these actual exports locally:

```sh
python scripts/verify_sas.py --log sas/output/sas.log
```

The Python audit requires the SAS completion record, version, matching input/program fingerprint, full metric keys, a clean saved log and numerical agreement. It uses absolute tolerances of `1e-9` for QALYs, life-years and survival, and `1e-6` for other values. PROC COMPARE uses `1e-6`; the Python audit adds the tighter health-outcome checks. A pass creates `sas/output/verification.json`. Keep raw logs and local SAS datasets outside Git.

## Refresh after changing the Python model

First rerun the main Python workflow so its saved reference outputs reflect the new parameters. Then:

```sh
python scripts/prepare_sas.py
python scripts/prepare_sas.py --check
```

The exporter preserves raw transition probabilities and does not calculate CEA estimates. It records hashes of parameters, aggregate Python reference outputs and the SAS program. Upload the refreshed `reference_inputs.sas`, rerun SAS, and download fresh outputs. An older successful SAS run cannot verify changed inputs or changed SAS calculations.

## SAS references

- [DATA step arrays](https://support.sas.com/documentation/cdl/en/lestmtsref/63323/HTML/default/p08do6szetrxe2n136ush727sbuo.htm)
- [PROC COMPARE options and absolute comparison criterion](https://support.sas.com/documentation/cdl/en/proc/61895/HTML/default/a000146741.htm)
