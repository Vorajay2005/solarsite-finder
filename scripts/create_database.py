import sqlite3
import os


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH      = os.path.join(PROJECT_ROOT, "database", "solar_site_finder.db")
SCHEMA_PATH  = os.path.join(PROJECT_ROOT, "database", "schema.sql")


def create_database():
    """Read schema.sql and execute it against the SQLite database."""
    print(f"Creating database at: {DB_PATH}")

    # Make sure the database/ folder exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    # Read the SQL schema file
    with open(SCHEMA_PATH, "r") as f:
        schema_sql = f.read()

   
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.executescript(schema_sql)
        conn.commit()
        print("All tables created successfully.")
    except sqlite3.Error as e:
        print(f"Error creating tables: {e}")
        raise
    finally:
        conn.close()
def verify_tables():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = cursor.fetchall()
    print("\nTables in database:")
    for (table_name,) in tables:
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        print(f"  {table_name} ({len(columns)} columns)")
    conn.close()
if __name__ == "__main__":
    create_database()
    verify_tables()
    print("\nDatabase setup complete. Next step: run scripts/load_datasets.py")
