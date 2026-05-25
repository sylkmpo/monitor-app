import os
os.environ["OPENCV_LOG_LEVEL"] = "OFF" # 彻底静音 OpenCV C++ 层面的所有警告和报错
os.environ["OPENCV_FFMPEG_LOGLEVEL"] = "-8" # 屏蔽底层 FFmpeg 音视频拉流警告 (-8 = AV_LOG_QUIET)
os.environ["OPENCV_VIDEOIO_DEBUG"] = "0"
os.environ["OPENCV_FFMPEG_DEBUG"] = "0"
os.environ["OPENCV_FFMPEG_READ_TIMEOUT"] = "3000"  # 限制读取超时为 3 秒
import cv2
import json
import math
import subprocess
import threading

import time
import requests
import datetime
import sys
from loguru import logger
from ultralytics import YOLO
from settings import BASE_DIR, settings

API_BASE_URL = settings.API_BASE_URL
AI_WORKER_USERNAME = settings.AI_WORKER_USERNAME
AI_WORKER_PASSWORD = settings.AI_WORKER_PASSWORD

# 配置企业级日志系统
logger.add("logs/ai_server_{time:%Y-%m-%d}.log", rotation="50 MB", retention="10 days", level="INFO")
logger.info("================ AI Server Starting ================")

# ====== 深度重构：极省显存与算力的全局单例模型 ======
logger.info("🚀 正在全局加载单例 YOLO 模型...")
model = YOLO("yolo26n.pt")
# 核心突破：多线程全局推理锁，避免 CUDA 上下文争抢爆显存
ai_inference_lock = threading.Lock()





SNAPSHOT_DIR = os.path.join(BASE_DIR, 'snapshots')
os.makedirs(SNAPSHOT_DIR, exist_ok=True)

RECORD_DIR = os.path.join(BASE_DIR, 'records')
os.makedirs(RECORD_DIR, exist_ok=True)

# ================= 🚨 新增：AI 专属安全通行证模块 =================
API_TOKEN = ""

def ai_login():
    """让 AI 服务作为虚拟员工登录后端拿通行证"""
    global API_TOKEN
    try:
        # 使用我们在数据库预留的 ai_worker 账号登录
        res = requests.post(f"{API_BASE_URL}/api/login", 
                            data={"username": AI_WORKER_USERNAME, "password": AI_WORKER_PASSWORD}, timeout=3)
        if res.status_code == 200:
            API_TOKEN = res.json()["access_token"]
            logger.info("✅ 身份验证成功：AI 服务已获取企业级 JWT 令牌！")
        else:
            logger.info("❌ AI 登录失败，请检查账号密码或后端状态。")
    except Exception as e:
        logger.info("❌ AI 无法连接到服务器鉴权:", e)

def get_auth_headers():
    """生成带有通行证的请求头"""
    return {"Authorization": f"Bearer {API_TOKEN}"}

# ================= 🚨 风险事件检测引擎 =================
EVENT_NAMES = {
    "intrusion": "禁区入侵",
    "line_crossing": "越线检测",
    "crowding": "人员聚集",
    "loitering": "长时间逗留",
    "fall_suspected": "疑似倒地"
}

DEFAULT_RULES = [
    {
        "id": "default_crowding",
        "rule_type": "crowding",
        "enabled": True,
        "rule_name": "默认人员聚集检测",
        "risk_level": "medium",
        "config": {"person_threshold": 3, "duration_threshold": 3, "cooldown_seconds": 30}
    },
    {
        "id": "default_fall",
        "rule_type": "fall_suspected",
        "enabled": True,
        "rule_name": "默认疑似倒地检测",
        "risk_level": "high",
        "config": {"aspect_ratio_threshold": 1.3, "duration_threshold": 2, "cooldown_seconds": 30}
    }
]

def center_of_box(box):
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

def box_aspect_ratio(box):
    x1, y1, x2, y2 = box
    width = max(1, x2 - x1)
    height = max(1, y2 - y1)
    return width / height

def point_in_region(point, region):
    if not region:
        return True
    x, y = point
    inside = False
    polygon = [(float(px), float(py)) for px, py in region]
    j = len(polygon) - 1
    for i in range(len(polygon)):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        intersects = ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-9) + xi)
        if intersects:
            inside = not inside
        j = i
    return inside

def side_of_line(point, line):
    (x1, y1), (x2, y2) = line
    return (x2 - x1) * (point[1] - y1) - (y2 - y1) * (point[0] - x1)

def full_frame_region(frame_shape):
    height, width = frame_shape[:2]
    return [[0, 0], [width, 0], [width, height], [0, height]]

def normalize_region(config, frame_shape):
    region = config.get("region")
    if region:
        return region
    return full_frame_region(frame_shape)

def fetch_camera_rules(cam_id):
    try:
        res = requests.get(f"{API_BASE_URL}/api/cameras/{cam_id}/rules", headers=get_auth_headers(), timeout=2)
        if res.status_code == 401:
            ai_login()
            res = requests.get(f"{API_BASE_URL}/api/cameras/{cam_id}/rules", headers=get_auth_headers(), timeout=2)
        if res.status_code == 200:
            rules = [rule for rule in res.json() if rule.get("enabled")]
            return rules if rules else [dict(rule) for rule in DEFAULT_RULES]
    except Exception:
        pass
    return [dict(rule) for rule in DEFAULT_RULES]

class CentroidTracker:
    def __init__(self, max_distance=90, max_lost_seconds=2.0):
        self.max_distance = max_distance
        self.max_lost_seconds = max_lost_seconds
        self.next_id = 1
        self.tracks = {}

    def update(self, boxes, now):
        matched_track_ids = set()
        new_tracks = {}

        for box in boxes:
            center = center_of_box(box)
            best_id = None
            best_distance = None

            for track_id, track in self.tracks.items():
                if track_id in matched_track_ids:
                    continue
                distance = math.dist(center, track["center"])
                if distance <= self.max_distance and (best_distance is None or distance < best_distance):
                    best_id = track_id
                    best_distance = distance

            if best_id is None:
                best_id = self.next_id
                self.next_id += 1
                track = {
                    "id": best_id,
                    "first_seen": now,
                    "history": []
                }
            else:
                track = self.tracks[best_id]

            history = track.get("history", [])
            history.append(center)
            track.update({
                "bbox": box,
                "center": center,
                "last_seen": now,
                "history": history[-20:],
                "aspect_ratio": box_aspect_ratio(box)
            })
            new_tracks[best_id] = track
            matched_track_ids.add(best_id)

        for track_id, track in self.tracks.items():
            if track_id not in matched_track_ids and now - track.get("last_seen", now) <= self.max_lost_seconds:
                new_tracks[track_id] = track

        self.tracks = new_tracks
        return list(self.tracks.values())

class EventEngine:
    def __init__(self, cam_id, cam_name):
        self.cam_id = cam_id
        self.cam_name = cam_name
        self.active_since = {}
        self.last_alert_at = {}
        self.last_line_side = {}
        self.rules = []
        self.last_rule_refresh = 0

    def refresh_rules_if_needed(self, now):
        if now - self.last_rule_refresh < 10 and self.rules:
            return
        self.rules = fetch_camera_rules(self.cam_id)
        self.last_rule_refresh = now

    def _can_emit(self, key, now, cooldown_seconds):
        last_alert = self.last_alert_at.get(key, 0)
        if now - last_alert < cooldown_seconds:
            return False
        self.last_alert_at[key] = now
        return True

    def _duration_ready(self, key, now, threshold):
        if key not in self.active_since:
            self.active_since[key] = now
        return now - self.active_since[key] >= threshold

    def _build_event(self, rule, now, person_count=0, track=None, confidence=0.85, duration=0):
        event_type = rule.get("rule_type")
        config = rule.get("config") or {}
        return {
            "camera_id": self.cam_id,
            "cam_name": self.cam_name,
            "event_type": event_type,
            "event_name": rule.get("rule_name") or EVENT_NAMES.get(event_type, event_type),
            "risk_level": rule.get("risk_level", "medium"),
            "confidence": confidence,
            "person_count": person_count,
            "region_name": config.get("region_name") or rule.get("rule_name"),
            "event_start_time": datetime.datetime.fromtimestamp(now - duration).isoformat(),
            "duration_seconds": round(duration, 2),
            "track": track
        }

    def evaluate(self, tracks, frame_shape, now):
        self.refresh_rules_if_needed(now)
        events = []
        alive_active_keys = set()

        for rule in self.rules:
            if not rule.get("enabled", True):
                continue

            rule_type = rule.get("rule_type")
            rule_id = rule.get("id", rule_type)
            config = rule.get("config") or {}
            cooldown = float(config.get("cooldown_seconds", 30))

            if rule_type == "intrusion":
                region = config.get("region")
                if not region:
                    continue
                min_duration = float(config.get("min_duration", 2))
                for track in tracks:
                    if point_in_region(track["center"], region):
                        key = f"{rule_id}:intrusion:{track['id']}"
                        alive_active_keys.add(key)
                        duration = now - self.active_since.get(key, now)
                        if self._duration_ready(key, now, min_duration) and self._can_emit(key, now, cooldown):
                            events.append(self._build_event(rule, now, 1, track, 0.9, max(duration, min_duration)))

            elif rule_type == "line_crossing":
                line = config.get("line")
                if not line or len(line) != 2:
                    continue
                direction = config.get("direction", "any")
                for track in tracks:
                    side = side_of_line(track["center"], line)
                    side_flag = 1 if side > 0 else -1 if side < 0 else 0
                    side_key = f"{rule_id}:line:{track['id']}"
                    old_side = self.last_line_side.get(side_key)
                    self.last_line_side[side_key] = side_flag
                    if old_side and side_flag and old_side != side_flag:
                        allowed = direction == "any"
                        allowed = allowed or (direction == "positive_to_negative" and old_side > 0 and side_flag < 0)
                        allowed = allowed or (direction == "negative_to_positive" and old_side < 0 and side_flag > 0)
                        if allowed and self._can_emit(side_key, now, cooldown):
                            events.append(self._build_event(rule, now, 1, track, 0.88, 0))

            elif rule_type == "crowding":
                region = normalize_region(config, frame_shape)
                threshold = int(config.get("person_threshold", 3))
                duration_threshold = float(config.get("duration_threshold", 3))
                in_region_tracks = [track for track in tracks if point_in_region(track["center"], region)]
                key = f"{rule_id}:crowding"
                if len(in_region_tracks) >= threshold:
                    alive_active_keys.add(key)
                    duration = now - self.active_since.get(key, now)
                    if self._duration_ready(key, now, duration_threshold) and self._can_emit(key, now, cooldown):
                        events.append(self._build_event(rule, now, len(in_region_tracks), None, 0.86, max(duration, duration_threshold)))

            elif rule_type == "loitering":
                region = config.get("region")
                if not region:
                    continue
                duration_threshold = float(config.get("duration_threshold", 30))
                for track in tracks:
                    if point_in_region(track["center"], region):
                        key = f"{rule_id}:loitering:{track['id']}"
                        alive_active_keys.add(key)
                        duration = now - self.active_since.get(key, now)
                        if self._duration_ready(key, now, duration_threshold) and self._can_emit(key, now, cooldown):
                            events.append(self._build_event(rule, now, 1, track, 0.84, max(duration, duration_threshold)))

            elif rule_type == "fall_suspected":
                ratio_threshold = float(config.get("aspect_ratio_threshold", 1.3))
                duration_threshold = float(config.get("duration_threshold", 2))
                for track in tracks:
                    if track.get("aspect_ratio", 0) >= ratio_threshold:
                        key = f"{rule_id}:fall:{track['id']}"
                        alive_active_keys.add(key)
                        duration = now - self.active_since.get(key, now)
                        if self._duration_ready(key, now, duration_threshold) and self._can_emit(key, now, cooldown):
                            events.append(self._build_event(rule, now, 1, track, 0.78, max(duration, duration_threshold)))

        stale_keys = [key for key in self.active_since if key not in alive_active_keys]
        for key in stale_keys:
            self.active_since.pop(key, None)

        return events

def draw_rule_overlay(frame, rules):
    for rule in rules:
        if not rule.get("enabled", True):
            continue
        config = rule.get("config") or {}
        if rule.get("rule_type") in ("intrusion", "crowding", "loitering"):
            region = config.get("region")
            if region:
                pts = [(int(x), int(y)) for x, y in region]
                color = (0, 165, 255) if rule.get("rule_type") != "intrusion" else (0, 0, 255)
                for idx in range(len(pts)):
                    cv2.line(frame, pts[idx], pts[(idx + 1) % len(pts)], color, 2)
        elif rule.get("rule_type") == "line_crossing":
            line = config.get("line")
            if line and len(line) == 2:
                cv2.line(frame, tuple(map(int, line[0])), tuple(map(int, line[1])), (255, 0, 0), 2)

def report_risk_event(event, frame, boxes):
    current_time = time.time()
    img_filename = f"event_{event['event_type']}_{event['cam_name']}_{int(current_time)}.jpg"
    img_path = os.path.join(SNAPSHOT_DIR, img_filename)

    snap_frame = frame.copy()
    for (x1, y1, x2, y2) in boxes:
        cv2.rectangle(snap_frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
    cv2.putText(snap_frame, event["event_name"], (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2, cv2.LINE_AA)
    cv2.imwrite(img_path, snap_frame)

    payload = {
        "camera_id": event["camera_id"],
        "cam_name": event["cam_name"],
        "alert_type": f"{event['event_name']} (风险等级: {event['risk_level']}, 人数: {event['person_count']})",
        "image_filename": img_filename,
        "event_type": event["event_type"],
        "event_name": event["event_name"],
        "risk_level": event["risk_level"],
        "confidence": event["confidence"],
        "person_count": event["person_count"],
        "region_name": event.get("region_name"),
        "event_start_time": event.get("event_start_time"),
        "duration_seconds": event.get("duration_seconds", 0)
    }

    try:
        requests.post(f"{API_BASE_URL}/api/alerts", json=payload, headers=get_auth_headers(), timeout=2)
        logger.info(f"🚨 [{event['cam_name']}] 上报风险事件: {event['event_name']}")
    except Exception as e:
        logger.info(f"⚠️ [{event['cam_name']}] 风险事件上报失败: {e}")

# ================= 🚨 新增：遗留文件自愈修复模块 =================
def fix_leftover_recording_files():
    """服务启动时，遍历并修复上次意外中断（断电、强杀等）留下的 _recording.mp4 文件残骸"""
    for root, dirs, files in os.walk(RECORD_DIR):
        for f in files:
            if f.endswith('_recording.mp4'):
                old_path = os.path.join(root, f)
                try:
                    # 读取该文件最后写入的时间，作为视频实际录制结束时间
                    mtime = os.path.getmtime(old_path)
                    end_str = datetime.datetime.fromtimestamp(mtime).strftime("%H-%M-%S")
                    start_str = f.replace('_recording.mp4', '')
                    new_path = os.path.join(root, f"{start_str}_到_{end_str}.mp4")
                    
                    # 🔴 关键修复：使用 ffmpeg 重新打包并引入 faststart，解决网页加载缓慢或无法播放问题
                    logger.info(f"🔄 正在快速修复遗留录像元数据 {f} ...")
                    ret = subprocess.run(['ffmpeg', '-y', '-i', old_path, '-c', 'copy', '-movflags', '+faststart', new_path], 
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if ret.returncode == 0 and os.path.exists(new_path):
                        try:
                            os.remove(old_path)
                        except Exception as e:
                            logger.info(f"⚠️ 无法删除旧文件 {old_path}: {e}")
                            time.sleep(1)
                            try:
                                os.remove(old_path)
                            except:
                                pass
                        logger.info(f"🔧 已修复意外中断的录像碎片: {f} -> 闭环为 {os.path.basename(new_path)}")
                    else:
                        try:
                            os.replace(old_path, new_path)
                        except:
                            pass
                except Exception as e:
                    pass
# ===============================================================

def report_status(cam_id, status):
    try:
        # 🚨 加上 headers=get_auth_headers()
        requests.put(f"{API_BASE_URL}/api/cameras/{cam_id}/status", 
                     json={"status": status}, headers=get_auth_headers(), timeout=2)
    except Exception:
        pass 

def process_video_stream(cam_id, cam_name, input_source, output_rtsp, stop_event):
    first_attempt = True
    while not stop_event.is_set():
        report_status(cam_id, "offline")
        if first_attempt:
            logger.info(f"[{cam_name}] 正在尝试连接摄像头: {input_source}")
        
        is_offline = False
        if str(input_source).isdigit():
            cap = cv2.VideoCapture(int(input_source), cv2.CAP_DSHOW)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        else:
            if isinstance(input_source, str) and "://" in input_source:
                import urllib.parse, socket
                parsed = urllib.parse.urlparse(input_source)
                host = parsed.hostname
                port = parsed.port or (554 if parsed.scheme == 'rtsp' else 80)
                if host:
                    try:
                        with socket.create_connection((host, port), timeout=2.0): pass
                    except Exception:
                        is_offline = True
            
            if is_offline:
                class DummyCap:
                    def isOpened(self): return False
                cap = DummyCap()
            else:
                try: cap = cv2.VideoCapture(input_source, cv2.CAP_FFMPEG, [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 3000, cv2.CAP_PROP_READ_TIMEOUT_MSEC, 3000])
                except TypeError: cap = cv2.VideoCapture(input_source, cv2.CAP_FFMPEG)
        
        if not cap.isOpened():
            if first_attempt:
                logger.info(f"❌ [{cam_name}] 连接失败，已转入后台静默重连...")
                first_attempt = False
            stop_event.wait(2)
            continue
            
        if not first_attempt:
            logger.info(f"✅ [{cam_name}] 在线！")
            first_attempt = True
            
        report_status(cam_id, "online")
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  
        width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30

        # ====== 深度重构点 2：破除 NVENC 8路硬性限制 ======
        # 使用 libx264 ultrafast 软编，将 GPU 的编码压力转移给多核 CPU，实现路数突破。
        gop_size = max(5, fps // 4)
        command = [
            'ffmpeg', '-y', '-f', 'rawvideo', '-vcodec', 'rawvideo', '-pix_fmt', 'bgr24',
            '-s', f"{width}x{height}", '-r', str(fps), '-i', '-',  
            '-c:v', 'libx264', '-preset', 'ultrafast', '-tune', 'zerolatency', 
            '-pix_fmt', 'yuv420p', '-delay', '0', '-bf', '0', '-g', str(gop_size), '-f', 'rtsp', output_rtsp              
        ]

        process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
        logger.info(f"🚀 [{cam_name}] 性能突破版推流已启动")

        frame_count = 0
        last_boxes = [] # 用于帧复用机制的检测框缓存
        last_tracks = []
        last_events = []
        tracker = CentroidTracker()
        event_engine = EventEngine(cam_id, cam_name)

        while cap.isOpened() and not stop_event.is_set():
            ret, frame = cap.read()
            if not ret: break
                
            frame_count += 1
            current_time = time.time()
            
            # ====== 深度重构点 3：AI 抽帧锁与追踪复用机制 ======
            # 每 5 帧仅进行 1 次真实推理（节省 80% 算力），期间复用边缘框位置以保持视觉流畅
            if frame_count % 5 == 0:
                with ai_inference_lock:
                    results = model(frame, stream=False, verbose=False, device=0, conf=0.5, iou=0.45)
                
                new_boxes = []
                for r in results:
                    for box in r.boxes:
                        if int(box.cls[0]) == 0:  # 只收集类为人的检测框
                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            new_boxes.append((x1, y1, x2, y2))
                last_boxes = new_boxes
                last_tracks = tracker.update(last_boxes, current_time)

            risk_events = event_engine.evaluate(last_tracks, frame.shape, current_time)
            if risk_events:
                last_events = risk_events
                for event in risk_events:
                    report_risk_event(event, frame, last_boxes)

            # ====== 视觉渲染（无论是否推断，都直接渲染历史缓存框）======
            annotated_frame = frame
            draw_rule_overlay(annotated_frame, event_engine.rules)
            for track in last_tracks:
                x1, y1, x2, y2 = track["bbox"]
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(annotated_frame, f"ID {track['id']}", (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)

            for idx, event in enumerate(last_events[-3:]):
                cv2.putText(annotated_frame, event["event_name"], (30, 85 + idx * 32), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)

            frame_h, frame_w = annotated_frame.shape[:2]
            scale_ratio = max(0.4, frame_w / 1920.0) 
            fs = 1.0 * scale_ratio
            th = max(1, int(round(2.0 * scale_ratio)))
            ct_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            (tw, th_h), baseline = cv2.getTextSize(ct_str, cv2.FONT_HERSHEY_SIMPLEX, fs, th)
            pad, tx, ty = int(15 * scale_ratio), int(30 * scale_ratio), int(45 * scale_ratio) + th_h 
            bx1, by1 = max(0, tx - pad), max(0, ty - th_h - pad)
            bx2, by2 = min(frame_w, tx + tw + pad), min(frame_h, ty + int(baseline) + pad)
            
            if by2 > by1 and bx2 > bx1:
                roi = annotated_frame[by1:by2, bx1:bx2]
                annotated_frame[by1:by2, bx1:bx2] = cv2.addWeighted(roi, 0.5, roi, 0, 0)
                
            cv2.putText(annotated_frame, ct_str, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, fs, (255, 255, 255), th, cv2.LINE_AA)

            try: process.stdin.write(annotated_frame.tobytes())
            except Exception: break 

        cap.release()
        try: process.terminate()
        except: pass
        if not stop_event.is_set(): stop_event.wait(5)


def start_recording(cam_id, rtsp_url, stop_event):
    """旁路录像线程：通过 Python 循环控制，录制带有起止时间命名、长度固定的标准 MP4 文件"""
    cam_record_dir = os.path.join(RECORD_DIR, str(cam_id))
    os.makedirs(cam_record_dir, exist_ok=True)
    
    time.sleep(8)  # 延迟等待 RTSP 主流成功推流后再拉流录制
    
    while not stop_event.is_set():
        # 获取开始时间
        start_time = datetime.datetime.now()
        start_str = start_time.strftime("%Y-%m-%d_%H-%M-%S")
        
        # 正在录制时的临时文件名
        temp_file = os.path.join(cam_record_dir, f"{start_str}_recording.mp4")
        
        cmd = [
            'ffmpeg', '-y', 
            '-rtsp_transport', 'tcp',
            '-timeout', '10000000', 
            '-t', '600', # 强制掐断输入流，保证最长只读 10 分钟 (600 秒)
            '-i', rtsp_url,
            '-c:v', 'copy', 
            '-movflags', 'empty_moov+default_base_moof+frag_keyframe', 
            '-min_frag_duration', '1000000', # 限制最小切片为1秒，避免产生过多微小碎片导致 Chrome 崩溃
            temp_file
        ]
        
        process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        start_ts = time.time()
        # 持续监控录制进程，直到自然结束（10分钟）或被打断
        while process.poll() is None:
            if stop_event.is_set() or (time.time() - start_ts > 610): # 强制：超过 10 分钟 10 秒 ffmpeg 若还装死没退，Python 直接出击杀进程
                try:
                    process.stdin.write(b'q\n')
                    process.stdin.flush()
                    process.wait(timeout=3)
                except Exception:
                    pass
                try:
                    process.terminate()
                    process.kill()
                except Exception:
                    pass
                break
            time.sleep(2)
            
        # 当这段录像结束（或被停止），生成结束时间，并重命名闭环该切片
        end_time = datetime.datetime.now()
        end_str = end_time.strftime("%H-%M-%S")
        final_file = os.path.join(cam_record_dir, f"{start_str}_到_{end_str}.mp4")
        
        if os.path.exists(temp_file):
            logger.info(f"🎬 正在处理和优化录像文件: {os.path.basename(final_file)}...")
            ret = subprocess.run(['ffmpeg', '-y', '-i', temp_file, '-c', 'copy', '-movflags', '+faststart', final_file], 
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # 使用更安全的物理文件清理策略
            if ret.returncode == 0 and os.path.exists(final_file):
                try:
                    os.remove(temp_file)
                except Exception as e:
                    logger.info(f"⚠️ 清理残骸失败: {e}，正在重试强删")
                    time.sleep(1)
                    try:
                        os.remove(temp_file)
                    except:
                        pass
            else:
                try:
                    os.replace(temp_file, final_file) # os.replace 可以在 Windows 覆盖已有文件
                except Exception:
                    pass


def cleanup_old_records():
    """后台静默线程：每天凌晨 0 点扫描 records 目录，强制删除超过 15 天的老旧监控录像"""
    while True:
        # 获取当前时间，计算距离下一个凌晨 0 点的大概秒数
        now = datetime.datetime.now()
        num_days = 1
        # 强制将下一个目标时间定为明天的 00:00:00
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=num_days)
        seconds_to_sleep = (midnight - now).total_seconds()
        
        logger.info(f"🌖 [硬盘维护服务] 下次清理老旧录像将在 {seconds_to_sleep / 3600:.2f} 小时后（凌晨 0 点）执行...")
        time.sleep(seconds_to_sleep)
        
        if os.path.exists(RECORD_DIR):
            logger.info("🕒 凌晨 0 点触发：开始扫描并强清超过 15 天的监控录像...")
            current_time = time.time()
            deleted_count = 0
            for root, dirs, files in os.walk(RECORD_DIR):
                for f in files:
                    if f.endswith('.mp4'):
                        file_path = os.path.join(root, f)
                        # 判断文件最后修改时间是否超过 15 天 (15 * 86400 秒)
                        if os.stat(file_path).st_mtime < current_time - 15 * 86400:
                            try:
                                os.remove(file_path)
                                deleted_count += 1
                                logger.info(f"🗑️ 已强制清理 15 天前的过期录像: {f}")
                            except Exception as e:
                                logger.info(f"⚠️ 无法删除过期文件 {f}: {e}")
            logger.info(f"✅ 硬盘维护巡检结束。本次自动清空了 {deleted_count} 个老旧片段。")

def get_cameras_from_api():
    try:
        # 🚨 加上 headers=get_auth_headers()
        res = requests.get(f"{API_BASE_URL}/api/cameras", headers=get_auth_headers(), timeout=2)
        if res.status_code == 200:
            return res.json()
        elif res.status_code == 401:
            # 如果 Token 过期，自动重新登录
            logger.info("⚠️ 令牌失效，尝试重新鉴权...")
            ai_login()
    except Exception:
        pass
    return []


if __name__ == '__main__':
    
    active_threads = {}
    ai_login()
    
    # 启动前自愈修复之前的意外中断遗留视频
    fix_leftover_recording_files()

    # 开启后台清理线程 (自动清理15天前的录像)
    threading.Thread(target=cleanup_old_records, daemon=True).start()

    logger.info("🔄 开始动态监听 API 配置中心...")
    try:
        while True:
            cams = get_cameras_from_api()
            current_ids = [c['id'] for c in cams]

            for cam in cams:
                cam_id = cam['id']
                
                # 🔴 新增：监测流地址和设备名称是否在后台被修改了，如果被修改立刻中断旧连接
                if cam_id in active_threads:
                    t_main, t_rec, old_stop_event, old_source, old_name = active_threads[cam_id]
                    if old_source != cam['input_source'] or old_name != cam['name']:
                        logger.info(f"🔄 检测到 [{old_name}] 配置发生修改，正在重启推流应用最新配置...")
                        report_status(cam_id, "offline")
                        old_stop_event.set()
                        t_main.join(timeout=2)
                        t_rec.join(timeout=2)
                        del active_threads[cam_id]

                if cam_id not in active_threads:
                    stop_event = threading.Event()
                    output_rtsp = f"rtsp://127.0.0.1:8554/{cam['stream_path']}"

                    # 启动 AI 分析推流主线程 (加 daemon=True 支持快速强杀)
                    t_main = threading.Thread(target=process_video_stream,
                                              args=(cam_id, cam['name'], cam['input_source'], output_rtsp, stop_event),
                                              daemon=True)
                    t_main.start()

                    # 启动录制旁路线程 (加 daemon=True 支持快速强杀)
                    t_rec = threading.Thread(target=start_recording, args=(cam_id, output_rtsp, stop_event), daemon=True)
                    t_rec.start()

                    # 将 input_source 和 name 也记录下来，用于后续的修改比对
                    active_threads[cam_id] = (t_main, t_rec, stop_event, cam['input_source'], cam['name'])

            for cam_id in list(active_threads.keys()):
                if cam_id not in current_ids:
                    report_status(cam_id, "offline")
                    t_main, t_rec, stop_event, _, _ = active_threads[cam_id]  # 🔴 修复解包错误，对应 5 个参数
                    stop_event.set()
                    t_main.join()
                    t_rec.join()
                    del active_threads[cam_id]

            time.sleep(3)

    except KeyboardInterrupt:
        logger.info("\n⚠️ 收到退出信号，正在快速强杀所有连线...")
        for cam_id, (t_main, t_rec, stop_event, _, _) in active_threads.items():
            report_status(cam_id, "offline")
            stop_event.set()
        
        # 仅等待最多 1 秒，若仍卡死则暴力退出结束，系统会自动回收 FFmpeg 进程
        for cam_id, (t_main, t_rec, stop_event, _, _) in active_threads.items():
            t_main.join(timeout=1.0)
            t_rec.join(timeout=1.0)
            
        logger.info("✅ 监控服务已全部退出！")
        sys.exit(0)
