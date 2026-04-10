# -*- coding: utf-8 -*-
import codecs

with codecs.open(r'd:\suiyuer\Projects\monitor-app\yolov26\ai_server.py', 'r', 'utf-8') as f:
    text = f.read()

text = text.replace('multiprocessing.freeze_support()\n    multiprocessing.freeze_support()', 'multiprocessing.freeze_support()')

with codecs.open(r'd:\suiyuer\Projects\monitor-app\yolov26\ai_server.py', 'w', 'utf-8') as f:
    f.write(text)
print('done')
