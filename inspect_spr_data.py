"""
SPR 数据源表结构深入分析
"""

from sqlalchemy import create_engine, text
import gzip
import struct
import json

DB_CONFIG = {
    'host': '10.18.120.240',
    'port': 35432,
    'database': 'equipment_mechanism',
    'user': 'postgres',
    'password': '6edef2d746f2274cab951a452d5fc13d',
    'driver': 'pg8000'
}

def create_db_engine():
    conn_str = f"postgresql+{DB_CONFIG['driver']}://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    return create_engine(conn_str, echo=False)

def analyze_curve_binary():
    """深入分析曲线二进制数据格式"""
    engine = create_db_engine()
    
    with engine.connect() as conn:
        print('=== 详细分析 Force/Time 曲线数据格式 ===')
        
        result = conn.execute(text('''
            SELECT id, graph_type, graph_values 
            FROM origin.bs_spr_graph 
            WHERE graph_type = 'Force/Time' 
            LIMIT 1
        '''))
        
        row = result.fetchone()
        if row:
            graph_id = row[0]
            graph_type = row[1]
            data = bytes(row[2])
            
            print(f'Graph ID: {graph_id}')
            print(f'Graph Type: {graph_type}')
            print(f'压缩数据大小: {len(data)} bytes')
            
            decompressed = gzip.decompress(data)
            print(f'解压后大小: {len(decompressed)} bytes')
            
            # 尝试解析为 float32 数组
            print(f'\n--- 尝试解析为 float32 数组 ---')
            num_floats = len(decompressed) // 4
            floats = struct.unpack(f'<{num_floats}f', decompressed[:num_floats*4])
            print(f'解析出 {num_floats} 个 float32 值')
            print(f'前20个值: {floats[:20]}')
            print(f'最后10个值: {floats[-10:]}')
            print(f'最小值: {min(floats)}, 最大值: {max(floats)}')
            
        print('\n=== 详细分析 Stroke/Time 曲线数据格式 ===')
        
        result = conn.execute(text('''
            SELECT id, graph_type, graph_values 
            FROM origin.bs_spr_graph 
            WHERE graph_type = 'Stroke/Time' 
            LIMIT 1
        '''))
        
        row = result.fetchone()
        if row:
            graph_id = row[0]
            graph_type = row[1]
            data = bytes(row[2])
            
            print(f'Graph ID: {graph_id}')
            print(f'Graph Type: {graph_type}')
            print(f'压缩数据大小: {len(data)} bytes')
            
            decompressed = gzip.decompress(data)
            print(f'解压后大小: {len(decompressed)} bytes')
            
            num_floats = len(decompressed) // 4
            floats = struct.unpack(f'<{num_floats}f', decompressed[:num_floats*4])
            print(f'解析出 {num_floats} 个 float32 值')
            print(f'前20个值: {floats[:20]}')
            print(f'最小值: {min(floats)}, 最大值: {max(floats)}')

def find_sample_583435():
    """查找 id=583435 对应的 graph 记录"""
    engine = create_db_engine()
    
    with engine.connect() as conn:
        print('\n=== 查找 id=583435 对应的 graph 记录 ===')
        
        # 获取 detail 记录
        detail = conn.execute(text('''
            SELECT id, sid, device_name, result_sequence_number, result_date_time,
                   program_id, p_name, program_identifier, program_version,
                   final_force, final_stroke, start_distance, end_distance,
                   velocity, cycle_time, limit_high, limit_low, parameter_type,
                   short_description, unit_id, position_id
            FROM origin.bs_spr_detail WHERE id = 583435
        ''')).fetchone()
        
        if detail:
            print(f'Detail Record:')
            cols = ['id', 'sid', 'device_name', 'result_sequence_number', 'result_date_time',
                   'program_id', 'p_name', 'program_identifier', 'program_version',
                   'final_force', 'final_stroke', 'start_distance', 'end_distance',
                   'velocity', 'cycle_time', 'limit_high', 'limit_low', 'parameter_type',
                   'short_description', 'unit_id', 'position_id']
            for i, col in enumerate(cols):
                print(f'  {col}: {detail[i]}')
            
            rsn = detail[3]  # result_sequence_number
            dev = detail[2]  # device_name
            
            # 查找对应的 graph 记录
            print(f'\n查找 graph 记录 (rsn={rsn}, device={dev})...')
            graphs = conn.execute(text('''
                SELECT id, graph_type, result_date_time, graph_values
                FROM origin.bs_spr_graph 
                WHERE result_sequence_number = :rsn AND device_name = :dev
            '''), {"rsn": rsn, "dev": dev}).fetchall()
            
            print(f'找到 {len(graphs)} 条 graph 记录')
            
            for g in graphs:
                print(f'\n--- Graph ID: {g[0]}, Type: {g[1]}, Time: {g[2]} ---')
                if g[3]:
                    data = bytes(g[3])
                    decompressed = gzip.decompress(data)
                    num_floats = len(decompressed) // 4
                    floats = struct.unpack(f'<{num_floats}f', decompressed[:num_floats*4])
                    print(f'  数据点数: {num_floats}')
                    print(f'  前10个值: {[round(f, 4) for f in floats[:10]]}')
                    print(f'  最小值: {min(floats):.4f}, 最大值: {max(floats):.4f}')
        else:
            print('未找到 id=583435 的记录')

def count_records():
    """统计记录数量"""
    engine = create_db_engine()
    
    with engine.connect() as conn:
        print('\n=== 统计记录数量 ===')
        
        cnt_detail = conn.execute(text('SELECT COUNT(*) FROM origin.bs_spr_detail')).scalar()
        cnt_graph = conn.execute(text('SELECT COUNT(*) FROM origin.bs_spr_graph')).scalar()
        
        print(f'bs_spr_detail: {cnt_detail} 条')
        print(f'bs_spr_graph: {cnt_graph} 条')
        
        # 统计每种 graph_type 的数量
        print('\n各 graph_type 数量:')
        result = conn.execute(text('''
            SELECT graph_type, COUNT(*) as cnt
            FROM origin.bs_spr_graph 
            GROUP BY graph_type
            ORDER BY cnt DESC
        '''))
        for row in result:
            print(f'  {row[0]}: {row[1]}')

if __name__ == "__main__":
    count_records()
    find_sample_583435()
    analyze_curve_binary()
