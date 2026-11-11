# Reproducible ACS S2701 Lollipop Chart
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
#   results/LollipopChart1_R.png
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
  "LollipopChart1_R.png"
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
# ACS S2701 variable
#
# S2701_C05_001E:
# Estimate - Percent without health insurance coverage
# ---------------------------------------------------------------------

estimate_column <- "S2701_C05_001E"


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
  estimate_column
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
# Convert Census estimates to numeric
#
# Invalid or unavailable values become NA rather than zero.
# ---------------------------------------------------------------------

data$uninsured_pct <- suppressWarnings(
  as.numeric(data[[estimate_column]])
)


# ---------------------------------------------------------------------
# Validate estimates
# ---------------------------------------------------------------------

if (any(is.na(data$uninsured_pct))) {
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


# ---------------------------------------------------------------------
# Keep variables required for visualization
# ---------------------------------------------------------------------

chart_data <- data[
  ,
  c(
    "geography",
    "uninsured_pct"
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

y_positions <- seq_along(
  chart_data$geography
)

upper_bound <- max(values) * 1.2


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
  mar = c(5.5, 10, 4.5, 1.5),
  family = "sans"
)


# ---------------------------------------------------------------------
# Create plotting area
# ---------------------------------------------------------------------

plot(
  values,
  y_positions,
  type = "n",
  xlim = c(0, upper_bound),
  ylim = c(
    0.5,
    length(y_positions) + 0.5
  ),
  xlab = "Uninsured population (%)",
  ylab = "",
  yaxt = "n",
  main = paste(
    "Lollipop chart for comparing uninsured shares",
    "2020-2024 ACS five-year estimates",
    sep = "\n"
  ),
  bty = "l"
)


# ---------------------------------------------------------------------
# Geography labels
# ---------------------------------------------------------------------

axis(
  side = 2,
  at = y_positions,
  labels = chart_data$geography,
  las = 1
)


# ---------------------------------------------------------------------
# Draw lollipop stems
# ---------------------------------------------------------------------

segments(
  x0 = 0,
  y0 = y_positions,
  x1 = values,
  y1 = y_positions,
  col = "#6c8da5",
  lwd = 2
)


# ---------------------------------------------------------------------
# Draw point estimates
# ---------------------------------------------------------------------

points(
  values,
  y_positions,
  pch = 19,
  col = "#23618c",
  cex = 1.2
)


# ---------------------------------------------------------------------
# Direct value labels
# ---------------------------------------------------------------------

text(
  x = values + 0.1,
  y = y_positions,
  labels = sprintf(
    "%.1f%%",
    values
  ),
  pos = 4,
  xpd = TRUE
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
  line = 4.2,
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
  "R lollipop chart created successfully.\n"
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
