"""
Custom Aurora DSQL database backend that handles async index creation.
"""

import re

from aurora_dsql_django.base import DatabaseWrapper as AuroraDSQLDatabaseWrapper
from aurora_dsql_django.schema import DatabaseSchemaEditor as AuroraDSQLSchemaEditor


class DatabaseSchemaEditor(AuroraDSQLSchemaEditor):
    """Custom schema editor that converts CREATE INDEX to CREATE INDEX ASYNC."""

    def execute(self, sql, params=()):
        """Override execute to convert CREATE INDEX to CREATE INDEX ASYNC."""
        if isinstance(sql, str):
            # Convert CREATE INDEX to CREATE INDEX ASYNC for Aurora DSQL
            if sql.strip().upper().startswith("CREATE INDEX"):
                # Replace CREATE INDEX with CREATE INDEX ASYNC
                sql = re.sub(
                    r"^CREATE INDEX\b", "CREATE INDEX ASYNC", sql, flags=re.IGNORECASE
                )
            elif sql.strip().upper().startswith("CREATE UNIQUE INDEX"):
                # Replace CREATE UNIQUE INDEX with CREATE UNIQUE INDEX ASYNC
                sql = re.sub(
                    r"^CREATE UNIQUE INDEX\b",
                    "CREATE UNIQUE INDEX ASYNC",
                    sql,
                    flags=re.IGNORECASE,
                )

        return super().execute(sql, params)


class DatabaseWrapper(AuroraDSQLDatabaseWrapper):
    """Custom Aurora DSQL database wrapper with async index support."""

    SchemaEditorClass = DatabaseSchemaEditor
