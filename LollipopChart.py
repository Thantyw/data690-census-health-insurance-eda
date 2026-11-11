"""
Reproducible ACS S2701 Lollipop Chart

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
    results/LollipopChart1.png

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
    / "LollipopChart1.png"
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
# ACS S2701 variable
#
# S2701_C05_001E:
# Estimate - Percent without health insurance coverage
# ---------------------------------------------------------------------

ESTIMATE_COLUMN = "S2701_C05_001E"


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
    }

    missing_columns = required_columns.difference(
        df.columns
    )

    if missing_columns:
        raise ValueError(
            "Required S2701 columns are missing: "
            f"{sorted(missing_columns)}"
        )

    # Retain state-level Census records.
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

    # Convert published Census estimates to numeric.
    # Invalid or unavailable values become missing rather than zero.
    df["uninsured_pct"] = pd.to_numeric(
        df[ESTIMATE_COLUMN],
        errors="coerce",
    )

    if df["uninsured_pct"].isna().any():
        raise ValueError(
            "Missing or nonnumeric estimates detected. "
            "Review Census annotations before publishing."
        )

    if not df["uninsured_pct"].between(
        0,
        100,
    ).all():

        raise ValueError(
            "Uninsured percentages must be "
            "between 0 and 100."
        )

    chart_data = df[
        [
            "geography",
            "uninsured_pct",
        ]
    ].copy()

    # Sort estimates to support comparison.
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
    """Generate the ACS S2701 lollipop chart."""

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

    fig, ax = plt.subplots(
        figsize=(9, 4.7)
    )

    # Draw stems from the zero baseline to each estimate.
    ax.hlines(
        names,
        0,
        values,
        color="#6c8da5",
    )

    # Draw point estimates at the end of each stem.
    ax.scatter(
        values,
        names,
        color="#23618c",
        s=60,
    )

    ax.set_xlim(
        0,
        max(values) * 1.2,
    )

    ax.set_xlabel(
        "Uninsured population (%)"
    )

    ax.set_title(
        "Lollipop chart for comparing uninsured shares\n"
        "2020–2024 ACS five-year estimates"
    )

    # Add direct value labels.
    for geography, value in zip(
        names,
        values,
    ):
        ax.text(
            value + 0.1,
            geography,
            f"{value:.1f}%",
            va="center",
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

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fig.tight_layout(
        rect=(0, 0.08, 1, 1)
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
        "Lollipop chart created successfully."
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
