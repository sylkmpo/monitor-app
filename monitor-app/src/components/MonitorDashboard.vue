<template>
  <div class="monitor-dashboard">
    <header class="header">
      <h1>📹 监控画面看板</h1>
      <div class="time-display">{{ currentTime }}</div>
    </header>

    <div v-if="cameras.length === 0" class="no-signal" style="position: relative; text-align: center; margin-top: 50px;">
      正在加载摄像头数据或暂无设备，请去左侧【摄像头管理】添加...
    </div>

    <div class="video-grid">
      <div class="card" v-for="cam in cameras" :key="cam.id">
        <div class="card-header">
          <div class="cam-name">{{ cam.name }}</div>
          <div class="status-badge">
            <div class="dot" :class="cam.status"></div>
            {{ cam.status === 'connected' ? '设备在线' : '设备离线' }}
          </div>
        </div>
        
        <div class="video-container">
          <div v-if="cam.status !== 'connected'" class="no-signal">NO SIGNAL</div>
          <iframe 
            v-if="cam.status === 'connected' && cam.url"
            :src="cam.url" 
            frameborder="0" 
            scrolling="no" 
            allowfullscreen>
          </iframe>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import axios from 'axios';

const currentTime = ref('');
let timeTimer = null;
let camTimer = null; // 新增一个摄像头刷新定时器
const cameras = ref([]);

const WEBRTC_BASE_URL = 'http://127.0.0.1:8889/';

const fetchCameras = async () => {
  try {
    const res = await axios.get('http://127.0.0.1:8000/api/cameras');
    cameras.value = res.data.map(cam => ({
      id: cam.id,
      name: cam.name,
      url: `${WEBRTC_BASE_URL}${cam.stream_path}/`, 
      // 🚨 核心修改：读取真实状态，如果没有则是离线
      status: cam.status === 'online' ? 'connected' : 'disconnected'
    }));
  } catch (error) {
    console.error("无法获取摄像头列表", error);
  }
};

const updateTime = () => {
  const now = new Date();
  currentTime.value = now.toLocaleString('zh-CN', { hour12: false });
};

onMounted(() => {
  updateTime();
  timeTimer = setInterval(updateTime, 1000);
  
  fetchCameras(); // 初次获取
  camTimer = setInterval(fetchCameras, 5000); // 🚨 每5秒自动同步一次最新状态
});

onUnmounted(() => {
  if (timeTimer) clearInterval(timeTimer);
  if (camTimer) clearInterval(camTimer);
});
</script>

<style scoped>
.monitor-dashboard { padding: 24px; box-sizing: border-box; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid var(--border-color); }
.header h1 { margin: 0; font-size: 24px; font-weight: 600; letter-spacing: 1px; color: var(--text-main); }
.time-display { font-size: 16px; color: var(--text-sub); font-variant-numeric: tabular-nums; font-weight: 500; }
.video-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
@media (max-width: 1000px) { .video-grid { grid-template-columns: 1fr; } }
.card { background-color: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; overflow: hidden; box-shadow: var(--shadow); transition: 0.3s; }
.card-header { padding: 12px 20px; display: flex; justify-content: space-between; align-items: center; background-color: var(--hover-bg); border-bottom: 1px solid var(--border-color); }
.cam-name { font-size: 15px; font-weight: bold; color: var(--text-main); }
.status-badge { display: flex; align-items: center; font-size: 13px; color: var(--text-sub); font-weight: 500;}
.dot { width: 8px; height: 8px; border-radius: 50%; margin-right: 8px; }
.dot.connected { background-color: var(--success); box-shadow: 0 0 8px rgba(16, 185, 129, 0.4); }
.dot.disconnected { background-color: var(--danger); box-shadow: 0 0 8px rgba(239, 68, 68, 0.4); }
.video-container { width: 100%; aspect-ratio: 16 / 9; background-color: #000; position: relative; }
.video-container iframe { width: 100%; height: 100%; border: none; display: block; }
.no-signal { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: var(--text-muted); font-size: 14px; letter-spacing: 2px; }
</style>