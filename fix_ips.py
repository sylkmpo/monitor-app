import os

files_to_fix = [
    r'd:\suiyuer\Projects\monitor-app\monitor-app\src\components\AlertCenter.vue',
    r'd:\suiyuer\Projects\monitor-app\monitor-app\src\components\CameraManager.vue',
    r'd:\suiyuer\Projects\monitor-app\monitor-app\src\components\Login.vue',
    r'd:\suiyuer\Projects\monitor-app\monitor-app\src\components\MonitorDashboard.vue',
    r'd:\suiyuer\Projects\monitor-app\monitor-app\src\components\UserCenter.vue'
]

for f in files_to_fix:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # We want to replace exactly:
    # 'http://127.0.0.1:8000...'  -> \http://\:8000...\
    content = content.replace(\"http://127.0.0.1:8000/api\", \"http://\:8000/api\")
    content = content.replace(\"http://127.0.0.1:8000/snapshots\", \"http://\:8000/snapshots\")
    content = content.replace(\"'http://127.0.0.1:8000/\", \"\http://\:8000/\")
    content = content.replace(\"'http://\:8000\", \"\http://\:8000\")

    # Replace any single quotes at the end of the URL string if we changed the start to a backtick
    content = content.replace(\"/api/login'\", \"/api/login\\")
    content = content.replace(\"/api/cameras'\", \"/api/cameras\\")
    content = content.replace(\"127.0.0.1\", \"\\")

    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)

with open(r'd:\suiyuer\Projects\monitor-app\monitor-app\vite.config.js', 'w', encoding='utf-8') as file:
    file.write(\"\"\"import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 5173
  }
})
\"\"\")
