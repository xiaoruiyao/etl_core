"""
查看 SPR 中的 parameter_type 分布
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

def check_parameter_types():
    conn_str = f"postgresql+pg8000://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    engine = create_engine(conn_str)
    
    with engine.connect() as conn:
        print('=== SPR parameter_type 分布 ===')
        result = conn.execute(text('''
            SELECT parameter_type, COUNT(*) as cnt
            FROM origin.bs_spr_detail
            GROUP BY parameter_type
            ORDER BY cnt DESC
        '''))
        for row in result:
            print(f'  {row[0]}: {row[1]} 条')
        
        print('\n=== 同一 program_identifier 是否有不同的 parameter_type ===')
        result = conn.execute(text('''
            SELECT program_identifier, COUNT(DISTINCT parameter_type) as type_count
            FROM origin.bs_spr_detail
            GROUP BY program_identifier
            HAVING COUNT(DISTINCT parameter_type) > 1
            LIMIT 10
        '''))
        rows = list(result)
        if rows:
            print(f'有 {len(rows)} 个 program_identifier 对应多种 parameter_type')
            for row in rows:
                print(f'  {row[0]}: {row[1]} 种')
        else:
            print('每个 program_identifier 只对应一种 parameter_type')

if __name__ == "__main__":
    check_parameter_types()
