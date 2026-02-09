"""
测试 SPR 迁移脚本
"""
from etl_spr_migration import create_db_engine, migrate_single_record

if __name__ == "__main__":
    engine = create_db_engine()
    try:
        with engine.begin() as conn:
            migrate_single_record(conn, 583435)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n错误: {e}")
