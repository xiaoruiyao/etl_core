"""
测试 FDS ETL 迁移
"""
from etl_fds_migration import create_db_engine, migrate_single_record

if __name__ == "__main__":
    test_id = 56872
    engine = create_db_engine()
    try:
        with engine.begin() as conn:
            result = migrate_single_record(conn, test_id)
            if result:
                print(f"\n✅ FDS 迁移成功 id={test_id}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n❌ FDS 迁移失败: {e}")
