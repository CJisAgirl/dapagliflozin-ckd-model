"""Transparent monthly scenario model. No clinical validation is implied."""
from copy import deepcopy
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

def load_inputs():
    cfg = json.loads((ROOT/'parameters/scenario.json').read_text())
    source = json.loads((ROOT/'parameters/ckd-transitions-source.json').read_text())
    matrices = {}
    for m in source['matrices']:
        arm = 'dapa' if m['arm'].startswith('dapagliflozin') else 'control'
        phase = 'early' if m['phase_as_printed'] == 'Months 0-4' else 'late'
        matrices[arm, phase] = np.asarray(m['mean'], dtype=float)
    return cfg, matrices

def stochastic(raw, method='normalize'):
    x = np.asarray(raw, float).copy()
    if x.shape != (8,8) or np.any(x < 0) or np.any(x > 1):
        raise ValueError('Expected an 8 by 8 probability matrix')
    if np.max(np.abs(x.sum(axis=1)-1)) > .0041:
        raise ValueError('Row error exceeds publication rounding tolerance')
    if method == 'normalize': x /= x.sum(axis=1, keepdims=True)
    elif method == 'diagonal': x[np.diag_indices(8)] += 1-x.sum(axis=1)
    else: raise ValueError('Unknown rounding correction')
    if x.min() < 0 or not np.allclose(x.sum(axis=1),1): raise ValueError('Invalid correction')
    return x

def prepare(cfg, matrices):
    out = {k:stochastic(v, cfg['rounding']) for k,v in matrices.items()}
    speed = cfg['renal_speed']
    if not 0 <= speed <= 1: raise ValueError('Renal speed must be a mixture weight [0,1]')
    out = {k:speed*v+(1-speed)*np.eye(8) for k,v in out.items()}
    a = cfg['effect_retention']
    if not 0 <= a <= 1: raise ValueError('Retention must be in [0,1]')
    for phase in ['early','late']:
        out['dapa',phase] = a*out['dapa',phase]+(1-a)*out['control',phase]
    return out

def death_probability(cfg, age):
    h = np.asarray(cfg['annual_mortality_hazard_at65'])*cfg['mortality_scale']
    h = h*2**((age-65)/cfg['mortality_age_doubling_years'])
    return -np.expm1(-h/12)

def transition_with_death(renal, death):
    """Mortality first; renal movements conditional on surviving the cycle."""
    p=np.zeros((9,9));p[:8,:8]=(1-death[:,None])*renal;p[:8,8]=death;p[8,8]=1
    return p

def cost_vector(cfg):
    return (np.asarray(cfg['annual_background_cost_2023'])*(1-cfg['background_drug_share'])
            *(1+cfg['annual_inflation_2023_2026'])**3*cfg['cost_scale'])

def step(v, renal, death):
    alive = v*(1-death)
    nxt = alive @ renal
    return nxt, float(v@death)

def cohort(cfg, matrices, arm='dapa', months=None):
    if arm not in ('dapa','control'): raise ValueError('Unknown arm')
    months = int(round(cfg['horizon_years']*12)) if months is None else months
    if months < 1: raise ValueError('Positive horizon required')
    initial=np.asarray(cfg['initial'],float)
    if initial.shape!=(8,) or initial.min()<0 or not np.isclose(initial.sum(),1): raise ValueError('Invalid initial distribution')
    mat=prepare(cfg,matrices); costs=cost_vector(cfg)
    utilities=np.clip(np.asarray(cfg['utilities'])+cfg['utility_shift'],0,1)
    on=initial.copy() if arm=='dapa' else np.zeros(8)
    off=np.zeros(8) if arm=='dapa' else initial.copy()
    dead=0.;trace=[]
    stop=1-(1-cfg['annual_discontinuation'])**(1/12)
    for t in range(months):
        phase='early' if t<cfg['early_months'] else 'late'
        before=on+off
        # KRT permanently ends drug exposure; never restart after discontinuation.
        off[6:]+=on[6:];on[6:]=0
        if t>=cfg['drug_end_month']: off+=on;on[:]=0
        pdeath=death_probability(cfg,cfg['age']+(t+.5)/12)
        on_matrix=mat['dapa' if t<cfg['effect_end_month'] else 'control',phase]
        nxt_on,d_on=step(on,on_matrix,pdeath)
        nxt_off,d_off=step(off,mat['control',phase],pdeath)
        end_alive=nxt_on+nxt_off
        # Mid-cycle occupancy correction; death occurs once, before renal transition.
        occupancy=(before+end_alive)/2
        exposure=(on[:6].sum()+nxt_on[:6].sum())/2
        drug=exposure*(365/12*cfg['daily_drug_price']+cfg['extra_annual_treatment_cost']/12)
        medical=float(occupancy@costs/12)
        qaly=float(occupancy@utilities/12-exposure*cfg['annual_treatment_disutility']/12)
        ly=float(occupancy.sum()/12)
        dead+=d_on+d_off
        # Additional policy deviation at end of cycle, not fitted trial adherence.
        stopped=nxt_on*stop;on=nxt_on-stopped;off=nxt_off+stopped
        disc=(1+cfg['discount'])**(-(t+.5)/12)
        row={'month':t+1,'medical':medical,'drug':float(drug),'qaly':qaly,'ly':ly,'discount':disc,
             'treatment_months':float(exposure),'dead':dead,'alive':float(end_alive.sum())}
        row.update({s:float(end_alive[i]) for i,s in enumerate(cfg['states'])})
        trace.append(row)
        if not np.isclose(end_alive.sum()+dead,1,atol=1e-10): raise AssertionError('Mass not conserved')
    totals={k:float(sum(r[k]*r['discount'] for r in trace)) for k in ['medical','drug','qaly','ly']}
    totals['cost']=totals['medical']+totals['drug']
    totals['treatment_months_discounted']=float(sum(r['treatment_months']*r['discount'] for r in trace))
    totals['survival_end']=trace[-1]['alive']
    return totals,trace

def contrast(dapa,control,wtp=100000):
    dc=dapa['cost']-control['cost'];dq=dapa['qaly']-control['qaly']
    if abs(dq)<1e-10: label='no QALY difference';icer=None
    elif dq>0 and dc<0:label='dominant';icer=None
    elif dq<0 and dc>0:label='dominated';icer=None
    elif dq>0:label='more effective, more costly';icer=dc/dq
    else:label='less effective, less costly';icer=None
    return {'delta_cost':dc,'delta_qaly':dq,'delta_ly':dapa['ly']-control['ly'],
            'icer':icer,'classification':label,'nmb_at_100k':wtp*dq-dc}

def evaluate(cfg,matrices):
    d,dt=cohort(cfg,matrices,'dapa');c,ct=cohort(cfg,matrices,'control')
    result={'dapa':d,'control':c,**contrast(d,c)}
    exposure=d['treatment_months_discounted']*365/12
    # Threshold includes all modeled background/penalty costs; assumes no price response in uptake.
    result['daily_price_threshold_at_100k']=(100000*result['delta_qaly']-(d['medical']-c['medical'])
        - d['treatment_months_discounted']*cfg['extra_annual_treatment_cost']/12)/exposure if exposure else None
    return result,{'dapa':dt,'control':ct}

def budget(cfg, matrices, targets=None):
    """Open population, existing users, age-specific cohorts, explicit stops/exits."""
    b=cfg['bia'];targets=targets or b['expanded_targets'];mat=prepare(cfg,matrices)
    costs=cost_vector(cfg);initial=np.asarray(cfg['initial']);p_exit=1-(1-b['annual_disenrollment'])**(1/12)
    p_stop=1-(1-b['annual_discontinuation'])**(1/12)
    # List entries: [renal occupancy, age at month zero, start month or None, kind].
    f=b['initial_treated_fraction'];cohorts=[{'v':initial*b['eligible_initial']*(1-f),'age0':cfg['age'],'start':None,'kind':'naive'},
         {'v':initial*b['eligible_initial']*f,'age0':cfg['age'],'start':-12,'kind':'on'}]
    rows=[];cumulative_dead=0.;cumulative_exit=0.
    for t in range(36):
        entrants=b['monthly_new_eligible'] if t>0 else 0
        if entrants:cohorts.append({'v':initial*entrants,'age0':cfg['age']-t/12,'start':None,'kind':'naive'})
        pre_total=sum(x['v'].sum() for x in cohorts)
        # KRT stops; retain histories in permanent off-treatment pool.
        extra=[]
        for x in cohorts:
            if x['kind']=='on' and x['v'][6:].sum()>0:
                v=np.zeros(8);v[6:]=x['v'][6:];x['v'][6:]=0
                extra.append({'v':v,'age0':x['age0'],'start':None,'kind':'off'})
        cohorts+=extra
        eligible=sum(x['v'][:6].sum() for x in cohorts)
        on_count=sum(x['v'][:6].sum() for x in cohorts if x['kind']=='on')
        start_mask=np.array([0.,1.,1.,1.,b['g4_start_eligible_fraction'],0.,0.,0.])
        available=sum(x['v']@start_mask for x in cohorts if x['kind']=='naive')
        needed=max(0,eligible*targets[t//12]-on_count)
        fraction=min(1,needed/available) if available else 0
        starts=0;extra=[]
        for x in cohorts:
            if x['kind']=='naive':
                v=x['v']*start_mask*fraction;x['v']-=v;starts+=v.sum()
                if v.sum()>0:extra.append({'v':v,'age0':x['age0'],'start':t,'kind':'on'})
        cohorts+=extra
        drug=medical=exposure=deaths=exits=stops=0.;extra=[]
        for x in cohorts:
            v=x['v'];is_on=x['kind']=='on'
            duration=t-x['start'] if is_on else t
            phase='late'  # Prevalent-plan approximation: same phase in both strategies.
            pdeath=death_probability(cfg,x['age0']+(t+.5)/12)
            nxt,d=step(v,mat['dapa' if is_on else 'control',phase],pdeath)
            exit_v=nxt*p_exit;nxt-=exit_v;deaths+=d;exits+=exit_v.sum()
            occupancy=(v+nxt)/2
            medical+=occupancy@costs/12*b['medical_payment_share']
            if is_on:
                exp=(v[:6].sum()+nxt[:6].sum())/2
                exposure+=exp;drug+=exp*365/12*cfg['daily_drug_price']*b['drug_payment_share']
                stopped=nxt*p_stop;nxt-=stopped;stops+=stopped.sum()
                if stopped.sum()>0:extra.append({'v':stopped,'age0':x['age0'],'start':None,'kind':'off'})
            x['v']=nxt
        cohorts+=extra
        remaining=sum(x['v'].sum() for x in cohorts)
        if not np.isclose(pre_total,remaining+deaths+exits,atol=1e-7):raise AssertionError('BIA accounting')
        cumulative_dead+=deaths;cumulative_exit+=exits
        rows.append({'month':t+1,'year':t//12+1,'eligible_pre_krt':float(eligible),'population_end':float(remaining),
          'entrants':entrants,'starts':float(starts),'stops':float(stops),'deaths':float(deaths),'exits':float(exits),
          'treatment_months':float(exposure),'drug':float(drug),'medical':float(medical),'total':float(drug+medical),
          'target':targets[t//12],'achieved_start_fraction':float((on_count+starts)/eligible) if eligible else 0})
    return rows

def budget_comparison(cfg,matrices):
    current=budget(cfg,matrices,cfg['bia']['current_targets']);expanded=budget(cfg,matrices,cfg['bia']['expanded_targets'])
    annual=[]
    for year in [1,2,3]:
        row={'year':year}
        for name,data in [('current',current),('expanded',expanded)]:
            selected=[r for r in data if r['year']==year]
            for k in ['drug','medical','total','treatment_months','starts','stops','deaths','exits','entrants']:
                row[name+'_'+k]=sum(r[k] for r in selected)
            row[name+'_population_end']=selected[-1]['population_end']
            row[name+'_eligible_average']=sum(r['eligible_pre_krt'] for r in selected)/12
        for k in ['drug','medical','total','treatment_months']: row['incremental_'+k]=row['expanded_'+k]-row['current_'+k]
        row['pmpm']=row['incremental_total']/(cfg['bia']['members']*12)
        row['incremental_cost_per_additional_treated_year']=row['incremental_total']/(row['incremental_treatment_months']/12) if row['incremental_treatment_months'] else None
        annual.append(row)
    return annual,{'current':current,'expanded':expanded}

def scenarios(cfg,matrices):
    specs=[('reference',{}),('horizon_3y',{'horizon_years':3}),('horizon_5y',{'horizon_years':5}),
      ('lifetime_age100_exploratory',{'horizon_years':100-cfg['age']}),('discount_0',{'discount':0}),('discount_5pct',{'discount':.05}),
      ('drug_price_half',{'daily_drug_price':cfg['daily_drug_price']/2}),('drug_price_double',{'daily_drug_price':cfg['daily_drug_price']*2}),
      ('mortality_half',{'mortality_scale':.5}),('mortality_double',{'mortality_scale':2}),
      ('medical_cost_half',{'cost_scale':.5}),('medical_cost_1_5',{'cost_scale':1.5}),
      ('no_inflation',{'annual_inflation_2023_2026':0}),('inflation_6pct',{'annual_inflation_2023_2026':.06}),
      ('background_drug_share_0',{'background_drug_share':0}),('background_drug_share_30pct',{'background_drug_share':.3}),
      ('utility_minus_005',{'utility_shift':-.05}),('utility_plus_005',{'utility_shift':.05}),
      ('no_arm_contrast',{'effect_retention':0}),('half_arm_contrast',{'effect_retention':.5}),
      ('slower_renal_movement',{'renal_speed':.5}),('stop_effect_only_after_30m',{'effect_end_month':30}),
      ('stop_drug_and_effect_after_30m',{'effect_end_month':30,'drug_end_month':30}),
      ('additional_stop_10pct',{'annual_discontinuation':.1}),('additional_stop_20pct',{'annual_discontinuation':.2}),
      ('early_5cycles',{'early_months':5}),('rounding_diagonal',{'rounding':'diagonal'}),
      ('age75',{'age':75}),('age80',{'age':80}),
      ('initial_G3a_only',{'initial':[0,0,1,0,0,0,0,0]}),('initial_G4_only',{'initial':[0,0,0,0,1,0,0,0]}),
      ('treatment_burden',{'extra_annual_treatment_cost':250,'annual_treatment_disutility':.01})]
    rows=[]
    for name,changes in specs:
        c=deepcopy(cfg);c.update(changes);r,_=evaluate(c,matrices)
        rows.append({'scenario':name,**{k:v for k,v in r.items() if not isinstance(v,dict)}})
    return rows

def psa(cfg,matrices,n=1000,seed=20261011):
    rng=np.random.default_rng(seed);rows=[]
    for i in range(n):
        c=deepcopy(cfg)
        for key,cv in [('cost_scale',.2),('mortality_scale',.3)]:
            sigma=np.sqrt(np.log1p(cv**2));c[key]=float(rng.lognormal(-sigma*sigma/2,sigma))
        c['daily_drug_price']*=float(rng.uniform(.5,1.5));c['effect_retention']=float(rng.uniform(0,1))
        c['utility_shift']=float(rng.normal(0,.03))
        r,_=evaluate(c,matrices)
        rows.append({'draw':i,**{k:r[k] for k in ['delta_cost','delta_qaly','nmb_at_100k']},
                     **{k:c[k] for k in ['cost_scale','mortality_scale','daily_drug_price','effect_retention','utility_shift']}})
    return rows


def budget_scenarios(cfg,matrices):
    specs=[('reference',{},{}),('drug_price_half',{'daily_drug_price':cfg['daily_drug_price']/2},{}),
      ('drug_price_double',{'daily_drug_price':cfg['daily_drug_price']*2},{}),
      ('eligible_half',{}, {'eligible_initial':500,'monthly_new_eligible':10}),
      ('eligible_double',{}, {'eligible_initial':2000,'monthly_new_eligible':40}),
      ('stop_0',{}, {'annual_discontinuation':0}),('stop_20pct',{}, {'annual_discontinuation':.2}),
      ('no_new_eligible',{}, {'monthly_new_eligible':0}),('exit_10pct',{}, {'annual_disenrollment':.1}),
      ('drug_payment_half',{}, {'drug_payment_share':.5}),('medical_payment_half',{}, {'medical_payment_share':.5}),
      ('slower_uptake',{}, {'expanded_targets':[.25,.3,.4]}),('no_G4_starts',{}, {'g4_start_eligible_fraction':0}),
      ('no_arm_contrast',{'effect_retention':0},{})]
    rows=[]
    for name,changes,bchanges in specs:
        c=deepcopy(cfg);c.update(changes);c['bia'].update(bchanges);b,_=budget_comparison(c,matrices)
        for r in b:rows.append({'scenario':name,**r})
    return rows
