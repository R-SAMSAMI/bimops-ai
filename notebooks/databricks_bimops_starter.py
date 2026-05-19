# Databricks notebook source
# MAGIC %md
# MAGIC # BIMOps AI: Revit to Databricks Lakehouse
# MAGIC
# MAGIC This notebook reads Revit schedule exports from a Unity Catalog volume and builds a full medallion lakehouse:
# MAGIC
# MAGIC - Bronze: raw Revit schedule tables
# MAGIC - Silver: cleaned BIM element tables
# MAGIC - Gold: dashboard-ready model inventory, program, MEP, structural, openings, and BIM quality tables

# COMMAND ----------

import csv
import re
from pathlib import Path

import pandas as pd

DATABASE_NAME = "bimops_ai"
RAW_VOLUME_DIR = "/Volumes/workspace/default/bimops_raw"
RAW_LOCAL_DIR = Path(RAW_VOLUME_DIR)

spark.sql(f"CREATE DATABASE IF NOT EXISTS {DATABASE_NAME}")
spark.sql(f"USE {DATABASE_NAME}")

# COMMAND ----------

def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def normalize_table_name(raw_name: str) -> str:
    table_name = slugify(raw_name)
    aliases = {
        "airterminals": "air_terminals",
        "datadevices": "data_devices",
        "ductfittings": "duct_fittings",
        "eequipment": "electrical_equipment",
        "efixtures": "electrical_fixtures",
        "lfixtures": "lighting_fixtures",
        "mequipment": "mechanical_equipment",
        "scolumns": "structural_columns",
        "sfoundations": "structural_foundations",
        "sframings": "structural_framing",
        "window": "windows",
    }
    return aliases.get(table_name, table_name)


def discipline_for_category(category: str) -> str:
    discipline_map = {
        "areas": "architecture",
        "doors": "architecture",
        "floors": "architecture",
        "levels": "architecture",
        "rooms": "architecture",
        "walls": "architecture",
        "windows": "architecture",
        "data_devices": "electrical",
        "electrical_equipment": "electrical",
        "electrical_fixtures": "electrical",
        "lighting_fixtures": "electrical",
        "air_terminals": "mechanical",
        "duct_fittings": "mechanical",
        "mechanical_equipment": "mechanical",
        "structural_columns": "structural",
        "structural_foundations": "structural",
        "structural_framing": "structural",
    }
    return discipline_map.get(category, "other")


def parse_first_number(value):
    match = re.search(r"-?\d+(?:\.\d+)?", str(value))
    return float(match.group(0)) if match else None


def missing_mask(series: pd.Series) -> pd.Series:
    return series.isna() | (series.astype(str).str.strip() == "")


def read_raw_rows(path: Path, delimiter: str) -> list[list[str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.reader(handle, delimiter=delimiter))


def detect_header_row(rows: list[list[str]]) -> int | None:
    for index, row in enumerate(rows):
        values = [str(value).strip().lower() for value in row if str(value).strip()]
        if len(values) < 2:
            continue
        if any(value in values for value in ["level", "name", "mark", "family", "family and type", "type"]):
            return int(index)
    return None


def repair_row_width(row: list[str], headers: list[str]) -> list[str]:
    if len(row) == len(headers):
        return row
    if len(row) < len(headers):
        return row + [""] * (len(headers) - len(row))

    extra_count = len(row) - len(headers)
    merge_index = headers.index("Circuit Number") if "Circuit Number" in headers else len(headers) - 1
    repaired = row[:merge_index]
    repaired.append(",".join(row[merge_index : merge_index + extra_count + 1]))
    repaired.extend(row[merge_index + extra_count + 1 :])
    return repaired[: len(headers)]


def read_revit_schedule(path: Path) -> pd.DataFrame:
    for delimiter in [",", "\t"]:
        rows = read_raw_rows(path, delimiter)
        header_row = detect_header_row(rows[:5])
        if header_row is None:
            continue

        headers = [str(value).strip() for value in rows[header_row]]
        data_rows = []
        for row in rows[header_row + 1 :]:
            if not any(str(value).strip() for value in row):
                continue
            data_rows.append(repair_row_width(row, headers))
        return pd.DataFrame(data_rows, columns=headers).dropna(how="all")

    return pd.read_csv(path).dropna(how="all")


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    clean = df.copy()
    clean.columns = [slugify(str(column)) for column in clean.columns]
    return clean


def to_spark(df: pd.DataFrame):
    clean = df.copy()
    for column in clean.columns:
        if clean[column].dtype == "object":
            clean[column] = clean[column].fillna("").astype(str)
    return spark.createDataFrame(clean)


def write_delta_table(df: pd.DataFrame, table_name: str) -> None:
    to_spark(df).write.mode("overwrite").option("overwriteSchema", "true").format("delta").saveAsTable(table_name)


def write_group_count(df: pd.DataFrame, group_columns: list[str], output: dict[str, pd.DataFrame], output_name: str, count_name: str = "record_count") -> None:
    available_columns = [column for column in group_columns if column in df.columns]
    if not available_columns:
        return
    output[output_name] = (
        df.groupby(available_columns, dropna=False)
        .size()
        .reset_index(name=count_name)
        .sort_values(count_name, ascending=False)
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Bronze and Silver

# COMMAND ----------

bronze_tables = {}
silver_tables = {}

for path in sorted(RAW_LOCAL_DIR.glob("*.csv")):
    table_name = normalize_table_name(path.stem)
    raw = read_revit_schedule(path)
    raw = normalize_columns(raw)
    raw["source_file"] = path.name
    raw["source_system"] = "revit_schedule_export"

    bronze_tables[table_name] = raw
    write_delta_table(raw, f"bronze_{table_name}")

    silver = raw.drop_duplicates().copy()
    silver["element_category"] = table_name
    silver_tables[table_name] = silver
    write_delta_table(silver, f"silver_{table_name}")

display(spark.sql("SHOW TABLES"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold: Core Inventory and Quality

# COMMAND ----------

gold_tables = {}

element_summary = pd.DataFrame(
    [
        {
            "element_category": category,
            "record_count": len(df),
            "column_count": len(df.columns),
        }
        for category, df in silver_tables.items()
    ]
).sort_values("record_count", ascending=False)
gold_tables["element_summary"] = element_summary

inventory = pd.DataFrame(
    [
        {
            "discipline": discipline_for_category(category),
            "element_category": category,
            "record_count": len(df),
            "column_count": len(df.columns),
        }
        for category, df in silver_tables.items()
    ]
)
gold_tables["model_inventory_by_category"] = inventory.sort_values(["discipline", "record_count"], ascending=[True, False])
gold_tables["model_inventory_by_discipline"] = (
    inventory.groupby("discipline", dropna=False)["record_count"]
    .sum()
    .reset_index()
    .sort_values("record_count", ascending=False)
)

quality_rows = []
for category, df in silver_tables.items():
    for column in df.columns:
        missing_count = int(missing_mask(df[column]).sum())
        quality_rows.append(
            {
                "discipline": discipline_for_category(category),
                "element_category": category,
                "field_name": column,
                "missing_count": missing_count,
                "total_records": len(df),
                "missing_rate": round(missing_count / len(df), 4) if len(df) else 0,
            }
        )
gold_tables["metadata_quality"] = pd.DataFrame(quality_rows)

tracked_fields = ["mark", "level", "type", "family_and_type", "classification_number", "manufacturer", "model", "comments"]
key_rows = []
for category, df in silver_tables.items():
    for field in tracked_fields:
        if field in df.columns:
            missing_count = int(missing_mask(df[field]).sum())
            key_rows.append(
                {
                    "discipline": discipline_for_category(category),
                    "element_category": category,
                    "field_name": field,
                    "missing_count": missing_count,
                    "total_records": len(df),
                    "missing_rate": round(missing_count / len(df), 4) if len(df) else 0,
                }
            )
gold_tables["key_field_completeness"] = pd.DataFrame(key_rows)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold: BIM Readiness and Asset Identity

# COMMAND ----------

important_fields = {
    "air_terminals": ["family_and_type", "level", "system_name", "flow", "mark"],
    "data_devices": ["mark", "family_and_type", "level", "comments"],
    "doors": ["type", "level", "family", "fire_rating", "width", "height", "material", "frame_material"],
    "duct_fittings": ["family_and_type", "level", "system_name", "size"],
    "electrical_equipment": ["mark", "family_and_type", "level", "location", "distribution_system", "electrical_data", "part_type"],
    "electrical_fixtures": ["mark", "family_and_type", "level", "panel", "circuit_number"],
    "lighting_fixtures": ["mark", "family_and_type", "level", "panel", "circuit_number"],
    "mechanical_equipment": ["mark", "family_and_type", "level", "system_name", "manufacturer", "model"],
    "rooms": ["number", "name", "level", "area", "occupancy", "floor_finish", "wall_finish", "ceiling_finish"],
    "structural_columns": ["mark", "family_and_type", "level", "base_level", "top_level", "structural_material"],
    "structural_foundations": ["mark", "family_and_type", "level", "structural_material", "volume"],
    "structural_framing": ["mark", "family_and_type", "level", "structural_material", "structural_usage", "cut_length"],
    "walls": ["type", "family_and_type", "base_constraint", "top_constraint", "function", "structural_material", "area"],
    "windows": ["type", "family_and_type", "level", "width", "height", "material"],
}

readiness_rows = []
for category, df in silver_tables.items():
    fields = [field for field in important_fields.get(category, []) if field in df.columns]
    if not fields:
        continue
    missing_cells = sum(int(missing_mask(df[field]).sum()) for field in fields)
    total_cells = len(df) * len(fields)
    readiness_rows.append(
        {
            "discipline": discipline_for_category(category),
            "element_category": category,
            "important_field_count": len(fields),
            "total_records": len(df),
            "missing_important_values": missing_cells,
            "bim_readiness_score": round(1 - (missing_cells / total_cells), 4) if total_cells else 0,
        }
    )
gold_tables["bim_readiness_score"] = pd.DataFrame(readiness_rows).sort_values("bim_readiness_score", ascending=False)

asset_rows = []
for category, df in silver_tables.items():
    if discipline_for_category(category) not in {"electrical", "mechanical", "structural"}:
        continue
    missing_mark = int(missing_mask(df["mark"]).sum()) if "mark" in df.columns else len(df)
    missing_type = int(missing_mask(df["family_and_type"]).sum()) if "family_and_type" in df.columns else len(df)
    asset_rows.append(
        {
            "discipline": discipline_for_category(category),
            "element_category": category,
            "total_assets": len(df),
            "missing_mark": missing_mark,
            "missing_family_and_type": missing_type,
            "asset_id_completion_rate": round(1 - ((missing_mark + missing_type) / (len(df) * 2)), 4) if len(df) else 0,
        }
    )
gold_tables["asset_identity_readiness"] = pd.DataFrame(asset_rows)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold: Building Program, Openings, and Envelope

# COMMAND ----------

if "rooms" in silver_tables:
    rooms = silver_tables["rooms"].copy()
    if "area" in rooms.columns:
        rooms["area_sf"] = rooms["area"].apply(parse_first_number)
    if {"level", "area_sf"}.issubset(rooms.columns):
        gold_tables["room_area_by_level"] = (
            rooms.groupby("level", dropna=False)["area_sf"].sum().reset_index(name="total_room_area_sf").sort_values("total_room_area_sf", ascending=False)
        )
    if {"occupancy", "area_sf"}.issubset(rooms.columns):
        gold_tables["program_area_by_occupancy"] = (
            rooms.groupby("occupancy", dropna=False)
            .agg(total_room_area_sf=("area_sf", "sum"), room_count=("name", "count"))
            .reset_index()
            .sort_values("total_room_area_sf", ascending=False)
        )
    finish_fields = [field for field in ["floor_finish", "wall_finish", "ceiling_finish", "base_finish"] if field in rooms.columns]
    if finish_fields:
        gold_tables["room_finish_completeness"] = pd.DataFrame(
            [
                {
                    "finish_field": field,
                    "missing_count": int(missing_mask(rooms[field]).sum()),
                    "total_rooms": len(rooms),
                    "completion_rate": round(1 - (int(missing_mask(rooms[field]).sum()) / len(rooms)), 4) if len(rooms) else 0,
                }
                for field in finish_fields
            ]
        )

if "doors" in silver_tables:
    doors = silver_tables["doors"].copy()
    write_group_count(doors, ["level"], gold_tables, "door_count_by_level", "door_count")
    write_group_count(doors, ["function"], gold_tables, "door_count_by_function", "door_count")
    write_group_count(doors, ["level", "fire_rating"], gold_tables, "door_fire_rating_by_level", "door_count")
    if "fire_rating" in doors.columns:
        rated = doors.copy()
        rated["is_fire_rated"] = ~rated["fire_rating"].astype(str).str.strip().isin(["", "NR", "None", "nan"])
        gold_tables["door_fire_rating_summary"] = rated.groupby("is_fire_rated", dropna=False).size().reset_index(name="door_count")

if "windows" in silver_tables:
    write_group_count(silver_tables["windows"], ["level"], gold_tables, "window_count_by_level", "window_count")
    write_group_count(silver_tables["windows"], ["type"], gold_tables, "window_count_by_type", "window_count")

if "walls" in silver_tables:
    walls = silver_tables["walls"].copy()
    write_group_count(walls, ["function"], gold_tables, "wall_count_by_function", "wall_count")
    write_group_count(walls, ["type"], gold_tables, "wall_count_by_type", "wall_count")
    write_group_count(walls, ["structural_material"], gold_tables, "wall_count_by_material", "wall_count")
    if "area" in walls.columns:
        walls["area_sf"] = walls["area"].apply(parse_first_number)
        if "function" in walls.columns:
            gold_tables["wall_area_by_function"] = walls.groupby("function", dropna=False)["area_sf"].sum().reset_index().sort_values("area_sf", ascending=False)

if "floors" in silver_tables:
    floors = silver_tables["floors"].copy()
    write_group_count(floors, ["type"], gold_tables, "floor_count_by_type", "floor_count")
    if "area" in floors.columns:
        floors["area_sf"] = floors["area"].apply(parse_first_number)
        if "level" in floors.columns:
            gold_tables["floor_area_by_level"] = floors.groupby("level", dropna=False)["area_sf"].sum().reset_index().sort_values("area_sf", ascending=False)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold: MEP and Structural

# COMMAND ----------

mep_categories = {
    "air_terminals": "air_terminal_count",
    "duct_fittings": "duct_fitting_count",
    "mechanical_equipment": "mechanical_equipment_count",
    "electrical_fixtures": "electrical_fixture_count",
    "lighting_fixtures": "lighting_fixture_count",
    "data_devices": "data_device_count",
}

for category, count_name in mep_categories.items():
    if category in silver_tables:
        df = silver_tables[category]
        write_group_count(df, ["level"], gold_tables, f"{category}_by_level", count_name)
        write_group_count(df, ["family_and_type"], gold_tables, f"{category}_by_family_type", count_name)
        write_group_count(df, ["system_name"], gold_tables, f"{category}_by_system", count_name)

if "electrical_equipment" in silver_tables:
    equipment = silver_tables["electrical_equipment"]
    write_group_count(equipment, ["level"], gold_tables, "electrical_equipment_by_level", "equipment_count")
    write_group_count(equipment, ["part_type"], gold_tables, "electrical_equipment_by_part_type", "equipment_count")
    write_group_count(equipment, ["distribution_system"], gold_tables, "electrical_distribution_system_summary", "equipment_count")

gold_tables["mep_inventory_summary"] = pd.DataFrame(
    [
        {"element_category": category, "record_count": len(silver_tables[category]), "discipline": discipline_for_category(category)}
        for category in ["air_terminals", "duct_fittings", "mechanical_equipment", "electrical_equipment", "electrical_fixtures", "lighting_fixtures", "data_devices"]
        if category in silver_tables
    ]
)

structural_categories = {
    "structural_columns": "column_count",
    "structural_foundations": "foundation_count",
    "structural_framing": "framing_count",
}

for category, count_name in structural_categories.items():
    if category in silver_tables:
        df = silver_tables[category].copy()
        write_group_count(df, ["level"], gold_tables, f"{category}_by_level", count_name)
        write_group_count(df, ["family_and_type"], gold_tables, f"{category}_by_family_type", count_name)
        write_group_count(df, ["structural_material"], gold_tables, f"{category}_by_material", count_name)
        write_group_count(df, ["structural_usage"], gold_tables, f"{category}_by_usage", count_name)
        if "volume" in df.columns:
            df["volume_cf"] = df["volume"].apply(parse_first_number)
            if "structural_material" in df.columns:
                gold_tables[f"{category}_volume_by_material"] = (
                    df.groupby("structural_material", dropna=False)["volume_cf"].sum().reset_index().sort_values("volume_cf", ascending=False)
                )

gold_tables["structural_inventory_summary"] = pd.DataFrame(
    [
        {"element_category": category, "record_count": len(silver_tables[category]), "discipline": "structural"}
        for category in structural_categories
        if category in silver_tables
    ]
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Write Gold Delta Tables

# COMMAND ----------

for name, table in gold_tables.items():
    if table is not None and not table.empty:
        write_delta_table(table, f"gold_{name}")

display(spark.sql("SHOW TABLES"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Dashboard Starter Queries
# MAGIC
# MAGIC ```sql
# MAGIC SELECT * FROM gold_model_inventory_by_discipline ORDER BY record_count DESC;
# MAGIC ```
# MAGIC
# MAGIC ```sql
# MAGIC SELECT * FROM gold_bim_readiness_score ORDER BY bim_readiness_score DESC;
# MAGIC ```
# MAGIC
# MAGIC ```sql
# MAGIC SELECT * FROM gold_room_area_by_level ORDER BY total_room_area_sf DESC;
# MAGIC ```
# MAGIC
# MAGIC ```sql
# MAGIC SELECT * FROM gold_mep_inventory_summary ORDER BY record_count DESC;
# MAGIC ```
# MAGIC
# MAGIC ```sql
# MAGIC SELECT * FROM gold_structural_inventory_summary ORDER BY record_count DESC;
# MAGIC ```

