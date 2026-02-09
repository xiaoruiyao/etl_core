from sqlalchemy import create_engine, text
import time

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
    print("Checking biz.result count...")
    initial_count = conn.execute(text("SELECT COUNT(*) FROM biz.result")).scalar()
    print(f"Initial Count: {initial_count}")
    
    time.sleep(5)
    
    final_count = conn.execute(text("SELECT COUNT(*) FROM biz.result")).scalar()
    print(f"Final Count (after 5s): {final_count}")
    
    if final_count > initial_count:
        print("✅ ETL is working! Data count increased.")
    elif final_count == initial_count and final_count > 0:
         print("⚠️ ETL running but count stable (maybe catchup finished or slow?).")
    else:
         print("❓ ETL might not be inserting yet.")
