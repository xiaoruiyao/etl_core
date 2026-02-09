
import struct
import base64
import json
from sqlalchemy import create_engine, text
from etl_fds_migration import parse_fds_curve, DB_CONFIG

def debug_parsing(autoindex):
    conn_str = f"postgresql+{DB_CONFIG['driver']}://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    engine = create_engine(conn_str)

    with engine.connect() as conn:
        query = text("""
            SELECT 
                autoindex, actualprogramid, systemid, startselection, ok_nok_code, 
                lastexecutedstep, starttime, cyclenumber, duration, bsn, progselection, curve 
            FROM origin.bs_fds_v_fds_curves 
            WHERE autoindex = :idx
        """)
        result = conn.execute(query, {"idx": autoindex}).fetchone()
        
        if not result:
            print(f"Record {autoindex} not found.")
            return
            
        print("Record found.")
        print(f"Autoindex: {result[0]}")
        print(f"ActualProgramID: {result[1]}")
        print(f"SystemID: {result[2]}")
        print(f"StartSelection: {result[3]}")
        print(f"OK_NOK_Code: {result[4]}")
        print(f"LastExecutedStep: {result[5]}")
        print(f"StartTime: {result[6]}")
        print(f"CycleNumber: {result[7]}")
        print(f"Duration: {result[8]}")
        print(f"BSN: {result[9]}")

        curve_blob = result[11] # Index 11 is curve based on query
        
        if curve_blob is None:
             print("Curve blob is None")
             # Continue to check KPIs


        print(f"Curve blob type: {type(curve_blob)}")
        
        if isinstance(curve_blob, bytes):
            print(f"Curve blob length: {len(curve_blob)}")
        elif isinstance(curve_blob, str):
            print(f"Curve blob length (str): {len(curve_blob)}")

        parsed = parse_fds_curve(curve_blob)
        if not parsed:
            print("Parsed result is None or empty.")
        else:
            print(f"Parsed {len(parsed)} points.")
            steps = set(p['step'] for p in parsed)
            print(f"Steps found: {steps}")
        if parsed:
                 print(f"First point: {parsed[0]}")
                 
        # Check Single Results
        print("-" * 20)
        print("Checking Single Results (KPIs)...")
        query_kpi = text(f"SELECT type, step, value, resultindex FROM origin.bs_fds_singleresult WHERE resultlistid = :rid")
        kpis = conn.execute(query_kpi, {"rid": autoindex}).fetchall()
        if kpis:
            print(f"Found {len(kpis)} KPI records.")
            steps = set(k[1] for k in kpis)
            print(f"KPI Steps: {steps}")
        else:
            print("No KPI records found.")

        # Check Migration Results in Biz Schema
        print("-" * 20)
        print("Checking Biz Schema...")
        
        # 1. Check Result
        query_biz_res = text("SELECT id, result_status FROM biz.result WHERE source_id = :src_id")
        biz_res = conn.execute(query_biz_res, {"src_id": autoindex}).fetchall()
        
        if biz_res:
             print(f"✅ Found {len(biz_res)} biz.result records.")
             for res in biz_res:
                 res_id = res[0]
                 status = res[1]
                 print(f"   ID: {res_id}, Status: {status}")
                 
                 # 2. Check Steps for each
                 query_biz_step = text("SELECT step_index, step_name, step_result FROM biz.step WHERE result_id = :rid ORDER BY step_index")
                 steps = conn.execute(query_biz_step, {"rid": res_id}).fetchall()
                 if steps:
                     print(f"      Found {len(steps)} steps in biz.step:")
                     for s in steps:
                         print(f"        Step {s[0]}: {s[1]}, Result: {s[2]}")
                 else:
                     print("      ❌ NO steps in biz.step!")
        else:
             print("❌ No record found in biz.result for this source_id.")


        # Check underlying table directly
        print("-" * 20)
        print("Checking origin.bs_fds_curveresults directly...")
        try:
            # Assuming link is via resultid = autoindex? Or is there a join?
            # Usually bs_fds_v_fds_curves joins bs_fds_results (autoindex) and bs_fds_curveresults (resultid)
            query_raw = text("SELECT curve FROM origin.bs_fds_curveresults WHERE resultid = :idx")
            raw_curve = conn.execute(query_raw, {"idx": autoindex}).fetchone()
            if raw_curve:
                print(f"✅ Found curve in bs_fds_curveresults! Length: {len(raw_curve[0]) if raw_curve[0] else 'None'}")
            else:
                print("❌ No curve found in bs_fds_curveresults for detailed check.")
        except Exception as e:
            print(f"⚠️ Failed to query bs_fds_curveresults: {e}")

if __name__ == "__main__":
    debug_parsing(403801)
