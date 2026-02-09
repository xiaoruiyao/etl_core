from sqlalchemy import create_engine, text
engine = create_engine('postgresql+pg8000://postgres:6edef2d746f2274cab951a452d5fc13d@10.18.120.240:35432/equipment_mechanism')
with engine.connect() as conn:
    try:
        result = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'biz' AND table_name = 'device_uri'"))
        print(result.fetchall())
    except Exception as e:
        print(e)
