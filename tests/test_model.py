import copy
import sqlite3
import unittest
import numpy as np
from model.economics import load_inputs,stochastic,prepare,transition_with_death,cohort,evaluate,budget_comparison
from model.claims import generate,estimate,estimate_arrays,arrays,make_database,extract_cohort

class EconomicsTests(unittest.TestCase):
    def setUp(self):self.c,self.m=load_inputs()
    def test_augmented_matrix_death_absorbing(self):
        for r in self.m.values():
            p=transition_with_death(stochastic(r),np.linspace(0,.2,8))
            np.testing.assert_allclose(p.sum(1),1);np.testing.assert_equal(p[8],np.eye(9)[8]);self.assertGreaterEqual(p.min(),0)
    def test_same_arms_zero_increment(self):
        self.c.update(effect_retention=0,daily_drug_price=0)
        r,_=evaluate(self.c,self.m)
        self.assertAlmostEqual(r['delta_cost'],0,7);self.assertAlmostEqual(r['delta_qaly'],0,10)
    def test_no_effect_positive_price_only_drug_increment(self):
        self.c['effect_retention']=0;r,_=evaluate(self.c,self.m)
        self.assertAlmostEqual(r['delta_cost'],r['dapa']['drug'],6);self.assertAlmostEqual(r['delta_qaly'],0,10)
    def test_analytic_immortal_identity(self):
        self.c.update(annual_mortality_hazard_at65=[0]*8,discount=0,horizon_years=1,initial=[0,1,0,0,0,0,0,0])
        m={k:np.eye(8) for k in self.m};r,_=evaluate(self.c,m)
        self.assertAlmostEqual(r['dapa']['ly'],1);self.assertAlmostEqual(r['dapa']['qaly'],.77)
        self.assertAlmostEqual(r['dapa']['drug'],6.052894*365)
    def test_mass_and_accounting(self):
        r,tr=evaluate(self.c,self.m)
        for arm,rows in tr.items():
            for row in rows:
                self.assertAlmostEqual(sum(row[s] for s in self.c['states'])+row['dead'],1)
            # Independent vector dot product of undiscounted stored cashflows.
            cash=np.asarray([x['medical']+x['drug'] for x in rows]);d=np.asarray([x['discount'] for x in rows])
            self.assertAlmostEqual(float(cash@d),r[arm]['cost'],6)
    def test_monthly_survival_closed_form(self):
        self.c.update(annual_mortality_hazard_at65=[.12]*8,mortality_age_doubling_years=1e15,discount=0)
        m={k:np.eye(8) for k in self.m};r,_=cohort(self.c,m,'control',months=12)
        self.assertAlmostEqual(r['survival_end'],np.exp(-.12),10)
    def test_discount_decreases_positive_totals(self):
        c=copy.deepcopy(self.c);c['discount']=0
        a,_=cohort(self.c,self.m);b,_=cohort(c,self.m)
        for key in ['cost','ly','qaly']:self.assertLess(a[key],b[key])
    def test_discontinuation_changes_both_cost_and_health(self):
        a,_=evaluate(self.c,self.m);self.c['annual_discontinuation']=.2;b,_=evaluate(self.c,self.m)
        self.assertLess(b['dapa']['drug'],a['dapa']['drug']);self.assertNotAlmostEqual(a['delta_qaly'],b['delta_qaly'])
    def test_budget_identical_strategies(self):
        self.c['bia']['expanded_targets']=self.c['bia']['current_targets']
        rows,_=budget_comparison(self.c,self.m)
        for r in rows:self.assertAlmostEqual(r['incremental_total'],0,7)
    def test_no_treated_budget_and_pmpm(self):
        b=self.c['bia'];b.update(initial_treated_fraction=0,current_targets=[0]*3,expanded_targets=[0]*3)
        rows,_=budget_comparison(self.c,self.m)
        for r in rows:self.assertEqual(r['expanded_drug'],0);self.assertEqual(r['pmpm'],0)
    def test_budget_open_population_reconciliation(self):
        rows,monthly=budget_comparison(self.c,self.m)
        for arm,data in monthly.items():
            expected=self.c['bia']['eligible_initial']+sum(x['entrants']-x['deaths']-x['exits'] for x in data)
            self.assertAlmostEqual(expected,data[-1]['population_end'],6)
        for r in rows:self.assertAlmostEqual(r['pmpm']*1200000,r['incremental_drug']+r['incremental_medical'],6)
    def test_budget_no_effect_has_no_medical_difference(self):
        self.c['effect_retention']=0
        rows,_=budget_comparison(self.c,self.m)
        for r in rows:self.assertAlmostEqual(r['incremental_medical'],0,6)
    def test_invalid_inputs_fail(self):
        with self.assertRaises(ValueError):stochastic(np.ones((8,8)))
        self.c['initial']=[0]*8
        with self.assertRaises(ValueError):cohort(self.c,self.m)

class ClaimsTests(unittest.TestCase):
    def test_sql_preserves_early_loss_and_excludes_decoys(self):
        df,_=generate(1000,seed=2);conn=make_database(':memory:',df);out=extract_cohort(conn);conn.close()
        np.testing.assert_array_equal(df.to_numpy(),out.to_numpy());self.assertTrue(((out.status==3)&(out.month==1)).any())
    def test_complete_cell_censoring_is_rejected(self):
        df,_=generate(4000,seed=22)
        ix=(df.older==1)&(df.severe==1)&(df.hf==1)&(df.a==0)
        df.loc[ix,'status']=3;df.loc[ix,'month']=1
        r=estimate(df,20);self.assertFalse(r['identified']);self.assertIn('censoring',r['reason'])
    def test_drug_price_matches_verified_source(self):
        import json
        from model.economics import ROOT
        c,_=load_inputs();e=json.loads((ROOT/'parameters/cms-price-evidence.json').read_text())
        self.assertEqual(c['daily_drug_price'],float(e['arithmetic_scenarios_usd']['per_tablet']))
    def test_reproducible_generation(self):
        a,ta=generate(200,seed=3);b,tb=generate(200,seed=3);self.assertTrue(a.equals(b));self.assertEqual(ta,tb)
    def test_positivity_failure_declared(self):
        df,_=generate(1000,scenario='positivity_failure');self.assertFalse(estimate(df,20)['identified'])
    def test_saturated_weights_balance_observed_covariates(self):
        df,_=generate(3000);r=estimate(df,30)
        self.assertLess(max(abs(x) for x in r['smd_after']),1e-10)
    def test_known_truth_large_sample(self):
        df,truth=generate(100000,seed=44,scenario='informative_censoring');r=estimate_arrays(*arrays(df))
        self.assertLess(abs(r['rd']-truth['risk_difference']),.008)
    def test_competing_deaths_not_censored(self):
        df,_=generate(8000,scenario='measured_confounding');r=estimate(df,20)
        self.assertEqual(r['min_censor_survival'],1);self.assertTrue((df.status==2).any())

if __name__=='__main__':unittest.main()
