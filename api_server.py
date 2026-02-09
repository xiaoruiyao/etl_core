"""
BIZ Dashboard API Server with WebSocket Support
FastAPI 后端服务，提供 biz schema 数据查询接口和设备实时数据 WebSocket
"""

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import json
import asyncio
import httpx
from typing import List, Dict, Set
from contextlib import asynccontextmanager

# --- Database Configuration ---
DB_CONFIG = {
    'host': '10.18.120.240',
    'port': 35432,
    'database': 'equipment_mechanism',
    'user': 'postgres',
    'password': '6edef2d746f2274cab951a452d5fc13d',
}

conn_str = f"postgresql+pg8000://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
engine = create_engine(conn_str, echo=False)

# --- External API for time series data ---
TIMESERIES_API_URL = "https://bff-model-product-infra-system.iot-2f.seres.cn/bff/aggquery/v2/query/v2/queryCurrentRawValueByUri"

# --- Proxy Configuration (for VPN/aTrust) ---
PROXY_URL = "http://127.0.0.1:7897"

# --- WebSocket Connection Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}  # device_id -> set of websockets
    
    async def connect(self, websocket: WebSocket, device_id: str):
        await websocket.accept()
        if device_id not in self.active_connections:
            self.active_connections[device_id] = set()
        self.active_connections[device_id].add(websocket)
        print(f"✅ WebSocket connected: {device_id} (total: {len(self.active_connections[device_id])})")
    
    def disconnect(self, websocket: WebSocket, device_id: str):
        if device_id in self.active_connections:
            self.active_connections[device_id].discard(websocket)
            if not self.active_connections[device_id]:
                del self.active_connections[device_id]
        print(f"❌ WebSocket disconnected: {device_id}")
    
    async def broadcast(self, device_id: str, message: dict):
        if device_id in self.active_connections:
            dead_connections = set()
            for connection in self.active_connections[device_id]:
                try:
                    await connection.send_json(message)
                except:
                    dead_connections.add(connection)
            for dc in dead_connections:
                self.active_connections[device_id].discard(dc)

manager = ConnectionManager()

# --- Background task for fetching real-time data ---
async def fetch_device_uri_data():
    """Periodically fetch device URI data and broadcast to WebSocket clients"""
    async with httpx.AsyncClient(timeout=30.0, verify=False, trust_env=False) as client:
        while True:
            try:
                # Get all device URIs that have active connections
                device_ids = list(manager.active_connections.keys())
                if device_ids:
                    for device_id in device_ids:
                        try:
                            # Get URIs for this device
                            with engine.connect() as conn:
                                query = text("""
                                    SELECT id, uri, name FROM biz.device_uri 
                                    WHERE device_id = :device_id
                                """)
                                rows = conn.execute(query, {"device_id": device_id}).fetchall()
                            
                            if rows:
                                uris = [row[1] for row in rows]
                                uri_names = {row[1]: row[2] for row in rows}
                                
                                print(f"📡 Fetching data for {device_id}, URIs: {uris}")
                                
                                # Fetch current values from external API
                                response = await client.post(
                                    TIMESERIES_API_URL,
                                    json=uris,
                                    headers={"Content-Type": "application/json"}
                                )
                                
                                print(f"📥 Response status: {response.status_code}")
                                
                                if response.status_code == 200:
                                    data = response.json()
                                    print(f"📦 Response data: {data}")
                                    
                                    if data.get("code") == "0x00000000":
                                        results = data.get("result", [])
                                        # Map results to URI names
                                        uri_values = []
                                        for i, uri in enumerate(uris):
                                            if i < len(results):
                                                result = results[i]
                                                uri_values.append({
                                                    "uri": uri,
                                                    "name": uri_names.get(uri, uri),
                                                    "value": result.get("v", "").strip() if result.get("v") else None,
                                                    "timestamp": result.get("t"),
                                                    "status": result.get("s")
                                                })
                                        
                                        # Broadcast to connected clients
                                        await manager.broadcast(device_id, {
                                            "type": "uri_data",
                                            "device_id": device_id,
                                            "data": uri_values,
                                            "fetch_time": datetime.now().isoformat()
                                        })
                                        print(f"✅ Broadcast {len(uri_values)} values to {device_id}")
                                    else:
                                        print(f"⚠️ API returned error code: {data.get('code')}")
                                else:
                                    print(f"❌ API returned status {response.status_code}: {response.text[:200]}")
                            else:
                                print(f"ℹ️ No URIs found for device {device_id}")
                        except httpx.TimeoutException as e:
                            print(f"⏱️ Timeout fetching data for {device_id}: {type(e).__name__}: {e}")
                        except httpx.RequestError as e:
                            print(f"🌐 Network error for {device_id}: {type(e).__name__}: {e}")
                            import traceback
                            traceback.print_exc()
                        except Exception as e:
                            print(f"❌ Error fetching data for {device_id}: {type(e).__name__}: {e}")
                            import traceback
                            traceback.print_exc()
                
                await asyncio.sleep(3)  # Fetch every 3 seconds
            except Exception as e:
                print(f"Background fetch error: {type(e).__name__}: {e}")
                await asyncio.sleep(5)

# --- App Lifecycle ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background task
    task = asyncio.create_task(fetch_device_uri_data())
    print("🔄 Started background data fetching task")
    yield
    task.cancel()

# --- FastAPI App ---
app = FastAPI(title="BIZ Dashboard API", version="2.0.0", lifespan=lifespan)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def row_to_dict(row, keys):
    """Convert SQLAlchemy row to dict"""
    return dict(zip(keys, row))


# ========== WebSocket Endpoint ==========

@app.websocket("/ws/device/{device_id}")
async def websocket_device(websocket: WebSocket, device_id: str):
    """WebSocket endpoint for real-time device data"""
    await manager.connect(websocket, device_id)
    try:
        # Send initial URI data
        with engine.connect() as conn:
            query = text("""
                SELECT id, uri, name, level FROM biz.device_uri 
                WHERE device_id = :device_id
                ORDER BY level, id
            """)
            rows = conn.execute(query, {"device_id": device_id}).fetchall()
            uri_list = [{"id": r[0], "uri": r[1], "name": r[2], "level": r[3]} for r in rows]
        
        await websocket.send_json({
            "type": "uri_list",
            "device_id": device_id,
            "uris": uri_list
        })
        
        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            # Can handle client messages here if needed
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket, device_id)


# ========== Device URI REST API ==========

@app.get("/api/devices/{device_name}/uris")
def get_device_uris(device_name: str):
    """获取设备的URI列表"""
    with engine.connect() as conn:
        query = text("""
            SELECT id, device_id, uri, level, name, COALESCE(display_type, 'card') as display_type
            FROM biz.device_uri
            WHERE device_id = :device_id
            ORDER BY level, id
        """)
        rows = conn.execute(query, {"device_id": device_name}).fetchall()
        keys = ["id", "device_id", "uri", "level", "name", "display_type"]
        return {"items": [row_to_dict(row, keys) for row in rows]}


@app.post("/api/devices/{device_name}/uris/current")
async def get_device_uri_current_values(device_name: str):
    """获取设备URI的当前值 (调用外部API)"""
    with engine.connect() as conn:
        query = text("""
            SELECT uri, name FROM biz.device_uri WHERE device_id = :device_id
        """)
        rows = conn.execute(query, {"device_id": device_name}).fetchall()
    
    if not rows:
        return {"items": []}
    
    uris = [r[0] for r in rows]
    uri_names = {r[0]: r[1] for r in rows}
    
    try:
        async with httpx.AsyncClient(timeout=30.0, verify=False, trust_env=False) as client:
            response = await client.post(
                TIMESERIES_API_URL,
                json=uris,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == "0x00000000":
                    results = data.get("result", [])
                    items = []
                    for i, uri in enumerate(uris):
                        if i < len(results):
                            result = results[i]
                            items.append({
                                "uri": uri,
                                "name": uri_names.get(uri, uri),
                                "value": result.get("v", "").strip() if result.get("v") else None,
                                "timestamp": result.get("t"),
                                "status": result.get("s")
                            })
                    return {"items": items}
    except Exception as e:
        print(f"❌ Proxy error: {type(e).__name__}: {e}")
        return {"error": str(e), "items": []}
    
    return {"items": []}


@app.post("/api/proxy/timeseries")
async def proxy_timeseries(uris: list[str]):
    """代理请求到外部时序API (解决CORS问题)"""
    print(f"🔄 Proxy request for {len(uris)} URIs: {uris}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0, verify=False, trust_env=False) as client:
            response = await client.post(
                TIMESERIES_API_URL,
                json=uris,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"📥 Proxy response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Proxy success: {data}")
                return data
            else:
                print(f"❌ Proxy failed: {response.status_code} - {response.text[:200]}")
                return {"code": "error", "msg": f"HTTP {response.status_code}"}
    except httpx.TimeoutException as e:
        print(f"⏱️ Proxy timeout: {e}")
        return {"code": "timeout", "msg": "Request timeout"}
    except httpx.RequestError as e:
        print(f"🌐 Proxy network error: {type(e).__name__}: {e}")
        return {"code": "network_error", "msg": str(e)}
    except Exception as e:
        print(f"❌ Proxy exception: {type(e).__name__}: {e}")
        return {"code": "error", "msg": str(e)}


# --- Original API Endpoints ---

@app.get("/api/stats")
def get_stats():
    """获取仪表盘统计数据"""
    with engine.connect() as conn:
        # 总数统计
        total = conn.execute(text("SELECT COUNT(*) FROM biz.result")).scalar()
        ok_count = conn.execute(text("SELECT COUNT(*) FROM biz.result WHERE result_status = 1")).scalar()
        nok_count = conn.execute(text("SELECT COUNT(*) FROM biz.result WHERE result_status = 0")).scalar()
        alarm_count = conn.execute(text("SELECT COUNT(*) FROM biz.alarm")).scalar()
        
        # 工艺分布
        craft_sql = text("""
            SELECT craft_type, COUNT(*) as count 
            FROM biz.result 
            GROUP BY craft_type 
            ORDER BY count DESC
        """)
        craft_rows = conn.execute(craft_sql).fetchall()
        craft_distribution = [{"craft_type": r[0], "count": r[1]} for r in craft_rows]
        
        # 最近7天趋势
        trend_sql = text("""
            SELECT DATE(start_time) as date, COUNT(*) as count
            FROM biz.result
            WHERE start_time >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY DATE(start_time)
            ORDER BY date
        """)
        trend_rows = conn.execute(trend_sql).fetchall()
        trend = {
            "dates": [str(r[0]) for r in trend_rows],
            "counts": [r[1] for r in trend_rows]
        }
        
        return {
            "total_count": total,
            "ok_count": ok_count,
            "nok_count": nok_count,
            "alarm_count": alarm_count,
            "craft_distribution": craft_distribution,
            "trend": trend
        }


@app.get("/api/results")
def get_results(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    craft_type: str = None,
    status: int = None,
    structure_id: int = None
):
    """获取结果列表"""
    with engine.connect() as conn:
        # 构建查询
        where_clauses = []
        params = {}
        
        if craft_type:
            where_clauses.append("craft_type = :craft_type")
            params["craft_type"] = craft_type
        if status is not None:
            where_clauses.append("result_status = :status")
            params["status"] = status
        
        # Hierarchy Filter
        if 'structure_id' in locals() and locals()['structure_id']:
            sid = locals()['structure_id']
            # Find path for this structure
            path_res = conn.execute(text("SELECT path FROM biz.structure WHERE id = :sid"), {"sid": sid}).fetchone()
            if path_res:
                path = path_res[0]
                # Filter results where device_name belongs to any node under this path
                where_clauses.append("""
                    device_name IN (
                        SELECT device_name FROM biz.structure 
                        WHERE path LIKE :path_like AND device_name IS NOT NULL
                    )
                """)
                params["path_like"] = f"{path}%"
            else:
                # Structure not found, return empty
                where_clauses.append("1=0")
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        # 计数
        count_sql = text(f"SELECT COUNT(*) FROM biz.result WHERE {where_sql}")
        total = conn.execute(count_sql, params).scalar()
        
        # 分页查询
        offset = (page - 1) * page_size
        query_sql = text(f"""
            SELECT id, cyclenumber, device_name, craft_type, bsn, vin,
                   program_id, result_status, start_time, end_time, cycle_time, key_value
            FROM biz.result
            WHERE {where_sql}
            ORDER BY start_time DESC
            LIMIT :limit OFFSET :offset
        """)
        params["limit"] = page_size
        params["offset"] = offset
        
        rows = conn.execute(query_sql, params).fetchall()
        keys = ["id", "cyclenumber", "device_name", "craft_type", "bsn", "vin",
                "program_id", "result_status", "start_time", "end_time", "cycle_time", "key_value"]
        
        items = []
        for row in rows:
            item = row_to_dict(row, keys)
            # 序列化时间
            if item["start_time"]:
                item["start_time"] = item["start_time"].isoformat()
            if item["end_time"]:
                item["end_time"] = item["end_time"].isoformat()
            items.append(item)
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size
        }


@app.get("/api/results/{result_id}")
def get_result_detail(result_id: int):
    """获取结果详情"""
    with engine.connect() as conn:
        query = text("""
            SELECT id, cyclenumber, device_name, craft_type, system_id, bsn, vin,
                   program_id, program_ver_id, result_status, status_code,
                   start_time, end_time, cycle_time, key_value
            FROM biz.result
            WHERE id = :id
        """)
        row = conn.execute(query, {"id": result_id}).fetchone()
        
        if not row:
            return {"error": "Result not found"}
        
        keys = ["id", "cyclenumber", "device_name", "craft_type", "system_id", "bsn", "vin",
                "program_id", "program_ver_id", "result_status", "status_code",
                "start_time", "end_time", "cycle_time", "key_value"]
        result = row_to_dict(row, keys)
        
        if result["start_time"]:
            result["start_time"] = result["start_time"].isoformat()
        if result["end_time"]:
            result["end_time"] = result["end_time"].isoformat()
        
        return result


@app.get("/api/results/{result_id}/steps")
def get_result_steps(result_id: int):
    """获取结果的步骤列表"""
    with engine.connect() as conn:
        query = text("""
            SELECT id, step_index, step_name, step_result, step_value, target_value,
                   start_time, end_time
            FROM biz.step
            WHERE result_id = :rid
            ORDER BY step_index
        """)
        rows = conn.execute(query, {"rid": result_id}).fetchall()
        
        keys = ["id", "step_index", "step_name", "step_result", "step_value", "target_value",
                "start_time", "end_time"]
        
        items = []
        for row in rows:
            item = row_to_dict(row, keys)
            if item["start_time"]:
                item["start_time"] = item["start_time"].isoformat()
            if item["end_time"]:
                item["end_time"] = item["end_time"].isoformat()
            items.append(item)
        
        return items


@app.get("/api/results/{result_id}/curves")
def get_result_curves(result_id: int):
    """获取结果的曲线数据"""
    with engine.connect() as conn:
        query = text("""
            SELECT id, step, curve_type, start_time, end_time, data_points
            FROM biz.curve
            WHERE result_id = :rid
            ORDER BY step, curve_type
        """)
        rows = conn.execute(query, {"rid": result_id}).fetchall()
        
        items = []
        for row in rows:
            item = {
                "id": row[0],
                "step": row[1],
                "curve_type": row[2],
                "start_time": row[3].isoformat() if row[3] else None,
                "end_time": row[4].isoformat() if row[4] else None,
                "data_points": row[5] if row[5] else None
            }
            items.append(item)
        
        return items


@app.get("/api/alarms")
def get_alarms(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    result_id: int = None,
    structure_id: int = None,
    limit: int = None
):
    """获取报警列表"""
    with engine.connect() as conn:
        where_clauses = []
        params = {}
        
        if result_id:
            where_clauses.append("a.result_id = :result_id") 
            params["result_id"] = result_id
            
        # Hierarchy Filter for Alarms
        if 'structure_id' in locals() and locals()['structure_id']:
            sid = locals()['structure_id']
            path_res = conn.execute(text("SELECT path FROM biz.structure WHERE id = :sid"), {"sid": sid}).fetchone()
            if path_res:
                path = path_res[0]
                # Filter alarms where associated device matches hierarchy
                # Note: Alarms join Result to get device_name usually, or we need to ensure device_name is available
                # The current get_alarms doesn't join result by default for filtering, let's check.
                # Actually below queries do join result r on a.result_id = r.id.
                # But to filter efficiently, we might need that join in the COUNT query too.
                pass 
            else:
                 where_clauses.append("1=0")

        # Refined Logic: We need to handle the JOIN if we filter by device/hierarchy
        # Let's reconstruct the queries to be safe.
        base_from = "FROM biz.alarm a"
        if ('structure_id' in locals() and locals()['structure_id']) or ('device_name' in locals() and locals().get('device_name')):
             base_from += " JOIN biz.result r ON a.result_id = r.id"
        
        if 'structure_id' in locals() and locals()['structure_id']:
             sid = locals()['structure_id']
             path_res = conn.execute(text("SELECT path FROM biz.structure WHERE id = :sid"), {"sid": sid}).fetchone()
             if path_res:
                 path = path_res[0]
                 where_clauses.append("""
                    r.device_name IN (
                        SELECT device_name FROM biz.structure 
                        WHERE path LIKE :path_like AND device_name IS NOT NULL
                    )
                 """)
                 params["path_like"] = f"{path}%"
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        # 计数 - Need to use base_from
        count_sql = text(f"SELECT COUNT(a.id) {base_from} WHERE {where_sql}")
        total = conn.execute(count_sql, params).scalar()
        
        # 查询
        select_fields = "a.id, a.result_id, a.step_id, a.alarm_code, a.alarm_level, a.alarm_msg, a.parent_alarm_id, a.create_time"
        # Ensure we always JOIN if needed for the SELECT too?
        # The main queries below DONT join result unless we change them. 
        # But wait, lines 521 and 531 in original code DO NOT join result.
        # So we MUST add the join to the query_sql if we added it to count_sql
        
        # Original query didn't have join.
        query_from = base_from 
        if "JOIN biz.result" not in query_from and "r.device_name" in where_sql:
             # Should be covered by base_from logic above
             pass

        if limit:
            query_sql = text(f"""
                SELECT {select_fields}
                {query_from}
                WHERE {where_sql}
                ORDER BY a.create_time DESC
                LIMIT :limit
            """)
            params["limit"] = limit
        else:
            offset = (page - 1) * page_size
            query_sql = text(f"""
                SELECT {select_fields}
                {query_from}
                WHERE {where_sql}
                ORDER BY a.create_time DESC
                LIMIT :limit OFFSET :offset
            """)
            params["limit"] = page_size
            params["offset"] = offset
        
        rows = conn.execute(query_sql, params).fetchall()
        keys = ["id", "result_id", "step_id", "alarm_code", "alarm_level", "alarm_msg", "parent_alarm_id", "create_time"]
        
        items = []
        for row in rows:
            item = row_to_dict(row, keys)
            if item["create_time"]:
                item["create_time"] = item["create_time"].isoformat()
            items.append(item)
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size
        }


# ========== Devices API ==========

@app.get("/api/devices")
def get_devices():
    """获取设备列表及统计 (Union of Result & Structure)"""
    with engine.connect() as conn:
        # Strategy:
        # 1. Get all devices from biz.result (The "Old Logic" source)
        # 2. Get all devices from biz.structure (The "New Logic" source)
        # 3. Union them to get the complete universe of devices
        # 4. Join stats
        
        query = text("""
            WITH 
            -- 1. Result Stats (Source of Truth for Production Devices)
            result_stats AS (
                SELECT 
                    device_name, 
                    MAX(craft_type) as craft_type,
                    COUNT(*) as total_count,
                    SUM(CASE WHEN result_status = 1 THEN 1 ELSE 0 END) as ok_count,
                    SUM(CASE WHEN result_status = 0 THEN 1 ELSE 0 END) as nok_count
                FROM biz.result
                WHERE device_name IS NOT NULL
                GROUP BY device_name
            ),
            
            -- 2. Structure Info (Source for PLCs / Non-Result Devices)
            structure_info AS (
                SELECT DISTINCT device_name, level_type
                FROM biz.structure 
                WHERE device_name IS NOT NULL
            ),
            
            -- 3. Alarm Stats
            alarm_stats AS (
                SELECT device_id, COUNT(*) as alarm_count
                FROM biz.alarm
                WHERE device_id IS NOT NULL
                GROUP BY device_id
            ),
            
            -- 4. URI Stats
            uri_stats AS (
                SELECT device_id, COUNT(*) as uri_count
                FROM biz.device_uri
                WHERE device_id IS NOT NULL
                GROUP BY device_id
            ),
            
            -- 5. Universe of Devices
            all_devices AS (
                SELECT device_name FROM result_stats
                UNION
                SELECT device_name FROM structure_info
            )
            
            SELECT 
                d.device_name,
                COALESCE(r.craft_type, s.level_type) as craft_type,
                COALESCE(r.total_count, 0) as total_count,
                COALESCE(r.ok_count, 0) as ok_count,
                COALESCE(r.nok_count, 0) as nok_count,
                CASE 
                    WHEN COALESCE(r.total_count, 0) = 0 THEN 0
                    ELSE ROUND(100.0 * COALESCE(r.ok_count, 0) / r.total_count, 1) 
                END as ok_rate,
                COALESCE(a.alarm_count, 0) as alarm_count,
                COALESCE(u.uri_count, 0) as uri_count
            FROM all_devices d
            LEFT JOIN result_stats r ON d.device_name = r.device_name
            LEFT JOIN structure_info s ON d.device_name = s.device_name
            LEFT JOIN alarm_stats a ON d.device_name = a.device_id
            LEFT JOIN uri_stats u ON d.device_name = u.device_id
            ORDER BY d.device_name
        """)
        
        rows = conn.execute(query).fetchall()
        
        items = []
        for row in rows:
            items.append({
                "device_name": row[0],
                "craft_type": row[1],
                "total_count": row[2],
                "ok_count": row[3],
                "nok_count": row[4],
                "ok_rate": float(row[5]),
                "alarm_count": row[6],
                "uri_count": row[7],
                "status": "error" if row[6] > 0 else "ok"
            })
        
        return {"items": items}


@app.get("/api/devices/{device_name}")
def get_device_detail(device_name: str):
    """获取设备详情统计"""
    with engine.connect() as conn:
        query = text("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN result_status = 1 THEN 1 ELSE 0 END) as ok_count,
                SUM(CASE WHEN result_status = 0 THEN 1 ELSE 0 END) as nok_count,
                ROUND(100.0 * SUM(CASE WHEN result_status = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) as ok_rate
            FROM biz.result
            WHERE device_name = :name
        """)
        row = conn.execute(query, {"name": device_name}).fetchone()
        
        alarm_query = text("""
            SELECT COUNT(a.id)
            FROM biz.alarm a
            LEFT JOIN biz.result r ON a.result_id = r.id
            WHERE COALESCE(a.device_id, r.device_name) = :name
        """)
        alarm_count = conn.execute(alarm_query, {"name": device_name}).scalar()
        
        # Get URI count
        uri_query = text("SELECT COUNT(*) FROM biz.device_uri WHERE device_id = :name")
        uri_count = conn.execute(uri_query, {"name": device_name}).scalar()
        
        return {
            "device_name": device_name,
            "total": row[0] if row else 0,
            "ok_count": row[1] if row else 0,
            "nok_count": row[2] if row else 0,
            "ok_rate": float(row[3]) if row and row[3] else 0,
            "alarm_count": alarm_count or 0,
            "uri_count": uri_count or 0
        }


@app.get("/api/devices/{device_name}/results")
def get_device_results(
    device_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    limit: int = None
):
    """获取设备的结果列表"""
    with engine.connect() as conn:
        count_sql = text("SELECT COUNT(*) FROM biz.result WHERE device_name = :name")
        total = conn.execute(count_sql, {"name": device_name}).scalar()
        
        if limit:
            query_sql = text("""
                SELECT id, cyclenumber, craft_type, bsn, result_status, start_time, key_value
                FROM biz.result
                WHERE device_name = :name
                ORDER BY start_time DESC
                LIMIT :limit
            """)
            rows = conn.execute(query_sql, {"name": device_name, "limit": limit}).fetchall()
        else:
            offset = (page - 1) * page_size
            query_sql = text("""
                SELECT id, cyclenumber, craft_type, bsn, result_status, start_time, key_value
                FROM biz.result
                WHERE device_name = :name
                ORDER BY start_time DESC
                LIMIT :limit OFFSET :offset
            """)
            rows = conn.execute(query_sql, {"name": device_name, "limit": page_size, "offset": offset}).fetchall()
        
        keys = ["id", "cyclenumber", "craft_type", "bsn", "result_status", "start_time", "key_value"]
        items = []
        for row in rows:
            item = row_to_dict(row, keys)
            if item["start_time"]:
                item["start_time"] = item["start_time"].isoformat()
            items.append(item)
        
        return {"items": items, "total": total}


        return {"items": items, "total": total}


@app.get("/api/devices/{device_name}/alarms")
def get_device_alarms(
    device_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    limit: int = None
):
    """获取设备的报警列表 (Hybrid: device_id OR result.device_name)"""
    with engine.connect() as conn:
        # Hybrid Filter: Matches alarm.device_id OR associated result's device_name
        base_query = """
            FROM biz.alarm a
            LEFT JOIN biz.result r ON a.result_id = r.id
            WHERE COALESCE(a.device_id, r.device_name) = :name
        """
        
        count_sql = text(f"SELECT COUNT(a.id) {base_query}")
        total = conn.execute(count_sql, {"name": device_name}).scalar()
        
        select_fields = "a.id, a.result_id, a.alarm_code, a.alarm_level, a.alarm_msg, a.create_time, COALESCE(a.device_id, r.device_name) as device_id"
        
        if limit:
            query_sql = text(f"""
                SELECT {select_fields}
                {base_query}
                ORDER BY a.create_time DESC
                LIMIT :limit
            """)
            params = {"name": device_name, "limit": limit}
        else:
            offset = (page - 1) * page_size
            query_sql = text(f"""
                SELECT {select_fields}
                {base_query}
                ORDER BY a.create_time DESC
                LIMIT :limit OFFSET :offset
            """)
            params = {"name": device_name, "limit": page_size, "offset": offset}
            
        rows = conn.execute(query_sql, params).fetchall()
        
        keys = ["id", "result_id", "alarm_code", "alarm_level", "alarm_msg", "create_time", "device_id"]
        items = []
        for row in rows:
            item = row_to_dict(row, keys)
            if item["create_time"]:
                item["create_time"] = item["create_time"].isoformat()
            items.append(item)
        
        return {"items": items, "total": total}


@app.get("/api/alarms/{alarm_id}/hierarchy")
def get_alarm_hierarchy(alarm_id: int):
    """获取报警的层级结构 (双向: 溯源 + 影响)"""
    with engine.connect() as conn:
        query = text("""
            WITH RECURSIVE 
            -- 1. Ancestors (Upwards)
            ancestors AS (
                SELECT id, result_id, alarm_code, alarm_msg, parent_alarm_id, -1 as level  -- Parents have negative level
                FROM biz.alarm 
                WHERE id = (SELECT parent_alarm_id FROM biz.alarm WHERE id = :target_id)
                
                UNION ALL
                
                SELECT a.id, a.result_id, a.alarm_code, a.alarm_msg, a.parent_alarm_id, t.level - 1
                FROM biz.alarm a 
                JOIN ancestors t ON a.id = t.parent_alarm_id
            ),
            
            -- 2. Descendants (Downwards)
            descendants AS (
                SELECT id, result_id, alarm_code, alarm_msg, parent_alarm_id, 1 as level -- Children have positive level
                FROM biz.alarm 
                WHERE parent_alarm_id = :target_id
                
                UNION ALL
                
                SELECT a.id, a.result_id, a.alarm_code, a.alarm_msg, a.parent_alarm_id, t.level + 1
                FROM biz.alarm a 
                JOIN descendants t ON a.parent_alarm_id = t.id
            )
            
            -- 3. Combine All
            SELECT * FROM ancestors
            UNION ALL
            SELECT id, result_id, alarm_code, alarm_msg, parent_alarm_id, 0 as level FROM biz.alarm WHERE id = :target_id
            UNION ALL
            SELECT * FROM descendants
            
            ORDER BY level ASC;
        """)
        rows = conn.execute(query, {"target_id": alarm_id}).fetchall()
        
        keys = ["id", "result_id", "alarm_code", "alarm_msg", "parent_alarm_id", "level"]
        return [row_to_dict(row, keys) for row in rows]


# ========== Device Hierarchy & Point APIs ==========

@app.get("/api/structure/tree")
def get_structure_tree():
    """获取设备层级树，后端组装成树形结构"""
    with engine.connect() as conn:
        # Fetch all nodes (Assuming volume is manageable for now, < 10k nodes)
        nodes = conn.execute(text("SELECT id, name, level_type, parent_id, path, device_name, attributes FROM biz.structure ORDER BY id")).fetchall()
        
        node_map = {}
        roots = []
        
        # 1. Create nodes
        for row in nodes:
            node = {
                "id": row.id,
                "label": row.name, # Use 'label' for element-plus tree compatibility
                "type": row.level_type,
                "parent_id": row.parent_id,
                "path": row.path,
                "device_name": row.device_name,
                "attributes": row.attributes,
                "children": []
            }
            node_map[row.id] = node
        
        # 2. Assemble tree
        for node_id, node in node_map.items():
            parent_id = node["parent_id"]
            if parent_id and parent_id in node_map:
                node_map[parent_id]["children"].append(node)
            else:
                roots.append(node)
                
        return roots

@app.get("/api/points")
def get_points(structure_id: int = None, plc_id: int = None):
    """
    查询点位：
    - 查工位: structure_id (Physical)
    - 查PLC: plc_id (Logical) -> 包含 PLC 自身 + 它控制的设备
    """
    with engine.connect() as conn:
        where_clauses = ["1=1"]
        params = {}
        
        if plc_id:
            # 逻辑视图: PLC自身 OR 属性中 plc_id 指向该 PLC 的节点
            where_clauses.append("""
                (structure_id = :plc_id OR 
                 structure_id IN (SELECT id FROM biz.structure WHERE attributes->>'plc_id' = :plc_id_str))
            """)
            params["plc_id"] = plc_id
            params["plc_id_str"] = str(plc_id)
        elif structure_id:
            # 物理视图: 该节点及其子节点（通过Path查询）
            # First get the path of the structure
            path_res = conn.execute(text("SELECT path FROM biz.structure WHERE id = :sid"), {"sid": structure_id}).fetchone()
            if path_res:
                path = path_res[0]
                where_clauses.append("structure_id IN (SELECT id FROM biz.structure WHERE path LIKE :path_like)")
                params["path_like"] = f"{path}%"
            else:
                return [] # Node not found
        
        query = text(f"""
            SELECT id, structure_id, device_id, point_name, point_uri, group_path, data_type, is_ts
            FROM biz.point
            WHERE {" AND ".join(where_clauses)}
        """)
        
        rows = conn.execute(query, params).fetchall()
        keys = ["id", "structure_id", "device_id", "point_name", "point_uri", "group_path", "data_type", "is_ts"]
        return [row_to_dict(row, keys) for row in rows]



@app.post("/api/proxy/timeseries")
async def proxy_timeseries(request: Request):
    """
    Proxy time-series request to external IoT platform (Realtime Value)
    Target: .../queryCurrentRawValueByUri
    """
    try:
        data = await request.json()
        if not data:
            return {"code": "400", "msg": "Empty body"}
        
        target_url = "https://bff-model-product-infra-system.iot-2f.seres.cn/bff/aggquery/v2/query/v2/queryCurrentRawValueByUri"
        
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.post(target_url, json=data, headers={"Content-Type": "application/json"}, timeout=5.0)
            if resp.status_code == 200:
                # print(f"✅ Proxy success: {resp.json().get('code')}")
                return resp.json()
            else:
                print(f"❌ Proxy failed: {resp.status_code} - {resp.text}")
                return {"code": str(resp.status_code), "msg": "Upstream error"}
                
    except Exception as e:
        print(f"❌ Proxy exception: {e}")
        return {"code": "500", "msg": str(e)}


@app.post("/api/proxy/timeseries/history")
async def proxy_timeseries_history(request: Request):
    """
    Proxy time-series request for HISTORY data
    Target: .../queryHistoryRawValueByUri
    Payload: { detail: {startTime, endTime, ...}, nodes: [{browsePath: ...}] }
    """
    try:
        data = await request.json()
        if not data:
            return {"code": "400", "msg": "Empty body"}
        
        target_url = "https://bff-model-product-infra-system.iot-2f.seres.cn/bff/aggquery/v2/query/v2/queryHistoryRawValueByUri"
        
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.post(target_url, json=data, headers={"Content-Type": "application/json"}, timeout=30.0)
            if resp.status_code == 200:
                print(f"✅ History Proxy success: {resp.json().get('code')}")
                return resp.json()
            else:
                print(f"❌ History Proxy failed: {resp.status_code} - {resp.text}")
                return {"code": str(resp.status_code), "msg": "Upstream error"}
                
    except Exception as e:
        print(f"❌ History Proxy exception: {e}")
        return {"code": "500", "msg": str(e)}


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting BIZ Dashboard API Server with WebSocket...")
    print("📖 API Docs: http://localhost:8000/docs")
    print("🔌 WebSocket: ws://localhost:8000/ws/device/{device_id}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
