# Databricks notebook source
# MAGIC %md
# MAGIC # BIMOps Copilot Assistant
# MAGIC
# MAGIC This notebook creates a lightweight AI assistant on top of the BIMOps Databricks lakehouse.
# MAGIC
# MAGIC It lets a user ask a natural-language BIM question, generates safe read-only SQL against the Gold tables,
# MAGIC runs the query in Databricks, and explains the answer in practical AEC language.
# MAGIC
# MAGIC **Workflow**
# MAGIC
# MAGIC 1. Ask a BIM/lakehouse question in the widget.
# MAGIC 2. The assistant discovers available `gold_*` tables.
# MAGIC 3. OpenAI generates one read-only Databricks SQL query.
# MAGIC 4. Databricks executes the query.
# MAGIC 5. The assistant summarizes what the result means and recommends the next BIM/data action.
# MAGIC
# MAGIC Keep your OpenAI API key private. Do not commit it to GitHub or paste it into screenshots.

# COMMAND ----------

# MAGIC %pip install openai

# COMMAND ----------

# MAGIC %md
# MAGIC If Databricks asks you to restart Python after installing `openai`, click **restart**, then continue from the next cell.

# COMMAND ----------

import json
import re
from textwrap import dedent

from openai import OpenAI
from pyspark.sql import functions as F

DATABASE_NAME = "bimops_ai"
spark.sql(f"USE {DATABASE_NAME}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Notebook Inputs
# MAGIC
# MAGIC Paste your OpenAI API key into the widget only for a private demo.
# MAGIC
# MAGIC For a more secure setup, create a Databricks secret and replace the widget line with:
# MAGIC
# MAGIC ```python
# MAGIC OPENAI_API_KEY = dbutils.secrets.get(scope="bimops", key="openai_api_key")
# MAGIC ```

# COMMAND ----------

dbutils.widgets.text("openai_api_key", "", "OpenAI API key")
dbutils.widgets.text(
    "question",
    "Which BIM categories have the weakest readiness scores, and what should the team improve first?",
    "BIM question",
)
dbutils.widgets.dropdown("max_result_rows", "20", ["5", "10", "20", "50"], "Rows to summarize")

OPENAI_API_KEY = dbutils.widgets.get("openai_api_key").strip()
QUESTION = dbutils.widgets.get("question").strip()
MAX_RESULT_ROWS = int(dbutils.widgets.get("max_result_rows"))

if not OPENAI_API_KEY:
    raise ValueError("Paste your OpenAI API key into the openai_api_key widget, then rerun this cell.")

client = OpenAI(api_key=OPENAI_API_KEY)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold Table Catalog
# MAGIC
# MAGIC The assistant uses the current Databricks catalog state instead of assuming table names.
# MAGIC This prevents failures when a table has a slightly different name than expected.

# COMMAND ----------

CURATED_TABLE_DESCRIPTIONS = {
    "gold_air_terminals_by_family_type": "Air terminal counts by family and type for HVAC inventory review.",
    "gold_air_terminals_by_level": "Air terminal counts by building level.",
    "gold_air_terminals_by_system": "Air terminal counts by mechanical system.",
    "gold_asset_identity_readiness": "Asset identity completion rates based on mark, family, type, manufacturer, model, and related fields.",
    "gold_bim_readiness_score": "BIM readiness score by category based on metadata completeness.",
    "gold_data_devices_by_family_type": "Data device counts by family and type for low-voltage and technology inventory.",
    "gold_data_devices_by_level": "Data device distribution by building level.",
    "gold_door_count_by_function": "Door counts by function for access, code, and planning review.",
    "gold_door_count_by_level": "Door counts by building level.",
    "gold_door_fire_rating_by_level": "Fire-rated door counts by level for life-safety review.",
    "gold_door_fire_rating_summary": "Fire-rated versus non-fire-rated door summary.",
    "gold_duct_fittings_by_family_type": "Duct fitting counts by family and type for HVAC component inventory.",
    "gold_duct_fittings_by_level": "Duct fitting counts by building level.",
    "gold_duct_fittings_by_system": "Duct fitting counts by mechanical system.",
    "gold_electrical_distribution_system_summary": "Electrical equipment grouped by distribution system.",
    "gold_electrical_equipment_by_level": "Electrical equipment counts by building level.",
    "gold_electrical_equipment_by_part_type": "Electrical equipment grouped by part type.",
    "gold_electrical_fixtures_by_family_type": "Electrical fixture counts by family and type.",
    "gold_electrical_fixtures_by_level": "Electrical fixture counts by building level.",
    "gold_element_summary": "High-level element summary across BIM categories.",
    "gold_floor_area_by_level": "Floor area summarized by building level.",
    "gold_floor_count_by_type": "Floor counts by floor type.",
    "gold_key_field_completeness": "Completeness and missing-rate metrics for key BIM metadata fields.",
    "gold_lighting_fixtures_by_family_type": "Lighting fixture counts by family and type.",
    "gold_lighting_fixtures_by_level": "Lighting fixture counts by building level.",
    "gold_mechanical_equipment_by_family_type": "Mechanical equipment counts by family and type.",
    "gold_mechanical_equipment_by_level": "Mechanical equipment counts by building level.",
    "gold_mechanical_equipment_by_system": "Mechanical equipment grouped by HVAC/mechanical system.",
    "gold_mep_inventory_summary": "MEP inventory summary across mechanical, electrical, lighting, data, and HVAC categories.",
    "gold_metadata_quality": "Broad metadata quality and missing-rate metrics across model categories and fields.",
    "gold_model_inventory_by_category": "BIM record counts grouped by element category.",
    "gold_model_inventory_by_discipline": "BIM record counts grouped by architecture, electrical, mechanical, and structural disciplines.",
    "gold_program_area_by_occupancy": "Program area and room count by occupancy or space-use classification.",
    "gold_room_area_by_level": "Room area summarized by building level.",
    "gold_room_finish_completeness": "Room finish metadata completeness for finish-related fields.",
    "gold_structural_columns_by_family_type": "Structural column counts by family and type.",
    "gold_structural_columns_by_material": "Structural column counts by material.",
    "gold_structural_columns_volume_by_material": "Structural column volume by material.",
    "gold_structural_foundations_by_family_type": "Structural foundation counts by family and type.",
    "gold_structural_foundations_by_level": "Structural foundation counts by building level.",
    "gold_structural_foundations_by_material": "Structural foundation counts by material.",
    "gold_structural_foundations_by_usage": "Structural foundation counts by usage classification.",
    "gold_structural_foundations_volume_by_material": "Structural foundation volume by material.",
    "gold_structural_framing_by_family_type": "Structural framing counts by family and type.",
    "gold_structural_framing_by_level": "Structural framing counts by building level.",
    "gold_structural_framing_by_material": "Structural framing counts by material.",
    "gold_structural_framing_by_usage": "Structural framing counts by usage classification.",
    "gold_structural_framing_volume_by_material": "Structural framing volume by material.",
    "gold_structural_inventory_summary": "Structural inventory summary across columns, foundations, and framing.",
    "gold_wall_area_by_function": "Wall area by wall function.",
    "gold_wall_count_by_function": "Wall counts by function.",
    "gold_wall_count_by_material": "Wall counts by material.",
    "gold_wall_count_by_type": "Wall counts by wall type.",
    "gold_window_count_by_level": "Window counts by building level.",
    "gold_window_count_by_type": "Window counts by window type.",
}


def list_gold_tables():
    tables_df = spark.sql(f"SHOW TABLES IN {DATABASE_NAME}")
    return [
        row["tableName"]
        for row in tables_df.collect()
        if row["tableName"].startswith("gold_")
    ]


def get_table_columns(table_name):
    return [field.name for field in spark.table(f"{DATABASE_NAME}.{table_name}").schema.fields]


def get_table_context():
    context = {}
    for table_name in sorted(list_gold_tables()):
        context[table_name] = {
            "description": CURATED_TABLE_DESCRIPTIONS.get(
                table_name,
                "Gold analytics table generated from cleaned BIM data.",
            ),
            "columns": get_table_columns(table_name),
        }
    return context


TABLE_CONTEXT = get_table_context()

if not TABLE_CONTEXT:
    raise ValueError(f"No gold_* tables found in database {DATABASE_NAME}. Run the BIMOps ETL notebook first.")

display(
    spark.createDataFrame(
        [
            {
                "table_name": table_name,
                "description": meta["description"],
                "columns": ", ".join(meta["columns"]),
            }
            for table_name, meta in TABLE_CONTEXT.items()
        ]
    )
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## SQL Guardrails
# MAGIC
# MAGIC The assistant is restricted to read-only `SELECT` statements against `bimops_ai.gold_*` tables.

# COMMAND ----------

BLOCKED_SQL_KEYWORDS = [
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "merge",
    "truncate",
    "grant",
    "revoke",
    "replace",
    "optimize",
    "vacuum",
]


def clean_sql(sql: str) -> str:
    cleaned = sql.strip()
    cleaned = re.sub(r"^```sql", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"^```", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    return cleaned.rstrip(";")


def referenced_tables(sql):
    known_tables = set(TABLE_CONTEXT.keys())
    matches = set()
    lowered_sql = sql.lower()
    for table_name in known_tables:
        if table_name.lower() in lowered_sql:
            matches.add(table_name)
    return matches


def validate_sql(sql: str) -> str:
    cleaned = clean_sql(sql)
    lowered = cleaned.lower()

    if not lowered.startswith("select"):
        raise ValueError("Only SELECT statements are allowed.")

    padded = f" {lowered} "
    for keyword in BLOCKED_SQL_KEYWORDS:
        if re.search(rf"\b{keyword}\b", padded):
            raise ValueError(f"Blocked SQL keyword detected: {keyword}")

    used_tables = referenced_tables(cleaned)
    if not used_tables:
        raise ValueError("The SQL must reference at least one known Gold table.")

    for table_name in used_tables:
        if not table_name.startswith("gold_"):
            raise ValueError(f"Only Gold tables are allowed. Found: {table_name}")

    return cleaned


def run_safe_sql(sql: str):
    safe_sql = validate_sql(sql)
    return spark.sql(safe_sql)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Copilot Functions
# MAGIC
# MAGIC The first model call writes SQL. The second model call explains the result and recommends a practical action.

# COMMAND ----------

def generate_sql(question: str) -> str:
    system_prompt = dedent(
        f"""
        You are BIMOps Copilot, an AEC data assistant working inside Databricks.

        Your job is to generate exactly one Databricks SQL SELECT query that answers the user's question.

        Database:
        {DATABASE_NAME}

        Available Gold tables:
        {json.dumps(TABLE_CONTEXT, indent=2)}

        Rules:
        - Return only SQL. Do not include markdown or explanation.
        - Use fully qualified table names like {DATABASE_NAME}.gold_model_inventory_by_category.
        - Use only the available Gold tables listed above.
        - Do not query Bronze or Silver tables.
        - Do not use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, MERGE, TRUNCATE, OPTIMIZE, or VACUUM.
        - Prefer concise queries with clear aliases.
        - Add ORDER BY and LIMIT when the question asks for ranking, weakest, strongest, most, least, top, or worst.
        - If the question asks about readiness or data quality, prioritize readiness, completeness, missing-rate, and metadata-quality tables.
        - If the question asks what to improve, return the rows that reveal the weakest metadata completeness or lowest readiness.
        """
    )

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
    )
    return validate_sql(response.output_text)


def summarize_result(question, sql, rows):
    system_prompt = dedent(
        """
        You are BIMOps Copilot, an AI assistant for BIM, AEC data, and Databricks lakehouse analytics.

        Explain SQL results for a mixed technical and non-technical AEC audience.

        Response format:

        Executive answer:
        One concise paragraph answering the question.

        Evidence from the lakehouse:
        2-4 bullets using only the provided rows.

        Recommended next action:
        1-3 bullets focused on BIM data quality, coordination, operations handoff, or dashboard follow-up.

        Guardrails:
        - Do not invent numbers.
        - Do not mention rows that are not provided.
        - If the result is empty, say so and recommend a safer follow-up question.
        - Keep it clear, practical, and professional.
        """
    )

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "question": question,
                        "sql": sql,
                        "rows": rows,
                    },
                    indent=2,
                    default=str,
                ),
            },
        ],
    )
    return response.output_text


def ask_bimops_copilot(question: str, max_rows: int = 20):
    print("Question")
    print(question)
    print()

    generated_sql = generate_sql(question)
    print("Generated SQL")
    print(generated_sql)
    print()

    result_df = run_safe_sql(generated_sql)
    display(result_df)

    rows = [row.asDict(recursive=True) for row in result_df.limit(max_rows).collect()]
    answer = summarize_result(question, generated_sql, rows)

    print("BIMOps Copilot Answer")
    print(answer)

    return {
        "question": question,
        "sql": generated_sql,
        "rows": rows,
        "answer": answer,
    }

# COMMAND ----------

# MAGIC %md
# MAGIC ## Ask BIMOps Copilot
# MAGIC
# MAGIC Update the `question` widget at the top, then rerun this cell.

# COMMAND ----------

copilot_response = ask_bimops_copilot(QUESTION, MAX_RESULT_ROWS)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Strong Demo Questions
# MAGIC
# MAGIC Paste one of these into the `question` widget:
# MAGIC
# MAGIC ```text
# MAGIC Which BIM categories have the weakest readiness scores, and what should the team improve first?
# MAGIC ```
# MAGIC
# MAGIC ```text
# MAGIC Which key BIM metadata fields have the highest missing rates?
# MAGIC ```
# MAGIC
# MAGIC ```text
# MAGIC Summarize the model inventory by discipline.
# MAGIC ```
# MAGIC
# MAGIC ```text
# MAGIC Which MEP categories have the most assets?
# MAGIC ```
# MAGIC
# MAGIC ```text
# MAGIC How many doors are fire-rated versus not fire-rated?
# MAGIC ```
# MAGIC
# MAGIC ```text
# MAGIC Which structural materials have the highest modeled volume?
# MAGIC ```
# MAGIC
# MAGIC ```text
# MAGIC Which building levels have the most room area?
# MAGIC ```
# MAGIC
# MAGIC ```text
# MAGIC What are the top data-quality risks in this BIM model?
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## Optional: Save Copilot Run Log
# MAGIC
# MAGIC This stores the latest question, SQL, and AI answer as a small Delta table.
# MAGIC It is useful for documenting demo prompts and making the assistant auditable.

# COMMAND ----------

run_log_df = spark.createDataFrame(
    [
        {
            "question": copilot_response["question"],
            "generated_sql": copilot_response["sql"],
            "answer": copilot_response["answer"],
        }
    ]
).withColumn("run_timestamp", F.current_timestamp())

run_log_df.write.mode("append").format("delta").saveAsTable(f"{DATABASE_NAME}.copilot_run_log")

display(spark.table(f"{DATABASE_NAME}.copilot_run_log").orderBy(F.desc("run_timestamp")).limit(10))
