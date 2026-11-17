"""PostgreSQL Row-Level Security (RLS) policy helpers for Defense-in-Depth multi-tenancy."""


def generate_rls_policy_sql(table_name: str, agency_column: str = "agency_id") -> str:
    return f"""
    ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS {table_name}_tenant_isolation ON {table_name};
    CREATE POLICY {table_name}_tenant_isolation ON {table_name}
        USING (
            current_setting('app.current_agency_id', true) IS NULL
            OR current_setting('app.current_agency_id', true) = ''
            OR {agency_column}::text = current_setting('app.current_agency_id', true)
        );
    """
