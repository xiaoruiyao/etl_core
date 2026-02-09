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

def backfill_device_ids():
    with engine.begin() as conn: # Use begin() for transaction
        print("🚀 Starting backfill of biz.alarm.device_id...")
        
        # Check counts before
        before_count = conn.execute(text("SELECT COUNT(*) FROM biz.alarm WHERE device_id IS NULL AND parent_alarm_id IS NULL")).scalar()
        print(f"📉 Root alarms with NULL device_id before: {before_count}")
        
        # Execute Update
        # Note: syntax for UPDATE with JOIN varies by DB. PostgreSQL supports FROM.
        update_sql = text("""
            UPDATE biz.alarm
            SET device_id = r.device_name
            FROM biz.result r
            WHERE biz.alarm.result_id = r.id
              AND biz.alarm.parent_alarm_id IS NULL
              AND biz.alarm.device_id IS NULL
        """)
        
        result = conn.execute(update_sql)
        print(f"✅ Updated {result.rowcount} rows.")
        
        # Check counts after
        after_count = conn.execute(text("SELECT COUNT(*) FROM biz.alarm WHERE device_id IS NULL AND parent_alarm_id IS NULL")).scalar()
        print(f"📈 Root alarms with NULL device_id after: {after_count}")

if __name__ == "__main__":
    backfill_device_ids()
