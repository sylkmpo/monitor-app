import os
import time
import pymysql
from pymysql.cursors import DictCursor
from dbutils.pooled_db import PooledDB
from loguru import logger
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import uvicorn
from typing import List

# 配置企业级日志系统
logger.add("logs/api_server_{time:%Y-%m-%d}.log", rotation="50 MB", retention="10 days", level="INFO")
logger.info("================ API Server Starting ================")

# ================= 配置区 =================
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': '123456',  # 你的数据库密码
    'charset': 'utf8mb4',
    'cursorclass': DictCursor,
    'autocommit': True
}
DB_NAME = 'monitor_db'

# 🚨 每次服务端重启强制刷新 Token 密钥，使得所有过去下发的会话立即过期，要求前端重新登录
import secrets
SECRET_KEY = secrets.token_hex(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # Token 过期时间: 1天
# ==========================================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
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
        
        # 🚨 新增：企业用户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY, 
                username VARCHAR(50) UNIQUE NOT NULL, 
                password_hash VARCHAR(255) NOT NULL, 
                role VARCHAR(20) NOT NULL
            )
        ''')

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

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

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
    conn = get_db(); cursor = conn.cursor(); cursor.execute("INSERT INTO alerts (cam_name, alert_type, image_filename) VALUES (%s, %s, %s)", (alert.cam_name, alert.alert_type, alert.image_filename)); conn.commit(); conn.close()
    return {"status": "success"}

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