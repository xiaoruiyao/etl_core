"""
SPR ETL 迁移验证脚本
"""
from sqlalchemy import create_engine, text
import json

DB_CONFIG = {
    'host': '10.18.120.240',
    'port': 35432,
    'database': 'equipment_mechanism',
    'user': 'postgres',
    'password': '6edef2d746f2274cab951a452d5fc13d',
    'driver': 'pg8000'
}

def verify_spr_migration(result_id):
    conn_str = f"postgresql+pg8000://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    engine = create_engine(conn_str)
    
    with engine.connect() as conn:
        print(f'=== 验证 SPR 迁移 id={result_id} ===\n')
        
        # 1. biz.result
        print('--- biz.result ---')
        r = conn.execute(text('SELECT id, source_id, cyclenumber, device_name, craft_type, result_status, key_value, cycle_time FROM biz.result WHERE source_id = :id AND craft_type = :craft'), {"id": result_id, "craft": "SPR"}).fetchone()
        if r:
            print(f'  id (auto): {r[0]}')
            print(f'  source_id: {r[1]}')
            print(f'  cyclenumber: {r[2]}')
            print(f'  device_name: {r[3]}')
            print(f'  craft_type: {r[4]}')
            print(f'  result_status: {r[5]} (1=OK, 0=NOK)')
            print(f'  key_value: {r[6]}')
            print(f'  cycle_time: {r[7]}')
            result_db_id = r[0]  # 使用自动生成的 id
        else:
            print('  未找到记录!')
            return
        
        # 2. biz.curve
        print('\n--- biz.curve ---')
        curves = conn.execute(text("SELECT curve_type, jsonb_array_length(data_points->'x') as points FROM biz.curve WHERE result_id = :id"), {"id": result_db_id}).fetchall()
        for c in curves:
            print(f'  {c[0]}: {c[1]} 个数据点')
        
        # 3. biz.step
        print('\n--- biz.step ---')
        s = conn.execute(text('SELECT step_index, step_name, step_result, step_value FROM biz.step WHERE result_id = :id'), {"id": result_db_id}).fetchone()
        if s:
            print(f'  step_index: {s[0]}')
            print(f'  step_name: {s[1]}')
            print(f'  step_result: {s[2]}')
            print(f'  step_value: {s[3]}')
        
        # 4. biz.extension
        print('\n--- biz.extension ---')
        e = conn.execute(text('SELECT extra_data FROM biz.extension WHERE result_id = :id'), {"id": result_db_id}).fetchone()
        if e:
            data = json.loads(e[0]) if isinstance(e[0], str) else e[0]
            for k, v in data.items():
                print(f'  {k}: {v}')
        
        # 5. biz.program
        print('\n--- biz.program ---')
        p = conn.execute(text('SELECT p.program_id, p.version, p.program_name, p.craft_type FROM biz.result r JOIN biz.program p ON r.program_ver_id = p.id WHERE r.id = :id'), {"id": result_db_id}).fetchone()
        if p:
            print(f'  program_id: {p[0]}')
            print(f'  version: {p[1]}')
            print(f'  program_name: {p[2]}')
            print(f'  craft_type: {p[3]}')
        
        print('\n✅ 验证完成!')

if __name__ == "__main__":
    import sys
    result_id = int(sys.argv[1]) if len(sys.argv) > 1 else 583435
    verify_spr_migration(result_id)
