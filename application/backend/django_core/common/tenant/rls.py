import re

_IDENTIFIER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _validate_identifier(value: str, label: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"Invalid SQL {label}: {value!r}")
    return value


def _policy_name(table_name: str) -> str:
    table = _validate_identifier(table_name, "table name")
    return _validate_identifier(f"{table[:40]}_tenant_isolation", "policy name")


def discover_tenant_relation_paths(model, *, include_self_agency: bool = False):
    """Return FK paths from a model to every reachable model with an agency FK."""
    def walk(current, visited, allow_self):
        if current in visited or not current._meta.managed:
            return []
        if allow_self:
            try:
                agency_field = current._meta.get_field("agency")
            except Exception:
                agency_field = None
            if agency_field is not None:
                return [([], agency_field)]
            if current._meta.app_label == "agencies" and current._meta.model_name == "agency":
                return [([], current._meta.pk)]
        results = []
        next_visited = set(visited)
        next_visited.add(current)
        for field in current._meta.concrete_fields:
            if not field.is_relation or not (field.many_to_one or field.one_to_one):
                continue
            parent = field.remote_field.model
            if parent is None or parent is current or not parent._meta.managed:
                continue
            for parent_path, agency_field in walk(parent, next_visited, True):
                results.append(([field, *parent_path], agency_field))
        return results

    return walk(model, set(), include_self_agency)


def _render_relation_conditions(relation_paths, *, child_agency_column=None, require_any=True):
    path_sql = []
    presence_sql = []
    for path_index, (fields, agency_field) in enumerate(relation_paths):
        if not fields:
            raise ValueError("A child-table relation path must contain at least one FK.")
        previous_alias = None
        from_clause = None
        join_clauses = []
        where_conditions = []
        first_fk = None
        for step_index, field in enumerate(fields):
            fk_column = _validate_identifier(field.column, "foreign key column")
            parent_model = field.remote_field.model
            parent_table = _validate_identifier(parent_model._meta.db_table, "parent table")
            parent_pk = _validate_identifier(field.target_field.column, "parent primary key")
            alias = f"p{path_index}_{step_index}"
            if step_index == 0:
                first_fk = fk_column
                from_clause = f'FROM "{parent_table}" AS "{alias}"'
                where_conditions.append(f'"{alias}"."{parent_pk}" = "{fk_column}"')
            else:
                join_clauses.append(
                    f'JOIN "{parent_table}" AS "{alias}" ON "{alias}"."{parent_pk}" = "{previous_alias}"."{fk_column}"'
                )
            previous_alias = alias
        agency_column = _validate_identifier(agency_field.column, "parent agency column")
        where_conditions.append(
            f'("{previous_alias}"."{agency_column}" IS NULL OR '
            f'"{previous_alias}"."{agency_column}"::text = NULLIF(current_setting(\'app.current_agency_id\', true), \'\'))'
        )
        exists_sql = " ".join([from_clause, *join_clauses, "WHERE " + " AND ".join(where_conditions)])
        path_sql.append(f'("{first_fk}" IS NULL OR EXISTS (SELECT 1 {exists_sql}))')
        presence_sql.append(f'"{first_fk}" IS NOT NULL')

    if not path_sql:
        return ""
    at_least_one = " OR ".join(presence_sql)
    path_conditions = "(" + " AND ".join(path_sql) + ")"
    conditions = []
    if child_agency_column:
        child_column = _validate_identifier(child_agency_column, "child agency column")
        child_matches = f'"{child_column}"::text = NULLIF(current_setting(\'app.current_agency_id\', true), \'\')'
        conditions.append(f'("{child_column}" IS NULL OR {child_matches})')
        conditions.append(f'({child_matches} OR ({at_least_one}))')
    elif require_any:
        conditions.append(f"({at_least_one})")
    conditions.append(path_conditions)
    return " AND ".join(conditions)


def generate_rls_policy_sql(
    table_name: str,
    agency_column: str = "agency_id",
    relation_paths=None,
    *,
    allow_global_rows: bool = False,
    allow_related_rows: bool = False,
) -> str:
    """Create fail-closed RLS; nullable agency rows need a tenant-owned parent."""
    table = _validate_identifier(table_name, "table name")
    column = _validate_identifier(agency_column, "column name")
    policy = _policy_name(table)
    current = "NULLIF(current_setting('app.current_agency_id', true), '')"
    agency_match = f'"{column}"::text = {current}'
    strict_relations = _render_relation_conditions(relation_paths or [], require_any=False)
    related_rows = _render_relation_conditions(relation_paths or [], require_any=True)

    if allow_global_rows:
        read_match = f'("{column}" IS NULL OR {agency_match})'
    elif allow_related_rows and related_rows:
        read_match = f'({agency_match} OR ("{column}" IS NULL AND {related_rows}))'
    else:
        read_match = agency_match
    if strict_relations:
        read_match = f"({read_match} AND {strict_relations})"

    if allow_global_rows:
        write_match = agency_match
    elif allow_related_rows and related_rows:
        write_match = f'({agency_match} OR ("{column}" IS NULL AND {related_rows}))'
    else:
        write_match = agency_match
    if strict_relations:
        write_match = f"({write_match} AND {strict_relations})"

    read_condition = f"({current} IS NOT NULL AND {read_match})"
    write_condition = f"({current} IS NOT NULL AND {write_match})"
    return f'''
        ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS "{policy}" ON "{table}";
        CREATE POLICY "{policy}" ON "{table}"
        USING (current_setting('app.tenant_bypass', true) = 'on' OR {read_condition})
        WITH CHECK (current_setting('app.tenant_bypass', true) = 'on' OR {write_condition});
    '''


def generate_related_rls_policy_sql(table_name: str, relation_paths, *, child_agency_column=None) -> str:
    """Create fail-closed RLS for child tables without a non-null agency_id."""
    table = _validate_identifier(table_name, "table name")
    if not relation_paths:
        raise ValueError("At least one tenant relation path is required.")
    policy = _policy_name(table)
    current = "NULLIF(current_setting('app.current_agency_id', true), '')"
    relation_condition = _render_relation_conditions(
        relation_paths, child_agency_column=child_agency_column, require_any=True
    )
    condition = f"({current} IS NOT NULL AND {relation_condition})"
    return f'''
        ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY;
        ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS "{policy}" ON "{table}";
        CREATE POLICY "{policy}" ON "{table}"
        USING (current_setting('app.tenant_bypass', true) = 'on' OR {condition})
        WITH CHECK (current_setting('app.tenant_bypass', true) = 'on' OR {condition});
    '''


def generate_user_scope_policy_sql(
    table_name: str,
    user_columns: list[str] | None = None,
    *,
    agency_column: str | None = None,
    agency_scope: bool = False,
    bypass_only: bool = False,
) -> str:
    """RLS for user-owned records or platform-only tables with no agency FK."""
    table = _validate_identifier(table_name, "table name")
    policy_suffix = "platform_only" if bypass_only else "user_scope"
    policy = _validate_identifier(f"{table[:40]}_{policy_suffix}", "policy name")
    if bypass_only:
        predicate = "current_setting('app.tenant_bypass', true) = 'on'"
    else:
        columns = [_validate_identifier(c, "user column") for c in (user_columns or [])]
        if not columns:
            raise ValueError("At least one user column is required for user-scoped RLS.")
        user_match = " OR ".join(
            f'"{column}"::text = NULLIF(current_setting(\'app.current_user_id\', true), \'\')'
            for column in columns
        )
        if agency_column:
            agency = _validate_identifier(agency_column, "agency column")
            if agency_scope:
                predicate = (
                    f'("{agency}"::text = NULLIF(current_setting(\'app.current_agency_id\', true), \'\') '
                    f'OR ("{agency}" IS NULL AND ({user_match})))'
                )
            else:
                predicate = (
                    f'(({user_match}) AND ("{agency}" IS NULL OR '
                    f'"{agency}"::text = NULLIF(current_setting(\'app.current_agency_id\', true), \'\')))' 
                )
        else:
            predicate = f"({user_match})"
    return f'''
        ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY;
        ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS "{policy}" ON "{table}";
        CREATE POLICY "{policy}" ON "{table}" FOR ALL
        USING (current_setting('app.tenant_bypass', true) = 'on' OR {predicate})
        WITH CHECK (current_setting('app.tenant_bypass', true) = 'on' OR {predicate});
    '''
