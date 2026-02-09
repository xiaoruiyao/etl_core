
import sqlalchemy
from sqlalchemy import create_engine, text
import json
from datetime import datetime

def json_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, bytes):
        return f"<binary data length={len(obj)}>"
    return str(obj)

def analyze_tables():
    DB_CONFIG = {
        'host': '10.18.120.240',
        'port': 35432,
        'database': 'equipment_mechanism',
        'user': 'postgres',
        'password': '6edef2d746f2274cab951a452d5fc13d',
        'driver': 'pg8000'
    }
    
    connection_string = f"postgresql+{DB_CONFIG['driver']}://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    
    try:
        engine = create_engine(connection_string)
        with engine.connect() as conn:
            target_id = 251067
            program_id = 68500 # From previous inspection of autoindex=251067
            
            print(f"=== ANALYZING RELATED DATA FOR Result ID {target_id} ===")
            
            # 1. Check bs_fds_singleresult (Step Results?)
            print(f"\n[checking origin.bs_fds_singleresult] WHERE resultlistid = {target_id}")
            query_single = text(f"SELECT * FROM origin.bs_fds_singleresult WHERE resultlistid = {target_id}")
            result_proxy = conn.execute(query_single)
            results_single = result_proxy.fetchall()
            if results_single:
                keys = result_proxy.keys()
                print(f"Found {len(results_single)} records:")
                for row in results_single:
                    row_dict = {k: json_serializer(v) for k, v in zip(keys, row)}
                    print(f"  {row_dict}")
            else:
                print("  No records found.")

            # 2. Check bs_fds_progtable (Program Info?)
            # Assuming actualprogramid (68500) maps to autoprogindex
            print(f"\n[checking origin.bs_fds_progtable] WHERE autoprogindex = {program_id}")
            query_prog = text(f"SELECT * FROM origin.bs_fds_progtable WHERE autoprogindex = {program_id}")
            prog_proxy = conn.execute(query_prog)
            result_prog = prog_proxy.fetchone()
            if result_prog:
                keys = prog_proxy.keys()
                row_dict = {k: json_serializer(v) for k, v in zip(keys, result_prog)}
                print(f"Found Program Record:\n  {row_dict}")
            else:
                print("  No records found using actualprogramid as autoprogindex.")
                # Try just listing one to see structure
                print("  Listing 1 random record from bs_fds_progtable to check structure:")
                random_proxy = conn.execute(text("SELECT * FROM origin.bs_fds_progtable LIMIT 1"))
                random_prog = random_proxy.fetchone()
                if random_prog:
                    keys = random_proxy.keys()
                    print(f"  { {k: json_serializer(v) for k, v in zip(keys, random_prog)} }")

            # 3. Check bs_fds_results (Base table)
            print(f"\n[checking origin.bs_fds_results] WHERE autoindex = {target_id}")
            query_res = text(f"SELECT * FROM origin.bs_fds_results WHERE autoindex = {target_id}")
            res_proxy = conn.execute(query_res)
            result_res = res_proxy.fetchone()
            if result_res:
                keys = res_proxy.keys()
                row_dict = {k: json_serializer(v) for k, v in zip(keys, result_res)}
                print(f"Found Result Record:\n  {row_dict}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze_tables()
