
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

def inspect_data():
    DB_CONFIG = {
        'host': '10.18.120.240',
        'port': 35432,
        'database': 'equipment_mechanism', # Changed from miot_quality_data to equipment_mechanism as per 需求.txt
        'user': 'postgres',
        'password': '6edef2d746f2274cab951a452d5fc13d',
        'driver': 'pg8000'
    }
    
    connection_string = f"postgresql+{DB_CONFIG['driver']}://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    
    try:
        engine = create_engine(connection_string)
        with engine.connect() as conn:
            # 1. List all tables in 'origin' schema
            print("Tables in 'origin' schema:")
            print("-" * 50)
            tables_query = text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'origin'")
            tables_result = conn.execute(tables_query)
            tables = [row[0] for row in tables_result]
            
            for table in tables:
                print(f"\nTable: {table}")
                # 2. Get columns for each table
                columns_query = text(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'origin' AND table_name = '{table}'")
                columns_result = conn.execute(columns_query)
                for col in columns_result:
                    print(f"  - {col[0]} ({col[1]})")
            print("-" * 50)
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_data()
