# Data Governance

BIMOps AI treats Revit schedule exports as governed analytical data rather than one-off CSV files.

## Governance Principles

| Principle | Implementation |
| --- | --- |
| Source traceability | Bronze and Silver tables include `source_file` and `source_system`. |
| Layered transformation | Raw, cleaned, and analytics-ready outputs are separated into Bronze, Silver, and Gold layers. |
| Plain-language definitions | Gold tables are documented in the data dictionary. |
| Quality visibility | Missing metadata rates and readiness scores are surfaced in Gold tables and dashboards. |
| Safe AI querying | The AI query layer restricts generated SQL to read-only `SELECT` statements over Gold tables. |
| Stakeholder usability | Metrics are organized around BIM managers, designers, project managers, facilities teams, and data teams. |

## Source Data

| Source | Description |
| --- | --- |
| Source model | Autodesk Snowdon Towers Revit sample project |
| Source documentation | https://help.autodesk.com/view/RVT/2024/ENU/?guid=GUID-61EF2F22-3A1F-4317-B925-1E85F138BE88 |
| Source format | Revit schedule exports as CSV |
| Source system label | `revit_schedule_export` |
| Included disciplines | Architecture, electrical, mechanical, structural |

## Layer Governance

| Layer | Purpose | Recommended Users |
| --- | --- | --- |
| Bronze | Preserve raw Revit schedule records with source tracking. | Data engineers, auditors, troubleshooting |
| Silver | Normalize columns, categories, duplicates, and element labels. | Data analysts, BIM analytics team |
| Gold | Produce dashboard-ready metrics and stakeholder-facing tables. | BIM managers, project teams, owners, AI query layer |

## Ownership Model

| Data Area | Likely Owner | Downstream Users |
| --- | --- | --- |
| Rooms, doors, windows, walls, floors | Architecture / BIM team | Designers, BIM managers, project managers |
| Electrical equipment and fixtures | Electrical / MEP team | MEP coordinators, operations teams, facilities teams |
| Air terminals, duct fittings, mechanical equipment | Mechanical / MEP team | MEP coordinators, operations teams, facilities teams |
| Framing, columns, foundations | Structural team | Structural engineers, BIM managers, project managers |
| Gold quality metrics | Data / BIM analytics team | BIM managers, digital delivery teams, project leadership |

## Quality Rules

| Rule | Applies To | Why It Matters |
| --- | --- | --- |
| `level` should not be missing | Most physical elements | Supports location-based analysis. |
| `mark` should not be missing | Asset-like elements | Supports asset identity and operations handoff. |
| `family_and_type` should not be missing | Most model elements | Supports category/type analysis. |
| `classification_number` should be populated where available | Elements using classification systems | Supports standardized reporting. |
| `manufacturer` and `model` should be populated for operational assets | Equipment and fixtures | Supports facilities and lifecycle use cases. |
| `area` should be populated for rooms and areas | Rooms and program data | Supports program analytics. |
| `fire_rating` should be reviewed for doors | Door schedules | Supports life-safety metadata review. |

## Refresh Cadence

For a real project, exports could be refreshed:

- At major design milestones
- Before BIM coordination reviews
- Before owner handoff
- After major model cleanup cycles
- On a recurring cadence if automated Revit extraction is added

## Known Limitations

- The workflow starts from exported schedules, not direct Revit API extraction.
- Some parameters are blank because the sample model was not authored for operations handoff.
- CSV exports may contain formatting quirks, units, or text fields that require parsing.
- The AI query layer should be treated as assisted analytics, not an authoritative substitute for domain review.

## AI Query Governance

The OpenAI-powered Databricks notebook:

- Receives only curated Gold table context.
- Allows only `SELECT` statements.
- Blocks write/destructive keywords.
- Requires queries to target Gold tables.
- Summarizes Databricks query results for AEC stakeholders.

