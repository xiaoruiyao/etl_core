import os
import json
from sqlalchemy import create_engine, text

# Database Configuration
DB_CONFIG = {
    "user": "postgres",
    "password": "tex", # Placeholder, relies on env or hardcoded string in other files. 
                       # I'll use the one from inspect_schema.py: 6edef2d746f2274cab951a452d5fc13d
    "host": "10.18.120.240",
    "port": "35432",
    "database": "equipment_mechanism",
    "driver": "pg8000"
}

CONN_STR = f"postgresql+pg8000://postgres:6edef2d746f2274cab951a452d5fc13d@10.18.120.240:35432/equipment_mechanism"

def init_hierarchy():
    engine = create_engine(CONN_STR)
    
    with engine.begin() as conn:
        print("1. Creating biz.structure table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "biz"."structure" (
                "id" bigserial PRIMARY KEY,
                "name" varchar(128) NOT NULL,
                "level_type" varchar(32) NOT NULL,
                "parent_id" int8,
                "path" varchar(255) NOT NULL,
                "device_name" varchar(64),
                "attributes" jsonb,
                "create_time" timestamp(6) DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_structure_parent ON "biz"."structure" ("parent_id");
            CREATE INDEX IF NOT EXISTS idx_structure_path ON "biz"."structure" ("path" varchar_pattern_ops);
            CREATE INDEX IF NOT EXISTS idx_structure_device ON "biz"."structure" ("device_name");
        """))

        print("2. Creating biz.point table...")
        conn.execute(text("""
           CREATE TABLE IF NOT EXISTS "biz"."point" (
                "id" bigserial PRIMARY KEY,
                "structure_id" int8 REFERENCES "biz"."structure"("id"),
                "device_id" varchar(64),
                "point_name" varchar(128),
                "point_uri" varchar(255),
                "group_path" varchar(255),
                "data_type" varchar(32),
                "is_ts" bool DEFAULT true
            );
            CREATE INDEX IF NOT EXISTS idx_point_structure ON "biz"."point" ("structure_id");
        """))
        
        print("3. Inserting Example Data...")
        # Clean up existing example data to avoid duplicates if re-run (optional, but good for dev)
        # For safety, I'll just check existence or insert if not exists, but simpler to just insert for this demo
        # assuming ID generation. To force specific relationships, I will use returning IDs or named insertion.
        
        # 3.1 Factory: Phoenix Factory
        # Path convention: /{id}/
        
        # Helper to insert and get ID
        def insert_node(name, level, parent_id, path_prefix, device_name=None, attrs=None):
            attrs_json = json.dumps(attrs) if attrs else 'null'
            # Fake query to get next ID is hard with auto-increment without executing.
            # So we insert and returning *
            
            # Construct basics
            if parent_id is None:
                parent_val = "NULL"
            else:
                parent_val = str(parent_id)
            
            d_name = f"'{device_name}'" if device_name else "NULL"
            
            # We insert with a placeholder path first, then update it, OR use a sequence? 
            # Easiest: Insert, get ID, update Path.
            res = conn.execute(text(f"""
                INSERT INTO "biz"."structure" (name, level_type, parent_id, path, device_name, attributes)
                VALUES ('{name}', '{level}', {parent_val}, '', {d_name}, '{attrs_json}')
                RETURNING id;
            """)).fetchone()
            new_id = res[0]
            
            # Calculate Path
            if parent_id:
                # Get parent path
                p_res = conn.execute(text(f"SELECT path FROM \"biz\".\"structure\" WHERE id={parent_id}")).fetchone()
                p_path = p_res[0]
                new_path = f"{p_path}{new_id}/"
            else:
                new_path = f"/{new_id}/"
            
            conn.execute(text(f"UPDATE \"biz\".\"structure\" SET path='{new_path}' WHERE id={new_id}"))
            print(f"   Created {level}: {name} (ID={new_id}, Path={new_path})")
            return new_id

        # Root: Phoenix Factory
        f_id = insert_node("凤凰工厂", "FACTORY", None, "")
        
        # Workshop: Welding
        w_id = insert_node("焊装车间", "WORKSHOP", f_id, "")
        
        # Line: UB1
        l_id = insert_node("下车体线UB1", "LINE", w_id, "")
        
        # Station: UB10900
        s_id = insert_node("UB10900工位", "STATION", l_id, "")
        
        # PLC: PLC3 (Level with Station, so parent is Line)
        plc_id = insert_node("PLC3", "PLC", l_id, "")
        
        # Device: UB090RB03 (Under Station, Controlled by PLC3)
        d_id = insert_node("UB090RB03", "DEVICE", s_id, "", device_name="UB090RB03", attrs={"plc_id": plc_id})
        
        # 3.2 Insert Point
        print("4. Inserting Point Data...")
        conn.execute(text(f"""
            INSERT INTO "biz"."point" (structure_id, device_id, point_name, point_uri, group_path, data_type)
            VALUES (
                {d_id}, 
                'UB090RB03', 
                'IO点位示例', 
                'opcua://test/io/1', 
                'fanuc机器人参数集/IO点位', 
                'float'
            )
        """))
        print("   Inserted Point for Device UB090RB03")

if __name__ == "__main__":
    try:
        init_hierarchy()
        print("✅ Migration Successful")
    except Exception as e:
        print(f"❌ Migration Failed: {e}")
