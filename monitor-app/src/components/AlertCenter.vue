<template>
  <div class="event-page">
    <div class="page-header">
      <div>
        <h2>风险事件中心</h2>
        <p>集中处理 AI 检测产生的入侵、越线、聚集、逗留和疑似倒地事件。</p>
      </div>
      <button class="btn primary" @click="refreshAll">刷新数据</button>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <span>事件总数</span>
        <strong>{{ stats.total_events || 0 }}</strong>
      </div>
      <div class="stat-card">
        <span>今日事件</span>
        <strong>{{ stats.today_events || 0 }}</strong>
      </div>
      <div class="stat-card danger">
        <span>高风险</span>
        <strong>{{ stats.high_events || 0 }}</strong>
      </div>
      <div class="stat-card critical">
        <span>严重风险</span>
        <strong>{{ stats.critical_events || 0 }}</strong>
      </div>
    </div>

    <div class="toolbar">
      <label class="filter-field">
        <span>设备</span>
        <select v-model.number="filters.camera_id" @change="fetchEvents">
          <option :value="0">全部设备</option>
          <option v-for="cam in cameras" :key="cam.id" :value="cam.id">{{ cam.name }}</option>
        </select>
      </label>

      <label class="filter-field">
        <span>事件类型</span>
        <select v-model="filters.event_type" @change="fetchEvents">
          <option value="">全部类型</option>
          <option v-for="item in eventTypes" :key="item.value" :value="item.value">{{ item.label }}</option>
        </select>
      </label>

      <label class="filter-field">
        <span>风险等级</span>
        <select v-model="filters.risk_level" @change="fetchEvents">
          <option value="">全部等级</option>
          <option value="low">低</option>
          <option value="medium">中</option>
          <option value="high">高</option>
          <option value="critical">严重</option>
        </select>
      </label>

      <label class="filter-field">
        <span>处理状态</span>
        <select v-model="filters.status_filter" @change="fetchEvents">
          <option value="">全部状态</option>
          <option value="new">待处理</option>
          <option value="confirmed">已确认</option>
          <option value="ignored">已忽略</option>
          <option value="resolved">已解决</option>
        </select>
      </label>
    </div>

    <div class="table-panel">
      <table class="event-table">
        <thead>
          <tr>
            <th>事件</th>
            <th>设备</th>
            <th>风险</th>
            <th>人数</th>
            <th>置信度</th>
            <th>状态</th>
            <th>时间</th>
            <th class="actions-col">操作</th>
          </tr>
        </thead>
        <tbody v-if="events.length > 0">
          <tr v-for="event in events" :key="event.id">
            <td>
              <div class="event-name">{{ event.event_name }}</div>
              <div class="event-meta">{{ getEventLabel(event.event_type) }} / {{ event.region_name || '未绑定区域' }}</div>
            </td>
            <td>{{ event.cam_name }}</td>
            <td><span class="risk-pill" :class="event.risk_level">{{ riskLabel(event.risk_level) }}</span></td>
            <td>{{ event.person_count }}</td>
            <td>{{ formatConfidence(event.confidence) }}</td>
            <td><span class="status-pill" :class="event.status">{{ statusLabel(event.status) }}</span></td>
            <td class="time-cell">{{ event.created_at }}</td>
            <td class="actions-col">
              <button class="icon-btn" @click="openImagePreview(event.image_filename)" title="查看抓拍">
                查看
              </button>
              <select class="status-select" :value="event.status" @change="updateStatus(event, $event.target.value)">
                <option value="new">待处理</option>
                <option value="confirmed">已确认</option>
                <option value="ignored">已忽略</option>
                <option value="resolved">已解决</option>
              </select>
            </td>
          </tr>
        </tbody>
        <tbody v-else>
          <tr>
            <td colspan="8" class="empty-state">暂无风险事件。</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="pagination">
      <span>共 {{ total }} 条</span>
      <div class="page-actions">
        <button class="btn ghost" :disabled="page <= 1" @click="changePage(page - 1)">上一页</button>
        <span>第 {{ page }} 页</span>
        <button class="btn ghost" :disabled="page * pageSize >= total" @click="changePage(page + 1)">下一页</button>
      </div>
    </div>

    <div v-if="previewImageUrl" class="preview-modal" @mousedown.self="closeImagePreview">
      <div class="preview-content">
        <button class="preview-close-btn" @click="closeImagePreview">×</button>
        <img :src="previewImageUrl" alt="风险事件抓拍" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import axios from 'axios';

const API_BASE = `http://${window.location.hostname}:8000/api`;
const hostUrl = window.location.hostname;

const cameras = ref([]);
const events = ref([]);
const stats = ref({});
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const previewImageUrl = ref(null);

const filters = ref({
  camera_id: 0,
  event_type: '',
  risk_level: '',
  status_filter: ''
});

const eventTypes = [
  { value: 'intrusion', label: '禁区入侵' },
  { value: 'line_crossing', label: '越线检测' },
  { value: 'crowding', label: '人员聚集' },
  { value: 'loitering', label: '长时间逗留' },
  { value: 'fall_suspected', label: '疑似倒地' },
  { value: 'person_detected', label: '人员出现' }
];

const fetchCameras = async () => {
  const res = await axios.get(`${API_BASE}/cameras`);
  cameras.value = res.data;
};

const fetchStats = async () => {
  const res = await axios.get(`${API_BASE}/events/stats`);
  stats.value = res.data;
};

const fetchEvents = async () => {
  const params = {
    page: page.value,
    page_size: pageSize.value
  };

  Object.entries(filters.value).forEach(([key, value]) => {
    if (value) params[key] = value;
  });

  const res = await axios.get(`${API_BASE}/events`, { params });
  events.value = res.data.items || [];
  total.value = res.data.total || 0;
};

const refreshAll = async () => {
  await Promise.all([fetchCameras(), fetchStats(), fetchEvents()]);
};

const changePage = async (nextPage) => {
  page.value = nextPage;
  await fetchEvents();
};

const updateStatus = async (event, status) => {
  await axios.put(`${API_BASE}/events/${event.id}/status`, { status });
  event.status = status;
  await fetchStats();
};

const openImagePreview = (filename) => {
  previewImageUrl.value = `http://${hostUrl}:8000/snapshots/${filename}`;
};

const closeImagePreview = () => {
  previewImageUrl.value = null;
};

const getEventLabel = (type) => eventTypes.find(item => item.value === type)?.label || type;
const riskLabel = (level) => ({ low: '低', medium: '中', high: '高', critical: '严重' }[level] || level);
const statusLabel = (status) => ({ new: '待处理', confirmed: '已确认', ignored: '已忽略', resolved: '已解决' }[status] || status);
const formatConfidence = (value) => `${Math.round((Number(value) || 0) * 100)}%`;

onMounted(refreshAll);
</script>

<style scoped>
.event-page {
  padding: 28px 32px;
  max-width: 1480px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 22px;
}

.page-header h2 {
  margin: 0 0 8px;
  color: var(--text-main);
  font-size: 24px;
  font-weight: 800;
}

.page-header p {
  margin: 0;
  color: var(--text-sub);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(160px, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
  box-shadow: var(--shadow-soft);
}

.stat-card span {
  color: var(--text-sub);
  font-weight: 700;
}

.stat-card strong {
  display: block;
  margin-top: 8px;
  font-size: 28px;
  color: var(--text-main);
}

.stat-card.danger strong {
  color: var(--danger);
}

.stat-card.critical strong {
  color: #991b1b;
}

.toolbar {
  display: grid;
  grid-template-columns: repeat(4, minmax(170px, 1fr));
  gap: 12px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 14px;
  box-shadow: var(--shadow-soft);
  margin-bottom: 18px;
}

.filter-field {
  display: flex;
  flex-direction: column;
  gap: 7px;
  color: var(--text-sub);
  font-weight: 700;
}

.filter-field select,
.status-select {
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-input);
  color: var(--text-main);
  padding: 9px 10px;
  outline: none;
}

.table-panel {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
  box-shadow: var(--shadow-soft);
}

.event-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.event-table th {
  background: var(--hover-bg);
  color: var(--text-sub);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 13px 16px;
  border-bottom: 1px solid var(--border-color);
}

.event-table td {
  padding: 14px 16px;
  border-bottom: 1px solid var(--border-color);
  color: var(--text-main);
  vertical-align: middle;
}

.event-table tr:hover td {
  background: var(--hover-bg);
}

.event-name {
  font-weight: 800;
}

.event-meta,
.time-cell {
  margin-top: 4px;
  color: var(--text-sub);
  font-size: 12px;
}

.risk-pill,
.status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 52px;
  border-radius: 999px;
  padding: 4px 9px;
  font-size: 12px;
  font-weight: 800;
}

.risk-pill.low {
  background: rgba(8, 145, 178, 0.12);
  color: var(--info);
}

.risk-pill.medium {
  background: rgba(217, 119, 6, 0.14);
  color: var(--warning);
}

.risk-pill.high,
.risk-pill.critical {
  background: rgba(220, 38, 38, 0.12);
  color: var(--danger);
}

.status-pill.new {
  background: rgba(217, 119, 6, 0.14);
  color: var(--warning);
}

.status-pill.confirmed {
  background: var(--primary-soft);
  color: var(--primary);
}

.status-pill.ignored {
  background: var(--hover-bg);
  color: var(--text-muted);
}

.status-pill.resolved {
  background: rgba(5, 150, 105, 0.12);
  color: var(--success);
}

.actions-col {
  text-align: right;
  white-space: nowrap;
}

.icon-btn {
  border: 1px solid var(--border-color);
  background: var(--bg-card);
  color: var(--text-main);
  border-radius: 6px;
  padding: 8px 10px;
  margin-right: 8px;
  cursor: pointer;
  font-weight: 800;
}

.btn {
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 9px 14px;
  cursor: pointer;
  font-weight: 800;
}

.btn.primary {
  background: var(--primary);
  border-color: var(--primary);
  color: #fff;
}

.btn.ghost {
  background: var(--bg-card);
  color: var(--text-main);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.empty-state {
  text-align: center;
  color: var(--text-muted);
  padding: 48px;
}

.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: var(--text-sub);
  margin-top: 14px;
}

.page-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.preview-modal {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.82);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 10000;
}

.preview-content {
  position: relative;
  max-width: 90%;
  max-height: 90%;
}

.preview-content img {
  max-width: 100%;
  max-height: 90vh;
  object-fit: contain;
  border-radius: 8px;
  box-shadow: 0 18px 42px rgba(0, 0, 0, 0.45);
}

.preview-close-btn {
  position: absolute;
  top: -42px;
  right: -6px;
  background: transparent;
  border: none;
  color: #fff;
  font-size: 30px;
  cursor: pointer;
}

@media (max-width: 1100px) {
  .stats-grid,
  .toolbar {
    grid-template-columns: repeat(2, minmax(160px, 1fr));
  }
}

@media (max-width: 760px) {
  .event-page {
    padding: 22px;
  }

  .page-header {
    flex-direction: column;
  }

  .stats-grid,
  .toolbar {
    grid-template-columns: 1fr;
  }

  .table-panel {
    overflow-x: auto;
  }
}
</style>
