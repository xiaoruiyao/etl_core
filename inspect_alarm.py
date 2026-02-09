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
    # Check simple query
    try:
        res = conn.execute(text("SELECT * FROM biz.alarm LIMIT 1"))
        print("Columns in biz.alarm:", res.keys())
    except Exception as e:
        print("Error selecting alarm:", e)

    # Check biz.device_uri just in case
    try:
        res = conn.execute(text("SELECT * FROM biz.device_uri LIMIT 1"))
        print("Columns in biz.device_uri:", res.keys())
    except:
        pass
