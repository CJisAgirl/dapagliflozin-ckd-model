"""Extract a pinned CMS 2026 dapagliflozin price; no economic model is run."""
import argparse
import csv
from datetime import date, datetime
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

URL = "https://www.cms.gov/files/zip/selected-drug-list-negotiated-prices-also-known-maximum-fair-prices-statutezip.zip"
ARCHIVE_SHA256 = "6fa6b047bd20b0dc3dc8c8aa554a2c133aa95511efaa021dc7a669ea109d0ed1"
CSV_NAME = "CMS_Negotiation_Program_Selected_Drug_List_and_Maximum_Fair_Price_Data_File_20260921.csv"
LABEL_URL = "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=72ad22ae-efe6-4cd6-a302-98aaee423d69"
NDC11 = "00310-6210-30"
REFERENCE = Path(__file__).resolve().parents[1] / "parameters" / "cms-price-evidence.json"


def read_rows(raw):
    if hashlib.sha256(raw).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("CMS archive has changed. Review and repin the source explicitly.")
    with ZipFile(io.BytesIO(raw)) as archive:
        csv_bytes = archive.read(CSV_NAME)
    rows = list(csv.DictReader(io.StringIO(csv_bytes.decode("utf-8-sig"))))
    return rows, hashlib.sha256(csv_bytes).hexdigest()


def select_price(rows, on_date):
    def parse(value):
        return datetime.strptime(value, "%m/%d/%Y").date()

    matches = []
    for row in rows:
        if row["Selected Drug Name"].strip().upper() != "FARXIGA" or row["NDC-11"].strip() != NDC11:
            continue
        start = parse(row["MFP Effective Date"])
        end = parse(row["MFP End Date"]) if row["MFP End Date"].strip() else date.max
        if start <= on_date <= end:
            matches.append(row)
    if len(matches) != 1:
        raise ValueError(f"Expected one effective product row, found {len(matches)}")
    row = matches[0]
    if row["Active Ingredient Name or Active Moiety Name"].strip().upper() != "DAPAGLIFLOZIN":
        raise ValueError("Ingredient mismatch")
    if row["NDC-9"].strip() != "00310-6210":
        raise ValueError("NDC-9 mismatch")
    if Decimal(row["NDC-9 MFP per Unit Price"]) <= 0:
        raise ValueError("Nonpositive price")
    return row


def extract(raw):
    rows, csv_sha = read_rows(raw)
    row = select_price(rows, date(2026, 10, 11))
    unit = Decimal(row["NDC-9 MFP per Unit Price"])
    return {
        "status": "verified_price_component_only_not_CEA_or_BIA_results",
        "verified_on": "2026-10-11",
        "source_url": URL,
        "archive_sha256": ARCHIVE_SHA256,
        "csv_name": CSV_NAME,
        "csv_sha256": csv_sha,
        "selection_date": "2026-10-11",
        "selected_raw_row": row,
        "dose_mapping": {
            "source_url": LABEL_URL,
            "label_updated": "2026-06-03",
            "location": "Table 18; 10 mg tablets, bottles of 30",
            "label_ndc": "0310-6210-30",
            "cms_ndc11": NDC11,
            "ndc9": "00310-6210",
            "tablets_per_day": 1,
            "dose_mg_per_day": 10,
            "mapping_method": "Manual label verification; five-digit CMS labeler padding",
        },
        "arithmetic_scenarios_usd": {
            "per_tablet": str(unit),
            "30_tablets": str(unit * 30),
            "365_tablets": str(unit * 365),
            "reported_single_mfp_per_30_des": row["Single MFP per 30 DES"],
        },
        "assumptions": [
            "One 10 mg tablet daily; 365-day arithmetic assumes no interruption.",
            "MFP-based drug component, not actual net plan payment or patient out-of-pocket.",
            "Fees, rebates, payment allocation and non-drug care are not included.",
            "The 30-day-equivalent field is distinct from 30 tablets at the NDC unit price.",
            "Effective dates select the price year; IPAY alone does not.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, help="Existing original CMS archive; otherwise download.")
    parser.add_argument("--check", action="store_true", help="Compare with the committed reference without writing.")
    args = parser.parse_args()
    if args.archive:
        raw = args.archive.read_bytes()
    else:
        with urlopen(URL, timeout=60) as response:
            raw = response.read()
    result = extract(raw)
    if args.check:
        if result != json.loads(REFERENCE.read_text()):
            raise ValueError("Extracted evidence differs from the reference.")
        print("PASS: source hash, product, effective dates and price arithmetic match the reference.")
    else:
        REFERENCE.parent.mkdir(parents=True, exist_ok=True)
        REFERENCE.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
        print(f"Saved {REFERENCE.name}; this is price evidence, not an economic result.")


if __name__ == "__main__":
    main()
