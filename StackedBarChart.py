"""
Reproducible ACS S2701 100% Stacked Bar Chart

Source:
    U.S. Census Bureau, American Community Survey (ACS),
    2020–2024 5-Year Estimates, Subject Table S2701,
    Selected Characteristics of Health Insurance Coverage
    in the United States.

Universe:
    Civilian noninstitutionalized population.

Measures:
    Percentage with health insurance coverage.
    Percentage without health insurance coverage.

Geographies:
    Delaware, District of Columbia, Maryland,
    Pennsylvania, and Virginia.

Output:
    results/StackedBarChart1.png

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
    / "StackedBarChart1.png"
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
# S2701_C03_001E:
# Estimate - Percent with health insurance coverage
#
# S2701_C05_001E:
# Estimate - Percent without health insurance coverage
# ---------------------------------------------------------------------

INSURED_COLUMN = "S2701_C03_001E"
UNINSURED_COLUMN = "S2701_C05_001E"


# ---------------------------------------------------------------------
# Load and validate Census data
# ---------------------------------------------------------------------

def load_data():
    """Load and validate insured and uninsured percentages."""

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
        INSURED_COLUMN,
        UNINSURED_COLUMN,
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

    # Convert Census percentages to numeric.
    # Invalid or unavailable values become missing rather than zero.
    df["insured_pct"] = pd.to_numeric(
        df[INSURED_COLUMN],
        errors="coerce",
    )

    df["uninsured_pct"] = pd.to_numeric(
        df[UNINSURED_COLUMN],
        errors="coerce",
    )

    if df[
        [
            "insured_pct",
            "uninsured_pct",
        ]
    ].isna().any().any():

        raise ValueError(
            "Missing or nonnumeric estimates detected. "
            "Review Census annotations before publishing."
        )

    # Validate percentage ranges.
    if not df["insured_pct"].between(
        0,
        100,
    ).all():

        raise ValueError(
            "Insured percentages must be between 0 and 100."
        )

    if not df["uninsured_pct"].between(
        0,
        100,
    ).all():

        raise ValueError(
            "Uninsured percentages must be between 0 and 100."
        )

    # Insured + uninsured should form approximately 100%.
    # A small tolerance is allowed for published rounding.
    df["composition_total"] = (
        df["insured_pct"]
        + df["uninsured_pct"]
    )

    if not df["composition_total"].between(
        99.9,
        100.1,
    ).all():

        raise ValueError(
            "Insured and uninsured percentages do not sum "
            "to approximately 100%. Review the source data."
        )

    chart_data = df[
        [
            "geography",
            "insured_pct",
            "uninsured_pct",
        ]
    ].copy()

    # Sort using uninsured percentage to maintain the same
    # comparison order as the other visualization examples.
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
    """Generate the ACS S2701 100% stacked bar chart."""

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

    insured = chart_data[
        "insured_pct"
    ].to_numpy()

    uninsured = chart_data[
        "uninsured_pct"
    ].to_numpy()

    fig, ax = plt.subplots(
        figsize=(9, 4.7)
    )

    # Insured portion.
    ax.barh(
        names,
        insured,
        color="#adbcc7",
        label="Insured",
    )

    # Uninsured portion stacked to the right.
    ax.barh(
        names,
        uninsured,
        left=insured,
        color="#23618c",
        label="Uninsured",
    )

    # Direct percentage labels.
    for i, (
        insured_value,
        uninsured_value,
    ) in enumerate(
        zip(
            insured,
            uninsured,
        )
    ):

        # Insured label.
        ax.text(
            insured_value / 2,
            i,
            f"{insured_value:.1f}%",
            ha="center",
            va="center",
        )

        # For very small uninsured segments, place the label
        # outside the bar so it remains readable.
        if uninsured_value < 4:
            ax.text(
                101,
                i,
                f"{uninsured_value:.1f}%",
                ha="left",
                va="center",
                color="black",
                fontsize=9,
            )
        else:
            ax.text(
                insured_value
                + uninsured_value / 2,
                i,
                f"{uninsured_value:.1f}%",
                ha="center",
                va="center",
                color="white",
                fontsize=9,
            )

    # A 100% stacked chart always uses a complete 0-100 scale.
    ax.set_xlim(
        0,
        100,
    )

    ax.set_xlabel(
        "Share of population (%)"
    )

    ax.set_title(
        "Insured and uninsured composition\n"
        "2020–2024 ACS five-year estimates"
    )

    # Place the legend below the chart.
    fig.legend(
        loc="lower center",
        bbox_to_anchor=(0.6, 0.06),
        ncol=2,
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
        rect=(0, 0.18, 1, 1)
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
        "Stacked bar chart created successfully."
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
