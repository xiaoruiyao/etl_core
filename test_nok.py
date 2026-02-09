"""
测试 id=167773 的 NOK 迁移，验证 alarm 记录生成
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

def check_source_data(detail_id):
    """检查源数据状态"""
    conn_str = f"postgresql+pg8000://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    engine = create_engine(conn_str)
    
    with engine.connect() as conn:
        print(f'=== 检查源数据 id={detail_id} ===')
        result = conn.execute(text('''
            SELECT DISTINCT id, short_description, final_force, limit_high, limit_low, parameter_type
            FROM origin.bs_spr_detail 
            WHERE id = :id
        '''), {"id": detail_id})
        
        rows = list(result)
        if not rows:
            print(f'  未找到 id={detail_id} 的记录')
            return
        
        print(f'  共 {len(rows)} 行')
        for row in rows[:3]:  # 只显示前3行
            print(f'  short_description: {row[1]}')
            print(f'  final_force: {row[2]}, limit_high: {row[3]}, limit_low: {row[4]}')
            print(f'  parameter_type: {row[5]}')
            print()

def test_migration_and_check_alarm(detail_id):
    """执行迁移并检查alarm表"""
    from etl_spr_migration import create_db_engine, migrate_single_record
    
    engine = create_db_engine()
    try:
        with engine.begin() as conn:
            migrate_single_record(conn, detail_id)
    except Exception as e:
        print(f"迁移失败: {e}")
        return
    
    # 验证 alarm 记录
    with engine.connect() as conn:
        print(f'\n=== 验证 alarm 记录 ===')
        
        # 获取刚写入的 result_id
        result_row = conn.execute(text('''
            SELECT id, source_id, result_status FROM biz.result 
            WHERE source_id = :sid AND craft_type = 'SPR'
        '''), {"sid": detail_id}).fetchone()
        
        if result_row:
            result_id = result_row[0]
            result_status = result_row[2]
            print(f'  result_id: {result_id}, source_id: {result_row[1]}, result_status: {result_status}')
            
            # 查看 alarm
            alarms = conn.execute(text('''
                SELECT id, result_id, step_id, alarm_code, alarm_level, alarm_msg
                FROM biz.alarm WHERE result_id = :rid
            '''), {"rid": result_id}).fetchall()
            
            if alarms:
                print(f'  ✓ 找到 {len(alarms)} 条 alarm 记录:')
                for a in alarms:
                    print(f'    alarm_id={a[0]}, code={a[3]}, level={a[4]}, msg={a[5]}')
            else:
                print(f'  ✗ 没有找到 alarm 记录 (result_status={result_status})')
        else:
            print('  未找到 result 记录')

if __name__ == "__main__":
    detail_id = 167773
    check_source_data(detail_id)
    test_migration_and_check_alarm(detail_id)
