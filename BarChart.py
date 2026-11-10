"""
Reproducible ACS S2701 Horizontal Bar Chart

Source:
    U.S. Census Bureau, American Community Survey (ACS),
    2020–2024 5-Year Estimates, Subject Table S2701,
    Selected Characteristics of Health Insurance Coverage
    in the United States.

Universe:
    Civilian noninstitutionalized population.

Measure:
    Percentage without health insurance coverage.

Geographies:
    Delaware, District of Columbia, Maryland,
    Pennsylvania, and Virginia.

Output:
    results/BarChart1.png

The script reads the official Census flat CSV stored in the
repository's data directory. Missing or unavailable values are
not replaced with zero.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
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

OUTPUT_FILE = (
    ROOT
    / "results"
    / "BarChart1.png"
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
# Estimate — Percent without health insurance coverage
#
# S2701_C05_001M:
# Margin of error — Percent without health insurance coverage
# ---------------------------------------------------------------------

ESTIMATE_COLUMN = "S2701_C05_001E"
MOE_COLUMN = "S2701_C05_001M"


# ---------------------------------------------------------------------
# Load and validate Census data
# ---------------------------------------------------------------------

def load_data():
    """Load and validate the five ACS S2701 estimates."""

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

    # Retain state-level Census records only.
    df = df[
        df["GEO_ID"].str.fullmatch(
            r"0400000US\d{2}",
            na=False,
        )
    ].copy()

    df["state_fips"] = df["GEO_ID"].str[-2:]

    # Retain the five jurisdictions used in the example.
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

    df["geography"] = (
        df["state_fips"].map(STATES)
    )

    # Convert Census estimate and MOE fields to numeric values.
    # Invalid or unavailable values become missing rather than zero.
    df["uninsured_pct"] = pd.to_numeric(
        df[ESTIMATE_COLUMN],
        errors="coerce",
    )

    df["uninsured_pct_moe90"] = pd.to_numeric(
        df[MOE_COLUMN],
        errors="coerce",
    )

    # Stop rather than publish a chart containing missing values.
    if df[
        [
            "uninsured_pct",
            "uninsured_pct_moe90",
        ]
    ].isna().any().any():

        raise ValueError(
            "Missing or nonnumeric estimates detected. "
            "Review Census annotations before publishing."
        )

    # Percentage values must remain within a valid range.
    if not df["uninsured_pct"].between(
        0,
        100,
    ).all():

        raise ValueError(
            "Uninsured percentages must be "
            "between 0 and 100."
        )

    # Margins of error cannot be negative.
    if (
        df["uninsured_pct_moe90"] < 0
    ).any():

        raise ValueError(
            "Margins of error cannot be negative."
        )

    # Keep only variables required for the visualization.
    chart_data = df[
        [
            "geography",
            "uninsured_pct",
            "uninsured_pct_moe90",
        ]
    ].copy()

    # Sort by estimate for easier visual comparison.
    # Geography provides a deterministic tie-break when
    # two displayed estimates are equal.
    chart_data = chart_data.sort_values(
        [
            "uninsured_pct",
            "geography",
        ],
        ascending=[
            True,
            True,
        ],
    ).reset_index(drop=True)

    return chart_data


# ---------------------------------------------------------------------
# Create visualization
# ---------------------------------------------------------------------

def create_chart(chart_data):
    """Generate the horizontal ACS S2701 bar chart."""

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )

    names = chart_data[
        "geography"
    ].tolist()

    values = chart_data[
        "uninsured_pct"
    ].to_numpy()

    margins = chart_data[
        "uninsured_pct_moe90"
    ].to_numpy()

    fig, ax = plt.subplots(
        figsize=(9, 4.7)
    )

    # Horizontal bars with published
    # ACS 90% margins of error.
    ax.barh(
        names,
        values,
        color="#23618c",
        xerr=margins,
        capsize=4,
    )

    # Preserve a zero baseline.
    upper_bound = max(
        values + margins
    )

    ax.set_xlim(
        0,
        upper_bound * 1.2,
    )

    ax.set_xlabel(
        "Uninsured population (%)"
    )

    ax.set_title(
        "Uninsured shares across five jurisdictions\n"
        "2020–2024 ACS five-year estimates"
    )

    # Add direct percentage labels.
    for i, value in enumerate(values):

        ax.text(
            value + margins[i] + 0.1,
            i,
            f"{value:.1f}%",
            va="center",
        )

    # Explain the uncertainty encoding.
    ax.text(
        0,
        -0.20,
        (
            "Error bars show published "
            "90% margins of error."
        ),
        transform=ax.transAxes,
        fontsize=9,
    )

    # Census source annotation.
    source = (
        "Source: U.S. Census Bureau, ACS S2701. "
        "Civilian noninstitutionalized population."
    )

    fig.text(
        0.02,
        0.015,
        source,
        fontsize=8,
    )

    # Ensure the output directory exists.
    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fig.tight_layout(
        rect=(0, 0.09, 1, 1)
    )

    fig.savefig(
        OUTPUT_FILE,
        dpi=180,
        bbox_inches="tight",
    )

    plt.close(fig)


# ---------------------------------------------------------------------
# Run reproducible example
# ---------------------------------------------------------------------

def main():

    chart_data = load_data()

    create_chart(chart_data)

    print(
        "Bar chart created successfully."
    )

    print(
        f"Output: {OUTPUT_FILE}"
    )

    print()

    print(
        chart_data.to_string(
            index=False
        )
    )


if __name__ == "__main__":
    main()
