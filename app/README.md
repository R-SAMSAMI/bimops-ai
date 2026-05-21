# BIMOps Copilot Databricks App

This folder contains a Streamlit app for Databricks Apps.

## Required Environment Variables

Set these in the Databricks App environment or secrets configuration:

```text
OPENAI_API_KEY
DATABRICKS_SERVER_HOSTNAME
DATABRICKS_HTTP_PATH
DATABRICKS_TOKEN
```

Optional:

```text
BIMOPS_DATABASE=bimops_ai
```

## How To Deploy

1. In Databricks, open **Apps**.
2. Create a new app.
3. Use this folder as the app source.
4. Add the required environment variables.
5. Start the app.

The app queries only Gold tables and blocks write/destructive SQL.
