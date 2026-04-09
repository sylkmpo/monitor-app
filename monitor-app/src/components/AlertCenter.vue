<template>
  <div class="alert-container">
    <div class="page-header">
      <h2>🚨 智能告警抓拍中心</h2>
      <div class="header-actions">
        <div class="action-group">
          <span class="filter-label">筛选设备：</span>
          <div class="select-wrapper">
            <select v-model="filterCamName" class="filter-input" @change="fetchAlerts">
              <option value="">所有设备</option>
              <option v-for="cam in cameras" :key="cam.id" :value="cam.name">{{ cam.name }}</option>
            </select>
          </div>
        </div>
        
        <button @click="fetchAlerts" class="btn btn-outline">
          <i class="icon">🔄</i> 刷新数据
        </button>

        <div class="divider"></div>

        <label class="select-all-wrapper">
          <input type="checkbox" :checked="isAllSelected" @change="toggleSelectAll" class="custom-checkbox" />
          <span>全选</span>
        </label>

        <button v-if="selectedAlerts.length > 0" @click="deleteSelected" class="btn btn-danger fade-in">
          <i class="icon">🗑️</i> 删除选中 ({{ selectedAlerts.length }})
        </button>
      </div>
    </div>

    <div v-for="(group, camName) in groupedAlerts" :key="camName" class="device-group">
      <h3 class="device-title">📷 设备: {{ camName }} <span class="badge">{{ group.length }}</span></h3>
      <div class="alert-grid">
        <div class="alert-card" v-for="alert in group" :key="alert.id">
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
      </div>
    </div>
    <div v-if="alerts.length === 0" class="empty-state">暂无告警记录</div>

    <!-- 放大预览模态框 -->
    <div v-if="previewImageUrl" class="preview-modal" @mousedown.self="closeImagePreview">
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
const cameras = ref([]);
const filterCamName = ref('');

// 按设备名称分组
const groupedAlerts = computed(() => {
  const groups = {};
  alerts.value.forEach(alert => {
    if (!groups[alert.cam_name]) {
      groups[alert.cam_name] = [];
    }
    groups[alert.cam_name].push(alert);
  });
  return groups;
});

// 预览图片逻辑
const previewImageUrl = ref(null);

const openImagePreview = (filename) => {
  previewImageUrl.value = `http://127.0.0.1:8000/snapshots/${filename}`;
};

const closeImagePreview = () => {
  previewImageUrl.value = null;
};

const fetchCameras = async () => {
  try {
    const res = await axios.get('http://127.0.0.1:8000/api/cameras');
    cameras.value = res.data;
  } catch (error) {
    console.error("获取设备列表失败", error);
  }
};

const fetchAlerts = async () => {
  try {
    const params = {};
    if (filterCamName.value) params.cam_name = filterCamName.value;

    const res = await axios.get('http://127.0.0.1:8000/api/alerts', { params });
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

onMounted(() => {
  fetchCameras();
  fetchAlerts();
});
</script>

<style scoped>
.alert-container { padding: 24px; max-width: 1400px; margin: 0 auto; }

/* 企业级布局：头部在一行或通过优雅换行实现 */
.page-header { display: flex; flex-direction: column; gap: 20px; margin-bottom: 30px; }
.page-header h2 { margin: 0; color: var(--text-main); font-size: 24px; font-weight: 600; letter-spacing: 0.5px; }

/* 操作栏容器 - 圆角阴影磨砂质感 */
.header-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  background: var(--bg-card);
  padding: 16px 24px;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  border: 1px solid var(--border-color);
}

/* 操作项分组 */
.action-group { display: flex; align-items: center; gap: 12px; }
.filter-label { color: var(--text-sub); font-size: 14px; font-weight: 500; }

.select-wrapper { position: relative; }
.filter-input {
  appearance: none;
  min-width: 200px;
  padding: 10px 36px 10px 16px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: var(--bg-body);
  color: var(--text-main);
  font-size: 14px;
  outline: none;
  cursor: pointer;
  transition: all 0.2s ease;
}
.filter-input:hover { border-color: var(--primary); }
.filter-input:focus { border-color: var(--primary); box-shadow: 0 0 0 3px rgba(var(--primary-rgb), 0.15); }
.select-wrapper::after {
  content: "▼";
  font-size: 10px;
  color: var(--text-sub);
  position: absolute;
  right: 14px;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
}

/* 按钮统一样式 */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 18px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  line-height: 1.2;
}
.btn .icon { font-size: 16px; font-style: normal; }

.btn-outline {
  background: transparent;
  color: var(--text-main);
  border: 1px solid var(--border-color);
}
.btn-outline:hover { background: var(--bg-body); border-color: var(--text-sub); }
.btn-outline:active { transform: scale(0.98); }

.btn-danger {
  background: var(--danger);
  color: white;
  border: 1px solid transparent;
  box-shadow: 0 4px 10px rgba(var(--danger-rgb, 244, 67, 54), 0.25);
}
.btn-danger:hover { filter: brightness(1.1); transform: translateY(-1px); }
.btn-danger:active { transform: scale(0.98); box-shadow: 0 2px 5px rgba(244, 67, 54, 0.2); }

/* 垂直分隔线 */
.divider { width: 1px; height: 24px; background: var(--border-color); margin: 0 8px; }

/* 全选框美化 */
.select-all-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: var(--text-main);
  font-size: 14px;
  font-weight: 500;
  padding: 6px 8px;
  border-radius: 6px;
  transition: background 0.2s;
}
.select-all-wrapper:hover { background: var(--bg-body); }
.custom-checkbox {
  appearance: none;
  width: 18px;
  height: 18px;
  border: 2px solid var(--border-color);
  border-radius: 4px;
  background: var(--bg-card);
  cursor: pointer;
  position: relative;
  transition: all 0.2s;
}
.custom-checkbox:checked {
  background: var(--primary);
  border-color: var(--primary);
}
.custom-checkbox:checked::after {
  content: "✔";
  position: absolute;
  color: white;
  font-size: 12px;
  left: 3px;
  top: 0px;
}

.fade-in { animation: fadeIn 0.3s cubic-bezier(0.16, 1, 0.3, 1); }
@keyframes fadeIn {
  from { opacity: 0; transform: translateX(-10px); }
  to { opacity: 1; transform: translateX(0); }
}

.device-group { margin-bottom: 40px; }
.device-title { margin-bottom: 20px; font-size: 18px; font-weight: 600; color: var(--text-main); display: flex; align-items: center; gap: 10px; border-bottom: 1px solid var(--border-color); padding-bottom: 12px; }
.badge { background: var(--primary); color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; }

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