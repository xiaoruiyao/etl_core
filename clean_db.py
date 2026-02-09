from sqlalchemy import create_engine, text

# --- Database Configuration ---
DB_CONFIG = {
    'host': '10.18.120.240',
    'port': 35432,
    'database': 'equipment_mechanism',
    'user': 'postgres',
    'password': '6edef2d746f2274cab951a452d5fc13d',
}

conn_str = f"postgresql+pg8000://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
engine = create_engine(conn_str, echo=True)

TABLES_TO_TRUNCATE = [
    "biz.alarm",
    "biz.curve",
    "biz.step",
    "biz.extension",
    "biz.result",
    # "biz.program" # Optional: keep programs for now to avoid re-inserting if unnecessary
]

with engine.begin() as conn:
    print("🚀 Starting Database Cleanup...")
    for table in TABLES_TO_TRUNCATE:
        try:
            print(f"Dataset: Truncating {table}...")
            # Use CASCADE to handle FKs
            conn.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
            print(f"✅ Truncated {table}")
        except Exception as e:
            print(f"❌ Failed to truncate {table}: {e}")
            
    print("🏁 Cleanup Complete.")
