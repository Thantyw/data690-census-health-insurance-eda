"""
fetch_acs_s2701.py

DATA 690 Census Bureau Capstone
ACS S2701 Data Acquisition Utility

Purpose
-------
Retrieve a complete ACS 5-Year Subject Table S2701 snapshot from the
U.S. Census Bureau API for the five jurisdictions used in this project.

The script:
1. Reads the Census API key from CENSUS_API_KEY.
2. Securely prompts for the key when it is not available.
3. Retrieves the complete S2701 group from the Census API.
4. Keeps only DE, DC, MD, PA, and VA.
5. Validates important fields and geography coverage.
6. Saves a NEW candidate snapshot first.
7. Does NOT overwrite the validated project snapshot by default.
8. Retrieves Census variable metadata for provenance and validation.

Examples
--------
python data_acquisition/fetch_acs_s2701.py --year 2024

python data_acquisition/fetch_acs_s2701.py --year 2019

Later, when a new ACS vintage is available:
python data_acquisition/fetch_acs_s2701.py --year 2025

Security
--------
Never place the Census API key directly in this file.
Never commit the API key to GitHub.
"""

from pathlib import Path
from datetime import datetime, timezone
from getpass import getpass
import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request

import pandas as pd


# ============================================================
# PROJECT CONFIGURATION
# ============================================================

TABLE = "S2701"
DATASET = "acs/acs5/subject"

STATES = {
    "10": "Delaware",
    "11": "District of Columbia",
    "24": "Maryland",
    "42": "Pennsylvania",
    "51": "Virginia",
}

# Important variables used by the current visualization examples.
REQUIRED_VARIABLES = [
    "S2701_C03_001E",  # Percent with health insurance coverage
    "S2701_C05_001E",  # Percent without health insurance coverage
    "S2701_C05_001M",  # 90% MOE: percent without coverage
]


# ============================================================
# REPOSITORY PATHS
# ============================================================

SCRIPT_DIR = Path(__file__).resolve().parent

# data_acquisition/ is directly under the repository root.
ROOT = SCRIPT_DIR.parent

DATA_DIR = ROOT / "data"

DATA_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# COMMAND-LINE ARGUMENTS
# ============================================================

def parse_arguments():
    parser = argparse.ArgumentParser(
        description=(
            "Retrieve a versioned ACS 5-Year S2701 snapshot "
            "from the U.S. Census Bureau API."
        )
    )

    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="ACS release year, for example 2019 or 2024.",
    )

    return parser.parse_args()


# ============================================================
# API KEY
# ============================================================

def get_api_key():
    """
    Retrieve the Census API key securely.

    Priority:
    1. CENSUS_API_KEY environment variable
    2. Secure interactive prompt

    The key is never saved by this script.
    """

    key = os.environ.get("CENSUS_API_KEY", "").strip()

    if key:
        print("Census API key found in CENSUS_API_KEY.")
        return key

    print()
    print("CENSUS_API_KEY was not found in the environment.")
    print("Enter your Census API key below.")
    print("The key will not be displayed or saved.")

    key = getpass(
        "Census API key: "
    ).strip()

    if not key:
        raise RuntimeError(
            "No Census API key was provided."
        )

    return key


# ============================================================
# API REQUEST HELPER
# ============================================================

def request_json(base_url, params):
    """
    Submit a Census API request and return decoded JSON.

    The complete request URL is intentionally not printed because
    it contains the private API key.
    """

    query = urllib.parse.urlencode(
        params,
        safe="(),:*"
    )

    request_url = f"{base_url}?{query}"

    try:
        with urllib.request.urlopen(
            request_url,
            timeout=60
        ) as response:

            raw = response.read()

    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"Census API returned HTTP {exc.code}. "
            "Check the year, dataset, and API key."
        ) from None

    except urllib.error.URLError as exc:
        raise RuntimeError(
            "Unable to connect to the Census API. "
            "Check your internet connection and API key."
        ) from exc

    try:
        return json.loads(raw)

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Census API returned an invalid JSON response."
        ) from exc


# ============================================================
# FETCH S2701 DATA
# ============================================================

def fetch_s2701(year, api_key):
    """
    Retrieve the complete S2701 group for all states.

    The full group is requested rather than only the three
    visualization variables so that the resulting snapshot remains
    compatible with the broader EDA workflow.
    """

    base_url = (
        f"https://api.census.gov/data/"
        f"{year}/{DATASET}"
    )

    params = {
        "get": f"NAME,group({TABLE})",
        "for": "state:*",
        "key": api_key,
    }

    print()
    print("=" * 70)
    print("REQUESTING CENSUS DATA")
    print("=" * 70)
    print(f"ACS release year : {year}")
    print("Product          : ACS 5-Year Subject Tables")
    print(f"Table            : {TABLE}")
    print("Geography        : State")
    print("API key          : [hidden]")
    print()

    body = request_json(
        base_url,
        params,
    )

    if not isinstance(body, list) or len(body) < 2:
        raise RuntimeError(
            "The Census API did not return a usable data table."
        )

    header = body[0]
    rows = body[1:]

    frame = pd.DataFrame(
        rows,
        columns=header,
    )

    return frame, base_url


# ============================================================
# SELECT PROJECT JURISDICTIONS
# ============================================================

def select_project_states(frame):
    """
    Retain the five jurisdictions used by the DATA 690 project.
    """

    if "state" not in frame.columns:
        raise ValueError(
            "The Census API response does not contain a state field."
        )

    selected = frame[
        frame["state"].isin(STATES.keys())
    ].copy()

    selected = selected.sort_values(
        "state"
    ).reset_index(drop=True)

    return selected


# ============================================================
# VALIDATE RESPONSE
# ============================================================

def validate_snapshot(frame, year):
    """
    Validate geography coverage and critical S2701 variables.
    """

    print("=" * 70)
    print("VALIDATING API RESPONSE")
    print("=" * 70)

    expected_states = set(STATES.keys())
    returned_states = set(frame["state"])

    if returned_states != expected_states:

        missing = expected_states - returned_states
        unexpected = returned_states - expected_states

        if missing:
            missing_names = [
                STATES.get(code, code)
                for code in sorted(missing)
            ]

            raise ValueError(
                "Missing expected jurisdictions: "
                + ", ".join(missing_names)
            )

        if unexpected:
            raise ValueError(
                "Unexpected state codes returned: "
                + ", ".join(sorted(unexpected))
            )

    if frame["state"].duplicated().any():
        raise ValueError(
            "Duplicate jurisdiction records were detected."
        )

    for variable in REQUIRED_VARIABLES:
        if variable not in frame.columns:
            raise ValueError(
                f"Required variable is missing: {variable}"
            )

    # Verify geography names.
    for code, expected_name in STATES.items():

        row = frame[
            frame["state"] == code
        ]

        actual_name = row.iloc[0]["NAME"]

        if actual_name != expected_name:
            raise ValueError(
                f"State {code} returned name "
                f"{actual_name!r}; expected {expected_name!r}."
            )

    # Validate numeric fields used by the visualization examples.
    for variable in REQUIRED_VARIABLES:

        numeric_values = pd.to_numeric(
            frame[variable],
            errors="coerce",
        )

        if numeric_values.isna().any():
            raise ValueError(
                f"{variable} contains missing or "
                "non-numeric values."
            )

    insured = pd.to_numeric(
        frame["S2701_C03_001E"],
        errors="coerce",
    )

    uninsured = pd.to_numeric(
        frame["S2701_C05_001E"],
        errors="coerce",
    )

    moe = pd.to_numeric(
        frame["S2701_C05_001M"],
        errors="coerce",
    )

    if not insured.between(0, 100).all():
        raise ValueError(
            "Insured percentages contain values outside 0–100."
        )

    if not uninsured.between(0, 100).all():
        raise ValueError(
            "Uninsured percentages contain values outside 0–100."
        )

    if (moe < 0).any():
        raise ValueError(
            "Negative margins of error were detected."
        )

    # Insured + uninsured should approximately equal 100%.
    composition = insured + uninsured

    if ((composition - 100).abs() > 0.11).any():
        raise ValueError(
            "Insured and uninsured percentages do not "
            "sum to approximately 100%."
        )

    print(f"Year                 : {year}")
    print(f"Jurisdictions        : {len(frame)}")
    print(f"Columns returned     : {len(frame.columns)}")
    print("Required variables   : PASS")
    print("Geography validation : PASS")
    print("Percentage ranges    : PASS")
    print("Composition check    : PASS")
    print()


# ============================================================
# DISPLAY IMPORTANT VALUES
# ============================================================

def display_summary(frame, year):
    """
    Display the values used by the current visualization examples.
    """

    summary = frame[
        [
            "NAME",
            "S2701_C03_001E",
            "S2701_C05_001E",
            "S2701_C05_001M",
        ]
    ].copy()

    summary.columns = [
        "Geography",
        "Insured (%)",
        "Uninsured (%)",
        "Uninsured MOE 90% (pp)",
    ]

    print("=" * 70)
    print(f"ACS S2701 {year} SUMMARY")
    print("=" * 70)

    print(
        summary.to_string(
            index=False
        )
    )

    print()


# ============================================================
# FETCH CENSUS VARIABLE METADATA
# ============================================================

def fetch_variable_metadata(year):
    """
    Retrieve official variable metadata for the ACS Subject dataset.

    This request does not contain the user's API key.
    """

    metadata_url = (
        f"https://api.census.gov/data/"
        f"{year}/{DATASET}/variables.json"
    )

    print("Retrieving Census variable metadata...")

    try:
        with urllib.request.urlopen(
            metadata_url,
            timeout=60
        ) as response:

            raw = response.read()

        metadata = json.loads(raw)

    except Exception as exc:
        raise RuntimeError(
            "Unable to retrieve Census variable metadata."
        ) from exc

    if "variables" not in metadata:
        raise RuntimeError(
            "Census metadata response does not contain variables."
        )

    # Keep only S2701 variables plus NAME.
    selected_variables = {}

    for name, details in metadata["variables"].items():

        if name == "NAME" or name.startswith("S2701_"):
            selected_variables[name] = details

    return {
        "variables": selected_variables
    }


# ============================================================
# COMPARE WITH EXISTING SNAPSHOT
# ============================================================

def compare_existing(frame, existing_file):
    """
    Compare important visualization values against an existing
    validated snapshot.

    The existing file is never modified.
    """

    print("=" * 70)
    print("EXISTING SNAPSHOT COMPARISON")
    print("=" * 70)

    if not existing_file.exists():
        print(
            "No existing snapshot was found for this year."
        )
        print(
            "The candidate file can be reviewed as a new vintage."
        )
        print()

        return

    existing = pd.read_csv(
        existing_file,
        dtype=str,
        keep_default_na=False,
        encoding="utf-8-sig",
    )

    # Existing Census flat downloads may use GEO_ID instead of state.
    if "state" not in existing.columns:

        if "GEO_ID" not in existing.columns:
            print(
                "Existing file does not contain state or GEO_ID. "
                "Automatic comparison cannot be completed."
            )
            print()
            return

        existing = existing[
            existing["GEO_ID"].str.fullmatch(
                r"0400000US\d{2}",
                na=False
            )
        ].copy()

        existing["state"] = (
            existing["GEO_ID"].str[-2:]
        )

    existing = existing[
        existing["state"].isin(STATES.keys())
    ].copy()

    comparison_columns = [
        "state",
        "S2701_C03_001E",
        "S2701_C05_001E",
        "S2701_C05_001M",
    ]

    missing_existing = [
        column
        for column in comparison_columns
        if column not in existing.columns
    ]

    if missing_existing:
        print(
            "Existing snapshot is missing comparison fields:"
        )

        for column in missing_existing:
            print(f"  - {column}")

        print()
        return

    current = frame[
        comparison_columns
    ].copy()

    old = existing[
        comparison_columns
    ].copy()

    current = current.sort_values(
        "state"
    ).reset_index(drop=True)

    old = old.sort_values(
        "state"
    ).reset_index(drop=True)

    matches = True

    print(
        f"{'Geography':24}"
        f"{'Existing':>12}"
        f"{'API':>12}"
        f"{'Match':>10}"
    )

    print("-" * 58)

    for code in STATES:

        old_row = old[
            old["state"] == code
        ]

        new_row = current[
            current["state"] == code
        ]

        if old_row.empty or new_row.empty:
            matches = False
            print(
                f"{STATES[code]:24}"
                f"{'missing':>12}"
                f"{'missing':>12}"
                f"{'NO':>10}"
            )
            continue

        old_value = str(
            old_row.iloc[0]["S2701_C05_001E"]
        ).strip()

        new_value = str(
            new_row.iloc[0]["S2701_C05_001E"]
        ).strip()

        same = old_value == new_value

        if not same:
            matches = False

        print(
            f"{STATES[code]:24}"
            f"{old_value:>12}"
            f"{new_value:>12}"
            f"{'YES' if same else 'NO':>10}"
        )

    print()

    if matches:
        print(
            "Comparison result: PASS — API uninsured estimates "
            "match the existing snapshot."
        )
    else:
        print(
            "Comparison result: REVIEW REQUIRED — one or more "
            "values differ from the existing snapshot."
        )

    print()


# ============================================================
# SAVE CANDIDATE SNAPSHOT
# ============================================================

def save_candidate_snapshot(frame, year):
    """
    Save the API result as a candidate file.

    The validated ACSST5Y{year}.S2701-Data.csv file is deliberately
    NOT overwritten by this acquisition script.
    """

    candidate_file = (
        DATA_DIR
        / f"ACSST5Y{year}.S2701-Data_API_candidate.csv"
    )

    frame.to_csv(
        candidate_file,
        index=False,
    )

    print("Candidate data snapshot saved:")
    print(candidate_file)
    print()

    return candidate_file


# ============================================================
# SAVE CANDIDATE METADATA
# ============================================================

def save_candidate_metadata(
    metadata,
    year,
    api_endpoint,
    candidate_file,
):
    """
    Save provenance and Census variable metadata for the candidate.

    The API key is never included.
    """

    metadata_file = (
        DATA_DIR
        / f"S2701_{year}_metadata_API_candidate.json"
    )

    document = {
        "project": (
            "DATA 690 Census Bureau Sponsored Project"
        ),
        "dataset": (
            "American Community Survey"
        ),
        "product": (
            "ACS 5-Year Subject Tables"
        ),
        "table": TABLE,
        "table_title": (
            "Selected Characteristics of "
            "Health Insurance Coverage "
            "in the United States"
        ),
        "vintage": year,
        "reference_period": (
            f"{year - 4}\u2013{year}"
        ),
        "retrieval_method": (
            "U.S. Census Bureau Data API"
        ),
        "api_endpoint": api_endpoint,
        "api_key_included": False,
        "retrieved_utc": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),
        "geography": "state",
        "jurisdictions": list(
            STATES.values()
        ),
        "candidate_data_file": (
            candidate_file.name
        ),
        "status": (
            "candidate_snapshot_pending_validation"
        ),
        "notes": (
            "This candidate snapshot was retrieved from the "
            "U.S. Census Bureau API. It does not automatically "
            "replace the validated project snapshot. The candidate "
            "should be compared and validated before promotion."
        ),
        "census_variable_metadata": metadata[
            "variables"
        ],
    }

    with open(
        metadata_file,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            document,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print("Candidate metadata saved:")
    print(metadata_file)
    print()

    return metadata_file


# ============================================================
# MAIN
# ============================================================

def main():

    args = parse_arguments()

    year = args.year

    existing_file = (
        DATA_DIR
        / f"ACSST5Y{year}.S2701-Data.csv"
    )

    print()
    print("=" * 70)
    print("ACS S2701 DATA ACQUISITION")
    print("=" * 70)
    print(f"Repository root : {ROOT}")
    print(f"Data directory  : {DATA_DIR}")
    print(f"Requested year  : {year}")
    print()

    api_key = get_api_key()

    raw_frame, api_endpoint = fetch_s2701(
        year,
        api_key,
    )

    frame = select_project_states(
        raw_frame
    )

    validate_snapshot(
        frame,
        year,
    )

    display_summary(
        frame,
        year,
    )

    compare_existing(
        frame,
        existing_file,
    )

    candidate_file = save_candidate_snapshot(
        frame,
        year,
    )

    variable_metadata = fetch_variable_metadata(
        year
    )

    metadata_file = save_candidate_metadata(
        variable_metadata,
        year,
        api_endpoint,
        candidate_file,
    )

    print("=" * 70)
    print("DATA ACQUISITION COMPLETED")
    print("=" * 70)
    print()
    print("IMPORTANT:")
    print(
        "The existing validated snapshot was NOT overwritten."
    )
    print()
    print("Review these candidate files:")
    print(f"  Data     : {candidate_file}")
    print(f"  Metadata : {metadata_file}")
    print()
    print(
        "After validation, a candidate may be intentionally "
        "promoted to the project's versioned data snapshot."
    )


if __name__ == "__main__":
    main()
