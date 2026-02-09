import requests
import json

def query_iot_data():
    # 1. 配置请求参数
    url = "https://bff-model-product-infra-system.iot-2f.seres.cn/bff/aggquery/v2/query/v2/queryHistoryRawValueByUri"
    
    # 从截图中提取的 JSON 数组 Payload
    # payload = [
    #     "/first_infomodel/b5ed23b41ddf4e5ba539c33ed9b0d1ee",
    #     "/first_infomodel/c05f5c158cb04417a8f0d84aae97dc5e",
    #     "/first_infomodel/5da0753034d447f2a077a61cef6f1ee1"
    # ]

    payload = {
  "detail": {
    "endTime": "2026-02-06 14:14:56",
    "maxSizePerNode": 0,
    "returnBounds": True,
    "startTime": "2026-02-06 14:13:56"
  },
  "nodes": [
    {
   
  
      "browsePath": "/first_infomodel/c05f5c158cb04417a8f0d84aae97dc5e"
 
    }
  ]
}
    
    headers = {
        'Content-Type': 'application/json'
    }

    try:
        # 2. 发送请求
        print(f"🚀 正在请求 API: {url}...")
        response = requests.post(url, headers=headers, json=payload, verify=False)
        
        # 3. 检查状态码
        response.raise_for_status()
        
        # 4. 解析并打印响应结果
        data = response.json()
        
        if data.get("code") == "0x00000000":
            print("✅ 请求成功！")
            # 格式化打印结果，方便观察工业遥测数据
            print(json.dumps(data, indent=4, ensure_ascii=False))
            
            # 如果你想提取具体的数值 (v)，可以遍历结果
            for item in data.get("result", []):
                print(f"🔹 时间戳 (t): {item.get('t')}, 测量值 (v): {item.get('v')}")
        else:
            print(f"❌ 业务逻辑错误: {data.get('msg')}")
            
    except requests.exceptions.RequestException as e:
        print(f"🔥 网络请求异常: {e}")

if __name__ == "__main__":
    query_iot_data()