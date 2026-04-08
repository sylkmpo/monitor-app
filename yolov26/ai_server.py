import os
import cv2
import subprocess
import threading
import time
import requests
from ultralytics import YOLO

print("正在加载 YOLO 模型到显卡...")
model = YOLO('yolo26n.pt') 

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT_DIR = os.path.join(BASE_DIR, 'snapshots')
os.makedirs(SNAPSHOT_DIR, exist_ok=True)

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
            print("✅ 身份验证成功：AI 服务已获取企业级 JWT 令牌！")
        else:
            print("❌ AI 登录失败，请检查账号密码或后端状态。")
    except Exception as e:
        print("❌ AI 无法连接到服务器鉴权:", e)

def get_auth_headers():
    """生成带有通行证的请求头"""
    return {"Authorization": f"Bearer {API_TOKEN}"}
# ===============================================================

def report_status(cam_id, status):
    try:
        # 🚨 加上 headers=get_auth_headers()
        requests.put(f"http://127.0.0.1:8000/api/cameras/{cam_id}/status", 
                     json={"status": status}, headers=get_auth_headers(), timeout=2)
    except Exception:
        pass 

def process_video_stream(cam_id, cam_name, input_source, output_rtsp, stop_event):
    while not stop_event.is_set():
        report_status(cam_id, "offline")
        print(f"[{cam_name}] 正在尝试连接摄像头: {input_source}")
        
        if str(input_source).isdigit():
            cap = cv2.VideoCapture(int(input_source), cv2.CAP_DSHOW)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        else:
            cap = cv2.VideoCapture(input_source)
        
        if not cap.isOpened():
            print(f"❌ [{cam_name}] 连接失败，5秒后重试...")
            time.sleep(5)
            continue
            
        report_status(cam_id, "online")
        
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  
        width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30

        command = [
            'ffmpeg', '-y', '-f', 'rawvideo', '-vcodec', 'rawvideo', '-pix_fmt', 'bgr24',
            '-s', f"{width}x{height}", '-r', str(fps), '-i', '-',  
            '-c:v', 'h264_nvenc', '-pix_fmt', 'yuv420p', '-profile:v', 'main',    
            '-preset', 'p2', '-tune', 'ull', '-rc', 'vbr', '-cq', '19',             
            '-bf', '0', '-g', str(fps), '-f', 'rtsp', output_rtsp              
        ]

        process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
        print(f"🚀 [{cam_name}] 推流与AI分析已启动")

        last_alert_time = 0 
        last_person_time = 0 
        event_ongoing = False 

        while cap.isOpened() and not stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                print(f"⚠️ [{cam_name}] 视频流异常中断...")
                break 

            results = model(frame, stream=True, verbose=False, device=0)
            pipe_broken = False
            
            for r in results:
                has_person = False
                for box in r.boxes:
                    if int(box.cls[0]) == 0: 
                        has_person = True
                        break
                
                current_time = time.time()
                
                if has_person:
                    last_person_time = current_time 
                    if not event_ongoing and (current_time - last_alert_time > 10):
                        event_ongoing = True 
                        last_alert_time = current_time
                        
                        timestamp_str = str(int(current_time))
                        img_filename = f"alert_{cam_name}_{timestamp_str}.jpg"
                        img_path = os.path.join(SNAPSHOT_DIR, img_filename)
                        
                        annotated_frame = r.plot() 
                        cv2.imwrite(img_path, annotated_frame)
                        
                        try:
                            # 🚨 加上 headers=get_auth_headers()
                            requests.post("http://127.0.0.1:8000/api/alerts", json={
                                "cam_name": cam_name,
                                "alert_type": "检测到人员闯入",
                                "image_filename": img_filename
                            }, headers=get_auth_headers(), timeout=2)
                            print(f"🚨 [{cam_name}] 新事件触发！抓拍: {img_filename}")
                        except Exception:
                            pass
                else:
                    if event_ongoing and (current_time - last_person_time > 5):
                        event_ongoing = False
                        print(f"✅ [{cam_name}] 人员已离开，重新布防。")

                annotated_frame_for_stream = r.plot()
                try:
                    process.stdin.write(annotated_frame_for_stream.tobytes())
                except Exception:
                    pipe_broken = True
                    break
                    
            if pipe_broken:
                break 

        cap.release()
        if process.stdin: process.stdin.close()
        if process.poll() is None: process.terminate()
        process.wait()
        time.sleep(3) 

def get_cameras_from_api():
    try:
        # 🚨 加上 headers=get_auth_headers()
        res = requests.get('http://127.0.0.1:8000/api/cameras', headers=get_auth_headers(), timeout=2)
        if res.status_code == 200:
            return res.json()
        elif res.status_code == 401:
            # 如果 Token 过期，自动重新登录
            print("⚠️ 令牌失效，尝试重新鉴权...")
            ai_login()
    except Exception:
        pass
    return []

if __name__ == '__main__':
    active_threads = {}
    
    # 🚨 脚本启动的第一步：先登录！
    ai_login()
    
    print("🔄 开始动态监听 API 配置中心...")
    try:
        while True:
            cams = get_cameras_from_api()
            current_ids = [c['id'] for c in cams]

            for cam in cams:
                if cam['id'] not in active_threads:
                    stop_event = threading.Event()
                    output_rtsp = f"rtsp://127.0.0.1:8554/{cam['stream_path']}"
                    t = threading.Thread(target=process_video_stream, args=(cam['id'], cam['name'], cam['input_source'], output_rtsp, stop_event))
                    t.start()
                    active_threads[cam['id']] = (t, stop_event)

            for cam_id in list(active_threads.keys()):
                if cam_id not in current_ids:
                    report_status(cam_id, "offline")
                    thread, stop_event = active_threads[cam_id]
                    stop_event.set()
                    del active_threads[cam_id]

            time.sleep(3) 
            
    except KeyboardInterrupt:
        print("\n⚠️ 收到退出信号，安全关闭所有摄像头...")
        for cam_id, (thread, stop_event) in active_threads.items():
            report_status(cam_id, "offline")
            stop_event.set()
            thread.join()