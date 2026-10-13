"""Create readable reports directly from computed results, never hand-entered estimates."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def plots(out,r,tr,bia,sens,draws,ceac,demo,summary):
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':150})
    fig,ax=plt.subplots(1,2,figsize=(11,4.2),layout='constrained')
    for arm,label,color in [('control','Standard care','#a34d38'),('dapa','Dapagliflozin strategy','#187c83')]:
        f=pd.DataFrame(tr[arm]);ax[0].plot(f.month/12,f.alive,label=label,color=color)
        ax[1].plot(f.month/12,f.Dialysis+f.Transplant,label=label,color=color)
    for a in ax:a.set_xlabel('Years');a.set_ylabel('Cohort proportion');a.set_ylim(bottom=0);a.legend(fontsize=8)
    ax[0].set_title('Survival under assumed mortality');ax[1].set_title('Current kidney replacement therapy occupancy')
    fig.suptitle('Exploratory CKD scenario under specified assumptions',fontsize=12)
    fig.savefig(out/'economic-trajectories.png');plt.close(fig)
    b=pd.DataFrame(bia);fig,ax=plt.subplots(figsize=(8,4.4),layout='constrained');x=np.arange(3)
    ax.bar(x-.22,b.incremental_drug/1e6,.22,label='Added drug cost',color='#298a91')
    ax.bar(x,b.incremental_medical/1e6,.22,label='Medical cost change',color='#a05b41')
    ax.bar(x+.22,b.incremental_total/1e6,.22,label='Net budget change',color='#3d526c')
    ax.axhline(0,color='gray',lw=.8);ax.set_xticks(x,['Year 1','Year 2','Year 3']);ax.set_ylabel('Million USD, assumed 2026 prices')
    ax.set_title('100,000-member plan scenario: expanded minus current uptake');ax.legend(fontsize=8)
    fig.savefig(out/'budget-impact.png');plt.close(fig)
    fig,ax=plt.subplots(1,2,figsize=(11,4.2),layout='constrained')
    ax[0].scatter(draws.delta_qaly,draws.delta_cost/1000,s=6,alpha=.4,color='#187c83')
    ax[0].axhline(0,color='gray',lw=.8);ax[0].axvline(0,color='gray',lw=.8)
    ax[0].set(xlabel='Incremental QALYs',ylabel='Incremental cost (thousand USD)',title='Assumption-based probabilistic scenarios')
    a=pd.DataFrame(ceac);ax[1].plot(a.wtp/1000,a.conditional_probability,color='#187c83')
    ax[1].set(xlabel='Willingness to pay (thousand USD/QALY)',ylabel='Fraction with positive net monetary benefit',ylim=(0,1),title='Conditional on chosen input distributions')
    fig.savefig(out/'uncertainty.png');plt.close(fig)
    before=np.abs(demo['iptw_ipcw']['smd_before']);after=np.abs(demo['iptw_ipcw']['smd_after'])
    fig,ax=plt.subplots(1,2,figsize=(11,4.2),layout='constrained');y=np.arange(3)
    ax[0].scatter(before,y,label='Before',color='#a34d38');ax[0].scatter(after,y,label='After IPTW',color='#187c83')
    ax[0].set_yticks(y,['Age >=75','Severe CKD','Heart failure']);ax[0].axvline(.1,ls='--',color='gray');ax[0].legend()
    ax[0].set(xlabel='Absolute standardized mean difference',title='Measured covariate balance (synthetic)')
    ok=[s for s in summary if s['identified_runs']];labels=[s['scenario'].replace('_','\n') for s in ok];xx=np.arange(len(ok))
    ax[1].bar(xx-.17,[s['crude_bias']*100 for s in ok],.34,label='Crude',color='#a34d38')
    ax[1].bar(xx+.17,[s['bias']*100 for s in ok],.34,label='IPTW + IPCW',color='#187c83')
    ax[1].set_xticks(xx,labels,fontsize=8);ax[1].axhline(0,color='gray',lw=.8);ax[1].legend()
    ax[1].set(ylabel='Mean bias (percentage points)',title='Known-truth simulation; positivity failure rejected')
    fig.savefig(out/'causal-diagnostics.png');plt.close(fig)


def money(v):return f'-${abs(v):,.0f}' if v<0 else f'${v:,.0f}'

def write_reports(out,cfg,r,bia,sens,demo,summary,ceac,audit):
    d=r['dapa'];c=r['control'];fit=demo['iptw_ipcw'];truth=demo['truth'];net=sum(x['incremental_total'] for x in bia)
    ic=money(r['icer'])+'/QALY' if r['icer'] is not None else r['classification']
    rows='\n'.join(f"| {x['year']} | {money(x['incremental_drug'])} | {money(x['incremental_medical'])} | {money(x['incremental_total'])} | ${x['pmpm']:.3f} |" for x in bia)
    en=f'''# Dapagliflozin in CKD economic and causal methods project

**Exploratory cost-effectiveness and budget-impact scenarios with a separate synthetic causal-methods study.** Evidence review 11 October 2026. The reference horizon is 10 years; age-100 extrapolation is a sensitivity scenario only.

## Decision and economic output

Dapagliflozin 10 mg daily plus standard care versus standard care without an SGLT2 inhibitor, in a hypothetical albuminuric T2D/CKD cohort with trial-compatible starting stages. Monthly states G1, G2, G3a, G3b, G4, G5, dialysis, transplant, and death; 3% annual discounting and half-cycle occupancy rewards.

Reference incremental cost: {money(r['delta_cost'])}; incremental QALYs: {r['delta_qaly']:.6f}; classification: {r['classification']}; ICER: {ic}; incremental NMB at $100,000/QALY: {money(r['nmb_at_100k'])}. Conditional daily drug-price threshold: ${r['daily_price_threshold_at_100k']:.4f}.

These figures must be read with the scenario register: renal matrices are transferred from a mixed diabetes-status population; stage mortality and age extrapolation are assumptions, utilities use a transferred UK tariff, and spending uses adjusted US proxies. Full healthcare-sector and actual insurer net costs are not estimated.

![Modelled survival and kidney replacement therapy](economic-trajectories.png)

## Budget output

| Year | Added drug cost | Medical cost change | Net budget | PMPM |
| --- | ---: | ---: | ---: | ---: |
{rows}

Three-year total: {money(net)}. The fixed plan denominator is 100,000 members times 36 months. Initial eligible cohort 1,000, monthly entrants 20 from month two, existing treatment20%, targets current20/20/20% versus expanded30/45/60%, annual plan exits5% and additional stops10%. Fractional people represent expected cohort counts. Current/expanded paths have equal initial and entry populations; survival and exit counts may differ. Starts are limited to never-treated G2–G4 members, with no restart. All BIA members use late renal matrices, including new starts, as a steady-response approximation; early dynamics are included only in CEA. G4 initiation eligibility is an assumed one-third share because within-stage eGFR is unavailable. Entrants start at age65; incumbent age increases.

![Incremental budget components](budget-impact.png)

## Causal methods and results

The separate synthetic target trial compares initiation of dapagliflozin versus sitagliptin with a365-day observable baseline, chronic lab evidence and12-month renal cumulative incidence with competing death. Its artificial drug effect never enters the economic model. SQL reconstructs observed data independently from enrollment, diagnoses, linked laboratories, fills and events; no future enrollment/survival inclusion rule. Toy codes are not deployable clinical phenotypes.

In the primary demonstration, n={demo['n']}, true risk difference={truth['risk_difference']:.6f}, IPTW/IPCW estimate={fit['rd']:.6f},95% interval[{fit['ci_low']:.6f},{fit['ci_high']:.6f}]. Treatment propensity is estimated nonparametrically across eight baseline age/severity/HF strata. Censoring probability is estimated within treatment-stratum cells from monthly at-risk opportunities; renal events receive inverse cumulative uncensoring weights. Competing deaths count as zero renal events and are not censored. A treatment-initiation estimand is used; post-index pharmacy patterns do not redefine treatment.

Bootstrap samples with complete censoring in a treatment-stratum cell are also unidentified; no zero censoring survival is divided into an event indicator. The summary records interval failures and coverage among valid intervals. Four simulation settings address measured confounding, measured informative censoring, hidden confounding and structural positivity failure. Each has {audit['monte_carlo_replicates_per_scenario']} replicates; full-run samples2,500 with100 nonparametric bootstrap resamples for normal95% intervals, refitting both weights in each resample. Primary demonstration uses300 resamples. Known truth is the conditional finite-baseline-cohort average analytic cumulative incidence under each strategy. Published bias, RMSE, coverage and Monte Carlo errors are in[causal-summary.json](causal-summary.json). No-overlap ATEs are rejected. Finite simulation precision, synthetic mechanisms and limited nuisance-model complexity constrain generalization.

![Synthetic covariate balance and estimator bias](causal-diagnostics.png)

## Validation and limits

Independent discounted cashflow recomputation agrees within1e-6USD; matrix mass conservation, absorbing death, identity scenarios, analytic survival, no-treatment budget, open-population accounting and SQL exclusions are tested. These checks assess computational implementation and accounting. Stage aggregates cannot identify the sustained decline and adjudicated death components of the DAPA-CKD composite. The age-100 scenario depends on the stated extrapolation assumptions.

Public source tables are preserved separately from normalization and assumptions. PSA samples selected subjective distributions; its acceptance curve is conditional on those choices, with no claim to a recovered trial joint distribution. No separate HF benefit, transplant incident cost, or observed adverse-event effect is claimed. Source totals include mixed medical/pharmacy components; an assumed20% pharmacy subtraction and3% annual2023–2026 conversion create background medical proxies. KRT transplant costs represent prevalent averages; dialysis cost is an explicit scenario. Drug MFP is not net payer liability.

![Uncertainty under selected parameter distributions](uncertainty.png)

See [methods](../METHODS.md), [sources](../SOURCES.md),[parameter register](../parameters/scenario.json),[validation](validation.json) and[run manifest](run-manifest.json).
'''
    (out/'REPORT.md').write_text(en)
