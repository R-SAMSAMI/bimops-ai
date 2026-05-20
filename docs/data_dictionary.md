# Data Dictionary

This dictionary defines the main BIMOps AI Gold tables used for dashboarding, stakeholder reporting, and natural-language querying.

## Core Inventory

| Table | Purpose | Example Question |
| --- | --- | --- |
| `gold_model_inventory_by_discipline` | BIM record counts by architecture, electrical, mechanical, and structural disciplines. | Which discipline has the most model records? |
| `gold_model_inventory_by_category` | BIM record counts by normalized element category. | Which Revit categories dominate the model? |
| `gold_element_summary` | General category-level row and column summary. | How many records were extracted from each schedule? |

## Building Program

| Table | Purpose | Example Question |
| --- | --- | --- |
| `gold_room_area_by_level` | Room area aggregated by level. | Which level has the most room area? |
| `gold_program_area_by_occupancy` | Room area and room count by occupancy/program. | Which occupancy type takes the most area? |
| `gold_room_finish_completeness` | Completion rate for room finish fields. | Which finish metadata is missing most often? |

## Envelope And Life Safety

| Table | Purpose | Example Question |
| --- | --- | --- |
| `gold_door_count_by_level` | Door counts by level. | Which level has the most doors? |
| `gold_door_fire_rating_summary` | Fire-rated vs non-fire-rated door counts. | How many doors are fire-rated? |
| `gold_door_fire_rating_by_level` | Fire rating counts by level. | Where are fire-rated doors concentrated? |
| `gold_window_count_by_level` | Window counts by level. | Which level has the most windows? |
| `gold_wall_area_by_function` | Wall area by function. | How much exterior vs interior wall area exists? |
| `gold_wall_count_by_type` | Wall counts by type. | Which wall types appear most often? |

## MEP Inventory

| Table | Purpose | Example Question |
| --- | --- | --- |
| `gold_mep_inventory_summary` | MEP record counts by category. | Which MEP category has the most assets? |
| `gold_electrical_equipment_by_level` | Electrical equipment by level. | Where is electrical equipment concentrated? |
| `gold_lighting_fixtures_by_level` | Lighting fixtures by level. | Which level has the most lighting fixtures? |
| `gold_air_terminals_by_level` | Air terminals by level. | Which level has the most air terminals? |
| `gold_duct_fittings_by_level` | Duct fittings by level. | Where are duct fittings concentrated? |
| `gold_mechanical_equipment_by_system` | Mechanical equipment by system. | Which mechanical systems have equipment records? |

## Structural System

| Table | Purpose | Example Question |
| --- | --- | --- |
| `gold_structural_inventory_summary` | Structural records by category. | Which structural category dominates the model? |
| `gold_structural_framing_by_material` | Framing counts by material. | Which framing material appears most often? |
| `gold_structural_framing_volume_by_material` | Framing volume by material. | Which material accounts for the most framing volume? |
| `gold_structural_foundations_by_usage` | Foundation counts by structural usage. | What foundation usage types are represented? |

## BIM Data Quality

| Table | Purpose | Example Question |
| --- | --- | --- |
| `gold_bim_readiness_score` | Category-level score based on important metadata field completion. | Which categories are least ready for handoff? |
| `gold_key_field_completeness` | Missing rates for key fields such as mark, level, type, classification, manufacturer, model, and comments. | Which key fields are missing most often? |
| `gold_asset_identity_readiness` | Asset identity completion based on mark and family/type availability. | Which asset categories need better IDs? |
| `gold_metadata_quality` | Broad missing-rate table across categories and fields. | What are the biggest metadata gaps? |

## Metric Definitions

| Metric | Definition |
| --- | --- |
| `record_count` | Number of rows extracted or summarized. |
| `missing_rate` | Percent of records where a field is blank or missing. |
| `bim_readiness_score` | `1 - missing important values / total important values`. |
| `asset_id_completion_rate` | Completion score for asset identity fields such as `mark` and `family_and_type`. |
| `total_room_area_sf` | Numeric room area extracted from Revit area strings and aggregated in square feet. |
| `volume_cf` | Numeric structural volume extracted from Revit volume strings and aggregated in cubic feet. |

