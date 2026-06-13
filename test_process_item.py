import sys
import logging
from etl_core.pipelines.fds import FdsPipeline

class TracingFdsPipeline(FdsPipeline):
    def process_item(self, autoindex, engine):
        from sqlalchemy import text
        from datetime import timedelta
        import json
        print(f"Tracing process_item for {autoindex}...")
        try:
            with engine.begin() as conn:
                print("1. Fetch Main Record")
                query_main = text('''
                    SELECT
                        autoindex, actualprogramid, systemid, startselection, ok_nok_code,
                        lastexecutedstep, starttime, cyclenumber, duration, bsn, progselection, curve
                    FROM origin.bs_fds_v_fds_curves
                    WHERE autoindex = :idx
                ''')
                record = conn.execute(query_main, {"idx": autoindex}).fetchone()
                if not record:
                    print("No record found.")
                    return False
                
                print("Unpacking record...")
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

                print("2. Fetch Program Info")
                query_prog = text(f"SELECT name, lastchangedatetime, startstring FROM origin.bs_fds_progtable WHERE autoprogindex = :pid")
                prog_rec = conn.execute(query_prog, {"pid": prog_id_num}).fetchone()
                
                print("3. Fetch Single Results")
                query_kpi = text(f"SELECT type, step, value, resultindex FROM origin.bs_fds_singleresult WHERE resultlistid = :rid ORDER BY step, resultindex")
                kpi_recs = conn.execute(query_kpi, {"rid": res_id}).fetchall()
                
                print("A. Insert Program")
                program_code = str(prog_id_num)
                prog_version = 'unknown'
                insert_prog = text('''
                    INSERT INTO biz.program (program_id, version, program_name, device_type, craft_type, parameter_type)
                    VALUES (:pid, :ver, :pname, :dev, 'FDS_DEFAULT', 'DEFAULT')
                    ON CONFLICT (program_id, version, parameter_type) DO NOTHING
                    RETURNING id
                ''')
                result_prog_insert = conn.execute(insert_prog, {
                    "pid": program_code, "ver": prog_version, "pname": None, "dev": sys_id
                }).fetchone()
                print("Program inserted.")
                
                print("B. Insert Result")
                insert_result = text('''
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
                ''')
                result_insert = conn.execute(insert_result, {
                    "source_id": res_id, 
                    "cnum": cycle_num, "dev": sys_id, "sys": sys_id, 
                    "bsn": bsn, "pid_str": program_code, "pid_fk": 1,
                    "status": 1, "start": start_time, "end": end_time,
                    "duration": duration
                })
                print("Result inserted.")
                
            return True
        except Exception as e:
            print(f"Exception parsing: {e}")
            return False

if __name__ == '__main__':
    p = TracingFdsPipeline()
    print("Starting TracingFdsPipeline...")
    p.process_item(4667587, p.engine)
