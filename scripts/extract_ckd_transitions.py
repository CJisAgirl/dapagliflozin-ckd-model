"""Extract and audit published renal transition inputs, without running a CEA."""
import argparse
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
import re
from urllib.request import urlopen
from zipfile import ZipFile
import xml.etree.ElementTree as ET

SOURCE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC10883141/supplementaryFiles"
PAPER_URL = "https://doi.org/10.1093/ckj/sfae025"
SOURCE_FILE = "sfae025_supplemental_file.docx"
SOURCE_SHA256 = "478a4040e00181c06ec9058c441bbfcbeb8ee3a2e212cfb4c14cbe1520eaa6ac"
STATES = ["CKD 1", "CKD 2", "CKD 3a", "CKD 3b", "CKD 4", "CKD 5", "Dialysis", "Kidney transplant"]
PHASES = ["Months 0-4", "Months 5 and onwards"]
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
ROOT = Path(__file__).resolve().parents[1]
PAIR = re.compile(r"^(\d+\.\d{3})\s*\((\d+\.\d{3})\)$")


def text(node):
    return "".join(n.text or "" for n in node.findall(".//w:t", NS)).strip()


def tables_from_docx(raw):
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("Supplement fingerprint changed; review the source before repinning.")
    with ZipFile(io.BytesIO(raw)) as doc:
        root = ET.fromstring(doc.read("word/document.xml"))
    tables = {}
    caption = None
    for node in root.find("w:body", NS):
        if node.tag.endswith("}p") and re.match(r"Table S\d+\.", text(node)):
            caption = text(node).split(".", 1)[0]
        elif node.tag.endswith("}tbl") and caption:
            if caption in tables:
                raise ValueError(f"Duplicate source table {caption}")
            tables[caption] = [[text(c) for c in r.findall("w:tc", NS)]
                               for r in node.findall("w:tr", NS)]
            caption = None
    return tables


def extract_matrices(tables):
    matrices = []
    for table_id, arm in [("Table S3", "dapagliflozin_plus_standard_care"),
                          ("Table S4", "placebo_plus_standard_care")]:
        table = tables[table_id]
        if table[1][1:9] != STATES:
            raise ValueError("Unexpected destination-state order")
        phase = None
        current = None
        for cells in table[2:]:
            if len(cells) == 1 and cells[0] in PHASES:
                phase = cells[0]
                current = {"table": table_id, "arm": arm, "phase_as_printed": phase,
                           "from_states": [], "to_states": list(STATES),
                           "mean": [], "se": []}
                matrices.append(current)
            elif len(cells) == 11 and cells[1] in STATES:
                if phase is None:
                    raise ValueError("State row precedes phase label")
                pairs = [PAIR.fullmatch(c) for c in cells[2:10]]
                if any(p is None for p in pairs):
                    raise ValueError("Unrecognized probability/SE cell; no default zeros allowed")
                current["from_states"].append(cells[1])
                current["mean"].append([p.group(1) for p in pairs])
                current["se"].append([p.group(2) for p in pairs])
    audit_matrices(matrices)
    return matrices


def audit_matrices(matrices):
    expected = {(t, p) for t in ["Table S3", "Table S4"] for p in PHASES}
    keys = [(m["table"], m["phase_as_printed"]) for m in matrices]
    if set(keys) != expected or len(keys) != len(expected):
        raise ValueError("Missing or duplicate treatment/phase matrix")
    row_checks = []
    # Eight cells rounded to 0.001 can have a total rounding error up to 0.004.
    tolerance = Decimal("0.004")
    for m in matrices:
        if m["from_states"] != STATES or m["to_states"] != STATES:
            raise ValueError("Missing, duplicated or reordered state")
        if len(m["mean"]) != 8 or len(m["se"]) != 8:
            raise ValueError("Unexpected matrix dimension")
        for state, means, errors in zip(STATES, m["mean"], m["se"]):
            if len(means) != 8 or len(errors) != 8:
                raise ValueError("Unexpected row dimension")
            probs, ses = list(map(Decimal, means)), list(map(Decimal, errors))
            if any(not p.is_finite() or not 0 <= p <= 1 for p in probs):
                raise ValueError("Invalid probability")
            if any(not se.is_finite() or se < 0 for se in ses):
                raise ValueError("Invalid standard error")
            total = sum(probs)
            deviation = total - 1
            if abs(deviation) > tolerance:
                raise ValueError("Row sum outside the printed-precision rounding bound")
            row_checks.append({"table": m["table"], "phase": m["phase_as_printed"],
                               "from_state": state, "sum_as_printed": str(total),
                               "deviation_from_one": str(deviation)})
    return {
        "status": "source_transcription_checked_not_clinical_model_validation",
        "matrices": len(matrices), "probability_cells": 256, "se_cells": 256,
        "rows": len(row_checks),
        "nonunit_rows_as_printed": sum(Decimal(r["deviation_from_one"]) != 0 for r in row_checks),
        "max_absolute_row_sum_deviation": str(max(abs(Decimal(r["deviation_from_one"])) for r in row_checks)),
        "rounding_bound": str(tolerance),
        "normalization_applied": False,
        "row_checks": row_checks,
    }


def extract(raw):
    matrices = extract_matrices(tables_from_docx(raw))
    evidence = {
        "use_status": "source_reference_only_not_approved_for_target_CEA",
        "citation": "McEwan et al. Clinical Kidney Journal 2024;17(2):sfae025. Supplement Tables S3 and S4.",
        "article_url": PAPER_URL, "download_url": SOURCE_URL,
        "source_filename": SOURCE_FILE, "source_sha256": SOURCE_SHA256,
        "license": "CC BY 4.0", "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "transformation": "Extracted table cells; means and SE retained as printed decimal strings; no normalization.",
        "verified_on": "2026-10-11",
        "unit": "monthly transition probability", "albuminuria": "elevated UACR",
        "diabetes_specificity": "Tables are not separately labeled as T2D-only; applicability remains unresolved.",
        "mortality_included": False,
        "limitations": [
            "The source models death separately; these matrices alone cannot estimate survival or QALYs.",
            "G1 must be retained as a possible destination even if baseline G1 occupancy is zero.",
            "Printed phase labels are retained; first-four-month cycle boundaries require an explicit implementation convention.",
            "Rounded row sums are not always one; an explicit correction and sensitivity check are required before propagation.",
            "Rounded zero probabilities or SEs are not proof of impossible events or zero uncertainty.",
            "Stage transitions are not adjudicated trial composite-endpoint risks.",
            "No US cost, utility, mortality or target-cohort calibration is provided by this extraction.",
        ],
        "matrices": matrices,
    }
    return evidence, audit_matrices(matrices)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--supplement", type=Path, help="Original supplemental DOCX, otherwise downloaded from Europe PMC.")
    parser.add_argument("--check", action="store_true", help="Check committed evidence and audit without writing.")
    args = parser.parse_args()
    if args.supplement:
        raw = args.supplement.read_bytes()
    else:
        with urlopen(SOURCE_URL, timeout=45) as response:
            archive = response.read()
        with ZipFile(io.BytesIO(archive)) as z:
            raw = z.read(SOURCE_FILE)
    evidence, audit = extract(raw)
    paths = [(ROOT / "parameters" / "ckd-transitions-source.json", evidence),
             (ROOT / "results" / "transition-input-audit.json", audit)]
    for path, value in paths:
        if args.check:
            if json.loads(path.read_text()) != value:
                raise ValueError(f"Reference mismatch: {path.name}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    print(f"PASS: 4 matrices, 256 mean/SE pairs; {audit['nonunit_rows_as_printed']} rows retain printed rounding differences. No clinical simulation run.")


if __name__ == "__main__":
    main()
