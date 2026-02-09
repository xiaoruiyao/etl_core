
from sqlalchemy import create_engine, text
from etl_fds_migration import DB_CONFIG

def clear_fds_data():
    conn_str = f"postgresql+{DB_CONFIG['driver']}://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    engine = create_engine(conn_str)
    
    print("WARNING: This will delete ALL FDS data (craft_type='FDS_DEFAULT') from biz schema.")
    print("Tables: biz.alarm, biz.curve, biz.step, biz.extension, biz.result")
    
    with engine.begin() as conn:
        # 1. Identify Result IDs to delete
        print("Identifying FDS records...")
        # We can delete directly using subqueries or just delete cascade if configured, 
        # but let's be explicit to avoid accidental cascade issues if FKs aren't set up that way.
        
        # Actually simplest is:
        # DELETE FROM biz.alarm WHERE result_id IN (SELECT id FROM biz.result WHERE craft_type = 'FDS_DEFAULT');
        # ...
        
        print("Deleting Alarms...")
        conn.execute(text("DELETE FROM biz.alarm WHERE result_id IN (SELECT id FROM biz.result WHERE craft_type = 'FDS_DEFAULT')"))
        
        print("Deleting Curves...")
        conn.execute(text("DELETE FROM biz.curve WHERE result_id IN (SELECT id FROM biz.result WHERE craft_type = 'FDS_DEFAULT')"))
        
        print("Deleting Steps...")
        conn.execute(text("DELETE FROM biz.step WHERE result_id IN (SELECT id FROM biz.result WHERE craft_type = 'FDS_DEFAULT')"))
        
        print("Deleting Extensions...")
        conn.execute(text("DELETE FROM biz.extension WHERE result_id IN (SELECT id FROM biz.result WHERE craft_type = 'FDS_DEFAULT')"))
        
        print("Deleting Results...")
        result = conn.execute(text("DELETE FROM biz.result WHERE craft_type = 'FDS_DEFAULT'"))
        
        print(f"✅ Deleted {result.rowcount} records from biz.result.")

if __name__ == "__main__":
    clear_fds_data()
