from sqlalchemy import create_engine, text

DB_CONFIG = {
    'host': '10.18.120.240',
    'port': 35432,
    'database': 'equipment_mechanism',
    'user': 'postgres',
    'password': '6edef2d746f2274cab951a452d5fc13d',
}

conn_str = f"postgresql+pg8000://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
engine = create_engine(conn_str)

with engine.connect() as conn:
    print("--- Check Alarms for Result 19706 ---")
    query = text("SELECT id, alarm_code, alarm_msg, device_id FROM biz.alarm WHERE result_id = 19706")
    rows = conn.execute(query).fetchall()
    
    print(f"Found {len(rows)} alarms.")
    for row in rows:
        print(row)
