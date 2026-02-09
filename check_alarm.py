"""
直接验证 alarm 记录
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

def check_alarm():
    conn_str = f"postgresql+pg8000://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    engine = create_engine(conn_str)
    
    with engine.connect() as conn:
        print('=== biz.result (source_id=167773) ===')
        results = conn.execute(text('SELECT id, source_id, result_status FROM biz.result WHERE source_id=167773 AND craft_type=:ct'), {'ct':'SPR'}).fetchall()
        for r in results:
            print(f'  id={r[0]}, source_id={r[1]}, result_status={r[2]}')
        
        print('\n=== biz.alarm (result_id=9) ===')
        alarms = conn.execute(text('SELECT id, alarm_code, alarm_level, alarm_msg FROM biz.alarm WHERE result_id=9')).fetchall()
        if alarms:
            for r in alarms:
                print(f'  alarm_id={r[0]}, code={r[1]}, level={r[2]}, msg={r[3]}')
        else:
            print('  没有找到 alarm 记录')
        
        print('\n=== 所有 alarm 记录 ===')
        all_alarms = conn.execute(text('SELECT id, result_id, alarm_code, alarm_level, alarm_msg FROM biz.alarm')).fetchall()
        if all_alarms:
            for r in all_alarms:
                print(f'  id={r[0]}, result_id={r[1]}, code={r[2]}, level={r[3]}, msg={r[4][:30]}...')
        else:
            print('  没有任何 alarm 记录')

if __name__ == "__main__":
    check_alarm()
