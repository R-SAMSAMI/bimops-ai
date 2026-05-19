# Dashboard Spec

## Dashboard Name

BIMOps AI Lakehouse Dashboard

## 1. Model Inventory

Purpose: show the full scope of BIM data extracted into the lakehouse.

Recommended visuals:

| Visual | Gold Table | Chart |
| --- | --- | --- |
| Records by discipline | `gold_model_inventory_by_discipline` | Bar chart |
| Records by category | `gold_model_inventory_by_category` | Bar chart |
| Top element categories | `gold_element_summary` | Bar chart |

Key message:

The project integrates architectural, electrical, mechanical, and structural Revit schedule exports into a unified lakehouse.

## 2. Building Program

Purpose: show how the building is organized by area, level, and program.

Recommended visuals:

| Visual | Gold Table | Chart |
| --- | --- | --- |
| Room area by level | `gold_room_area_by_level` | Bar chart |
| Program area by occupancy | `gold_program_area_by_occupancy` | Bar chart or treemap |
| Finish completeness | `gold_room_finish_completeness` | Bar chart |

Key message:

Rooms become analyzable program data, not just model geometry.

## 3. Envelope and Openings

Purpose: summarize doors, windows, walls, and floors.

Recommended visuals:

| Visual | Gold Table | Chart |
| --- | --- | --- |
| Door count by level | `gold_door_count_by_level` | Bar chart |
| Fire-rated door summary | `gold_door_fire_rating_summary` | Donut or bar chart |
| Window count by level | `gold_window_count_by_level` | Bar chart |
| Wall area by function | `gold_wall_area_by_function` | Bar chart |
| Wall count by type | `gold_wall_count_by_type` | Table |

Key message:

The lakehouse can surface building-envelope and life-safety metadata from design models.

## 4. MEP Asset Inventory

Purpose: show operational asset counts and system distribution.

Recommended visuals:

| Visual | Gold Table | Chart |
| --- | --- | --- |
| MEP inventory summary | `gold_mep_inventory_summary` | Bar chart |
| Electrical equipment by level | `gold_electrical_equipment_by_level` | Bar chart |
| Lighting fixtures by level | `gold_lighting_fixtures_by_level` | Bar chart |
| Air terminals by level | `gold_air_terminals_by_level` | Bar chart |
| Duct fittings by level | `gold_duct_fittings_by_level` | Bar chart |
| Mechanical equipment by system | `gold_mechanical_equipment_by_system` | Table |

Key message:

MEP categories become an asset inventory that can support operations handoff.

## 5. Structural System

Purpose: summarize structural model content by type, material, and level.

Recommended visuals:

| Visual | Gold Table | Chart |
| --- | --- | --- |
| Structural inventory summary | `gold_structural_inventory_summary` | Bar chart |
| Structural framing by family/type | `gold_structural_framing_by_family_type` | Bar chart |
| Structural framing by material | `gold_structural_framing_by_material` | Bar chart |
| Structural volume by material | `gold_structural_framing_volume_by_material` | Bar chart |
| Foundations by usage | `gold_structural_foundations_by_usage` | Bar chart |

Key message:

Structural quantities and material metadata can be profiled from Revit exports.

## 6. BIM Data Quality

Purpose: show readiness for analytics, operations, and AI querying.

Recommended visuals:

| Visual | Gold Table | Chart |
| --- | --- | --- |
| BIM readiness by category | `gold_bim_readiness_score` | Bar chart |
| Key field completeness | `gold_key_field_completeness` | Heatmap/table |
| Asset identity readiness | `gold_asset_identity_readiness` | Bar chart |
| Top missing metadata fields | `gold_metadata_quality` | Table |

Key message:

The lakehouse does not only store BIM data; it measures whether that data is complete enough to trust.

## Suggested Dashboard Story

1. Start with total records by discipline to show scale.
2. Move into building program to show architectural meaning.
3. Show openings and envelope data for design/model insight.
4. Show MEP and structural summaries for cross-discipline depth.
5. End with BIM readiness and missing metadata to show data-specialist value.
