import json
import os
import re
from textwrap import dedent

import pandas as pd
import streamlit as st
from databricks import sql
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config, oauth_service_principal
from openai import OpenAI


DATABASE_NAME = os.getenv("BIMOPS_DATABASE", "bimops_ai")
DATABRICKS_HOST = os.getenv("DATABRICKS_HOST", "")
DATABRICKS_WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID", "")


CURATED_TABLE_DESCRIPTIONS = {
    "gold_asset_identity_readiness": "Asset identity completion rates based on mark, family, type, manufacturer, model, and related fields.",
    "gold_bim_readiness_score": "BIM readiness score by category based on metadata completeness.",
    "gold_door_fire_rating_summary": "Fire-rated versus non-fire-rated door summary.",
    "gold_key_field_completeness": "Completeness and missing-rate metrics for key BIM metadata fields.",
    "gold_mep_inventory_summary": "MEP inventory summary across mechanical, electrical, lighting, data, and HVAC categories.",
    "gold_metadata_quality": "Broad metadata quality and missing-rate metrics across model categories and fields.",
    "gold_model_inventory_by_category": "BIM record counts grouped by element category.",
    "gold_model_inventory_by_discipline": "BIM record counts grouped by architecture, electrical, mechanical, and structural disciplines.",
    "gold_program_area_by_occupancy": "Program area and room count by occupancy or space-use classification.",
    "gold_room_area_by_level": "Room area summarized by building level.",
    "gold_structural_inventory_summary": "Structural inventory summary across columns, foundations, and framing.",
    "gold_wall_area_by_function": "Wall area by wall function.",
}


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


st.set_page_config(
    page_title="BIMOps Copilot",
    page_icon="🏗️",
    layout="wide",
)


st.markdown(
    """
    <style>
    .main .block-container {
        padding-top: 2rem;
        max-width: 1280px;
    }
    .bimops-header {
        background: #17202A;
        color: white;
        padding: 24px 28px;
        border-radius: 8px;
        border-left: 8px solid #F2B705;
    }
    .bimops-header h1 {
        margin: 0;
        font-size: 34px;
        letter-spacing: 0;
    }
    .bimops-header p {
        margin: 10px 0 0 0;
        color: #D6DEE8;
        font-size: 16px;
    }
    .metric-card {
        border: 1px solid #E4E7EC;
        border-radius: 8px;
        padding: 16px;
        background: #FFFFFF;
    }
    .small-label {
        color: #667085;
        font-size: 13px;
        font-weight: 600;
        text-transform: uppercase;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def connection_ready():
    required = {
        "DATABRICKS_HOST": DATABRICKS_HOST,
        "DATABRICKS_WAREHOUSE_ID": DATABRICKS_WAREHOUSE_ID,
        "DATABRICKS_CLIENT_ID": os.getenv("DATABRICKS_CLIENT_ID", ""),
        "DATABRICKS_CLIENT_SECRET": os.getenv("DATABRICKS_CLIENT_SECRET", ""),
    }
    missing = [name for name, value in required.items() if not value]
    return missing


@st.cache_data(ttl=3600)
def get_warehouse_connection_details():
    workspace = WorkspaceClient()
    warehouse = workspace.warehouses.get(id=DATABRICKS_WAREHOUSE_ID)
    if not warehouse.odbc_params:
        raise ValueError("The selected SQL warehouse did not return connection details.")

    return {
        "server_hostname": warehouse.odbc_params.hostname,
        "http_path": warehouse.odbc_params.path,
    }


def credential_provider():
    config = Config(
        host=DATABRICKS_HOST,
        client_id=os.getenv("DATABRICKS_CLIENT_ID"),
        client_secret=os.getenv("DATABRICKS_CLIENT_SECRET"),
    )
    return oauth_service_principal(config)


def get_connection():
    details = get_warehouse_connection_details()
    return sql.connect(
        server_hostname=details["server_hostname"],
        http_path=details["http_path"],
        credentials_provider=credential_provider,
    )


@st.cache_data(ttl=300)
def run_sql(query):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            columns = [column[0] for column in cursor.description] if cursor.description else []
    return pd.DataFrame(rows, columns=columns)


@st.cache_data(ttl=300)
def get_gold_tables():
    tables_df = run_sql(f"SHOW TABLES IN {DATABASE_NAME}")
    if "tableName" not in tables_df.columns:
        return []
    return sorted(
        table_name
        for table_name in tables_df["tableName"].tolist()
        if str(table_name).startswith("gold_")
    )


@st.cache_data(ttl=300)
def get_table_columns(table_name):
    columns_df = run_sql(f"DESCRIBE TABLE {DATABASE_NAME}.{table_name}")
    if "col_name" not in columns_df.columns:
        return []
    columns = []
    for value in columns_df["col_name"].tolist():
        value = str(value)
        if value and not value.startswith("#"):
            columns.append(value)
    return columns


def get_table_context():
    context = {}
    for table_name in get_gold_tables():
        context[table_name] = {
            "description": CURATED_TABLE_DESCRIPTIONS.get(
                table_name,
                "Gold analytics table generated from cleaned BIM data.",
            ),
            "columns": get_table_columns(table_name),
        }
    return context


def clean_sql(query):
    cleaned = query.strip()
    cleaned = re.sub(r"^```sql", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"^```", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    return cleaned.rstrip(";")


def referenced_tables(query, table_context):
    lowered = query.lower()
    return {
        table_name
        for table_name in table_context
        if table_name.lower() in lowered
    }


def validate_sql(query, table_context):
    cleaned = clean_sql(query)
    lowered = cleaned.lower()

    if not lowered.startswith("select"):
        raise ValueError("Only SELECT statements are allowed.")

    padded = f" {lowered} "
    for keyword in BLOCKED_SQL_KEYWORDS:
        if re.search(rf"\b{keyword}\b", padded):
            raise ValueError(f"Blocked SQL keyword detected: {keyword}")

    used_tables = referenced_tables(cleaned, table_context)
    if not used_tables:
        raise ValueError("The generated SQL must reference at least one known Gold table.")

    for table_name in used_tables:
        if not table_name.startswith("gold_"):
            raise ValueError(f"Only Gold tables are allowed. Found: {table_name}")

    return cleaned


def generate_sql(question, table_context):
    client = OpenAI(api_key=st.session_state.openai_api_key)
    system_prompt = dedent(
        f"""
        You are BIMOps Copilot, an AEC data assistant working with a Databricks lakehouse.

        Generate exactly one Databricks SQL SELECT query that answers the user's question.

        Database:
        {DATABASE_NAME}

        Available Gold tables:
        {json.dumps(table_context, indent=2)}

        Rules:
        - Return only SQL. Do not include markdown or explanation.
        - Use fully qualified table names like {DATABASE_NAME}.gold_model_inventory_by_category.
        - Use only the listed Gold tables.
        - Do not query Bronze or Silver tables.
        - Do not use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, MERGE, TRUNCATE, OPTIMIZE, or VACUUM.
        - Add ORDER BY and LIMIT when ranking categories, fields, levels, systems, or disciplines.
        - If the question asks what to improve, return rows that show the weakest readiness or highest missing rates.
        """
    )

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
    )
    return validate_sql(response.output_text, table_context)


def summarize_result(question, generated_sql, result_df):
    client = OpenAI(api_key=st.session_state.openai_api_key)
    rows = result_df.head(20).to_dict(orient="records")

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {
                "role": "system",
                "content": dedent(
                    """
                    You are BIMOps Copilot, an assistant for BIM, AEC data, and Databricks lakehouse analytics.

                    Response format:

                    Executive answer:
                    One concise paragraph answering the question.

                    Evidence from the lakehouse:
                    2-4 bullets using only the provided rows.

                    Recommended next action:
                    1-3 bullets focused on BIM data quality, coordination, operations handoff, or dashboard follow-up.

                    Do not invent numbers. Keep it practical and professional.
                    """
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "question": question,
                        "sql": generated_sql,
                        "rows": rows,
                    },
                    indent=2,
                    default=str,
                ),
            },
        ],
    )
    return response.output_text


def ask_copilot(question, table_context):
    generated_sql = generate_sql(question, table_context)
    result_df = run_sql(generated_sql)
    answer = summarize_result(question, generated_sql, result_df)
    return generated_sql, result_df, answer


st.markdown(
    """
    <div class="bimops-header">
      <h1>BIMOps Copilot</h1>
      <p>Ask governed BIM lakehouse questions across Revit-derived Gold tables, metadata quality, MEP assets, spatial program, and structural inventory.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

missing_config = connection_ready()
if missing_config:
    st.error("Missing required app configuration: " + ", ".join(missing_config))
    st.stop()

if "openai_api_key" not in st.session_state:
    st.session_state.openai_api_key = ""

with st.sidebar:
    st.subheader("BIMOps Lakehouse")
    st.caption(f"Database: `{DATABASE_NAME}`")
    st.caption(f"Warehouse resource: `{DATABRICKS_WAREHOUSE_ID}`")
    st.session_state.openai_api_key = st.text_input(
        "OpenAI API key",
        value=st.session_state.openai_api_key,
        type="password",
        help="Used only in this app session. Do not paste keys into screenshots.",
    )
    st.markdown("**Sample questions**")
    sample_questions = [
        "Which BIM categories have the weakest readiness scores, and what should the team improve first?",
        "Which key BIM metadata fields have the highest missing rates?",
        "Summarize the model inventory by discipline.",
        "Which MEP categories have the most assets?",
        "How many doors are fire-rated versus not fire-rated?",
        "Which structural materials have the highest modeled volume?",
        "What are the top data-quality risks in this BIM model?",
    ]
    selected_sample = st.selectbox("Choose a starter prompt", sample_questions)
    st.markdown("---")
    st.markdown("**Lakehouse Layers**")
    st.markdown("- Bronze: raw Revit schedule exports")
    st.markdown("- Silver: cleaned BIM element tables")
    st.markdown("- Gold: analytics-ready building intelligence")

table_context = get_table_context()
if not table_context:
    st.warning(f"No Gold tables found in `{DATABASE_NAME}`. Run the BIMOps ETL notebook first.")
    st.stop()

col_a, col_b, col_c = st.columns(3)
with col_a:
    st.metric("Gold tables", len(table_context))
with col_b:
    st.metric("Query mode", "Read-only")
with col_c:
    st.metric("AI layer", "SQL + summary")

if "messages" not in st.session_state:
    st.session_state.messages = []

question = st.chat_input("Ask a BIM lakehouse question...")

if st.button("Use selected sample question"):
    question = selected_sample

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sql"):
            with st.expander("Generated SQL"):
                st.code(message["sql"], language="sql")
        if message.get("data") is not None:
            st.dataframe(message["data"], use_container_width=True)

if question:
    if not st.session_state.openai_api_key:
        st.warning("Paste your OpenAI API key in the sidebar first.")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Querying BIMOps lakehouse..."):
            try:
                generated_sql, result_df, answer = ask_copilot(question, table_context)
                st.markdown(answer)
                with st.expander("Generated SQL", expanded=False):
                    st.code(generated_sql, language="sql")
                st.dataframe(result_df, use_container_width=True)

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "sql": generated_sql,
                        "data": result_df,
                    }
                )
            except Exception as error:
                error_message = f"Error: {error}"
                st.error(error_message)
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": error_message,
                    }
                )

with st.expander("Available Gold tables"):
    table_rows = [
        {
            "table_name": table_name,
            "description": meta["description"],
            "columns": ", ".join(meta["columns"]),
        }
        for table_name, meta in table_context.items()
    ]
    st.dataframe(pd.DataFrame(table_rows), use_container_width=True)
