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
    print("--- Sampling biz.alarm ---")
    # Check if device_id is populated
    query = text("SELECT id, result_id, device_id, alarm_msg FROM biz.alarm LIMIT 10")
    rows = conn.execute(query).fetchall()
    for row in rows:
        print(row)
    
    print("\n--- Check count of alarms with NULL device_id ---")
    null_count = conn.execute(text("SELECT COUNT(*) FROM biz.alarm WHERE device_id IS NULL")).scalar()
    total_count = conn.execute(text("SELECT COUNT(*) FROM biz.alarm")).scalar()
    print(f"Total Alarms: {total_count}")
    print(f"Alarms with NULL device_id: {null_count}")

    print("\n--- Check specific device 'UB090RB03' ---")
    dev_query = text("SELECT COUNT(*) FROM biz.alarm WHERE device_id = 'UB090RB03'")
    dev_count = conn.execute(dev_query).scalar()
    print(f"Alarms for UB090RB03 by device_id: {dev_count}")
    
    # Check via result join for this device to see what we expected
    join_query = text("SELECT COUNT(*) FROM biz.alarm a JOIN biz.result r ON a.result_id = r.id WHERE r.device_name = 'UB090RB03'")
    join_count = conn.execute(join_query).scalar()
    print(f"Alarms for UB090RB03 by result join: {join_count}")
