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
          <div style="display:flex; align-items:center; gap: 15px;">
            <button @click="openHistory(cam)" class="history-btn">🎞️ 历史</button>
            <div class="status-badge">
              <div class="dot" :class="cam.status"></div>
              {{ cam.status === 'connected' ? '设备在线' : '设备离线' }}
            </div>
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

    <div v-if="showHistoryModal" class="modal-overlay" @click.self="closeHistory">
      <div class="modal-content">
        <div class="modal-header">
          <h3>🎞️ 【{{ currentHistoryCam.name }}】历史录像</h3>
          <button @click="closeHistory" class="close-btn">✖</button>
        </div>

        <div class="modal-body">
          <div class="video-player">
            <video v-if="playingUrl" :src="playingUrl" controls autoplay class="html5-video"></video>
            <div v-else class="no-video-selected">请从右侧选择时段播放</div>
          </div>

          <div class="video-list">
            <h4>录像切片 (最近15天)</h4>
            <div v-if="records.length === 0" style="color: var(--text-muted); font-size: 13px;">暂无录像记录</div>
            <button
              v-for="record in records"
              :key="record.filename"
              @click="playRecord(record)"
              :class="['record-item', { active: playingUrl && playingUrl.split('?')[0] === record.url }]"
            >
              🎥 {{ formatRecordName(record.filename) }}
            </button>
          </div>
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
let camTimer = null;
const cameras = ref([]);

const WEBRTC_BASE_URL = 'http://127.0.0.1:8889/';

// 历史录像模态框相关
const showHistoryModal = ref(false);
const currentHistoryCam = ref(null);
const records = ref([]);
const playingUrl = ref(null);

const fetchCameras = async () => {
  try {
    const res = await axios.get('http://127.0.0.1:8000/api/cameras');
    cameras.value = res.data.map(cam => ({
      id: cam.id,
      name: cam.name,
      url: `${WEBRTC_BASE_URL}${cam.stream_path}/`,
      status: cam.status === 'online' ? 'connected' : 'disconnected'
    }));
  } catch (error) {
    console.error("无法获取摄像头列表", error);
  }
};

// 打开历史模态框拉取列表
const openHistory = async (cam) => {
  currentHistoryCam.value = cam;
  showHistoryModal.value = true;
  playingUrl.value = null;
  records.value = [];
  try {
    const res = await axios.get(`http://127.0.0.1:8000/api/cameras/${cam.id}/records`);
    records.value = res.data;
  } catch(e) {}
};

const closeHistory = () => {
  showHistoryModal.value = false;
  playingUrl.value = null;
};

// 播放具体录像，添加时间戳参数打破浏览器对 MP4 大小的强缓存
const playRecord = (record) => {
  playingUrl.value = null;
  setTimeout(() => {
    // 仅针对正在录制中的记录，在 URL 上加随机数骗过浏览器的旧时长缓存，强制拉取新数据
    if (record.url.includes('_recording')) {
      playingUrl.value = `${record.url}?t=${new Date().getTime()}`;
    } else {
      playingUrl.value = record.url;
    }
  }, 50);
};

// 格式化文件名，将 _ 和 - 替换为 : 展示，避免修改系统真实文件导致 Windows 报错
const formatRecordName = (filename) => {
  let name = filename.replace('.mp4', '').replace('_recording', ' (正在录制)');
  // 匹配类似 _17-30-00 并替换为 17:30:00 (使用空格分隔日期和时间)
  name = name.replace(/_(\d{2})-(\d{2})-(\d{2})/g, ' $1:$2:$3');
  // 把 _到_ 替换为友好的  到
  name = name.replace(/_到_/g, ' 到 ');
  return name;
};

const updateTime = () => {
  const now = new Date();
  currentTime.value = now.toLocaleString('zh-CN', { hour12: false });
};

onMounted(() => {
  updateTime();
  timeTimer = setInterval(updateTime, 1000);
  fetchCameras();
  camTimer = setInterval(fetchCameras, 5000);
});

onUnmounted(() => {
  if (timeTimer) clearInterval(timeTimer);
  if (camTimer) clearInterval(camTimer);
});
</script>

<style scoped>
/* 保留原有样式 */
.monitor-dashboard { padding: 24px; box-sizing: border-box; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid var(--border-color); }
.header h1 { margin: 0; font-size: 24px; font-weight: 600; color: var(--text-main); }
.time-display { font-size: 16px; color: var(--text-sub); font-variant-numeric: tabular-nums; font-weight: 500; }
.video-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
@media (max-width: 1000px) { .video-grid { grid-template-columns: 1fr; } }
.card { background-color: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; overflow: hidden; box-shadow: var(--shadow); transition: 0.3s; }
.card-header { padding: 12px 20px; display: flex; justify-content: space-between; align-items: center; background-color: var(--hover-bg); border-bottom: 1px solid var(--border-color); }
.cam-name { font-size: 15px; font-weight: bold; color: var(--text-main); }
.history-btn { background: var(--primary); color: white; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 12px; font-weight: bold; }
.history-btn:hover { background: var(--primary-hover); }
.status-badge { display: flex; align-items: center; font-size: 13px; color: var(--text-sub); font-weight: 500;}
.dot { width: 8px; height: 8px; border-radius: 50%; margin-right: 8px; }
.dot.connected { background-color: var(--success); box-shadow: 0 0 8px rgba(16, 185, 129, 0.4); }
.dot.disconnected { background-color: var(--danger); box-shadow: 0 0 8px rgba(239, 68, 68, 0.4); }
.video-container { width: 100%; aspect-ratio: 16 / 9; background-color: #000; position: relative; }
.video-container iframe { width: 100%; height: 100%; border: none; display: block; }
.no-signal { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: var(--text-muted); font-size: 14px; letter-spacing: 2px; }

/* 模态框样式 */
.modal-overlay { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.6); display: flex; justify-content: center; align-items: center; z-index: 9999; }
.modal-content { background: var(--bg-card); width: 85%; max-width: 1200px; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.5); border: 1px solid var(--border-color); }
.modal-header { padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; background: var(--bg-sidebar); border-bottom: 1px solid var(--border-color); }
.modal-header h3 { margin: 0; color: var(--text-main); font-size: 18px; }
.close-btn { background: none; border: none; color: var(--text-sub); font-size: 20px; cursor: pointer; }
.modal-body { display: flex; height: auto; min-height: 50vh; max-height: 80vh; }
.video-player { flex: 3; background: var(--bg-body); display: flex; justify-content: center; align-items: center; padding: 20px; }
.html5-video { width: 100%; aspect-ratio: 16 / 9; object-fit: contain; outline: none; background: #000; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); border: 1px solid var(--border-color); }
.no-video-selected { color: var(--text-muted); font-size: 15px; }
.video-list { flex: 1; min-width: 250px; border-left: 1px solid var(--border-color); background: var(--bg-sidebar); padding: 15px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; }
.video-list h4 { margin: 0 0 10px 0; color: var(--text-main); font-size: 14px; }
.record-item { background: var(--bg-body); border: 1px solid var(--border-color); padding: 10px; text-align: left; border-radius: 6px; cursor: pointer; color: var(--text-sub); transition: 0.2s; font-size: 13px; }
.record-item:hover { background: var(--hover-bg); border-color: var(--primary); }
.record-item.active { background: var(--primary); color: white; border-color: var(--primary); }
</style>