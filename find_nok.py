from sqlalchemy import create_engine, text

def find_nok():
    engine = create_engine('postgresql+pg8000://postgres:6edef2d746f2274cab951a452d5fc13d@10.18.120.240:35432/equipment_mechanism')
    with engine.connect() as conn:
        # Find first NOK (0)
        row = conn.execute(text("SELECT autoindex, ok_nok_code, lastexecutedstep FROM origin.bs_fds_results WHERE ok_nok_code != 1 LIMIT 1")).fetchone()
        if row:
            print(f"Found NOK: {row}")
        else:
            print("No NOK records found.")

if __name__ == "__main__":
    find_nok()
