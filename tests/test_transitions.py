"""Input-integrity tests for the published transition reference."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("transitions", ROOT / "scripts/extract_ckd_transitions.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TransitionIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / "parameters/ckd-transitions-source.json").read_text())
        self.matrices = copy.deepcopy(self.data["matrices"])

    def test_reference_audit_and_scope(self):
        self.assertEqual(module.audit_matrices(self.matrices), json.loads((ROOT / "results/transition-input-audit.json").read_text()))
        self.assertFalse(self.data["mortality_included"])
        self.assertEqual(self.data["use_status"], "published_source_reference")

    def test_rounding_differences_are_preserved(self):
        before = copy.deepcopy(self.matrices)
        audit = module.audit_matrices(self.matrices)
        self.assertEqual(audit["nonunit_rows_as_printed"], 10)
        self.assertEqual(audit["max_absolute_row_sum_deviation"], "0.002")
        self.assertEqual(self.matrices, before)

    def test_large_probability_mass_error_is_rejected(self):
        self.matrices[0]["mean"][0][0] = "0.600"
        with self.assertRaisesRegex(ValueError, "Row sum"):
            module.audit_matrices(self.matrices)

    def test_invalid_probability_or_se_is_rejected(self):
        for field, value in [("mean", "-0.001"), ("mean", "NaN"), ("se", "-0.001"), ("se", "Infinity")]:
            with self.subTest(field=field, value=value):
                damaged = copy.deepcopy(self.matrices)
                damaged[0][field][0][0] = value
                with self.assertRaises(ValueError):
                    module.audit_matrices(damaged)

    def test_missing_g1_is_rejected(self):
        self.matrices[0]["from_states"] = self.matrices[0]["from_states"][1:]
        with self.assertRaisesRegex(ValueError, "state"):
            module.audit_matrices(self.matrices)

    def test_duplicate_phase_is_rejected(self):
        self.matrices[1]["phase_as_printed"] = self.matrices[0]["phase_as_printed"]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            module.audit_matrices(self.matrices)

    def test_missing_cell_is_rejected(self):
        self.matrices[0]["mean"][0].pop()
        with self.assertRaisesRegex(ValueError, "dimension"):
            module.audit_matrices(self.matrices)

    def test_source_changes_are_rejected_before_parsing(self):
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            module.tables_from_docx(b"not the pinned source")


if __name__ == "__main__":
    unittest.main()
