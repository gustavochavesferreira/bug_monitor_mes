from models import init_db

if __name__ == "__main__":
    print("Creating database schema in PostgreSQL...")
    init_db()
    print("Done.")
