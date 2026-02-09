
import time
from sqlalchemy import create_engine, text

# DB Config
DB_CONFIG = {
    'host': '10.18.120.240',
    'port': 35432,
    'database': 'equipment_mechanism',
    'user': 'postgres',
    'password': '6edef2d746f2274cab951a452d5fc13d',
    'driver': 'pg8000'
}

conn_str = f"postgresql+{DB_CONFIG['driver']}://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
engine = create_engine(conn_str)

def get_counts():
    with engine.connect() as conn:
        fds_count = conn.execute(text("SELECT count(*) FROM biz.result WHERE craft_type = 'FDS_DEFAULT'")).scalar()
        spr_count = conn.execute(text("SELECT count(*) FROM biz.result WHERE craft_type = 'SPR'")).scalar()
    return fds_count, spr_count

print("Measuring speed (10s interval)...")
start_fds, start_spr = get_counts()
time.sleep(10)
end_fds, end_spr = get_counts()

fds_speed = (end_fds - start_fds) / 10.0
spr_speed = (end_spr - start_spr) / 10.0

print(f"FDS: Start={start_fds}, End={end_fds}, Speed={fds_speed:.2f} rows/s")
print(f"SPR: Start={start_spr}, End={end_spr}, Speed={spr_speed:.2f} rows/s")
