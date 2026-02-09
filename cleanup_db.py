from sqlalchemy import create_engine, text

def cleanup():
    print("Connecting to DB...")
    engine = create_engine('postgresql+pg8000://postgres:6edef2d746f2274cab951a452d5fc13d@10.18.120.240:35432/equipment_mechanism')
    with engine.connect() as conn:
        print("Dropping biz.curve...")
        conn.execute(text("DROP TABLE IF EXISTS biz.curve CASCADE"))
        # Also clean other tables to allow fresh migration
        print("Truncating other tables...")
        conn.execute(text("TRUNCATE TABLE biz.step, biz.alarm, biz.extension, biz.result, biz.program CASCADE"))
        conn.commit()
    print("Cleanup complete.")

if __name__ == "__main__":
    cleanup()
