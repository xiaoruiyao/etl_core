
import struct
import base64
import json
import argparse
import os
import concurrent.futures
import time
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta

# --- CHECKPOINT FILE ---
CHECKPOINT_FILE = os.path.join(os.path.dirname(__file__), "fds_checkpoint.json")


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

# --- MIGRATION CONFIGURATION ---
DB_CONFIG = {
    'host': '10.18.120.240',
    'port': 35432,
    'database': 'equipment_mechanism',  
    'user': 'postgres',
    'password': '6edef2d746f2274cab951a452d5fc13d',
    'driver': 'pg8000'
}

# --- FDS 错误码映射表 ---
FDS_ERROR_CODES = {
    0: "结果为空",
    10: "未达到最小扭矩",
    11: "超过了最大扭矩",
    110: "最后阶段造成的不合格",
    12: "未达到阈值扭矩",
    13: "松开扭矩出错",
    30: "未达到最小的经滤波扭矩",
    31: "超过了最大的经滤波扭矩",
    40: "未达到最大的扭矩梯度",
    41: "超过了最大的扭矩梯度",
    50: "未达到最小角度",
    51: "超过了最大的角度",
    60: "未达到最小时间",
    61: "超过了最大时间",
    70: "未达到最小深度",
    71: "超过了最大深度",
    75: "未达到最小深度梯度",
    76: "超过了最大的深度梯度",
    200: "程序意外终止",
    202: "出现了故障",
    203: "超过了总拧紧时间",
    204: "启动终止",
}


def get_error_message(code):
    """根据错误码获取中文描述"""
    return FDS_ERROR_CODES.get(code, f"未知错误码: {code}")

# --- CURVE PARSING LOGIC (Reused from existing script) ---
def parse_fds_curve(curve_data, start_offset=7816):
    """
    Parses FDS curve binary data.
    """
    if curve_data is None:
        return None

    if isinstance(curve_data, bytes):
        data = curve_data
    elif isinstance(curve_data, str):
        try:
            data = base64.b64decode(curve_data)
        except Exception as e:
            print(f"Base64 Decode Error: {e}")
            return None
    else:
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
            # Variant B structure: <hhffffffffi
            values = struct.unpack('<hhffffffffi', chunk)
            
            record = {
                'rpm_set': values[0],               # 转速设定值
                'rpm_actual': values[1],            # 实际转速
                'torque': round(values[2], 4),      # 扭矩
                'torque_filtered': round(values[3], 4), # 过滤扭矩
                'torque_gradient': round(values[4], 4), # 扭矩单位角度变化量
                'depth': round(values[5], 4),       # 深度
                'depth_gradient': round(values[6], 4),  # 深度单位时间变化量
                'angle': round(values[7], 4),       # 角度
                'pressure_set': round(values[8], 4),# 压力设定值
                'pressure_actual': round(values[9], 4), # 实际压力
                'step': values[10]                  # 步骤
            }
            curve_records.append(record)
        except Exception:
            pass
            
    return curve_records

def create_db_engine():
    conn_str = f"postgresql+{DB_CONFIG['driver']}://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    # Increase pool size for multi-threading
    return create_engine(conn_str, echo=False, pool_size=20, max_overflow=50)

def migrate_single_record(autoindex, engine):
    """
    Migrates a single record identified by autoindex from origin to biz.
    Note: Connects to DB inside the function to be thread-safe.
    """
    # print(f"Processing Autoindex: {autoindex}...") # Reduce logging for speed
    
    try:
        # Use engine.begin() to manage connection and transaction automatically.
        # This commits if successful, rolls back on exception.
        with engine.begin() as conn:
            # 1. Fetch Main Record from View
            # Note: bs_fds_v_fds_curves has the curve blob and basic info
            query_main = text(f"""
                SELECT 
                    autoindex, actualprogramid, systemid, startselection, ok_nok_code, 
                    lastexecutedstep, starttime, cyclenumber, duration, bsn, progselection, curve 
                FROM origin.bs_fds_v_fds_curves 
                WHERE autoindex = :idx
            """)
            record = conn.execute(query_main, {"idx": autoindex}).fetchone()
            
            if not record:
                # print(f"❌ Record {autoindex} not found in origin.bs_fds_v_fds_curves")
                return False

            # Unpack record
            res_id = record[0] 
            prog_id_num = record[1]
            sys_id = record[2].strip() if record[2] else None
            start_sel = record[3].strip() if record[3] else None
            ok_nok = record[4]
            last_step = record[5]
            start_time = record[6]
            cycle_num = str(record[7])
            duration = float(record[8]) if record[8] else 0.0
            bsn = record[9].strip() if record[9] else None
            prog_sel = record[10].strip() if record[10] else None
            curve_blob = record[11]

            # Calculate End Time
            end_time = start_time + timedelta(seconds=duration)

            # 2. Fetch Additional Data: Program Info
            query_prog = text(f"SELECT name, lastchangedatetime, startstring FROM origin.bs_fds_progtable WHERE autoprogindex = :pid")
            prog_rec = conn.execute(query_prog, {"pid": prog_id_num}).fetchone()
            
            program_name = None
            prog_version = None
            program_code = None
            
            if prog_rec:
                program_name = prog_rec[0].strip() if prog_rec[0] else None
                prog_version = prog_rec[1].strftime('%Y%m%d%H%M%S') if prog_rec[1] else 'unknown'
                program_code = prog_rec[2].strip() if prog_rec[2] else str(prog_id_num)
            else:
                program_code = str(prog_id_num) 
                prog_version = 'unknown'

            # 3. Fetch Additional Data: Single Results (KPIs)
            query_kpi = text(f"SELECT type, step, value, resultindex FROM origin.bs_fds_singleresult WHERE resultlistid = :rid ORDER BY step, resultindex")
            kpi_recs = conn.execute(query_kpi, {"rid": res_id}).fetchall()
            
            kpis_by_step = {} # step_num -> list of {type, value}
            all_kpis_list = []
            
            for kpi in kpi_recs:
                s_idx = kpi[1]
                k_data = {'type': kpi[0], 'value': float(kpi[2]), 'result_index': kpi[3]}
                if s_idx not in kpis_by_step:
                    kpis_by_step[s_idx] = []
                kpis_by_step[s_idx].append(k_data)
                all_kpis_list.append(k_data)

            # --- INSERT INTO BIZ SCHEMA ---
            
            # A. Insert Program (Ignore if exists)
            insert_prog = text("""
                INSERT INTO biz.program (program_id, version, program_name, device_type, craft_type, parameter_type)
                VALUES (:pid, :ver, :pname, :dev, 'FDS_DEFAULT', 'DEFAULT')
                ON CONFLICT (program_id, version, parameter_type) DO NOTHING
                RETURNING id
            """)
            result_prog_insert = conn.execute(insert_prog, {
                "pid": program_code, "ver": prog_version, "pname": program_name, "dev": sys_id
            }).fetchone()
            
            program_db_id = None
            if result_prog_insert:
                program_db_id = result_prog_insert[0]
            else:
                fetch_prog_id = text("SELECT id FROM biz.program WHERE program_id = :pid AND version = :ver AND parameter_type = 'DEFAULT'")
                program_db_id = conn.execute(fetch_prog_id, {"pid": program_code, "ver": prog_version}).scalar()

            # B. Insert Result
            result_clean_status = 1 if ok_nok == 1 else 0
            
            insert_result = text("""
                INSERT INTO biz.result (
                    source_id, cyclenumber, device_name, system_id, bsn, vin, 
                    program_id, program_ver_id, result_status, 
                    start_time, end_time, cycle_time, craft_type
                ) VALUES (
                    :source_id, :cnum, :dev, :sys, :bsn, NULL,
                    :pid_str, :pid_fk, :status,
                    :start, :end, :duration, 'FDS_DEFAULT'
                )
                RETURNING id
            """)
            result_insert = conn.execute(insert_result, {
                "source_id": res_id,  # 原始表的 autoindex
                "cnum": cycle_num, "dev": sys_id, "sys": sys_id, 
                "bsn": bsn, "pid_str": program_code, "pid_fk": program_db_id,
                "status": result_clean_status, "start": start_time, "end": end_time,
                "duration": duration
            })
            
            result_db_id = result_insert.fetchone()[0]

            # C. Insert Extension (KPIs)
            insert_ext = text("""
                INSERT INTO biz.extension (result_id, extra_data, operator_id, fixture_id)
                VALUES (:rid, :extra, NULL, NULL)
            """)
            extra_json = json.dumps({
                "single_results": all_kpis_list,
                "origin_info": {
                    "progselection": prog_sel,
                    "startselection": start_sel,
                    "lastexecutedstep": last_step
                }
            })
            conn.execute(insert_ext, {"rid": result_db_id, "extra": extra_json})

            # D. Parse and Insert Curve + Steps
            parsed_points = parse_fds_curve(curve_blob)
            points_by_step = {}
            if parsed_points:
                for p in parsed_points:
                    s = p['step']
                    if s not in points_by_step: points_by_step[s] = []
                    points_by_step[s].append(p)
            
            # Identify all unique steps from various sources
            all_steps = set()
            if points_by_step:
                all_steps.update(points_by_step.keys())
            if kpis_by_step:
                all_steps.update(kpis_by_step.keys())
            
            # Fallback: if no steps found but we have last executed step info
            if not all_steps and last_step and int(last_step) > 0:
                all_steps.update(range(1, int(last_step) + 1))
            
            sorted_steps = sorted(all_steps)
            
            total_pts = len(parsed_points) if parsed_points else 0
            time_per_pt = duration / total_pts if total_pts > 0 else 0
            
            current_pt_idx = 0
            
            for s_num in sorted_steps:
                pts = points_by_step.get(s_num, [])
                count = len(pts)
                
                # Calculate Step Times
                if count > 0:
                    s_start = start_time + timedelta(seconds=current_pt_idx * time_per_pt)
                    s_end = start_time + timedelta(seconds=(current_pt_idx + count) * time_per_pt)
                else:
                    # No curve data for this step - default to overall end time or 0 duration
                    # If we have absolutely no curve data, just assign the result start/end to the steps?
                    # Or zero duration at end? Let's use start_time if it's the first step, else previous step end... 
                    # For simplicity/safety: use start_time + duration (end_time) for all empty steps or just 0 duration
                    s_start = start_time
                    s_end = end_time 
                
                # D1. Insert Curve Data (Only if points exist)
                if pts:
                    times = []
                    torques = []
                    speeds = [] # rpm
                    angles = []
                    depths = []
                    pressures = []
                    
                    for idx_in_step, p in enumerate(pts):
                        t = (current_pt_idx + idx_in_step) * time_per_pt
                        times.append(round(t, 4))
                        torques.append(p['torque'])
                        speeds.append(p['rpm_actual'])
                        angles.append(p['angle'])
                        depths.append(p['depth'])
                        pressures.append(p['pressure_actual'])
                    
                    curves_to_insert = [
                        ('TORQUE', times, torques),
                        ('SPEED', times, speeds),
                        ('ANGLE', times, angles),
                        ('DEPTH', times, depths),
                        ('PRESSURE', times, pressures),
                        ('TORQUE_ANGLE', angles, torques)
                    ]

                    insert_curve = text("""
                        INSERT INTO biz.curve (result_id, step, start_time, end_time, curve_type, data_points)
                        VALUES (:rid, :step, :s_start, :s_end, :ctype, CAST(:data AS jsonb))
                    """)
                    
                    for c_type, x_data, y_data in curves_to_insert:
                        payload = {"x": x_data, "y": y_data}
                        conn.execute(insert_curve, {
                            "rid": result_db_id,
                            "step": s_num,
                            "s_start": s_start,
                            "s_end": s_end,
                            "ctype": c_type, 
                            "data": json.dumps(payload)
                        })

                # D2. Insert Step Record (Always if step exists in list)
                step_val = 0.0
                if s_num in kpis_by_step and kpis_by_step[s_num]:
                    step_val = kpis_by_step[s_num][0]['value']
                
                s_res = 1
                # If overall result is NOK and this is the last step, mark it as faulty
                if result_clean_status == 0 and int(s_num) == last_step:
                    s_res = 0
                
                insert_step = text("""
                    INSERT INTO biz.step (
                        result_id, step_index, step_name, step_result, 
                        step_value, start_time, end_time
                    ) VALUES (
                        :rid, :sidx, :sname, :sres, 
                        :sval, :sstart, :send
                    ) RETURNING id
                """)
                step_db_id = conn.execute(insert_step, {
                    "rid": result_db_id, "sidx": s_num, "sname": f"Step {s_num}",
                    "sres": s_res, "sval": step_val,
                    "sstart": s_start, "send": s_end
                }).fetchone()[0]

                # D3. Insert Alarm (if NOK)
                if s_res == 0:
                        insert_alarm = text("""
                        INSERT INTO biz.alarm (result_id, step_id, alarm_code, alarm_level, alarm_msg, device_id)
                        VALUES (:rid, :sid, :code, :level, :msg, :dev)
                        """)
                        error_msg = get_error_message(ok_nok)
                        conn.execute(insert_alarm, {
                            "rid": result_db_id,
                            "sid": step_db_id,
                            "code": str(ok_nok),
                            "level": "ERROR",
                            "msg": error_msg,
                            "dev": sys_id
                        })
                
                current_pt_idx += count

        # print(f"✅ Successfully migrated {autoindex}")
        return True

    except Exception as e:
        # import traceback
        # traceback.print_exc()
        print(f"❌ Error migrating {autoindex}: {e}")
        return False

def migrate_batch(start_autoindex=None, batch_size=200, limit=None, resume=False, workers=5): # Increased batch size and default workers
    """
    批量多线程迁移 FDS 记录
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

        # FETCH NEXT BATCH OF IDs
        with engine.connect() as conn:
            query = """
                SELECT autoindex 
                FROM origin.bs_fds_v_fds_curves
                WHERE autoindex > :last_idx
                ORDER BY autoindex
                LIMIT :batch
            """
            autoindexes = [row[0] for row in conn.execute(text(query), {"last_idx": last_autoindex, "batch": batch_size}).fetchall()]
        
        if not autoindexes:
            print("没有更多数据了。")
            break
            
        print(f"📥 获取批次: {len(autoindexes)} 条记录 (Start: {autoindexes[0]}, End: {autoindexes[-1]})")
        
        # PARALLEL EXECUTION
        batch_success = 0
        batch_failed = 0
        max_id_in_batch = last_autoindex
        
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            # Create a dictionary of future -> autoindex
            future_to_id = {executor.submit(migrate_single_record, idx, engine): idx for idx in autoindexes}
            
            for future in concurrent.futures.as_completed(future_to_id):
                idx = future_to_id[future]
                try:
                    result = future.result()
                    if result:
                        batch_success += 1
                        # print(f"  ✓ {idx}")
                    else:
                        batch_failed += 1
                        print(f"  × {idx}")
                except Exception as exc:
                    print(f"  💥 {idx} generated an exception: {exc}")
                    batch_failed += 1
                
                # Update max ID seen so far to safely advance checkpoint
                if idx > max_id_in_batch:
                    max_id_in_batch = idx

        end_time = time.time()
        duration = end_time - start_time
        speed = len(autoindexes) / duration if duration > 0 else 0
        
        success += batch_success
        failed += batch_failed
        total_processed += len(autoindexes)
        last_autoindex = max_id_in_batch # Move goalpost to the end of this batch
        
        # SAVE CHECKPOINT
        save_checkpoint(last_autoindex, success, failed)
        print(f"⏱️ 批次完成. 用时: {duration:.2f}s, 速度: {speed:.1f} rec/s. 进度: 总成功 {success}, 总失败 {failed}, 最新断点 {last_autoindex}")


def main():
    parser = argparse.ArgumentParser(description="FDS ETL Migration")
    parser.add_argument("--single-id", type=int, help="Run migration for a single autoindex")
    parser.add_argument("--batch", action="store_true", help="批量迁移模式")
    parser.add_argument("--start-autoindex", type=int, help="批量模式起始 autoindex (使用 > 条件)")
    parser.add_argument("--resume", action="store_true", help="从上次断点继续执行")
    parser.add_argument("--limit", type=int, help="批量模式最大记录数")
    parser.add_argument("--workers", type=int, default=10, help="并发线程数") # Default 10 workers
    args = parser.parse_args()

    engine = create_db_engine()
    
    if args.single_id:
        try:
             # For single test, just pass engine
            migrate_single_record(args.single_id, engine)
            print(f"Single ID {args.single_id} processed.")
        except Exception as e:
            print(f"Single ID failed: {e}")
    elif args.batch or args.resume:
        migrate_batch(
            start_autoindex=args.start_autoindex, 
            limit=args.limit, 
            resume=args.resume,
            workers=args.workers
        )
    else:
        print("使用方法:")
        print("  --single-id <id>        : 迁移单条记录")
        print("  --batch                 : 批量迁移模式")
        print("  --resume                : 恢复模式")
        print("  --workers <n>           : 线程数 (默认10)")
        
if __name__ == "__main__":
    main()
