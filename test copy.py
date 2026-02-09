import requests
import json
import time

class SeresIoTClient:
    def __init__(self, token):
        self.base_url = "https://modeltool-model-product-infra-system.iot-2f.seres.cn"
        # self.headers = {
        #     'Authorization': f'bearer {token}',
        #     'Content-Type': 'application/json; charset=UTF-8',
        #     'Tenantid': 'platform',
        #     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36'
        # }
        self.headers = {
        'Content-Type': 'application/json'
        }

    def get_raw_value(self, node_id):
        """获取实时数据 (raw-valueV2)"""
        url = f"{self.base_url}/bff/v1/variable/ts/raw-valueV2"
        payload = [node_id]
        
        try:
            response = requests.post(url, headers=self.headers, json=payload, verify=False)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ 实时数据获取失败: {e}")
            return None

    def get_history_value(self, node_id, start_ms, end_ms, max_size=500):
        """获取历史数据 (history-raw-valueV2)"""
        url = f"{self.base_url}/bff/v1/variable/ts/history-raw-valueV2"
        payload = {
            "detail": {
                "maxSizePerNode": max_size,
                "startTime": start_ms,
                "endTime": end_ms,
                "returnBounds": True
            },
            "nodes": [
                {
                    "continuationPoint": None,
                    "identifier": node_id
                }
            ]
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload, verify=False)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ 历史数据获取失败: {e}")
            return None

# --- 使用示例 ---
# 这里的 Token 是从你提供的 curl 中提取的，注意它会过期
TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..." 
NODE_ID = "/first_infomodel/5da0753034d447f2a077a61cef6f1ee1"

client = SeresIoTClient(TOKEN)

# 1. 查询实时值
print("🚀 正在读取实时数据...")
raw_data = client.get_raw_value(NODE_ID)
print(json.dumps(raw_data, indent=2, ensure_ascii=False))

# 2. 查询历史值 (示例查询过去一小时)
now_ms = int(time.time() * 1000)
one_hour_ago_ms = now_ms - (10 * 1000)

print(f"\n⏳ 正在读取历史数据 ({one_hour_ago_ms} -> {now_ms})...")
history_data = client.get_history_value(NODE_ID, one_hour_ago_ms, now_ms)
print(json.dumps(history_data, indent=2, ensure_ascii=False))