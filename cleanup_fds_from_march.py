"""
清理 biz.* 表中 FDS 数据：删除 start_time >= 2026-03-01 的 result 及其关联记录
删除顺序：alarm -> curve -> extension -> step -> result -> (孤立的 program)
"""

import json
from datetime import datetime
from sqlalchemy import text
from etl_core.common.db import create_db_engine

CUTOFF_DATE = '2026-03-16'
CRAFT_TYPE = 'FDS_DEFAULT'
CHECKPOINT_FILE = 'etl_core/checkpoints/fds.json'


def main():
    engine = create_db_engine(pool_size=2, max_overflow=5)

    with engine.begin() as conn:
        # 查找需要删除的 result IDs
        print(f"查询 start_time >= {CUTOFF_DATE} 且 craft_type = '{CRAFT_TYPE}' 的记录...")
        result_ids_rows = conn.execute(text("""
            SELECT id FROM biz.result
            WHERE start_time >= :cutoff AND craft_type = :craft
        """), {"cutoff": CUTOFF_DATE, "craft": CRAFT_TYPE}).fetchall()

        result_ids = [r[0] for r in result_ids_rows]
        print(f"找到 {len(result_ids)} 条 result 记录需要删除")

        if not result_ids:
            print("无需删除，退出。")
            return

        # 分批处理，避免 IN 子句过长
        BATCH = 1000
        total_alarm = total_curve = total_ext = total_step = total_result = 0

        for i in range(0, len(result_ids), BATCH):
            batch = result_ids[i:i + BATCH]
            ids_tuple = tuple(batch)

            # 1. 删除 alarm
            r = conn.execute(text("DELETE FROM biz.alarm WHERE result_id = ANY(:ids)"),
                             {"ids": list(ids_tuple)})
            total_alarm += r.rowcount

            # 2. 删除 curve
            r = conn.execute(text("DELETE FROM biz.curve WHERE result_id = ANY(:ids)"),
                             {"ids": list(ids_tuple)})
            total_curve += r.rowcount

            # 3. 删除 extension
            r = conn.execute(text("DELETE FROM biz.extension WHERE result_id = ANY(:ids)"),
                             {"ids": list(ids_tuple)})
            total_ext += r.rowcount

            # 4. 删除 step
            r = conn.execute(text("DELETE FROM biz.step WHERE result_id = ANY(:ids)"),
                             {"ids": list(ids_tuple)})
            total_step += r.rowcount

            # 5. 删除 result
            r = conn.execute(text("DELETE FROM biz.result WHERE id = ANY(:ids)"),
                             {"ids": list(ids_tuple)})
            total_result += r.rowcount

            print(f"  批次 {i // BATCH + 1}: 已处理 {min(i + BATCH, len(result_ids))}/{len(result_ids)}")

        print(f"\n删除汇总:")
        print(f"  alarm    : {total_alarm}")
        print(f"  curve    : {total_curve}")
        print(f"  extension: {total_ext}")
        print(f"  step     : {total_step}")
        print(f"  result   : {total_result}")

        # 6. 删除孤立的 program（craft_type = FDS_DEFAULT 且没有 result 引用）
        r = conn.execute(text("""
            DELETE FROM biz.program
            WHERE craft_type = :craft
              AND id NOT IN (SELECT DISTINCT program_ver_id FROM biz.result WHERE program_ver_id IS NOT NULL)
        """), {"craft": CRAFT_TYPE})
        print(f"  program  : {r.rowcount} (孤立记录)")

    # 重置 checkpoint
    print(f"\n重置 FDS checkpoint...")
    with open(CHECKPOINT_FILE, 'r') as f:
        cp = json.load(f)

    # 需要回退到 2026-03-01 之前对应的 autoindex
    # 通过查询源表找到该时间点之前的最后一个 autoindex
    with engine.connect() as conn:
        last_idx = conn.execute(text("""
            SELECT MAX(autoindex) FROM origin.bs_fds_v_fds_curves
            WHERE starttime < :cutoff
        """), {"cutoff": CUTOFF_DATE}).scalar()

    if last_idx is not None:
        old_idx = cp.get('last_autoindex')
        cp['last_autoindex'] = last_idx
        cp['last_time'] = datetime.now().isoformat()
        with open(CHECKPOINT_FILE, 'w') as f:
            json.dump(cp, f, indent=2)
        print(f"  checkpoint 已从 {old_idx} 回退到 {last_idx}")
    else:
        print("  无法确定回退位置，checkpoint 未修改，请手动检查")

    print("\n完成。")


if __name__ == '__main__':
    main()
