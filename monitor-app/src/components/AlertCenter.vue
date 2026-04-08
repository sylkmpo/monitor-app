<template>
  <div class="alert-container">
    <h2>🚨 智能告警抓拍中心</h2>
    <div class="header-actions">
      <button @click="fetchAlerts" class="refresh-btn">🔄 刷新记录</button>

      <label class="select-all">
        <input type="checkbox" :checked="isAllSelected" @change="toggleSelectAll" /> 全选
      </label>
      <button v-if="selectedAlerts.length > 0" @click="deleteSelected" class="delete-btn">
        🗑️ 删除选中 ({{ selectedAlerts.length }})
      </button>
    </div>

    <div class="alert-grid">
      <div class="alert-card" v-for="alert in alerts" :key="alert.id">
        <input type="checkbox" class="alert-checkbox" :value="alert.id" v-model="selectedAlerts" />

        <div class="img-wrapper" @click="openImagePreview(alert.image_filename)">
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

    <!-- 放大预览模态框 -->
    <div v-if="previewImageUrl" class="preview-modal" @click.self="closeImagePreview">
      <div class="preview-content">
        <button class="preview-close-btn" @click="closeImagePreview">✖</button>
        <img :src="previewImageUrl" alt="大图预览" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import axios from 'axios';

const alerts = ref([]);
const selectedAlerts = ref([]); // 记录选中的告警 ID

// 预览图片逻辑
const previewImageUrl = ref(null);

const openImagePreview = (filename) => {
  previewImageUrl.value = `http://127.0.0.1:8000/snapshots/${filename}`;
};

const closeImagePreview = () => {
  previewImageUrl.value = null;
};

const fetchAlerts = async () => {
  try {
    const res = await axios.get('http://127.0.0.1:8000/api/alerts');
    alerts.value = res.data;
    selectedAlerts.value = []; // 每次刷新后清空选中状态
  } catch (error) {
    console.error("获取告警失败", error);
  }
};

// 全选状态计算属性
const isAllSelected = computed(() => {
  return alerts.value.length > 0 && selectedAlerts.value.length === alerts.value.length;
});

// 全选 / 取消全选逻辑
const toggleSelectAll = (e) => {
  if (e.target.checked) {
    selectedAlerts.value = alerts.value.map(a => a.id);
  } else {
    selectedAlerts.value = [];
  }
};

// 删除选中逻辑
const deleteSelected = async () => {
  if (!confirm(`确定要彻底删除选中的 ${selectedAlerts.value.length} 张图片及记录吗？`)) return;

  try {
    await axios.delete('http://127.0.0.1:8000/api/alerts', {
      data: { alert_ids: selectedAlerts.value }
    });
    fetchAlerts(); // 重新拉取最新数据
  } catch (error) {
    alert("删除失败，请检查网络");
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
/* 调整头部样式适配复选框 */
.header-actions { display: flex; gap: 15px; align-items: center; margin-bottom: 20px; }
.refresh-btn { background: var(--primary); color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-weight: bold; }
.delete-btn { background: var(--danger); color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-weight: bold; }
.select-all { color: var(--text-main); font-weight: bold; cursor: pointer; display: flex; align-items: center; gap: 5px; }

.alert-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
.alert-card { position: relative; background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 8px; overflow: hidden; box-shadow: var(--shadow); transition: 0.3s; }
.alert-card:hover { transform: translateY(-2px); border-color: var(--primary); }

/* 复选框浮动在图片左上角 */
.alert-checkbox { position: absolute; top: 10px; left: 10px; z-index: 10; width: 18px; height: 18px; cursor: pointer; accent-color: var(--primary); }

.img-wrapper { width: 100%; aspect-ratio: 16/9; background: var(--bg-body); border-bottom: 1px solid var(--border-color); cursor: pointer; }
.img-wrapper img { width: 100%; height: 100%; object-fit: contain; display: block; }
.alert-info { padding: 15px; }
.alert-type { color: var(--danger); font-weight: bold; margin-bottom: 8px; font-size: 16px; }
.cam-name { color: var(--text-main); font-size: 14px; margin-bottom: 4px; font-weight: 500; }
.time { color: var(--text-sub); font-size: 13px; margin-bottom: 4px; }
.empty-state { text-align: center; color: var(--text-muted); padding: 50px; grid-column: 1 / -1; background: var(--bg-card); border: 1px dashed var(--border-color); border-radius: 8px; }

/* 放大预览模态框样式 */
.preview-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 10000;
}
.preview-content {
  position: relative;
  max-width: 90%;
  max-height: 90%;
  display: flex;
  justify-content: center;
}
.preview-content img {
  max-width: 100%;
  max-height: 90vh;
  object-fit: contain;
  border-radius: 8px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.6);
}
.preview-close-btn {
  position: absolute;
  top: -40px;
  right: -10px;
  background: none;
  border: none;
  color: white;
  font-size: 30px;
  cursor: pointer;
  transition: color 0.2s;
}
.preview-close-btn:hover {
  color: var(--danger);
}
</style>