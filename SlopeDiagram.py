"""
Reproducible ACS S2701 Slope Diagram

Source:
    U.S. Census Bureau, American Community Survey (ACS),
    2015–2019 and 2020–2024 5-Year Estimates,
    Subject Table S2701,
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
    results/SlopeDiagram1.png

Purpose:
    Descriptively compare uninsured percentages between two
    non-overlapping ACS five-year periods.

Important:
    The chart does not test statistical significance and should
    not be interpreted as establishing causal change.
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

DATA_FILE_2019 = (
    ROOT
    / "data"
    / "ACSST5Y2019.S2701-Data.csv"
)

DATA_FILE_2024 = (
    ROOT
    / "data"
    / "ACSST5Y2024.S2701-Data.csv"
)

OUTPUT_FILE = (
    ROOT
    / "results"
    / "SlopeDiagram1.png"
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
# Load one ACS five-year snapshot
# ---------------------------------------------------------------------

def load_snapshot(file_path, period):

    if not file_path.exists():
        raise FileNotFoundError(
            f"Required Census file not found: {file_path}"
        )

    df = pd.read_csv(
        file_path,
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
            f"{period}: required S2701 columns are missing: "
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

    # Retain selected jurisdictions.
    df = df[
        df["state_fips"].isin(STATES)
    ].copy()

    if set(df["state_fips"]) != set(STATES):
        raise ValueError(
            f"{period}: expected exactly Delaware, "
            "District of Columbia, Maryland, "
            "Pennsylvania, and Virginia."
        )

    if df["state_fips"].duplicated().any():
        raise ValueError(
            f"{period}: duplicate state records found."
        )

    df["geography"] = (
        df["state_fips"].map(STATES)
    )

    df["uninsured_pct"] = pd.to_numeric(
        df[ESTIMATE_COLUMN],
        errors="coerce",
    )

    if df["uninsured_pct"].isna().any():
        raise ValueError(
            f"{period}: missing or nonnumeric estimates "
            "detected. Review Census annotations."
        )

    if not df["uninsured_pct"].between(
        0,
        100,
    ).all():

        raise ValueError(
            f"{period}: uninsured percentages must "
            "be between 0 and 100."
        )

    return df[
        [
            "state_fips",
            "geography",
            "uninsured_pct",
        ]
    ].copy()


# ---------------------------------------------------------------------
# Prepare cross-period comparison
# ---------------------------------------------------------------------

def prepare_comparison():

    earlier = load_snapshot(
        DATA_FILE_2019,
        "2015–2019",
    )

    later = load_snapshot(
        DATA_FILE_2024,
        "2020–2024",
    )

    comparison = earlier.merge(
        later,
        on=[
            "state_fips",
            "geography",
        ],
        how="inner",
        suffixes=(
            "_2015_2019",
            "_2020_2024",
        ),
        validate="one_to_one",
    )

    if len(comparison) != len(STATES):
        raise ValueError(
            "The two ACS periods do not contain "
            "the same five jurisdictions."
        )

    comparison[
        "change_percentage_points"
    ] = (
        comparison[
            "uninsured_pct_2020_2024"
        ]
        -
        comparison[
            "uninsured_pct_2015_2019"
        ]
    )

    # Deterministic ordering for plotting and validation.
    comparison = comparison.sort_values(
        "geography"
    ).reset_index(drop=True)

    return comparison


# ---------------------------------------------------------------------
# Create visualization
# ---------------------------------------------------------------------

def create_chart(comparison):

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )

    fig, ax = plt.subplots(
        figsize=(9, 5)
    )

    colors = plt.get_cmap(
        "tab10"
    ).colors

    for i, row in comparison.iterrows():

        earlier = row[
            "uninsured_pct_2015_2019"
        ]

        later = row[
            "uninsured_pct_2020_2024"
        ]

        change = row[
            "change_percentage_points"
        ]

        geography = row[
            "geography"
        ]

        ax.plot(
            [0, 1],
            [
                earlier,
                later,
            ],
            marker="o",
            color=colors[i],
            label=(
                f"{geography} "
                f"({change:+.1f} pp)"
            ),
        )

    ax.set_xticks(
        [0, 1]
    )

    ax.set_xticklabels(
        [
            "2015–2019",
            "2020–2024",
        ]
    )

    ax.set_ylabel(
        "Uninsured population (%)"
    )

    ax.set_title(
        "Change between non-overlapping five-year periods\n"
        "Descriptive comparison; significance not tested"
    )

    max_value = max(
        comparison[
            "uninsured_pct_2015_2019"
        ].max(),
        comparison[
            "uninsured_pct_2020_2024"
        ].max(),
    )

    ax.set_ylim(
        0,
        max_value * 1.2,
    )

    ax.legend(
        bbox_to_anchor=(1.02, 1),
        loc="upper left",
        fontsize=9,
    )

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

    comparison = prepare_comparison()

    create_chart(comparison)

    print(
        "Slope diagram created successfully."
    )

    print(
        f"Output: {OUTPUT_FILE}"
    )

    print()

    print(
        comparison[
            [
                "geography",
                "uninsured_pct_2015_2019",
                "uninsured_pct_2020_2024",
                "change_percentage_points",
            ]
        ].to_string(
            index=False
        )
    )

    print()
    print(
        "Interpretation: descriptive comparison only; "
        "statistical significance was not tested."
    )


if __name__ == "__main__":
    main()
