"""
Drop every table defined on the SQLAlchemy Base (full metadata wipe).

Also removes alembic_version if present so you can run migrations from a clean state.

Usage (from server/):

    uv run --package zenve-api python examples/reset_db.py
    uv run --package zenve-api python examples/reset_db.py -y
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import text

from zenve_db.database import Base, Session


def reset_db() -> None:
    db = Session()
    try:
        db.execute(text("DROP SCHEMA public CASCADE"))
        db.execute(text("CREATE SCHEMA public"))
        db.execute(text("DROP TABLE IF EXISTS alembic_version"))
        db.commit()
    except Exception as e:
        db.rollback()
        raise RuntimeError(f"Failed to reset database: {e}") from e
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Drop all application tables. Irreversible.",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Skip confirmation prompt",
    )
    args = parser.parse_args()

    if not args.yes:
        confirm = input(
            "This DESTROYS all ORM tables and alembic_version. Type 'yes' to continue: "
        )
        if confirm.strip() != "yes":
            print("Aborted.")
            sys.exit(0)

    reset_db()
    print("Done. Recreate schema with: just migrate  (or: uv run alembic upgrade head)")


if __name__ == "__main__":
    main()
