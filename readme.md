Camera Sensor Front

ffmpeg -f dshow -i video="1080P USB Camera" -c:v libx264 -preset ultrafast -tune zerolatency -f rtsp rtsp://127.0.0.1:8555/mystream


ffmpeg -f dshow -rtbufsize 1024M -i video="Camera Sensor Front" -c:v libx264 -preset ultrafast -tune zerolatency -f rtsp rtsp://127.0.0.1:8554/camera1


ffmpeg -f dshow -rtbufsize 1024M -video_size 1280x720 -framerate 30 -i video="1080P USB Camera" -c:v libx264 -preset ultrafast -tune zerolatency -f rtsp rtsp://127.0.0.1:8554/camera2