# Health insurance coverage example planning and exploratory analysis

Thant Win | DATA 690 Census Bureau project | November 5, 2026

**Meeting purpose:** Confirm that ACS S2701 is a useful common dataset for comparison visualization guidance, agree on the first executable examples, and clarify uncertainty and accessibility expectations.

**Current evidence:** Both official Census API data extracts and the selected variable definitions have been verified. The full Python EDA pipeline completed. The selected records passed missingness and count-consistency checks; six draft charts and CSV table alternatives are available in results/. Statistical significance and causal effects have not been tested.

## Initial descriptive findings

- Virginia has the highest displayed uninsured percentage among the five selected jurisdictions in 2020–2024 (6.9% ±0.1 percentage points), and DC has the lowest (3.6% ±0.3 percentage points). Margins of error are at the 90% level; displayed ranks alone do not establish statistically distinguishable differences.
- Maryland and Delaware both display 6.3%, with margins of error of ±0.1 and ±0.4 percentage points, respectively. This is a useful example of equal rounded values with different precision.
- Virginia's displayed rate changes from 8.6% in 2015–2019 to 6.9% in 2020–2024 (−1.7 percentage points). Delaware's changes from 5.7% to 6.3% (+0.6 percentage points). These are descriptive changes, with no policy attribution or significance conclusion.
- Pennsylvania has the largest uninsured count in this selected group (721,936), while its displayed rate is 5.6%. This illustrates why rates and counts answer different questions. The counts are survey population estimates, not sample sizes.

Source: U.S. Census Bureau (2020, 2026b), selected S2701 estimates; calculations in results/.

## Proposed dataset and analytical questions

The main examples will use 2020–2024 ACS five-year estimates (U.S. Census Bureau, 2026b) for Maryland, Virginia, Delaware, Pennsylvania, and the District of Columbia. A second extract, 2015–2019 (U.S. Census Bureau, 2020), will support a descriptive two-period comparison. Census guidance identifies these non-overlapping periods as candidates for comparison, subject to topic and variable comparability checks (U.S. Census Bureau, 2026a).

1. How do uninsured percentages compare across the selected jurisdictions?
2. How do counts and rates lead to different interpretations when populations differ?
3. How does insured/uninsured composition vary across jurisdictions?
4. How do uninsured percentages differ among children, working-age adults, and older adults?
5. What descriptive change appears between the two five-year periods, and how should uncertainty be communicated?

## Links to assigned guidance pages

| Assigned page | Example or discussion | Review emphasis |
|---|---|---|
| Bar Chart | Overall uninsured percentage by jurisdiction | Zero baseline, direct labels, source and period |
| Stacked Bar Chart | Insured and uninsured shares summing to approximately 100% | Common denominator, rounding, small-segment readability |
| Dot Plot Chart | Overall percentage with published 90% margins of error | Uncertainty, readable scales, cautious ranking |
| Lollipop Charts | The same overall percentage comparison | Zero reference, direct labels, whether dots/bars are clearer |
| Slope Diagram | Two-period uninsured percentages | Exactly two periods, comparability, no causal claim |
| Tables | Estimates, units, and margins of error | Precise values, headers, downloadable alternative |
| Axes | Distinguish percentage and count scales | Units, baseline and consistent comparisons |
| Axes–Dual or Double-Y | Explain separate panels for counts and percentages | Avoid implying relationships through arbitrary dual scales |
| Comparing Data and Values | Compare rates, counts, subgroups, and periods | Comparable definitions and denominators |
| Typography | Apply legible titles, labels, notes, and hierarchy | Readability and accessibility review |

These examples will serve the guidance website. Dataset exploration is not a separate predictive modeling or healthcare policy evaluation project. The initial charts will require human review and accessible alternatives; structured accessibility criteria can guide that review (Elavsky et al., 2022).

## Validation before findings

- Confirm that both files are five-year subject tables, with the correct vintage and geography.
- Expect five overall rows per period and one unique geography key per extract.
- Preserve the population definition, estimates, margins of error, source annotations, and raw special values.
- Distinguish unavailable estimates from genuine zeros.
- Check that insured + uninsured counts equal the population total and that shares sum to approximately 100%, allowing for displayed rounding.
- Report changes in **percentage points**. For example, a hypothetical change from 8% to 6% is −2 percentage points, not −2%. These numbers are explanatory only, not Census findings.
- Use published 90% margins of error for uncertainty displays. Use an appropriate statistical procedure before describing differences as statistically significant (U.S. Census Bureau, 2025).
- Do not add overall, age, and sex rows together or treat summary estimates as independent individual observations.

## Suggested opening for the meeting

“I have prepared an exploratory workflow using ACS Table S2701 to support the visualization guidance pages. I verified the selected variable definitions for the two five-year periods and prepared checks for missing values, annotations, denominators, and margins of error. The analysis now includes verified source extracts, initial descriptive results, and draft visualizations. I have not tested statistical significance, so I will distinguish observed patterns from inferential conclusions. I would appreciate confirmation of the example scope and the preferred treatment of uncertainty before implementing the first page.”

## Decisions to request

1. Is S2701 suitable as the shared example source for my assigned comparison pages?
2. Should the first implementation prioritize a bar chart, a dot plot with uncertainty, and a table, then expand to the remaining types?
3. Is the five-jurisdiction scope appropriate, and should the age comparison remain an optional extension?
4. What uncertainty guidance and statistical review should the temporal comparison include?
5. Where should data snapshots, Python/R code, and accessible table alternatives live in the repository?
6. Which topic/tag connections should link these examples to the component documentation?

## What to bring after data loading

Bring the five-jurisdiction results table, the ranked comparison chart, the dot plot with margins of error, and the quality-check summary. Present the two-period comparison only after verifying comparable definitions. Separate observed descriptive findings, interpretation limitations, and decisions requested. No demonstrated improvement in website usability or sponsor acceptance should be claimed until those evaluations occur.

## References

Elavsky, F., Bennett, C., & Moritz, D. (2022). How accessible is my visualization? Evaluating visualization accessibility with Chartability. *Computer Graphics Forum, 41*(3), 57–70. https://doi.org/10.1111/cgf.14522

U.S. Census Bureau. (2020). *Selected characteristics of health insurance coverage in the United States: 2015–2019 American Community Survey five-year estimates subject tables* (Table S2701) [Data set]. https://data.census.gov/table/ACSST5Y2019.S2701

U.S. Census Bureau. (2025, September 24). *Statistical testing tool*. https://www.census.gov/programs-surveys/acs/guidance/statistical-testing-tool.html

U.S. Census Bureau. (2026a, October 29). *Comparing ACS data*. https://www.census.gov/programs-surveys/acs/guidance/comparing-acs-data.html

U.S. Census Bureau. (2026b). *Selected characteristics of health insurance coverage in the United States: 2020–2024 American Community Survey five-year estimates subject tables* (Table S2701) [Data set]. https://data.census.gov/table/ACSST5Y2024.S2701
