
import struct
import gzip
import json
import os
from datetime import datetime, timedelta
from sqlalchemy import text
from ..common.base import BaseEtlPipeline

CRAFT_TYPE = 'SPR'

# --- Helpers ---
def parse_spr_curve(curve_data):
    if curve_data is None:
        return None
    try:
        data = bytes(curve_data)
        decompressed = gzip.decompress(data)
        num_floats = len(decompressed) // 4
        values = struct.unpack(f'<{num_floats}f', decompressed[:num_floats*4])
        return [round(v, 4) for v in values]
    except Exception as e:
        print(f"曲线解析错误: {e}")
        return None

def generate_time_axis(num_points, cycle_time):
    if num_points <= 1:
        return [0.0]
    dt = cycle_time / (num_points - 1) if cycle_time > 0 else 0.001
    return [round(i * dt, 6) for i in range(num_points)]

# --- Pipeline Implementation ---
class SprPipeline(BaseEtlPipeline):
    def __init__(self, checkpoint_file="spr_v2_checkpoint.json", batch_size=200, workers=10, limit=None):
        super().__init__("SPR", checkpoint_file, batch_size, workers, limit)

    def get_next_batch(self, last_autoindex, batch_size):
        with self.engine.connect() as conn:
            query = text("""
                SELECT id as offset_id, id 
                FROM origin.bs_spr_detail_v2
                WHERE id > :last_idx
                ORDER BY id
                LIMIT :batch
            """)
            rows = conn.execute(query, {"last_idx": last_autoindex, "batch": batch_size}).fetchall()
        
        # Deduplication logic (handled by returning all rows, process_item handles idempotency)
        # We return the raw rows (tuples) as "items".
        # deduplication Logic: original script collected unique IDs but updated offset to max SID.
        # Here we return all rows. Base class processes them in parallel.
        # Idempotency check inside process_item is crucial.
        return rows

    def get_item_offset(self, item):
        # item is (sid, detail_id)
        return item[0]

    def process_item(self, item, engine):
        sid, detail_id = item
        
        try:
            with engine.begin() as conn:
                # 0. Check Existence
                check_exist = text("SELECT id FROM biz.result WHERE source_id = :sid AND craft_type = :craft")
                exist_res = conn.execute(check_exist, {"sid": detail_id, "craft": CRAFT_TYPE}).fetchone()
                if exist_res:
                    return True
                
                # 1. Query Details
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
                    return False
                
                first_row = all_rows[0]
                # Unpack first row
                res_id = first_row[0]
                device_name = first_row[1]
                result_seq_num = first_row[2]
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
                
                # 2. Result Status
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
                
                end_time = result_time + timedelta(seconds=cycle_time) if cycle_time else result_time
                
                # 3. Query Graphs
                query_graphs = text("""
                    SELECT id, graph_type, graph_values
                    FROM origin.bs_spr_graph_v2 WHERE id = :id
                """)
                graphs = conn.execute(query_graphs, {"id": detail_id}).fetchall()
                
                # A. Insert Programs
                insert_prog = text("""
                    INSERT INTO biz.program (program_id, version, program_name, craft_type, parameter_type,
                                            device_type, target_value, upper_limit, lower_limit)
                    VALUES (:pid, :ver, :pname, :craft, :param_type, :dev, :target, :upper, :lower)
                    ON CONFLICT (program_id, version, parameter_type) DO NOTHING
                    RETURNING id
                """)
                
                param_programs = {}
                for row in all_rows:
                    param_type = row[16]
                    limit_high = float(row[14]) if row[14] else 0.0
                    limit_low = float(row[15]) if row[15] else 0.0
                    
                    if param_type in param_programs:
                        continue
                    
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
                        fetch_prog = text("SELECT id FROM biz.program WHERE program_id = :pid AND version = :ver AND parameter_type = :param_type")
                        param_programs[param_type] = conn.execute(fetch_prog, {
                            "pid": program_identifier or str(program_id_num),
                            "ver": str(program_version) if program_version else "1",
                            "param_type": param_type
                        }).scalar()
                
                program_db_id = param_programs.get('Final Force') or (list(param_programs.values())[0] if param_programs else None)
                
                # B. Insert Result
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
                    "source_id": res_id,
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
                result_db_id = result_insert.fetchone()[0]
                
                # C. Insert Extension
                insert_ext = text("""
                    INSERT INTO biz.extension (result_id, extra_data)
                    VALUES (:rid, CAST(:extra AS jsonb))
                """)
                
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
                    "parameter_limits": param_limits
                }
                conn.execute(insert_ext, {"rid": result_db_id, "extra": json.dumps(extra_data)})
                # d. Insert Step
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
                    "rid": result_db_id,
                    "sidx": 0,
                    "sname": "Riveting",
                    "sres": result_status,
                    "sval": final_force,
                    "target": None, # Should be target_value but simplified
                    "sstart": result_time,
                    "send": end_time
                })
                step_db_id = step_result.fetchone()[0]

                # E. Insert Curves
                insert_curve = text("""
                    INSERT INTO biz.curve (result_id, step, curve_type, start_time, end_time, data_points)
                    VALUES (:rid, :step, :ctype, :sstart, :send, CAST(:data AS jsonb))
                """)
                
                for graph in graphs:
                    graph_type = graph[1]
                    graph_values = graph[2]
                    
                    if graph_values:
                        values = parse_spr_curve(graph_values)
                        if values:
                            time_axis = generate_time_axis(len(values), cycle_time)
                            
                            if 'Force' in graph_type:
                                curve_type = 'FORCE'
                            elif 'Stroke' in graph_type:
                                curve_type = 'STROKE'
                            else:
                                curve_type = graph_type.upper().replace('/', '_')
                            
                            payload = {"x": time_axis, "y": values}
                            conn.execute(insert_curve, {
                                "rid": result_db_id,
                                "step": 0,
                                "ctype": curve_type,
                                "sstart": result_time,
                                "send": end_time,
                                "data": json.dumps(payload)
                            })
                
                # F. Insert Alarm
                if result_status == 0:
                    insert_alarm = text("""
                        INSERT INTO biz.alarm (result_id, step_id, alarm_code, alarm_level, alarm_msg, device_id)
                        VALUES (:rid, :sid, :code, :level, :msg, :dev)
                    """)
                    conn.execute(insert_alarm, {
                        "rid": result_db_id,
                        "sid": step_db_id,
                        "code": "SPR_NOK",
                        "level": "ERROR",
                        "msg": short_desc or "SPR process failed",
                        "dev": device_name
                    })

            return True

        except Exception as e:
            print(f"[{self.name}] ❌ Error processing {detail_id}: {e}")
            return False
