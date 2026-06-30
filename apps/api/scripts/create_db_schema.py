from __future__ import annotations

from app.core.database import create_database_schema


if __name__ == "__main__":
    create_database_schema()
    print("PolarYix database schema created or already up to date.")
