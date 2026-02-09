
import sqlalchemy
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
engine = create_engine(conn_str, echo=True)

def apply_migration():
    with engine.connect() as conn:
        with conn.begin():
            try:
                # 1. Add column
                print("Adding parent_alarm_id column...")
                conn.execute(text('ALTER TABLE "biz"."alarm" ADD COLUMN IF NOT EXISTS "parent_alarm_id" int8 REFERENCES "biz"."alarm"("id");'))
                
                # 2. Add index
                print("Adding index...")
                conn.execute(text('CREATE INDEX IF NOT EXISTS idx_alarm_parent_id ON "biz"."alarm" ("parent_alarm_id");'))
                
                print("✅ Migration successful!")
            except Exception as e:
                print(f"❌ Migration failed: {e}")
                raise e

if __name__ == "__main__":
    apply_migration()
