-- =============================================
-- FDS 设备信息模型 - 初始化脚本
-- 数据库: PostgreSQL
-- 描述: 适用于多种工艺类型（拧紧、焊接、压装等）的统一模型
-- =============================================

CREATE SCHEMA IF NOT EXISTS "biz";

-- 1. 工艺程序/配方表 (Program)
-- 定义特定工艺程序的标准参数和版本
CREATE TABLE IF NOT EXISTS "biz"."program" (
  "id" bigserial PRIMARY KEY,
  "program_id" varchar(64) NOT NULL,    -- PLC/控制器中的程序号
  "version" varchar(16) NOT NULL,       -- 版本控制 (如 'v1.0', '20231001')
  "program_name" varchar(128),
  "craft_type" varchar(64),             -- 工艺类型: TIGHTENING, PRESS, WELDING, GLUING, SPR
  "parameter_type" varchar(64),         -- 参数类型: Final Force, Final Stroke, Cycle time 等
  "device_type" varchar(64),            -- 设备类型/型号
  "target_value" numeric(10,2),
  "upper_limit" numeric(10,2),
  "lower_limit" numeric(10,2),
  "is_active" bool DEFAULT true,
  "create_time" timestamp(6) DEFAULT CURRENT_TIMESTAMP,
  UNIQUE("program_id", "version", "parameter_type")  -- 程序号+版本+参数类型的唯一性
);

COMMENT ON TABLE "biz"."program" IS '工艺标准/配方定义';
COMMENT ON COLUMN "biz"."program"."craft_type" IS '工艺类型 (如 拧紧)';


-- 2. 生产结果主表 (Result)
-- 存储单个操作周期的顶层结果
CREATE TABLE IF NOT EXISTS "biz"."result" (
  "id" bigserial,
  "cyclenumber" varchar(64),            -- 设备生成的唯一周期号
  "device_name" varchar(64),
  "craft_type" varchar(64),             -- 冗余字段，便于不关联查询直接统计
  "system_id" varchar(64) NOT NULL,     -- 逻辑系统/工位 ID
  "bsn" varchar(64),                    -- 零件条码 / 序列号
  "vin" varchar(64),                    -- 车辆识别代码
  "program_id" varchar(64),             -- 外键引用字符串 (冗余)
  "program_ver_id" int8,                -- 关联 program.id
  "result_status" int2 NOT NULL,        -- 1:OK, 0:NOK, 2:Warn
  "status_code" varchar(32),            -- 具体的错误代码 (如有)
  "start_time" timestamp(6) NOT NULL,
  "end_time" timestamp(6) NOT NULL,
  "cycle_time" numeric(10,3),           -- 周期时长 (秒)
  "key_value" numeric(10,2),            -- 关键 KPI (如 最终扭矩, 最大压力)
  "create_time" timestamp(6) DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("id", "start_time")
) PARTITION BY RANGE (start_time);

-- 创建当前月份的默认分区 (示例)
CREATE TABLE IF NOT EXISTS "biz"."result_default" PARTITION OF "biz"."result" DEFAULT;

-- 结果表索引
CREATE INDEX IF NOT EXISTS idx_result_bsn ON "biz"."result" ("bsn", "start_time");
CREATE INDEX IF NOT EXISTS idx_result_vin ON "biz"."result" ("vin", "start_time");
CREATE INDEX IF NOT EXISTS idx_result_craft_time ON "biz"."result" ("craft_type", "start_time");


-- 3. 过程步骤表 (Step)
-- 操作过程的步骤明细
CREATE TABLE IF NOT EXISTS "biz"."step" (
  "id" bigserial PRIMARY KEY,
  "result_id" int8 NOT NULL,            -- 关联 result.id
  "step_index" int4 NOT NULL,           -- 序号
  "step_name" varchar(64),
  "step_result" int2,                   -- 1:OK, 0:NOK, 2:Warn
  "step_value" numeric(10,2),           -- 该步骤的关键值
  "target_value" numeric(10,2),
  "start_time" timestamp(6),
  "end_time" timestamp(6)
);

CREATE INDEX IF NOT EXISTS idx_step_result_id ON "biz"."step" ("result_id");


-- 4. 报警/事件表 (Alarm)
-- 生产过程中的报警或错误
CREATE TABLE IF NOT EXISTS "biz"."alarm" (
  "id" bigserial PRIMARY KEY,
  "result_id" int8 NOT NULL,            -- 关联 result.id (对象级报警)
  "step_id" int8,                       -- 关联 step.id (步骤级报警, 可选)
  "alarm_code" varchar(64),
  "alarm_level" varchar(16),            -- INFO, WARN, ERROR
  "alarm_msg" text,
  "create_time" timestamp(6) DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_alarm_result_id ON "biz"."alarm" ("result_id");
CREATE INDEX IF NOT EXISTS idx_alarm_step_id ON "biz"."alarm" ("step_id");


-- 5. 曲线数据表 (Curve)
-- 存储高频采样数据
CREATE TABLE IF NOT EXISTS "biz"."curve" (
  "id" bigserial PRIMARY KEY,
  "result_id" int8,                     -- 每个结果包含多行曲线(按步骤)
  "step" int4,                          -- 步骤号
  "curve_type" varchar(32),             -- 如: TORQUE_ANGLE, FORCE_DISPLACEMENT
  "start_time" timestamp(6),
  "end_time" timestamp(6),
  "data_points" jsonb,                  -- 存储为 JSON 数组: { "x": [...], "y": [...] }
  "storage_path" varchar(255),          -- 备选: 磁盘/S3 文件路径
  "sample_rate" int4                    -- 采样率 (Hz)
);


-- 6. 扩展属性表 (Extension)
-- 存储主表中无法容纳的特定工艺字段
CREATE TABLE IF NOT EXISTS "biz"."extension" (
  "result_id" int8 PRIMARY KEY,         -- 1:1 关联 result
  "extra_data" jsonb,                   -- 特定工艺参数的键值对
  "operator_id" varchar(64),
  "fixture_id" varchar(64)
);

-- JSONB 索引 (例如: 查找所有高湿度的记录)
CREATE INDEX IF NOT EXISTS idx_extension_data ON "biz"."extension" USING GIN (extra_data);
