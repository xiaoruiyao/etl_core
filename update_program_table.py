"""
更新 program 表添加 parameter_type 列
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

def update_program_table():
    conn_str = f"postgresql+pg8000://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    engine = create_engine(conn_str)
    
    with engine.begin() as conn:
        print('更新 biz.program 表结构...')
        
        # 1. 添加 parameter_type 列 (如果不存在)
        try:
            conn.execute(text('''
                ALTER TABLE biz.program 
                ADD COLUMN IF NOT EXISTS parameter_type varchar(64)
            '''))
            print('  ✓ 添加 parameter_type 列')
        except Exception as e:
            print(f'  列可能已存在: {e}')
        
        # 2. 删除旧的唯一约束
        try:
            conn.execute(text('''
                ALTER TABLE biz.program 
                DROP CONSTRAINT IF EXISTS program_program_id_version_key
            '''))
            print('  ✓ 删除旧唯一约束 (program_id, version)')
        except Exception as e:
            print(f'  跳过: {e}')
        
        # 3. 添加新的唯一约束 (如果不存在)
        try:
            conn.execute(text('''
                ALTER TABLE biz.program 
                DROP CONSTRAINT IF EXISTS program_program_id_version_parameter_type_key
            '''))
            conn.execute(text('''
                ALTER TABLE biz.program 
                ADD CONSTRAINT program_program_id_version_parameter_type_key 
                UNIQUE (program_id, version, parameter_type)
            '''))
            print('  ✓ 添加新唯一约束 (program_id, version, parameter_type)')
        except Exception as e:
            print(f'  约束错误: {e}')
        
        print('\n完成!')

if __name__ == "__main__":
    update_program_table()
