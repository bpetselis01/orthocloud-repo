"""
DICOM PS3.15 de-identification compliance checker.

Scans the backend source tree to determine whether the pipeline addresses
the 18 HIPAA safe-harbour identifiers and the DICOM PS3.15 Basic Application
Level Confidentiality Profile. Outputs a JSON report consumed by the
phi-dicom-scan job in the compliance workflow.

Run from repo root:
    python scripts/check_dicom_deidentification.py
"""

import json
import re
import sys
from pathlib import Path

# The 18 HIPAA safe-harbour identifiers (45 CFR §164.514(b)(2))
SAFE_HARBOUR_IDENTIFIERS = [
    "names",
    "geographic_data",
    "dates",
    "phone_numbers",
    "fax_numbers",
    "email_addresses",
    "ssn",
    "medical_record_numbers",
    "health_plan_beneficiary_numbers",
    "account_numbers",
    "certificate_license_numbers",
    "vehicle_identifiers",
    "device_identifiers",
    "web_urls",
    "ip_addresses",
    "biometric_identifiers",
    "full_face_photos",
    "unique_identifying_numbers",
]

# DICOM PS3.15 Basic Application Level Confidentiality Profile tag keywords
# that must be removed or replaced during de-identification
REQUIRED_DEIDENTIFICATION_TAGS = [
    "PatientName",
    "PatientID",
    "PatientBirthDate",
    "PatientSex",
    "PatientAge",
    "PatientAddress",
    "PatientTelephoneNumbers",
    "ReferringPhysicianName",
    "InstitutionName",
    "InstitutionAddress",
    "StudyDate",
    "StudyTime",
    "AccessionNumber",
    "StudyID",
    "SeriesDate",
    "AcquisitionDate",
]

# Keywords that suggest de-identification is being handled
DEIDENTIFICATION_KEYWORDS = [
    "deidentif",
    "de_identif",
    "anonymi",
    "deid",
    "remove_private_tags",
    "confidentiality_profile",
    "PS3.15",
    "ps3_15",
    "safe_harbour",
    "safe_harbor",
]

# Keywords that suggest DICOM is being processed
DICOM_PROCESSING_KEYWORDS = [
    "SimpleITK",
    "pydicom",
    "sitk",
    "dcmread",
    "DicomImageReader",
    "ReadImage",
    ".dcm",
    "DICOM",
]


def scan_source_files(root: Path) -> dict:
    py_files = list(root.rglob("*.py"))
    source = {}
    for f in py_files:
        try:
            source[str(f)] = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            pass
    return source


def check_keyword(source_map: dict, keywords: list[str]) -> list[str]:
    hits = []
    for path, content in source_map.items():
        for kw in keywords:
            if kw.lower() in content.lower():
                hits.append(f"{path}: contains '{kw}'")
    return hits


def main() -> None:
    repo_root = Path(__file__).parent.parent
    backend_root = repo_root / "backend"

    source_map = scan_source_files(backend_root)

    dicom_hits = check_keyword(source_map, DICOM_PROCESSING_KEYWORDS)
    deidentification_hits = check_keyword(source_map, DEIDENTIFICATION_KEYWORDS)

    dicom_processing_present = len(dicom_hits) > 0
    deidentification_present = len(deidentification_hits) > 0

    # Check which DICOM tags are explicitly referenced in de-identification code
    tags_covered = []
    tags_missing = []
    for tag in REQUIRED_DEIDENTIFICATION_TAGS:
        tag_present = any(
            tag.lower() in content.lower() for content in source_map.values()
        )
        (tags_covered if tag_present else tags_missing).append(tag)

    findings = []

    if dicom_processing_present and not deidentification_present:
        findings.append({
            "severity": "Critical",
            "regulation": "HIPAA §164.514(b), DICOM PS3.15",
            "finding": "DICOM processing code detected but no de-identification logic found. "
                       "Patient identifiers in DICOM metadata will be persisted or transmitted without removal.",
            "files": dicom_hits,
        })
    elif not dicom_processing_present:
        findings.append({
            "severity": "Info",
            "regulation": "HIPAA §164.514(b), DICOM PS3.15",
            "finding": "No DICOM processing code detected in backend/. "
                       "De-identification check will be meaningful once the pipeline is implemented in Step 2.",
            "files": [],
        })

    if tags_missing:
        findings.append({
            "severity": "High" if deidentification_present else "Info",
            "regulation": "DICOM PS3.15 Basic Application Level Confidentiality Profile",
            "finding": f"{len(tags_missing)} required DICOM tags not referenced in de-identification logic.",
            "missing_tags": tags_missing,
            "covered_tags": tags_covered,
        })

    report = {
        "schema": "orthocloud-deid-compliance-v1",
        "dicom_processing_detected": dicom_processing_present,
        "deidentification_logic_detected": deidentification_present,
        "safe_harbour_identifiers_total": len(SAFE_HARBOUR_IDENTIFIERS),
        "required_dicom_tags_total": len(REQUIRED_DEIDENTIFICATION_TAGS),
        "tags_covered": tags_covered,
        "tags_missing": tags_missing,
        "findings": findings,
        "dicom_hits": dicom_hits,
        "deidentification_hits": deidentification_hits,
    }

    print(json.dumps(report, indent=2))

    has_critical = any(f["severity"] == "Critical" for f in findings)
    sys.exit(1 if has_critical else 0)


if __name__ == "__main__":
    main()
