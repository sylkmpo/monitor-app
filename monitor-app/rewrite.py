# -*- coding: utf-8 -*-
import codecs
import re

with codecs.open(r'd:\suiyuer\Projects\monitor-app\yolov26\ai_server.py', 'r', 'utf-8') as f:
    text = f.read()

# 1. Remove global model load. Use regex since text encoding matches can be tricky with console outputs.
text = re.sub(r'logger.info\([\"\'].*?YOLO.*?(?:显存|樉鍗?).*?[\"\']\)\r?\nmodel = YOLO\([\"\']yolo26n\.pt[\"\']\)', '', text)

# 2. Add multiprocessing import
if 'import multiprocessing' not in text:
    text = text.replace("import threading", "import threading\nimport multiprocessing")

# 3. Add model load inside process_video_stream
old_def = r"def process_video_stream\(cam_id,\s*cam_name,\s*input_source,\s*output_rtsp,\s*stop_event\):\r?\n\s*first_attempt = True"
new_def = '''def process_video_stream(cam_id, cam_name, input_source, output_rtsp, stop_event):
    from ultralytics import YOLO
    logger.info(f"[{cam_name}] 采用多进程重构：正在独立进程加载专属 YOLO 模型，突破 GIL 多路并发上限...")
    model = YOLO('yolo26n.pt')
    first_attempt = True'''
text = re.sub(old_def, new_def, text)

# 4. Change threading to multiprocessing for t_main
text = re.sub(r't_main = threading\.Thread\(target=process_video_stream,\s*args=\(cam_id,\s*cam\[[\'"]name[\'"]\],\s*cam\[[\'"]input_source[\'"]\],\s*output_rtsp,\s*stop_event\),\s*daemon=True\)', 
              '''t_main = multiprocessing.Process(target=process_video_stream,
                                              args=(cam_id, cam['name'], cam['input_source'], output_rtsp, stop_event),
                                              daemon=True)''', text)

# 5. Change threading.Event() to multiprocessing.Event()
text = text.replace("stop_event = threading.Event()", "stop_event = multiprocessing.Event()")

# 6. Ensure freeze_support is called early in main
text = re.sub(r"if __name__ == \'?__main__\'?:\r?\n\s*", "if __name__ == '__main__':\n    multiprocessing.freeze_support()\n    ", text)

with codecs.open(r'd:\suiyuer\Projects\monitor-app\yolov26\ai_server.py', 'w', 'utf-8') as f:
    f.write(text)
print("Rewrite script completed!")
