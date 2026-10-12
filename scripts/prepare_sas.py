"""Serialize inputs and Python reference values; never executes SAS."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUTS = [
    'parameters/scenario.json', 'parameters/ckd-transitions-source.json',
    'results/cea.json', 'results/budget-annual.csv',
    'results/budget-monthly-current.csv', 'results/budget-monthly-expanded.csv',
]
SCALARS = [
    'age', 'horizon_years', 'discount', 'early_months',
    'mortality_age_doubling_years', 'background_drug_share',
    'annual_inflation_2023_2026', 'daily_drug_price',
    'annual_discontinuation', 'effect_retention', 'effect_end_month',
    'drug_end_month', 'renal_speed', 'mortality_scale', 'cost_scale',
    'utility_shift', 'extra_annual_treatment_cost', 'annual_treatment_disutility',
]
CEA_METRICS = ['medical', 'drug', 'cost', 'qaly', 'ly',
               'treatment_months_discounted', 'survival_end']
CONTRAST_METRICS = ['delta_cost', 'delta_qaly', 'delta_ly', 'icer',
                    'nmb_at_100k', 'daily_price_threshold_at_100k']
BUDGET_METRICS = ['current_drug', 'current_medical', 'current_total',
                  'expanded_drug', 'expanded_medical', 'expanded_total',
                  'incremental_drug', 'incremental_medical', 'incremental_total',
                  'incremental_treatment_months', 'pmpm',
                  'incremental_cost_per_additional_treated_year']


def read_csv(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def references(root=ROOT):
    cea = json.loads((root / 'results/cea.json').read_text())
    rows = [(arm, metric, cea[arm][metric])
            for arm in ('dapa', 'control') for metric in CEA_METRICS]
    rows += [('contrast', metric, cea[metric]) for metric in CONTRAST_METRICS]
    budget = [(f"year{row['year']}", metric,
               None if row[metric] == '' else float(row[metric]))
              for row in read_csv(root / 'results/budget-annual.csv')
              for metric in BUDGET_METRICS]
    return rows, budget


def number(value):
    if value is None:
        return '.'
    if not math.isfinite(float(value)):
        raise ValueError('Nonfinite input')
    return format(float(value), '.17g')


def dataset(name, columns, rows):
    lengths = ' '.join(f'{col} ${length}' for col, length in columns if length)
    inputs = ' '.join(col + (' $' if length else '') for col, length in columns)
    lines = [f'data {name};']
    if lengths:
        lines.append(f'  length {lengths};')
    lines += ['  infile datalines dlm="|" dsd truncover lrecl=32767;',
              f'  input {inputs};', 'datalines;']
    for row in rows:
        encoded = []
        for value, (_, length) in zip(row, columns, strict=True):
            if length:
                text = str(value)
                if len(text) > length or any(c in text for c in '|;\n\r"'):
                    raise ValueError('Unsafe character value')
                encoded.append(text)
            else:
                encoded.append(number(value))
        lines.append('|'.join(encoded))
    return '\n'.join(lines + [';', 'run;', ''])


def build(root=ROOT):
    cfg = json.loads((root / INPUTS[0]).read_text())
    source = json.loads((root / INPUTS[1]).read_text())
    hashes = {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
              for name in INPUTS}
    program_hash = hashlib.sha256((root / 'sas/replicate_economics.sas').read_bytes()).hexdigest()
    bundle_id = hashlib.sha256(json.dumps(
        {'sources': hashes, 'program': program_hash}, sort_keys=True).encode()).hexdigest()
    code = [f'/* Serialized public inputs; bundle {bundle_id}. */',
            f'%let bundle_id={bundle_id};']
    code.append(dataset('ckd_parameters', [(k, 0) for k in SCALARS] +
                        [('rounding', 12), ('plan_members', 0)],
                        [[cfg[k] for k in SCALARS] + [cfg['rounding'], cfg['bia']['members']]]))
    vectors = ['initial', 'annual_mortality_hazard_at65',
               'annual_background_cost_2023', 'utilities']
    if any(len(cfg[key]) != 8 for key in vectors):
        raise ValueError('Expected eight living states')
    code.append(dataset('ckd_states', [('state_index', 0), ('state_name', 12),
                        ('initial', 0), ('annual_hazard', 0), ('annual_cost', 0), ('utility', 0)],
                        [[i+1, cfg['states'][i], *[cfg[k][i] for k in vectors]] for i in range(8)]))
    matrix_rows = []
    for matrix in source['matrices']:
        arm = 1 if matrix['arm'].startswith('dapagliflozin') else 2
        phase = 1 if matrix['phase_as_printed'] == 'Months 0-4' else 2
        matrix_rows += [[arm, phase, i+1, j+1, float(value)]
                        for i, row in enumerate(matrix['mean']) for j, value in enumerate(row)]
    if len(matrix_rows) != 256 or len({tuple(row[:4]) for row in matrix_rows}) != 256:
        raise ValueError('Expected four complete 8 by 8 raw matrices')
    code.append(dataset('ckd_transitions', [(k, 0) for k in
                        ['arm_index', 'phase_index', 'from_state', 'to_state', 'probability']], matrix_rows))
    monthly = []
    for arm in ('current', 'expanded'):
        rows = read_csv(root / f'results/budget-monthly-{arm}.csv')
        if [int(r['month']) for r in rows] != list(range(1, 37)):
            raise ValueError('Budget trace must have 36 ordered months')
        monthly += [[arm, *[float(r[k]) for k in
                    ['month', 'year', 'drug', 'medical', 'treatment_months']]] for r in rows]
    code.append(dataset('budget_monthly_input', [('arm', 8)] + [(k, 0) for k in
                        ['month', 'year', 'drug', 'medical', 'treatment_months']], monthly))
    cea, budget = references(root)
    for name, rows in [('python_cea', cea), ('python_budget', budget)]:
        code.append(dataset(name, [('group', 8), ('metric', 48), ('value', 0)], rows))
    content = '\n'.join(code)
    manifest = {'source_sha256': hashes, 'program_sha256': program_hash, 'bundle_id': bundle_id,
                'bundle_sha256': hashlib.sha256(content.encode()).hexdigest(),
                'status': 'inputs_prepared_not_SAS_execution',
                'cea_reference_values': len(cea), 'budget_reference_values': len(budget)}
    return content, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    content, manifest = build()
    code_path = ROOT / 'sas/reference_inputs.sas'
    manifest_path = ROOT / 'sas/input-manifest.json'
    if args.check:
        if code_path.read_text() != content or json.loads(manifest_path.read_text()) != manifest:
            raise SystemExit('SAS input bundle is stale; run python scripts/prepare_sas.py')
        print('SAS inputs match saved parameters and reference outputs. SAS execution is not checked.')
    else:
        code_path.parent.mkdir(parents=True, exist_ok=True)
        code_path.write_text(content)
        manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
        print('Prepared SAS inputs. No SAS code has been executed.')


if __name__ == '__main__':
    main()
