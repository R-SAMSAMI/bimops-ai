# Databricks Quickstart

This guide moves the local BIMOps AI prototype into Databricks.

## 1. Upload Revit schedule exports

Upload these local files:

```text
exports/revit_schedules/rooms.csv
exports/revit_schedules/doors.csv
exports/revit_schedules/eequipment.csv
```

Target folder in Databricks:

```text
/FileStore/bimops/revit_schedules/
```

## 2. Import the notebook

Import this file as a Databricks notebook:

```text
notebooks/databricks_bimops_starter.py
```

## 3. Run the notebook

The notebook creates a database:

```sql
bimops_ai
```

It then writes these Delta tables:

```text
bronze_rooms
bronze_doors
bronze_electrical_equipment
silver_rooms
silver_doors
silver_electrical_equipment
gold_element_summary
gold_metadata_quality
gold_bim_readiness_score
gold_room_area_by_level
gold_program_area_by_occupancy
gold_room_finish_completeness
gold_door_count_by_level
gold_door_count_by_function
gold_door_fire_rating_summary
gold_door_fire_rating_by_level
gold_electrical_equipment_by_level
gold_electrical_equipment_by_part_type
gold_electrical_distribution_system_summary
gold_electrical_data_completeness
```

## 4. Start with these SQL queries

```sql
SELECT * FROM gold_element_summary;
```

```sql
SELECT element_category, field_name, missing_count, total_records, missing_rate
FROM gold_metadata_quality
WHERE missing_rate > 0.25
ORDER BY missing_rate DESC;
```

```sql
SELECT *
FROM gold_room_area_by_level
ORDER BY total_room_area_sf DESC;
```

```sql
SELECT *
FROM gold_bim_readiness_score
ORDER BY bim_readiness_score DESC;
```

```sql
SELECT *
FROM gold_program_area_by_occupancy
ORDER BY total_room_area_sf DESC;
```

```sql
SELECT *
FROM gold_door_fire_rating_summary;
```

## 5. Dashboard ideas

Create Databricks dashboard visuals for:

- Element count by category
- Room area by level
- Program area by occupancy
- BIM readiness score by category
- Missing metadata by category and field
- Electrical equipment count by level
- Door fire rating summary

These visuals are the first version of the BIMOps AI lakehouse dashboard.
