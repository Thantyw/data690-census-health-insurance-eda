# Reproducible ACS S2701 Accessible Table
#
# Source:
#   U.S. Census Bureau, American Community Survey (ACS),
#   2020-2024 5-Year Estimates,
#   Subject Table S2701,
#   Selected Characteristics of Health Insurance Coverage
#   in the United States.
#
# Universe:
#   Civilian noninstitutionalized population.
#
# Measure:
#   Percentage without health insurance coverage and
#   published 90% margin of error.
#
# Geographies:
#   Delaware, District of Columbia, Maryland,
#   Pennsylvania, and Virginia.
#
# Outputs:
#   results/Table1_R.csv
#   results/Table1_R.html
#
# Purpose:
#   Provide precise Census estimates and uncertainty in
#   machine-readable and accessible tabular formats.
#
# Missing or unavailable Census values are not replaced with zero.


# ---------------------------------------------------------------------
# File locations
# ---------------------------------------------------------------------

data_file <- file.path(
  "data",
  "ACSST5Y2024.S2701-Data.csv"
)

csv_output <- file.path(
  "results",
  "Table1_R.csv"
)

html_output <- file.path(
  "results",
  "Table1_R.html"
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
# Validate input file
# ---------------------------------------------------------------------

if (!file.exists(data_file)) {
  stop(
    paste(
      "Required Census file not found:",
      data_file
    )
  )
}


# ---------------------------------------------------------------------
# Read Census snapshot
# ---------------------------------------------------------------------

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
      paste(
        missing_columns,
        collapse = ", "
      )
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
# Retain selected jurisdictions
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

data$Geography <- unname(
  states[data$state_fips]
)


# ---------------------------------------------------------------------
# Convert estimate and MOE to numeric
# ---------------------------------------------------------------------

data$uninsured_pct <- suppressWarnings(
  as.numeric(
    data[[estimate_column]]
  )
)

data$moe90 <- suppressWarnings(
  as.numeric(
    data[[moe_column]]
  )
)


# ---------------------------------------------------------------------
# Validate numeric values
# ---------------------------------------------------------------------

if (
  any(is.na(data$uninsured_pct)) ||
  any(is.na(data$moe90))
) {
  stop(
    paste(
      "Missing or nonnumeric Census estimates or margins",
      "of error detected. Review Census annotations."
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

if (any(data$moe90 < 0)) {
  stop(
    "Margins of error must not be negative."
  )
}


# ---------------------------------------------------------------------
# Prepare final table
# ---------------------------------------------------------------------

table_data <- data.frame(
  Geography = data$Geography,
  `Uninsured population (%)` = data$uninsured_pct,
  `90% margin of error (pp)` = data$moe90,
  check.names = FALSE,
  stringsAsFactors = FALSE
)


# ---------------------------------------------------------------------
# Sort by estimate and then geography
# ---------------------------------------------------------------------

table_data <- table_data[
  order(
    table_data[["Uninsured population (%)"]],
    table_data[["Geography"]]
  ),
  ,
  drop = FALSE
]

rownames(table_data) <- NULL


# ---------------------------------------------------------------------
# Create output directory
# ---------------------------------------------------------------------

dir.create(
  dirname(csv_output),
  recursive = TRUE,
  showWarnings = FALSE
)


# ---------------------------------------------------------------------
# Save machine-readable CSV
# ---------------------------------------------------------------------

write.csv(
  table_data,
  csv_output,
  row.names = FALSE,
  quote = TRUE
)


# ---------------------------------------------------------------------
# HTML escaping helper
# ---------------------------------------------------------------------

html_escape <- function(x) {

  x <- gsub(
    "&",
    "&amp;",
    x,
    fixed = TRUE
  )

  x <- gsub(
    "<",
    "&lt;",
    x,
    fixed = TRUE
  )

  x <- gsub(
    ">",
    "&gt;",
    x,
    fixed = TRUE
  )

  x <- gsub(
    "\"",
    "&quot;",
    x,
    fixed = TRUE
  )

  x
}


# ---------------------------------------------------------------------
# Build accessible HTML rows
# ---------------------------------------------------------------------

html_rows <- character(
  nrow(table_data)
)

for (i in seq_len(nrow(table_data))) {

  geography <- html_escape(
    table_data$Geography[i]
  )

  estimate <- sprintf(
    "%.1f%%",
    table_data[
      ["Uninsured population (%)"]
    ][i]
  )

  moe <- sprintf(
    "±%.1f",
    table_data[
      ["90% margin of error (pp)"]
    ][i]
  )

  html_rows[i] <- paste0(
    "        <tr>\n",
    "            <th scope=\"row\">",
    geography,
    "</th>\n",
    "            <td>",
    estimate,
    "</td>\n",
    "            <td>",
    moe,
    "</td>\n",
    "        </tr>"
  )
}


# ---------------------------------------------------------------------
# Build complete accessible HTML document
# ---------------------------------------------------------------------

html_document <- paste0(
'<!DOCTYPE html>
<html lang="en">

<head>

    <meta charset="utf-8">

    <meta name="viewport"
          content="width=device-width, initial-scale=1">

    <title>
        ACS S2701 Uninsured Population Estimates
    </title>

    <style>

        body {
            font-family: Arial, Helvetica, sans-serif;
            margin: 2rem;
            line-height: 1.5;
            color: #222;
        }

        table {
            border-collapse: collapse;
            width: 100%;
            max-width: 850px;
        }

        caption {
            text-align: left;
            font-weight: bold;
            font-size: 1.15rem;
            margin-bottom: 0.75rem;
        }

        th,
        td {
            border-bottom: 1px solid #cccccc;
            padding: 0.65rem;
            text-align: left;
        }

        thead th {
            border-bottom: 2px solid #555555;
        }

        tbody th {
            font-weight: normal;
        }

        .note {
            max-width: 850px;
            margin-top: 1rem;
            font-size: 0.9rem;
        }

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

            <th scope="col">
                Geography
            </th>

            <th scope="col">
                Uninsured population (%)
            </th>

            <th scope="col">
                90% margin of error (percentage points)
            </th>

        </tr>

    </thead>

    <tbody>
',
paste(
  html_rows,
  collapse = "\n"
),
'

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
'
)


# ---------------------------------------------------------------------
# Save HTML
# ---------------------------------------------------------------------

writeLines(
  html_document,
  html_output,
  useBytes = TRUE
)


# ---------------------------------------------------------------------
# Report results
# ---------------------------------------------------------------------

cat(
  "Accessible R Census table created successfully.\n"
)

cat(
  paste(
    "CSV output:",
    csv_output,
    "\n"
  )
)

cat(
  paste(
    "HTML output:",
    html_output,
    "\n\n"
  )
)

print(
  table_data,
  row.names = FALSE
)
