#!/usr/bin/env python3
"""Run tests, offline models, audit, plots, and reports from one entry point."""
import argparse
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path
import subprocess
import sys
import numpy as np
import pandas as pd
from model.economics import load_inputs,evaluate,budget_comparison,scenarios,psa,budget_scenarios
from model.claims import claims_delivery,simulate_methods
from model.reporting import write_reports,plots
ROOT=Path(__file__).resolve().parent

def write_json(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')

def main():
    p=argparse.ArgumentParser();p.add_argument('--quick',action='store_true',help='Smoke run; outputs in results/quick, not reference results')
    p.add_argument('--verify-sources',action='store_true',help='Download and hash-check CMS and CKJ originals')
    args=p.parse_args()
    subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=ROOT,check=True)
    if args.verify_sources:
        for script in ['extract_cms_price.py','extract_ckd_transitions.py']:
            subprocess.run([sys.executable,str(ROOT/'scripts'/script),'--check'],cwd=ROOT,check=True)
    out=ROOT/'results';out=out/'quick' if args.quick else out;out.mkdir(parents=True,exist_ok=True)
    cfg,matrices=load_inputs();r,tr=evaluate(cfg,matrices);bia,btr=budget_comparison(cfg,matrices)
    write_json(out/'cea.json',r);pd.DataFrame(bia).to_csv(out/'budget-annual.csv',index=False)
    for arm,data in tr.items():pd.DataFrame(data).to_csv(out/f'cea-trace-{arm}.csv',index=False)
    for arm,data in btr.items():pd.DataFrame(data).to_csv(out/f'budget-monthly-{arm}.csv',index=False)
    sens=pd.DataFrame(scenarios(cfg,matrices));sens.to_csv(out/'sensitivity.csv',index=False)
    pd.DataFrame(budget_scenarios(cfg,matrices)).to_csv(out/'budget-sensitivity.csv',index=False)
    print('Economic scenarios complete.',flush=True)
    draws=pd.DataFrame(psa(cfg,matrices,n=50 if args.quick else 1000));draws.to_csv(out/'psa-draws.csv',index=False)
    ceac=[]
    for wtp in range(0,200001,10000):
        probability=float((wtp*draws.delta_qaly-draws.delta_cost>0).mean())
        ceac.append({'wtp':wtp,'conditional_probability':probability,'mcse':float(np.sqrt(probability*(1-probability)/len(draws)))})
    pd.DataFrame(ceac).to_csv(out/'acceptability.csv',index=False)
    demo=claims_delivery(out)
    print('Synthetic SQL cohort and primary causal analysis complete.',flush=True)
    mc,summary=simulate_methods(repetitions=5 if args.quick else 200,n=2500,bootstrap=20 if args.quick else 100)
    pd.DataFrame(mc).to_csv(out/'causal-replicates.csv',index=False);write_json(out/'causal-summary.json',summary)
    print('Causal simulation complete.',flush=True)
    # Cross-check stored trace sums without calling economic total accumulator.
    audit={}
    for arm in ['dapa','control']:
        frame=pd.read_csv(out/f'cea-trace-{arm}.csv')
        independent=float(np.dot(frame.medical+frame.drug,frame.discount))
        err=abs(independent-r[arm]['cost']);assert err<1e-6
        audit[arm+'_cost_reconciliation_error']=err
    audit.update({'test_suite_passed':True,'sql_cohort_reconstructed':True,'synthetic_estimates_used_as_clinical_inputs':False,
       'clinical_validation':'NOT established: mixed-population matrices, assumed mortality/transport and cost allocations.',
       'trial_composite_validation':'Not identified from stage-only aggregates; no counterfeit composite HR calibration.',
       'lifetime':'Exploratory sensitivity capped at age100; not a validated lifetime forecast.',
       'mode':'quick' if args.quick else 'full','psa_draws':len(draws),'monte_carlo_replicates_per_scenario':5 if args.quick else 200})
    reference=ROOT/'parameters/computational-reference.json'
    if reference.exists():
        ref=json.loads(reference.read_text());errors={k:abs(r[k]-v) for k,v in ref['cea'].items()}
        if max(errors.values())>1e-6:raise AssertionError('Computational reference changed; inspect inputs before updating')
        audit['reference_max_abs_error']=max(errors.values())
    write_json(out/'validation.json',audit)
    plots(out,r,tr,bia,sens,draws,ceac,demo,summary)
    write_reports(out,cfg,r,bia,sens,demo,summary,ceac,audit)
    inputs={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((ROOT/'parameters').glob('*.json'))}
    manifest={'python':platform.python_version(),'packages':{n:importlib.metadata.version(n) for n in ['numpy','pandas','scipy','matplotlib']},
              'input_sha256':inputs,'code_sha256':{str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(ROOT.rglob('*')) if f.suffix in ['.py','.sql'] and '.venv' not in f.parts},'seeds':{'psa':20261011,'causal_mc':20261011,'claims':711},'mode':audit['mode'],
              'outputs':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(out.iterdir()) if f.is_file() and f.name!='run-manifest.json'}}
    write_json(out/'run-manifest.json',manifest)
    print(f'Complete. Read {out/"REPORT.md"}',flush=True)
if __name__=='__main__':main()
