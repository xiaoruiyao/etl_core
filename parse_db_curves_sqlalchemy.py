"""
FDS Curve Database Parser (使用 SQLAlchemy)
解析PostgreSQL数据库中的曲线数据并存储到curve_plain字段

Database: 10.18.120.240:35432
Database Name: miot_quality_data
Table: origin.fds_curves

依赖: 
  - sqlalchemy (已安装 ✓)
  - psycopg2-binary 或 pg8000 (需要安装其中之一)

安装驱动:
  pip install psycopg2-binary  # 推荐
  或
  pip install pg8000  # 纯Python，无需编译
"""

import struct
import base64
import json
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta


def parse_fds_curve(curve_data, start_offset=7816):
    """
    解析FDS曲线数据（支持bytes或Base64字符串）
    
    Args:
        curve_data: 二进制数据(bytes) 或 Base64字符串(str)
        start_offset: 数据起始偏移量 (默认7816)
        
    Returns:
        list: 解析后的记录列表
    """
    if curve_data is None:
        return None

    # 处理不同类型的输入
    if isinstance(curve_data, bytes):
        # 直接使用二进制数据（来自数据库bytea字段）
        data = curve_data
    elif isinstance(curve_data, str):
        # Base64字符串（来自CSV文件）
        try:
            data = base64.b64decode(curve_data)
        except Exception as e:
            print(f"Base64解码错误: {e}")
            return None
    else:
        print(f"不支持的数据类型: {type(curve_data)}")
        return None

    frame_size = 40
    if len(data) <= start_offset:
        return []

    num_rows = (len(data) - start_offset) // frame_size
    
    curve_records = []
    for i in range(num_rows):
        offset = start_offset + i * frame_size
        chunk = data[offset : offset + frame_size]
        
        try:
            # Variant B 结构: <hhffffffffi
            values = struct.unpack('<hhffffffffi', chunk)
            
            record = {
                '转速设定值': values[0],
                '实际转速': values[1],
                '扭矩': round(values[2], 4),
                '过滤扭矩': round(values[3], 4),
                '扭矩单位角度变化量': round(values[4], 4),
                '深度': round(values[5], 4),
                '深度单位时间变化量': round(values[6], 4),
                '角度': round(values[7], 4),
                '压力设定值': round(values[8], 4),
                '实际压力': round(values[9], 4),
                '步骤': values[10]
            }
            curve_records.append(record)
        except Exception:
            pass
            
    return curve_records


def create_db_engine(host, port, database, user, password, driver='psycopg2'):
    """
    创建SQLAlchemy数据库引擎
    
    Args:
        driver: 'psycopg2' 或 'pg8000'
    """
    # 构建连接字符串
    # postgresql+psycopg2://user:password@host:port/database
    # postgresql+pg8000://user:password@host:port/database
    
    connection_string = f"postgresql+{driver}://{user}:{password}@{host}:{port}/{database}"
    
    try:
        engine = create_engine(connection_string, echo=False)
        # 测试连接
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print(f"✓ 数据库连接成功 (驱动: {driver})")
        return engine
    except Exception as e:
        print(f"✗ 数据库连接失败: {e}")
        if driver == 'psycopg2':
            print("\n提示: 如果psycopg2未安装，请尝试:")
            print("  1. pip install psycopg2-binary")
            print("  2. 或使用 pg8000: 修改脚本中的 driver='pg8000'")
        raise


def process_curves(engine, batch_size=100, start_date='2024-12-01', min_autoindex=None):
    """
    处理曲线数据
    
    Args:
        engine: SQLAlchemy引擎
        batch_size: 批处理大小
        start_date: 起始日期
        min_autoindex: 最小autoindex值 (可选，用于筛选 autoindex > min_autoindex)
    """
    with engine.connect() as conn:
        # 构建WHERE条件
        where_conditions = ["starttime >= :start_date", "curve IS NOT NULL", "curve_plain IS NULL"]
        params = {"start_date": start_date}
        
        if min_autoindex is not None:
            where_conditions.append("autoindex > :min_autoindex")
            params["min_autoindex"] = min_autoindex
        
        where_clause = " AND ".join(where_conditions)
        
        # 统计待处理记录数
        count_query = text(f"""
            SELECT COUNT(*) as total 
            FROM origin.fds_curves 
            WHERE {where_clause}
        """)
        
        result = conn.execute(count_query, params)
        total_count = result.scalar()
        
        print(f"\n📊 待处理记录总数: {total_count}")
        if min_autoindex is not None:
            print(f"   筛选条件: autoindex > {min_autoindex}")
        
        if total_count == 0:
            print("没有需要处理的记录")
            return
        
        # 分批处理
        offset = 0
        processed = 0
        success = 0
        failed = 0
        
        while True:
            # 查询一批数据 - Always fetch from start since we are removing items from the result set (by updating curve_plain)
            select_query = text(f"""
                SELECT autoindex, curve, starttime, duration, actualprogramid, systemid, startselection, ok_nok_code, lastexecutedstep, cyclenumber, bsn, progselection, create_time, update_time
                FROM origin.fds_curves 
                WHERE {where_clause}
                ORDER BY autoindex
                LIMIT :batch_size
            """)
            
            query_params = params.copy()
            query_params["batch_size"] = batch_size
            
            result = conn.execute(select_query, query_params)
            records = result.fetchall()
            
            if not records:
                break
            
            print(f"\n🔄 处理批次: {processed + 1} 到 {processed + len(records)} / {total_count} (剩余: {total_count - processed})")
            
            # 处理每条记录
            for record in records:
                record_id = record[0]
                curve_data = record[1]
                starttime = record[2]
                duration = record[3]
                
                # Metadata fields
                metadata = {
                    'actualprogramid': record[4],
                    'systemid': record[5],
                    'startselection': record[6],
                    'ok_nok_code': record[7],
                    'lastexecutedstep': record[8],
                    'cyclenumber': record[9],
                    'bsn': record[10],
                    'progselection': record[11],
                    'create_time': record[12],
                    'update_time': record[13]
                }
                
                try:
                    # 解析曲线
                    parsed_data = parse_fds_curve(curve_data)
                    
                    if parsed_data is None:
                        print(f"  ⚠ ID {record_id}: Base64解码失败")
                        failed += 1
                        continue
                    
                    if len(parsed_data) == 0:
                        print(f"  ⚠ ID {record_id}: 未提取到数据点")
                        failed += 1
                        continue
                    
                    # 1. Update curve_plain in origin.fds_curves
                    json_data = json.dumps(parsed_data, ensure_ascii=False)
                    update_query = text("""
                        UPDATE origin.fds_curves 
                        SET curve_plain = CAST(:json_data AS jsonb)
                        WHERE autoindex = :record_id
                    """)
                    conn.execute(
                        update_query, 
                        {"json_data": json_data, "record_id": record_id}
                    )

                    # 2. Split by step and insert into origin.fds_curves_by_step
                    # Group points by step
                    steps_data = {}
                    for point in parsed_data:
                        step_num = point['步骤']
                        if step_num not in steps_data:
                            steps_data[step_num] = []
                        steps_data[step_num].append(point)
                    
                    # Calculate timing
                    total_points = len(parsed_data)
                    time_per_point = 0
                    if total_points > 0 and duration is not None:
                        # Duration is typically in seconds, double check unit if needed. Assuming seconds based on context.
                        time_per_point = float(duration) / total_points
                    
                    current_point_index = 0
                    
                    for step_num in sorted(steps_data.keys()):
                        points = steps_data[step_num]
                        step_points_count = len(points)
                        
                        # Calculate start and end time for this step
                        # Start time offset from curve start
                        start_offset_seconds = current_point_index * time_per_point
                        end_offset_seconds = (current_point_index + step_points_count) * time_per_point
                        
                        step_start_time = starttime + timedelta(seconds=start_offset_seconds)
                        step_end_time = starttime + timedelta(seconds=end_offset_seconds)
                        
                        # Prepare insert
                        step_json_data = json.dumps(points, ensure_ascii=False)
                        
                        insert_query = text("""
                            INSERT INTO origin.fds_curves_by_step (
                                origin_data_id, step, curve_plain, start_time, end_time,
                                actualprogramid, systemid, startselection, ok_nok_code, 
                                lastexecutedstep, cyclenumber, bsn, progselection, 
                                create_time, update_time
                            ) VALUES (
                                :origin_data_id, :step, CAST(:curve_plain AS jsonb), :start_time, :end_time,
                                :actualprogramid, :systemid, :startselection, :ok_nok_code,
                                :lastexecutedstep, :cyclenumber, :bsn, :progselection,
                                :create_time, :update_time
                            )
                        """)
                        
                        insert_params = {
                            "origin_data_id": record_id,
                            "step": step_num,
                            "curve_plain": step_json_data,
                            "start_time": step_start_time,
                            "end_time": step_end_time,
                            **metadata
                        }
                        
                        conn.execute(insert_query, insert_params)
                        current_point_index += step_points_count

                    success += 1
                    if success % 10 == 0:
                        print(f"  ✓ 已成功处理 {success} 条记录")
                    conn.commit()  # Commit after each record
                    
                except Exception as e:
                    print(f"  ✗ ID {record_id}: 错误 - {e}")
                    failed += 1
                    conn.rollback() # Rollback on error
                    continue
            
            # 提交批次 (redundant but keeps logic clean if loop finishes)
            # conn.commit() 
            # print(f"  💾 批次已提交到数据库")
            
            processed += len(records)
        
        # 最终统计
        print(f"\n{'='*60}")
        print(f"📈 处理完成!")
        print(f"{'='*60}")
        print(f"总处理数: {processed}")
        print(f"✓ 成功: {success}")
        print(f"✗ 失败: {failed}")
        print(f"成功率: {success/processed*100:.2f}%" if processed > 0 else "N/A")
        print(f"{'='*60}\n")


def main():
    """
    主函数
    """
    # 数据库配置
    DB_CONFIG = {
        'host': '10.18.120.240',
        'port': 35432,
        'database': 'miot_quality_data',
        'user': 'postgres',
        'password': '6edef2d746f2274cab951a452d5fc13d',
        'driver': 'pg8000'  # 使用 pg8000 驱动
    }
    
    # 处理配置
    BATCH_SIZE = 100
    START_DATE = '2024-12-01'  # 只处理12月及以后的数据
    MIN_AUTOINDEX = 4486968    # 只处理 autoindex > 2955030 的记录
    
    print("="*60)
    print("FDS曲线数据库解析器 (SQLAlchemy)")
    print("="*60)
    print(f"数据库: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    print(f"数据表: origin.fds_curves")
    print(f"起始日期: {START_DATE}")
    print(f"最小autoindex: {MIN_AUTOINDEX}")
    print(f"批处理大小: {BATCH_SIZE}")
    print(f"数据库驱动: {DB_CONFIG['driver']}")
    print("="*60)
    
    try:
        # 创建数据库引擎
        engine = create_db_engine(**DB_CONFIG)
        
        # 处理曲线数据
        process_curves(engine, batch_size=BATCH_SIZE, start_date=START_DATE, min_autoindex=MIN_AUTOINDEX)
        
        # 关闭引擎
        engine.dispose()
        print("✓ 数据库连接已关闭")
        
    except Exception as e:
        print(f"\n✗ 致命错误: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
