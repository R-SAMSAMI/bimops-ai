# Databricks notebook source
# MAGIC %md
# MAGIC # Ask the BIM Lakehouse with OpenAI
# MAGIC
# MAGIC This notebook adds a lightweight natural-language query layer on top of the BIMOps AI Gold tables.
# MAGIC
# MAGIC Workflow:
# MAGIC
# MAGIC 1. User asks a BIM question in plain English.
# MAGIC 2. OpenAI selects the most relevant Gold table and generates SQL.
# MAGIC 3. Databricks executes the SQL.
# MAGIC 4. OpenAI summarizes the result for a non-technical AEC stakeholder.
# MAGIC
# MAGIC Keep your OpenAI API key private. Do not commit it to GitHub.

# COMMAND ----------

# MAGIC %pip install openai

# COMMAND ----------

# MAGIC %md
# MAGIC If Databricks asks you to restart Python after installing `openai`, click restart, then continue from the next cell.

# COMMAND ----------

import json
import os
import re
from textwrap import dedent

from openai import OpenAI
from pyspark.sql import functions as F

DATABASE_NAME = "bimops_ai"
spark.sql(f"USE {DATABASE_NAME}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Add Your OpenAI API Key
# MAGIC
# MAGIC Option A is best if you have Databricks secrets configured.
# MAGIC
# MAGIC Option B is easiest for a short private demo. Paste your key into the widget at the top of the notebook after this cell runs.

# COMMAND ----------

dbutils.widgets.text("openai_api_key", "", "OpenAI API key")
dbutils.widgets.text("question", "Which BIM categories have the weakest readiness scores?", "BIM question")

OPENAI_API_KEY = dbutils.widgets.get("openai_api_key").strip()

# Optional secure Databricks secret fallback. Uncomment after creating the secret.
# OPENAI_API_KEY = dbutils.secrets.get(scope="bimops", key="openai_api_key")

if not OPENAI_API_KEY:
    raise ValueError("Paste your OpenAI API key into the openai_api_key widget, then rerun this cell.")

client = OpenAI(api_key=OPENAI_API_KEY)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold Tables Available To The AI Layer

# COMMAND ----------

GOLD_TABLES = {
    "gold_model_inventory_by_discipline": "Record counts grouped by architecture, electrical, mechanical, and structural disciplines.",
    "gold_model_inventory_by_category": "Record counts for each BIM element category such as walls, doors, rooms, duct fittings, and structural framing.",
    "gold_bim_readiness_score": "BIM readiness score by category based on important metadata fields.",
    "gold_key_field_completeness": "Missing rate for key fields such as mark, level, type, classification, manufacturer, model, and comments.",
    "gold_room_area_by_level": "Total room area by building level.",
    "gold_program_area_by_occupancy": "Room area and room count by occupancy or program type.",
    "gold_mep_inventory_summary": "MEP asset inventory record counts by category.",
    "gold_structural_inventory_summary": "Structural inventory record counts by category.",
    "gold_door_fire_rating_summary": "Fire-rated vs non-fire-rated door counts.",
    "gold_wall_area_by_function": "Wall area grouped by wall function.",
    "gold_air_terminals_by_level": "Air terminal counts by level.",
    "gold_structural_framing_by_material": "Structural framing counts by material.",
    "gold_asset_identity_readiness": "Asset identity completion rates based on mark and family/type availability.",
    "gold_metadata_quality": "Broad metadata missing-rate table across all generated Gold tables and fields.",
}


def get_table_schema(table_name: str) -> list[str]:
    return [field.name for field in spark.table(f"{DATABASE_NAME}.{table_name}").schema.fields]


TABLE_CONTEXT = {
    name: {
        "description": description,
        "columns": get_table_schema(name),
    }
    for name, description in GOLD_TABLES.items()
}

display(
    spark.createDataFrame(
        [
            {
                "table_name": table,
                "description": meta["description"],
                "columns": ", ".join(meta["columns"]),
            }
            for table, meta in TABLE_CONTEXT.items()
        ]
    )
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## SQL Safety Rules
# MAGIC
# MAGIC The generated SQL is limited to read-only `SELECT` queries against the `bimops_ai.gold_*` tables.

# COMMAND ----------

def clean_sql(sql: str) -> str:
    sql = sql.strip()
    sql = re.sub(r"^```sql", "", sql, flags=re.IGNORECASE).strip()
    sql = re.sub(r"^```", "", sql).strip()
    sql = re.sub(r"```$", "", sql).strip()
    return sql


def validate_sql(sql: str) -> str:
    cleaned = clean_sql(sql)
    lowered = cleaned.lower()

    if not lowered.startswith("select"):
        raise ValueError("Only SELECT statements are allowed.")

    blocked = [" insert ", " update ", " delete ", " drop ", " alter ", " create ", " merge ", " truncate ", " grant ", " revoke "]
    padded = f" {lowered} "
    if any(token in padded for token in blocked):
        raise ValueError("The generated SQL contains a blocked keyword.")

    if "gold_" not in lowered:
        raise ValueError("The SQL must query one of the Gold tables.")

    return cleaned


def generate_sql(question: str) -> str:
    system_prompt = dedent(
        f"""
        You are an AEC data specialist working with a Databricks lakehouse.
        Generate exactly one Databricks SQL SELECT query that answers the user's question.

        Database: {DATABASE_NAME}

        Available Gold tables and columns:
        {json.dumps(TABLE_CONTEXT, indent=2)}

        Rules:
        - Return only SQL, no explanation.
        - Use fully qualified table names like {DATABASE_NAME}.gold_bim_readiness_score.
        - Use only the listed Gold tables.
        - Do not write INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, MERGE, or TRUNCATE.
        - Prefer concise queries with ORDER BY and LIMIT when useful.
        - If the user asks about weakest, worst, lowest, or highest risk readiness, sort bim_readiness_score ascending.
        - If the user asks about missing metadata, use missing_rate and missing_count.
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


def summarize_result(question: str, sql: str, rows: list[dict]) -> str:
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {
                "role": "system",
                "content": dedent(
                    """
                    You summarize Databricks SQL results for AEC stakeholders.
                    Be concise, practical, and specific.
                    Mention what the result means for BIM analytics, model readiness, operations handoff, or project teams when relevant.
                    Do not invent numbers beyond the provided rows.
                    """
                ),
            },
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

# COMMAND ----------

# MAGIC %md
# MAGIC ## Ask A BIM Lakehouse Question
# MAGIC
# MAGIC Try questions such as:
# MAGIC
# MAGIC - Which BIM categories have the weakest readiness scores?
# MAGIC - Which discipline has the most BIM records?
# MAGIC - Which fields have the worst metadata completeness?
# MAGIC - Which level has the most room area?
# MAGIC - How many doors are fire-rated versus non-fire-rated?
# MAGIC - Which MEP asset category has the most records?
# MAGIC - Which structural category has the most records?

# COMMAND ----------

question = dbutils.widgets.get("question").strip()
print(f"Question: {question}")

sql = generate_sql(question)
print("Generated SQL:")
print(sql)

result_df = spark.sql(sql)
display(result_df)

rows = [row.asDict(recursive=True) for row in result_df.limit(20).collect()]
answer = summarize_result(question, sql, rows)

print("Plain-English answer:")
print(answer)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Example Questions For Interview Demo
# MAGIC
# MAGIC Use the `question` widget at the top of the notebook and rerun the previous cell.
# MAGIC
# MAGIC ```text
# MAGIC Which BIM categories have the weakest readiness scores?
# MAGIC ```
# MAGIC
# MAGIC ```text
# MAGIC Summarize the model inventory by discipline.
# MAGIC ```
# MAGIC
# MAGIC ```text
# MAGIC Which key fields have the highest missing metadata rates?
# MAGIC ```
# MAGIC
# MAGIC ```text
# MAGIC Which level has the most room area?
# MAGIC ```
# MAGIC
# MAGIC ```text
# MAGIC How many doors are fire-rated versus non-fire-rated?
# MAGIC ```
# MAGIC
# MAGIC ```text
# MAGIC Which MEP asset categories have the most records?
# MAGIC ```

