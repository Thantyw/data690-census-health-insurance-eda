# Reproducible ACS S2701 Slope Diagram
#
# Source:
#   U.S. Census Bureau, American Community Survey (ACS),
#   2015-2019 and 2020-2024 5-Year Estimates,
#   Subject Table S2701,
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
#   results/SlopeDiagram1_R.png
#
# Purpose:
#   Descriptively compare uninsured percentages between two
#   non-overlapping ACS five-year periods.
#
# Important:
#   Statistical significance is not tested.


# ---------------------------------------------------------------------
# File locations
# ---------------------------------------------------------------------

data_file_2019 <- file.path(
  "data",
  "ACSST5Y2019.S2701-Data.csv"
)

data_file_2024 <- file.path(
  "data",
  "ACSST5Y2024.S2701-Data.csv"
)

output_file <- file.path(
  "results",
  "SlopeDiagram1_R.png"
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
# Function to load and validate one ACS snapshot
# ---------------------------------------------------------------------

load_snapshot <- function(file_path, period) {

  if (!file.exists(file_path)) {
    stop(
      paste(
        "Required Census file not found:",
        file_path
      )
    )
  }

  data <- read.csv(
    file_path,
    stringsAsFactors = FALSE,
    check.names = FALSE,
    na.strings = NULL
  )

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
        period,
        "- required S2701 columns are missing:",
        paste(
          missing_columns,
          collapse = ", "
        )
      )
    )
  }


  # -------------------------------------------------------------------
  # Retain state-level records
  # -------------------------------------------------------------------

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


  # -------------------------------------------------------------------
  # Retain selected jurisdictions
  # -------------------------------------------------------------------

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
        period,
        "- expected exactly Delaware,",
        "District of Columbia, Maryland,",
        "Pennsylvania, and Virginia."
      )
    )
  }

  if (anyDuplicated(data$state_fips) > 0) {
    stop(
      paste(
        period,
        "- duplicate state records found."
      )
    )
  }


  # -------------------------------------------------------------------
  # Create readable geography names
  # -------------------------------------------------------------------

  data$geography <- unname(
    states[data$state_fips]
  )


  # -------------------------------------------------------------------
  # Convert estimate to numeric
  # -------------------------------------------------------------------

  data$uninsured_pct <- suppressWarnings(
    as.numeric(
      data[[estimate_column]]
    )
  )


  # -------------------------------------------------------------------
  # Validate estimates
  # -------------------------------------------------------------------

  if (any(is.na(data$uninsured_pct))) {
    stop(
      paste(
        period,
        "- missing or nonnumeric estimates detected.",
        "Review Census annotations."
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
      paste(
        period,
        "- uninsured percentages must",
        "be between 0 and 100."
      )
    )
  }


  # -------------------------------------------------------------------
  # Return required variables
  # -------------------------------------------------------------------

  data[
    ,
    c(
      "state_fips",
      "geography",
      "uninsured_pct"
    )
  ]
}


# ---------------------------------------------------------------------
# Load the two non-overlapping ACS periods
# ---------------------------------------------------------------------

earlier <- load_snapshot(
  data_file_2019,
  "2015-2019"
)

later <- load_snapshot(
  data_file_2024,
  "2020-2024"
)


# ---------------------------------------------------------------------
# Rename estimate columns before merging
# ---------------------------------------------------------------------

names(earlier)[
  names(earlier) == "uninsured_pct"
] <- "uninsured_pct_2015_2019"

names(later)[
  names(later) == "uninsured_pct"
] <- "uninsured_pct_2020_2024"


# ---------------------------------------------------------------------
# Merge the two periods
# ---------------------------------------------------------------------

comparison <- merge(
  earlier,
  later,
  by = c(
    "state_fips",
    "geography"
  ),
  all = FALSE,
  sort = FALSE
)


# ---------------------------------------------------------------------
# Validate matching jurisdictions
# ---------------------------------------------------------------------

if (nrow(comparison) != length(states)) {
  stop(
    paste(
      "The two ACS periods do not contain",
      "the same five jurisdictions."
    )
  )
}

if (anyDuplicated(comparison$state_fips) > 0) {
  stop(
    "Duplicate jurisdictions detected after merging periods."
  )
}


# ---------------------------------------------------------------------
# Calculate descriptive percentage-point change
#
# Change =
# 2020-2024 uninsured percentage
# minus
# 2015-2019 uninsured percentage
# ---------------------------------------------------------------------

comparison$change_percentage_points <- (
  comparison$uninsured_pct_2020_2024 -
  comparison$uninsured_pct_2015_2019
)


# ---------------------------------------------------------------------
# Sort alphabetically for deterministic cross-language comparison
# ---------------------------------------------------------------------

comparison <- comparison[
  order(comparison$geography),
  ,
  drop = FALSE
]

rownames(comparison) <- NULL


# ---------------------------------------------------------------------
# Determine chart range
# ---------------------------------------------------------------------

max_value <- max(
  comparison$uninsured_pct_2015_2019,
  comparison$uninsured_pct_2020_2024
)

upper_limit <- max_value * 1.2


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
  height = 5,
  units = "in",
  res = 180
)


# ---------------------------------------------------------------------
# Chart layout
# ---------------------------------------------------------------------

par(
  mar = c(5.5, 5.5, 4.5, 10),
  family = "sans"
)


# ---------------------------------------------------------------------
# Create empty plotting area
# ---------------------------------------------------------------------

plot(
  NA,
  xlim = c(0.8, 2.2),
  ylim = c(0, upper_limit),
  xaxt = "n",
  xlab = "",
  ylab = "Uninsured population (%)",
  main = paste(
    "Change between non-overlapping five-year periods",
    "Descriptive comparison; significance not tested",
    sep = "\n"
  ),
  bty = "l"
)


# ---------------------------------------------------------------------
# Period labels
# ---------------------------------------------------------------------

axis(
  side = 1,
  at = c(1, 2),
  labels = c(
    "2015-2019",
    "2020-2024"
  )
)


# ---------------------------------------------------------------------
# Colors for the five jurisdictions
# ---------------------------------------------------------------------

line_colors <- c(
  "#1f77b4",
  "#ff7f0e",
  "#2ca02c",
  "#d62728",
  "#9467bd"
)


# ---------------------------------------------------------------------
# Draw one slope for each jurisdiction
# ---------------------------------------------------------------------

for (i in seq_len(nrow(comparison))) {

  earlier_value <- (
    comparison$uninsured_pct_2015_2019[i]
  )

  later_value <- (
    comparison$uninsured_pct_2020_2024[i]
  )

  lines(
    x = c(1, 2),
    y = c(
      earlier_value,
      later_value
    ),
    type = "o",
    pch = 19,
    lwd = 2,
    col = line_colors[i]
  )
}


# ---------------------------------------------------------------------
# Create legend labels with percentage-point changes
# ---------------------------------------------------------------------

legend_labels <- sprintf(
  "%s (%+.1f pp)",
  comparison$geography,
  comparison$change_percentage_points
)


# ---------------------------------------------------------------------
# Legend
# ---------------------------------------------------------------------

legend(
  "topright",
  inset = c(-0.48, 0),
  legend = legend_labels,
  col = line_colors,
  lty = 1,
  lwd = 2,
  pch = 19,
  xpd = TRUE,
  bty = "n",
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
  line = 4.2,
  adj = 0,
  cex = 0.7
)


# ---------------------------------------------------------------------
# Finish image
# ---------------------------------------------------------------------

dev.off()


# ---------------------------------------------------------------------
# Report cross-period values
# ---------------------------------------------------------------------

cat(
  "R slope diagram created successfully.\n"
)

cat(
  paste(
    "Output:",
    output_file,
    "\n\n"
  )
)

print(
  comparison[
    ,
    c(
      "geography",
      "uninsured_pct_2015_2019",
      "uninsured_pct_2020_2024",
      "change_percentage_points"
    )
  ],
  row.names = FALSE
)

cat(
  "\nInterpretation: descriptive comparison only; ",
  "statistical significance was not tested.\n",
  sep = ""
)
