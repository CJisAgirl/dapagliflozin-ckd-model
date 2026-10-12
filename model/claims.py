"""Synthetic claims and known-truth causal-method evaluation; no clinical effects."""
import json
import sqlite3
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import expit

ROOT=Path(__file__).resolve().parents[1]
SCENARIOS=['measured_confounding','informative_censoring','unmeasured_confounding','positivity_failure']

def generate(n=4000,seed=711,scenario='informative_censoring'):
    if scenario not in SCENARIOS:raise ValueError('Unknown experiment')
    rng=np.random.default_rng(seed)
    older=rng.binomial(1,.35,n);severe=rng.binomial(1,.4,n);hf=rng.binomial(1,.25,n);u=rng.binomial(1,.3,n)
    hidden=scenario=='unmeasured_confounding'
    e=expit(-.8+1.3*severe+.5*older+.8*hf+hidden*1.5*u)
    if scenario=='positivity_failure':e=np.where(severe==1,1,0)
    a=rng.binomial(1,e)
    q=expit(-3.4+.8*severe+.5*older+.4*hf+.2*a) if scenario in ['informative_censoring','unmeasured_confounding'] else np.zeros(n)
    def risks(treatment):
        renal=np.exp(-4.8+.7*severe+.25*older+.4*hf+hidden*.9*u+np.log(.75)*treatment)
        death=np.exp(-5.2+.5*older+.5*hf+.4*severe+hidden*.4*u+np.log(.95)*treatment)
        return renal,death
    k,d=risks(a);p_any=-np.expm1(-(k+d));pk=p_any*k/(k+d)
    status=np.zeros(n,dtype=int);month=np.full(n,12,dtype=int)
    for m in range(1,13):
        active=status==0
        cens=active & (rng.random(n)<q);status[cens]=3;month[cens]=m
        z=rng.random(n);active=status==0
        renal=active & (z<pk);death=active & (z>=pk) & (z<p_any)
        status[renal]=1;status[death]=2;month[renal|death]=m
    truth=[]
    for treatment in [0,1]:
        ka,da=risks(treatment);truth.append(ka/(ka+da)*(-np.expm1(-12*(ka+da))))
    df=pd.DataFrame({'person_id':np.arange(n),'older':older,'severe':severe,'hf':hf,'a':a,'status':status,'month':month})
    return df,{'risk_control':float(truth[0].mean()),'risk_dapa':float(truth[1].mean()),'risk_difference':float((truth[1]-truth[0]).mean()),
               'definition':'Synthetic 12-month renal cumulative incidence, death competing. Artificial hazards, not evidence for either drug.'}

def arrays(df):
    x=df[['older','severe','hf']].to_numpy(float);a=df.a.to_numpy(int)
    s=(df.older+2*df.severe+4*df.hf).to_numpy(int)
    return x,a,s,df.status.to_numpy(int),df.month.to_numpy(int)

def estimate_arrays(x,a,s,status,month,ipcw=True):
    n=len(a);ns=np.bincount(s,minlength=8);nt=np.bincount(s,weights=a,minlength=8)
    valid=ns>0
    if np.any((nt[valid]==0)|(nt[valid]==ns[valid])):
        return {'identified':False,'reason':'Empty treatment cell: population ATE not identified; no clipping or extrapolation.'}
    e=(nt/np.maximum(ns,1))[s];weights=np.where(a==1,1/e,1/(1-e))
    cell=s+8*a
    # Every observed month contributes one start-of-month censoring opportunity.
    exposure=np.bincount(cell,weights=month,minlength=16)
    cens=np.bincount(cell,weights=status==3,minlength=16)
    q=(cens/np.maximum(exposure,1))[cell] if ipcw else np.zeros(n)
    if np.any(q>=1):
        return {'identified':False,'reason':'No uncensored follow-up in a treatment-stratum cell; censoring positivity fails.'}
    g=(1-q)**month
    # Event-only IPCW estimator: competing deaths contribute zero, not censoring.
    y=(status==1)/g
    risk=[float(np.sum(weights[a==v]*y[a==v])/np.sum(weights[a==v])) for v in [0,1]]
    crude=[float(np.mean(status[a==v]==1)) for v in [0,1]]
    means=[x[a==v].mean(axis=0) for v in [0,1]]
    sd=np.sqrt(sum(np.var(x[a==v],axis=0) for v in [0,1])/2)
    weighted=[np.average(x[a==v],axis=0,weights=weights[a==v]) for v in [0,1]]
    return {'identified':True,'risk_control':risk[0],'risk_dapa':risk[1],'rd':risk[1]-risk[0],
       'crude_rd':crude[1]-crude[0],'propensity_min':float(e.min()),'propensity_max':float(e.max()),
       'max_weight':float(weights.max()),'min_censor_survival':float(g.min()),
       'effective_n':[float(weights[a==v].sum()**2/(weights[a==v]**2).sum()) for v in [0,1]],
       'smd_before':((means[1]-means[0])/sd).tolist(),'smd_after':((weighted[1]-weighted[0])/sd).tolist()}

def estimate(df,bootstrap=200,seed=812,ipcw=True):
    ar=arrays(df);r=estimate_arrays(*ar,ipcw=ipcw)
    if not r['identified']:return r
    rng=np.random.default_rng(seed);boot=[]
    for _ in range(bootstrap):
        ix=rng.integers(0,len(df),len(df));z=estimate_arrays(*(v[ix] for v in ar),ipcw=ipcw)
        if z['identified'] and np.isfinite(z['rd']):boot.append(z['rd'])
    interval_valid=len(boot)>=.95*bootstrap and len(boot)>1
    se=float(np.std(boot,ddof=1)) if interval_valid else None
    r.update({'bootstrap_se':se,'ci_low':r['rd']-1.96*se if se is not None else None,
              'ci_high':r['rd']+1.96*se if se is not None else None,'bootstrap_valid':len(boot),'interval_valid':interval_valid})
    return r

def simulate_methods(repetitions=200,n=2500,bootstrap=100,seed=20261011):
    records=[];summaries=[]
    for j,scenario in enumerate(SCENARIOS):
        part=[]
        for i in range(repetitions):
            df,truth=generate(n,seed+j*100000+i,scenario);r=estimate(df,bootstrap,seed+700000+j*100000+i)
            row={'scenario':scenario,'replicate':i,'truth':truth['risk_difference'],'identified':r['identified']}
            if r['identified']:
                row.update({k:r[k] for k in ['rd','crude_rd','ci_low','ci_high','bootstrap_se']})
                row['covered']=r['ci_low']<=truth['risk_difference']<=r['ci_high'] if r['interval_valid'] else None
                row['interval_valid']=r['interval_valid']
                row['bias']=r['rd']-truth['risk_difference'];row['crude_bias']=r['crude_rd']-truth['risk_difference']
            part.append(row)
        records+=part;ok=[r for r in part if r['identified']]
        summary={'scenario':scenario,'repetitions':repetitions,'n_per_replicate':n,'bootstrap_per_replicate':bootstrap,'identified_runs':len(ok)}
        if ok:
            errors=np.array([r['bias'] for r in ok]);intervals=[r for r in ok if r['interval_valid']];m=len(ok)
            coverage=np.mean([r['covered'] for r in intervals]) if intervals else 0.0
            summary.update({'bias':float(errors.mean()),'bias_mcse':float(errors.std(ddof=1)/np.sqrt(m)),
                'crude_bias':float(np.mean([r['crude_bias'] for r in ok])),'rmse':float(np.sqrt(np.mean(errors**2))),
                'coverage':float(coverage),'valid_intervals':len(intervals),'interval_failure_fraction':1-len(intervals)/m,
                'coverage_mcse':float(np.sqrt(coverage*(1-coverage)/max(len(intervals),1))),
                'mean_truth':float(np.mean([r['truth'] for r in ok]))})
        summaries.append(summary)
    return records,summaries

def make_database(path,df):
    """Flat toy code sets and labs are explicit; not validated clinical phenotypes."""
    conn=sqlite3.connect(path)
    for name in ['enrollment','diagnoses','labs','fills','events']:
        conn.execute(f'DROP TABLE IF EXISTS {name}')
    conn.executescript('''CREATE TABLE enrollment(person_id INTEGER,start_day INTEGER,end_day INTEGER,age INTEGER);
    CREATE TABLE diagnoses(person_id INTEGER,day INTEGER,code TEXT);
    CREATE TABLE labs(person_id INTEGER,day INTEGER,egfr REAL,uacr REAL);
    CREATE TABLE fills(person_id INTEGER,day INTEGER,drug TEXT,days_supply INTEGER);
    CREATE TABLE events(person_id INTEGER,day INTEGER,event TEXT);''')
    en=[];dx=[];labs=[];fills=[];events=[]
    for r in df.itertuples(index=False):
        pid=int(r.person_id);m=int(r.month);status=int(r.status)
        end=int(round((m-1)*365/12)) if status==3 else 365
        en.append((pid,-500,end,80 if r.older else 70))
        dx.extend([(pid,-240,'T2D'),(pid,-40,'T2D')])
        if r.hf:dx.append((pid,-100,'HF'))
        for day in [-220,-30]:labs.append((pid,day,27. if r.severe else 50.,600.))
        drug='dapagliflozin' if r.a else 'sitagliptin'
        # The index fill is recorded even if disenrollment immediately follows initiation.
        fills.append((pid,0,drug,30))
        last=int(round(m*365/12))-1 if status in [1,2] else end
        for day in range(30,min(last,end)+1,30):fills.append((pid,day,drug,30))
        if status in [1,2]:events.append((pid,int(round(m*365/12))-1,'KRT' if status==1 else 'death'))
    # Four disjoint decoys per type exercise exclusions, kept outside known-truth analysis.
    start=len(df)
    for i in range(20):
        pid=start+i;kind=i%5;en.append((pid,-100 if kind==0 else -500,365,70))
        if kind!=1:dx.extend([(pid,-240,'T2D'),(pid,-40,'T2D')])
        for day in [-220,-30]:labs.append((pid,day,90. if kind==2 else 50.,600.))
        fills.append((pid,0,'dapagliflozin',30))
        if kind==3:fills.append((pid,-60,'sitagliptin',30))
        if kind==4:events.append((pid,-5,'KRT'))
    for name,rows in [('enrollment',en),('diagnoses',dx),('labs',labs),('fills',fills),('events',events)]:
        conn.executemany(f'INSERT INTO {name} VALUES ({",".join("?" for _ in rows[0])})',rows)
    conn.commit();return conn

def extract_cohort(conn):
    return pd.read_sql_query((ROOT/'sql/cohort.sql').read_text(),conn)

def claims_delivery(outdir,seed=711):
    outdir.mkdir(exist_ok=True,parents=True);raw=ROOT/'data';raw.mkdir(exist_ok=True)
    df,truth=generate(seed=seed);db=make_database(raw/'synthetic.sqlite',df);cohort=extract_cohort(db);db.close()
    # Validate SQL reconstruction against generation without exposing latent U/truth to estimator.
    cols=['person_id','older','severe','hf','a','status','month']
    if not df[cols].equals(cohort[cols].astype(df[cols].dtypes)):raise AssertionError('SQL cohort differs from eligible observed data')
    fit=estimate(cohort,bootstrap=300,seed=812)
    no_censor=estimate(cohort,bootstrap=100,seed=913,ipcw=False)
    result={'label':'SYNTHETIC METHOD DEMONSTRATION','n':len(cohort),'excluded_decoys':20,'truth':truth,'iptw_ipcw':fit,
            'iptw_without_ipcw':no_censor,'counts':{str(k):int(v) for k,v in cohort.status.value_counts().items()}}
    (outdir/'claims-demo.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
