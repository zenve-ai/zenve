import sys
from typing import Any

from sqlalchemy import text

from zenve_db.database import make_session


def clean_table(table_name: str) -> None:
    """Delete all rows from a table by name.

    Args:
        table_name: Name of the table to truncate (e.g., "runs", "agents")
    """
    db = make_session()
    try:
        query = text(f"DELETE FROM {table_name}")
        result: Any = db.execute(query)
        db.commit()

        print(f"Deleted {result.rowcount} rows from {table_name}")
    except Exception as e:
        db.rollback()
        raise RuntimeError(f"Failed to clean table {table_name}: {e}") from e
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python examples/clean_table.py <table_name>")
        sys.exit(1)

    table = sys.argv[1]
    clean_table(table)
