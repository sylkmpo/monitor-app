# -*- coding: utf-8 -*-
import codecs
import re

with codecs.open(r'd:\suiyuer\Projects\monitor-app\yolov26\ai_server.py', 'r', 'utf-8') as f:
    text = f.read()

# 1. Restore threading and single model instance
text = text.replace('import multiprocessing', '')
text = re.sub(r"model = YOLO\('.*?'\)", "", text) # Remove all model loading
text = re.sub(r"logger\.info\([\"\'](?:姝ｅ湪鍔犺浇|正在加载|采用多进程重构).*?[\"\']\)\s*", "", text)

# Insert global model load
insert_pos = text.find('logger.info("================ AI Server Starting ================")')
if insert_pos != -1:
    insert_str = 'logger.info("================ AI Server Starting ================")\n\n# ====== 深度重构：极省显存与算力的全局单例模型 ======\nlogger.info("🚀 正在全局加载单例 YOLO 模型...")\nmodel = YOLO("yolo26n.pt")\n# 核心突破：多线程全局推理锁，避免 CUDA 上下文争抢爆显存\nai_inference_lock = threading.Lock()\n'
    text = text.replace('logger.info("================ AI Server Starting ================")', insert_str)

# 2. Replace process_video_stream
old_process_pattern = re.compile(r"def process_video_stream\(.*?(?=\ndef start_recording)", re.DOTALL)
new_process_code = """def process_video_stream(cam_id, cam_name, input_source, output_rtsp, stop_event):
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

        last_alert_time = last_person_time = 0 
        event_ongoing = False 
        max_person_count, frame_count = 0, 0
        last_boxes = [] # 用于帧复用机制的检测框缓存

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
            
            person_count = len(last_boxes)
            
            # --- 报警逻辑 ---
            if person_count > 0:
                last_person_time = current_time 
                if not event_ongoing or person_count > max_person_count:
                    event_ongoing = True 
                    if current_time - last_alert_time > 8:
                        last_alert_time = current_time
                        max_person_count = person_count 
                        
                        img_filename = f"alert_{cam_name}_{int(current_time)}.jpg"
                        img_path = os.path.join(SNAPSHOT_DIR, img_filename)
                        
                        snap_frame = frame.copy()
                        for (x1, y1, x2, y2) in last_boxes:
                            cv2.rectangle(snap_frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                        cv2.imwrite(img_path, snap_frame)
                        
                        try:
                            # 此处为了不阻塞后续操作，可以直接忽略超时的警告
                            requests.post("http://127.0.0.1:8000/api/alerts", json={
                                "cam_name": cam_name,
                                "alert_type": f"检测到异常闯入 (当前共有 {person_count} 人)",
                                "image_filename": img_filename
                            }, headers={"Authorization": f"Bearer {}"}, timeout=2)
                        except Exception: pass
            else:
                if event_ongoing and (current_time - last_person_time > 5):
                    event_ongoing, max_person_count = False, 0 

            # ====== 视觉渲染（无论是否推断，都直接渲染历史缓存框）======
            annotated_frame = frame
            for (x1, y1, x2, y2) in last_boxes:
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

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

"""
# Fix the API token string formatting 
new_process_code = new_process_code.replace('Bearer {}', 'Bearer {API_TOKEN}')

text = old_process_pattern.sub(new_process_code, text)

# 3. Fix __main__ block threading
text = text.replace("multiprocessing.freeze_support()", "")
text = text.replace("import multiprocessing", "")
text = text.replace("multiprocessing.Process", "threading.Thread")
text = text.replace("multiprocessing.Event()", "threading.Event()")

with codecs.open(r'd:\suiyuer\Projects\monitor-app\yolov26\ai_server.py', 'w', 'utf-8') as f:
    f.write(text)
print('Deep Refactor Completed!')
