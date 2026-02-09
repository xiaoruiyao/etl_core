
import sqlalchemy
from sqlalchemy import create_engine, text
import json
from datetime import datetime

def json_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, bytes):
        return f"<binary data length={len(obj)}>"
    return str(obj)

def verify_data(target_id):
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
    
    print(f"=== VERIFICATION FOR ID {target_id} ===")
    
    with engine.connect() as conn:
        # 1. Check Result (and Program link)
        print("\n--- [biz.result] ---")
        res = conn.execute(text(f"SELECT * FROM biz.result WHERE id = {target_id}"))
        row = res.fetchone()
        if row:
            keys = res.keys()
            print({k: json_serializer(v) for k, v in zip(keys, row)})
            
            prog_fk = row._mapping['program_ver_id'] if 'program_ver_id' in row._mapping else row[8] # Index fallback
            print(f"  > Linked Program FK: {prog_fk}")
            
            # Check Program
            print("\n--- [biz.program] ---")
            prog = conn.execute(text(f"SELECT * FROM biz.program WHERE id = {prog_fk}"))
            p_row = prog.fetchone()
            if p_row:
                p_keys = prog.keys()
                print({k: json_serializer(v) for k, v in zip(p_keys, p_row)})
            else:
                print("  ❌ Linked Program not found!")
        else:
            print("❌ Result not found!")

        # 2. Check Steps
        print("\n--- [biz.step] (Top 3) ---")
        steps = conn.execute(text(f"SELECT * FROM biz.step WHERE result_id = {target_id} ORDER BY step_index LIMIT 3"))
        rows = steps.fetchall()
        for r in rows:
            print({k: json_serializer(v) for k, v in zip(steps.keys(), r)})
            
        # 3. Check Alarm
        print("\n--- [biz.alarm] ---")
        cur = conn.execute(text(f"SELECT * FROM biz.alarm WHERE result_id = {target_id}"))
        rows = cur.fetchall()
        for r in rows:
             print({k: json_serializer(v) for k, v in zip(cur.keys(), r)})
        if not rows:
             print("No Alarm records found.")
            
        # 3. Check Extension (KPIs)
        print("\n--- [biz.extension] ---")
        ext = conn.execute(text(f"SELECT * FROM biz.extension WHERE result_id = {target_id}"))
        e_row = ext.fetchone()
        if e_row:
             print({k: json_serializer(v) for k, v in zip(ext.keys(), e_row)})
        else:
            print("❌ Extension not found")

        # 4. Check Curve
        print("\n--- [biz.curve] ---")
        cur = conn.execute(text(f"SELECT id, result_id, step, start_time, end_time, curve_type, jsonb_array_length(data_points->'x') as points_count FROM biz.curve WHERE result_id = {target_id} ORDER BY step, curve_type"))
        c_rows = cur.fetchall()
        for r in c_rows:
             print({k: json_serializer(v) for k, v in zip(cur.keys(), r)})
        if not c_rows:
            print("❌ Curve not found")

if __name__ == "__main__":
    import sys
    target = 251067
    if len(sys.argv) > 1:
        target = int(sys.argv[1])
    verify_data(target)
