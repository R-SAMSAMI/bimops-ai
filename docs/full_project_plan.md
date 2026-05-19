# Full Project Plan

BIMOps AI should grow from a proof of concept into a small BIM lakehouse product. The goal is to export multiple Revit schedules, land them in Databricks, and create Gold tables that answer meaningful building data questions.

## Phase 1: Current Working Dataset

Already exported:

| Schedule | File | Purpose |
| --- | --- | --- |
| Rooms | `rooms.csv` | Program, area, level, finish, and occupancy analysis |
| Doors | `doors.csv` | Opening counts, fire rating review, door metadata quality |
| Electrical Equipment | `eequipment.csv` | MEP asset inventory and electrical distribution summaries |

Current Gold metrics:

| Gold Table | Meaning |
| --- | --- |
| `gold_element_summary` | Counts BIM records by category |
| `gold_metadata_quality` | Finds missing fields across Revit exports |
| `gold_bim_readiness_score` | Scores each category based on important fields |
| `gold_room_area_by_level` | Total room area by level |
| `gold_program_area_by_occupancy` | Program area by occupancy type |
| `gold_room_finish_completeness` | Finish metadata completeness for rooms |
| `gold_door_fire_rating_summary` | Fire-rated vs non-fire-rated doors |
| `gold_door_fire_rating_by_level` | Door fire ratings by level |
| `gold_electrical_equipment_by_level` | Electrical equipment distribution by level |
| `gold_electrical_equipment_by_part_type` | Electrical asset mix |
| `gold_electrical_distribution_system_summary` | Distribution system usage |
| `gold_electrical_data_completeness` | Electrical data completeness |

## Phase 2: Export More Schedules

Add these schedules next.

| Priority | Revit Category | Suggested File Name | Why It Matters |
| --- | --- | --- | --- |
| 1 | Levels | `levels.csv` | Creates a clean building hierarchy |
| 1 | Spaces | `spaces.csv` | MEP-oriented room/space analysis |
| 1 | Mechanical Equipment | `mechanical_equipment.csv` | Adds HVAC asset inventory |
| 1 | Plumbing Fixtures | `plumbing_fixtures.csv` | Adds plumbing asset inventory |
| 2 | Lighting Fixtures | `lighting_fixtures.csv` | Electrical fixture distribution and counts |
| 2 | Air Terminals | `air_terminals.csv` | HVAC terminal counts by space/level |
| 2 | Windows | `windows.csv` | Envelope and opening analysis |
| 2 | Furniture | `furniture.csv` | Occupancy and space planning inventory |
| 3 | Sheets | `sheets.csv` | Documentation completeness |
| 3 | Views | `views.csv` | Model/documentation organization |
| 3 | Materials | `materials.csv` | Finish/material reporting |

## Recommended Fields

For most element schedules, include:

- Mark
- Family
- Type
- Family and Type
- Level
- Phase Created
- Phase Demolished
- Comments

For assets, also include:

- System Name
- Classification Number
- Classification Title
- Manufacturer
- Model
- Cost

For rooms/spaces, include:

- Number
- Name
- Level
- Area
- Volume
- Department
- Occupancy
- Finish fields

## Final Dashboard Sections

Build the dashboard around four sections:

1. **Model Inventory**
   - Element counts by category
   - Asset counts by discipline
   - Elements by level

2. **Building Program**
   - Room area by level
   - Program area by occupancy
   - Room count by level

3. **Model Quality**
   - BIM readiness score by category
   - Missing metadata by field
   - Finish completeness

4. **Operations Readiness**
   - Asset inventory by system/type
   - Equipment by level
   - Fire-rated door summary
   - Electrical distribution systems

## Project Story

The final project demonstrates how exported BIM metadata can be transformed into a Databricks lakehouse and used for:

- Model health checks
- Asset inventory
- Program analytics
- Metadata completeness review
- Operations handoff readiness
- AI-ready building data
