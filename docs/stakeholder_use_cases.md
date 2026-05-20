# Stakeholder Use Cases

BIMOps AI turns Revit schedule exports into Gold tables that can support dashboards, SQL analysis, and natural-language questions for different AEC stakeholders.

## BIM Manager

Needs:

- Understand model completeness.
- Identify categories that need metadata cleanup.
- Track readiness for coordination or handoff.

Useful questions:

- Which BIM categories have the weakest readiness scores?
- Which fields are missing most often?
- Which categories are missing `mark`, `level`, or `family_and_type`?

Useful Gold tables:

- `gold_bim_readiness_score`
- `gold_key_field_completeness`
- `gold_metadata_quality`
- `gold_model_inventory_by_category`

## Designer / Design Technologist

Needs:

- Understand program distribution.
- Review room and occupancy summaries.
- Explore building elements without manually inspecting every schedule.

Useful questions:

- Which level has the most room area?
- Which occupancy type uses the most area?
- How are walls distributed by function?
- How many doors and windows exist by level?

Useful Gold tables:

- `gold_room_area_by_level`
- `gold_program_area_by_occupancy`
- `gold_wall_area_by_function`
- `gold_door_count_by_level`
- `gold_window_count_by_level`

## Project Manager

Needs:

- Understand project data scale.
- See discipline-level model inventory.
- Identify areas that may need cleanup before downstream use.

Useful questions:

- Which discipline has the most BIM records?
- Which categories dominate the model?
- Which categories may require the most metadata cleanup?

Useful Gold tables:

- `gold_model_inventory_by_discipline`
- `gold_model_inventory_by_category`
- `gold_bim_readiness_score`

## MEP / Operations Stakeholder

Needs:

- Review equipment and fixture inventory.
- Identify assets missing identity or system metadata.
- Prepare data for handoff and facilities workflows.

Useful questions:

- Which MEP asset categories have the most records?
- Which level has the most air terminals?
- Which assets are missing mark or family/type values?

Useful Gold tables:

- `gold_mep_inventory_summary`
- `gold_air_terminals_by_level`
- `gold_electrical_equipment_by_level`
- `gold_asset_identity_readiness`

## Structural Team

Needs:

- Summarize structural systems.
- Understand framing, columns, and foundation distributions.
- Review material and usage summaries.

Useful questions:

- Which structural category has the most records?
- Which framing materials appear most often?
- What foundation usage types are represented?

Useful Gold tables:

- `gold_structural_inventory_summary`
- `gold_structural_framing_by_material`
- `gold_structural_foundations_by_usage`

## Facilities / Owner Handoff Team

Needs:

- Identify assets and metadata needed for operations.
- Understand gaps before handoff.
- Convert model data into operational intelligence.

Useful questions:

- Which assets are missing mark values?
- Which equipment records are missing manufacturer or model?
- Which categories are least ready for handoff?

Useful Gold tables:

- `gold_asset_identity_readiness`
- `gold_key_field_completeness`
- `gold_bim_readiness_score`

## Data / AI Team

Needs:

- Build reliable data products from model metadata.
- Govern Gold tables for downstream analytics.
- Connect dashboards, SQL, and LLM-based query tools.

Useful questions:

- Which Gold tables support natural-language querying?
- Which fields should be included in a semantic layer?
- Which categories have enough metadata to support AI workflows?

Useful Gold tables:

- `gold_model_inventory_by_category`
- `gold_bim_readiness_score`
- `gold_key_field_completeness`
- `gold_metadata_quality`

