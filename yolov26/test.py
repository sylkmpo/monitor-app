import cv2

def test_cameras():
    print("正在扫描电脑上的 USB 摄像头...")
    for i in range(5):  # 扫描 0 到 4 号设备
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            print(f"✅ 成功找到摄像头，索引号为: {i}")
            cap.release()
        else:
            print(f"❌ 索引号 {i} 没有连接设备")

test_cameras()