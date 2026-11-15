"""
fetch_acs_s2701.py

DATA 690 – Census Bureau Sponsored Capstone
ACS S2701 Data Acquisition and Schema Validation Utility

Purpose
-------
Retrieve ACS 5-Year Subject Table S2701 data from the
U.S. Census Bureau API and transform the API response into
the exact project schema used by the validated S2701 snapshots.

The utility:

1. Reads the Census API key from CENSUS_API_KEY or securely
   prompts for the key.
2. Retrieves the complete ACS S2701 subject-table group.
3. Retains the five project jurisdictions:
      Delaware
      District of Columbia
      Maryland
      Pennsylvania
      Virginia
4. Constructs project-specific geography/provenance fields:
      NAME
      GEO_ID
      NAME.1
      state
      source_file
5. Matches the exact column names and column order of the
   existing validated project snapshot.
6. Normalizes Census API null values to the blank representation
   used by the validated project snapshot.
7. Validates important analytical fields.
8. Compares the candidate against the existing validated snapshot.
9. Saves the result as an API candidate.
10. Never overwrites the validated project snapshot automatically.

Example
-------
python data_acquisition/fetch_acs_s2701.py --year 2024

Security
--------
Never place a real Census API key directly in this file.
Never commit a Census API key to GitHub.
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

# Key analytical variables used by the current visualization
# examples.
REQUIRED_VARIABLES = [
    "S2701_C03_001E",  # Percent with health insurance coverage
    "S2701_C05_001E",  # Percent without health insurance coverage
    "S2701_C05_001M",  # 90% MOE: percent without coverage
]

PROJECT_PREFIX_COLUMNS = [
    "NAME",
    "GEO_ID",
    "NAME.1",
]

PROJECT_SUFFIX_COLUMNS = [
    "state",
    "source_file",
]


# ============================================================
# REPOSITORY PATHS
# ============================================================

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
DATA_DIR = ROOT / "data"

DATA_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# COMMAND-LINE ARGUMENTS
# ============================================================

def parse_arguments():
    """
    Parse command-line arguments.
    """

    parser = argparse.ArgumentParser(
        description=(
            "Retrieve ACS S2701 data from the Census API and "
            "validate it against the project's existing schema."
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
    2. Interactive hidden prompt

    The key is never printed or saved.
    """

    key = os.environ.get(
        "CENSUS_API_KEY",
        "",
    ).strip()

    if key:
        print("CENSUS_API_KEY found in environment.")
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
# HTTP / JSON HELPER
# ============================================================

def request_json(base_url, params=None):
    """
    Retrieve JSON from a Census endpoint.

    The complete request URL is intentionally not printed because
    data requests may contain the user's Census API key.
    """

    if params:
        query = urllib.parse.urlencode(
            params,
            safe="(),:*",
        )

        request_url = f"{base_url}?{query}"

    else:
        request_url = base_url

    try:
        with urllib.request.urlopen(
            request_url,
            timeout=120,
        ) as response:
            raw = response.read()

    except urllib.error.HTTPError as exc:
        try:
            error_body = exc.read().decode(
                "utf-8",
                errors="replace",
            )
        except Exception:
            error_body = ""

        message = (
            f"Census API returned HTTP {exc.code}."
        )

        if error_body:
            message += (
                f"\nCensus response: {error_body[:500]}"
            )

        raise RuntimeError(message) from None

    except urllib.error.URLError as exc:
        raise RuntimeError(
            "Unable to connect to the Census API."
        ) from exc

    try:
        return json.loads(raw)

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Census API returned invalid JSON."
        ) from exc


# ============================================================
# FETCH COMPLETE S2701 GROUP
# ============================================================

def fetch_s2701(year, api_key):
    """
    Retrieve the complete S2701 group for all states.

    group(S2701) already contains NAME. Therefore NAME is not
    requested separately. This prevents duplicate NAME columns.
    """

    base_url = (
        f"https://api.census.gov/data/"
        f"{year}/{DATASET}"
    )

    params = {
        "get": f"group({TABLE})",
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

    if (
        not isinstance(body, list)
        or len(body) < 2
    ):
        raise RuntimeError(
            "Census API did not return a usable table."
        )

    header = body[0]
    rows = body[1:]

    # Detect duplicate API fields before constructing DataFrame.
    duplicate_columns = sorted(
        {
            column
            for column in header
            if header.count(column) > 1
        }
    )

    if duplicate_columns:
        raise RuntimeError(
            "Census API returned duplicate columns: "
            + ", ".join(duplicate_columns)
        )

    frame = pd.DataFrame(
        rows,
        columns=header,
    )

    print(f"Raw API rows      : {len(frame)}")
    print(f"Raw API columns   : {len(frame.columns)}")
    print()

    return frame, base_url


# ============================================================
# SELECT PROJECT JURISDICTIONS
# ============================================================

def select_project_states(frame):
    """
    Keep only the five jurisdictions used by the project.
    """

    if "state" not in frame.columns:
        raise ValueError(
            "Census API response does not contain "
            "the state geography field."
        )

    # Standardize state codes before filtering.
    frame = frame.copy()

    frame["state"] = (
        frame["state"]
        .astype(str)
        .str.zfill(2)
    )

    selected = frame[
        frame["state"].isin(
            STATES.keys()
        )
    ].copy()

    selected = (
        selected
        .sort_values("state")
        .reset_index(drop=True)
    )

    expected_states = set(
        STATES.keys()
    )

    actual_states = set(
        selected["state"]
    )

    if actual_states != expected_states:
        missing = (
            expected_states
            - actual_states
        )

        unexpected = (
            actual_states
            - expected_states
        )

        if missing:
            raise ValueError(
                "Missing project jurisdictions: "
                + ", ".join(
                    STATES.get(code, code)
                    for code in sorted(missing)
                )
            )

        if unexpected:
            raise ValueError(
                "Unexpected jurisdictions: "
                + ", ".join(
                    sorted(unexpected)
                )
            )

    if selected["state"].duplicated().any():
        raise ValueError(
            "Duplicate state records detected."
        )

    return selected


# ============================================================
# LOAD EXISTING VALIDATED SNAPSHOT
# ============================================================

def load_reference_snapshot(year):
    """
    Load the existing validated project snapshot.

    This file acts as the schema contract for the API candidate.
    """

    reference_file = (
        DATA_DIR
        / f"ACSST5Y{year}.S2701-Data.csv"
    )

    if not reference_file.exists():
        raise FileNotFoundError(
            "\nThe existing validated snapshot was not found:\n"
            f"{reference_file}\n\n"
            "The acquisition utility requires an existing "
            "validated snapshot because that file is used as "
            "the schema contract."
        )

    reference = pd.read_csv(
        reference_file,
        dtype=str,
        keep_default_na=False,
        encoding="utf-8-sig",
    )

    print("=" * 70)
    print("REFERENCE SNAPSHOT")
    print("=" * 70)
    print(f"File             : {reference_file.name}")
    print(f"Rows             : {len(reference)}")
    print(f"Columns          : {len(reference.columns)}")
    print()

    return reference, reference_file


# ============================================================
# VALIDATE REFERENCE SCHEMA
# ============================================================

def validate_reference_schema(reference):
    """
    Confirm that the validated snapshot contains the structural
    fields required by the acquisition workflow.
    """

    required_project_fields = (
        PROJECT_PREFIX_COLUMNS
        + REQUIRED_VARIABLES
        + PROJECT_SUFFIX_COLUMNS
    )

    missing = [
        column
        for column in required_project_fields
        if column not in reference.columns
    ]

    if missing:
        raise ValueError(
            "Reference snapshot is missing required fields:\n"
            + "\n".join(
                f"  - {column}"
                for column in missing
            )
        )

    if reference.columns.duplicated().any():
        duplicates = (
            reference.columns[
                reference.columns.duplicated()
            ]
            .tolist()
        )

        raise ValueError(
            "Reference snapshot contains duplicate "
            "column labels: "
            + ", ".join(duplicates)
        )

    print("Reference schema validation: PASS")
    print()


# ============================================================
# CONSTRUCT EXACT PROJECT SCHEMA
# ============================================================

def construct_project_schema(
    api_frame,
    reference,
    year,
):
    """
    Transform the raw Census API response into the exact schema
    used by the existing validated project snapshot.

    NAME.1 is created explicitly. It is not created by allowing
    pandas to silently rename a duplicate NAME field.

    Census API null values are converted to blank strings so that
    annotation fields use the same representation as the existing
    validated CSV.
    """

    frame = api_frame.copy()

    if "NAME" not in frame.columns:
        raise ValueError(
            "API response does not contain NAME."
        )

    if "state" not in frame.columns:
        raise ValueError(
            "API response does not contain state."
        )

    # --------------------------------------------------------
    # Standardize state codes
    # --------------------------------------------------------

    frame["state"] = (
        frame["state"]
        .astype(str)
        .str.zfill(2)
    )

    # --------------------------------------------------------
    # Construct project geography fields
    # --------------------------------------------------------

    frame["GEO_ID"] = (
        "0400000US"
        + frame["state"]
    )

    frame["NAME.1"] = (
        frame["NAME"]
        .astype(str)
    )

    # --------------------------------------------------------
    # Construct provenance field
    # --------------------------------------------------------

    frame["source_file"] = (
        f"Census API {year} ACS five-year subject S2701"
    )

    # --------------------------------------------------------
    # Use validated reference as exact schema contract
    # --------------------------------------------------------

    reference_columns = (
        reference.columns.tolist()
    )

    api_columns = set(
        frame.columns
    )

    missing_columns = [
        column
        for column in reference_columns
        if column not in api_columns
    ]

    if missing_columns:
        print()
        print("=" * 70)
        print("SCHEMA CONSTRUCTION FAILED")
        print("=" * 70)

        print(
            "The Census API response cannot currently "
            "construct every reference column."
        )

        print()
        print(
            f"Missing columns: {len(missing_columns)}"
        )

        for column in missing_columns[:50]:
            print(f"  - {column}")

        if len(missing_columns) > 50:
            print(
                f"  ... and "
                f"{len(missing_columns) - 50} more"
            )

        raise ValueError(
            "API candidate cannot reproduce the exact "
            "reference schema."
        )

    # --------------------------------------------------------
    # Exact reference column order
    # --------------------------------------------------------

    candidate = frame[
        reference_columns
    ].copy()

    # --------------------------------------------------------
    # Normalize API null values
    # --------------------------------------------------------
    #
    # Census API JSON can return null for annotation fields.
    # The validated CSV represents these values as blank cells.
    # Converting null/None/NaN to "" makes the API candidate
    # structurally and representationally compatible with the
    # existing project snapshot.
    # --------------------------------------------------------

    candidate = candidate.fillna("")

    return candidate


# ============================================================
# EXACT SCHEMA VALIDATION
# ============================================================

def validate_exact_schema(
    candidate,
    reference,
):
    """
    Require the candidate to have exactly the same row count,
    column count, column names, and column order as the validated
    reference snapshot.
    """

    print("=" * 70)
    print("EXACT SCHEMA VALIDATION")
    print("=" * 70)

    candidate_columns = (
        candidate.columns.tolist()
    )

    reference_columns = (
        reference.columns.tolist()
    )

    print(
        f"Reference rows     : {len(reference)}"
    )

    print(
        f"Candidate rows     : {len(candidate)}"
    )

    print(
        f"Reference columns  : {len(reference_columns)}"
    )

    print(
        f"Candidate columns  : {len(candidate_columns)}"
    )

    # --------------------------------------------------------
    # Row count
    # --------------------------------------------------------

    if len(candidate) != len(reference):
        raise ValueError(
            "Candidate row count does not match "
            "reference row count."
        )

    # --------------------------------------------------------
    # Column count
    # --------------------------------------------------------

    if len(candidate_columns) != len(
        reference_columns
    ):
        raise ValueError(
            "Candidate column count does not match "
            "reference column count."
        )

    # --------------------------------------------------------
    # Column names and order
    # --------------------------------------------------------

    if candidate_columns != reference_columns:
        differences = []

        for index, (
            reference_column,
            candidate_column,
        ) in enumerate(
            zip(
                reference_columns,
                candidate_columns,
            ),
            start=1,
        ):
            if (
                reference_column
                != candidate_column
            ):
                differences.append(
                    (
                        index,
                        reference_column,
                        candidate_column,
                    )
                )

        print()
        print("Column-order differences:")

        for (
            index,
            expected,
            actual,
        ) in differences[:25]:
            print(
                f"{index:4}: "
                f"expected={expected!r}, "
                f"actual={actual!r}"
            )

        raise ValueError(
            "Candidate columns do not exactly match "
            "the reference schema."
        )

    print("Row count          : PASS")
    print("Column count       : PASS")
    print("Column names       : PASS")
    print("Column order       : PASS")
    print("Exact schema       : PASS")
    print()


# ============================================================
# ANALYTICAL VALIDATION
# ============================================================

def validate_analytical_fields(
    candidate,
    year,
):
    """
    Validate the analytical fields used by the current
    visualization examples.
    """

    print("=" * 70)
    print("ANALYTICAL VALIDATION")
    print("=" * 70)

    # --------------------------------------------------------
    # Geography validation
    # --------------------------------------------------------

    for (
        state_code,
        expected_name,
    ) in STATES.items():

        rows = candidate.loc[
            candidate["state"]
            == state_code
        ]

        if len(rows) != 1:
            raise ValueError(
                f"Expected exactly one row for "
                f"{expected_name}; found {len(rows)}."
            )

        actual_name = str(
            rows["NAME"].iloc[0]
        ).strip()

        if actual_name != expected_name:
            raise ValueError(
                f"State {state_code}: "
                f"expected {expected_name!r}, "
                f"received {actual_name!r}."
            )

        actual_name_1 = str(
            rows["NAME.1"].iloc[0]
        ).strip()

        if actual_name_1 != expected_name:
            raise ValueError(
                f"NAME.1 mismatch for {expected_name}."
            )

        expected_geo_id = (
            f"0400000US{state_code}"
        )

        actual_geo_id = str(
            rows["GEO_ID"].iloc[0]
        ).strip()

        if actual_geo_id != expected_geo_id:
            raise ValueError(
                f"GEO_ID mismatch for {expected_name}: "
                f"{actual_geo_id!r}"
            )

    # --------------------------------------------------------
    # Required analytical fields
    # --------------------------------------------------------

    numeric = {}

    for variable in REQUIRED_VARIABLES:

        if variable not in candidate.columns:
            raise ValueError(
                f"Missing required variable: {variable}"
            )

        values = pd.to_numeric(
            candidate[variable],
            errors="coerce",
        )

        if values.isna().any():
            raise ValueError(
                f"{variable} contains missing or "
                "non-numeric values."
            )

        numeric[variable] = values

    insured = numeric[
        "S2701_C03_001E"
    ]

    uninsured = numeric[
        "S2701_C05_001E"
    ]

    uninsured_moe = numeric[
        "S2701_C05_001M"
    ]

    # --------------------------------------------------------
    # Percentage validation
    # --------------------------------------------------------

    if not insured.between(
        0,
        100,
    ).all():
        raise ValueError(
            "Insured percentages fall outside 0–100."
        )

    if not uninsured.between(
        0,
        100,
    ).all():
        raise ValueError(
            "Uninsured percentages fall outside 0–100."
        )

    # --------------------------------------------------------
    # MOE validation
    # --------------------------------------------------------

    if (
        uninsured_moe < 0
    ).any():
        raise ValueError(
            "Negative uninsured MOE detected."
        )

    # --------------------------------------------------------
    # Composition validation
    # --------------------------------------------------------

    composition = (
        insured
        + uninsured
    )

    if (
        (composition - 100)
        .abs()
        .gt(0.11)
        .any()
    ):
        raise ValueError(
            "Insured + uninsured does not sum "
            "to approximately 100%."
        )

    print(f"Year               : {year}")
    print("Geographies        : PASS")
    print("GEO_ID             : PASS")
    print("NAME / NAME.1      : PASS")
    print("Required variables : PASS")
    print("Percentage ranges  : PASS")
    print("MOE validation     : PASS")
    print("Composition        : PASS")
    print()


# ============================================================
# DISPLAY KEY VALUES
# ============================================================

def display_summary(
    candidate,
    year,
):
    """
    Display the principal values used by the current project
    visualization examples.
    """

    summary = candidate[
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
    print(
        f"ACS S2701 {year} PROJECT VALUES"
    )
    print("=" * 70)

    print(
        summary.to_string(
            index=False
        )
    )

    print()


# ============================================================
# NORMALIZE VALUES FOR COMPARISON
# ============================================================

def normalize_value(value):
    """
    Normalize values before comparison.

    Rules
    -----
    - Actual Python None values are treated as blank.
    - pandas NA/NaN values are treated as blank.
    - Empty strings remain blank.
    - Text representations of null values are treated as blank.
    - Numeric strings such as 6.30 and 6.3 are treated as equal.
    - Non-numeric text is preserved.
    """

    # --------------------------------------------------------
    # Actual Python None
    # --------------------------------------------------------

    if value is None:
        return ""

    # --------------------------------------------------------
    # pandas missing values
    # --------------------------------------------------------

    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass

    # --------------------------------------------------------
    # Convert to normalized text
    # --------------------------------------------------------

    text = str(
        value
    ).strip()

    # --------------------------------------------------------
    # Normalize textual missing-value representations
    # --------------------------------------------------------

    if text.lower() in {
        "",
        "none",
        "nan",
        "null",
        "<na>",
    }:
        return ""

    # --------------------------------------------------------
    # Normalize equivalent numeric representations
    # --------------------------------------------------------

    try:
        number = float(
            text
        )

        if number.is_integer():
            return str(
                int(number)
            )

        return (
            f"{number:.12g}"
        )

    except ValueError:
        return text


# ============================================================
# COMPARE KEY ANALYTICAL VALUES
# ============================================================

def compare_key_values(
    candidate,
    reference,
):
    """
    Compare the three key analytical fields against the
    validated snapshot.
    """

    print("=" * 70)
    print("KEY VALUE COMPARISON")
    print("=" * 70)

    fields = [
        "S2701_C03_001E",
        "S2701_C05_001E",
        "S2701_C05_001M",
    ]

    all_match = True

    reference_work = (
        reference.copy()
    )

    reference_work["state"] = (
        reference_work["state"]
        .astype(str)
        .str.zfill(2)
    )

    for (
        state_code,
        geography,
    ) in STATES.items():

        candidate_row = candidate.loc[
            candidate["state"]
            == state_code
        ]

        reference_row = (
            reference_work.loc[
                reference_work["state"]
                == state_code
            ]
        )

        if (
            candidate_row.empty
            or reference_row.empty
        ):
            print(
                f"{geography}: MISSING"
            )

            all_match = False
            continue

        state_match = True

        for field in fields:

            candidate_value = normalize_value(
                candidate_row[
                    field
                ].iloc[0]
            )

            reference_value = normalize_value(
                reference_row[
                    field
                ].iloc[0]
            )

            if (
                candidate_value
                != reference_value
            ):
                state_match = False
                all_match = False

                print(
                    f"{geography} | {field}: "
                    f"reference={reference_value!r}, "
                    f"API={candidate_value!r}"
                )

        if state_match:
            print(
                f"{geography}: PASS"
            )

    print()

    if all_match:
        print(
            "Key analytical comparison: PASS"
        )

    else:
        print(
            "Key analytical comparison: REVIEW REQUIRED"
        )

    print()

    return all_match


# ============================================================
# FULL SNAPSHOT COMPARISON
# ============================================================

def compare_full_snapshot(
    candidate,
    reference,
):
    """
    Compare all project fields except source_file.

    source_file is excluded because it is a provenance field.
    The API-generated candidate intentionally records API
    acquisition provenance.
    """

    print("=" * 70)
    print("FULL SNAPSHOT COMPARISON")
    print("=" * 70)

    comparison_columns = [
        column
        for column in reference.columns
        if column != "source_file"
    ]

    reference_compare = (
        reference[
            comparison_columns
        ]
        .copy()
    )

    candidate_compare = (
        candidate[
            comparison_columns
        ]
        .copy()
    )

    # --------------------------------------------------------
    # Normalize state codes
    # --------------------------------------------------------

    reference_compare["state"] = (
        reference_compare["state"]
        .astype(str)
        .str.zfill(2)
    )

    candidate_compare["state"] = (
        candidate_compare["state"]
        .astype(str)
        .str.zfill(2)
    )

    # --------------------------------------------------------
    # Sort both snapshots deterministically
    # --------------------------------------------------------

    reference_compare = (
        reference_compare
        .sort_values("state")
        .reset_index(drop=True)
    )

    candidate_compare = (
        candidate_compare
        .sort_values("state")
        .reset_index(drop=True)
    )

    mismatch_count = 0
    examples = []

    # --------------------------------------------------------
    # Compare every value
    # --------------------------------------------------------

    for column in comparison_columns:

        for row_index in range(
            len(reference_compare)
        ):

            reference_value = normalize_value(
                reference_compare.iloc[
                    row_index
                ][column]
            )

            candidate_value = normalize_value(
                candidate_compare.iloc[
                    row_index
                ][column]
            )

            if (
                reference_value
                != candidate_value
            ):
                mismatch_count += 1

                if len(examples) < 20:

                    state_code = (
                        reference_compare.iloc[
                            row_index
                        ]["state"]
                    )

                    geography = STATES.get(
                        state_code,
                        state_code,
                    )

                    examples.append(
                        (
                            geography,
                            column,
                            reference_value,
                            candidate_value,
                        )
                    )

    # --------------------------------------------------------
    # Report results
    # --------------------------------------------------------

    if mismatch_count == 0:
        print(
            "All comparable values match the "
            "validated snapshot."
        )

        print(
            "Full snapshot comparison: PASS"
        )

        print()

        return True

    print(
        f"Value mismatches detected: {mismatch_count}"
    )

    print()
    print("First mismatches:")

    for (
        geography,
        column,
        reference_value,
        candidate_value,
    ) in examples:

        print(
            f"  {geography} | {column} | "
            f"reference={reference_value!r} | "
            f"API={candidate_value!r}"
        )

    print()

    print(
        "Full snapshot comparison: REVIEW REQUIRED"
    )

    print()

    return False


# ============================================================
# FETCH VARIABLE METADATA
# ============================================================

def fetch_variable_metadata(year):
    """
    Retrieve official Census variable metadata.

    The API key is not included in this metadata request.
    """

    metadata_url = (
        f"https://api.census.gov/data/"
        f"{year}/{DATASET}/variables.json"
    )

    print(
        "Retrieving Census variable metadata..."
    )

    metadata = request_json(
        metadata_url
    )

    if "variables" not in metadata:
        raise RuntimeError(
            "Census metadata response does not "
            "contain variables."
        )

    selected = {}

    for (
        variable,
        details,
    ) in metadata[
        "variables"
    ].items():

        if (
            variable == "NAME"
            or variable.startswith(
                f"{TABLE}_"
            )
        ):
            selected[
                variable
            ] = details

    print(
        f"Metadata variables retained: {len(selected)}"
    )

    print()

    return selected


# ============================================================
# SAVE CANDIDATE DATA
# ============================================================

def save_candidate(
    candidate,
    year,
):
    """
    Save the API result as a candidate snapshot.

    The existing validated snapshot is never overwritten.
    """

    candidate_file = (
        DATA_DIR
        / (
            f"ACSST5Y{year}."
            f"{TABLE}-Data_API_candidate.csv"
        )
    )

    candidate.to_csv(
        candidate_file,
        index=False,
        encoding="utf-8",
    )

    print("Candidate data saved:")
    print(candidate_file)
    print()

    return candidate_file


# ============================================================
# SAVE CANDIDATE METADATA
# ============================================================

def save_metadata(
    year,
    api_endpoint,
    candidate_file,
    reference_file,
    metadata_variables,
    key_match,
    full_match,
    candidate,
):
    """
    Save provenance and validation metadata.

    The Census API key is never stored.
    """

    metadata_file = (
        DATA_DIR
        / (
            f"S2701_{year}_"
            f"metadata_API_candidate.json"
        )
    )

    if (
        key_match
        and full_match
    ):
        validation_status = "pass"

    elif key_match:
        validation_status = "partial_pass"

    else:
        validation_status = "review_required"

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
            "Selected Characteristics of Health "
            "Insurance Coverage in the United States"
        ),
        "vintage": year,
        "reference_period": (
            f"{year - 4}\u2013{year}"
        ),
        "retrieval_method": (
            "U.S. Census Bureau Data API"
        ),
        "api_endpoint": api_endpoint,
        "api_key_stored": False,
        "retrieved_utc": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),
        "geography": "State",
        "jurisdictions": list(
            STATES.values()
        ),
        "candidate_file": (
            candidate_file.name
        ),
        "reference_file": (
            reference_file.name
        ),
        "candidate_rows": int(
            len(candidate)
        ),
        "candidate_columns": int(
            len(candidate.columns)
        ),
        "schema_match": True,
        "key_analytical_values_match": (
            bool(key_match)
        ),
        "full_snapshot_match_excluding_source_file": (
            bool(full_match)
        ),
        "validation_status": (
            validation_status
        ),
        "status": (
            "candidate_pending_review"
        ),
        "notes": (
            "The API candidate was transformed to the exact "
            "column schema of the existing validated project "
            "snapshot. Census API null annotation values were "
            "normalized to blank strings to match the validated "
            "CSV representation. The existing validated snapshot "
            "was not overwritten automatically."
        ),
        "census_variable_metadata": (
            metadata_variables
        ),
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
# FINAL REPORT
# ============================================================

def print_final_report(
    candidate,
    reference,
    candidate_file,
    metadata_file,
    key_match,
    full_match,
):
    """
    Print final acquisition and validation status.
    """

    print("=" * 70)
    print("ACS S2701 DATA ACQUISITION COMPLETED")
    print("=" * 70)

    print()

    print(
        f"Candidate shape : {candidate.shape}"
    )

    print(
        f"Reference shape : {reference.shape}"
    )

    print()

    print(
        "Exact schema match       : PASS"
    )

    print(
        "Key analytical values    : "
        + (
            "PASS"
            if key_match
            else "REVIEW REQUIRED"
        )
    )

    print(
        "Full snapshot comparison : "
        + (
            "PASS"
            if full_match
            else "REVIEW REQUIRED"
        )
    )

    print()

    print(
        "Validated snapshot overwritten: NO"
    )

    print()

    print("Candidate files:")

    print(
        f"  Data     : {candidate_file}"
    )

    print(
        f"  Metadata : {metadata_file}"
    )

    print()

    if (
        key_match
        and full_match
    ):
        print(
            "OVERALL VALIDATION STATUS: PASS"
        )

        print(
            "The API candidate matches the project's "
            "validated schema and comparable data values."
        )

    elif key_match:
        print(
            "OVERALL VALIDATION STATUS: PARTIAL PASS"
        )

        print(
            "The key analytical values match, but differences "
            "remain elsewhere in the complete S2701 snapshot. "
            "Review those differences before promotion."
        )

    else:
        print(
            "OVERALL VALIDATION STATUS: REVIEW REQUIRED"
        )

        print(
            "Do not promote this candidate until the "
            "reported differences are reviewed."
        )

    print()


# ============================================================
# MAIN
# ============================================================

def main():

    args = parse_arguments()

    year = args.year

    print()
    print("=" * 70)
    print("ACS S2701 DATA ACQUISITION")
    print("=" * 70)

    print(
        f"Repository root : {ROOT}"
    )

    print(
        f"Data directory  : {DATA_DIR}"
    )

    print(
        f"Requested year  : {year}"
    )

    print()

    # --------------------------------------------------------
    # Load existing validated snapshot
    # --------------------------------------------------------

    reference, reference_file = (
        load_reference_snapshot(
            year
        )
    )

    # --------------------------------------------------------
    # Validate existing schema
    # --------------------------------------------------------

    validate_reference_schema(
        reference
    )

    # --------------------------------------------------------
    # Obtain API key
    # --------------------------------------------------------

    api_key = get_api_key()

    # --------------------------------------------------------
    # Retrieve complete Census S2701 group
    # --------------------------------------------------------

    raw_frame, api_endpoint = (
        fetch_s2701(
            year,
            api_key,
        )
    )

    # --------------------------------------------------------
    # Select project jurisdictions
    # --------------------------------------------------------

    selected_frame = (
        select_project_states(
            raw_frame
        )
    )

    # --------------------------------------------------------
    # Construct exact project schema
    # --------------------------------------------------------

    candidate = (
        construct_project_schema(
            selected_frame,
            reference,
            year,
        )
    )

    # --------------------------------------------------------
    # Validate exact schema
    # --------------------------------------------------------

    validate_exact_schema(
        candidate,
        reference,
    )

    # --------------------------------------------------------
    # Validate analytical logic
    # --------------------------------------------------------

    validate_analytical_fields(
        candidate,
        year,
    )

    # --------------------------------------------------------
    # Display key project values
    # --------------------------------------------------------

    display_summary(
        candidate,
        year,
    )

    # --------------------------------------------------------
    # Compare key analytical values
    # --------------------------------------------------------

    key_match = (
        compare_key_values(
            candidate,
            reference,
        )
    )

    # --------------------------------------------------------
    # Compare complete snapshot
    # --------------------------------------------------------

    full_match = (
        compare_full_snapshot(
            candidate,
            reference,
        )
    )

    # --------------------------------------------------------
    # Retrieve official Census variable metadata
    # --------------------------------------------------------

    metadata_variables = (
        fetch_variable_metadata(
            year
        )
    )

    # --------------------------------------------------------
    # Save candidate only
    # --------------------------------------------------------

    candidate_file = (
        save_candidate(
            candidate,
            year,
        )
    )

    # --------------------------------------------------------
    # Save provenance and validation metadata
    # --------------------------------------------------------

    metadata_file = (
        save_metadata(
            year=year,
            api_endpoint=api_endpoint,
            candidate_file=candidate_file,
            reference_file=reference_file,
            metadata_variables=metadata_variables,
            key_match=key_match,
            full_match=full_match,
            candidate=candidate,
        )
    )

    # --------------------------------------------------------
    # Final report
    # --------------------------------------------------------

    print_final_report(
        candidate=candidate,
        reference=reference,
        candidate_file=candidate_file,
        metadata_file=metadata_file,
        key_match=key_match,
        full_match=full_match,
    )


if __name__ == "__main__":
    main()
