/* Base SAS reference CEA replication and budget aggregation QC.
   Set project to the repository directory on the SAS server before running.
   This program does not require SAS/IML. */
%let project=/home/your-user/dapagliflozin-ckd-model;
options errorabend;
%include "&project./sas/reference_inputs.sas";
options dlcreatedir;
libname sasout "&project./sas/output";

data sasout.cea_trace;
  length arm $8;
  array raw[2,2,8,8] _temporary_;
  array renal[2,2,8,8] _temporary_;
  array init[8] _temporary_;
  array haz[8] _temporary_;
  array costs[8] _temporary_;
  array util[8] _temporary_;
  array on[8] _temporary_;
  array off[8] _temporary_;
  array next_on[8] _temporary_;
  array next_off[8] _temporary_;
  array pd[8] _temporary_;
  array state[8] G1 G2 G3a G3b G4 G5 Dialysis Transplant;
  set ckd_parameters;
  do k=1 to 8;
    set ckd_states point=k;
    init[k]=initial; haz[k]=annual_hazard;
    costs[k]=annual_cost*(1-background_drug_share)
      *(1+annual_inflation_2023_2026)**3*cost_scale;
    util[k]=min(1,max(0,utility+utility_shift));
  end;
  do k=1 to 256;
    set ckd_transitions point=k;
    raw[arm_index,phase_index,from_state,to_state]=probability;
  end;
  /* Correct publication rounding in SAS, before applying scenario mixtures. */
  do a=1 to 2; do p=1 to 2; do i=1 to 8;
    row_sum=0;
    do j=1 to 8;
      if missing(raw[a,p,i,j]) or raw[a,p,i,j]<0 or raw[a,p,i,j]>1 then do;
        put 'ERROR: Invalid renal matrix input.'; abort cancel;
      end;
      row_sum=row_sum+raw[a,p,i,j];
    end;
    if abs(row_sum-1)>.0041 then do;
      put 'ERROR: Row exceeds publication rounding tolerance.'; abort cancel;
    end;
    do j=1 to 8;
      if rounding='normalize' then adjusted=raw[a,p,i,j]/row_sum;
      else if rounding='diagonal' then adjusted=raw[a,p,i,j]+(i=j)*(1-row_sum);
      else do; put 'ERROR: Unknown rounding method.'; abort cancel; end;
      renal[a,p,i,j]=renal_speed*adjusted+(1-renal_speed)*(i=j);
    end;
  end; end; end;
  do p=1 to 2; do i=1 to 8; do j=1 to 8;
    renal[1,p,i,j]=effect_retention*renal[1,p,i,j]
      +(1-effect_retention)*renal[2,p,i,j];
  end; end; end;

  do a=1 to 2;
    if a=1 then arm='dapa'; else arm='control';
    dead=0;
    do i=1 to 8;
      on[i]=init[i]*(a=1); off[i]=init[i]*(a=2);
    end;
    stop_probability=1-(1-annual_discontinuation)**(1/12);
    do t=0 to round(horizon_years*12)-1;
      phase=1+(t>=early_months);
      do i=1 to 8;
        if i>=7 or t>=drug_end_month then do;
          off[i]=off[i]+on[i]; on[i]=0;
        end;
        h=haz[i]*mortality_scale
          *2**((age+(t+.5)/12-65)/mortality_age_doubling_years);
        pd[i]=1-exp(-h/12);
        next_on[i]=0; next_off[i]=0;
      end;
      active_arm=1+(t>=effect_end_month);
      new_deaths=0;
      do i=1 to 8;
        new_deaths=new_deaths+(on[i]+off[i])*pd[i];
        do j=1 to 8;
          next_on[j]=next_on[j]+on[i]*(1-pd[i])*renal[active_arm,phase,i,j];
          next_off[j]=next_off[j]+off[i]*(1-pd[i])*renal[2,phase,i,j];
        end;
      end;
      medical=0; qaly=0; ly=0; treatment_months=0; alive=0;
      do i=1 to 8;
        state[i]=next_on[i]+next_off[i];
        occupancy=(on[i]+off[i]+state[i])/2;
        medical=medical+occupancy*costs[i]/12;
        qaly=qaly+occupancy*util[i]/12;
        ly=ly+occupancy/12;
        alive=alive+state[i];
        if i<=6 then treatment_months=treatment_months+(on[i]+next_on[i])/2;
      end;
      drug=treatment_months*(365/12*daily_drug_price+extra_annual_treatment_cost/12);
      qaly=qaly-treatment_months*annual_treatment_disutility/12;
      dead=dead+new_deaths;
      if missing(alive) or abs(alive+dead-1)>1e-10 then do;
        put 'ERROR: CEA population accounting failed.'; abort cancel;
      end;
      do i=1 to 8;
        off[i]=next_off[i]+next_on[i]*stop_probability;
        on[i]=next_on[i]*(1-stop_probability);
      end;
      discount_factor=(1+discount)**(-(t+.5)/12);
      month=t+1;
      output;
    end;
  end;
  stop;
  keep arm month medical drug qaly ly discount_factor treatment_months
       dead alive G1 G2 G3a G3b G4 G5 Dialysis Transplant;
run;

proc sql;
  create table arm_totals as
  select arm, sum(medical*discount_factor) as medical,
    sum(drug*discount_factor) as drug,
    calculated medical+calculated drug as cost,
    sum(qaly*discount_factor) as qaly,
    sum(ly*discount_factor) as ly,
    sum(treatment_months*discount_factor) as treatment_months_discounted,
    min(alive) as survival_end
  from sasout.cea_trace group by arm;
quit;
data sas_cea;
  length group $8 metric $48;
  set arm_totals;
  group=arm;
  array vals[7] medical drug cost qaly ly treatment_months_discounted survival_end;
  do k=1 to dim(vals); metric=vname(vals[k]); value=vals[k]; output; end;
  keep group metric value;
run;
proc sql;
  create table contrasts as
  select d.cost-c.cost as delta_cost, d.qaly-c.qaly as delta_qaly,
    d.ly-c.ly as delta_ly, d.medical-c.medical as delta_medical,
    d.treatment_months_discounted as exposure
  from arm_totals d, arm_totals c where d.arm='dapa' and c.arm='control';
quit;
data contrast_long;
  length group $8 metric $48;
  if _n_=1 then set ckd_parameters(keep=extra_annual_treatment_cost);
  set contrasts;
  group='contrast';
  if delta_qaly>=1e-10 and delta_cost>=0 then icer=delta_cost/delta_qaly;
  else icer=.;
  nmb_at_100k=100000*delta_qaly-delta_cost;
  if exposure>0 then daily_price_threshold_at_100k=
    (100000*delta_qaly-delta_medical-exposure*extra_annual_treatment_cost/12)/(exposure*365/12);
  else daily_price_threshold_at_100k=.;
  array vals[6] delta_cost delta_qaly delta_ly icer nmb_at_100k daily_price_threshold_at_100k;
  do k=1 to dim(vals); metric=vname(vals[k]); value=vals[k]; output; end;
  keep group metric value;
run;
data sas_cea; set sas_cea contrast_long; run;

/* Budget QC starts from Python monthly population traces, not raw renal inputs. */
proc sql;
  create table budget_totals as
  select arm, year, sum(drug) as drug, sum(medical) as medical,
    sum(drug+medical) as total, sum(treatment_months) as exposure
  from budget_monthly_input group by arm, year;
  create table budget_difference as
  select c.year, c.drug as current_drug, c.medical as current_medical,
    c.total as current_total, e.drug as expanded_drug,
    e.medical as expanded_medical, e.total as expanded_total,
    e.drug-c.drug as incremental_drug, e.medical-c.medical as incremental_medical,
    e.total-c.total as incremental_total,
    e.exposure-c.exposure as incremental_treatment_months
  from budget_totals c inner join budget_totals e on c.year=e.year
  where c.arm='current' and e.arm='expanded';
quit;
data sas_budget;
  length group $8 metric $48;
  if _n_=1 then set ckd_parameters(keep=plan_members);
  set budget_difference;
  group=cats('year',put(year,1.));
  pmpm=incremental_total/(plan_members*12);
  if incremental_treatment_months ne 0 then
    incremental_cost_per_add_year=incremental_total/(incremental_treatment_months/12);
  else incremental_cost_per_add_year=.;
  array vals[12] current_drug current_medical current_total expanded_drug
    expanded_medical expanded_total incremental_drug incremental_medical
    incremental_total incremental_treatment_months pmpm incremental_cost_per_add_year;
  do k=1 to dim(vals);
    metric=vname(vals[k]);
    if k=12 then metric='incremental_cost_per_additional_treated_year';
    value=vals[k]; output;
  end;
  keep group metric value;
run;

%macro compare_and_export(name);
  proc sort data=python_&name.; by group metric; run;
  proc sort data=sas_&name.; by group metric; run;
  proc compare base=python_&name. compare=sas_&name.
      method=absolute criterion=1e-6 briefsummary;
    id group metric; var value;
  run;
  %let comparison_code=&sysinfo;
  %if &comparison_code ne 0 %then %do;
    %put ERROR: &name. comparison failed with SYSINFO=&comparison_code.;
    %abort cancel;
  %end;
  /* Export with explicit numeric precision, independent of PROC EXPORT defaults. */
  data _null_;
    set sas_&name.;
    file "&project./sas/output/&name..csv" dlm=',' dsd lrecl=32767;
    if _n_=1 then put 'group,metric,value';
    put group metric value :best32.;
  run;
%mend;
%compare_and_export(cea);
%compare_and_export(budget);

/* Written only after both comparisons pass. Python performs a second audit. */
data _null_;
  file "&project./sas/output/run.csv" dlm=',' dsd lrecl=32767;
  length engine $8 version $64 input_bundle $64 status $16;
  engine='SAS'; version="&sysvlong4.";
  input_bundle="&bundle_id."; status='PASS';
  put 'engine,version,bundle_id,status';
  put engine version input_bundle status;
run;
%put NOTE: CKD_SAS_REFERENCE_CHECKS_PASSED;
