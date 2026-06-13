import sys
import logging
from sqlalchemy import text
from etl_core.pipelines.fds import FdsPipeline

def run_trace():
    print('Starting test.py trace...', flush=True)
    p = FdsPipeline()
    autoindex = 4667587
    print(f'Pipeline initialized. Starting test for autoindex {autoindex}...', flush=True)
    try:
        with p.engine.begin() as conn:
            print('1. Engine began transaction.', flush=True)
            query_main = text("""
                SELECT
                    autoindex, actualprogramid, systemid, startselection, ok_nok_code,
                    lastexecutedstep, starttime, cyclenumber, duration, bsn, progselection, curve
                FROM origin.bs_fds_v_fds_curves
                WHERE autoindex = :idx
            """)
            print('2. Executing query_main...', flush=True)
            record = conn.execute(query_main, {'idx': autoindex}).fetchone()
            print(f'3. Finished query_main. Record found: {bool(record)}', flush=True)
    except Exception as e:
        print(f'Exception: {e}', flush=True)

if __name__ == '__main__':
    run_trace()
