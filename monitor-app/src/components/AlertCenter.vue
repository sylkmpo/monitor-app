<template>
  <div class="alert-container">
    <h2>🚨 智能告警抓拍中心</h2>
    <div class="header-actions">
      <button @click="fetchAlerts" class="refresh-btn">🔄 刷新记录</button>
    </div>

    <div class="alert-grid">
      <div class="alert-card" v-for="alert in alerts" :key="alert.id">
        <div class="img-wrapper">
          <img :src="`http://127.0.0.1:8000/snapshots/${alert.image_filename}`" alt="抓拍画面" @error="handleImgError" />
        </div>
        <div class="alert-info">
          <div class="alert-type">⚠️ {{ alert.alert_type }}</div>
          <div class="cam-name">📍 设备: {{ alert.cam_name }}</div>
          <div class="time">🕒 {{ alert.timestamp }}</div>
        </div>
      </div>
      <div v-if="alerts.length === 0" class="empty-state">暂无告警记录</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import axios from 'axios';

const alerts = ref([]);

const fetchAlerts = async () => {
  try {
    const res = await axios.get('http://127.0.0.1:8000/api/alerts');
    alerts.value = res.data;
  } catch (error) {
    console.error("获取告警失败", error);
  }
};

const handleImgError = (e) => {
  e.target.src = 'https://via.placeholder.com/400x225?text=Image+Lost';
};

onMounted(fetchAlerts);
</script>

<style scoped>
.alert-container { padding: 24px; }
h2 { margin-top: 0; color: var(--text-main); }
.header-actions { margin-bottom: 20px; }
.refresh-btn { background: var(--primary); color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-weight: bold; }
.alert-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
.alert-card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 8px; overflow: hidden; box-shadow: var(--shadow); transition: 0.3s; }
.alert-card:hover { transform: translateY(-2px); border-color: var(--primary); }
.img-wrapper { width: 100%; aspect-ratio: 16/9; background: var(--bg-body); border-bottom: 1px solid var(--border-color); }
.img-wrapper img { width: 100%; height: 100%; object-fit: contain; display: block; }
.alert-info { padding: 15px; }
.alert-type { color: var(--danger); font-weight: bold; margin-bottom: 8px; font-size: 16px; }
.cam-name { color: var(--text-main); font-size: 14px; margin-bottom: 4px; font-weight: 500; }
.time { color: var(--text-sub); font-size: 13px; margin-bottom: 4px; }
.empty-state { text-align: center; color: var(--text-muted); padding: 50px; grid-column: 1 / -1; background: var(--bg-card); border: 1px dashed var(--border-color); border-radius: 8px; }
</style>