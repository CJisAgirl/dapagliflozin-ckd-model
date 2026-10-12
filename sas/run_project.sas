/* DAPAGLIFLOZIN CKD: SINGLE-FILE SAS PROJECT
   Paste this entire file into a new SAS Studio program.
   No data upload, path edit, Python installation or SAS/IML is needed to submit it.
   Reference CEA is recalculated; the budget section checks Python trace aggregation.
   Economic inputs contain explicit assumptions; this is not a clinical forecast.
   SAS execution is pending. Generating this file does not validate its execution.
   Outputs are temporary: download them before ending the SAS session.
*/
%let output_dir=%sysfunc(pathname(work));
libname sasout "&output_dir.";

/* SECTION 1: Embedded parameters and reference results. */
/* Serialized public inputs; bundle 27be29209e0e27c695145398713796924993615230b56b09c94a792b18466b2a. */
%let bundle_id=27be29209e0e27c695145398713796924993615230b56b09c94a792b18466b2a;
data ckd_parameters;
  length rounding $12;
  infile datalines dlm="|" dsd truncover lrecl=32767;
  input age horizon_years discount early_months mortality_age_doubling_years background_drug_share annual_inflation_2023_2026 daily_drug_price annual_discontinuation effect_retention effect_end_month drug_end_month renal_speed mortality_scale cost_scale utility_shift extra_annual_treatment_cost annual_treatment_disutility rounding $ plan_members;
datalines;
65|10|0.029999999999999999|4|10|0.20000000000000001|0.029999999999999999|6.0528940000000002|0|1|1200|1200|1|1|1|0|0|0|normalize|100000
;
run;

data ckd_states;
  length state_name $12;
  infile datalines dlm="|" dsd truncover lrecl=32767;
  input state_index state_name $ initial annual_hazard annual_cost utility;
datalines;
1|G1|0|0.02|30908|0.77000000000000002
2|G2|0.10000000000000001|0.02|30908|0.77000000000000002
3|G3a|0.29999999999999999|0.029999999999999999|34513|0.77000000000000002
4|G3b|0.45000000000000001|0.044999999999999998|34513|0.77000000000000002
5|G4|0.14999999999999999|0.070000000000000007|46557|0.76000000000000001
6|G5|0|0.12|46557|0.72999999999999998
7|Dialysis|0|0.17999999999999999|100000|0.68000000000000005
8|Transplant|0|0.050000000000000003|44645|0.70999999999999996
;
run;

data ckd_transitions;
  infile datalines dlm="|" dsd truncover lrecl=32767;
  input arm_index phase_index from_state to_state probability;
datalines;
1|1|1|1|0.58599999999999997
1|1|1|2|0.219
1|1|1|3|0.049000000000000002
1|1|1|4|0.049000000000000002
1|1|1|5|0.024
1|1|1|6|0.024
1|1|1|7|0.024
1|1|1|8|0.025000000000000001
1|1|2|1|0.017999999999999999
1|1|2|2|0.70899999999999996
1|1|2|3|0.246
1|1|2|4|0.019
1|1|2|5|0.0030000000000000001
1|1|2|6|0.0030000000000000001
1|1|2|7|0.001
1|1|2|8|0.001
1|1|3|1|0.001
1|1|3|2|0.079000000000000001
1|1|3|3|0.749
1|1|3|4|0.16200000000000001
1|1|3|5|0.0080000000000000002
1|1|3|6|0
1|1|3|7|0
1|1|3|8|0
1|1|4|1|0.001
1|1|4|2|0.0050000000000000001
1|1|4|3|0.079000000000000001
1|1|4|4|0.81200000000000006
1|1|4|5|0.10199999999999999
1|1|4|6|0.001
1|1|4|7|0
1|1|4|8|0
1|1|5|1|0.001
1|1|5|2|0.0030000000000000001
1|1|5|3|0.0060000000000000001
1|1|5|4|0.14299999999999999
1|1|5|5|0.84299999999999997
1|1|5|6|0.0040000000000000001
1|1|5|7|0.001
1|1|5|8|0.001
1|1|6|1|0.063
1|1|6|2|0.125
1|1|6|3|0.062
1|1|6|4|0.124
1|1|6|5|0.375
1|1|6|6|0.125
1|1|6|7|0.063
1|1|6|8|0.062
1|1|7|1|0
1|1|7|2|0
1|1|7|3|0
1|1|7|4|0
1|1|7|5|0
1|1|7|6|0
1|1|7|7|0.995
1|1|7|8|0.0050000000000000001
1|1|8|1|0
1|1|8|2|0
1|1|8|3|0
1|1|8|4|0
1|1|8|5|0
1|1|8|6|0
1|1|8|7|0.0070000000000000001
1|1|8|8|0.99299999999999999
1|2|1|1|0.89100000000000001
1|2|1|2|0.070000000000000007
1|2|1|3|0.0089999999999999993
1|2|1|4|0.014999999999999999
1|2|1|5|0.0060000000000000001
1|2|1|6|0.0030000000000000001
1|2|1|7|0.0030000000000000001
1|2|1|8|0.0030000000000000001
1|2|2|1|0.0050000000000000001
1|2|2|2|0.90900000000000003
1|2|2|3|0.078
1|2|2|4|0.0060000000000000001
1|2|2|5|0.002
1|2|2|6|0
1|2|2|7|0
1|2|2|8|0
1|2|3|1|0.001
1|2|3|2|0.025000000000000001
1|2|3|3|0.91300000000000003
1|2|3|4|0.058999999999999997
1|2|3|5|0.002
1|2|3|6|0
1|2|3|7|0
1|2|3|8|0
1|2|4|1|0
1|2|4|2|0.001
1|2|4|3|0.025000000000000001
1|2|4|4|0.93799999999999994
1|2|4|5|0.035000000000000003
1|2|4|6|0
1|2|4|7|0
1|2|4|8|0
1|2|5|1|0
1|2|5|2|0
1|2|5|3|0.001
1|2|5|4|0.035000000000000003
1|2|5|5|0.95199999999999996
1|2|5|6|0.01
1|2|5|7|0.001
1|2|5|8|0
1|2|6|1|0.001
1|2|6|2|0.002
1|2|6|3|0.002
1|2|6|4|0.001
1|2|6|5|0.027
1|2|6|6|0.92000000000000004
1|2|6|7|0.044999999999999998
1|2|6|8|0.002
1|2|7|1|0
1|2|7|2|0
1|2|7|3|0
1|2|7|4|0
1|2|7|5|0
1|2|7|6|0
1|2|7|7|0.995
1|2|7|8|0.0050000000000000001
1|2|8|1|0
1|2|8|2|0
1|2|8|3|0
1|2|8|4|0
1|2|8|5|0
1|2|8|6|0
1|2|8|7|0.0070000000000000001
1|2|8|8|0.99299999999999999
2|1|1|1|0.375
2|1|1|2|0.313
2|1|1|3|0.156
2|1|1|4|0.031
2|1|1|5|0.031
2|1|1|6|0.031
2|1|1|7|0.031
2|1|1|8|0.031
2|1|2|1|0.0089999999999999993
2|1|2|2|0.77000000000000002
2|1|2|3|0.19500000000000001
2|1|2|4|0.016
2|1|2|5|0.0040000000000000001
2|1|2|6|0.002
2|1|2|7|0.002
2|1|2|8|0.001
2|1|3|1|0.002
2|1|3|2|0.070000000000000007
2|1|3|3|0.77400000000000002
2|1|3|4|0.14899999999999999
2|1|3|5|0.0040000000000000001
2|1|3|6|0
2|1|3|7|0
2|1|3|8|0
2|1|4|1|0.002
2|1|4|2|0.0040000000000000001
2|1|4|3|0.084000000000000005
2|1|4|4|0.82599999999999996
2|1|4|5|0.082000000000000003
2|1|4|6|0.001
2|1|4|7|0.001
2|1|4|8|0
2|1|5|1|0.001
2|1|5|2|0.002
2|1|5|3|0.0050000000000000001
2|1|5|4|0.127
2|1|5|5|0.85599999999999998
2|1|5|6|0.0070000000000000001
2|1|5|7|0.001
2|1|5|8|0.001
2|1|6|1|0.042999999999999997
2|1|6|2|0.17399999999999999
2|1|6|3|0.042999999999999997
2|1|6|4|0.043999999999999997
2|1|6|5|0.17499999999999999
2|1|6|6|0.34799999999999998
2|1|6|7|0.13
2|1|6|8|0.042999999999999997
2|1|7|1|0
2|1|7|2|0
2|1|7|3|0
2|1|7|4|0
2|1|7|5|0
2|1|7|6|0
2|1|7|7|0.995
2|1|7|8|0.0050000000000000001
2|1|8|1|0
2|1|8|2|0
2|1|8|3|0
2|1|8|4|0
2|1|8|5|0
2|1|8|6|0
2|1|8|7|0.0070000000000000001
2|1|8|8|0.99299999999999999
2|2|1|1|0.88400000000000001
2|2|1|2|0.074999999999999997
2|2|1|3|0.014999999999999999
2|2|1|4|0.010999999999999999
2|2|1|5|0.0040000000000000001
2|2|1|6|0.0040000000000000001
2|2|1|7|0.0040000000000000001
2|2|1|8|0.0040000000000000001
2|2|2|1|0.0040000000000000001
2|2|2|2|0.91500000000000004
2|2|2|3|0.071999999999999995
2|2|2|4|0.0080000000000000002
2|2|2|5|0.002
2|2|2|6|0
2|2|2|7|0
2|2|2|8|0
2|2|3|1|0
2|2|3|2|0.023
2|2|3|3|0.91000000000000003
2|2|3|4|0.064000000000000001
2|2|3|5|0.0030000000000000001
2|2|3|6|0
2|2|3|7|0
2|2|3|8|0
2|2|4|1|0
2|2|4|2|0.001
2|2|4|3|0.025999999999999999
2|2|4|4|0.93100000000000005
2|2|4|5|0.041000000000000002
2|2|4|6|0
2|2|4|7|0.001
2|2|4|8|0
2|2|5|1|0
2|2|5|2|0.001
2|2|5|3|0.001
2|2|5|4|0.028000000000000001
2|2|5|5|0.95399999999999996
2|2|5|6|0.014
2|2|5|7|0.002
2|2|5|8|0
2|2|6|1|0.001
2|2|6|2|0.001
2|2|6|3|0.001
2|2|6|4|0.002
2|2|6|5|0.037999999999999999
2|2|6|6|0.91000000000000003
2|2|6|7|0.043999999999999997
2|2|6|8|0.0030000000000000001
2|2|7|1|0
2|2|7|2|0
2|2|7|3|0
2|2|7|4|0
2|2|7|5|0
2|2|7|6|0
2|2|7|7|0.995
2|2|7|8|0.0050000000000000001
2|2|8|1|0
2|2|8|2|0
2|2|8|3|0
2|2|8|4|0
2|2|8|5|0
2|2|8|6|0
2|2|8|7|0.0070000000000000001
2|2|8|8|0.99299999999999999
;
run;

data budget_monthly_input;
  length arm $8;
  infile datalines dlm="|" dsd truncover lrecl=32767;
  input arm $ month year drug medical treatment_months;
datalines;
current|1|1|36676.666248429952|2616929.4908387512|199.21184898130286
current|2|1|37101.303564540671|2663758.4961247258|201.5182959281405
current|3|1|37515.957271270403|2710012.5216599195|203.77051621024196
current|4|1|37920.833315979711|2755703.2789801164|205.96962844493783
current|5|1|38316.145916503592|2800840.4787810692|208.11679617121231
current|6|1|38702.115051948218|2845432.1185550699|210.21321422079257
current|7|1|39078.964325838802|2889484.7374171261|212.2600971116882
current|8|1|39446.919155180192|2933003.6413292396|214.25866921194927
current|9|1|39806.20524429153|2975993.1016750881|216.21015645019278
current|10|1|40157.047307008659|3018456.5298922444|218.11577937515779
current|11|1|40499.668005078893|3060396.6306367484|219.97674738952182
current|12|1|40834.287074336571|3101815.5357362786|221.79425400366455
current|13|2|41161.120613608451|3142714.9209831781|223.5694729733068
current|14|2|41480.380514283883|3183096.1076283031|225.3035552011828
current|15|2|41792.274011139256|3222960.1502600801|226.99762629731103
current|16|2|42097.003337367387|3262307.9125897586|228.65278470526286
current|17|2|42394.765468852544|3301140.1325145294|230.27010031317502
current|18|2|42685.751944585929|3339457.4776920998|231.85061347832357
current|19|2|42970.148751762899|3377260.5927353543|233.3953344030208
current|20|2|43248.136265548077|3414550.1390203503|234.90524280744788
current|21|2|43519.889234786708|3451326.8279976621|236.38128785204088
current|22|2|43785.576806065998|3487591.4488017764|237.8243882681854
current|23|2|44045.362579532855|3523344.8908679681|239.23543266139265
current|24|2|44299.40469075719|3558588.162188781|240.61527995594543
current|25|3|44547.855913692547|3593322.4037723723|241.96475995413741
current|26|3|44790.863780485306|3627548.9008017243|243.28467398702361
current|27|3|45028.570714457812|3661269.090937952|244.57579563672778
current|28|3|45261.114173135509|3694484.5701598525|245.83887151330552
current|29|3|45488.626798629055|3727197.0964856087|247.07462207155359
current|30|3|45711.236573097216|3759408.5918833893|248.28374245541659
current|31|3|45929.066977349932|3791121.1426398209|249.46690335945308
current|32|3|46142.237150974703|3822336.9984234073|250.62475189857059
current|33|3|46350.862052615266|3853058.5702509647|251.75791247859311
current|34|3|46555.052619274022|3883288.427539588|252.8669876615198
current|35|3|46754.915923705965|3913029.294402929|253.95255902042507
current|36|3|46950.555329139126|3942284.0453312523|255.0151879798276
expanded|1|1|55018.255002011872|2616635.2085810062|298.83545664799306
expanded|2|1|55658.439198487438|2662883.6368626049|302.31266138096049
expanded|3|1|56283.763880077626|2708572.113190311|305.70915563126761
expanded|4|1|56894.563503406425|2753710.6388368178|309.02675602319601
expanded|5|1|57491.178892507283|2798307.5539529701|312.26731376605147
expanded|6|1|58073.954403535128|2842369.7719045146|315.43269925410272
expanded|7|1|58643.235520341164|2885902.9882855187|318.52478900677812
expanded|8|1|59199.36682807449|2928911.8668067236|321.54545466214392
expanded|9|1|59742.690317746899|2971400.2041355693|324.49655376802986
expanded|10|1|60273.543979901515|3013371.0756360395|327.37992214344348
expanded|11|1|60792.26065021049|3054826.9638254428|330.19736760835377
expanded|12|1|61299.167074047044|3095769.8712341054|332.95066490285126
expanded|13|2|92707.869121182361|3135682.4867892531|503.54920203626631
expanded|14|2|93441.669916668921|3174582.119002129|507.53489180050673
expanded|15|2|94159.698774838747|3213003.2305186116|511.43491519655493
expanded|16|2|94862.424712734399|3250943.9612475568|515.25181972291261
expanded|17|2|95550.293101893607|3288402.9107867549|518.98802444588318
expanded|18|2|96223.727487610959|3325379.0911731948|522.64582988102302
expanded|19|2|96883.131210942811|3361871.8871416543|526.22742680317288
expanded|20|2|97528.888860538937|3397881.0225349478|529.7349041321786
expanded|21|2|98161.367577244178|3433406.5317490716|533.17025601892703
expanded|22|2|98780.918230926531|3468448.7352965074|536.53538823736824
expanded|23|2|99387.876486053647|3503008.2187356628|539.83212397227305
expanded|24|2|99982.563770064895|3537085.8143500024|543.06220907900183
expanded|25|3|134110.1386025165|3570101.2569189877|728.42849176047366
expanded|26|3|134882.46156395032|3602074.5253467704|732.62341733292919
expanded|27|3|135640.54913249778|3633605.4460881134|736.7410223845211
expanded|28|3|136384.77783563701|3664692.6822944423|740.78335205028475
expanded|29|3|137115.49454003363|3695335.7239994016|744.75229036049939
expanded|30|3|137833.02055227384|3725534.7545664934|748.64958251410769
expanded|31|3|138537.65509360103|3755290.5393813597|752.47685375198739
expanded|32|3|139229.67824626243|3784604.3330339054|756.23562536022882
expanded|33|3|139909.35345357686|3813477.8018769431|759.9273282494388
expanded|34|3|140576.92964282824|3841912.9593798732|763.55331448536845
expanded|35|3|141232.64302925015|3869912.1121324385|767.11486708739835
expanded|36|3|141876.71865026563|3897477.8147150152|770.61320836185325
;
run;

data python_cea;
  length group $8 metric $48;
  infile datalines dlm="|" dsd truncover lrecl=32767;
  input group $ metric $ value;
datalines;
dapa|medical|228398.20071005306
dapa|drug|13467.161950105925
dapa|cost|241865.36266015898
dapa|qaly|4.893822573008217
dapa|ly|6.4233936891415651
dapa|treatment_months_discounted|73.147821408825408
dapa|survival_end|0.43926647556277559
control|medical|235841.03555024342
control|drug|0
control|cost|235841.03555024342
control|qaly|4.7508722475238745
control|ly|6.2660243587453861
control|treatment_months_discounted|0
control|survival_end|0.39571469655793429
contrast|delta_cost|6024.3271099155536
contrast|delta_qaly|0.1429503254843425
contrast|delta_ly|0.15736933039617895
contrast|icer|42142.800931050726
contrast|nmb_at_100k|8270.7054385186966
contrast|daily_price_threshold_at_100k|9.7702104999462591
;
run;

data python_budget;
  length group $8 metric $48;
  infile datalines dlm="|" dsd truncover lrecl=32767;
  input group $ metric $ value;
datalines;
year1|current_drug|466056.11248040717
year1|current_medical|34371826.561626375
year1|current_total|34837882.674106784
year1|expanded_drug|699370.41925034742
year1|expanded_medical|34332661.893251628
year1|expanded_total|35032032.312501974
year1|incremental_drug|233314.30676994025
year1|incremental_medical|-39164.668374747038
year1|incremental_total|194149.63839519024
year1|incremental_treatment_months|1267.262791296369
year1|pmpm|0.1617913653293252
year1|incremental_cost_per_additional_treated_year|1838.4471450936999
year2|current_drug|513479.8142182912
year2|current_medical|40264338.76327984
year2|current_total|40777818.577498131
year2|expanded_drug|1157670.4292506999
year2|expanded_medical|40089696.009325348
year2|expanded_total|41247366.43857605
year2|incremental_drug|644190.61503240874
year2|incremental_medical|-174642.75395449251
year2|incremental_total|469547.8610779196
year2|incremental_treatment_months|3498.9658724094734
year2|pmpm|0.39128988423159966
year2|incremental_cost_per_additional_treated_year|1610.3541841792614
year3|current_drug|549510.9580065565
year3|current_medical|45268349.132628858
year3|current_total|45817860.090635419
year3|expanded_drug|1657329.4203426933
year3|expanded_medical|44854019.949733742
year3|expanded_total|46511349.37007644
year3|incremental_drug|1107818.462336137
year3|incremental_medical|-414329.18289511651
year3|incremental_total|693489.27944102138
year3|incremental_treatment_months|6017.1925856825374
year3|pmpm|0.57790773286751784
year3|incremental_cost_per_additional_treated_year|1383.01562311526
;
run;

/* SECTION 2: SAS calculations and comparisons. */

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
    file "&output_dir./&name..csv" dlm=',' dsd lrecl=32767;
    if _n_=1 then put 'group,metric,value';
    put group metric value :best32.;
  run;
%mend;
%compare_and_export(cea);
%compare_and_export(budget);

/* Written only after both comparisons pass. Python performs a second audit. */
data _null_;
  file "&output_dir./run.csv" dlm=',' dsd lrecl=32767;
  length engine $8 version $64 input_bundle $64 status $16;
  engine='SAS'; version="&sysvlong4.";
  input_bundle="&bundle_id."; status='PASS';
  put 'engine,version,bundle_id,status';
  put engine version input_bundle status;
run;
%put NOTE: CKD_SAS_REFERENCE_CHECKS_PASSED;

/* SECTION 3: Display the main outputs in the SAS Studio Results tab. */
title "Reference cost-effectiveness model: costs and health outcomes";
proc print data=arm_totals noobs;
  var arm medical drug cost qaly ly survival_end;
  format medical drug cost comma16.2 qaly ly 12.6 survival_end percent10.2;
run;
title "Incremental cost-effectiveness results: conditional on model assumptions";
proc print data=sas_cea(where=(group='contrast')) noobs;
  var metric value;
  format value best20.;
run;
title "Three-year budget aggregation check";
proc print data=sas_budget noobs;
  var group metric value;
  format value best20.;
run;
title;
%put NOTE: CSV exports are in &output_dir.;
%put NOTE: Download cea.csv, budget.csv and run.csv, and save the SAS log before closing this session.;
