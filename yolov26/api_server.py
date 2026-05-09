import os
import time
import json
import pymysql
from pymysql.cursors import DictCursor
from dbutils.pooled_db import PooledDB
from loguru import logger
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import uvicorn
from typing import Any, Dict, List, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)

def load_env_file(path):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

load_env_file(os.path.join(PROJECT_DIR, ".env"))
load_env_file(os.path.join(BASE_DIR, ".env"))

def env_int(key, default):
    try:
        return int(os.getenv(key, default))
    except (TypeError, ValueError):
        return default

# 配置企业级日志系统
logger.add("logs/api_server_{time:%Y-%m-%d}.log", rotation="50 MB", retention="10 days", level="INFO")
logger.info("================ API Server Starting ================")

# ================= 配置区 =================
DB_CONFIG = {
    'host': os.getenv('MYSQL_HOST', '127.0.0.1'),
    'port': env_int('MYSQL_PORT', 3306),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', '123456'),
    'charset': 'utf8mb4',
    'cursorclass': DictCursor,
    'autocommit': True
}
DB_NAME = os.getenv('MYSQL_DATABASE', 'monitor_db')

SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'monitor-app-dev-secret-key-change-me')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = env_int('JWT_EXPIRE_MINUTES', 60 * 24)
DEFAULT_ADMIN_USERNAME = os.getenv('DEFAULT_ADMIN_USERNAME', 'admin')
DEFAULT_ADMIN_PASSWORD = os.getenv('DEFAULT_ADMIN_PASSWORD', 'admin123456')
AI_WORKER_USERNAME = os.getenv('AI_WORKER_USERNAME', 'ai_worker')
AI_WORKER_PASSWORD = os.getenv('AI_WORKER_PASSWORD', 'ai_pass666')
CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')
# ==========================================

app = FastAPI(title=os.getenv('APP_NAME', 'monitor-system'))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if CORS_ORIGINS == "*" else [origin.strip() for origin in CORS_ORIGINS.split(",") if origin.strip()],
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

# ======= 🛡️ 密码加密与 JWT 验证基础 =======
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

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
            (DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD, 'admin'),
            (AI_WORKER_USERNAME, AI_WORKER_PASSWORD, 'ai_worker')
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

# ======= 🚨 依赖注入：检查令牌的“保安” =======
def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的认证凭据", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None: raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    conn = get_db()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
    conn.close()
    if user is None: raise credentials_exception
    return user

# ======= API 路由 =======

# 1. 登录拿 Token 接口
@app.post("/api/login")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = get_db()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE username = %s", (form_data.username,))
        user = cursor.fetchone()
    conn.close()
    
    if not user or not verify_password(form_data.password, user['password_hash']):
        raise HTTPException(status_code=400, detail="用户名或密码错误")
    
    access_token = create_access_token(data={"sub": user['username'], "role": user['role']})
    return {"access_token": access_token, "token_type": "bearer", "username": user['username'], "role": user['role']}

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
    conn = get_db()
    with conn.cursor() as cursor:
        cursor.execute("SELECT password_hash FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
    
    if not user or not verify_password(req.old_password, user['password_hash']):
        conn.close()
        raise HTTPException(status_code=400, detail="原密码错误")
        
    new_hash = get_password_hash(req.new_password)
    with conn.cursor() as cursor:
        cursor.execute("UPDATE users SET password_hash = %s WHERE username = %s", (new_hash, username))
        conn.commit()
    conn.close()
    return {"msg": "密码修改成功"}

@app.get("/api/cameras")
def get_cameras(current_user: dict = Depends(get_current_user)):
    conn = get_db(); cursor = conn.cursor(); cursor.execute("SELECT * FROM cameras"); cams = cursor.fetchall(); conn.close()
    return cams

@app.post("/api/cameras")
def add_camera(cam: Camera, current_user: dict = Depends(get_current_user)):
    conn = get_db(); cursor = conn.cursor()
    cursor.execute("SELECT id FROM cameras WHERE input_source = %s", (cam.input_source,))
    if cursor.fetchone(): raise HTTPException(status_code=400, detail="该视频源已添加")
    auto_stream_path = f"cam_{int(time.time())}"
    final_name = cam.name.strip() if cam.name.strip() else f"未命名_{auto_stream_path[-4:]}"
    cursor.execute("INSERT INTO cameras (name, model, input_source, stream_path) VALUES (%s, %s, %s, %s)", (final_name, cam.model, cam.input_source, auto_stream_path)); conn.commit(); conn.close()
    return {"status": "success"}

@app.put("/api/cameras/{cam_id}")
def update_camera(cam_id: int, cam: Camera, current_user: dict = Depends(get_current_user)):
    conn = get_db(); cursor = conn.cursor()
    
    # 检查流地址冲突
    cursor.execute("SELECT id FROM cameras WHERE input_source = %s AND id != %s", (cam.input_source, cam_id))
    if cursor.fetchone(): raise HTTPException(status_code=400, detail="冲突")
    
    # 🚨 取出修改前的老名字
    cursor.execute("SELECT name FROM cameras WHERE id = %s", (cam_id,))
    old_cam = cursor.fetchone()
    old_name = old_cam['name'] if old_cam else None
    
    # 执行设摄像头的更新
    cursor.execute("UPDATE cameras SET name=%s, model=%s, input_source=%s WHERE id=%s", (cam.name, cam.model, cam.input_source, cam_id))
    
    # 🚨 同步把历史告警库中，这个老名字全部替换为新名字！
    if old_name and old_name != cam.name:
        cursor.execute("UPDATE alerts SET cam_name=%s WHERE cam_name=%s", (cam.name, old_name))
        
    conn.commit(); conn.close()
    return {"status": "success"}

@app.delete("/api/cameras/{cam_id}")
def delete_camera(cam_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_db(); cursor = conn.cursor(); cursor.execute("DELETE FROM cameras WHERE id = %s", (cam_id,)); conn.commit(); conn.close()
    return {"status": "success"}

@app.put("/api/cameras/{cam_id}/status")
def update_camera_status(cam_id: int, stat: CameraStatus, current_user: dict = Depends(get_current_user)):
    conn = get_db(); cursor = conn.cursor(); cursor.execute("UPDATE cameras SET status=%s WHERE id=%s", (stat.status, cam_id)); conn.commit(); conn.close()
    return {"status": "success"}

@app.get("/api/health")
def health_check():
    db_status = "ok"
    storage_status = "ok"
    camera_count = 0
    online_camera_count = 0
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS total, SUM(status = 'online') AS online_count FROM cameras")
        row = cursor.fetchone()
        camera_count = row["total"] or 0
        online_camera_count = row["online_count"] or 0
        conn.close()
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
def metrics_summary(current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) AS total, SUM(status = 'online') AS online_count FROM cameras")
    cameras = cursor.fetchone()
    cursor.execute("SELECT COUNT(*) AS total FROM alert_events WHERE DATE(created_at) = CURDATE()")
    today_events = cursor.fetchone()["total"]
    cursor.execute("SELECT COUNT(*) AS total FROM camera_rules WHERE enabled = 1")
    active_rules = cursor.fetchone()["total"]
    conn.close()
    return {
        "camera_count": cameras["total"] or 0,
        "online_camera_count": cameras["online_count"] or 0,
        "today_events": today_events or 0,
        "active_rules": active_rules or 0
    }

def normalize_rule(row):
    if not row:
        return row
    try:
        config = json.loads(row.get("config_json") or "{}")
    except Exception:
        config = {}
    row["enabled"] = bool(row.get("enabled"))
    row["config"] = config
    row.pop("config_json", None)
    for field in ("created_at", "updated_at"):
        if row.get(field):
            row[field] = row[field].strftime("%Y-%m-%d %H:%M:%S")
    return row

@app.get("/api/cameras/{cam_id}/rules")
def get_camera_rules(cam_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM camera_rules WHERE camera_id = %s ORDER BY id DESC", (cam_id,))
    rules = [normalize_rule(rule) for rule in cursor.fetchall()]
    conn.close()
    return rules

@app.post("/api/cameras/{cam_id}/rules")
def add_camera_rule(cam_id: int, rule: CameraRule, current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM cameras WHERE id = %s", (cam_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="摄像头不存在")

    rule_name = rule.rule_name.strip() if rule.rule_name.strip() else rule.rule_type
    cursor.execute(
        """
        INSERT INTO camera_rules (camera_id, rule_type, enabled, rule_name, risk_level, config_json)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (cam_id, rule.rule_type, int(rule.enabled), rule_name, rule.risk_level, json.dumps(rule.config, ensure_ascii=False))
    )
    conn.commit()
    rule_id = cursor.lastrowid
    conn.close()
    return {"status": "success", "id": rule_id}

@app.put("/api/rules/{rule_id}")
def update_camera_rule(rule_id: int, rule: CameraRule, current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    rule_name = rule.rule_name.strip() if rule.rule_name.strip() else rule.rule_type
    cursor.execute(
        """
        UPDATE camera_rules
        SET rule_type=%s, enabled=%s, rule_name=%s, risk_level=%s, config_json=%s
        WHERE id=%s
        """,
        (rule.rule_type, int(rule.enabled), rule_name, rule.risk_level, json.dumps(rule.config, ensure_ascii=False), rule_id)
    )
    conn.commit()
    updated = cursor.rowcount
    conn.close()
    if not updated:
        raise HTTPException(status_code=404, detail="规则不存在")
    return {"status": "success"}

@app.delete("/api/rules/{rule_id}")
def delete_camera_rule(rule_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM camera_rules WHERE id = %s", (rule_id,))
    conn.commit()
    deleted = cursor.rowcount
    conn.close()
    if not deleted:
        raise HTTPException(status_code=404, detail="规则不存在")
    return {"status": "success"}

@app.get("/api/events/stats")
def get_event_stats(current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) AS total_events FROM alert_events")
    total = cursor.fetchone()["total_events"]
    cursor.execute("SELECT COUNT(*) AS today_events FROM alert_events WHERE DATE(created_at) = CURDATE()")
    today = cursor.fetchone()["today_events"]
    cursor.execute("SELECT risk_level, COUNT(*) AS count FROM alert_events GROUP BY risk_level")
    risk_counts = {row["risk_level"]: row["count"] for row in cursor.fetchall()}
    cursor.execute("SELECT event_type, COUNT(*) AS count FROM alert_events GROUP BY event_type ORDER BY count DESC LIMIT 10")
    top_event_types = cursor.fetchall()
    conn.close()
    return {
        "total_events": total,
        "today_events": today,
        "critical_events": risk_counts.get("critical", 0),
        "high_events": risk_counts.get("high", 0),
        "risk_counts": risk_counts,
        "top_event_types": top_event_types
    }

@app.get("/api/events")
def get_events(
    camera_id: Optional[int] = None,
    event_type: Optional[str] = None,
    risk_level: Optional[str] = None,
    status_filter: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(get_current_user)
):
    page = max(page, 1)
    page_size = max(1, min(page_size, 100))
    conditions = []
    params = []
    if camera_id:
        conditions.append("camera_id = %s")
        params.append(camera_id)
    if event_type:
        conditions.append("event_type = %s")
        params.append(event_type)
    if risk_level:
        conditions.append("risk_level = %s")
        params.append(risk_level)
    if status_filter:
        conditions.append("status = %s")
        params.append(status_filter)

    where_sql = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    offset = (page - 1) * page_size
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) AS total FROM alert_events{where_sql}", tuple(params))
    total = cursor.fetchone()["total"]
    cursor.execute(
        f"SELECT * FROM alert_events{where_sql} ORDER BY created_at DESC LIMIT %s OFFSET %s",
        tuple(params + [page_size, offset])
    )
    rows = cursor.fetchall()
    conn.close()
    for row in rows:
        for field in ("event_start_time", "event_end_time", "created_at"):
            if row.get(field):
                row[field] = row[field].strftime("%Y-%m-%d %H:%M:%S")
    return {"total": total, "page": page, "page_size": page_size, "items": rows}

@app.put("/api/events/{event_id}/status")
def update_event_status(event_id: int, req: EventStatusUpdate, current_user: dict = Depends(get_current_user)):
    allowed_status = {"new", "confirmed", "ignored", "resolved"}
    if req.status not in allowed_status:
        raise HTTPException(status_code=400, detail="非法事件状态")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE alert_events SET status=%s WHERE id=%s", (req.status, event_id))
    conn.commit()
    updated = cursor.rowcount
    conn.close()
    if not updated:
        raise HTTPException(status_code=404, detail="事件不存在")
    return {"status": "success"}


from fastapi import Request

@app.get("/api/cameras/{cam_id}/records")
def get_camera_records(cam_id: int, request: Request, current_user: dict = Depends(get_current_user)):
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
def add_alert(alert: Alert, current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO alerts (cam_name, alert_type, image_filename) VALUES (%s, %s, %s)", (alert.cam_name, alert.alert_type, alert.image_filename))
    alert_id = cursor.lastrowid

    event_type = alert.event_type or "person_detected"
    event_name = alert.event_name or alert.alert_type
    camera_id = alert.camera_id
    if camera_id is None:
        cursor.execute("SELECT id FROM cameras WHERE name = %s LIMIT 1", (alert.cam_name,))
        camera = cursor.fetchone()
        camera_id = camera["id"] if camera else None

    cursor.execute(
        """
        INSERT INTO alert_events (
            camera_id, cam_name, event_type, event_name, risk_level, confidence,
            person_count, image_filename, region_name, event_start_time,
            event_end_time, duration_seconds
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            camera_id,
            alert.cam_name,
            event_type,
            event_name,
            alert.risk_level or "medium",
            alert.confidence or 0,
            alert.person_count or 0,
            alert.image_filename,
            alert.region_name,
            alert.event_start_time,
            alert.event_end_time,
            alert.duration_seconds or 0
        )
    )
    event_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"status": "success", "alert_id": alert_id, "event_id": event_id}

@app.get("/api/alerts")
def get_alerts(cam_name: str = None, current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    query = "SELECT * FROM alerts"
    conditions = []
    params = []
    
    if cam_name:
        conditions.append("cam_name = %s")
        params.append(cam_name)
        
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
        
    query += " ORDER BY timestamp DESC LIMIT 100"
    
    cursor.execute(query, tuple(params))
    alerts = cursor.fetchall()
    for alert in alerts: 
        alert['timestamp'] = alert['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
    conn.close()
    return alerts


class DeleteAlertsRequest(BaseModel):
    alert_ids: List[int]


@app.delete("/api/alerts")
def delete_alerts(req: DeleteAlertsRequest, current_user: dict = Depends(get_current_user)):
    if not req.alert_ids:
        return {"status": "success"}

    conn = get_db()
    cursor = conn.cursor()

    # 防止 SQL 注入，构造格式化字符串
    format_strings = ','.join(['%s'] * len(req.alert_ids))

    # 1. 先查出所有要删除的文件名，用于删除硬盘上的图片
    cursor.execute(f"SELECT image_filename FROM alerts WHERE id IN ({format_strings})", tuple(req.alert_ids))
    alerts_to_delete = cursor.fetchall()

    for alert in alerts_to_delete:
        file_path = os.path.join(SNAPSHOT_DIR, alert['image_filename'])
        if os.path.exists(file_path):
            try:
                os.remove(file_path)  # 删除物理图片
            except Exception as e:
                pass

    # 2. 从数据库删除记录
    cursor.execute(f"DELETE FROM alerts WHERE id IN ({format_strings})", tuple(req.alert_ids))
    conn.commit()
    conn.close()

    return {"status": "success", "deleted_count": len(req.alert_ids)}


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
