"""Input/export safeguards only. These tests do not run or validate the SAS engine."""
import copy
import json
import tempfile
from pathlib import Path
import unittest
from scripts.prepare_sas import ROOT, build, references, standalone_program
from scripts.verify_sas import compare_rows, verify


class SasBridgeTests(unittest.TestCase):
    def setUp(self):
        self.expected = [('dapa', 'cost', 100.0), ('contrast', 'delta_qaly', .125),
                         ('contrast', 'icer', None)]
        self.rows = [{'group': g, 'metric': m, 'value': '.' if v is None else str(v)}
                     for g, m, v in self.expected]

    def test_export_comparison_and_allowed_missing_icer(self):
        result = compare_rows(self.rows, self.expected)
        self.assertEqual(result['values_checked'], 3)

    def test_duplicate_or_missing_keys_fail(self):
        for rows in (self.rows + [self.rows[0]], self.rows[:-1]):
            with self.assertRaises(ValueError):
                compare_rows(rows, self.expected)

    def test_nonfinite_missing_or_changed_outputs_fail(self):
        for token in ('nan', 'inf', '.', '101'):
            rows = copy.deepcopy(self.rows); rows[0]['value'] = token
            with self.assertRaises(ValueError):
                compare_rows(rows, self.expected)

    def test_health_outcomes_have_tighter_tolerance(self):
        rows = copy.deepcopy(self.rows); rows[1]['value'] = str(.125+1e-7)
        with self.assertRaises(ValueError):
            compare_rows(rows, self.expected)

    def test_bundle_structure_and_reference_counts(self):
        content, manifest = build()
        self.assertEqual(manifest['status'], 'inputs_prepared_not_SAS_execution')
        self.assertIn('data ckd_transitions;', content)
        self.assertEqual(tuple(map(len, references())), (20, 36))

    def test_absent_engine_output_cannot_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(OSError):
                verify(Path(directory), Path(directory) / 'sas.log')

    def test_standalone_has_inputs_and_no_server_path_dependency(self):
        content, _ = build()
        program = standalone_program(content)
        self.assertIn(content, program)
        self.assertNotIn('%include', program.lower())
        self.assertNotIn('&project', program.lower())
        self.assertIn('%sysfunc(pathname(work))', program)
        self.assertIn('file "&output_dir./run.csv"', program)
        self.assertEqual(program.count('data sasout.cea_trace;'), 1)


if __name__ == '__main__':
    unittest.main()
