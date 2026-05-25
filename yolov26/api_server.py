import os
import pymysql
from pymysql.cursors import DictCursor
from dbutils.pooled_db import PooledDB
from loguru import logger
from fastapi import FastAPI, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from datetime import datetime
import uvicorn
from typing import Any, Dict, List, Optional
from repositories.alert_repository import AlertRepository
from repositories.camera_repository import CameraRepository
from repositories.event_repository import EventRepository
from repositories.rule_repository import RuleRepository
from repositories.user_repository import UserRepository
from services.alert_service import AlertService
from services.notification_service import EventNotificationService
from security import (
    create_access_token,
    get_password_hash,
    make_current_user_dependency,
    make_role_dependency,
    verify_password,
)
from settings import BASE_DIR, settings

# 配置企业级日志系统
logger.add("logs/api_server_{time:%Y-%m-%d}.log", rotation="50 MB", retention="10 days", level="INFO")
logger.info("================ API Server Starting ================")

# ================= 配置区 =================
DB_CONFIG = {
    'host': settings.MYSQL_HOST,
    'port': settings.MYSQL_PORT,
    'user': settings.MYSQL_USER,
    'password': settings.MYSQL_PASSWORD,
    'charset': 'utf8mb4',
    'cursorclass': DictCursor,
    'autocommit': True
}
DB_NAME = settings.MYSQL_DATABASE

DEFAULT_ADMIN_USERNAME = settings.DEFAULT_ADMIN_USERNAME
DEFAULT_ADMIN_PASSWORD = settings.DEFAULT_ADMIN_PASSWORD
AI_WORKER_USERNAME = settings.AI_WORKER_USERNAME
AI_WORKER_PASSWORD = settings.AI_WORKER_PASSWORD
ROLE_ADMIN = settings.ROLE_ADMIN
ROLE_OPERATOR = settings.ROLE_OPERATOR
ROLE_VIEWER = settings.ROLE_VIEWER
ROLE_AI_WORKER = settings.ROLE_AI_WORKER
# ==========================================

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

SNAPSHOT_DIR = os.path.join(BASE_DIR, 'snapshots')
os.makedirs(SNAPSHOT_DIR, exist_ok=True)
# 原有的 snapshots
app.mount("/snapshots", StaticFiles(directory=SNAPSHOT_DIR), name="snapshots")

# 新增 records
RECORD_DIR = os.path.join(BASE_DIR, 'records')
os.makedirs(RECORD_DIR, exist_ok=True)
app.mount("/records", StaticFiles(directory=RECORD_DIR), name="records")

# 💡 全局数据库连接池 (解决 PyMySQL 在 FastAPI 下的多线程阻塞问题)
DB_POOL = None

def get_db():
    if DB_POOL is None:
        init_db()
    return DB_POOL.connection()

def init_db():
    global DB_POOL
    logger.info("Initializing database and connection pool...")
    # 1. 优先创建数据库（不用池，直接连）
    conn = pymysql.connect(host=DB_CONFIG['host'], port=DB_CONFIG['port'], 
                           user=DB_CONFIG['user'], password=DB_CONFIG['password'])
    conn.cursor().execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    conn.close()

    # 2. 初始化连接池
    pool_config = DB_CONFIG.copy()
    pool_config['database'] = DB_NAME
    
    DB_POOL = PooledDB(
        creator=pymysql,  # 使用链接数据库的模块
        maxconnections=20, # 连接池允许的最大连接数
        mincached=5,       # 初始化时，链接池中至少创建的空闲的链接
        maxcached=10,      # 链接池中最多闲置的链接
        maxshared=3,       # 链接池中最多共享的链接数量
        blocking=True,     # 连接池中如果没有可用连接后，是否阻塞等待
        maxusage=None,     # 一个链接最多被重复使用的次数
        setsession=[],     # 开始会话前执行的命令列表
        ping=1,            # ping MySQL服务端，检查是否服务可用
        **pool_config
    )
    logger.info("Connection pool created.")

    # 3. 建表逻辑
    conn = get_db()
    with conn.cursor() as cursor:
        cursor.execute('''CREATE TABLE IF NOT EXISTS cameras (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(255) NOT NULL, model VARCHAR(255), input_source VARCHAR(255) NOT NULL, stream_path VARCHAR(255) NOT NULL, status VARCHAR(50) DEFAULT 'offline')''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS alerts (id INT AUTO_INCREMENT PRIMARY KEY, cam_name VARCHAR(255) NOT NULL, alert_type VARCHAR(255) NOT NULL, image_filename VARCHAR(255) NOT NULL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS camera_rules (
                id INT AUTO_INCREMENT PRIMARY KEY,
                camera_id INT NOT NULL,
                rule_type VARCHAR(50) NOT NULL,
                enabled TINYINT(1) DEFAULT 1,
                rule_name VARCHAR(100) NOT NULL,
                risk_level VARCHAR(20) DEFAULT 'medium',
                config_json TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_camera_rules_camera_id (camera_id),
                INDEX idx_camera_rules_type (rule_type)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alert_events (
                id INT AUTO_INCREMENT PRIMARY KEY,
                camera_id INT,
                cam_name VARCHAR(255) NOT NULL,
                event_type VARCHAR(50) NOT NULL,
                event_name VARCHAR(100) NOT NULL,
                risk_level VARCHAR(20) DEFAULT 'medium',
                confidence FLOAT DEFAULT 0,
                person_count INT DEFAULT 0,
                image_filename VARCHAR(255) NOT NULL,
                region_name VARCHAR(100),
                event_start_time DATETIME,
                event_end_time DATETIME,
                duration_seconds FLOAT DEFAULT 0,
                status VARCHAR(20) DEFAULT 'new',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_alert_events_camera_id (camera_id),
                INDEX idx_alert_events_type (event_type),
                INDEX idx_alert_events_status (status),
                INDEX idx_alert_events_created_at (created_at)
            )
        ''')
        
        # 🚨 新增：企业用户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY, 
                username VARCHAR(50) UNIQUE NOT NULL, 
                password_hash VARCHAR(255) NOT NULL, 
                role VARCHAR(20) NOT NULL
            )
        ''')

        default_users = [
            (DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD, ROLE_ADMIN),
            (AI_WORKER_USERNAME, AI_WORKER_PASSWORD, ROLE_AI_WORKER)
        ]
        for username, password, role in default_users:
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
                    (username, get_password_hash(password), role)
                )
                logger.info(f"Default user initialized: {username} ({role})")

    conn.close()

init_db()

user_repository = UserRepository(get_db)
alert_repository = AlertRepository(get_db)
camera_repository = CameraRepository(get_db)
event_repository = EventRepository(get_db)
rule_repository = RuleRepository(get_db)
event_notifier = EventNotificationService()
alert_service = AlertService(alert_repository, SNAPSHOT_DIR, logger)


# Auth dependencies are built from the security module while keeping DB access local to this file.
def load_user_by_username(username: str):
    return user_repository.find_by_username(username)


get_current_user = make_current_user_dependency(load_user_by_username)
require_roles = make_role_dependency(get_current_user)


@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    await event_notifier.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        event_notifier.disconnect(websocket)

# ======= API 路由 =======

# 1. 登录拿 Token 接口
@app.post("/api/login")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = user_repository.find_by_username(form_data.username)
    
    if not user or not verify_password(form_data.password, user['password_hash']):
        raise HTTPException(status_code=400, detail="用户名或密码错误")
    
    access_token = create_access_token(data={"sub": user['username'], "role": user['role']})
    return {"access_token": access_token, "token_type": "bearer", "username": user['username'], "role": user['role']}

@app.get("/api/users/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "username": current_user["username"],
        "role": current_user["role"]
    }

# 数据模型定义
class Camera(BaseModel): 
    input_source: str
    name: str = ""
    model: str = ""

class CameraStatus(BaseModel): 
    status: str

class Alert(BaseModel): 
    cam_name: str
    alert_type: str
    image_filename: str
    camera_id: Optional[int] = None
    event_type: Optional[str] = None
    event_name: Optional[str] = None
    risk_level: Optional[str] = "medium"
    confidence: Optional[float] = 0
    person_count: Optional[int] = 0
    region_name: Optional[str] = None
    event_start_time: Optional[datetime] = None
    event_end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = 0

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class CameraRule(BaseModel):
    rule_type: str
    enabled: bool = True
    rule_name: str = ""
    risk_level: str = "medium"
    config: Dict[str, Any] = Field(default_factory=dict)

class EventStatusUpdate(BaseModel):
    status: str

# 🚨 以下所有业务接口，全部加入 `current_user: dict = Depends(get_current_user)` 进行拦截保护

@app.put("/api/users/me/password")
def change_password(req: ChangePasswordRequest, current_user: dict = Depends(get_current_user)):
    username = current_user['username']
    current_password_hash = user_repository.get_password_hash(username)

    if not current_password_hash or not verify_password(req.old_password, current_password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")

    new_hash = get_password_hash(req.new_password)
    user_repository.update_password_hash(username, new_hash)
    return {"msg": "密码修改成功"}


@app.get("/api/cameras")
def get_cameras(current_user: dict = Depends(require_roles(ROLE_OPERATOR, ROLE_VIEWER, ROLE_AI_WORKER))):
    return camera_repository.list_all()

@app.post("/api/cameras")
def add_camera(cam: Camera, current_user: dict = Depends(require_roles(ROLE_OPERATOR))):
    if camera_repository.input_source_exists(cam.input_source):
        raise HTTPException(status_code=400, detail="该视频源已添加")
    camera_repository.create(cam.name, cam.model, cam.input_source)
    return {"status": "success"}

@app.put("/api/cameras/{cam_id}")
def update_camera(cam_id: int, cam: Camera, current_user: dict = Depends(require_roles(ROLE_OPERATOR))):
    if camera_repository.input_source_exists(cam.input_source, exclude_id=cam_id):
        raise HTTPException(status_code=400, detail="视频源冲突")
    camera_repository.update(cam_id, cam.name, cam.model, cam.input_source)
    return {"status": "success"}

@app.delete("/api/cameras/{cam_id}")
def delete_camera(cam_id: int, current_user: dict = Depends(require_roles())):
    camera_repository.delete(cam_id)
    return {"status": "success"}

@app.put("/api/cameras/{cam_id}/status")
def update_camera_status(cam_id: int, stat: CameraStatus, current_user: dict = Depends(require_roles(ROLE_OPERATOR, ROLE_AI_WORKER))):
    camera_repository.update_status(cam_id, stat.status)
    return {"status": "success"}


@app.get("/api/health")
def health_check():
    db_status = "ok"
    storage_status = "ok"
    camera_count = 0
    online_camera_count = 0
    try:
        camera_summary = camera_repository.count_summary()
        camera_count = camera_summary["total"]
        online_camera_count = camera_summary["online_count"]
    except Exception as e:
        db_status = f"error: {e}"

    for path in (SNAPSHOT_DIR, RECORD_DIR):
        if not os.path.exists(path) or not os.access(path, os.W_OK):
            storage_status = "error"

    return {
        "status": "ok" if db_status == "ok" and storage_status == "ok" else "degraded",
        "database": db_status,
        "storage": storage_status,
        "camera_count": camera_count,
        "online_camera_count": online_camera_count,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

@app.get("/api/metrics/summary")
def metrics_summary(current_user: dict = Depends(require_roles(ROLE_OPERATOR, ROLE_VIEWER))):
    cameras = camera_repository.count_summary()
    active_rules = rule_repository.active_count()
    today_events = event_repository.today_count()
    return {
        "camera_count": cameras["total"],
        "online_camera_count": cameras["online_count"],
        "today_events": today_events or 0,
        "active_rules": active_rules or 0
    }

@app.get("/api/cameras/{cam_id}/rules")
def get_camera_rules(cam_id: int, current_user: dict = Depends(require_roles(ROLE_OPERATOR, ROLE_VIEWER, ROLE_AI_WORKER))):
    return rule_repository.list_by_camera(cam_id)

@app.post("/api/cameras/{cam_id}/rules")
def add_camera_rule(cam_id: int, rule: CameraRule, current_user: dict = Depends(require_roles(ROLE_OPERATOR))):
    if not rule_repository.camera_exists(cam_id):
        raise HTTPException(status_code=404, detail="摄像头不存在")

    rule_id = rule_repository.create(
        camera_id=cam_id,
        rule_type=rule.rule_type,
        enabled=rule.enabled,
        rule_name=rule.rule_name,
        risk_level=rule.risk_level,
        config=rule.config,
    )
    return {"status": "success", "id": rule_id}

@app.put("/api/rules/{rule_id}")
def update_camera_rule(rule_id: int, rule: CameraRule, current_user: dict = Depends(require_roles(ROLE_OPERATOR))):
    updated = rule_repository.update(
        rule_id=rule_id,
        rule_type=rule.rule_type,
        enabled=rule.enabled,
        rule_name=rule.rule_name,
        risk_level=rule.risk_level,
        config=rule.config,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="规则不存在")
    return {"status": "success"}

@app.delete("/api/rules/{rule_id}")
def delete_camera_rule(rule_id: int, current_user: dict = Depends(require_roles(ROLE_OPERATOR))):
    deleted = rule_repository.delete(rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="规则不存在")
    return {"status": "success"}


@app.get("/api/events/stats")
def get_event_stats(current_user: dict = Depends(require_roles(ROLE_OPERATOR, ROLE_VIEWER))):
    return event_repository.stats()

@app.get("/api/events")
def get_events(
    camera_id: Optional[int] = None,
    event_type: Optional[str] = None,
    risk_level: Optional[str] = None,
    status_filter: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(require_roles(ROLE_OPERATOR, ROLE_VIEWER))
):
    return event_repository.list_events(
        camera_id=camera_id,
        event_type=event_type,
        risk_level=risk_level,
        status_filter=status_filter,
        page=page,
        page_size=page_size,
    )

@app.put("/api/events/{event_id}/status")
def update_event_status(event_id: int, req: EventStatusUpdate, current_user: dict = Depends(require_roles(ROLE_OPERATOR))):
    allowed_status = {"new", "confirmed", "ignored", "resolved"}
    if req.status not in allowed_status:
        raise HTTPException(status_code=400, detail="非法事件状态")

    updated = event_repository.update_status(event_id, req.status)
    if not updated:
        raise HTTPException(status_code=404, detail="事件不存在")
    return {"status": "success"}

@app.get("/api/cameras/{cam_id}/records")
def get_camera_records(cam_id: int, request: Request, current_user: dict = Depends(require_roles(ROLE_OPERATOR, ROLE_VIEWER))):
    import urllib.parse
    cam_dir = os.path.join(RECORD_DIR, str(cam_id))
    if not os.path.exists(cam_dir):
        return []

    files = os.listdir(cam_dir)
    # 取消过滤，把包含 _recording.mp4 的切片也一并返回给前端，允许用户看最近录制未完成的片段
    mp4_files = sorted([f for f in files if f.endswith('.mp4')], reverse=True)

    # 动态获取请求的主机名（解决局域网其他设备不能看录像的问题）
    domain = request.url.hostname
    
    return [
        {"filename": f, "url": f"http://{domain}:8000/records/{cam_id}/{urllib.parse.quote(f)}"}
        for f in mp4_files
    ]

@app.post("/api/alerts")
async def add_alert(alert: Alert, current_user: dict = Depends(require_roles(ROLE_OPERATOR, ROLE_AI_WORKER))):
    alert_payload = alert.model_dump() if hasattr(alert, "model_dump") else alert.dict()
    result = alert_service.create_alert(alert_payload)
    await event_notifier.broadcast({
        "type": "risk_event_created",
        "alert_id": result["alert_id"],
        "event_id": result["event_id"],
        "cam_name": alert_payload.get("cam_name"),
        "event_type": alert_payload.get("event_type") or "person_detected",
        "risk_level": alert_payload.get("risk_level") or "medium",
    })
    return {"status": "success", **result}

@app.get("/api/alerts")
def get_alerts(cam_name: str = None, current_user: dict = Depends(require_roles(ROLE_OPERATOR, ROLE_VIEWER))):
    return alert_service.list_alerts(cam_name)


class DeleteAlertsRequest(BaseModel):
    alert_ids: List[int]


@app.delete("/api/alerts")
def delete_alerts(req: DeleteAlertsRequest, current_user: dict = Depends(require_roles(ROLE_OPERATOR))):
    if not req.alert_ids:
        return {"status": "success", "deleted_count": 0}

    deleted_count = alert_service.delete_alerts(req.alert_ids)
    return {"status": "success", "deleted_count": deleted_count}

if __name__ == '__main__':
    # 修复：不能更换 Windows 的底层事件循环（会破坏视频流传输），改用猴子补丁静音报错
    import sys
    if sys.platform == 'win32':
        import asyncio
        from asyncio.proactor_events import _ProactorBasePipeTransport
        # 拦截底层的断开连接抛错，让它静默执行
        def silence_connection_lost(func):
            def wrapper(self, *args, **kwargs):
                try:
                    return func(self, *args, **kwargs)
                except (ConnectionResetError, RuntimeError):
                    pass
            return wrapper
        _ProactorBasePipeTransport._call_connection_lost = silence_connection_lost(_ProactorBasePipeTransport._call_connection_lost)

    logger.info("🚀 企业级 API 服务器 (含JWT鉴权) 启动: http://127.0.0.1:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, access_log=False)
