<template>
  <div class="monitor-dashboard">
    <header class="header">
      <h1>📹 智能监控多画面看板 (WebRTC 高清版)</h1>
      <div class="time-display">{{ currentTime }}</div>
    </header>

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

const currentTime = ref('');
let timer = null;

// 🚀 绝杀改动：直接填写 WebRTC 的 HTTP 地址
// 注意：确保 192.168.237.222 是运行着 MediaMTX 服务器的那台电脑的 IP
const cameras = ref([
  { 
    id: 'cam1', 
    name: 'USB AI 智能监控', 
    // 端口改为 8889 (MediaMTX 默认 WebRTC 端口)，直接填流名称 ai_cam1
    url: 'http://192.168.237.222:8889/ai_cam1', 
    status: 'connected' 
  },
  { 
    id: 'cam2', 
    name: '大门监控', 
    url: 'http://192.168.237.222:8889/ai_cam2',
    status: 'disconnected' 
  },
  { 
    id: 'cam3', 
    name: '地下车库 A 区', 
    url: '', 
    status: 'disconnected' 
  },
  { 
    id: 'cam4', 
    name: '内部机房走廊', 
    url: '', 
    status: 'disconnected' 
  }
]);

// 时钟更新逻辑
const updateTime = () => {
  const now = new Date();
  currentTime.value = now.getFullYear() + '-' + 
    String(now.getMonth() + 1).padStart(2, '0') + '-' + 
    String(now.getDate()).padStart(2, '0') + ' ' + 
    String(now.getHours()).padStart(2, '0') + ':' + 
    String(now.getMinutes()).padStart(2, '0') + ':' + 
    String(now.getSeconds()).padStart(2, '0');
};

// 组件挂载
onMounted(() => {
  updateTime();
  timer = setInterval(updateTime, 1000);
  // 🧹 这里删除了所有 jsmpeg 的复杂连接代码，全靠 iframe 搞定！
});

onUnmounted(() => {
  if (timer) clearInterval(timer);
});
</script>

<style scoped>
.monitor-dashboard {
  --bg-dark: #0f1015;
  --card-bg: #1c1d26;
  --text-main: #ffffff;
  --text-sub: #8a8d98;
  --border-color: #2d2f3d;
  --success: #10b981;
  --error: #ef4444;

  background-color: var(--bg-dark);
  color: var(--text-main);
  font-family: 'Segoe UI', system-ui, sans-serif;
  min-height: 100vh;
  padding: 24px;
  box-sizing: border-box;
}

.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid var(--border-color); }
.header h1 { margin: 0; font-size: 24px; font-weight: 600; letter-spacing: 1px; }
.time-display { font-size: 16px; color: var(--text-sub); font-variant-numeric: tabular-nums; }

.video-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(450px, 1fr)); gap: 24px; }
.card { background-color: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; overflow: hidden; box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2); transition: transform 0.2s; }
.card:hover { border-color: #4b4d63; }
.card-header { padding: 12px 20px; display: flex; justify-content: space-between; align-items: center; background-color: rgba(255, 255, 255, 0.02); border-bottom: 1px solid var(--border-color); }
.cam-name { font-size: 15px; font-weight: 500; }
.status-badge { display: flex; align-items: center; font-size: 13px; color: var(--text-sub); }
.dot { width: 8px; height: 8px; border-radius: 50%; margin-right: 8px; }
.dot.connected { background-color: var(--success); box-shadow: 0 0 8px var(--success); }
.dot.disconnected { background-color: var(--error); box-shadow: 0 0 8px var(--error); }

.video-container { width: 100%; aspect-ratio: 16 / 9; background-color: #000; position: relative; }
/* 🚀 绝杀改动：确保 iframe 铺满且去边框 */
.video-container iframe { width: 100%; height: 100%; border: none; display: block; }
.no-signal { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: #555; font-size: 14px; letter-spacing: 2px; }
</style>