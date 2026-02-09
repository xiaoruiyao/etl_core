"""
查看 program 表所有记录
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

def check_programs():
    conn_str = f"postgresql+pg8000://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    engine = create_engine(conn_str)
    
    with engine.connect() as conn:
        count = conn.execute(text('SELECT COUNT(*) FROM biz.program')).scalar()
        print(f'=== biz.program (共 {count} 条) ===')
        result = conn.execute(text('SELECT id, program_id, parameter_type, upper_limit, lower_limit FROM biz.program'))
        for r in result.fetchall():
            print(f'  id={r[0]}, program_id={r[1][:25] if r[1] else ""}..., parameter_type={r[2]}, upper={r[3]}, lower={r[4]}')

if __name__ == "__main__":
    check_programs()
