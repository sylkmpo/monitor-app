好，选方案 B 很稳。这个方向不是盲目堆技术，而是把项目改成一个“后端开发者能讲清楚架构、工程化和业务闭环”的项目。

**目标定位**

把项目升级为：

> 基于 FastAPI + MySQL + Vue3 + FFmpeg/MediaMTX + YOLO 的智能视频监控平台，支持摄像头接入、实时 AI 检测、告警事件、录像索引、权限控制、后台任务、健康检查和容器化部署。

核心改造重点放在后端，让简历看起来像“我设计并实现了一个完整后端系统”，而不是“我写了几个接口”。

**阶段 1：后端结构重构**

目标：把现在的 `api_server.py` 从单文件脚本改成标准后端项目结构。

建议结构：

```text
yolov26/backend/
  app/
    main.py
    core/
      config.py
      security.py
      logging.py
    db/
      session.py
      init_db.py
    models/
      user.py
      camera.py
      alert.py
      recording.py
    schemas/
      user.py
      camera.py
      alert.py
      recording.py
      common.py
    routers/
      auth.py
      cameras.py
      alerts.py
      recordings.py
      health.py
    services/
      auth_service.py
      camera_service.py
      alert_service.py
      recording_service.py
    repositories/
      camera_repo.py
      alert_repo.py
      user_repo.py
    tasks/
      cleanup_task.py
      repair_recording_task.py
```

这一阶段完成后，你简历可以写：

> 对原有单体脚本式后端进行分层重构，拆分 Router、Service、Repository、Schema、Config 等模块，提升代码可维护性和业务扩展能力。

**阶段 2：配置与安全改造**

目标：解决硬编码问题，让项目更像真实后端。

要改：

1. MySQL 用户名、密码、库名放到 `.env`
2. JWT Secret 固定到环境变量，不再每次启动随机生成
3. AI 服务账号密码改成配置项
4. CORS 从 `*` 改成可配置白名单
5. 增加 `.env.example`
6. 敏感配置不提交 Git

示例配置：

```env
APP_NAME=monitor-system
APP_ENV=dev
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=123456
MYSQL_DATABASE=monitor_db
JWT_SECRET_KEY=change-this-in-production
JWT_EXPIRE_MINUTES=1440
AI_WORKER_USERNAME=ai_worker
AI_WORKER_PASSWORD=ai_pass666
```

简历点：

> 基于 Pydantic Settings 实现配置隔离，将数据库连接、JWT 密钥、服务端口等敏感配置从代码中剥离，支持多环境部署。

**阶段 3：数据库模型正规化**

目标：从手写 SQL 建表升级到 ORM + 数据模型。

建议使用：

- `SQLAlchemy`
- `Alembic`
- `PyMySQL` 或 `mysqlclient`

核心表：

1. `users`
   - id
   - username
   - password_hash
   - role
   - created_at
   - updated_at

2. `cameras`
   - id
   - name
   - model
   - input_source
   - stream_path
   - status
   - last_online_at
   - created_at
   - updated_at

3. `alerts`
   - id
   - camera_id
   - alert_type
   - image_filename
   - confidence
   - person_count
   - created_at

4. `recordings`
   - id
   - camera_id
   - filename
   - file_path
   - start_time
   - end_time
   - duration_seconds
   - file_size
   - status

5. `camera_status_logs`，可选
   - id
   - camera_id
   - old_status
   - new_status
   - changed_at

简历点：

> 设计摄像头、告警事件、录像片段、用户权限等核心数据模型，并通过 Alembic 管理数据库迁移，解决原始 SQL 分散和表结构演进困难的问题。

**阶段 4：接口能力增强**

目标：让 API 更像一个完整后端服务。

重点接口：

认证模块：

```text
POST /api/auth/login
GET  /api/auth/me
PUT  /api/users/me/password
```

摄像头模块：

```text
GET    /api/cameras?page=1&page_size=10&status=online
POST   /api/cameras
GET    /api/cameras/{id}
PUT    /api/cameras/{id}
DELETE /api/cameras/{id}
PUT    /api/cameras/{id}/status
```

告警模块：

```text
GET    /api/alerts?camera_id=1&start_time=&end_time=&page=1
POST   /api/alerts
DELETE /api/alerts
GET    /api/alerts/stats
```

录像模块：

```text
GET /api/cameras/{id}/recordings
GET /api/recordings?camera_id=1&date=2026-04-10
```

健康检查：

```text
GET /api/health
GET /api/metrics/summary
```

返回格式统一成：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

简历点：

> 设计 RESTful API，支持分页查询、条件筛选、统一响应结构和异常处理，提升接口一致性和前后端协作效率。

**阶段 5：权限系统增强**

目标：从“登录就能访问”升级为角色权限。

角色建议：

```text
admin      系统管理员，可管理用户、摄像头、告警、录像
operator   运维人员，可管理摄像头和处理告警
viewer     只读用户，只能查看监控和告警
ai_worker  AI 服务账号，只能上报状态和告警
```

权限控制示例：

```text
添加摄像头：admin / operator
删除摄像头：admin
查看告警：admin / operator / viewer
删除告警：admin / operator
AI 上报告警：ai_worker
```

简历点：

> 实现基于 JWT + RBAC 的权限控制体系，区分管理员、运维人员、只读用户和 AI 服务账号，保障内部接口访问安全。

**阶段 6：后台任务与录像治理**

目标：把现在散落在 `ai_server.py` 里的维护逻辑变得可管理。

任务包括：

1. 过期录像清理
2. 异常中断录像修复
3. 录像元数据入库
4. 摄像头离线状态检测
5. 告警图片清理

建议先用：

- FastAPI lifespan 启动后台任务
- 或 APScheduler

暂时不用 Celery，除非后面做方案 C。

简历点：

> 通过后台任务机制实现录像文件自动修复、过期清理和摄像头状态巡检，降低人工维护成本。

**阶段 7：可观测性**

目标：让系统能被监控、能排查问题。

要做：

1. 请求日志
2. 业务日志
3. 错误日志
4. request_id
5. 健康检查接口
6. 服务状态统计接口

例如：

```text
GET /api/health
```

返回：

```json
{
  "status": "ok",
  "database": "ok",
  "storage": "ok",
  "camera_count": 2,
  "online_camera_count": 1
}
```

简历点：

> 增加健康检查、结构化日志和请求链路标识，支持快速定位接口异常、数据库异常和视频服务异常。

**阶段 8：Docker Compose 部署**

目标：让项目能一键启动，简历非常加分。

服务建议：

```text
mysql
backend
frontend
mediamtx
```

最终启动方式：

```bash
docker compose up -d
```

配套文件：

```text
docker-compose.yml
Dockerfile.backend
Dockerfile.frontend
.env.example
```

简历点：

> 使用 Docker Compose 编排 FastAPI、MySQL、MediaMTX 和前端服务，实现本地开发环境一键部署。

**阶段 9：测试补充**

目标：不是追求高覆盖率，而是覆盖关键后端能力。

测试范围：

1. 登录成功/失败
2. Token 校验
3. 摄像头新增、修改、删除
4. 告警创建、查询、删除
5. 权限拦截
6. 健康检查

工具：

```text
pytest
httpx
pytest-asyncio
```

简历点：

> 基于 Pytest 编写接口测试，覆盖认证、权限、摄像头管理和告警管理等核心流程，提升系统回归可靠性。

**阶段 10：README 和简历材料包装**

目标：让面试官一眼看懂项目。

README 要补：

1. 项目简介
2. 技术栈
3. 系统架构图
4. 核心功能
5. 数据库设计
6. 接口文档说明
7. 启动方式
8. 项目亮点
9. 后续优化方向

建议最终简历写法：

> 智能视频监控平台  
> 基于 FastAPI + MySQL + Vue3 + FFmpeg/MediaMTX + YOLO 构建智能监控系统，支持多摄像头接入、实时 AI 人员检测、告警抓拍、录像切片、历史回放和用户权限管理。  
> 负责后端架构设计与核心模块实现，将原有脚本式服务重构为 Router-Service-Repository 分层架构，引入 SQLAlchemy/Alembic 管理数据模型和迁移，基于 JWT + RBAC 实现多角色权限控制。  
> 设计告警事件、录像片段和摄像头状态模型，实现分页筛选、统一响应、异常处理、后台清理任务和健康检查接口，并通过 Docker Compose 完成 MySQL、FastAPI、MediaMTX、前端服务的一键部署。

**推荐执行顺序**

1. 先修乱码和 README，避免项目观感太差。
2. 再拆后端目录，把 `api_server.py` 分层。
3. 接着做 `.env` 配置和 JWT 稳定化。
4. 再引入 ORM 和 Alembic。
5. 然后补权限、分页、统一响应。
6. 最后做后台任务、Docker、测试和简历包装。

我建议真正动手时按这个节奏来：

```text
第 1 天：修乱码、整理 README、后端目录重构
第 2 天：配置外置、JWT、安全模块、统一响应
第 3 天：SQLAlchemy 模型、数据库迁移、Repository 层
第 4 天：摄像头/告警/录像接口增强
第 5 天：RBAC 权限、健康检查、后台任务
第 6 天：Docker Compose、测试、接口文档
第 7 天：最终 README、架构图、简历描述
```

这套做完，你这个项目就可以从“功能演示型项目”升级成“后端工程型项目”。下一步我可以直接从第 1 阶段开始，先把后端改造成标准目录结构。





可以。下面这版计划会围绕“危险行为/风险事件检测”重写，不再把项目定位成简单的人员检测系统，而是升级成 **智能风险事件监控平台**。

**改造目标**

把当前逻辑：

```text
检测到人 -> 告警
```

升级为：

```text
YOLO 检测人/物体 -> 轨迹与区域分析 -> 规则引擎判断危险事件 -> 生成结构化告警 -> 后端统一管理、查询、统计、回放
```

最终项目亮点变成：

> 基于 YOLO + 规则引擎实现禁区入侵、越线、人员聚集、长时间逗留、疑似倒地等风险事件检测，并完成告警闭环、录像回溯和后端工程化治理。

**阶段 1：重新定义业务模型**

先把“告警”从一条简单文本升级成结构化事件。

新增/调整事件类型：

```text
person_detected       人员出现，低级别
intrusion             禁区入侵
line_crossing         越线检测
crowding              人员聚集
loitering             长时间逗留
fall_suspected        疑似倒地
fire_smoke            明火/烟雾，后续扩展
no_helmet             未戴安全帽，后续扩展
```

告警表建议升级字段：

```text
id
camera_id
event_type
event_name
risk_level        low / medium / high / critical
confidence
person_count
snapshot_filename
recording_id
region_name
event_start_time
event_end_time
duration_seconds
status            new / confirmed / ignored / resolved
created_at
```

简历价值：

> 设计结构化风险事件模型，支持事件类型、风险等级、持续时间、关联录像和处理状态管理。

**阶段 2：摄像头规则配置**

每个摄像头应该支持不同检测规则，而不是所有摄像头写死同一套逻辑。

新增规则配置表：

```text
camera_rules
```

字段：

```text
id
camera_id
rule_type          intrusion / line_crossing / crowding / loitering / fall_suspected
enabled
rule_name
risk_level
config_json
created_at
updated_at
```

`config_json` 示例：

禁区入侵：

```json
{
  "region": [[120, 80], [600, 80], [600, 420], [120, 420]],
  "min_duration": 2
}
```

越线检测：

```json
{
  "line": [[300, 100], [300, 600]],
  "direction": "left_to_right"
}
```

聚集检测：

```json
{
  "region": [[0, 0], [1280, 0], [1280, 720], [0, 720]],
  "person_threshold": 5,
  "duration_threshold": 3
}
```

逗留检测：

```json
{
  "region": [[100, 100], [900, 100], [900, 600], [100, 600]],
  "duration_threshold": 30
}
```

简历价值：

> 设计基于 JSON 配置的摄像头规则系统，使不同监控点可动态配置禁区、警戒线、人数阈值和停留时间。

**阶段 3：改造 AI 检测流程**

当前流程是：

```text
读取视频帧
YOLO 检测 person
画框
发现人就告警
推流
```

升级后流程：

```text
读取视频帧
YOLO 检测目标
提取 person boxes
更新目标轨迹
加载摄像头规则
执行风险事件检测
事件去重/冷却
生成抓拍
上报告警
渲染检测结果
推流
```

建议拆成这些模块：

```text
ai/
  model.py              YOLO 模型加载
  frame_reader.py       视频帧读取
  tracker.py            简单目标跟踪
  detectors/
    intrusion.py
    line_crossing.py
    crowding.py
    loitering.py
    fall.py
  event_engine.py       统一事件引擎
  alert_client.py       上报告警到后端
```

简历价值：

> 将 AI 服务从单一人员检测改造成事件检测流水线，拆分模型推理、目标跟踪、规则判断、事件上报等模块。

**阶段 4：目标跟踪能力**

危险行为判断通常不能只看单帧，需要连续帧状态。

先做轻量版，不上复杂模型：

```text
centroid tracking
```

每个人维护：

```text
track_id
bbox
center
first_seen
last_seen
last_region
history_points
```

可支持：

1. 判断是否跨线
2. 判断是否逗留
3. 判断是否持续倒地
4. 判断是否持续在禁区
5. 减少重复告警

后续可以升级：

```text
ByteTrack / DeepSORT
```

但第一版用中心点跟踪就够。

简历价值：

> 实现轻量级目标跟踪机制，维护人员轨迹和停留时间，为越线、逗留、持续入侵等时序事件提供基础。

**阶段 5：实现核心危险事件检测**

建议第一版实现 5 个，难度和展示效果比较均衡。

1. 禁区入侵 `intrusion`

判断逻辑：

```text
人框中心点进入多边形区域
并持续超过 min_duration
触发高风险告警
```

用到：

```text
point in polygon
```

2. 越线检测 `line_crossing`

判断逻辑：

```text
同一 track_id 的中心点从线的一侧移动到另一侧
并符合方向规则
触发告警
```

用到：

```text
cross product 判断点在线的哪一侧
```

3. 人员聚集 `crowding`

判断逻辑：

```text
指定区域内人数 >= threshold
持续超过 duration_threshold
触发告警
```

4. 长时间逗留 `loitering`

判断逻辑：

```text
同一个 track_id 在区域内停留超过 N 秒
触发告警
```

5. 疑似倒地 `fall_suspected`

先做规则版：

```text
人体框 width / height > 1.3
且持续超过 2-3 秒
触发疑似倒地
```

注意：这个只能叫“疑似倒地”，不要简历里说成高精度摔倒识别。

简历价值：

> 基于检测框、轨迹、区域规则和连续帧状态实现禁区入侵、越线、聚集、逗留、疑似倒地等风险事件检测。

**阶段 6：事件去重与冷却机制**

否则同一个事件会疯狂刷告警。

设计事件缓存：

```text
event_key = camera_id + event_type + region_name + track_id
```

规则：

```text
同一事件 30 秒内只告警一次
事件持续期间更新状态，不重复插入
事件结束后记录 end_time
```

字段：

```text
last_alert_time
active_events
cooldown_seconds
```

简历价值：

> 设计事件去重与冷却机制，避免连续帧重复告警，降低告警噪声。

**阶段 7：后端接口扩展**

新增规则管理接口：

```text
GET    /api/cameras/{id}/rules
POST   /api/cameras/{id}/rules
PUT    /api/rules/{id}
DELETE /api/rules/{id}
```

新增风险事件接口：

```text
GET /api/events
GET /api/events/{id}
PUT /api/events/{id}/status
GET /api/events/stats
```

查询参数：

```text
camera_id
event_type
risk_level
status
start_time
end_time
page
page_size
```

统计接口返回：

```json
{
  "total_events": 128,
  "critical_events": 5,
  "high_events": 22,
  "today_events": 14,
  "top_event_types": [
    {"event_type": "intrusion", "count": 45},
    {"event_type": "loitering", "count": 31}
  ]
}
```

简历价值：

> 提供风险事件分页检索、状态流转、类型筛选和统计分析接口，支撑前端告警中心与运营分析。

**阶段 8：前端展示升级**

前端不一定要复杂，但要能展示“危险事件检测”的成果。

建议新增：

1. 规则配置页面
   - 选择摄像头
   - 选择规则类型
   - 配置人数阈值、停留时间
   - 第一版区域坐标可以先用 JSON 输入

2. 告警中心升级
   - 按事件类型筛选
   - 按风险等级筛选
   - 展示事件状态
   - 展示持续时间
   - 展示关联摄像头

3. 实时画面标注
   - 人框
   - 禁区区域
   - 警戒线
   - 事件文字标识

第一版可以先把区域/警戒线画在 AI 推流画面中，不急着做复杂拖拽绘制。

简历价值：

> 实现风险事件可视化展示，支持按摄像头、事件类型、风险等级和处理状态筛选告警。

**阶段 9：录像与事件关联**

让告警不只是截图，还能回溯录像。

做法：

1. 录像片段入库
2. 告警事件关联最近录像
3. 前端点告警可以跳到对应录像片段

简化版逻辑：

```text
事件发生时间 event_start_time
查找同 camera_id 下 start_time <= event_time <= end_time 的录像
绑定 recording_id
```

简历价值：

> 实现风险事件与录像片段关联，支持从告警记录快速回溯事件发生时段的视频。

**阶段 10：测试与评估**

准备几类测试视频：

```text
正常路过
进入禁区
越过警戒线
多人聚集
长时间停留
模拟倒地姿态
```

记录指标：

```text
检测延迟
告警去重效果
误报场景
多路摄像头 CPU 占用
```

README 里可以写：

```text
在 2 路 720p 视频流下，系统可实时完成 YOLO 推理、风险规则判断、抓拍上报与录像切片。
```

不要乱写高精度百分比，除非你真的测过。

**阶段 11：简历最终写法**

可以写成这样：

> 智能风险事件监控平台  
> 基于 FastAPI + MySQL + Vue3 + FFmpeg/MediaMTX + YOLO 构建智能视频监控系统，支持多摄像头接入、实时目标检测、危险事件识别、告警抓拍、录像回溯和权限管理。  
> 负责后端架构与 AI 事件检测流程设计，将原有人员检测升级为规则化风险事件检测引擎，结合 YOLO 检测框、轻量级目标跟踪、多边形禁区、警戒线、人数阈值和连续帧状态，实现禁区入侵、越线、人员聚集、长时间逗留、疑似倒地等事件识别。  
> 设计风险事件、检测规则、录像片段等数据模型，支持事件去重、冷却、分页筛选、状态流转、统计分析和录像关联，提升系统告警准确性与可维护性。

**建议开发顺序**

```text
第 1 步：新增事件类型和风险事件数据模型
第 2 步：新增摄像头规则 camera_rules
第 3 步：重构 AI 服务，拆出 event_engine
第 4 步：实现轻量级目标跟踪
第 5 步：实现禁区入侵
第 6 步：实现越线检测
第 7 步：实现聚集和逗留检测
第 8 步：实现疑似倒地检测
第 9 步：加入事件去重和冷却机制
第 10 步：扩展后端 API
第 11 步：升级前端告警展示
第 12 步：补 README、测试样例和简历描述
```

最小可行版本我建议先做这 3 个：

```text
禁区入侵
越线检测
人员聚集
```

这三个稳定、好展示、实现难度适中，也最适合面试讲。然后再加逗留和疑似倒地。