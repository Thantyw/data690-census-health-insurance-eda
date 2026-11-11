"""
Reproducible ACS S2701 Accessible Table

Source:
    U.S. Census Bureau, American Community Survey (ACS),
    2020–2024 5-Year Estimates, Subject Table S2701,
    Selected Characteristics of Health Insurance Coverage
    in the United States.

Universe:
    Civilian noninstitutionalized population.

Measure:
    Percentage without health insurance coverage and
    published 90% margin of error.

Geographies:
    Delaware, District of Columbia, Maryland,
    Pennsylvania, and Virginia.

Outputs:
    results/Table1.csv
    results/Table1.html

Purpose:
    Provide precise Census estimates and uncertainty in
    machine-readable and accessible tabular formats.

Missing or unavailable Census values are not replaced with zero.
"""

from pathlib import Path
from html import escape

import pandas as pd


# ---------------------------------------------------------------------
# File locations
# ---------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent

DATA_FILE = (
    ROOT
    / "data"
    / "ACSST5Y2024.S2701-Data.csv"
)

CSV_OUTPUT = (
    ROOT
    / "results"
    / "Table1.csv"
)

HTML_OUTPUT = (
    ROOT
    / "results"
    / "Table1.html"
)


# ---------------------------------------------------------------------
# Geographic scope
# ---------------------------------------------------------------------

STATES = {
    "10": "Delaware",
    "11": "District of Columbia",
    "24": "Maryland",
    "42": "Pennsylvania",
    "51": "Virginia",
}


# ---------------------------------------------------------------------
# ACS S2701 variables
#
# S2701_C05_001E:
# Estimate - Percent without health insurance coverage
#
# S2701_C05_001M:
# Margin of error - Percent without health insurance coverage
# ---------------------------------------------------------------------

ESTIMATE_COLUMN = "S2701_C05_001E"
MOE_COLUMN = "S2701_C05_001M"


# ---------------------------------------------------------------------
# Load and validate Census data
# ---------------------------------------------------------------------

def load_data():

    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Required Census file not found: {DATA_FILE}"
        )

    df = pd.read_csv(
        DATA_FILE,
        dtype=str,
        keep_default_na=False,
        encoding="utf-8-sig",
    )

    required_columns = {
        "GEO_ID",
        ESTIMATE_COLUMN,
        MOE_COLUMN,
    }

    missing_columns = required_columns.difference(
        df.columns
    )

    if missing_columns:
        raise ValueError(
            "Required S2701 columns are missing: "
            f"{sorted(missing_columns)}"
        )


    # -----------------------------------------------------------------
    # Retain state-level records
    # -----------------------------------------------------------------

    df = df[
        df["GEO_ID"].str.fullmatch(
            r"0400000US\d{2}",
            na=False,
        )
    ].copy()

    df["state_fips"] = df["GEO_ID"].str[-2:]


    # -----------------------------------------------------------------
    # Retain selected jurisdictions
    # -----------------------------------------------------------------

    df = df[
        df["state_fips"].isin(STATES)
    ].copy()

    if set(df["state_fips"]) != set(STATES):
        raise ValueError(
            "Expected exactly Delaware, District of Columbia, "
            "Maryland, Pennsylvania, and Virginia."
        )

    if df["state_fips"].duplicated().any():
        raise ValueError(
            "Duplicate state records were found "
            "in the Census export."
        )

    df["Geography"] = (
        df["state_fips"].map(STATES)
    )


    # -----------------------------------------------------------------
    # Convert estimate and MOE to numeric
    #
    # Invalid or unavailable values become missing rather than zero.
    # -----------------------------------------------------------------

    df["Uninsured population (%)"] = pd.to_numeric(
        df[ESTIMATE_COLUMN],
        errors="coerce",
    )

    df["90% margin of error (pp)"] = pd.to_numeric(
        df[MOE_COLUMN],
        errors="coerce",
    )


    # -----------------------------------------------------------------
    # Validate values
    # -----------------------------------------------------------------

    if df[
        [
            "Uninsured population (%)",
            "90% margin of error (pp)",
        ]
    ].isna().any().any():

        raise ValueError(
            "Missing or nonnumeric Census estimates or margins "
            "of error detected. Review Census annotations."
        )

    if not df[
        "Uninsured population (%)"
    ].between(
        0,
        100,
    ).all():

        raise ValueError(
            "Uninsured percentages must be between 0 and 100."
        )

    if (
        df[
            "90% margin of error (pp)"
        ] < 0
    ).any():

        raise ValueError(
            "Margins of error must not be negative."
        )


    # -----------------------------------------------------------------
    # Prepare final table
    # -----------------------------------------------------------------

    table = df[
        [
            "Geography",
            "Uninsured population (%)",
            "90% margin of error (pp)",
        ]
    ].copy()

    table = table.sort_values(
        [
            "Uninsured population (%)",
            "Geography",
        ],
        ascending=[
            True,
            True,
        ],
    ).reset_index(drop=True)

    return table


# ---------------------------------------------------------------------
# Save machine-readable CSV
# ---------------------------------------------------------------------

def save_csv(table):

    CSV_OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    table.to_csv(
        CSV_OUTPUT,
        index=False,
        float_format="%.1f",
    )


# ---------------------------------------------------------------------
# Save accessible HTML table
# ---------------------------------------------------------------------

def save_html(table):

    rows = []

    for _, row in table.iterrows():

        geography = escape(
            str(row["Geography"])
        )

        estimate = (
            f'{row["Uninsured population (%)"]:.1f}%'
        )

        moe = (
            f'±{row["90% margin of error (pp)"]:.1f}'
        )

        rows.append(
            f"""
            <tr>
                <th scope="row">{geography}</th>
                <td>{estimate}</td>
                <td>{moe}</td>
            </tr>
            """
        )

    table_rows = "\n".join(rows)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport"
          content="width=device-width, initial-scale=1">

    <title>
        ACS S2701 Uninsured Population Estimates
    </title>

    <style>
        body {{
            font-family: Arial, Helvetica, sans-serif;
            margin: 2rem;
            line-height: 1.5;
            color: #222;
        }}

        table {{
            border-collapse: collapse;
            width: 100%;
            max-width: 850px;
        }}

        caption {{
            text-align: left;
            font-weight: bold;
            font-size: 1.15rem;
            margin-bottom: 0.75rem;
        }}

        th,
        td {{
            border-bottom: 1px solid #cccccc;
            padding: 0.65rem;
            text-align: left;
        }}

        thead th {{
            border-bottom: 2px solid #555555;
        }}

        tbody th {{
            font-weight: normal;
        }}

        .note {{
            max-width: 850px;
            margin-top: 1rem;
            font-size: 0.9rem;
        }}
    </style>
</head>

<body>

<main>

<table>

    <caption>
        Uninsured population estimates across five jurisdictions,
        2020–2024 ACS five-year estimates
    </caption>

    <thead>
        <tr>
            <th scope="col">Geography</th>
            <th scope="col">
                Uninsured population (%)
            </th>
            <th scope="col">
                90% margin of error (percentage points)
            </th>
        </tr>
    </thead>

    <tbody>
        {table_rows}
    </tbody>

</table>

<p class="note">
    <strong>Source:</strong>
    U.S. Census Bureau, American Community Survey,
    2020–2024 ACS 5-Year Estimates,
    Subject Table S2701,
    <em>Selected Characteristics of Health Insurance Coverage
    in the United States</em>.
    Universe: civilian noninstitutionalized population.
</p>

<p class="note">
    <strong>Note:</strong>
    Margins of error are published at the 90% confidence level.
    Differences between displayed estimates should not automatically
    be interpreted as statistically significant.
</p>

</main>

</body>
</html>
"""

    HTML_OUTPUT.write_text(
        html,
        encoding="utf-8",
    )


# ---------------------------------------------------------------------
# Run reproducible example
# ---------------------------------------------------------------------

def main():

    table = load_data()

    save_csv(table)

    save_html(table)

    print(
        "Accessible Census table created successfully."
    )

    print(
        f"CSV output: {CSV_OUTPUT}"
    )

    print(
        f"HTML output: {HTML_OUTPUT}"
    )

    print()

    print(
        table.to_string(
            index=False
        )
    )


if __name__ == "__main__":
    main()
