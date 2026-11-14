# Reproducible ACS S2701 100% Stacked Bar Chart
#
# Source:
#   U.S. Census Bureau, American Community Survey (ACS),
#   2020-2024 5-Year Estimates, Subject Table S2701,
#   Selected Characteristics of Health Insurance Coverage
#   in the United States.
#
# Universe:
#   Civilian noninstitutionalized population.
#
# Measures:
#   Percentage with health insurance coverage.
#   Percentage without health insurance coverage.
#
# Geographies:
#   Delaware, District of Columbia, Maryland,
#   Pennsylvania, and Virginia.
#
# Output:
#   results/StackedBarChart1_R.png
#
# This script reads the official Census flat CSV stored in the
# repository's data directory. Missing or unavailable values are
# not replaced with zero.


# ---------------------------------------------------------------------
# File locations
# ---------------------------------------------------------------------

data_file <- file.path(
  "data",
  "ACSST5Y2024.S2701-Data.csv"
)

output_file <- file.path(
  "results",
  "StackedBarChart1_R.png"
)


# ---------------------------------------------------------------------
# Geographic scope
# ---------------------------------------------------------------------

states <- c(
  "10" = "Delaware",
  "11" = "District of Columbia",
  "24" = "Maryland",
  "42" = "Pennsylvania",
  "51" = "Virginia"
)


# ---------------------------------------------------------------------
# ACS S2701 variables
#
# S2701_C03_001E:
# Estimate - Percent with health insurance coverage
#
# S2701_C05_001E:
# Estimate - Percent without health insurance coverage
# ---------------------------------------------------------------------

insured_column <- "S2701_C03_001E"
uninsured_column <- "S2701_C05_001E"


# ---------------------------------------------------------------------
# Load Census data
# ---------------------------------------------------------------------

if (!file.exists(data_file)) {
  stop(
    paste(
      "Required Census file not found:",
      data_file
    )
  )
}

data <- read.csv(
  data_file,
  stringsAsFactors = FALSE,
  check.names = FALSE,
  na.strings = NULL
)


# ---------------------------------------------------------------------
# Validate required columns
# ---------------------------------------------------------------------

required_columns <- c(
  "GEO_ID",
  insured_column,
  uninsured_column
)

missing_columns <- setdiff(
  required_columns,
  names(data)
)

if (length(missing_columns) > 0) {
  stop(
    paste(
      "Required S2701 columns are missing:",
      paste(missing_columns, collapse = ", ")
    )
  )
}


# ---------------------------------------------------------------------
# Retain state-level Census records
# ---------------------------------------------------------------------

state_rows <- grepl(
  "^0400000US[0-9]{2}$",
  data$GEO_ID
)

data <- data[
  state_rows,
  ,
  drop = FALSE
]

data$state_fips <- substr(
  data$GEO_ID,
  nchar(data$GEO_ID) - 1,
  nchar(data$GEO_ID)
)


# ---------------------------------------------------------------------
# Retain the five jurisdictions used in the example
# ---------------------------------------------------------------------

data <- data[
  data$state_fips %in% names(states),
  ,
  drop = FALSE
]

if (!setequal(
  data$state_fips,
  names(states)
)) {
  stop(
    paste(
      "Expected exactly Delaware, District of Columbia,",
      "Maryland, Pennsylvania, and Virginia."
    )
  )
}

if (anyDuplicated(data$state_fips) > 0) {
  stop(
    "Duplicate state records were found in the Census export."
  )
}


# ---------------------------------------------------------------------
# Create readable geography names
# ---------------------------------------------------------------------

data$geography <- unname(
  states[data$state_fips]
)


# ---------------------------------------------------------------------
# Convert Census percentages to numeric
#
# Invalid or unavailable values become NA rather than zero.
# ---------------------------------------------------------------------

data$insured_pct <- suppressWarnings(
  as.numeric(data[[insured_column]])
)

data$uninsured_pct <- suppressWarnings(
  as.numeric(data[[uninsured_column]])
)


# ---------------------------------------------------------------------
# Validate estimates
# ---------------------------------------------------------------------

if (
  any(is.na(data$insured_pct)) ||
  any(is.na(data$uninsured_pct))
) {
  stop(
    paste(
      "Missing or nonnumeric estimates detected.",
      "Review Census annotations before publishing."
    )
  )
}

if (
  any(
    data$insured_pct < 0 |
    data$insured_pct > 100
  )
) {
  stop(
    "Insured percentages must be between 0 and 100."
  )
}

if (
  any(
    data$uninsured_pct < 0 |
    data$uninsured_pct > 100
  )
) {
  stop(
    "Uninsured percentages must be between 0 and 100."
  )
}


# ---------------------------------------------------------------------
# Validate part-to-whole composition
#
# Insured + uninsured should equal approximately 100%.
# A small tolerance is allowed for published rounding.
# ---------------------------------------------------------------------

data$composition_total <- (
  data$insured_pct +
  data$uninsured_pct
)

if (
  any(
    data$composition_total < 99.9 |
    data$composition_total > 100.1
  )
) {
  stop(
    paste(
      "Insured and uninsured percentages do not sum",
      "to approximately 100%. Review the source data."
    )
  )
}


# ---------------------------------------------------------------------
# Keep variables required for visualization
# ---------------------------------------------------------------------

chart_data <- data[
  ,
  c(
    "geography",
    "insured_pct",
    "uninsured_pct"
  )
]


# ---------------------------------------------------------------------
# Sort by uninsured estimate, then geography
# ---------------------------------------------------------------------

chart_data <- chart_data[
  order(
    chart_data$uninsured_pct,
    chart_data$geography
  ),
  ,
  drop = FALSE
]

rownames(chart_data) <- NULL


# ---------------------------------------------------------------------
# Prepare chart data
#
# barplot() expects each column to represent one stacked bar.
# ---------------------------------------------------------------------

plot_matrix <- rbind(
  Insured = chart_data$insured_pct,
  Uninsured = chart_data$uninsured_pct
)


# ---------------------------------------------------------------------
# Ensure output directory exists
# ---------------------------------------------------------------------

dir.create(
  dirname(output_file),
  recursive = TRUE,
  showWarnings = FALSE
)


# ---------------------------------------------------------------------
# Create PNG
# ---------------------------------------------------------------------

png(
  filename = output_file,
  width = 9,
  height = 4.7,
  units = "in",
  res = 180
)


# ---------------------------------------------------------------------
# Chart layout
# ---------------------------------------------------------------------

par(
  mar = c(6.5, 10, 4.5, 1.5),
  family = "sans"
)


# ---------------------------------------------------------------------
# Create horizontal 100% stacked bars
# ---------------------------------------------------------------------

bar_positions <- barplot(
  plot_matrix,
  names.arg = chart_data$geography,
  horiz = TRUE,
  las = 1,
  xlim = c(0, 100),
  col = c(
    "#adbcc7",
    "#23618c"
  ),
  border = NA,
  xlab = "Share of population (%)",
  main = paste(
    "Insured and uninsured composition",
    "2020-2024 ACS five-year estimates",
    sep = "\n"
  ),
  legend.text = FALSE
)


# ---------------------------------------------------------------------
# Add insured percentage labels
# ---------------------------------------------------------------------

text(
  x = chart_data$insured_pct / 2,
  y = bar_positions,
  labels = sprintf(
    "%.1f%%",
    chart_data$insured_pct
  ),
  cex = 0.9
)


# ---------------------------------------------------------------------
# Add uninsured percentage labels
#
# Small segments are labeled outside the bar.
# ---------------------------------------------------------------------

for (i in seq_len(nrow(chart_data))) {

  uninsured_value <- (
    chart_data$uninsured_pct[i]
  )

  insured_value <- (
    chart_data$insured_pct[i]
  )

  if (uninsured_value < 4) {

    text(
      x = 101,
      y = bar_positions[i],
      labels = sprintf(
        "%.1f%%",
        uninsured_value
      ),
      pos = 4,
      xpd = TRUE,
      cex = 0.8
    )

  } else {

    text(
      x = (
        insured_value +
        uninsured_value / 2
      ),
      y = bar_positions[i],
      labels = sprintf(
        "%.1f%%",
        uninsured_value
      ),
      col = "white",
      cex = 0.8
    )
  }
}


# ---------------------------------------------------------------------
# Legend
# ---------------------------------------------------------------------

legend(
  "bottom",
  inset = c(0, -0.28),
  legend = c(
    "Insured",
    "Uninsured"
  ),
  fill = c(
    "#adbcc7",
    "#23618c"
  ),
  border = NA,
  horiz = TRUE,
  xpd = TRUE,
  bty = "n"
)


# ---------------------------------------------------------------------
# Census source
# ---------------------------------------------------------------------

mtext(
  paste(
    "Source: U.S. Census Bureau, ACS S2701.",
    "Civilian noninstitutionalized population."
  ),
  side = 1,
  line = 5.3,
  adj = 0,
  cex = 0.7
)


# ---------------------------------------------------------------------
# Finish image
# ---------------------------------------------------------------------

dev.off()


# ---------------------------------------------------------------------
# Report results
# ---------------------------------------------------------------------

cat(
  "R stacked bar chart created successfully.\n"
)

cat(
  paste(
    "Output:",
    output_file,
    "\n\n"
  )
)

print(
  chart_data,
  row.names = FALSE
)
