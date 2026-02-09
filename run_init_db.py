
import sqlalchemy
from sqlalchemy import create_engine, text

def init_db():
    DB_CONFIG = {
        'host': '10.18.120.240',
        'port': 35432,
        'database': 'equipment_mechanism',  
        'user': 'postgres',
        'password': '6edef2d746f2274cab951a452d5fc13d',
        'driver': 'pg8000'
    }
    
    conn_str = f"postgresql+{DB_CONFIG['driver']}://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    engine = create_engine(conn_str, echo=True)
    
    print("Reading init_db.sql...")
    with open('e:\\work_place\\fds_etl\\init_db.sql', 'r', encoding='utf-8') as f:
        sql = f.read()
        
    print("Executing SQL...")
    with engine.connect() as conn:
        # Split by simple ; might be brittle for stored procs, but simple DDL is fine
        # Alternatively, execute the whole block if driver supports it. 
        # pg8000 might prefer single statements, but let's try block first or split strictly.
        # This is a simple parser.
        statements = sql.split(';')
        for stmt in statements:
            if stmt.strip():
                try:
                    conn.execute(text(stmt))
                    conn.commit()
                except Exception as e:
                    print(f"Warning: {e}")
                    conn.rollback()
        
    print("Database initialized.")

if __name__ == "__main__":
    init_db()
