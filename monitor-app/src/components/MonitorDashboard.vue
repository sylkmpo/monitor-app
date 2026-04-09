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
            <video v-if="playingUrl" :src="playingUrl" controls autoplay muted class="html5-video"></video>
            <div v-else class="no-video-selected">请从右侧选择时段播放</div>
          </div>

          <div class="video-list">
            <div class="list-header">
              <h4>录像切片检索</h4>
            </div>
            
            <!-- 企业级筛选面板 -->
            <div class="filter-panel">
              <div class="filter-row">
                <span class="filter-icon">📅</span>
                <input type="date" v-model="selectedDate" class="enterprise-input" />
              </div>
              <div class="filter-row">
                <span class="filter-icon">⏰</span>
                <div class="time-range-group">
                  <select v-model.number="selectedStartHour" class="enterprise-select">
                    <option v-for="h in 24" :key="'s'+(h-1)" :value="h-1">{{ String(h-1).padStart(2, '0') }}:00</option>
                  </select>
                  <span class="range-divider">至</span>
                  <select v-model.number="selectedEndHour" class="enterprise-select">
                    <option v-for="h in 24" :key="'e'+(h-1)" :value="h-1">{{ String(h-1).padStart(2, '0') }}:59</option>
                  </select>
                </div>
              </div>
            </div>

            <div class="records-scroll-area">
              <div v-if="filteredRecords.length === 0" class="empty-records">
                <svg viewBox="0 0 24 24" width="32" height="32" stroke="var(--border-color)" stroke-width="1.5" fill="none"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                <p>该时段暂无录像</p>
              </div>
              
              <button
                v-for="record in filteredRecords"
                :key="record.filename"
                @click="playRecord(record)"
                :class="['record-item', { active: playingUrl && playingUrl.split('?')[0] === record.url }]"
              >
                <div class="record-icon">
                  <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none"><path d="M23 7l-7 5 7 5V7z"></path><rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect></svg>
                </div>
                <div class="record-info">
                  <span class="record-name">{{ formatRecordName(record.filename) }}</span>
                </div>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
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

// 初始化日期为当天
const getTodayStr = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};
const selectedDate = ref(getTodayStr());
const selectedStartHour = ref(0);
const selectedEndHour = ref(23);

const filteredRecords = computed(() => {
  return records.value.filter(r => {
    // 1. 先过滤日期
    if (selectedDate.value && !r.filename.startsWith(selectedDate.value)) {
      return false;
    }
    
    // 2. 解析时段 (文件格式：YYYY-MM-DD_HH-MM-SS...)
    // 提取中间代表小时的这两位，比如 "2026-04-09_11-59-04" -> 截取下标 11~12 为 "11"
    const hourStr = r.filename.substring(11, 13);
    const hour = parseInt(hourStr, 10);
    
    if (!isNaN(hour)) {
      // 如果选中了非法的范围 (比如 23 到 1，需要做处理吗？一般确保 start <= end 即可)
      const start = Math.min(selectedStartHour.value, selectedEndHour.value);
      const end = Math.max(selectedStartHour.value, selectedEndHour.value);
      
      if (hour < start || hour > end) {
        return false;
      }
    }
    
    return true;
  });
});

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
  selectedDate.value = getTodayStr(); // 每次打开强制重置回今天
  selectedStartHour.value = 0;        // 重置为 0 点
  selectedEndHour.value = 23;         // 重置为 23 点
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
    // 强制每次点击历史录像时都加上时间戳
    // 这样浏览器将不会使用之前被破坏或因为没下完而卡住的缓存视频
    playingUrl.value = `${record.url}?t=${new Date().getTime()}`;
  }, 50);
};

// 格式化文件名，将 _ 和 - 替换为 : 展示，避免修改系统真实文件导致 Windows 报错
const formatRecordName = (filename) => {
  let name = filename.replace('.mp4', '').replace('_recording', ' (正在录制)');
  // 匹配类似 _17-30-00 并替换为 17:30:00 (使用空格分隔日期和时间)
  name = name.replace(/_(\d{2})-(\d{2})-(\d{2})/g, ' $1:$2:$3');
  // 替换残留的 _到_ 及其变体，使其展示更友好
  name = name.replace(/_?到_?/g, ' 到 ');
  return name.trim();
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
.modal-body { display: flex; height: 75vh; }
.video-player { flex: 3; background: #0b0f19; display: flex; justify-content: center; align-items: center; position: relative;}
.html5-video { width: 100%; height: 100%; object-fit: contain; outline: none; background: #000; box-shadow: 0 4px 15px rgba(0,0,0,0.3); border-right: 1px solid var(--border-color); }
.no-video-selected { color: rgba(255,255,255,0.4); font-size: 15px; font-weight: 500; letter-spacing: 1px; }

.video-list { 
  flex: 1; min-width: 320px; 
  border-left: 1px solid var(--border-color); 
  background: var(--bg-body); 
  display: flex; flex-direction: column; 
}
.list-header { 
  padding: 18px 20px; 
  border-bottom: 1px solid var(--border-color); 
  background: var(--bg-card); 
}
.list-header h4 { margin: 0; color: var(--text-main); font-size: 16px; font-weight: 600;}

/* 检索筛选面板 */
.filter-panel {
  padding: 15px 20px;
  background: var(--bg-sidebar);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.filter-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.filter-icon {
  font-size: 16px;
  opacity: 0.7;
}

/* 企业级表单输入框样式 */
.enterprise-input, .enterprise-select {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-body);
  color: var(--text-main);
  font-size: 13px;
  transition: all 0.2s;
  outline: none;
}
.enterprise-input:focus, .enterprise-select:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}
.time-range-group {
  display: flex;
  align-items: center;
  flex: 1;
  gap: 6px;
}
.range-divider {
  color: var(--text-muted);
  font-size: 12px;
}

/* 录像切片瀑布流区 */
.records-scroll-area {
  flex: 1;
  padding: 15px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.empty-records {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  padding: 40px 0;
  gap: 12px;
  font-size: 14px;
}

.record-item {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  padding: 12px 14px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 1px 2px rgba(0,0,0,0.02);
}
.record-item:hover { 
  transform: translateY(-1px);
  border-color: var(--primary); 
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}
.record-item.active { 
  background: var(--primary-light, rgba(37, 99, 235, 0.05));
  border-color: var(--primary); 
}
.record-item.active .record-icon, .record-item.active .record-name {
  color: var(--primary);
}

.record-icon {
  color: var(--text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-body);
  padding: 8px;
  border-radius: 6px;
}
.record-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  text-align: left;
}
.record-name {
  color: var(--text-main);
  font-size: 13px;
  font-weight: 500;
}
</style>