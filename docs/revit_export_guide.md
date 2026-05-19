# Revit Schedule Export Guide

This project starts with schedule exports because they are the simplest reliable bridge from Revit to a data pipeline.

## Recommended sample model

Use one of the local Autodesk sample files in this folder, starting with:

- `Snowdon Towers Sample Architectural.rvt`

## Export a Rooms schedule

1. Open the architectural model in Revit.
2. Go to `View > Schedules > Schedule/Quantities`.
3. Choose `Rooms`.
4. Add these fields if available:
   - Number
   - Name
   - Level
   - Area
   - Department
5. Save the schedule view.
6. Export with `File > Export > Reports > Schedule`.
7. Save as `exports/revit_schedules/rooms.csv`.

## Export a Doors schedule

1. Go to `View > Schedules > Schedule/Quantities`.
2. Choose `Doors`.
3. Add these fields if available:
   - Mark
   - Level
   - Type
   - Width
   - Height
   - Fire Rating
   - Room Name
4. Export as `exports/revit_schedules/doors.csv`.

## Export an Equipment schedule

For MEP files, use mechanical, electrical, plumbing, or specialty equipment depending on what the model contains.

Suggested fields:

- Mark
- Family and Type
- Level
- System Name
- Space Name
- Comments

Export as `exports/revit_schedules/equipment.csv`.

## Tips

- Keep the exported file names simple and lowercase.
- If Revit exports tab-delimited text instead of CSV, save it with a `.csv` extension anyway; the Python pipeline will try to detect the delimiter.
- Do not worry if some columns are missing. The pipeline is intentionally forgiving for a beginner project.
