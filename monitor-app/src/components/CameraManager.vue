<template>
  <div class="manager-container">
    <!-- 头部操作区 -->
    <div class="page-header">
      <div class="header-title">
        <h2>设备管理中心</h2>
        <span class="subtitle">统一管理系统中的所有监控设备节点</span>
      </div>
      <button class="btn-primary" @click="openAddModal">
        <svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round" class="icon"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
        添加新设备
      </button>
    </div>

    <!-- 数据表格区 -->
    <div class="table-card">
      <table class="enterprise-table">
        <thead>
          <tr>
            <th style="width: 80px">设备 ID</th>
            <th style="width: 200px">设备名称</th>
            <th style="width: 150px">设备型号</th>
            <th style="width: 100px">运行状态</th>
            <th>视频流入口 (源地址)</th>
            <th style="width: 180px">系统通道路径</th>
            <th style="width: 150px; text-align: right">操作</th>
          </tr>
        </thead>
        <tbody v-if="cameras.length > 0">
          <tr v-for="cam in cameras" :key="cam.id" class="table-row">
            <td class="col-id">#{{ String(cam.id).padStart(4, '0') }}</td>
            <td class="col-name">
              <div class="device-name">
                <div class="device-icon">📹</div>
                {{ cam.name }}
              </div>
            </td>
            <td class="col-model">
              <span class="badge" v-if="cam.model">{{ cam.model }}</span>
              <span class="text-muted" v-else>未知型号</span>
            </td>
            <td class="col-status">
              <span class="status-indicator" :class="cam.status === 'online' ? 'status-online' : 'status-offline'">
                <span class="status-dot"></span>
                {{ cam.status === 'online' ? '在线' : '离线' }}
              </span>
            </td>
            <td class="col-source" :title="cam.input_source">
              <code class="code-block">{{ cam.input_source }}</code>
            </td>
            <td class="col-path">
              <span class="path-text">{{ cam.stream_path }}</span>
            </td>
            <td class="col-actions">
              <button class="btn-icon btn-edit" @click="startEdit(cam)" title="编辑">
                <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>
              </button>
              <button class="btn-icon btn-delete" @click="deleteCamera(cam.id)" title="删除">
                <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
              </button>
            </td>
          </tr>
        </tbody>
        <tbody v-else>
          <tr>
            <td colspan="7" class="empty-state">
              <div class="empty-content">
                <svg viewBox="0 0 24 24" width="48" height="48" stroke="var(--border-color)" stroke-width="1" fill="none"><rect x="2" y="2" width="20" height="20" rx="2" ry="2"></rect><circle cx="12" cy="12" r="3"></circle><line x1="12" y1="15" x2="12" y2="22"></line><line x1="12" y1="2" x2="12" y2="9"></line><line x1="15" y1="12" x2="22" y2="12"></line><line x1="2" y1="12" x2="9" y2="12"></line></svg>
                <p>暂无接入设备，请点击上方按钮添加。</p>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 高级系统弹窗 -->
    <div class="modal-overlay" v-if="showModal" @click.self="closeModal">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ isEditing ? '编辑设备参数' : '接入新设备' }}</h3>
          <button class="close-btn" @click="closeModal">×</button>
        </div>
        
        <div class="modal-body">
          <div class="form-group">
            <label>设备名称</label>
            <input v-model="form.name" placeholder="请输入直观的节点名称，如：大门摄像头" />
          </div>
          <div class="form-group">
            <label>设备型号</label>
            <input v-model="form.model" placeholder="请手动输入配置型号，或直接点击下方热门品牌" />
            <div class="quick-tags">
              <span class="quick-tag" v-for="m in presetModels" :key="m" @click="form.model = m">
                {{ m }}
              </span>
            </div>
          </div>
          <div class="form-group required-group">
            <label>视频流地址 (必填)</label>
            <input v-model="form.input_source" 
                   placeholder="请输入 RTSP 地址，或填写 0 使用本地摄像头" />
            <!-- <span class="hint-text">如果是在本地测试可以直接填写 0。正规流地址请以 rtsp:// 开头。</span> -->
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-ghost" @click="closeModal">取消</button>
          <button class="btn-primary" @click="submitCamera" :disabled="!form.input_source.trim()">
            {{ isEditing ? '保存修改' : '确认添加设备' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import axios from 'axios';

const API_BASE = 'http://127.0.0.1:8000/api/cameras';
const cameras = ref([]);

// 预设的人气品牌型号
const presetModels = [
  '海康威视 (Hikvision)',
  '大华股份 (Dahua)',
  '宇视科技 (Uniview)',
  '天地伟业 (Tiandy)',
  'TP-LINK 安防',
  '萤石 (EZVIZ)',
  '小米 (Xiaomi) / Tapo',
  'USB 本地摄像头',
  '模拟/虚拟视频流'
];

// 弹窗与表单状态
const showModal = ref(false);
const isEditing = ref(false);
const editingId = ref(null);
const form = ref({ name: '', model: '', input_source: '' });

const fetchCameras = async () => {
  try {
    const res = await axios.get(API_BASE);
    cameras.value = res.data;
  } catch (err) {
    console.error("拉取设备列表失败", err);
  }
};

const openAddModal = () => {
  isEditing.value = false;
  editingId.value = null;
  form.value = { name: '', model: '', input_source: '' };
  showModal.value = true;
};

const startEdit = (cam) => {
  isEditing.value = true;
  editingId.value = cam.id;
  
  form.value.model = cam.model || '';
  form.value.name = cam.name;
  form.value.input_source = cam.input_source;
  
  showModal.value = true;
};

const closeModal = () => {
  showModal.value = false;
};

const submitCamera = async () => {
  if (!form.value.input_source.trim()) return;

  try {
    if (isEditing.value) {
      await axios.put(`${API_BASE}/${editingId.value}`, form.value);
    } else {
      await axios.post(API_BASE, form.value);
    }
    closeModal();
    fetchCameras();
  } catch (err) {
    if (err.response && err.response.data.detail) {
      alert(`操作失败: ${err.response.data.detail}`);
    } else {
      alert('网络通信异常，请检查后端运行状态。');
    }
  }
};

const deleteCamera = async (id) => {
  if (confirm('警告：此操作将移除该设备及相关的实时推流通道，确认执行吗？')) {
    try {
      await axios.delete(`${API_BASE}/${id}`);
      fetchCameras();
    } catch (err) {
      alert('删除失败');
    }
  }
};

let pollInterval = null;

onMounted(() => {
  fetchCameras();
  // 增加 3 秒轮询，实时同步在线/离线状态
  pollInterval = setInterval(() => {
    if (!showModal.value) { // 弹窗开启时不刷新避免打断操作
      fetchCameras(); 
    }
  }, 3000);
});

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval);
});
</script>

<style scoped>
/* 页面级容器 */
.manager-container {
  padding: 30px 40px;
  background-color: var(--bg-body);
  min-height: 100%;
}

/* 顶部标题区域 */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 25px;
}
.header-title h2 {
  margin: 0 0 8px 0;
  font-size: 24px;
  color: var(--text-main);
  font-weight: 600;
  letter-spacing: 0.5px;
}
.subtitle {
  color: var(--text-muted);
  font-size: 14px;
}

/* 核心按钮样式 */
.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--primary);
  color: #fff;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}
.btn-primary:hover:not(:disabled) {
  filter: brightness(1.1);
  transform: translateY(-1px);
  box-shadow: 0 6px 10px rgba(0, 0, 0, 0.15);
}
.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-ghost {
  background: transparent;
  color: var(--text-sub);
  border: 1px solid var(--border-color);
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: 0.2s;
}
.btn-ghost:hover {
  background: var(--hover-bg);
  color: var(--text-main);
}

/* 表格卡片卡槽 */
.table-card {
  background: var(--bg-card);
  border-radius: 12px;
  border: 1px solid var(--border-color);
  box-shadow: var(--shadow);
  overflow: hidden;
}

/* 企业级数据表格 */
.enterprise-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}
.enterprise-table th {
  background-color: var(--hover-bg);
  padding: 16px 20px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-sub);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 2px solid var(--border-color);
}
.enterprise-table td {
  padding: 16px 20px;
  font-size: 14px;
  color: var(--text-main);
  border-bottom: 1px solid var(--border-color);
  vertical-align: middle;
}
.table-row:hover {
  background-color: var(--hover-bg);
}

/* 运行状态指示器 */
.col-status {
  white-space: nowrap;
}
.status-indicator {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}
.status-online {
  background: rgba(34, 197, 94, 0.1);
  color: #16a34a;
}
.status-online .status-dot {
  background: #22c55e;
  box-shadow: 0 0 8px #22c55e;
}
.status-offline {
  background: rgba(239, 68, 68, 0.1);
  color: #dc2626;
}
.status-offline .status-dot {
  background: #ef4444;
}

/* 表格单元格定制 */
.col-id { color: var(--text-muted); font-family: monospace; }
.device-name { display: flex; align-items: center; gap: 10px; font-weight: 500; }
.device-icon { background: var(--bg-body); padding: 6px; border-radius: 6px; border: 1px solid var(--border-color); font-size: 16px;}
.badge { display: inline-block; padding: 4px 10px; background: var(--bg-body); border: 1px solid var(--border-color); border-radius: 20px; font-size: 12px; color: var(--text-sub); }
.code-block { background: var(--bg-body); padding: 6px 10px; border-radius: 6px; border: 1px solid var(--border-color); font-family: monospace; color: var(--primary); font-size: 13px;}
.path-text { color: var(--text-sub); }

/* 操作区按键 */
.col-actions { text-align: right; }
.btn-icon {
  background: transparent;
  border: 1px solid transparent;
  padding: 8px;
  border-radius: 6px;
  cursor: pointer;
  color: var(--text-muted);
  transition: 0.2s;
  margin-left: 5px;
  display: inline-flex;
}
.btn-edit:hover { background: rgba(59, 130, 246, 0.1); color: var(--primary); border-color: rgba(59, 130, 246, 0.2); }
.btn-delete:hover { background: rgba(239, 68, 68, 0.1); color: var(--danger); border-color: rgba(239, 68, 68, 0.2); }

/* 空状态 */
.empty-state { text-align: center; padding: 60px 0; }
.empty-content { display: inline-flex; flex-direction: column; align-items: center; gap: 15px; color: var(--text-muted); font-size: 14px; }

/* 模态弹框（背景与容器） */
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 999;
  animation: fadeIn 0.2s ease-out;
}
.modal-content {
  background: var(--bg-card);
  width: 500px;
  max-width: 90%;
  border-radius: 12px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  border: 1px solid var(--border-color);
  animation: slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  overflow: hidden;
}

/* 弹框头部 */
.modal-header {
  padding: 20px 25px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--bg-body);
}
.modal-header h3 { margin: 0; font-size: 18px; color: var(--text-main); font-weight: 600; }
.close-btn { background: transparent; border: none; font-size: 24px; color: var(--text-muted); cursor: pointer; line-height: 1; transition: 0.2s; }
.close-btn:hover { color: var(--danger); transform: scale(1.1); }

/* 弹框表单与设备型号选择相关 */
.modal-body { padding: 25px; }
.form-group { margin-bottom: 20px; display: flex; flex-direction: column; }
.form-group label { margin-bottom: 8px; font-size: 14px; font-weight: 500; color: var(--text-sub); }
.form-group input {
  padding: 12px 15px;
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-main);
  font-size: 14px;
  transition: all 0.2s;
  outline: none;
}
.form-group input:focus { border-color: var(--primary); box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1); }

.quick-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}
.quick-tag {
  padding: 4px 10px;
  background: var(--bg-body);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  font-size: 12px;
  color: var(--text-sub);
  cursor: pointer;
  transition: all 0.2s;
}
.quick-tag:hover {
  background: rgba(59, 130, 246, 0.1);
  color: var(--primary);
  border-color: rgba(59, 130, 246, 0.3);
}

.required-group label::after { content: " *"; color: var(--danger); }
.hint-text { margin-top: 8px; font-size: 12px; color: var(--text-muted); }

/* 弹框尾部 */
.modal-footer {
  padding: 15px 25px;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  background: var(--bg-body);
}

/* 动画效果 */
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
@keyframes slideUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
</style>