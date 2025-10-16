"""
Custom SQLAlchemy types for cross-database compatibility
"""
import uuid
import json
from sqlalchemy import TypeDecorator, String, CHAR, Text
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID, JSONB as PostgreSQLJSONB, ARRAY as PostgreSQLARRAY


class GUID(TypeDecorator):
    """
    Platform-independent GUID type.

    Uses PostgreSQL's UUID type when available, otherwise uses
    CHAR(36) for SQLite and other databases, storing as stringified hex values.

    This ensures UUIDs work correctly in both production (PostgreSQL) and
    testing (SQLite) environments.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        """
        Select the appropriate type based on the database dialect.

        - PostgreSQL: Use native UUID type
        - SQLite/Others: Use CHAR(36) to store UUID as string
        """
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PostgreSQLUUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        """
        Convert Python UUID to database-appropriate format.

        Args:
            value: UUID instance, string, or None
            dialect: Database dialect

        Returns:
            - PostgreSQL: UUID instance
            - SQLite: String representation of UUID
            - None if value is None
        """
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value) if not isinstance(value, uuid.UUID) else value
        else:
            if not isinstance(value, uuid.UUID):
                return str(value)
            else:
                return str(value)

    def process_result_value(self, value, dialect):
        """
        Convert database value back to Python UUID.

        Args:
            value: Database value (UUID or string)
            dialect: Database dialect

        Returns:
            UUID instance or None
        """
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            return uuid.UUID(value)
        return value


class JSON(TypeDecorator):
    """
    Platform-independent JSON type.

    Uses PostgreSQL's JSONB type when available, otherwise uses
    TEXT for SQLite and other databases, storing as JSON strings.

    This ensures JSON columns work correctly in both production (PostgreSQL) and
    testing (SQLite) environments.
    """
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        """
        Select the appropriate type based on the database dialect.

        - PostgreSQL: Use native JSONB type
        - SQLite/Others: Use TEXT to store JSON as string
        """
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PostgreSQLJSONB())
        else:
            return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        """
        Convert Python dict/list to database-appropriate format.

        Args:
            value: Dict, list, or None
            dialect: Database dialect

        Returns:
            - PostgreSQL: Python dict/list (JSONB handles serialization)
            - SQLite: JSON string
            - None if value is None
        """
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            return json.dumps(value)

    def process_result_value(self, value, dialect):
        """
        Convert database value back to Python dict/list.

        Args:
            value: Database value (dict or JSON string)
            dialect: Database dialect

        Returns:
            Python dict/list or None
        """
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, str):
                return json.loads(value)
            return value


class StringArray(TypeDecorator):
    """
    Platform-independent String Array type.

    Uses PostgreSQL's ARRAY(Text) type when available, otherwise uses
    TEXT for SQLite and other databases, storing as JSON array strings.

    This ensures array columns work correctly in both production (PostgreSQL) and
    testing (SQLite) environments.
    """
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        """
        Select the appropriate type based on the database dialect.

        - PostgreSQL: Use native ARRAY(Text) type
        - SQLite/Others: Use TEXT to store array as JSON string
        """
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PostgreSQLARRAY(Text))
        else:
            return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        """
        Convert Python list to database-appropriate format.

        Args:
            value: List of strings or None
            dialect: Database dialect

        Returns:
            - PostgreSQL: Python list (ARRAY handles it)
            - SQLite: JSON string
            - None if value is None
        """
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            return json.dumps(value)

    def process_result_value(self, value, dialect):
        """
        Convert database value back to Python list.

        Args:
            value: Database value (list or JSON string)
            dialect: Database dialect

        Returns:
            Python list or None
        """
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, str):
                return json.loads(value)
            return value
