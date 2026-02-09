"""
查看同一 id 在 bs_spr_detail 中有多少行
"""
from sqlalchemy import create_engine, text

DB_CONFIG = {
    'host': '10.18.120.240',
    'port': 35432,
    'database': 'equipment_mechanism',
    'user': 'postgres',
    'password': '6edef2d746f2274cab951a452d5fc13d',
    'driver': 'pg8000'
}

def check_id_rows():
    conn_str = f"postgresql+pg8000://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    engine = create_engine(conn_str)
    
    with engine.connect() as conn:
        print('=== 查看 id=583435 在 bs_spr_detail 中的所有行 ===')
        result = conn.execute(text('''
            SELECT id, parameter_type, limit_high, limit_low, final_force, final_stroke, velocity, cycle_time
            FROM origin.bs_spr_detail 
            WHERE id = 583435
            ORDER BY parameter_type
        '''))
        
        rows = list(result)
        print(f'共 {len(rows)} 行')
        for row in rows:
            print(f'  id={row[0]}, parameter_type={row[1]}, limit_high={row[2]}, limit_low={row[3]}')

if __name__ == "__main__":
    check_id_rows()
