import sys
from datetime import datetime
from models import Base, engine, init_db

def reset_database():
    print("⚠️ WARNING: This will DROP ALL TABLES and all data will be lost!")
    confirm = input("Type 'YES' to proceed: ")
    if confirm != "YES":
        print("Aborted. No changes made.")
        sys.exit(0)

    print(f"[{datetime.now()}] Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print(f"[{datetime.now()}] Tables dropped.")

    print(f"[{datetime.now()}] Recreating tables...")
    init_db()
    print(f"[{datetime.now()}] Tables created.")
    print(f"[{datetime.now()}] Database reset complete.")

if __name__ == "__main__":
    reset_database()
