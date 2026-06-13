"""
添加性能优化索引
解决问题：
  - alarm 查询 LEFT JOIN + OR 条件无法走索引 → 加 device_id / result_id 索引
  - result 按 device_name + start_time 排序扫描慢 → 加复合索引
  - curve / step 按 result_id 查询无索引
"""
from sqlalchemy import create_engine, text

CONN_STR = "postgresql+pg8000://postgres:6edef2d746f2274cab951a452d5fc13d@10.18.120.240:35432/equipment_mechanism"
engine = create_engine(CONN_STR, echo=False)

INDEXES = [
    # result: 设备结果查询（按设备名 + 时间倒序）
    (
        "idx_result_device_start",
        'CREATE INDEX IF NOT EXISTS idx_result_device_start ON biz.result (device_name, start_time DESC);'
    ),
    # alarm: device_id 直接查询
    (
        "idx_alarm_device_id",
        'CREATE INDEX IF NOT EXISTS idx_alarm_device_id ON biz.alarm (device_id);'
    ),
    # alarm: result_id JOIN 加速
    (
        "idx_alarm_result_id",
        'CREATE INDEX IF NOT EXISTS idx_alarm_result_id ON biz.alarm (result_id);'
    ),
    # curve: 按 result_id 查询
    (
        "idx_curve_result_id",
        'CREATE INDEX IF NOT EXISTS idx_curve_result_id ON biz.curve (result_id);'
    ),
    # step: 按 result_id 查询
    (
        "idx_step_result_id",
        'CREATE INDEX IF NOT EXISTS idx_step_result_id ON biz.step (result_id);'
    ),
    # device_uri: 按 device_id 查询
    (
        "idx_device_uri_device_id",
        'CREATE INDEX IF NOT EXISTS idx_device_uri_device_id ON biz.device_uri (device_id);'
    ),
]

def main():
    with engine.begin() as conn:
        for name, sql in INDEXES:
            try:
                conn.execute(text(sql))
                print(f"[OK] {name}")
            except Exception as e:
                print(f"[FAIL] {name}: {e}")
    print("\nDone.")

if __name__ == "__main__":
    main()
