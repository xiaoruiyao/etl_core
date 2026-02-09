
import struct
import base64
import json
import os
from datetime import datetime, timedelta
from sqlalchemy import text
from ..common.base import BaseEtlPipeline

# --- FDS Constants & Helpers ---
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
    60: "未达到最小时间",
    61: "超过了最大时间",
    50: "未达到最小角度",
    51: "超过了最大的角度",
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
    return FDS_ERROR_CODES.get(code, f"未知错误码: {code}")

def parse_fds_curve(curve_data, start_offset=7816):
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
                'rpm_set': values[0],               
                'rpm_actual': values[1],            
                'torque': round(values[2], 4),      
                'torque_filtered': round(values[3], 4), 
                'torque_gradient': round(values[4], 4), 
                'depth': round(values[5], 4),       
                'depth_gradient': round(values[6], 4),  
                'angle': round(values[7], 4),       
                'pressure_set': round(values[8], 4),
                'pressure_actual': round(values[9], 4), 
                'step': values[10]                  
            }
            curve_records.append(record)
        except Exception:
            pass
            
    return curve_records

# --- Pipeline Implementation ---
class FdsPipeline(BaseEtlPipeline):
    def __init__(self, checkpoint_file="fds_checkpoint.json", batch_size=200, workers=10, limit=None):
        super().__init__("FDS", checkpoint_file, batch_size, workers, limit)

    def get_next_batch(self, last_autoindex, batch_size):
        with self.engine.connect() as conn:
            query = text("""
                SELECT autoindex 
                FROM origin.bs_fds_v_fds_curves
                WHERE autoindex > :last_idx
                ORDER BY autoindex
                LIMIT :batch
            """)
            return [row[0] for row in conn.execute(query, {"last_idx": last_autoindex, "batch": batch_size}).fetchall()]

    def process_item(self, autoindex, engine):
        try:
            with engine.begin() as conn:
                # 1. Fetch Main Record
                query_main = text("""
                    SELECT 
                        autoindex, actualprogramid, systemid, startselection, ok_nok_code, 
                        lastexecutedstep, starttime, cyclenumber, duration, bsn, progselection, curve 
                    FROM origin.bs_fds_v_fds_curves 
                    WHERE autoindex = :idx
                """)
                record = conn.execute(query_main, {"idx": autoindex}).fetchone()
                
                if not record:
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

                end_time = start_time + timedelta(seconds=duration)

                # 2. Fetch Program Info
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

                # 3. Fetch Single Results (KPIs)
                query_kpi = text(f"SELECT type, step, value, resultindex FROM origin.bs_fds_singleresult WHERE resultlistid = :rid ORDER BY step, resultindex")
                kpi_recs = conn.execute(query_kpi, {"rid": res_id}).fetchall()
                
                kpis_by_step = {} 
                all_kpis_list = []
                
                for kpi in kpi_recs:
                    s_idx = kpi[1]
                    k_data = {'type': kpi[0], 'value': float(kpi[2]), 'result_index': kpi[3]}
                    if s_idx not in kpis_by_step:
                        kpis_by_step[s_idx] = []
                    kpis_by_step[s_idx].append(k_data)
                    all_kpis_list.append(k_data)

                # --- INSERT INTO BIZ ---
                
                # A. Program
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

                # B. Result
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
                    "source_id": res_id, 
                    "cnum": cycle_num, "dev": sys_id, "sys": sys_id, 
                    "bsn": bsn, "pid_str": program_code, "pid_fk": program_db_id,
                    "status": result_clean_status, "start": start_time, "end": end_time,
                    "duration": duration
                })
                
                result_db_id = result_insert.fetchone()[0]

                # C. Extension
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

                # D. Curve + Steps
                parsed_points = parse_fds_curve(curve_blob)
                points_by_step = {}
                if parsed_points:
                    for p in parsed_points:
                        s = p['step']
                        if s not in points_by_step: points_by_step[s] = []
                        points_by_step[s].append(p)
                
                # Identify all unique steps
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
                        s_start = start_time
                        s_end = end_time 
                    
                    # D1. Insert Curve Data
                    if pts:
                        times = []
                        torques = []
                        speeds = [] 
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
                        
                        # Store curve components
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

                    # D2. Insert Step Record
                    step_val = 0.0
                    if s_num in kpis_by_step and kpis_by_step[s_num]:
                        step_val = kpis_by_step[s_num][0]['value']
                    
                    s_res = 1
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

                    # D3. Insert Alarm
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

            return True

        except Exception as e:
            print(f"[{self.name}] ❌ Error processing {autoindex}: {e}")
            return False
