import os
from sqlmodel import SQLModel, create_engine, Session

sqlite_file_name = os.getenv("DB_PATH", "bernabei.db")
sqlite_url = f"sqlite:///{sqlite_file_name}"

from sqlalchemy import text

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, echo=False, connect_args=connect_args)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

def verify_db_persistence():
    try:
        with Session(engine) as session:
            # Create a test table if not exists
            session.exec(text("CREATE TABLE IF NOT EXISTS _persistence_check (id INTEGER PRIMARY KEY, timestamp TEXT)"))
            session.commit()
            
            # Insert a record
            import datetime
            ts = datetime.datetime.now().isoformat()
            session.exec(text(f"INSERT INTO _persistence_check (timestamp) VALUES ('{ts}')"))
            session.commit()
            
            # Read it back
            result = session.exec(text("SELECT count(*) FROM _persistence_check")).one()
            count = result[0] if result else 0
            
            print(f"✅ DB READ/WRITE TEST PASSED: Successfully wrote timestamp {ts}. Total records: {count}")
            return True
    except Exception as e:
        print(f"❌ DB READ/WRITE TEST FAILED: {e}")
        return False
