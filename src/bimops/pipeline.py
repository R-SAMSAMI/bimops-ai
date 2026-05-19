from __future__ import annotations

import csv
import re
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPORT_DIR = PROJECT_ROOT / "exports" / "revit_schedules"
BRONZE_DIR = PROJECT_ROOT / "data" / "bronze"
SILVER_DIR = PROJECT_ROOT / "data" / "silver"
GOLD_DIR = PROJECT_ROOT / "data" / "gold"


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def read_schedule(path: Path) -> pd.DataFrame:
    for delimiter in [",", "\t"]:
        rows = read_raw_rows(path, delimiter)
        header_row = detect_header_row(rows[:5])
        if header_row is not None:
            return build_dataframe_from_rows(rows, header_row).dropna(how="all")

    return pd.read_csv(path).dropna(how="all")


def read_raw_rows(path: Path, delimiter: str) -> list[list[str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.reader(handle, delimiter=delimiter))


def detect_header_row(rows: list[list[str]]) -> int | None:
    for index, row in enumerate(rows):
        values = [str(value).strip().lower() for value in row if str(value).strip()]
        if len(values) < 2:
            continue
        if any(value in values for value in ["level", "name", "mark", "family", "family and type"]):
            return int(index)
    return None


def build_dataframe_from_rows(rows: list[list[str]], header_row: int) -> pd.DataFrame:
    headers = [str(value).strip() for value in rows[header_row]]
    cleaned_rows = []

    for row in rows[header_row + 1 :]:
        if not any(str(value).strip() for value in row):
            continue
        cleaned_rows.append(repair_row_width(row, headers))

    return pd.DataFrame(cleaned_rows, columns=headers)


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


def normalize_table_name(raw_name: str) -> str:
    table_name = slugify(raw_name)
    aliases = {
        "airterminals": "air_terminals",
        "datadevices": "data_devices",
        "ductfittings": "duct_fittings",
        "eequipment": "electrical_equipment",
        "efixtures": "electrical_fixtures",
        "electrical_equipment_schedule": "electrical_equipment",
        "electrical_equipment_schedule_2": "electrical_equipment",
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


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    clean = df.copy()
    clean.columns = [slugify(str(column)) for column in clean.columns]
    return clean


def parse_first_number(value: object) -> float | None:
    match = re.search(r"-?\d+(?:\.\d+)?", str(value))
    return float(match.group(0)) if match else None


def missing_mask(series: pd.Series) -> pd.Series:
    return series.isna() | (series.astype(str).str.strip() == "")


def write_group_count(df: pd.DataFrame, group_columns: list[str], output_name: str, count_name: str = "record_count") -> None:
    available_columns = [column for column in group_columns if column in df.columns]
    if not available_columns:
        return

    grouped = (
        df.groupby(available_columns, dropna=False)
        .size()
        .reset_index(name=count_name)
        .sort_values(count_name, ascending=False)
    )
    write_table(grouped, GOLD_DIR, output_name)


def write_table(df: pd.DataFrame, directory: Path, name: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    df.to_csv(directory / f"{name}.csv", index=False)
    df.to_parquet(directory / f"{name}.parquet", index=False)


def reset_output_dirs() -> None:
    for directory in [BRONZE_DIR, SILVER_DIR, GOLD_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
        for path in directory.glob("*"):
            if path.name != ".gitkeep" and path.is_file():
                path.unlink()


def build_bronze_tables() -> dict[str, pd.DataFrame]:
    tables: dict[str, pd.DataFrame] = {}

    for path in sorted(EXPORT_DIR.glob("*.csv")):
        table_name = normalize_table_name(path.stem)
        df = read_schedule(path)
        df["source_file"] = path.name
        df["source_system"] = "revit_schedule_export"
        tables[table_name] = df
        write_table(df, BRONZE_DIR, table_name)

    return tables


def build_silver_tables(bronze: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    silver: dict[str, pd.DataFrame] = {}

    for table_name, df in bronze.items():
        clean = normalize_columns(df)
        clean = clean.drop_duplicates()
        clean["element_category"] = table_name
        silver[table_name] = clean
        write_table(clean, SILVER_DIR, table_name)

    return silver


def build_gold_tables(silver: dict[str, pd.DataFrame]) -> None:
    summary_rows = []
    quality_rows = []
    readiness_rows = []

    for table_name, df in silver.items():
        summary_rows.append(
            {
                "element_category": table_name,
                "record_count": len(df),
                "column_count": len(df.columns),
            }
        )

        for column in df.columns:
            missing_count = int(df[column].isna().sum() + (df[column].astype(str).str.strip() == "").sum())
            quality_rows.append(
                {
                    "element_category": table_name,
                    "field_name": column,
                    "missing_count": missing_count,
                    "total_records": len(df),
                    "missing_rate": round(missing_count / len(df), 4) if len(df) else 0,
                }
            )

        important_fields = important_fields_for_category(table_name, df)
        if important_fields:
            missing_cells = sum(int(missing_mask(df[field]).sum()) for field in important_fields)
            total_cells = len(df) * len(important_fields)
            readiness_rows.append(
                {
                    "element_category": table_name,
                    "important_field_count": len(important_fields),
                    "total_records": len(df),
                    "missing_important_values": missing_cells,
                    "bim_readiness_score": round(1 - (missing_cells / total_cells), 4) if total_cells else 0,
                }
            )

    write_table(pd.DataFrame(summary_rows), GOLD_DIR, "element_summary")
    write_table(pd.DataFrame(quality_rows), GOLD_DIR, "metadata_quality")
    write_table(pd.DataFrame(readiness_rows), GOLD_DIR, "bim_readiness_score")
    build_inventory_gold_tables(silver)
    build_generic_quality_gold_tables(silver)

    if "rooms" in silver:
        build_room_gold_tables(silver["rooms"].copy())

    if "doors" in silver:
        build_door_gold_tables(silver["doors"].copy())

    if "electrical_equipment" in silver:
        build_electrical_gold_tables(silver["electrical_equipment"].copy())

    build_architecture_gold_tables(silver)
    build_mep_gold_tables(silver)
    build_structural_gold_tables(silver)


def important_fields_for_category(table_name: str, df: pd.DataFrame) -> list[str]:
    fields_by_category = {
        "air_terminals": ["family_and_type", "level", "system_name", "flow", "mark"],
        "data_devices": ["mark", "family_and_type", "level", "comments"],
        "rooms": ["number", "name", "level", "area", "occupancy", "floor_finish", "wall_finish", "ceiling_finish"],
        "doors": ["type", "level", "family", "fire_rating", "width", "height", "material", "frame_material"],
        "duct_fittings": ["family_and_type", "level", "system_name", "size"],
        "electrical_equipment": ["mark", "family_and_type", "level", "location", "distribution_system", "electrical_data", "part_type"],
        "electrical_fixtures": ["mark", "family_and_type", "level", "panel", "circuit_number"],
        "lighting_fixtures": ["mark", "family_and_type", "level", "panel", "circuit_number"],
        "mechanical_equipment": ["mark", "family_and_type", "level", "system_name", "manufacturer", "model"],
        "structural_columns": ["mark", "family_and_type", "level", "base_level", "top_level", "structural_material"],
        "structural_foundations": ["mark", "family_and_type", "level", "structural_material", "volume"],
        "structural_framing": ["mark", "family_and_type", "level", "structural_material", "structural_usage", "cut_length"],
        "walls": ["type", "family_and_type", "base_constraint", "top_constraint", "function", "structural_material", "area"],
        "windows": ["type", "family_and_type", "level", "width", "height", "material"],
    }
    return [field for field in fields_by_category.get(table_name, []) if field in df.columns]


def build_inventory_gold_tables(silver: dict[str, pd.DataFrame]) -> None:
    inventory = []
    for category, df in silver.items():
        inventory.append(
            {
                "discipline": discipline_for_category(category),
                "element_category": category,
                "record_count": len(df),
                "column_count": len(df.columns),
            }
        )

    inventory_df = pd.DataFrame(inventory).sort_values(["discipline", "record_count"], ascending=[True, False])
    write_table(inventory_df, GOLD_DIR, "model_inventory_by_category")

    discipline_summary = (
        inventory_df.groupby("discipline", dropna=False)["record_count"]
        .sum()
        .reset_index()
        .sort_values("record_count", ascending=False)
    )
    write_table(discipline_summary, GOLD_DIR, "model_inventory_by_discipline")


def build_generic_quality_gold_tables(silver: dict[str, pd.DataFrame]) -> None:
    tracked_fields = ["mark", "level", "type", "family_and_type", "classification_number", "manufacturer", "model", "comments"]
    rows = []

    for category, df in silver.items():
        for field in tracked_fields:
            if field not in df.columns:
                continue
            missing_count = int(missing_mask(df[field]).sum())
            rows.append(
                {
                    "discipline": discipline_for_category(category),
                    "element_category": category,
                    "field_name": field,
                    "missing_count": missing_count,
                    "total_records": len(df),
                    "missing_rate": round(missing_count / len(df), 4) if len(df) else 0,
                }
            )

    write_table(pd.DataFrame(rows), GOLD_DIR, "key_field_completeness")

    assets = []
    for category, df in silver.items():
        if discipline_for_category(category) not in {"electrical", "mechanical", "structural"}:
            continue
        missing_mark = int(missing_mask(df["mark"]).sum()) if "mark" in df.columns else len(df)
        missing_type = int(missing_mask(df["family_and_type"]).sum()) if "family_and_type" in df.columns else len(df)
        assets.append(
            {
                "discipline": discipline_for_category(category),
                "element_category": category,
                "total_assets": len(df),
                "missing_mark": missing_mark,
                "missing_family_and_type": missing_type,
                "asset_id_completion_rate": round(1 - ((missing_mark + missing_type) / (len(df) * 2)), 4) if len(df) else 0,
            }
        )
    write_table(pd.DataFrame(assets), GOLD_DIR, "asset_identity_readiness")


def build_room_gold_tables(rooms: pd.DataFrame) -> None:
    if "area" in rooms.columns:
        rooms["area_sf"] = rooms["area"].apply(parse_first_number)

    if {"level", "area_sf"}.issubset(rooms.columns):
        room_area_by_level = (
            rooms.groupby("level", dropna=False)["area_sf"]
            .sum()
            .reset_index()
            .rename(columns={"area_sf": "total_room_area_sf"})
            .sort_values("total_room_area_sf", ascending=False)
        )
        write_table(room_area_by_level, GOLD_DIR, "room_area_by_level")

    if {"occupancy", "area_sf"}.issubset(rooms.columns):
        program_area = (
            rooms.groupby("occupancy", dropna=False)
            .agg(total_room_area_sf=("area_sf", "sum"), room_count=("name", "count"))
            .reset_index()
            .sort_values("total_room_area_sf", ascending=False)
        )
        write_table(program_area, GOLD_DIR, "program_area_by_occupancy")

    finish_fields = [field for field in ["floor_finish", "wall_finish", "ceiling_finish", "base_finish"] if field in rooms.columns]
    if finish_fields:
        finish_summary = []
        for field in finish_fields:
            missing_count = int(missing_mask(rooms[field]).sum())
            finish_summary.append(
                {
                    "finish_field": field,
                    "missing_count": missing_count,
                    "total_rooms": len(rooms),
                    "completion_rate": round(1 - (missing_count / len(rooms)), 4) if len(rooms) else 0,
                }
            )
        write_table(pd.DataFrame(finish_summary), GOLD_DIR, "room_finish_completeness")


def build_door_gold_tables(doors: pd.DataFrame) -> None:
    write_group_count(doors, ["level"], "door_count_by_level", "door_count")
    write_group_count(doors, ["function"], "door_count_by_function", "door_count")
    write_group_count(doors, ["level", "fire_rating"], "door_fire_rating_by_level", "door_count")

    if "fire_rating" in doors.columns:
        fire_rating = doors.copy()
        fire_rating["is_fire_rated"] = ~fire_rating["fire_rating"].astype(str).str.strip().isin(["", "NR", "None", "nan"])
        fire_rating_summary = (
            fire_rating.groupby("is_fire_rated", dropna=False)
            .size()
            .reset_index(name="door_count")
            .sort_values("door_count", ascending=False)
        )
        write_table(fire_rating_summary, GOLD_DIR, "door_fire_rating_summary")


def build_electrical_gold_tables(equipment: pd.DataFrame) -> None:
    write_group_count(equipment, ["level"], "electrical_equipment_by_level", "equipment_count")
    write_group_count(equipment, ["part_type"], "electrical_equipment_by_part_type", "equipment_count")
    write_group_count(equipment, ["distribution_system"], "electrical_distribution_system_summary", "equipment_count")

    if "electrical_data" in equipment.columns:
        electrical_data = equipment["electrical_data"].fillna("").astype(str)
        load_summary = pd.DataFrame(
            [
                {
                    "metric": "records_with_electrical_data",
                    "record_count": int((electrical_data.str.strip() != "").sum()),
                },
                {
                    "metric": "records_missing_electrical_data",
                    "record_count": int((electrical_data.str.strip() == "").sum()),
                },
            ]
        )
        write_table(load_summary, GOLD_DIR, "electrical_data_completeness")


def build_architecture_gold_tables(silver: dict[str, pd.DataFrame]) -> None:
    if "walls" in silver:
        walls = silver["walls"].copy()
        write_group_count(walls, ["function"], "wall_count_by_function", "wall_count")
        write_group_count(walls, ["type"], "wall_count_by_type", "wall_count")
        write_group_count(walls, ["structural_material"], "wall_count_by_material", "wall_count")
        if "area" in walls.columns:
            walls["area_sf"] = walls["area"].apply(parse_first_number)
            if "function" in walls.columns:
                wall_area_by_function = (
                    walls.groupby("function", dropna=False)["area_sf"]
                    .sum()
                    .reset_index()
                    .sort_values("area_sf", ascending=False)
                )
                write_table(wall_area_by_function, GOLD_DIR, "wall_area_by_function")

    if "windows" in silver:
        windows = silver["windows"].copy()
        write_group_count(windows, ["level"], "window_count_by_level", "window_count")
        write_group_count(windows, ["type"], "window_count_by_type", "window_count")

    if "floors" in silver:
        floors = silver["floors"].copy()
        write_group_count(floors, ["type"], "floor_count_by_type", "floor_count")
        if "area" in floors.columns:
            floors["area_sf"] = floors["area"].apply(parse_first_number)
            if "level" in floors.columns:
                floor_area_by_level = (
                    floors.groupby("level", dropna=False)["area_sf"]
                    .sum()
                    .reset_index()
                    .sort_values("area_sf", ascending=False)
                )
                write_table(floor_area_by_level, GOLD_DIR, "floor_area_by_level")


def build_mep_gold_tables(silver: dict[str, pd.DataFrame]) -> None:
    mep_categories = {
        "air_terminals": "air_terminal_count",
        "duct_fittings": "duct_fitting_count",
        "mechanical_equipment": "mechanical_equipment_count",
        "electrical_fixtures": "electrical_fixture_count",
        "lighting_fixtures": "lighting_fixture_count",
        "data_devices": "data_device_count",
    }

    for category, count_name in mep_categories.items():
        if category not in silver:
            continue
        df = silver[category].copy()
        write_group_count(df, ["level"], f"{category}_by_level", count_name)
        write_group_count(df, ["family_and_type"], f"{category}_by_family_type", count_name)
        write_group_count(df, ["system_name"], f"{category}_by_system", count_name)

    mep_inventory = []
    for category in ["air_terminals", "duct_fittings", "mechanical_equipment", "electrical_equipment", "electrical_fixtures", "lighting_fixtures", "data_devices"]:
        if category in silver:
            mep_inventory.append(
                {
                    "element_category": category,
                    "record_count": len(silver[category]),
                    "discipline": discipline_for_category(category),
                }
            )
    write_table(pd.DataFrame(mep_inventory), GOLD_DIR, "mep_inventory_summary")


def build_structural_gold_tables(silver: dict[str, pd.DataFrame]) -> None:
    structural_categories = {
        "structural_columns": "column_count",
        "structural_foundations": "foundation_count",
        "structural_framing": "framing_count",
    }

    for category, count_name in structural_categories.items():
        if category not in silver:
            continue
        df = silver[category].copy()
        write_group_count(df, ["level"], f"{category}_by_level", count_name)
        write_group_count(df, ["family_and_type"], f"{category}_by_family_type", count_name)
        write_group_count(df, ["structural_material"], f"{category}_by_material", count_name)
        write_group_count(df, ["structural_usage"], f"{category}_by_usage", count_name)

        if "volume" in df.columns:
            df["volume_cf"] = df["volume"].apply(parse_first_number)
            if "structural_material" in df.columns:
                volume_by_material = (
                    df.groupby("structural_material", dropna=False)["volume_cf"]
                    .sum()
                    .reset_index()
                    .sort_values("volume_cf", ascending=False)
                )
                write_table(volume_by_material, GOLD_DIR, f"{category}_volume_by_material")

    structural_inventory = []
    for category in structural_categories:
        if category in silver:
            structural_inventory.append(
                {
                    "element_category": category,
                    "record_count": len(silver[category]),
                    "discipline": "structural",
                }
            )
    write_table(pd.DataFrame(structural_inventory), GOLD_DIR, "structural_inventory_summary")


def main() -> None:
    reset_output_dirs()
    bronze = build_bronze_tables()
    silver = build_silver_tables(bronze)
    build_gold_tables(silver)
    print(f"Processed {len(bronze)} Revit schedule exports.")
    print(f"Bronze: {BRONZE_DIR}")
    print(f"Silver: {SILVER_DIR}")
    print(f"Gold: {GOLD_DIR}")


if __name__ == "__main__":
    main()
