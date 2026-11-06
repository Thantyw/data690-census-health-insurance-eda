# Workflow validation

Official 2019 and 2024 S2701 JSON metadata were retrieved and parsed. The selected overall, age, and sex variable labels match across these vintages. Matching labels alone do not establish complete statistical comparability.

The loader, missing-value conversion, known descriptive period difference, count identities, output tables, and six chart-generation paths were checked using temporary artificial inputs. No artificial estimates or charts are included in this package. Notebook code cells were compiled. The notebook has not been tested in the user's Databricks workspace.

See the actual-data update below and results/ for calculated findings.

Actual-data update: The authenticated Census API route and full Python pipeline completed successfully for both vintages. Sixty selected summary records and ten overall jurisdiction-period records were validated. All selected quality checks passed, and six chart files were produced. The GitHub workflow and user Databricks workspace remain unverified.
