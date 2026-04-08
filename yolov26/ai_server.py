import cv2
import subprocess
import threading
import time
from ultralytics import YOLO

print("正在加载 YOLO 模型到显卡...")
model = YOLO('yolo26n.pt') 

stop_event = threading.Event()

def process_video_stream(cam_name, input_source, output_rtsp):
    print(f"[{cam_name}] 正在连接摄像头...")
    
    # 🚀 核心改动 1：智能判断是 USB 还是 网络流
    if isinstance(input_source, int):
        # 如果传入的是数字 0, 1, 2，说明是本地 USB 摄像头
        # cv2.CAP_DSHOW 是 Windows 系统下读取高画质 USB 摄像头的底层接口
        cap = cv2.VideoCapture(input_source, cv2.CAP_DSHOW)
        
        # 强制将 USB 摄像头分辨率拉满！(假设你的摄像头支持 1080P)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    else:
        # 如果是 RTSP 网址，按网络流处理
        cap = cv2.VideoCapture(input_source)
    
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    if fps == 0: fps = 30 # USB 摄像头默认按 30 帧算

    print(f"[{cam_name}] 成功获取分辨率: {width}x{height}, FPS: {fps}")
    
    command = [
        'ffmpeg',
        '-y',
        '-f', 'rawvideo',
        '-vcodec', 'rawvideo',
        '-pix_fmt', 'bgr24',
        '-s', f"{width}x{height}",
        '-r', str(fps),
        '-i', '-',  
        '-c:v', 'h264_nvenc',    
        '-pix_fmt', 'yuv420p',   
        '-profile:v', 'main',    
        '-preset', 'p2',         
        '-tune', 'ull',          
        '-rc', 'vbr',            
        '-cq', '19',             
        '-bf', '0',              
        '-g', str(fps),          
        '-f', 'rtsp',
        output_rtsp              
    ]

    # 🌟 绝杀 2：暂时删掉 stderr=subprocess.DEVNULL，如果显卡不支持 nvenc 我们能立刻看到红字报错！
    process = subprocess.Popen(command, stdin=subprocess.PIPE)

    # process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    print(f"🚀 [{cam_name}] GPU AI 推流已启动: {output_rtsp}")

    while cap.isOpened() and not stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            print(f"[{cam_name}] 视频流断开！")
            break

        results = model(frame, stream=True, verbose=False, device=0)
        
        pipe_broken = False
        for r in results:
            annotated_frame = r.plot()
            try:
                process.stdin.write(annotated_frame.tobytes())
            except Exception:
                pipe_broken = True
                break
        
        if pipe_broken:
            break

    print(f"[{cam_name}] 正在清理资源...")
    cap.release()
    if process.stdin:
        try:
            process.stdin.close()
        except:
            pass
    if process.poll() is None:
        process.terminate()
    process.wait()
    print(f"[{cam_name}] 任务已安全结束")


if __name__ == '__main__':
    # ================= 核心配置区 =================
    CAM1_IN = 0  
    CAM1_OUT = "rtsp://127.0.0.1:8554/ai_cam1"

    thread1 = threading.Thread(target=process_video_stream, args=("USB监控", CAM1_IN, CAM1_OUT))
    thread1.start()

    CAM2_IN = "rtsp://192.168.237.170:8554/camera1"
    CAM2_OUT = "rtsp://127.0.0.1:8554/ai_cam2"

    thread2 = threading.Thread(target=process_video_stream, args=("其他", CAM2_IN, CAM2_OUT))
    thread2.start()

    # 👇 把这里的注释去掉，恢复优雅退出功能 👇
    try:
        while thread1.is_alive()&thread2.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⚠️ 接收到手动退出信号 (Ctrl+C)！正在安全停机...")
        stop_event.set()
    
    thread1.join()
    thread2.join()
    print("✅ 系统已完全安全关闭。")