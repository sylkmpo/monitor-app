import os
os.environ["OPENCV_LOG_LEVEL"] = "OFF" # 彻底静音 OpenCV C++ 层面的所有警告和报错
os.environ["OPENCV_FFMPEG_LOGLEVEL"] = "-8" # 屏蔽底层 FFmpeg 音视频拉流警告 (-8 = AV_LOG_QUIET)
os.environ["OPENCV_VIDEOIO_DEBUG"] = "0"
os.environ["OPENCV_FFMPEG_DEBUG"] = "0"
os.environ["OPENCV_FFMPEG_READ_TIMEOUT"] = "3000"  # 限制读取超时为 3 秒
import cv2
import subprocess
import threading
import time
import requests
import datetime
import sys
from loguru import logger
from ultralytics import YOLO

# 配置企业级日志系统
logger.add("logs/ai_server_{time:%Y-%m-%d}.log", rotation="50 MB", retention="10 days", level="INFO")
logger.info("================ AI Server Starting ================")

logger.info("正在加载 YOLO 模型到显卡...")
model = YOLO('yolo26n.pt') 



BASE_DIR = os.path.dirname(os.path.abspath(__file__))
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
        res = requests.post("http://127.0.0.1:8000/api/login", 
                            data={"username": "ai_worker", "password": "ai_pass666"}, timeout=3)
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
        requests.put(f"http://127.0.0.1:8000/api/cameras/{cam_id}/status", 
                     json={"status": status}, headers=get_auth_headers(), timeout=2)
    except Exception:
        pass 

def process_video_stream(cam_id, cam_name, input_source, output_rtsp, stop_event):
    first_attempt = True
    while not stop_event.is_set():
        report_status(cam_id, "offline")
        if first_attempt:
            logger.info(f"[{cam_name}] 正在尝试连接摄像头: {input_source}")
        
        if str(input_source).isdigit():
            cap = cv2.VideoCapture(int(input_source), cv2.CAP_DSHOW)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        else:
            # ✅ 新增强力拦截器：用 Python 原生 Socket "探路"，直接绕过 OpenCV 的恶心 C++ 底层报错！
            is_offline = False
            if isinstance(input_source, str) and "://" in input_source:
                import urllib.parse, socket
                parsed = urllib.parse.urlparse(input_source)
                host = parsed.hostname
                port = parsed.port or (554 if parsed.scheme == 'rtsp' else 80)
                if host:
                    try:
                        # 仅用 2 秒快速尝试握手，不成功直接丢弃，绝不让 OpenCV 碰这个地址
                        with socket.create_connection((host, port), timeout=2.0):
                            pass
                    except (socket.timeout, ConnectionRefusedError, OSError):
                        is_offline = True
            
            if is_offline:
                # 伪造一个失败的拉流对象，避开真实的 ffmpeg 调用
                class DummyCap:
                    def isOpened(self): return False
                cap = DummyCap()
            else:
                # ✅ 经过探路，确认网络通畅，安全放行给 OpenCV
                try:
                    cap = cv2.VideoCapture(input_source, cv2.CAP_FFMPEG, [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 3000, cv2.CAP_PROP_READ_TIMEOUT_MSEC, 3000])
                except TypeError:
                    # 兼容老版 OpenCV
                    cap = cv2.VideoCapture(input_source, cv2.CAP_FFMPEG)
        
        if not cap.isOpened():
            if first_attempt:
                logger.info(f"❌ [{cam_name}] 连接失败。已转入后台静默秒级重连模式...")
                first_attempt = False
            stop_event.wait(2)  # 每两秒重新拉取，确保第一时间抢占画面
            continue
            
        if not first_attempt:
            logger.info(f"✅ [{cam_name}] 摄像头已恢复在线！")
            first_attempt = True # 下次掉线可以重新提醒一次
            
        report_status(cam_id, "online")
        
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30

        # ✅ 将 GOP (关键帧间隔) 从 1 秒降为 0.25 秒，配合 NVENC 零延迟参数，极大缩短 WebRTC 秒开首帧时间
        gop_size = max(5, fps // 4)
        command = [
            'ffmpeg', '-y', '-f', 'rawvideo', '-vcodec', 'rawvideo', '-pix_fmt', 'bgr24',
            '-s', f"{width}x{height}", '-r', str(fps), '-i', '-',  
            '-c:v', 'h264_nvenc', '-pix_fmt', 'yuv420p', '-profile:v', 'main',    
            '-preset', 'p1', '-tune', 'ull', '-zerolatency', '1', '-delay', '0', '-rc', 'vbr', '-cq', '19',             
            '-bf', '0', '-g', str(gop_size), '-f', 'rtsp', output_rtsp              
        ]

        process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
        logger.info(f"🚀 [{cam_name}] 推流与AI分析已启动")

        last_alert_time = 0 
        last_person_time = 0 
        event_ongoing = False 
        max_person_count = 0  # 🔴 记录当前事件周期内的最大人数

        while cap.isOpened() and not stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                logger.info(f"⚠️ [{cam_name}] 视频流异常中断...")
                break
                
            # 🔴 新增改进：加入 conf=0.5 和 iou=0.45 参数，过滤掉模糊和重叠产生的虚假人数
            results = model(frame, stream=True, verbose=False, device=0, conf=0.5, iou=0.45)
            pipe_broken = False
            
            for r in results:
                person_count = 0
                for box in r.boxes:
                    if int(box.cls[0]) == 0: 
                        person_count += 1
                
                current_time = time.time()
                
                if person_count > 0:
                    last_person_time = current_time 
                    
                    # 💡 核心改良：引入 max_person_count
                    # 只有当是一次“全新的事件” 或者 “画面人数突破了这次事件的历史最高值” 时，才去尝试抓拍
                    if not event_ongoing or person_count > max_person_count:
                        event_ongoing = True 
                        
                        if current_time - last_alert_time > 8:
                            last_alert_time = current_time
                            max_person_count = person_count  # 更新当前事件的最大人数水位标杆
                            
                            timestamp_str = str(int(current_time))
                            img_filename = f"alert_{cam_name}_{timestamp_str}.jpg"
                            img_path = os.path.join(SNAPSHOT_DIR, img_filename)
                            
                            annotated_frame = r.plot() 
                            cv2.imwrite(img_path, annotated_frame)
                            
                            try:
                                # 🚨 加上 headers=get_auth_headers()
                                requests.post("http://127.0.0.1:8000/api/alerts", json={
                                    "cam_name": cam_name,
                                    "alert_type": f"检测到异常闯入 (当前共有 {person_count} 人)",
                                    "image_filename": img_filename
                                }, headers=get_auth_headers(), timeout=2)
                                logger.info(f"🚨 [{cam_name}] 新事件触发！画面人数变为 {person_count}，抓拍: {img_filename}")
                            except Exception:
                                pass
                else:
                    if event_ongoing and (current_time - last_person_time > 5):
                        event_ongoing = False
                        max_person_count = 0 # 事件结束，最高人数清零
                        logger.info(f"✅ [{cam_name}] 人员已全部离开，重新布防。")

                annotated_frame_for_stream = r.plot()
                
                # ====== 🔴 恢复：无损原生画质与高保真比例时间水印 ======
                frame_h, frame_w = annotated_frame_for_stream.shape[:2]
                scale_ratio = max(0.4, frame_w / 1920.0) 
                
                font_scale = 1.0 * scale_ratio
                thickness = max(1, int(round(2.0 * scale_ratio)))
                
                current_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                (text_w, text_h), baseline = cv2.getTextSize(current_time_str, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
                
                padding = int(15 * scale_ratio)
                text_x = int(30 * scale_ratio)
                text_y = int(45 * scale_ratio) + text_h 
                
                x1, y1 = max(0, text_x - padding), max(0, text_y - text_h - padding)
                x2, y2 = min(frame_w, text_x + text_w + padding), min(frame_h, text_y + int(baseline) + padding)
                
                # 仅截取文字区域 (ROI) 将其原位加深，不污染全局画质
                if y2 > y1 and x2 > x1:
                    roi = annotated_frame_for_stream[y1:y2, x1:x2]
                    darkened = cv2.addWeighted(roi, 0.5, roi, 0, 0)
                    annotated_frame_for_stream[y1:y2, x1:x2] = darkened
                
                # 写入纯白抗锯齿时间文字
                cv2.putText(annotated_frame_for_stream, current_time_str, (text_x, text_y), 
                            cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)
                # ====================================================

                try:
                    process.stdin.write(annotated_frame_for_stream.tobytes())
                except Exception:
                    pipe_broken = True
                    break
                    
            if pipe_broken:
                break 

        cap.release()
        if 'process' in locals() and process:
            if process.stdin: 
                try: process.stdin.close()
                except: pass
            if process.poll() is None: 
                process.terminate()
            try: process.wait(timeout=2)
            except: process.kill()
        
        # 🔴 新增：当内部流循环异常断开时，先短暂休眠，避免死循环爆CPU或刷屏
        if not stop_event.is_set():
            logger.info(f"⚠️ [{cam_name}] 视频流异常断开或推流失败，将于 5 秒后尝试重启...")
            stop_event.wait(5)


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
        res = requests.get('http://127.0.0.1:8000/api/cameras', headers=get_auth_headers(), timeout=2)
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
        for cam_id, (t_main, t_rec, stop_event, _) in active_threads.items():
            report_status(cam_id, "offline")
            stop_event.set()
        
        # 仅等待最多 1 秒，若仍卡死则暴力退出结束，系统会自动回收 FFmpeg 进程
        for cam_id, (t_main, t_rec, stop_event, _) in active_threads.items():
            t_main.join(timeout=1.0)
            t_rec.join(timeout=1.0)
            
        logger.info("✅ 监控服务已全部退出！")
        sys.exit(0)
