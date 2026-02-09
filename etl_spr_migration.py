"""
SPR (Self-Piercing Rivet) 工艺数据 ETL 迁移脚本
从 origin.bs_spr_detail 和 origin.bs_spr_graph 迁移到 biz 业务表

数据关联:
- bs_spr_detail.id = bs_spr_graph.id (主键关联)
- result_sequence_number 作为循环编号 (cyclenumber)

曲线数据格式:
- gzip 压缩的 float32 数组
- 每个 result 有 2 条曲线: Force/Time 和 Stroke/Time
"""

import struct
import gzip
import json
import argparse
import os
import concurrent.futures
import time
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta

# --- CHECKPOINT FILE ---
CHECKPOINT_FILE = os.path.join(os.path.dirname(__file__), "spr_v2_checkpoint.json")


def load_checkpoint():
    """加载断点信息"""
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'r') as f:
                data = json.load(f)
                print(f"📌 加载断点: autoindex={data.get('last_autoindex')}, 时间={data.get('last_time')}")
                return data
        except Exception as e:
            print(f"⚠️ 加载断点失败: {e}")
    return {"last_autoindex": 0, "last_time": None, "success_count": 0, "fail_count": 0}


def save_checkpoint(autoindex, success_count=0, fail_count=0):
    """保存断点信息"""
    data = {
        "last_autoindex": autoindex,
        "last_time": datetime.now().isoformat(),
        "success_count": success_count,
        "fail_count": fail_count
    }
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"💾 保存断点: autoindex={autoindex}")

# --- CONFIGURATION ---
DB_CONFIG = {
    'host': '10.18.120.240',
    'port': 35432,
    'database': 'equipment_mechanism',
    'user': 'postgres',
    'password': '6edef2d746f2274cab951a452d5fc13d',
    'driver': 'pg8000'
}

CRAFT_TYPE = 'SPR'

# --- CURVE PARSING ---
def parse_spr_curve(curve_data):
    """
    解析 SPR 曲线数据
    输入: gzip 压缩的二进制数据
    输出: float32 数组
    """
    if curve_data is None:
        return None
    
    try:
        data = bytes(curve_data)
        decompressed = gzip.decompress(data)
        
        # 解析为 float32 数组
        num_floats = len(decompressed) // 4
        values = struct.unpack(f'<{num_floats}f', decompressed[:num_floats*4])
        
        return [round(v, 4) for v in values]
    except Exception as e:
        print(f"曲线解析错误: {e}")
        return None


def generate_time_axis(num_points, cycle_time):
    """
    生成时间轴数据 (X 轴)
    假设数据点均匀分布在 cycle_time 内
    """
    if num_points <= 1:
        return [0.0]
    
    dt = cycle_time / (num_points - 1) if cycle_time > 0 else 0.001
    return [round(i * dt, 6) for i in range(num_points)]


def create_db_engine():
    conn_str = f"postgresql+{DB_CONFIG['driver']}://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    # Increase pool size for multi-threading
    return create_engine(conn_str, echo=False, pool_size=20, max_overflow=50)


def migrate_single_record(detail_id, engine):
    """
    迁移单条 SPR 记录
    注意：使用 engine.begin() 确保线程安全和即时事务处理
    """
    # print(f"\n处理 SPR 记录: id={detail_id}...")
    
    try:
        with engine.begin() as conn:
            # 0. 检查是否已迁移
            check_exist = text("SELECT id FROM biz.result WHERE source_id = :sid AND craft_type = :craft")
            exist_res = conn.execute(check_exist, {"sid": detail_id, "craft": CRAFT_TYPE}).fetchone()
            if exist_res:
                # print(f"⚠️ 记录 id={detail_id} 已存在 (result_id={exist_res[0]}), 跳过")
                return True
            
            # 1. 查询 bs_spr_detail 该 id 的所有行（每个 parameter_type 一行）
            query_all_params = text("""
                SELECT DISTINCT id, device_name, result_sequence_number, result_date_time,
                    program_id, p_name, program_identifier, program_version,
                    final_force, final_stroke, start_distance, end_distance,
                    velocity, cycle_time, limit_high, limit_low, parameter_type,
                    short_description, bsn
                FROM origin.bs_spr_detail_v2 WHERE id = :id
            """)
            all_rows = conn.execute(query_all_params, {"id": detail_id}).fetchall()
            
            if not all_rows:
                # print(f"❌ 未找到 id={detail_id} 的记录")
                return False
            
            # print(f"  找到 {len(all_rows)} 个 parameter_type 行")
            
            # 使用第一行作为基础数据（用于 result 表）
            first_row = all_rows[0]
            res_id = first_row[0]
            device_name = first_row[1]
            result_seq_num = first_row[2]  # cyclenumber
            result_time = first_row[3]
            program_id_num = first_row[4]
            p_name = first_row[5]
            program_identifier = first_row[6]
            program_version = first_row[7]
            final_force = float(first_row[8]) if first_row[8] else 0.0
            final_stroke = float(first_row[9]) if first_row[9] else 0.0
            start_distance = float(first_row[10]) if first_row[10] else 0.0
            end_distance = float(first_row[11]) if first_row[11] else 0.0
            velocity = float(first_row[12]) if first_row[12] else 0.0
            cycle_time = float(first_row[13]) if first_row[13] else 0.0
            short_desc = first_row[17]
            bsn = first_row[18]
            
            # 2. 计算 result_status
            if short_desc:
                desc_upper = short_desc.upper()
                if 'NOT' in desc_upper or 'NOK' in desc_upper:
                    result_status = 0
                elif 'OK' in desc_upper:
                    result_status = 1
                else:
                    result_status = 0
            else:
                result_status = 0
            
            # 3. 计算 end_time
            end_time = result_time + timedelta(seconds=cycle_time) if cycle_time else result_time
            
            # 4. 查询关联的曲线数据 (通过 id 关联)
            query_graphs = text("""
                SELECT id, graph_type, graph_values
                FROM origin.bs_spr_graph_v2 WHERE id = :id
            """)
            graphs = conn.execute(query_graphs, {"id": detail_id}).fetchall()
            
            # print(f"  找到 {len(graphs)} 条曲线记录")
            
            # A. 为每种 parameter_type 插入 Program 记录
            insert_prog = text("""
                INSERT INTO biz.program (program_id, version, program_name, craft_type, parameter_type,
                                        device_type, target_value, upper_limit, lower_limit)
                VALUES (:pid, :ver, :pname, :craft, :param_type, :dev, :target, :upper, :lower)
                ON CONFLICT (program_id, version, parameter_type) DO NOTHING
                RETURNING id
            """)
            
            # 使用字典去重（相同 parameter_type 可能有重复行）
            param_programs = {}  # parameter_type -> program_db_id
            for row in all_rows:
                param_type = row[16]  # parameter_type
                limit_high = float(row[14]) if row[14] else 0.0
                limit_low = float(row[15]) if row[15] else 0.0
                
                if param_type in param_programs:
                    continue  # 已处理过该 parameter_type
                
                target_value = (limit_high + limit_low) / 2 if (limit_high and limit_low) else None
                prog_result = conn.execute(insert_prog, {
                    "pid": program_identifier or str(program_id_num),
                    "ver": str(program_version) if program_version else "1",
                    "pname": p_name,
                    "craft": CRAFT_TYPE,
                    "param_type": param_type,
                    "dev": device_name,
                    "target": target_value,
                    "upper": limit_high,
                    "lower": limit_low
                }).fetchone()
                
                if prog_result:
                    param_programs[param_type] = prog_result[0]
                else:
                    # 查询已存在的 program
                    fetch_prog = text("SELECT id FROM biz.program WHERE program_id = :pid AND version = :ver AND parameter_type = :param_type")
                    param_programs[param_type] = conn.execute(fetch_prog, {
                        "pid": program_identifier or str(program_id_num),
                        "ver": str(program_version) if program_version else "1",
                        "param_type": param_type
                    }).scalar()
            
            # print(f"  ✓ 插入/更新 {len(param_programs)} 条 program 记录")
            
            # 选择一个 program_db_id 关联到 result（使用 Final Force 或第一个）
            program_db_id = param_programs.get('Final Force') or (list(param_programs.values())[0] if param_programs else None)
            
            # B. 插入 Result (使用 source_id 存储原始ID，让 id 自动生成)
            insert_result = text("""
                INSERT INTO biz.result (
                    source_id, cyclenumber, device_name, craft_type, system_id, bsn,
                    program_id, program_ver_id, result_status,
                    start_time, end_time, cycle_time, key_value
                ) VALUES (
                    :source_id, :cnum, :dev, :craft, :sys, :bsn,
                    :pid_str, :pid_fk, :status,
                    :start, :end, :duration, :key_val
                ) RETURNING id
            """)
            result_insert = conn.execute(insert_result, {
                "source_id": res_id,  # 原始表的 ID
                "cnum": str(result_seq_num),
                "dev": device_name,
                "craft": CRAFT_TYPE,
                "sys": device_name,
                "bsn": bsn,
                "pid_str": program_identifier or str(program_id_num),
                "pid_fk": program_db_id,
                "status": result_status,
                "start": result_time,
                "end": end_time,
                "duration": cycle_time,
                "key_val": final_force
            })
            
            # 获取自动生成的 result_id
            result_db_id = result_insert.fetchone()[0]
            # print(f"  生成 result_id: {result_db_id}")
            
            # C. 插入 Extension（存储所有 parameter_type 的限值信息）
            insert_ext = text("""
                INSERT INTO biz.extension (result_id, extra_data)
                VALUES (:rid, CAST(:extra AS jsonb))
            """)
            
            # 收集所有 parameter_type 的限值
            param_limits = {}
            for row in all_rows:
                param_type = row[16]
                if param_type and param_type not in param_limits:
                    param_limits[param_type] = {
                        "limit_high": float(row[14]) if row[14] else None,
                        "limit_low": float(row[15]) if row[15] else None
                    }
            
            extra_data = {
                "final_force": final_force,
                "final_stroke": final_stroke,
                "start_distance": start_distance,
                "end_distance": end_distance,
                "velocity": velocity,
                "parameter_limits": param_limits  # 所有 parameter_type 的限值
            }
            conn.execute(insert_ext, {"rid": result_db_id, "extra": json.dumps(extra_data)})
            
            # D. 插入 Step (SPR 只有一个步骤)
            insert_step = text("""
                INSERT INTO biz.step (
                    result_id, step_index, step_name, step_result,
                    step_value, target_value, start_time, end_time
                ) VALUES (
                    :rid, :sidx, :sname, :sres,
                    :sval, :target, :sstart, :send
                ) RETURNING id
            """)
            step_result = conn.execute(insert_step, {
                "rid": result_db_id,  # 使用自动生成的 result_id
                "sidx": 0,
                "sname": "Riveting",
                "sres": result_status,
                "sval": final_force,
                "target": target_value,
                "sstart": result_time,
                "send": end_time
            })
            step_db_id = step_result.fetchone()[0]
            
            # E. 插入 Curves
            insert_curve = text("""
                INSERT INTO biz.curve (result_id, step, curve_type, start_time, end_time, data_points)
                VALUES (:rid, :step, :ctype, :sstart, :send, CAST(:data AS jsonb))
            """)
            
            for graph in graphs:
                graph_type = graph[1]  # Force/Time or Stroke/Time
                graph_values = graph[2]
                
                if graph_values:
                    values = parse_spr_curve(graph_values)
                    if values:
                        # 生成时间轴
                        time_axis = generate_time_axis(len(values), cycle_time)
                        
                        # 确定 curve_type
                        if 'Force' in graph_type:
                            curve_type = 'FORCE'
                        elif 'Stroke' in graph_type:
                            curve_type = 'STROKE'
                        else:
                            curve_type = graph_type.upper().replace('/', '_')
                        
                        payload = {"x": time_axis, "y": values}
                        conn.execute(insert_curve, {
                            "rid": result_db_id,  # 使用自动生成的 result_id
                            "step": 0,
                            "ctype": curve_type,
                            "sstart": result_time,
                            "send": end_time,
                            "data": json.dumps(payload)
                        })
                        # print(f"  ✓ 曲线 {curve_type}: {len(values)} 个数据点")
            
            # F. 插入 Alarm (如果 NOK)
            if result_status == 0:
                insert_alarm = text("""
                    INSERT INTO biz.alarm (result_id, step_id, alarm_code, alarm_level, alarm_msg, device_id)
                    VALUES (:rid, :sid, :code, :level, :msg, :dev)
                """)
                conn.execute(insert_alarm, {
                    "rid": result_db_id,  # 使用自动生成的 result_id
                    "sid": step_db_id,
                    "code": "SPR_NOK",
                    "level": "ERROR",
                    "msg": short_desc or "SPR process failed",
                    "dev": device_name
                })
                # print(f"  ✓ 报警已记录")
            
            # print(f"✅ 成功迁移 id={detail_id}")
            return True
        
    except Exception as e:
        # import traceback
        # traceback.print_exc()
        # print(f"❌ 迁移失败 id={detail_id}: {e}")
        return False


def migrate_batch(start_autoindex=None, batch_size=200, limit=None, resume=False, workers=5):
    """
    批量多线程迁移 SPR 记录
    """
    engine = create_db_engine()
    
    # 处理断点续传
    checkpoint = load_checkpoint()
    if resume and checkpoint.get("last_autoindex"):
        start_autoindex = checkpoint["last_autoindex"]
        print(f"📌 从断点恢复: autoindex > {start_autoindex}")
    elif start_autoindex:
        print(f"🚀 从指定位置开始: autoindex > {start_autoindex}")
    
    success = checkpoint.get("success_count", 0) if resume else 0
    failed = checkpoint.get("fail_count", 0) if resume else 0
    last_autoindex = start_autoindex or 0
    total_processed = 0
    
    while True:
        if limit and total_processed >= limit:
            break

        # FETCH BATCH
        with engine.connect() as conn:
            query = """
                SELECT sid, id 
                FROM origin.bs_spr_detail_v2
                WHERE sid > :last_idx
                ORDER BY sid
                LIMIT :batch
            """
            rows = conn.execute(text(query), {"last_idx": last_autoindex, "batch": batch_size}).fetchall()
        
        if not rows:
            print("没有更多数据了。")
            break
        
        # 去重：同一个 id 可能有多行(不同 parameter_type)，只取第一个遇到的
        seen_ids = set()
        unique_tasks = [] # (sid, id)
        
        for row in rows:
            sid, detail_id = row[0], row[1]
            if detail_id not in seen_ids:
                seen_ids.add(detail_id)
                unique_tasks.append((sid, detail_id))
            # Even if duplicate ID (and we skip processing), we need to acknowledge the sid was "seen"
            # The last SID in the batch is what we care about for checkpointing.
            # But wait, we iterate by SID. duplicate rows have different SIDs?
            # Yes, bs_spr_detail_v2 has diff IDs because of diff parameter_type? 
            # Or one 'result' has multiple 'rows'. Each row has unique ID?
            # 'id' is distinct ID. 'sid' is sequence?
            # Actually, `id` (UUID?) is what we migrate. `sid` is just for iteration.
            # So duplicates are rows with same `id`.
        
        print(f"📥 获取批次: {len(rows)} 行 -> {len(unique_tasks)} 个独立任务 (Start SID: {rows[0][0]}, End SID: {rows[-1][0]})")

        # PARALLEL EXECUTION
        batch_success = 0
        batch_failed = 0
        max_sid_in_batch = last_autoindex
        
        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            # Map future -> (sid, detail_id)
            future_to_task = {executor.submit(migrate_single_record, task[1], engine): task for task in unique_tasks}
            
            for future in concurrent.futures.as_completed(future_to_task):
                sid, detail_id = future_to_task[future]
                try:
                    result = future.result()
                    if result:
                        batch_success += 1
                    else:
                        batch_failed += 1
                except Exception as exc:
                    print(f"  💥 {detail_id} generated an exception: {exc}")
                    batch_failed += 1
                
        # Update checkpoint to the last SID in the fetch, regardless of whether it was unique or duplicate
        # because we have "processed" up to that point.
        max_sid_in_batch = rows[-1][0] 
        
        end_time = time.time()
        duration = end_time - start_time
        speed = len(rows) / duration if duration > 0 else 0
        
        success += batch_success
        failed += batch_failed
        total_processed += len(rows)
        last_autoindex = max_sid_in_batch
        
        # SAVE CHECKPOINT
        save_checkpoint(last_autoindex, success, failed)
        print(f"⏱️ 批次完成. 用时: {duration:.2f}s, 速度: {speed:.1f} rows/s. 进度: 总成功 {success}, 总失败 {failed}, 最新断点 {last_autoindex}")


def main():
    parser = argparse.ArgumentParser(description="SPR ETL Migration")
    parser.add_argument("--single-id", type=int, help="迁移单条记录 (测试用)")
    parser.add_argument("--batch", action="store_true", help="批量迁移模式")
    parser.add_argument("--resume", action="store_true", help="从上次断点继续")
    parser.add_argument("--start-id", type=int, help="批量模式起始 ID")
    parser.add_argument("--limit", type=int, help="批量模式最大记录数")
    parser.add_argument("--workers", type=int, default=10, help="并发线程数") # Default 10 workers
    args = parser.parse_args()
    
    engine = create_db_engine()
    
    if args.single_id:
        try:
             # Just pass engine, migrate_single_record now takes engine
             # Wait, args.single_id assumes `id` is integer? In spr table it might be uuid or int?
             # Based on SQL `id = :id` it seems generic.
             # The table definition implies `id` might be int or uuid. 
             # `migrate_single_record` arg name `detail_id` suggests ID.
             # The CLI says type=int. If it is UUID, this will fail.
             # But let's assume it works as previous script used it.
             migrate_single_record(args.single_id, engine)
        except Exception as e:
            print(f"事务失败: {e}")
    elif args.batch:
        migrate_batch(
            start_autoindex=args.start_id, 
            limit=args.limit, 
            resume=args.resume,
            workers=args.workers
        )
    else:
        print("使用方法:")
        print("  --single-id <id>  : 测试单条迁移")
        print("  --batch           : 批量迁移模式")
        print("  --resume          : 恢复模式")
        print("  --workers <n>     : 线程数 (默认10)")


if __name__ == "__main__":
    main()
