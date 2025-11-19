# backend/init_db.py
from models import init_db

if __name__ == "__main__":
    print("Creating database and tables...")
    init_db()
    print("Done. Database created at backend/bugs.db (SQLite).")