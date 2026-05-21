# BIMOps Copilot Databricks App

This folder contains a Streamlit app for Databricks Apps.

## Required Environment Variables

Add a SQL warehouse resource in Databricks Apps:

```text
Resource type: SQL warehouse
Warehouse: Serverless Starter Warehouse
Permission: Can use
Resource key: sql-warehouse
```

The app receives the selected warehouse through `DATABRICKS_WAREHOUSE_ID`.
Databricks automatically provides app identity variables such as `DATABRICKS_HOST`,
`DATABRICKS_CLIENT_ID`, and `DATABRICKS_CLIENT_SECRET`.

Paste the OpenAI API key into the Streamlit sidebar when running a private demo.

## How To Deploy

1. In Databricks, open **Apps**.
2. Create a new app.
3. Use the repository as the app source.
4. Add the SQL warehouse resource with key `sql-warehouse`.
5. Start the app.

The app queries only Gold tables and blocks write/destructive SQL.
