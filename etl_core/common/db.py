
from sqlalchemy import create_engine
from .config import DB_CONFIG

def create_db_engine(pool_size=10, max_overflow=20):
    conn_str = f"postgresql+{DB_CONFIG['driver']}://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    return create_engine(conn_str, echo=False, pool_size=pool_size, max_overflow=max_overflow)
