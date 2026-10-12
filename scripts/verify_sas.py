"""Audit actual SAS exports and a saved SAS log; fixtures are not execution evidence."""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
try:
    from .prepare_sas import ROOT, build, read_csv, references
except ImportError:
    from prepare_sas import ROOT, build, read_csv, references


def compare_rows(actual, expected):
    found = {}
    for row in actual:
        key = (row['group'], row['metric'])
        if key in found:
            raise ValueError(f'Duplicate output key: {key}')
        token = row['value'].strip()
        value = None if token in ('', '.') else float(token)
        if value is not None and not math.isfinite(value):
            raise ValueError(f'Nonfinite output: {key}')
        found[key] = value
    wanted = {(group, metric): value for group, metric, value in expected}
    if set(found) != set(wanted):
        raise ValueError('Output keys differ from the full reference set')
    errors = {}
    for key, value in wanted.items():
        observed = found[key]
        if value is None or observed is None:
            if observed != value:
                raise ValueError(f'Unexpected missing value: {key}')
            continue
        tolerance = 1e-9 if key[1] in ('qaly', 'ly', 'delta_qaly', 'delta_ly', 'survival_end') else 1e-6
        error = abs(observed-value)
        if error > tolerance:
            raise ValueError(f'{key}: difference {error} exceeds {tolerance}')
        errors['/'.join(key)] = error
    return {'values_checked': len(wanted), 'absolute_errors': errors}


def verify(output, log, root=ROOT):
    content, manifest = build(root)
    if (root / 'sas/reference_inputs.sas').read_text() != content:
        raise ValueError('Stale SAS input bundle; regenerate and rerun SAS')
    if json.loads((root / 'sas/input-manifest.json').read_text()) != manifest:
        raise ValueError('Input manifest does not match current sources')
    meta = read_csv(output / 'run.csv')
    if len(meta) != 1 or meta[0].get('engine') != 'SAS' or meta[0].get('status') != 'PASS':
        raise ValueError('SAS completion record is absent or unsuccessful')
    if meta[0].get('bundle_id') != manifest['bundle_id']:
        raise ValueError('Run used different inputs or SAS program')
    if not re.match(r'^(9\.|V\.)', meta[0].get('version', '')):
        raise ValueError('Expected a SAS SYSVLONG4 version string')
    text = log.read_text(errors='replace')
    if 'NOTE: CKD_SAS_REFERENCE_CHECKS_PASSED' not in text:
        raise ValueError('Saved SAS log lacks the completion marker')
    if re.search(r'^\s*ERROR(?:\s+\d+(?:-\d+)?)?\s*:|is uninitialized|Invalid numeric data|'
                 r'Missing values were generated', text, flags=re.I | re.M):
        raise ValueError('SAS log contains an error or invalid-value diagnostic')
    cea, budget = references(root)
    return {'status': 'PASS', 'verified_at': datetime.now(timezone.utc).isoformat(),
            'engine': 'SAS', 'version': meta[0]['version'], 'bundle_id': manifest['bundle_id'],
            'cea': compare_rows(read_csv(output / 'cea.csv'), cea),
            'budget_aggregation': compare_rows(read_csv(output / 'budget.csv'), budget),
            'scope': 'Reference CEA recomputation and budget aggregation; no independent BIA population model, PSA or causal estimator.',
            'clinical_validation': 'Not established by this computational comparison.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'sas/output')
    parser.add_argument('--log', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = verify(args.output, args.log)
    except (ValueError, KeyError, OSError) as error:
        if args.output.is_dir():
            (args.output / 'verification.json').write_text(json.dumps(
                {'status': 'FAIL', 'reason': str(error)}, indent=2) + '\n')
        raise SystemExit(f'SAS verification failed: {error}')
    (args.output / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(f"PASS: {result['cea']['values_checked']} CEA and "
          f"{result['budget_aggregation']['values_checked']} budget values checked against Python.")


if __name__ == '__main__':
    main()
