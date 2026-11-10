# Reproducible ACS S2701 Horizontal Bar Chart
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
# Measure:
#   Percentage without health insurance coverage.
#
# Geographies:
#   Delaware, District of Columbia, Maryland,
#   Pennsylvania, and Virginia.
#
# Output:
#   results/BarChart1_R.png
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
  "BarChart1_R.png"
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
# S2701_C05_001E:
# Estimate - Percent without health insurance coverage
#
# S2701_C05_001M:
# Margin of error - Percent without health insurance coverage
# ---------------------------------------------------------------------

estimate_column <- "S2701_C05_001E"
moe_column <- "S2701_C05_001M"


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
  estimate_column,
  moe_column
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
# Convert Census estimates and MOEs to numeric
#
# Invalid or unavailable values become NA rather than zero.
# ---------------------------------------------------------------------

data$uninsured_pct <- suppressWarnings(
  as.numeric(data[[estimate_column]])
)

data$uninsured_pct_moe90 <- suppressWarnings(
  as.numeric(data[[moe_column]])
)


# ---------------------------------------------------------------------
# Validate estimates
# ---------------------------------------------------------------------

if (
  any(is.na(data$uninsured_pct)) ||
  any(is.na(data$uninsured_pct_moe90))
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
    data$uninsured_pct < 0 |
    data$uninsured_pct > 100
  )
) {
  stop(
    "Uninsured percentages must be between 0 and 100."
  )
}

if (
  any(data$uninsured_pct_moe90 < 0)
) {
  stop(
    "Margins of error cannot be negative."
  )
}


# ---------------------------------------------------------------------
# Keep variables required for visualization
# ---------------------------------------------------------------------

chart_data <- data[
  ,
  c(
    "geography",
    "uninsured_pct",
    "uninsured_pct_moe90"
  )
]


# ---------------------------------------------------------------------
# Sort by estimate, then geography for deterministic ties
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
# Prepare chart values
# ---------------------------------------------------------------------

values <- chart_data$uninsured_pct

margins <- chart_data$uninsured_pct_moe90

names(values) <- chart_data$geography

upper_bound <- max(
  values + margins
) * 1.2


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
# Horizontal bar chart
# ---------------------------------------------------------------------

bar_positions <- barplot(
  values,
  names.arg = chart_data$geography,
  horiz = TRUE,
  las = 1,
  xlim = c(0, upper_bound),
  col = "#23618c",
  border = NA,
  xlab = "Uninsured population (%)",
  main = paste(
    "Uninsured shares across five jurisdictions",
    "2020-2024 ACS five-year estimates",
    sep = "\n"
  )
)


# ---------------------------------------------------------------------
# Add published 90% margins of error
# ---------------------------------------------------------------------

arrows(
  x0 = values - margins,
  y0 = bar_positions,
  x1 = values + margins,
  y1 = bar_positions,
  angle = 90,
  code = 3,
  length = 0.05
)


# ---------------------------------------------------------------------
# Direct percentage labels
# ---------------------------------------------------------------------

text(
  x = values + margins + 0.1,
  y = bar_positions,
  labels = sprintf(
    "%.1f%%",
    values
  ),
  pos = 4,
  xpd = TRUE
)


# ---------------------------------------------------------------------
# Statistical note
# ---------------------------------------------------------------------

mtext(
  "Error bars show published 90% margins of error.",
  side = 1,
  line = 4.2,
  adj = 0,
  cex = 0.8
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
  "R bar chart created successfully.\n"
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
