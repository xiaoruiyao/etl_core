from sqlalchemy import create_engine, text

def check():
    engine = create_engine('postgresql+pg8000://postgres:6edef2d746f2274cab951a452d5fc13d@10.18.120.240:35432/equipment_mechanism')
    with engine.connect() as conn:
        row = conn.execute(text("SELECT autoindex, ok_nok_code, lastexecutedstep FROM origin.bs_fds_results WHERE autoindex=537067")).fetchone()
        print(f"Row: {row}")

if __name__ == "__main__":
    import sys
    tid = 537067
    if len(sys.argv) > 1:
        tid = int(sys.argv[1])
    
    engine = create_engine('postgresql+pg8000://postgres:6edef2d746f2274cab951a452d5fc13d@10.18.120.240:35432/equipment_mechanism')
    with engine.connect() as conn:
        row = conn.execute(text(f"SELECT autoindex, ok_nok_code, lastexecutedstep FROM origin.bs_fds_results WHERE autoindex={tid}")).fetchone()
        print(f"Row: {row}")
