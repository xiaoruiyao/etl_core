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
engine = create_engine(conn_str, echo=False)

with engine.connect() as conn:
    print("Checking origin.bs_spr_detail_v2...")
    
    # Check Max ID
    max_id = conn.execute(text("SELECT MAX(id) FROM origin.bs_spr_detail_v2")).scalar()
    print(f"Max ID: {max_id}")
    
    # Check Max SID
    max_sid = conn.execute(text("SELECT MAX(sid) FROM origin.bs_spr_detail_v2")).scalar()
    print(f"Max SID: {max_sid}")

    # Check Min SID
    min_sid = conn.execute(text("SELECT MIN(sid) FROM origin.bs_spr_detail_v2")).scalar()
    print(f"Min SID: {min_sid}")

    # Check Count
    count = conn.execute(text("SELECT COUNT(*) FROM origin.bs_spr_detail_v2")).scalar()
    print(f"Count: {count}")
    
    # Sample top rows
    rows = conn.execute(text("SELECT sid, id FROM origin.bs_spr_detail_v2 ORDER BY sid LIMIT 5")).fetchall()
    print("Sample (sid, id):", rows)
